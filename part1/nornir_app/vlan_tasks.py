from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Tuple

from nornir.core.task import Task, Result
from nornir_netmiko.tasks import netmiko_send_command, netmiko_send_config


# -----------------------------
# Helpers
# -----------------------------

def _sanitize_hostname(name: str) -> str:
    """
    Cisco hostname:
      - letras, números y guion
      - max 63 chars
    """
    name = (name or "").strip()
    name = re.sub(r"[^A-Za-z0-9\-]", "-", name)
    name = re.sub(r"-{2,}", "-", name).strip("-")
    return name[:63]


def _parse_hostname(show_run_hostname: str) -> str:
    """
    Input esperado: output de "show run | include ^hostname"
    """
    for line in (show_run_hostname or "").splitlines():
        line = line.strip()
        if line.startswith("hostname "):
            return line.split("hostname ", 1)[1].strip()
    return ""


def _strip_trailing_prompt(text: str) -> str:
    """
    Algunos outputs devuelven el prompt al final.
    Esto lo deja más limpio para backup/evidencia.
    """
    if not text:
        return ""
    lines = text.splitlines()
    if lines and re.match(r"^\S.+[>#]$", lines[-1].strip()):
        return "\n".join(lines[:-1]).rstrip()
    return text.rstrip()


def _format_vlan_brief_like_console(raw: str) -> str:
    """
    IOSv a veces devuelve VLAN 1 con todos los puertos en una sola línea.
    Esto lo formatea en varias líneas (tipo CLI real) para que quede prolijo.
    """
    try:
        lines = [l.rstrip("\r") for l in (raw or "").splitlines()]
        out: List[str] = []
        i = 0

        while i < len(lines):
            line = lines[i]

            # Detectar VLAN 1 default active ...
            if re.match(r"^\s*1\s+default\s+active\s+", line):
                m = re.match(r"^(\s*1)\s+(default)\s+(active)\s+(.*)$", line)
                if m:
                    vlan_col, name_col, status_col, ports = m.groups()
                    ports = ports.strip()
                    port_list = [p.strip() for p in ports.split(",") if p.strip()]

                    # 4 por línea para que quede “tipo CLI”
                    chunks = [port_list[j:j + 4] for j in range(0, len(port_list), 4)]

                    first_chunk = ", ".join(chunks[0]) if chunks else ""
                    out.append(f"{vlan_col:<4} {name_col:<32} {status_col:<9} {first_chunk}")

                    # indent similar al CLI
                    indent = " " * 48
                    for c in chunks[1:]:
                        out.append(f"{indent}{', '.join(c)}")

                    i += 1
                    continue

            out.append(line)
            i += 1

        return "\n".join(out)
    except Exception:
        return raw or ""


def _extract_relevant_vlans(show_vlan_brief: str, keep_ids: List[int]) -> str:
    """
    Devuelve un "show vlan brief" recortado, dejando:
      - Encabezado
      - VLANs pedidas (keep_ids)
      - Continuaciones (líneas indentadas) de VLAN 1 si aplica
    """
    raw = (show_vlan_brief or "").strip("\n")
    raw = _format_vlan_brief_like_console(raw)

    lines = raw.splitlines()
    kept: List[str] = []
    header_mode = False
    keep_set = set(int(x) for x in keep_ids)

    last_kept_vlan_id = None

    for line in lines:
        stripped = line.strip()

        # Header
        if stripped.startswith("VLAN Name"):
            header_mode = True
            kept.append(line.rstrip())
            last_kept_vlan_id = None
            continue

        if header_mode and stripped.startswith("----"):
            kept.append(line.rstrip())
            last_kept_vlan_id = None
            continue

        # VLAN line (comienza con número)
        m = re.match(r"^\s*(\d+)\s+", line)
        if m:
            vid = int(m.group(1))
            if vid in keep_set:
                kept.append(line.rstrip())
                last_kept_vlan_id = vid
            else:
                last_kept_vlan_id = None
            continue

        # Continuación de puertos (para VLAN 1 wrap)
        if last_kept_vlan_id == 1 and re.match(r"^\s{10,}\S", line):
            kept.append(line.rstrip())

    return "\n".join(kept).rstrip()


def _parse_vlan_brief_map(show_vlan_full: str) -> Dict[int, str]:
    """
    Parse robusto de 'show vlan brief' -> { vlan_id: vlan_name }

    Espera líneas tipo:
      10   VLAN_DATOS                       active
      1002 fddi-default                     act/unsup

    Nota: la columna Name ocupa un ancho fijo en IOS (aprox 32),
    así que capturamos "todo" entre ID y Status.
    """
    out: Dict[int, str] = {}
    for line in (show_vlan_full or "").splitlines():
        m = re.match(r"^\s*(\d+)\s+(.+?)\s{2,}(\S+)\s*", line)
        if not m:
            continue
        vid = int(m.group(1))
        name = m.group(2).strip()
        # status = m.group(3)  # no lo usamos ahora
        out[vid] = name
    return out


# -----------------------------
# Tasks
# -----------------------------

def create_vlans(task: Task, vlans: List[Dict[str, Any]]) -> Result:
    """
    Crea VLANs SOLO si faltan o si el nombre no coincide.
    (Idempotente: no reconfigura lo que ya está OK)
    """
    # Leemos VLANs actuales una sola vez
    vr = task.run(task=netmiko_send_command, command_string="show vlan brief", name="precheck_vlans")
    show_vlan_full = _strip_trailing_prompt(vr.result)
    current_map = _parse_vlan_brief_map(show_vlan_full)

    cfg: List[str] = []
    changes: List[str] = []

    for v in vlans:
        vid = int(v["id"])
        desired_name = str(v["name"]).strip()

        current_name = current_map.get(vid)

        if current_name == desired_name:
            # ya está OK -> no tocamos
            continue

        # si existe pero con otro nombre, lo renombramos igual (y si no existe, lo crea)
        cfg.extend([f"vlan {vid}", f"name {desired_name}", "exit"])
        if current_name is None:
            changes.append(f"create vlan {vid} name {desired_name}")
        else:
            changes.append(f"rename vlan {vid}: '{current_name}' -> '{desired_name}'")

    if not cfg:
        return Result(host=task.host, result="No VLAN changes needed.", changed=False)

    r = task.run(task=netmiko_send_config, config_commands=cfg, name="create_vlans")
    result_text = (r.result or "").rstrip()
    if changes:
        result_text = "\n".join(changes) + "\n\n" + result_text

    return Result(host=task.host, result=result_text, changed=True)


def set_hostname(task: Task, desired_hostname: str) -> Result:
    """
    Setea hostname SOLO si no coincide.
    """
    desired_hostname = _sanitize_hostname(desired_hostname)
    if not desired_hostname:
        return Result(host=task.host, result="Hostname vacío. Se omite.", changed=False)

    # Pre-check: hostname actual
    hr = task.run(
        task=netmiko_send_command,
        command_string="show run | include ^hostname",
        name="precheck_hostname",
    )
    actual_hostname = _parse_hostname(_strip_trailing_prompt(hr.result))

    if actual_hostname == desired_hostname:
        return Result(host=task.host, result=f"Hostname already OK: {actual_hostname}", changed=False)

    r = task.run(
        task=netmiko_send_config,
        config_commands=[f"hostname {desired_hostname}"],
        name="set_hostname",
    )
    return Result(host=task.host, result=r.result, changed=True)


def save_config(task: Task) -> Result:
    # IOSv acepta "write memory"
    r = task.run(task=netmiko_send_command, command_string="write memory", name="save_config")
    return Result(host=task.host, result=r.result, changed=True)


def backup_running_config(task: Task, backup_dir: str = "backups", tag: str = "backup") -> Result:
    """
    Backup de running-config a un archivo local:
      backups/<hostname>_<tag>_<YYYYmmdd_HHMMSS>.cfg
    """
    h = task.run(task=netmiko_send_command, command_string="show run | include ^hostname", name="get_hostname")
    current_hostname = _parse_hostname(_strip_trailing_prompt(h.result)) or task.host.name

    run = task.run(task=netmiko_send_command, command_string="show running-config", name="show_running_config")
    cfg_text = _strip_trailing_prompt(run.result)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    Path(backup_dir).mkdir(parents=True, exist_ok=True)

    filename = f"{current_hostname}_{tag}_{ts}.cfg"
    fullpath = Path(backup_dir) / filename
    fullpath.write_text(cfg_text, encoding="utf-8")

    return Result(host=task.host, result=f"Backup OK: {fullpath}", changed=False)


def validate_config(task: Task, desired_hostname: str, desired_vlans: List[Dict[str, Any]]) -> Result:
    """
    Valida:
      - hostname
      - VLAN IDs presentes
      - VLAN name correcto

    Devuelve payload usable por UI + evidencia.
    """
    deviations: List[str] = []

    desired_hostname = _sanitize_hostname(desired_hostname)

    # Hostname actual
    hr = task.run(task=netmiko_send_command, command_string="show run | include ^hostname", name="validate_hostname")
    actual_hostname = _parse_hostname(_strip_trailing_prompt(hr.result))

    if desired_hostname and actual_hostname != desired_hostname:
        deviations.append(f"HOSTNAME mismatch: expected '{desired_hostname}' actual '{actual_hostname}'")

    # VLANs
    vr = task.run(task=netmiko_send_command, command_string="show vlan brief", name="validate_vlans_show")
    show_vlan_full = _strip_trailing_prompt(vr.result)

    desired_vlan_ids = sorted({int(v["id"]) for v in desired_vlans})
    # Para UI: default VLANs + las pedidas
    keep_ids = sorted(set(desired_vlan_ids + [1, 1002, 1003, 1004, 1005]))

    current_map = _parse_vlan_brief_map(show_vlan_full)
    present_ids = set(current_map.keys())

    missing = sorted(set(desired_vlan_ids) - present_ids)
    if missing:
        deviations.append(f"Missing VLAN IDs: {missing}")

    # Validar nombres de VLAN
    expected_map = {int(v["id"]): str(v["name"]).strip() for v in desired_vlans}
    for vid, expected_name in expected_map.items():
        actual_name = current_map.get(vid)
        if actual_name is None:
            continue
        if actual_name != expected_name:
            deviations.append(f"VLAN {vid} name mismatch: expected '{expected_name}' actual '{actual_name}'")

    ok = len(deviations) == 0

    # UI corto
    show_vlan_short = _extract_relevant_vlans(show_vlan_full, keep_ids)

    payload = {
        "ok": ok,
        "desired_hostname": desired_hostname,
        "actual_hostname": actual_hostname,
        "desired_vlans": desired_vlans,
        "deviations": deviations,

        # UI (texto preformateado)
        "show_vlan_brief": show_vlan_short,

        # Para evidencia JSON legible
        "show_vlan_brief_lines": show_vlan_short.splitlines(),

        # FULL / forense
        "show_vlan_brief_full": show_vlan_full,
    }

    return Result(host=task.host, result=payload, failed=not ok)
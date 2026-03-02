from __future__ import annotations

import re
from typing import Dict, Any

from nornir.core.task import Task, Result
from nornir_netmiko.tasks import netmiko_send_command


# -----------------------------
# Helpers
# -----------------------------

def _sanitize_hostname(name: str) -> str:
    """
    Cisco hostname rules:
      - letters, numbers, hyphen
      - max 63 chars

    Nota: esta función espera SOLO el nombre, no "hostname <X>".
    """
    name = (name or "").strip()
    name = re.sub(r"[^A-Za-z0-9\-]", "-", name)
    name = re.sub(r"-{2,}", "-", name).strip("-")
    return name[:63]


def _normalize_expected(expected: str) -> str:
    """
    Acepta:
      - "SW-DC1-AR"
      - "hostname SW-DC1-AR"
    y devuelve SOLO "SW-DC1-AR" sanitizado.
    """
    e = (expected or "").strip()
    if e.lower().startswith("hostname "):
        e = e.split(" ", 1)[1].strip()
    return _sanitize_hostname(e)


def _parse_hostname(output: str) -> str:
    """
    Parse "hostname <X>" desde el output.
    """
    for line in (output or "").splitlines():
        line = line.strip()
        if line.startswith("hostname "):
            return line.split("hostname ", 1)[1].strip()
    return ""


def _strip_trailing_prompt(text: str) -> str:
    """
    Algunos devices devuelven el prompt al final del output.
    Remueve una última línea tipo:
      - "SW-DC1-AR#"
      - "SW-DC1-AR>"
    Evita falsos positivos chequeando que sea UNA sola palabra + prompt.
    """
    if not text:
        return ""
    lines = text.splitlines()
    if not lines:
        return ""

    last = lines[-1].strip()

    # Prompt típico: no espacios, termina en # o >
    # Ej: SW-DC1-AR#, SW1>, Router-1#
    if re.match(r"^[A-Za-z0-9\-\._/()]+[>#]$", last):
        return "\n".join(lines[:-1]).rstrip()

    return text.rstrip()


def _collapse_spaces(s: str) -> str:
    """
    Normaliza múltiples espacios a uno solo (para outputs raros).
    """
    return re.sub(r"[ \t]+", " ", (s or "").strip())


# -----------------------------
# Tasks
# -----------------------------

def show_version(task: Task) -> Result:
    """
    Test rápido de conectividad / evidencia.
    """
    r = task.run(
        task=netmiko_send_command,
        command_string="show version | i IOSv",
        name="show_version",
    )
    out = _strip_trailing_prompt(r.result)
    out = out.strip()
    return Result(host=task.host, result=out, changed=False)


def validate_hostname(task: Task, expected: str) -> Result:
    """
    Valida hostname contra lo esperado.
    Devuelve payload estructurado usable por UI o evidencia.

    expected: preferible SOLO hostname (ej: "SW-DC1-AR"),
              pero tolera "hostname SW-DC1-AR" por compatibilidad.
    """
    expected_clean = _normalize_expected(expected)

    r = task.run(
        task=netmiko_send_command,
        command_string="show run | include ^hostname",
        name="validate_hostname",
    )

    raw_output = _strip_trailing_prompt(r.result)
    actual = _parse_hostname(raw_output)
    actual_clean = _sanitize_hostname(actual)

    ok = True
    deviations = []

    # Comparación robusta (por si hay tabs o algo raro)
    if expected_clean and _collapse_spaces(actual_clean) != _collapse_spaces(expected_clean):
        ok = False
        deviations.append(f"Hostname mismatch: expected '{expected_clean}' actual '{actual_clean}'")

    payload: Dict[str, Any] = {
        "ok": ok,
        "expected": expected_clean,
        "actual": actual_clean,
        "raw_output": raw_output,
        "deviations": deviations,
    }

    return Result(
        host=task.host,
        result=payload,
        failed=not ok,
        changed=False,
    )
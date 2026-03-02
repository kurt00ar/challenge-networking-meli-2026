# frontend/app.py
from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path

from flask import Flask, render_template, request, send_from_directory, abort
from werkzeug.utils import safe_join
from nornir import InitNornir

from nornir_app.vlan_tasks import (
    create_vlans,
    set_hostname,
    save_config,
    backup_running_config,
    validate_config,
)

app = Flask(__name__)

# ---- UX: evita cache durante lab (especialmente templates) ----
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0

NR_CONFIG = "nornir_app/inventory/config.yaml"

DEFAULT_ROWS = [
    {"id": 10, "name": "VLAN_DATOS"},
    {"id": 20, "name": "VLAN_VOZ"},
    {"id": 50, "name": "VLAN_SEGURIDAD"},
]

# Defaults por host para evitar hostnames vacíos
DEFAULT_HOSTNAMES = {
    "SW-DC1-AR": "SW-DC1-AR",
    "SW-DC1-BR": "SW-DC1-BR",
}


# -----------------------------------------------------------------------------
# Anti-cache headers (mejor que solo config)
# -----------------------------------------------------------------------------
@app.after_request
def add_no_cache_headers(resp):
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def _safe_int(v, default=None):
    try:
        return int(v)
    except Exception:
        return default


def _clean_vlan_rows(form) -> list[dict]:
    rows = []
    for i in (1, 2, 3):
        vid = _safe_int(form.get(f"vlan_id_{i}"), None)
        vname = (form.get(f"vlan_name_{i}") or "").strip()
        if vid and vname:
            rows.append({"id": vid, "name": vname})
    return rows


def _fmt_seconds(s: float) -> str:
    return f"{s:.2f}s"


def _pick_desired_hostname(host_name: str, user_value: str) -> str:
    """
    Evita mandar hostname vacío:
    - si user_value viene vacío => usa default por host
    - si user_value viene => úsalo (sanitiza en vlan_tasks.py)
    """
    v = (user_value or "").strip()
    return v if v else DEFAULT_HOSTNAMES.get(host_name, host_name)


def _extract_filename_from_backup_msg(msg: str) -> str | None:
    """
    msg típico: "Backup OK: backups/SW-DC1-AR_prechange_....cfg"
    Devuelve solo el filename para construir URL /backups/<file>
    """
    if not msg:
        return None
    marker = "Backup OK:"
    if marker not in msg:
        return None
    path_part = msg.split(marker, 1)[1].strip()
    try:
        return Path(path_part).name
    except Exception:
        return None


# -----------------------------------------------------------------------------
# Health
# -----------------------------------------------------------------------------
@app.get("/health")
def health():
    return {"ok": True}


# -----------------------------------------------------------------------------
# UI
# -----------------------------------------------------------------------------
@app.get("/")
def index():
    return render_template(
        "index.html",
        default_rows=DEFAULT_ROWS,
        default_sw1=DEFAULT_HOSTNAMES["SW-DC1-AR"],
        default_sw2=DEFAULT_HOSTNAMES["SW-DC1-BR"],
    )


# -----------------------------------------------------------------------------
# Static evidence / backups (para links en result.html)
# -----------------------------------------------------------------------------
@app.get("/evidence/<path:filename>")
def download_evidence(filename: str):
    """
    Sirve archivos dentro de ./evidence/...
    Ej: /evidence/flask/run_20260225_041015.json
    """
    base_dir = Path("evidence").resolve()

    safe_path = safe_join(str(base_dir), filename)
    if not safe_path:
        abort(400)

    p = Path(safe_path)
    if not p.exists() or not p.is_file():
        abort(404)

    # send_from_directory requiere dir + filename relativo
    return send_from_directory(str(base_dir), filename, as_attachment=False)


@app.get("/backups/<path:filename>")
def download_backup(filename: str):
    """
    Sirve archivos dentro de ./backups/...
    Ej: /backups/SW-DC1-AR_prechange_20260225_040951.cfg
    """
    base_dir = Path("backups").resolve()

    safe_path = safe_join(str(base_dir), filename)
    if not safe_path:
        abort(400)

    p = Path(safe_path)
    if not p.exists() or not p.is_file():
        abort(404)

    return send_from_directory(str(base_dir), filename, as_attachment=False)


# -----------------------------------------------------------------------------
# Apply
# -----------------------------------------------------------------------------
@app.post("/apply")
def apply():
    t0 = time.perf_counter()

    # form inputs
    sw1_hostname_in = (request.form.get("hostname_switch1") or "").strip()
    sw2_hostname_in = (request.form.get("hostname_switch2") or "").strip()
    vlans = _clean_vlan_rows(request.form) or DEFAULT_ROWS

    # Inicializa Nornir
    nr = InitNornir(config_file=NR_CONFIG)

    # Resolver desired hostnames (con fallback)
    desired_by_host = {
        "SW-DC1-AR": _pick_desired_hostname("SW-DC1-AR", sw1_hostname_in),
        "SW-DC1-BR": _pick_desired_hostname("SW-DC1-BR", sw2_hostname_in),
    }

    inputs = {
        "switch1_hostname": desired_by_host["SW-DC1-AR"],
        "switch2_hostname": desired_by_host["SW-DC1-BR"],
        "vlans": vlans,
    }

    results_view: dict = {}
    overall_ok = True

    summary = {
        "hosts_ok": 0,
        "hosts_total": len(nr.inventory.hosts),
        "alerts_total": 0,
    }

    for host_name in nr.inventory.hosts.keys():
        host_t0 = time.perf_counter()

        host_nr = nr.filter(name=host_name)
        desired_hostname = desired_by_host.get(host_name, host_name)

        host_block = {
            "ok": True,
            "steps": [],
            "alerts": [],
            "validation": None,
            "backup_pre": None,
            "backup_post": None,
            # Opcional: links directos a backups
            "backup_pre_file": None,
            "backup_post_file": None,
            "timing": {
                "host_total": None,
                "host_total_human": None,
            },
        }

        def run_step(step_name: str, fn, **kwargs):
            step_t0 = time.perf_counter()
            r = host_nr.run(task=fn, **kwargs)
            elapsed = time.perf_counter() - step_t0

            out = str(r[host_name].result)
            host_block["steps"].append(
                {
                    "name": step_name,
                    "output": out,
                    "elapsed_s": elapsed,
                    "elapsed_human": _fmt_seconds(elapsed),
                }
            )
            return r, out

        try:
            # ✅ Backup PRE
            _, out_pre = run_step(
                "backup_prechange",
                backup_running_config,
                backup_dir="backups",
                tag="prechange",
            )
            host_block["backup_pre"] = out_pre
            host_block["backup_pre_file"] = _extract_filename_from_backup_msg(out_pre)

            # VLANs
            run_step("create_vlans", create_vlans, vlans=vlans)

            # Hostname
            run_step("set_hostname", set_hostname, desired_hostname=desired_hostname)

            # Save config
            run_step("save_config", save_config)

            # ✅ Backup POST
            _, out_post = run_step(
                "backup_postchange",
                backup_running_config,
                backup_dir="backups",
                tag="postchange",
            )
            host_block["backup_post"] = out_post
            host_block["backup_post_file"] = _extract_filename_from_backup_msg(out_post)

            # Validate (payload estructurado)
            step_t0 = time.perf_counter()
            r5 = host_nr.run(task=validate_config, desired_hostname=desired_hostname, desired_vlans=vlans)
            elapsed = time.perf_counter() - step_t0

            validation_payload = r5[host_name].result
            host_block["validation"] = validation_payload

            # Step “corto” para no ensuciar
            host_block["steps"].append(
                {
                    "name": "validate_config",
                    "output": "OK" if validation_payload.get("ok", False) else "ALERTS",
                    "elapsed_s": elapsed,
                    "elapsed_human": _fmt_seconds(elapsed),
                }
            )

            if not validation_payload.get("ok", False):
                host_block["ok"] = False
                overall_ok = False
                host_block["alerts"] = validation_payload.get("deviations", [])
                summary["alerts_total"] += len(host_block["alerts"])
            else:
                summary["hosts_ok"] += 1

        except Exception as e:
            host_block["ok"] = False
            overall_ok = False
            msg = f"Unhandled exception on host '{host_name}': {type(e).__name__}: {e}"
            host_block["alerts"] = [msg]
            summary["alerts_total"] += 1
            host_block["steps"].append(
                {
                    "name": "exception",
                    "output": msg,
                    "elapsed_s": 0.0,
                    "elapsed_human": _fmt_seconds(0.0),
                }
            )

        host_block["timing"]["host_total"] = time.perf_counter() - host_t0
        host_block["timing"]["host_total_human"] = _fmt_seconds(host_block["timing"]["host_total"])
        results_view[host_name] = host_block

    total_elapsed = time.perf_counter() - t0
    total_elapsed_human = _fmt_seconds(total_elapsed)

    # Badge status
    badge = {"text": "CHANGE SUCCESSFUL", "tone": "success"} if overall_ok else {"text": "CHANGE COMPLETED WITH ALERTS", "tone": "warning"}

    # Evidence JSON
    Path("evidence/flask").mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    evidence_path = f"evidence/flask/run_{ts}.json"

    evidence_payload = {
        "overall_ok": overall_ok,
        "badge": badge,
        "execution_time_s": total_elapsed,
        "execution_time_human": total_elapsed_human,
        "summary": summary,
        "inputs": inputs,
        "results": results_view,
    }

    Path(evidence_path).write_text(
        json.dumps(evidence_payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # URL servida por nuestro endpoint /evidence/...
    evidence_url = "/" + evidence_path.replace("\\", "/")

    return render_template(
        "result.html",
        overall_ok=overall_ok,
        badge=badge,
        summary=summary,
        execution_time_human=total_elapsed_human,
        execution_time_s=total_elapsed,
        evidence_path=evidence_path,
        evidence_url=evidence_url,
        inputs=inputs,
        results=results_view,
    )
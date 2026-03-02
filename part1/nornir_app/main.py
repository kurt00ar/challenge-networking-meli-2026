from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from nornir import InitNornir
from nornir_utils.plugins.functions import print_result
from nornir_netmiko.tasks import netmiko_send_command

from nornir_app.vlan_tasks import (
    create_vlans,
    set_hostname,
    save_config,
    backup_running_config,
    validate_config,
)

# === Challenge VLANs ===
VLANS = [
    {"id": 10, "name": "VLAN_DATOS"},
    {"id": 20, "name": "VLAN_VOZ"},
    {"id": 50, "name": "VLAN_SEGURIDAD"},
]

# === Hostname deseado por host (inventario) ===
HOSTNAME_MAP = {
    "SW-DC1-AR": "SW-DC1-AR",
    "SW-DC1-BR": "SW-DC1-BR",
}

NR_CONFIG = "nornir_app/inventory/config.yaml"


def _fmt_seconds(s: float) -> str:
    return f"{s:.2f}s"


def _append_text(path: Path, txt: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(txt + "\n")


def _pick_desired_hostname(host_name: str, desired: str) -> str:
    # fallback seguro si alguna vez desired viene vacío
    d = (desired or "").strip()
    return d if d else host_name


def _to_jsonable(v: Any) -> Any:
    """
    Asegura que el evidence JSON no explote por objetos raros.
    """
    if isinstance(v, (dict, list, str, int, float, bool)) or v is None:
        return v
    return str(v)


def run() -> None:
    t0 = time.perf_counter()

    nr = InitNornir(config_file=NR_CONFIG)
    hosts = list(nr.inventory.hosts.keys())

    # Evidence
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    evidence_txt = Path(f"evidence/cli/run_{ts}.txt")
    evidence_json = Path(f"evidence/cli/run_{ts}.json")

    def log(txt: str) -> None:
        print(txt)
        _append_text(evidence_txt, txt)

    log(f"=== CLI RUN {ts} ===")
    log(f"Inventory hosts: {hosts}")
    log(f"NR config: {NR_CONFIG}")

    summary = {
        "hosts_total": len(hosts),
        "hosts_ok": 0,
        "alerts_total": 0,
    }

    results: Dict[str, Dict[str, Any]] = {}

    # 1) Test conectividad (show version)
    log("\n[1] Connectivity test: show version | i IOSv")
    r0 = nr.run(task=netmiko_send_command, command_string="show version | i IOSv", name="show_version")
    print_result(r0)

    # 2) Apply + backup + validate por host
    for h in hosts:
        host_t0 = time.perf_counter()

        desired_hostname = _pick_desired_hostname(h, HOSTNAME_MAP.get(h, h))
        host_nr = nr.filter(name=h)

        host_block: Dict[str, Any] = {
            "ok": True,
            "desired_hostname": desired_hostname,
            "steps": [],
            "alerts": [],
            "validation": None,
            "backup_pre": None,
            "backup_post": None,
            "timing": {"host_total_s": None, "host_total_human": None},
        }

        log("\n==============================")
        log(f"HOST: {h}  (desired_hostname={desired_hostname})")
        log("==============================")

        def run_step(step_name: str, fn, **kwargs):
            step_t0 = time.perf_counter()
            r = host_nr.run(task=fn, **kwargs)
            elapsed = time.perf_counter() - step_t0

            out = r[h].result
            host_block["steps"].append(
                {
                    "name": step_name,
                    "elapsed_s": elapsed,
                    "elapsed_human": _fmt_seconds(elapsed),
                    "output": _to_jsonable(out),
                }
            )
            return r, out

        try:
            # Backup PRE
            r_pre, out_pre = run_step("backup_prechange", backup_running_config, backup_dir="backups", tag="prechange")
            host_block["backup_pre"] = str(out_pre)
            print_result(r_pre)

            # VLANs
            r_vl, _out_vl = run_step("create_vlans", create_vlans, vlans=VLANS)
            print_result(r_vl)

            # Hostname
            r_hn, _out_hn = run_step("set_hostname", set_hostname, desired_hostname=desired_hostname)
            print_result(r_hn)

            # Save
            r_sv, _out_sv = run_step("save_config", save_config)
            print_result(r_sv)

            # Backup POST
            r_post, out_post = run_step("backup_postchange", backup_running_config, backup_dir="backups", tag="postchange")
            host_block["backup_post"] = str(out_post)
            print_result(r_post)

            # Validate (single source of truth)
            r_val, payload = run_step("validate_config", validate_config, desired_hostname=desired_hostname, desired_vlans=VLANS)
            print_result(r_val)

            host_block["validation"] = payload

            if isinstance(payload, dict) and not payload.get("ok", False):
                host_block["ok"] = False
                host_block["alerts"] = payload.get("deviations", []) or []
                summary["alerts_total"] += len(host_block["alerts"])

                log(">>> ALERTS DETECTADAS:")
                for d in host_block["alerts"]:
                    log(f" - {d}")
            else:
                summary["hosts_ok"] += 1
                log(">>> OK: Sin desviaciones.")

        except Exception as e:
            host_block["ok"] = False
            msg = f"Unhandled exception on host '{h}': {type(e).__name__}: {e}"
            host_block["alerts"] = [msg]
            summary["alerts_total"] += 1
            log(">>> ERROR:")
            log(msg)

        host_block["timing"]["host_total_s"] = time.perf_counter() - host_t0
        host_block["timing"]["host_total_human"] = _fmt_seconds(host_block["timing"]["host_total_s"])

        results[h] = host_block

    total_elapsed = time.perf_counter() - t0
    overall_ok = summary["hosts_ok"] == summary["hosts_total"] and summary["alerts_total"] == 0

    # Evidence JSON estructurado
    payload_json = {
        "timestamp": ts,
        "overall_ok": overall_ok,
        "execution_time_s": total_elapsed,
        "execution_time_human": _fmt_seconds(total_elapsed),
        "summary": summary,
        "inputs": {
            "vlans": VLANS,
            "hostname_map": HOSTNAME_MAP,
        },
        "results": results,
        "evidence_txt": str(evidence_txt),
    }

    evidence_json.write_text(json.dumps(payload_json, indent=2, ensure_ascii=False), encoding="utf-8")

    # Resumen final
    log("\n=== SUMMARY ===")
    log(f"Overall OK: {overall_ok}")
    log(f"Execution time: {_fmt_seconds(total_elapsed)}")
    log(f"Hosts OK: {summary['hosts_ok']} / {summary['hosts_total']}")
    log(f"Alerts total: {summary['alerts_total']}")
    log(f"Evidence TXT: {evidence_txt}")
    log(f"Evidence JSON: {evidence_json}")
    log("=== END RUN ===")


if __name__ == "__main__":
    run()
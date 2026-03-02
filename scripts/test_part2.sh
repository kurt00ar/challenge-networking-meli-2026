#!/usr/bin/env bash
set -euo pipefail

CONTAINER="Challenge-Networking-Meli-2026"
PART2_DIR="/app/part2/ansible_app"
INV="inventories/lab/hosts.yml"

echo "== Entering container and running Part2 tests =="
docker exec -it "$CONTAINER" bash -lc "
  set -e
  cd $PART2_DIR

  echo '--- ansible --version ---'
  ansible --version

  echo '--- inventory graph ---'
  ansible-inventory -i $INV --graph

  echo '--- FGT system_status ---'
  ansible -i $INV fortigate -m fortinet.fortios.fortios_monitor_fact -a 'vdom=root selector=system_status' -vv

  echo '--- PAN show system info ---'
  ansible -i $INV paloalto -m paloaltonetworks.panos.panos_op -a 'provider={{ provider }} cmd=\"show system info\"' -vv
"
echo "✅ Done."

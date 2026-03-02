SHELL := /bin/bash

# ---------- Project knobs ----------
PROJECT_NAME := Challenge-Networking-Meli-2026
SERVICE      := challenge-networking
CONTAINER    := Challenge-Networking-Meli-2026

PART2_DIR    := /app/part2/ansible_app
INV          := inventories/lab/hosts.yml

# Env handling (root)
ENV_FILE     := .env
ENV_EXAMPLE  := .env.example

# Compose commands:
DC      := docker compose
DC_ENV  := docker compose --env-file $(ENV_FILE)

# ---------- Helpers ----------
.PHONY: help env env-force env-show env-check \
        build up down restart ps logs shell sh-part2 \
        lint-ansible test test-fgt test-pan \
        part2 part2-fgt part2-pan part2-run-all part2-all \
        evidence-fgt evidence-pan evidence-all clean

help:
	@echo ""
	@echo "Targets:"
	@echo "  make env            Create .env from .env.example if missing (stops so you can edit)"
	@echo "  make env-force      Create .env from .env.example if missing (continues)"
	@echo "  make env-show       Print loaded env keys (no values)"
	@echo "  make env-check      Validate required keys exist in .env"
	@echo "  make build          Build image(s)"
	@echo "  make up             Start container(s)"
	@echo "  make down           Stop container(s) (never requires .env)"
	@echo "  make restart        Restart container(s) (requires env-check)"
	@echo "  make ps             Show compose status"
	@echo "  make logs           Follow logs"
	@echo "  make shell          Bash into main container"
	@echo "  make sh-part2       Bash into container and cd Part2 Ansible dir"
	@echo "  make lint-ansible   Syntax check Part2 playbooks"
	@echo "  make test           Run connectivity tests to FortiGate + Palo Alto"
	@echo "  make part2          Run Part2 core playbooks (01-03)"
	@echo "  make part2-run-all  Run playbooks/run_all.yml (full pipeline)"
	@echo "  make part2-all      Run ALL Part2 playbooks if present"
	@echo "  make evidence-fgt   Save evidence (FGT) to part2/evidence/<TS>/"
	@echo "  make evidence-pan   Save evidence (PAN) to part2/evidence/<TS>/"
	@echo "  make evidence-all   Save evidence (FGT+PAN) to part2/evidence/<TS>/"
	@echo "  make clean          Stop and remove container(s)"
	@echo ""

# ---------- Env ----------
env:
	@test -f $(ENV_FILE) || (cp $(ENV_EXAMPLE) $(ENV_FILE) && echo "✅ Creado $(ENV_FILE) desde $(ENV_EXAMPLE). Editalo y volvé a correr." && exit 1)

env-force:
	@test -f $(ENV_FILE) || (cp $(ENV_EXAMPLE) $(ENV_FILE) && echo "✅ Creado $(ENV_FILE) desde $(ENV_EXAMPLE).")

env-show: env-force
	@echo "== Keys in $(ENV_FILE) (sin mostrar valores) =="
	@grep -E '^[A-Z0-9_]+=' $(ENV_FILE) | sed 's/=.*$$/=***/g' || true

env-check: env-force
	@set -e; \
	missing=0; \
	for k in PAN_HOST PAN_API_KEY FGT_HOST; do \
	  if ! grep -qE "^$${k}=" $(ENV_FILE); then \
	    echo "❌ Falta $${k} en $(ENV_FILE)"; missing=1; \
	  fi; \
	done; \
	if [ $$missing -eq 1 ]; then exit 1; fi; \
	echo "✅ .env OK (keys requeridas presentes): PAN_HOST PAN_API_KEY FGT_HOST"

# ---------- Compose lifecycle ----------
build: env-check
	$(DC_ENV) build --no-cache

up: env-check
	$(DC_ENV) up -d --build

down:
	$(DC) down

restart: env-check
	$(DC) down
	$(DC_ENV) up -d --build

ps:
	$(DC) ps

logs:
	$(DC) logs -f $(SERVICE)

# ---------- Shell helpers ----------
shell:
	$(DC) exec $(SERVICE) bash

sh-part2: env-check
	$(DC_ENV) exec $(SERVICE) bash -lc "cd $(PART2_DIR) && pwd && ls -la && bash"

# ---------- Ansible checks ----------
lint-ansible: env-check
	$(DC_ENV) exec $(SERVICE) bash -lc "\
		set -e; \
		cd $(PART2_DIR); \
		echo '== ansible --version =='; ansible --version; \
		echo '== inventory graph =='; ansible-inventory -i $(INV) --graph; \
		echo '== playbooks found =='; ls -la playbooks || true; \
		echo '== syntax-check playbooks =='; \
		shopt -s nullglob; \
		files=(playbooks/*.yml); \
		if [ $${#files[@]} -eq 0 ]; then echo 'WARN: no playbooks/*.yml found'; exit 0; fi; \
		for f in \"$${files[@]}\"; do \
		  echo \"-- $$f\"; \
		  ansible-playbook -i $(INV) \"$$f\" --syntax-check; \
		done \
	"

# ---------- Connectivity tests ----------
test: env-check test-fgt test-pan
	@echo ""
	@echo "✅ All connectivity tests passed."
	@echo ""

test-fgt: env-check
	$(DC_ENV) exec -e PAN_HOST -e PAN_API_KEY -e PAN_HTTPS_PORT -e FGT_HOST -e FGT_USER -e FGT_PASS $(SERVICE) bash -lc "\
		set -e; \
		cd $(PART2_DIR); \
		echo '== FortiGate system_status =='; \
		ansible -i $(INV) fortigate \
		  -m fortinet.fortios.fortios_monitor_fact \
		  -a 'vdom=root selector=system_status' \
	"

test-pan: env-check
	$(DC_ENV) exec -e PAN_HOST -e PAN_API_KEY -e PAN_HTTPS_PORT $(SERVICE) bash -lc "\
		set -e; \
		cd $(PART2_DIR); \
		test -f playbooks/00_test_pan.yml || (echo '❌ Missing playbook: playbooks/00_test_pan.yml' && exit 1); \
		echo '== Palo Alto API test =='; \
		ansible-playbook -i $(INV) playbooks/00_test_pan.yml \
	"

# ---------- Run Part2 ----------
part2: env-check
	$(DC_ENV) exec $(SERVICE) bash -lc "\
		set -e; \
		cd $(PART2_DIR); \
		ansible-playbook -i $(INV) playbooks/01_fortigate_ipsec.yml; \
		ansible-playbook -i $(INV) playbooks/02_paloalto_ipsec.yml; \
		ansible-playbook -i $(INV) playbooks/03_paloalto_network.yml; \
	"

part2-fgt: env-check
	$(DC_ENV) exec $(SERVICE) bash -lc "\
		set -e; \
		cd $(PART2_DIR); \
		ansible-playbook -i $(INV) playbooks/01_fortigate_ipsec.yml; \
	"

part2-pan: env-check
	$(DC_ENV) exec $(SERVICE) bash -lc "\
		set -e; \
		cd $(PART2_DIR); \
		ansible-playbook -i $(INV) playbooks/02_paloalto_ipsec.yml; \
		ansible-playbook -i $(INV) playbooks/03_paloalto_network.yml; \
	"

part2-run-all: env-check
	$(DC_ENV) exec $(SERVICE) bash -lc "\
		set -e; \
		cd $(PART2_DIR); \
		test -f playbooks/run_all.yml || (echo '❌ Missing playbook: playbooks/run_all.yml' && exit 1); \
		echo '==> Running run_all.yml'; \
		ansible-playbook -i $(INV) playbooks/run_all.yml \
	"

part2-all: env-check
	$(DC_ENV) exec $(SERVICE) bash -lc "\
		set -e; \
		cd $(PART2_DIR); \
		for f in playbooks/*.yml; do echo \"==> $$f\"; ansible-playbook -i $(INV) \"$$f\"; done \
	"

# ---------- Evidence (igual que lo venías usando, lo dejo tal cual) ----------
evidence-fgt: env-check
	$(DC_ENV) exec $(SERVICE) bash -lc "\
		set -e; \
		TS=$$(date +%Y%m%d_%H%M%S); \
		OUT=/app/part2/evidence/$$TS; mkdir -p $$OUT; \
		cd $(PART2_DIR); \
		echo '== FGT Evidence ->' $$OUT; \
		ansible -i $(INV) fortigate -m fortinet.fortios.fortios_monitor_fact -a 'vdom=root selector=vpn_ipsec' -o > $$OUT/fgt_vpn_ipsec.txt; \
		ansible -i $(INV) fortigate -m fortinet.fortios.fortios_monitor_fact -a 'vdom=root selector=router_ipv4' -o > $$OUT/fgt_router_ipv4.txt; \
		ansible -i $(INV) fortigate -m fortinet.fortios.fortios_monitor_fact -a 'vdom=root selector=system_interface' -o > $$OUT/fgt_system_interface.txt; \
		echo \"Saved: $$OUT/fgt_vpn_ipsec.txt\"; \
	"

evidence-pan: env-check
	$(DC_ENV) exec $(SERVICE) bash -lc "\
		set -e; \
		TS=$$(date +%Y%m%d_%H%M%S); \
		OUT=/app/part2/evidence/$$TS; mkdir -p $$OUT; \
		cd $(PART2_DIR); \
		echo '== PAN Evidence ->' $$OUT; \
		ansible -i $(INV) paloalto -m paloaltonetworks.panos.panos_op \
		  -a 'ip_address='\"$$PAN_HOST\"' api_key='\"$$PAN_API_KEY\"' port='\"$$PAN_HTTPS_PORT\"' cmd=\"show system info\"' -o > $$OUT/pan_show_system_info.txt; \
		ansible -i $(INV) paloalto -m paloaltonetworks.panos.panos_op \
		  -a 'ip_address='\"$$PAN_HOST\"' api_key='\"$$PAN_API_KEY\"' port='\"$$PAN_HTTPS_PORT\"' cmd=\"show vpn ike-sa\"' -o > $$OUT/pan_show_vpn_ike_sa.txt; \
		ansible -i $(INV) paloalto -m paloaltonetworks.panos.panos_op \
		  -a 'ip_address='\"$$PAN_HOST\"' api_key='\"$$PAN_API_KEY\"' port='\"$$PAN_HTTPS_PORT\"' cmd=\"show vpn ipsec-sa\"' -o > $$OUT/pan_show_vpn_ipsec_sa.txt; \
		echo \"Saved: $$OUT/pan_show_system_info.txt\"; \
	"

evidence-all: env-check
	$(DC_ENV) exec $(SERVICE) bash -lc "\
		set -e; \
		TS=$$(date +%Y%m%d_%H%M%S); \
		OUT=/app/part2/evidence/$$TS; mkdir -p $$OUT; \
		cd $(PART2_DIR); \
		echo '== Evidence ALL ->' $$OUT; \
		ansible -i $(INV) fortigate -m fortinet.fortios.fortios_monitor_fact -a 'vdom=root selector=vpn_ipsec' -o > $$OUT/fgt_vpn_ipsec.txt; \
		ansible -i $(INV) paloalto -m paloaltonetworks.panos.panos_op \
		  -a 'ip_address='\"$$PAN_HOST\"' api_key='\"$$PAN_API_KEY\"' port='\"$$PAN_HTTPS_PORT\"' cmd=\"show system info\"' -o > $$OUT/pan_show_system_info.txt; \
		echo \"Saved evidence under: $$OUT\"; \
		ls -la $$OUT; \
	"

clean:
	$(DC) down --remove-orphans
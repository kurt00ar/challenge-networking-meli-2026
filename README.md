
# MELI Technical Challenge — Parte 1 y Parte 2 (Automatización de Redes)

Este repositorio contiene mi solución al **Laboratorio de Candidatos – Networking Mercado Libre 2026**.

El objetivo general del challenge es:

> Evaluar la capacidad del candidato para desarrollar automatización de red, validaciones de configuración, planificación de VPN IPSec entre dispositivos heterogéneos y uso adecuado de control de versiones con Git.

---

# 📌 Descripción del Challenge

El challenge está dividido en dos partes:

## 🔹 Parte 1 – Automatización de Switch Cisco

- Desarrollo de script en Python
- Interfaz frontend para configuración de VLANs
- Configuración automática de:
  - VLAN 10 – VLAN_DATOS
  - VLAN 20 – VLAN_VOZ
  - VLAN 50 – VLAN_SEGURIDAD
- Cambio de hostname
- Guardado en NVRAM
- Backup automático
- Validación post-configuración
- Uso correcto de Git

---

## 🔹 Parte 2 – Automatización VPN IPSec

- Configuración de túnel IPSec entre:
  - FortiGate
  - Palo Alto
- Red de túnel: `169.255.1.0/30`
- Automatización mediante APIs
- Validación y manejo de alertas
- Documentación del plan de automatización

El enunciado completo se encuentra incluido en el repositorio.

---

# 🏗️ Arquitectura del Laboratorio

El laboratorio fue desarrollado utilizando:

- 🖥️ **GNS3-Server** para simulación realista de dispositivos
- 🐳 **Docker** para encapsular el entorno de automatización
- 🧠 Automatización ejecutándose dentro de contenedor
- 🔌 GNS3 ejecutándose en servidor externo con soporte KVM

---

## Topología del Laboratorio

![Topología Challenger](docs/img/topologia.jpg)

---

## ⚠️ Consideración Técnica (GNS3 y macOS)

No fue posible virtualizar GNS3 dentro de Docker en macOS debido a:

- Requerimiento de virtualización basada en **KVM**
- macOS no soporta KVM de forma nativa
- Docker Desktop no expone virtualización anidada compatible

Por este motivo:

- GNS3-Server fue desplegado en servidor externo con soporte KVM
- El contenedor Docker se conecta a los dispositivos del laboratorio vía red

Esta arquitectura replica un escenario real de automatización en entornos distribuidos.

---

# 🧠 Decisiones Técnicas

## 🔵 Parte 1 — Nornir + Flask

Framework utilizado:

- **Nornir**
- netmiko
- nornir_netmiko
- flask
- jinja2

Motivos:

- Modelo concurrente
- Inventario estructurado
- Integración directa con Netmiko
- Ideal para automatización L2/L3

Frontend desarrollado con Flask (UI simple, funcional y reproducible).

---

## 🟢 Parte 2 — Ansible Multi-Vendor

Framework utilizado:

- **Ansible**
- fortinet.fortios
- paloaltonetworks.panos
- ansible.netcommon

Interacción:

- API REST Palo Alto
- API FortiGate

Motivos:

- Idempotencia
- Separación clara de playbooks
- Integración nativa con APIs de seguridad
- Excelente para entornos multi-vendor

---

## 🐳 Docker Compose

Se utilizó un único contenedor que incluye:

- Python 3.10
- Nornir
- Ansible
- Dependencias necesarias
- Separación lógica:
  - `/part1`
  - `/part2`

Esto garantiza reproducibilidad total del entorno.

---

# 📂 Estructura del Repositorio

```text
.
├── docker-compose.yml
├── Makefile
├── .env
├── .env.example
├── part1/
├── part2/
├── docs/
└── scripts/


⸻

🚀 Inicio Rápido (Modo Evaluador)

1️⃣ Clonar el repositorio

git clone https://github.com/kurt00ar/challenge-networking-meli-2026.git
cd challenge-networking-meli-2026


⸻

2️⃣ Configurar variables de entorno

cp .env.example .env

Completar:
	•	PAN_HOST
	•	PAN_API_KEY
	•	PAN_WAN_IF
	•	PAN_VSYS
	•	PAN_VR
	•	FGT_HOST
	•	FGT_USER
	•	FGT_PASS
	•	VPN_PSK

⸻

3️⃣ Construir y levantar el entorno

docker compose up -d --build
docker compose ps


⸻

4️⃣ Ejecutar automatización completa

make part2-run-all


⸻

🔵 Parte 1 — Automatización L2
	•	Interfaz Web: http://localhost:5500
	•	Evidencia: part1/evidence/flask/
	•	Backups: part1/backups/

⸻

🟢 Parte 2 — VPN IPsec

Flujo de ejecución:
	1.	00_pre_backup.yml
	2.	01_fortigate_ipsec.yml
	3.	02_paloalto_ipsec.yml
	4.	03_paloalto_network.yml
	5.	04_validate.yml
	6.	06_post_backup.yml

⸻

📁 Evidencia y Backups

Evidencia:

part2/evidence/<timestamp>/

Backups:

part2/backups/fortigate/<timestamp>/
part2/backups/paloalto/<timestamp>/


⸻

🔎 Validaciones Implementadas
	•	Asociación del túnel al Virtual Router
	•	Membresía en zona VPN
	•	Políticas de firewall
	•	Rutas estáticas
	•	Conectividad validada vía playbooks

⸻

♻️ Reset Completo del Entorno

docker compose down -v --remove-orphans
docker image rm challenge-networking-meli-2026:1.0.0 2>/dev/null || true
docker builder prune -f
docker compose up -d --build


⸻

🧩 Consideraciones Finales
	•	Proyecto orientado a laboratorio
	•	Arquitectura reproducible
	•	Evidencia organizada
	•	Automatización multi-vendor
	•	Control de versiones aplicado correctamente


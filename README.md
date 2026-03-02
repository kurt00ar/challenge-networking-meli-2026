# MELI Technical Challenge — Parte 1 y Parte 2 (Automatización de Redes)

Este repositorio contiene mi solución al Challenge Técnico de Networking para MELI, dividido en:

- **Parte 1:** Automatización L2 utilizando **Flask + Nornir + Netmiko**  
  (Provisionamiento de VLANs, validaciones, backups automáticos y generación de evidencia)

- **Parte 2:** Automatización de VPN IPsec **FortiGate ↔ Palo Alto** utilizando **Ansible**  
  (Backups pre y post cambio, configuración completa, validaciones y evidencia)

> Objetivo: entregar una solución reproducible, basada en automatización, con evidencia clara y estructura profesional.

---

## 📂 Estructura del Repositorio

```text
.
├── docker-compose.yml
├── Makefile
├── .env
├── .env.example
├── part1/                 # UI Flask + Automatización L2 (Nornir)
├── part2/                 # Automatización IPsec (Ansible)
├── docs/                  # Documentación e imágenes
└── scripts/               # Scripts auxiliares


⸻

🚀 Inicio Rápido (Modo Evaluador)

1️⃣ Clonar el repositorio

git clone https://github.com/kurt00ar/challenge-networking-meli-2026.git
cd challenge-networking-meli-2026


⸻

2️⃣ Configurar variables de entorno

Copiar el archivo de ejemplo:

cp .env.example .env

Editar .env y completar:
	•	PAN_HOST, PAN_API_KEY, PAN_WAN_IF, PAN_VSYS, PAN_VR
	•	FGT_HOST, FGT_USER, FGT_PASS
	•	VPN_PSK

⸻

3️⃣ Construir y levantar el contenedor

docker compose up -d --build
docker compose ps


⸻

4️⃣ Ejecutar automatización completa

make part2-run-all


⸻

🔵 Parte 1 — Automatización L2 (Flask + Nornir)
	•	Interfaz Web: expuesta en el puerto 5500
	•	Evidencia generada en: part1/evidence/flask/*.json
	•	Backups generados en: part1/backups/*.cfg

Acceso a la UI

Abrir en navegador:

http://localhost:5500


⸻

🟢 Parte 2 — VPN IPsec FortiGate ↔ Palo Alto (Ansible)

Flujo de ejecución
	1.	00_pre_backup.yml
	2.	01_fortigate_ipsec.yml
	3.	02_paloalto_ipsec.yml
	4.	03_paloalto_network.yml
	5.	04_validate.yml
	6.	06_post_backup.yml

⸻

📁 Evidencia y Backups
	•	Evidencia:
part2/evidence/<timestamp>/...
	•	Backups FortiGate:
part2/backups/fortigate/<timestamp>/...
	•	Backups Palo Alto:
part2/backups/paloalto/<timestamp>/...

⸻

🔎 Qué debe validar el evaluador
	•	Backups pre y post cambio generados automáticamente
	•	Evidencia organizada por timestamp
	•	Validaciones exitosas en:
	•	Interfaces de túnel
	•	Virtual Router
	•	Zonas
	•	Políticas
	•	Rutas
	•	Validaciones de conectividad (según playbook)

⸻

🗺️ Topología del Laboratorio

Ver:
	•	docs/img/topologia.jpg
	•	docs/img/l2-topology.jpg

⸻

♻️ Cómo reiniciar el laboratorio desde cero

Simulación completa de entorno limpio:

docker compose down -v --remove-orphans
docker image rm challenge-networking-meli-2026:1.0.0 2>/dev/null || true
docker builder prune -f
docker compose up -d --build


⸻

🧩 Consideraciones
	•	Este repositorio está orientado a entorno de laboratorio.
	•	Las credenciales deben manejarse de forma segura.
	•	.env.example sirve como plantilla de referencia.

---

# 📘 Documento adicional

Crear archivo:

docs/part2/runbook.md

Contenido:

```markdown
# Parte 2 — Runbook Operativo (FGT ↔ PAN IPsec)

## Requisitos

- Palo Alto accesible vía API (PAN_HOST / PAN_API_KEY)
- FortiGate accesible vía HTTP/HTTPS
- Archivo `.env` correctamente configurado

---

## Ejecución

```bash
docker compose up -d --build
make part2-run-all


⸻

Resultado Esperado
	•	Backups pre y post cambio generados automáticamente
	•	Evidencia organizada en carpetas por timestamp
	•	Validaciones exitosas

⸻

Troubleshooting

Si falla API de Palo Alto:
	•	Verificar PAN_HOST
	•	Verificar PAN_API_KEY
	•	Confirmar acceso API habilitado en management

Si falla el commit:
	•	Validar que tunnel.10 esté en el Virtual Router
	•	Verificar membresía en zona VPN
	•	Confirmar políticas y rutas


![Docker](https://img.shields.io/badge/docker-compose-blue)
![Python](https://img.shields.io/badge/python-3.10-blue)
![Automation](https://img.shields.io/badge/network-automation-success)
![Status](https://img.shields.io/badge/status-lab%20ready-brightgreen)

# MELI Technical Challenge — Parte 1 y Parte 2 (Automatización de Redes)

Este repositorio contiene mi solución al **Laboratorio de Candidatos – Networking Mercado Libre 2026**.

## 🎯 Objetivo del Challenge

Evaluar la capacidad del candidato para:

- Desarrollar automatización de red multi-vendor
- Implementar validaciones post-configuración
- Diseñar túneles VPN IPsec entre plataformas heterogéneas
- Aplicar control de versiones con Git
- Entregar evidencia estructurada y reproducible

---

# 🧩 Descripción del Challenge

El challenge está dividido en dos partes:

## 🔵 Parte 1 — Automatización L2 (Switch Cisco)

- Automatización en **Python**
- Interfaz web en **Flask**
- Uso de **Nornir + Netmiko**
- Creación automática de VLANs:
  - VLAN 10 — VLAN_DATOS
  - VLAN 20 — VLAN_VOZ
  - VLAN 50 — VLAN_SEGURIDAD
- Cambio de hostname
- Guardado en NVRAM
- Backups automáticos (pre/post)
- Validación post-configuración
- Evidencia JSON por ejecución (timestamp)

---

## 🟢 Parte 2 — Automatización VPN IPsec (FortiGate ↔ Palo Alto)

- Túnel IPsec entre:
  - FortiGate (Argentina)
  - Palo Alto (Brasil)
- Red de túnel: `169.255.1.0/30`
- Automatización mediante **Ansible + APIs**
- Validaciones técnicas automatizadas
- Backups pre y post cambio
- Evidencia estructurada por timestamp

---

# 🏗️ Arquitectura del Laboratorio (GNS3 + Docker)

El laboratorio fue desarrollado utilizando:

- **GNS3-Server** para simulación realista de dispositivos de red
- **Docker Compose** para encapsular el entorno de automatización
- Automatización ejecutándose dentro de un contenedor reproducible
- GNS3 desplegado en servidor externo con soporte KVM

## 🗺️ Topología del Laboratorio

![Topología Challenger](docs/img/topologia.jpg)

---

# ⚠️ Consideración Técnica (GNS3 y macOS)

No fue posible virtualizar GNS3 dentro de Docker en macOS debido a:

- Requerimiento de virtualización basada en **KVM**
- macOS no soporta KVM de forma nativa
- Docker Desktop no expone virtualización anidada compatible

Por este motivo:

- **GNS3-Server fue desplegado en un servidor externo con soporte KVM**
- El contenedor Docker interactúa vía red con los dispositivos del laboratorio
- Se mantiene un modelo de automatización distribuida realista

---

# 🌎 Diseño del Laboratorio — Modelo Multisede

El laboratorio simula una empresa multinacional con dos sedes interconectadas:

- 🇦🇷 Argentina
- 🇧🇷 Brasil

Este enfoque representa un entorno real enterprise acorde a compañías globales como Mercado Libre.

---

## 📊 Tabla de direccionamiento

| Sede | WAN (/30) | VLAN 10 DATOS | VLAN 20 VOZ | VLAN 50 SEGURIDAD | Host Test |
|------|-----------|---------------|-------------|-------------------|----------|
| 🇦🇷 Argentina | `201.254.16.0/30` (TASA) | `10.10.10.0/24` | `10.10.20.0/24` | `10.10.50.0/24` | `10.10.10.10` |
| 🇧🇷 Brasil | `200.169.116.0/30` (CLARO) | `10.20.10.0/24` | `10.20.20.0/24` | `10.20.50.0/24` | `10.20.10.10` |

## 🔐 VPN IPsec (Túnel)

- Red de túnel: `169.255.1.0/30`
- `.1` → FortiGate (Argentina)
- `.2` → Palo Alto (Brasil)

---

# 🧠 Design Decisions

- Separación clara entre automatización L2 (Nornir) y seguridad multi-vendor (Ansible)
- Uso de Docker para garantizar reproducibilidad
- GNS3 externo con KVM para compatibilidad con appliances virtuales
- Modelo multisede para simular entorno enterprise real
- Generación obligatoria de backups pre y post cambio
- Evidencia estructurada por timestamp
- Validaciones técnicas automatizadas post-configuración

---

# 🧰 Tech Stack

## Parte 1
- Python 3.10
- Nornir
- Netmiko
- Flask
- Jinja2

## Parte 2
- Ansible
- `fortinet.fortios`
- `paloaltonetworks.panos`
- `ansible.netcommon`
- API REST FortiGate
- API REST Palo Alto

## Packaging
- Docker
- Docker Compose
- Makefile

---

# 🔐 Consideración de Seguridad — Propuestas IPsec

Durante la implementación se utilizaron propuestas compatibles con ambos dispositivos debido a limitaciones del entorno de laboratorio y licenciamiento de appliances virtuales.

En producción se recomienda:

- AES-256
- SHA-256 o superior
- DH Group 14 o superior
- IKEv2

El uso de algoritmos más débiles en este laboratorio responde exclusivamente a restricciones del entorno de prueba.

---

# 🏢 Escalabilidad y Gestión Centralizada

Si el entorno creciera:

- **Palo Alto:** implementar **Panorama**
- **Fortinet:** implementar **FortiManager**

Beneficios:
- Gestión centralizada
- Versionado de políticas
- Control de cambios
- Rollback seguro
- Visibilidad global

---

# 📂 Estructura del Repositorio

```text
.
├── docker-compose.yml
├── Makefile
├── .env
├── .env.example
├── part1/                 # Flask UI + Nornir
├── part2/                 # Ansible automation
├── docs/
│   └── img/
│       ├── topologia.jpg
│       ├── Part1-VLANs.jpg
│       └── Part1-Results.jpg
└── scripts/

```
---

# 🚀 Inicio Rápido (Modo Evaluador)

1️⃣ Clonar el repositorio

git clone https://github.com/kurt00ar/challenge-networking-meli-2026.git
cd challenge-networking-meli-2026

2️⃣ Configurar variables de entorno

cp .env.example .env

Editar .env y completar:
	•	PAN_HOST
	•	PAN_API_KEY
	•	PAN_WAN_IF
	•	PAN_VSYS
	•	PAN_VR
	•	FGT_HOST
	•	FGT_USER
	•	FGT_PASS
	•	VPN_PSK

3️⃣ Levantar el entorno

docker compose up -d --build
docker compose ps

4️⃣ Ejecutar automatización completa

make part2-run-all

---

# 🔵 Parte 1 — Automatización L2

La Parte 1 automatiza switches Cisco usando Nornir + Netmiko y expone una UI en Flask.

### 📸 Interfaz Web (Configuración VLANs y Hostnames)
![Part1 VLANs](docs/img/Part1-VLANs.jpg)

### 📸 Resultados y Evidencia Generada
![Part1 Results](docs/img/Part1-Results.jpg)

Outputs generados
	•	Evidencia: part1/evidence/flask/
	•	Backups: part1/backups/

---

# 🟢 Parte 2 — VPN IPsec

Flujo de playbooks
	1.	00_pre_backup.yml
	2.	01_fortigate_ipsec.yml
	3.	02_paloalto_ipsec.yml
	4.	03_paloalto_network.yml
	5.	04_validate.yml
	6.	06_post_backup.yml

Outputs generados
	•	Evidencia: part2/evidence/<timestamp>/
	•	Backups FortiGate: part2/backups/fortigate/<timestamp>/
	•	Backups Palo Alto: part2/backups/paloalto/<timestamp>/

Validaciones implementadas
	•	Asociación del túnel al Virtual Router
	•	Membresía en zona VPN
	•	Políticas de firewall
	•	Rutas estáticas
	•	Conectividad validada automáticamente

  ---

# ♻️ Reset completo del entorno

docker compose down -v --remove-orphans
docker image rm challenge-networking-meli-2026:1.0.0 2>/dev/null || true
docker builder prune -f
docker compose up -d --build

---

# 🎥 Evidencia adicional

https://youtu.be/3aqSMiEkk2w 
Video mostrando:
	1.	Arquitectura (GNS3 + Docker)
	2.	Ejecución Parte 1
	3.	Ejecución Parte 2
	4.	Evidencia por timestamp
	5.	Historial de commits

---

# 📌 Notas Finales

Este laboratorio fue diseñado para:
	•	Demostrar automatización multi-vendor real
	•	Aplicar infraestructura reproducible
	•	Implementar validaciones post-cambio
	•	Generar evidencia trazable
	•	Simular un entorno enterprise realista

Todo el código fue versionado utilizando Git siguiendo buenas prácticas de control de cambios.

---

```md
# 📌 Parte 2 — Plan de Automatización: `docs/parte2_plan_automatizacion_vpn_ipsec.md`
# 📌 Parte 2 — Plan Enterprise Automatización: `docs/part2_Enterprise_Automation_Plan.md` 

```

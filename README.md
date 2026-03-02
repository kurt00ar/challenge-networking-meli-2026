
![Docker](https://img.shields.io/badge/docker-compose-blue)
![Python](https://img.shields.io/badge/python-3.10-blue)
![Automation](https://img.shields.io/badge/network-automation-success)
![Status](https://img.shields.io/badge/status-lab%20ready-brightgreen)

# MELI Technical Challenge — Parte 1 y Parte 2 (Automatización de Redes)

Este repositorio contiene mi solución al **Laboratorio de Candidatos – Networking Mercado Libre 2026**.

**Objetivo del challenge:**
> Evaluar la capacidad del candidato para desarrollar automatización de red, validaciones de configuración, planificación de VPN IPSec entre dispositivos heterogéneos y uso adecuado de control de versiones con Git.

---

## 🧩 Descripción del Challenge

El challenge está dividido en dos partes:

### Parte 1 — Automatización L2 (Switch Cisco)
- Automatización en **Python**
- Interfaz web (Flask) para definir **VLANs** y **hostnames**
- Creación automática de VLANs:
  - VLAN 10 — VLAN_DATOS
  - VLAN 20 — VLAN_VOZ
  - VLAN 50 — VLAN_SEGURIDAD
- Cambio de hostname
- Guardado en NVRAM
- Backups automáticos (pre/post)
- Validación post-configuración
- Evidencia por corrida (timestamp)

### Parte 2 — Automatización VPN IPsec (FortiGate ↔ Palo Alto)
- Túnel IPsec entre:
  - FortiGate (Argentina)
  - Palo Alto (Brasil)
- Red de túnel: `169.255.1.0/30`
- Automatización mediante **Ansible + APIs**
- Validaciones + evidencia
- Backups pre y post cambio

El enunciado completo se encuentra incluido en el repositorio.

---

## 🏗️ Arquitectura del Laboratorio (GNS3 + Docker)

El laboratorio fue desarrollado utilizando:

- **GNS3-Server** para simulación realista de dispositivos de red
- **Docker Compose** para encapsular el entorno de automatización
- Automatización ejecutándose dentro de un contenedor reproducible
- GNS3 ejecutándose en un servidor externo con soporte KVM

### Topología del Laboratorio

![Topología Challenger](docs/img/topologia.jpg)

---

## ⚠️ Consideración Técnica (GNS3 y macOS)

No fue posible virtualizar GNS3 dentro de Docker en macOS debido a:

- Requerimiento de virtualización basada en **KVM**
- macOS no soporta KVM de forma nativa
- Docker Desktop en macOS no expone virtualización anidada compatible

Por este motivo:
- **GNS3-Server fue desplegado en un servidor externo con soporte KVM**
- El contenedor Docker se conecta a los dispositivos del laboratorio vía red (automatización distribuida realista)

---

## 🌎 Diseño del Laboratorio — Modelo Multisede

El laboratorio fue diseñado simulando un escenario real de empresa multinacional con dos sucursales interconectadas mediante VPN IPsec:

- 🇦🇷 Argentina
- 🇧🇷 Brasil

Esto busca representar un entorno acorde a una empresa global como Mercado Libre.

### Tabla de direccionamiento

| Sede | WAN (/30) | VLAN 10 DATOS | VLAN 20 VOZ | VLAN 50 SEGURIDAD | Host Test |
|------|-----------|---------------|-------------|-------------------|----------|
| 🇦🇷 Argentina | `201.254.16.0/30` (TASA) | `10.10.10.0/24` | `10.10.20.0/24` | `10.10.50.0/24` | `10.10.10.10` |
| 🇧🇷 Brasil | `200.169.116.0/30` (CLARO) | `10.20.10.0/24` | `10.20.20.0/24` | `10.20.50.0/24` | `10.20.10.10` |

### VPN IPsec (túnel)
- Red de túnel: `169.255.1.0/30`
- `.1` → FortiGate (Argentina)
- `.2` → Palo Alto (Brasil)

---

## 🧰 Tech Stack

**Parte 1 (Nornir + Flask)**
- Nornir
- Netmiko / nornir_netmiko
- Flask + Jinja2
- Python 3.10

**Parte 2 (Ansible Multi-Vendor)**
- Ansible
- `fortinet.fortios`
- `paloaltonetworks.panos`
- `ansible.netcommon`
- APIs: FortiGate / Palo Alto

**Packaging**
- Docker + Docker Compose
- Makefile (run end-to-end)

---

## 🔐 Consideración de Seguridad — Propuestas IPSec

Durante la implementación del laboratorio se utilizaron propuestas compatibles con ambos dispositivos **debido a limitaciones del entorno/lab y licenciamiento de appliances virtuales**.

En un entorno productivo se recomienda:
- AES-256
- SHA-256 o superior
- DH Group 14 o superior
- IKEv2

El uso de algoritmos más débiles en este laboratorio responde exclusivamente a restricciones del entorno de prueba.

---

## 🏢 Escalabilidad y Gestión Centralizada (Recomendación)

Si este entorno creciera a múltiples dispositivos por sede:

- **Palo Alto**: recomendar **Panorama** (gestión centralizada, templates, rollback, visibilidad global).
- **Fortinet**: recomendar **FortiManager** (ADOMs, control central de políticas, cambios masivos, versionado).

---

## 📂 Estructura del Repositorio

```text
.
├── docker-compose.yml
├── Makefile
├── .env
├── .env.example
├── part1/                 # Flask UI + Nornir/Netmiko
├── part2/                 # Ansible (FortiGate ↔ Palo Alto)
├── docs/                  # Documentación e imágenes
└── scripts/               # Scripts auxiliares

```
---

🚀 Inicio Rápido (Modo Evaluador)

1) Clonar el repositorio

git clone https://github.com/kurt00ar/challenge-networking-meli-2026.git
cd challenge-networking-meli-2026

2) Configurar variables de entorno

cp .env.example .env

Completar en .env:
      •     PAN_HOST, PAN_API_KEY, PAN_WAN_IF, PAN_VSYS, PAN_VR
      •     FGT_HOST, FGT_USER, FGT_PASS
      •     VPN_PSK

3) Construir y levantar el entorno

docker compose up -d --build
docker compose ps

4) Ejecutar automatización completa

make part2-run-all


---

🔵 Parte 1 — Automatización L2 (VLANs + Hostname)

La Parte 1 automatiza switches Cisco usando Nornir + Netmiko y expone una UI en Flask para definir hostnames y VLANs.

Funcionalidades:
      •     Creación automática de VLANs
      •     Cambio de hostname
      •     Guardado en NVRAM
      •     Backup pre/post
      •     Validación automática
      •     Evidencia JSON por ejecución

### Interfaz Web (Configuración VLANs y Hostnames)
![Part1 VLANs](docs/img/Part1-VLANs.jpg)

### Resultados y Evidencia Generada
![Part1 Results](docs/img/Part1-Results.jpg)

Outputs:
      •     Evidencia: part1/evidence/flask/
      •     Backups: part1/backups/

---

🟢 Parte 2 — VPN IPsec (FortiGate ↔ Palo Alto)

Flujo de playbooks:
      1.    00_pre_backup.yml
      2.    01_fortigate_ipsec.yml
      3.    02_paloalto_ipsec.yml
      4.    03_paloalto_network.yml
      5.    04_validate.yml
      6.    06_post_backup.yml

Outputs:
      •     Evidencia: part2/evidence/<timestamp>/
      •     Backups FortiGate: part2/backups/fortigate/<timestamp>/
      •     Backups Palo Alto: part2/backups/paloalto/<timestamp>/

Validaciones implementadas:
      •     Túnel asociado a Virtual Router
      •     Membresía en zona VPN
      •     Políticas de firewall
      •     Rutas estáticas
      •     Conectividad validada vía playbooks

---

♻️ Reset completo del entorno

docker compose down -v --remove-orphans
docker image rm challenge-networking-meli-2026:1.0.0 2>/dev/null || true
docker builder prune -f
docker compose up -d --build


---

🎥 Evidencia adicional (video)

Se recomienda un video corto (7–10 min) mostrando:
      1.    Arquitectura (GNS3 + Docker)
      2.    Ejecución Parte 1 (UI + evidencia)
      3.    Ejecución Parte 2 (Ansible + backups + validaciones)
      4.    Evidencia por timestamp + historial de commits

Si se requiere acceso al laboratorio para validación técnica, puedo generar accesos VPN temporales bajo solicitud.

---

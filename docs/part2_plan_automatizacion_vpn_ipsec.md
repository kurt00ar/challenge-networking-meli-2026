
# Parte 2 — Plan de Automatización (VPN IPsec FortiGate ↔ Palo Alto)

## 1. Objetivo

Automatizar el aprovisionamiento y validación de una **VPN IPsec Site-to-Site** entre un **FortiGate** y un **Palo Alto** utilizando **Ansible** (y módulos/API oficiales), asegurando:

- Configuración consistente (determinística).
- **Backups completos** pre y post cambio en ambos equipos.
- **Commit** en Palo Alto.
- Evidencia en JSON + outputs de validación por corrida (timestamp).
- Capacidad de reproducir la ejecución desde contenedor Docker.

---

## 2. Alcance

Incluye:

1) Recolección de información y backups previos (pre-change).  
2) Configuración automatizada de:
   - Parametrización IKE/IPsec (Phase 1 / Phase 2).
   - Interfaz/túnel, rutas y políticas (según modelo/routing del lab).
   - NAT/policies si aplica al escenario.
3) Commit y verificación en Palo Alto.
4) Verificación y backups posteriores (post-change).
5) Generación de evidencia en archivos (timestamp).

No incluye (fuera de alcance):
- Publicación de un lab completo para el evaluador (GNS3 appliances).  
- Integración con PKI/certificados para IKE (se usa PSK en lab).
- Alta disponibilidad (HA) o BGP dinámico (si se requiere, es extensible).

---

## 3. Parámetros de implementación (Lab)

### 3.1 Túnel /30 provisto por el enunciado

- **Subnet del Tunnel IPsec:** `169.255.1.0/30`
- **FortiGate (tunnel IP):** `169.255.1.1/30`
- **Palo Alto (tunnel IP):** `169.255.1.2/30`

> Esta subred se usa para direccionamiento del túnel (tipo route-based), y facilita ruteo/validación.

### 3.2 IKE / IPsec (Phase 1 y Phase 2)

#### IKE
- **Versión:** IKEv2
- **Autenticación:** PSK (lab)
- **Proposal (P1) / Cifrados:** **DES**
- **Integrity/Hash:** **SHA-256**
- **DH Group:** (según soporte del lab; documentado en variables/inventory)
- **DPD:** habilitado

> Nota importante: el FortiGate del lab soporta IKEv2 pero está limitado a proposals con **DES** y hashes como `md5/sha1/sha256/sha384/sha512`.  
> Se selecciona **DES-SHA256** para compatibilidad.

#### IPsec / ESP (Phase 2)
- **Transform/Proposal:** DES + SHA-256 (o el equivalente compatible)
- **PFS:** (según soporte del lab; parametrizado)
- **Selectors:** (según si se usa policy-based o route-based; en este plan se asume route-based por el uso del /30)

### 3.3 Redes LAN/WAN (referenciales)

Este documento asume que las redes reales y peers se definen vía variables:

- **WAN FortiGate:** IP/Interface parametrizada en `group_vars` / `.env`
- **WAN Palo Alto:** IP/Interface parametrizada
- **Peer IP pública:** parametrizada (IP del peer remoto)
- **LANs protegidas:** listas parametrizadas (local_subnets / remote_subnets)

> El objetivo es que el evaluador vea claramente *qué* se configura, y que el código lo lea de un único lugar (variables).

---

## 4. Herramientas / Tecnologías / APIs utilizadas

- **Docker / Docker Compose**: ejecución reproducible del stack.
- **Ansible**:
  - FortiGate: colección `fortinet.fortios`
  - Palo Alto: colección `paloaltonetworks.panos`
  - Plugins base: `ansible.netcommon`
- **API Palo Alto**:
  - Autenticación por `api_key` (keygen)
  - Operaciones: `show system info`, commit, configuración de IKE/IPsec/tunnel/policies
- **FortiGate**:
  - Automatización vía módulos FortiOS (colección)
  - Extracción de config para backups y verificación

---

## 5. Estructura de repo (Parte 2)

Ruta principal:

- `part2/ansible_app/`
  - `playbooks/`
    - `00_pre_backup.yml`
    - `01_plan_check.yml`
    - `02_config_fortigate.yml`
    - `03_config_paloalto.yml`
    - `04_commit_paloalto.yml`
    - `05_validate.yml`
    - `06_post_backup.yml`
    - `run_all.yml`
  - `inventories/lab/`
    - `hosts.yml`
    - `group_vars/`
      - `all.yml`
      - `fortigate.yml`
      - `paloalto.yml`
  - `evidence/` (generado)
  - `backups/` (generado)

Outputs generados:

- **Backups:** `part2/backups/<timestamp>/...`
- **Evidencia:** `part2/evidence/<timestamp>/...`

---

## 6. Flujo lógico (pasos del plan)

### Paso 0 — Pre-Backup (FortiGate + Palo Alto)
Objetivo: capturar estado previo antes de aplicar cambios.

- FortiGate: backup de configuración completa
- Palo Alto: export/backup (o snapshot) + output de comandos relevantes

**Salida esperada:**
- Carpeta `part2/backups/<timestamp>/pre/...`
- Evidencia `part2/evidence/<timestamp>/pre_checks.json`

---

### Paso 1 — Plan & Pre-checks
Objetivo: validar conectividad y precondiciones.

Validaciones mínimas:
- reachability (ping/https/api) al Palo Alto
- reachability (https/ssh/api) al FortiGate
- validación de variables (que exista peer IP, PSK, proposals, etc.)
- “dry validations” (que no haya naming conflicts)

**Si falla algo:**
- Se corta la ejecución (fail-fast).
- Se registra evidencia con detalle del error.

---

### Paso 2 — Config FortiGate
Objetivo: aprovisionar Phase1/Phase2, túnel, rutas/policies.

Acciones típicas:
- crear `vpn ipsec phase1-interface` (IKEv2 + DES-SHA256 + DPD)
- crear `vpn ipsec phase2-interface` (DES-SHA256 + PFS si corresponde)
- crear interface de túnel y asignar `169.255.1.1/30`
- rutas estáticas o políticas según topología (parametrizado)
- reglas de firewall (permitir tráfico LAN ↔ LAN remoto)

---

### Paso 3 — Config Palo Alto
Objetivo: crear IKE Gateway, IPsec Tunnel, Tunnel Interface y rutas/policies.

Acciones típicas:
- IKE Crypto Profile (DES + SHA-256)
- IKE Gateway (peer, auth PSK, IKEv2)
- IPsec Crypto Profile (DES + SHA-256)
- IPsec Tunnel (vinculado al gateway)
- Tunnel Interface con `169.255.1.2/30`
- Virtual Router: rutas a subnets remotas
- Security Policies: permitir tráfico de subnets
- NAT policy si aplica (opcional/parametrizado)

---

### Paso 4 — Commit Palo Alto
Objetivo: asegurar que los cambios queden aplicados en running config.

- Commit obligatorio.
- Evidencia del commit (éxito/fracaso + message).

---

### Paso 5 — Validación funcional (post-change)
Objetivo: confirmar que la VPN levanta y que hay paso de tráfico.

Checks recomendados:
- FortiGate:
  - estado del túnel / SA up
  - contadores tx/rx (si hay tráfico)
  - rutas correctas hacia redes remotas
- Palo Alto:
  - `show vpn ike-sa` / `show vpn ipsec-sa` (según comandos disponibles)
  - contadores y estado
  - rutas instaladas en VR

Prueba de conectividad (si hay hosts/loopbacks):
- ping desde un extremo hacia una IP del otro lado (o loopback de lab)
- opcional: traceroute

**Salida esperada:**
- Evidencia JSON: `part2/evidence/<timestamp>/validate.json`
- Consola: resumen de estado y hallazgos

---

### Paso 6 — Post-Backup (FortiGate + Palo Alto)
Objetivo: guardar el estado final para auditoría y comparación.

- FortiGate: backup full post-change
- Palo Alto: export config / snapshot post-change

**Salida esperada:**
- `part2/backups/<timestamp>/post/...`
- Evidencia: `part2/evidence/<timestamp>/post_checks.json`

---

## 7. Consideraciones de seguridad / hardening

1) **Secretos y credenciales**
- PSK y API keys deben manejarse por variables/secret injection (idealmente `.env.local` excluido del repo).
- En entorno de evaluación, se pueden usar credenciales dummy.

2) **Principio de mínimo privilegio**
- Usuario API en Palo Alto con permisos limitados a networking/vpn (si el lab lo permite).
- FortiGate con cuenta de automatización con perfil restringido.

3) **Trazabilidad**
- Backups pre/post y evidencia por corrida con timestamp.
- Logs legibles para auditoría.

4) **Idempotencia**
- Los playbooks están diseñados para evitar duplicar objetos (nombres determinísticos).
- Si un objeto existe, se actualiza en lugar de recrearse (según módulos).

---

## 8. Validación / Alertas / Criterios de éxito

### Criterios de éxito (OK)
- La ejecución completa finaliza sin errores.
- Se generan:
  - `backups/<timestamp>/pre` y `backups/<timestamp>/post`
  - `evidence/<timestamp>/...` con resultados de checks
- La VPN queda:
  - IKE SA UP
  - IPsec SA UP
  - Rutas presentes
  - Paso de tráfico validado (si hay endpoints)

### Alertas (WARN / FAIL)
- **WARN**
  - SA UP pero sin tráfico (posible falta de rutas o endpoints de prueba)
  - Proposals negociadas distintas a las esperadas (registrar)
- **FAIL**
  - No reachability a algún equipo (API/SSH)
  - Commit falla en Palo Alto
  - SA DOWN luego de aplicar config
  - Variables incompletas o inconsistentes

---

## 9. Cómo ejecutar (desde Docker)

### Opción A — Ejecutar TODO (run_all)
Dentro del contenedor (o desde `docker compose exec`):

```bash
cd /app/part2/ansible_app
ansible-playbook -i inventories/lab/hosts.yml playbooks/run_all.yml
```
### Opción B — Ejecutar por etapas

```bash
ansible-playbook -i inventories/lab/hosts.yml playbooks/00_pre_backup.yml
ansible-playbook -i inventories/lab/hosts.yml playbooks/01_plan_check.yml
ansible-playbook -i inventories/lab/hosts.yml playbooks/02_config_fortigate.yml
ansible-playbook -i inventories/lab/hosts.yml playbooks/03_config_paloalto.yml
ansible-playbook -i inventories/lab/hosts.yml playbooks/04_commit_paloalto.yml
ansible-playbook -i inventories/lab/hosts.yml playbooks/05_validate.yml
ansible-playbook -i inventories/lab/hosts.yml playbooks/06_post_backup.yml
```

---

## 10. Evidencia entregable

Cada corrida genera evidencia y backups con timestamp:
	•	part2/backups/<timestamp>/pre/
	•	part2/backups/<timestamp>/post/
	•	part2/evidence/<timestamp>/

Esto permite al evaluador:
	•	auditar qué se tocó,
	•	comparar pre vs post,
	•	validar que el proceso es repetible.

⸻

## 11. Notas finales

Este plan prioriza compatibilidad y reproducibilidad.
Si el lab dispone de cifrados modernos, se recomienda migrar DES → AES (por seguridad).
En este challenge se usa DES-SHA256 exclusivamente por limitaciones del FortiGate del lab.

---
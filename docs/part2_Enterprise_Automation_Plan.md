# Parte 2 — Enterprise Automation Plan
## IPsec VPN Deployment — FortiGate ↔ Palo Alto

---

# Executive Summary

This document defines the automated deployment, validation and audit workflow for a Site-to-Site IPsec VPN between a FortiGate and a Palo Alto firewall.

The objective is to ensure:

- Deterministic configuration
- Reproducibility via Docker
- Full audit traceability (pre/post backups)
- Automated validation
- Infrastructure-as-Code compliance

This implementation was developed as part of the MELI Networking Technical Challenge 2026.

---

# Architecture Overview

Tunnel subnet:

169.255.1.0/30

| Device       | Tunnel IP        |
|-------------|-----------------|
| FortiGate   | 169.255.1.1     |
| Palo Alto   | 169.255.1.2/30  |

Protected networks:

| FortiGate LAN | Palo Alto LAN |
|--------------|--------------|
| 10.10.10.0/24 | 10.20.10.0/24 |

Encryption profile:

- IKEv2
- DES-SHA256
- DH Group 2
- DPD enabled

Note: DES is used strictly due to lab hardware limitations.

---

# Design Principles

1. Idempotent automation
2. Full configuration backup before and after changes
3. Fail-fast validation model
4. API-based interaction (no screen scraping)
5. Deterministic naming conventions
6. Infrastructure as Code (Ansible)

---

# Automation Workflow

## Phase 1 — Pre-Change Audit

- FortiGate full configuration backup
- Palo Alto running configuration export
- Baseline validation
- API connectivity verification

Output:
part2/backups/<timestamp>/pre/

---

## Phase 2 — FortiGate Deployment

Automated configuration:

- Phase1 interface (IKEv2)
- Phase2 selectors
- Tunnel interface
- Static route
- Firewall policies

Verification:
- VPN object presence
- Route installed
- Policy existence

---

## Phase 3 — Palo Alto Deployment

Automated configuration:

- IKE Crypto Profile
- IPsec Crypto Profile
- IKE Gateway
- IPsec Tunnel
- Tunnel interface
- Virtual Router route
- Security policies

Commit operation executed programmatically.

---

## Phase 4 — Post-Change Validation

FortiGate:
- IPsec SA status
- Route validation
- Traffic counters

Palo Alto:
- IKE SA status
- IPsec SA status
- Routing table verification

Expected Result:
- SA UP (IKE + IPsec)
- Bidirectional policy match
- Route installation

---

## Phase 5 — Post-Change Backup

- Full backup on both devices
- Stored under:
  part2/backups/<timestamp>/post/

---

# Risk Considerations

- DES is cryptographically weak (lab constraint)
- PSK stored externally (not in repository)
- Change window recommended for production use
- Configuration rollback available via pre-backup

---

# Security Considerations

- API key authentication (Palo Alto)
- Restricted automation account (recommended)
- Logging enabled on policies
- No credentials stored in plain text

---

# Execution

From Docker container:

cd /app/part2/ansible_app
ansible-playbook -i inventories/lab/hosts.yml playbooks/run_all.yml

---

# Deliverables Generated

- Pre-change backup
- Post-change backup
- Validation logs
- Timestamped evidence
- Deterministic configuration deployment

---

# Production Recommendation

In real environments replace DES with:

AES256-SHA256 + DH Group 14+

Enable:
- Replay protection
- PFS
- Strict policy objects
- Zone-based segmentation
# Parte 2 — VPN IPsec Parameters Reference

This document centralizes all deployment variables used in automation.

---

# 1. Tunnel Subnet

| Parameter | Value |
|-----------|-------|
| Tunnel Network | 169.255.1.0/30 |
| FortiGate Tunnel IP | 169.255.1.1 |
| Palo Alto Tunnel IP | 169.255.1.2 |

---

# 2. FortiGate Configuration

## Phase 1

| Parameter | Value |
|-----------|-------|
| Name | VPN_MELI_CHAL |
| Interface | port3 |
| IKE Version | 2 |
| Remote Gateway | 200.169.116.2 |
| Proposal | des-sha256 |
| DH Group | 2 |
| DPD | on-idle |
| Authentication | PSK |

## Phase 2

| Parameter | Value |
|-----------|-------|
| Name | VPN_MELI_CHAL_P2 |
| Proposal | des-sha256 |
| Local Subnet | 10.10.10.0/24 |
| Remote Subnet | 10.20.10.0/24 |
| DH Group | 2 |

## Routing

| Destination | Device |
|-------------|--------|
| 10.20.10.0/24 | VPN_MELI_CHAL |

## Policies

| Rule Name | Source | Destination | Action |
|-----------|--------|------------|--------|
| LAN_to_VPN_MELI | LAN_ZONE | VPN_MELI_CHAL | Accept |
| VPN_to_LAN_MELI | VPN_MELI_CHAL | LAN_ZONE | Accept |

---

# 3. Palo Alto Configuration

## IKE Crypto Profile

| Parameter | Value |
|-----------|-------|
| Name | VPN_MELI_CHALLENGE-IKE-CRYPTO |
| Encryption | des |
| Hash | sha256 |
| DH | group2 |
| Lifetime | 28800 |

## IPsec Crypto Profile

| Parameter | Value |
|-----------|-------|
| Name | VPN_MELI_CHALLENGE-IPSEC-CRYPTO |
| ESP Encryption | des |
| ESP Authentication | sha256 |
| PFS | group2 |
| Lifetime | 3600 |

## Logical Objects

| Object | Name |
|--------|------|
| IKE Gateway | VPN_MELI_CHALLENGE-IKEGW |
| IPsec Tunnel | VPN_MELI_CHALLENGE-IPSEC |

---

# 4. Automation Execution

| Component | Technology |
|-----------|-----------|
| Orchestration | Ansible |
| FortiGate API | fortinet.fortios |
| Palo Alto API | paloaltonetworks.panos |
| Runtime | Docker |

---

# 5. Evidence Paths

| Type | Path |
|------|------|
| Pre Backup | part2/backups/<timestamp>/pre |
| Post Backup | part2/backups/<timestamp>/post |
| Validation Logs | part2/evidence/<timestamp> |
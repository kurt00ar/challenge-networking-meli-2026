# -----------------------------------------------------------------------------
# Challenge Networking MELI 2026
# Image única (Part1 + Part2 tools):
# - Python 3.10 (slim)
# - Nornir + Netmiko + Napalm
# - Ansible Core + collections (Fortinet + Palo Alto + netcommon + community.general)
# - PAN-OS SDK (pan-os-python) + xmltodict
# -----------------------------------------------------------------------------

FROM python:3.10.19-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_RUN_PORT=5000

# Mantengo la convención del compose: trabajo en /app/part1
WORKDIR /app/part1

# -----------------------------------------------------------------------------
# System packages
# -----------------------------------------------------------------------------
RUN apt-get update \
    && apt-get -y upgrade \
    && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    git \
    openssh-client \
    build-essential \
    libffi-dev \
    libssl-dev \
    iproute2 \
    iputils-ping \
    netcat-openbsd \
    dnsutils \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# -----------------------------------------------------------------------------
# Python dependencies (reproducible)
# -----------------------------------------------------------------------------
RUN pip install --upgrade pip

COPY requirements.txt /app/part1/requirements.txt
RUN pip install --no-cache-dir -r /app/part1/requirements.txt

# -----------------------------------------------------------------------------
# Ansible collections (instaladas en path global, no en HOME)
# -----------------------------------------------------------------------------
RUN mkdir -p /usr/share/ansible/collections \
    && ansible-galaxy collection install -p /usr/share/ansible/collections \
    ansible.netcommon \
    ansible.utils \
    community.general \
    fortinet.fortios \
    paloaltonetworks.panos

# -----------------------------------------------------------------------------
# Create non-root user
# -----------------------------------------------------------------------------
RUN useradd -m -u 1000 appuser
ENV HOME=/home/appuser

# -----------------------------------------------------------------------------
# SSH legacy compatibility for IOSvL2 (GNS3 lab)
# -----------------------------------------------------------------------------
RUN mkdir -p /home/appuser/.ssh \
    && chmod 700 /home/appuser/.ssh

COPY --chown=appuser:appuser configs/ssh_config /home/appuser/.ssh/config
RUN chmod 600 /home/appuser/.ssh/config

# -----------------------------------------------------------------------------
# Copy Part1 code (build context = ./part1)
# -----------------------------------------------------------------------------
COPY --chown=appuser:appuser . /app/part1

USER appuser

EXPOSE 5000

# -----------------------------------------------------------------------------
# Start Flask app (Part1)
# -----------------------------------------------------------------------------
CMD ["python", "-m", "flask", "--app", "frontend/app.py", "run", "--host=0.0.0.0", "--port=5000"]
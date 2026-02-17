+++
title = "systemd Deployment"
weight = 3
+++

systemd is the recommended deployment method for production Zentinel installations on Linux. It provides robust process supervision, socket activation, resource limits, and integration with system logging.

## Overview

```
┌────────────────────────────────────────────────────────────┐
│                      systemd                               │
│  ┌─────────────────────────────────────────────────────┐  │
│  │              zentinel-agents.target                  │  │
│  │  ┌──────────────┐ ┌──────────────┐ ┌─────────────┐  │  │
│  │  │zentinel-auth │ │zentinel-waf  │ │zentinel-echo│  │  │
│  │  │   .service   │ │  .service    │ │  .service   │  │  │
│  │  └──────┬───────┘ └──────┬───────┘ └──────┬──────┘  │  │
│  │         │                │                │         │  │
│  │  ┌──────┴───────┐ ┌──────┴───────┐ ┌──────┴──────┐  │  │
│  │  │zentinel-auth │ │zentinel-waf  │ │zentinel-echo│  │  │
│  │  │   .socket    │ │  .socket     │ │  .socket    │  │  │
│  │  └──────────────┘ └──────────────┘ └─────────────┘  │  │
│  └─────────────────────────────────────────────────────┘  │
│                            │                               │
│                            ▼                               │
│               ┌────────────────────────┐                  │
│               │    zentinel.service    │                  │
│               └────────────────────────┘                  │
└────────────────────────────────────────────────────────────┘
```

## Installation

### Create User and Directories

```bash
# Create zentinel user
sudo useradd --system --no-create-home --shell /usr/sbin/nologin zentinel

# Create directories
sudo mkdir -p /etc/zentinel
sudo mkdir -p /var/run/zentinel
sudo mkdir -p /var/log/zentinel

# Set permissions
sudo chown -R zentinel:zentinel /etc/zentinel
sudo chown -R zentinel:zentinel /var/run/zentinel
sudo chown -R zentinel:zentinel /var/log/zentinel
```

### Install Binaries

```bash
# Download and install
curl -sSL https://zentinelproxy.io/install.sh | sudo sh

# Or from source
cargo build --release
sudo cp target/release/zentinel /usr/local/bin/
sudo cp target/release/zentinel-echo-agent /usr/local/bin/
sudo cp target/release/zentinel-auth-agent /usr/local/bin/
```

## Unit Files

### Zentinel Proxy Service

```ini
# /etc/systemd/system/zentinel.service
[Unit]
Description=Zentinel Reverse Proxy
Documentation=https://zentinelproxy.io/docs/
After=network-online.target zentinel-agents.target
Wants=network-online.target zentinel-agents.target

[Service]
Type=simple
User=zentinel
Group=zentinel
ExecStart=/usr/local/bin/zentinel --config /etc/zentinel/zentinel.kdl
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=5

# Security hardening
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
PrivateDevices=true
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
ReadWritePaths=/var/run/zentinel /var/log/zentinel

# Resource limits
LimitNOFILE=65536
MemoryMax=1G

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=zentinel

[Install]
WantedBy=multi-user.target
```

### Agent Socket (Template)

```ini
# /etc/systemd/system/zentinel-agent@.socket
[Unit]
Description=Zentinel Agent Socket (%i)
PartOf=zentinel-agents.target

[Socket]
ListenStream=/var/run/zentinel/%i.sock
SocketUser=zentinel
SocketGroup=zentinel
SocketMode=0600

[Install]
WantedBy=sockets.target
```

### Agent Service (Template)

```ini
# /etc/systemd/system/zentinel-agent@.service
[Unit]
Description=Zentinel Agent (%i)
Documentation=https://zentinelproxy.io/docs/agents/
Requires=zentinel-agent@%i.socket
After=zentinel-agent@%i.socket
PartOf=zentinel-agents.target

[Service]
Type=simple
User=zentinel
Group=zentinel
ExecStart=/usr/local/bin/zentinel-%i-agent --socket /var/run/zentinel/%i.sock
Restart=on-failure
RestartSec=5

# Security hardening
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true

# Resource limits (adjust per agent)
MemoryMax=256M

[Install]
WantedBy=multi-user.target
```

### Agents Target

```ini
# /etc/systemd/system/zentinel-agents.target
[Unit]
Description=Zentinel Agents
Documentation=https://zentinelproxy.io/docs/agents/

[Install]
WantedBy=multi-user.target
```

## Per-Agent Configuration

For agents with specific requirements, create dedicated unit files:

### Auth Agent

```ini
# /etc/systemd/system/zentinel-auth.socket
[Unit]
Description=Zentinel Auth Agent Socket

[Socket]
ListenStream=/var/run/zentinel/auth.sock
SocketUser=zentinel
SocketGroup=zentinel
SocketMode=0600

[Install]
WantedBy=zentinel-agents.target
```

```ini
# /etc/systemd/system/zentinel-auth.service
[Unit]
Description=Zentinel Auth Agent
Requires=zentinel-auth.socket
After=zentinel-auth.socket

[Service]
Type=simple
User=zentinel
Group=zentinel
ExecStart=/usr/local/bin/zentinel-auth-agent \
    --socket /var/run/zentinel/auth.sock \
    --config /etc/zentinel/auth.toml
Restart=on-failure
RestartSec=5

# Auth agent needs access to secrets
Environment="AUTH_SECRET_FILE=/etc/zentinel/secrets/auth.key"
ReadOnlyPaths=/etc/zentinel/secrets

MemoryMax=128M

[Install]
WantedBy=zentinel-agents.target
```

### WAF Agent (gRPC)

```ini
# /etc/systemd/system/zentinel-waf.service
[Unit]
Description=Zentinel WAF Agent
After=network-online.target

[Service]
Type=simple
User=zentinel
Group=zentinel
ExecStart=/usr/local/bin/zentinel-waf-agent \
    --grpc 127.0.0.1:50051 \
    --rules /etc/zentinel/waf/crs-rules
Restart=on-failure
RestartSec=5

# WAF may need more memory for rules
MemoryMax=512M

[Install]
WantedBy=zentinel-agents.target
```

## Zentinel Configuration

```kdl
// /etc/zentinel/zentinel.kdl

system {
    listen "0.0.0.0:80"
    listen "0.0.0.0:443" {
        tls {
            cert "/etc/zentinel/tls/cert.pem"
            key "/etc/zentinel/tls/key.pem"
        }
    }
}

admin {
    listen "127.0.0.1:9090"
}

agents {
    agent "auth" type="auth" {
        unix-socket "/var/run/zentinel/auth.sock"
        events "request_headers"
        timeout-ms 50
        failure-mode "closed"
    }

    agent "waf" type="waf" {
        grpc "http://127.0.0.1:50051"
        events "request_headers" "request_body"
        timeout-ms 100
        failure-mode "open"
        max-request-body-bytes 1048576
    }
}

upstreams {
    upstream "api" {
        targets "10.0.1.10:8080" "10.0.1.11:8080"
        health-check {
            path "/health"
            interval-ms 5000
        }
    }
}

routes {
    route "api" {
        matches { path-prefix "/api/" }
        upstream "api"
        agents "auth" "waf"
    }
}
```

## Deployment Commands

### Enable and Start

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable socket activation for agents
sudo systemctl enable zentinel-auth.socket
sudo systemctl enable zentinel-waf.service
sudo systemctl enable zentinel-agents.target

# Start agents target (starts sockets, services start on demand)
sudo systemctl start zentinel-agents.target

# Enable and start Zentinel
sudo systemctl enable zentinel.service
sudo systemctl start zentinel.service
```

### Management

```bash
# Check status
sudo systemctl status zentinel
sudo systemctl status zentinel-auth
sudo systemctl status zentinel-waf

# View logs
sudo journalctl -u zentinel -f
sudo journalctl -u zentinel-auth -f

# Reload configuration (graceful)
sudo systemctl reload zentinel

# Restart
sudo systemctl restart zentinel

# Stop everything
sudo systemctl stop zentinel
sudo systemctl stop zentinel-agents.target
```

## Socket Activation

Socket activation provides several benefits:
- Agents start on-demand when first connection arrives
- Faster system boot (agents start lazily)
- systemd holds the socket during agent restarts (no connection loss)

```bash
# Check socket status
sudo systemctl status zentinel-auth.socket

# Socket is listening even if service isn't running
ss -l | grep zentinel
```

## Log Management

### journald Configuration

```ini
# /etc/systemd/journald.conf.d/zentinel.conf
[Journal]
SystemMaxUse=1G
MaxRetentionSec=7day
```

### Log Queries

```bash
# All Zentinel logs
journalctl -u 'zentinel*' --since today

# Just proxy logs
journalctl -u zentinel -f

# Agent logs with priority
journalctl -u zentinel-auth -p err

# JSON output for parsing
journalctl -u zentinel -o json | jq
```

### Forward to External System

```bash
# Export to file for shipping
journalctl -u zentinel -o json --since "1 hour ago" > /var/log/zentinel/export.json
```

## Resource Management

### CPU and Memory Limits

```ini
# In service file
[Service]
CPUQuota=200%          # Max 2 CPU cores
MemoryMax=1G           # Hard memory limit
MemoryHigh=800M        # Soft limit (throttling starts)
TasksMax=1000          # Max threads/processes
```

### File Descriptor Limits

```ini
[Service]
LimitNOFILE=65536      # Open files
LimitNPROC=4096        # Processes
```

### Verify Limits

```bash
# Check effective limits
cat /proc/$(pgrep -f zentinel)/limits
```

## Health Checks

### Systemd Watchdog

```ini
# /etc/systemd/system/zentinel.service.d/watchdog.conf
[Service]
WatchdogSec=30
```

Zentinel must notify systemd periodically:

```rust
// In Zentinel code
sd_notify::notify(false, &[sd_notify::NotifyState::Watchdog])?;
```

### External Health Checks

```bash
# Simple HTTP check
curl -f http://localhost:9090/health || systemctl restart zentinel

# As a systemd timer
# /etc/systemd/system/zentinel-healthcheck.timer
[Unit]
Description=Zentinel Health Check Timer

[Timer]
OnBootSec=1min
OnUnitActiveSec=30s

[Install]
WantedBy=timers.target
```

## Upgrades

### Rolling Upgrade

```bash
# 1. Deploy new binary
sudo cp zentinel-new /usr/local/bin/zentinel.new
sudo mv /usr/local/bin/zentinel.new /usr/local/bin/zentinel

# 2. Graceful restart
sudo systemctl reload zentinel
# or for full restart:
sudo systemctl restart zentinel

# 3. Verify
curl http://localhost:9090/health
```

### Blue-Green with Socket Activation

```bash
# Start new version on different port
zentinel --config /etc/zentinel/zentinel-new.kdl &

# Test new version
curl http://localhost:8081/health

# Switch traffic (update load balancer or DNS)
# Stop old version
sudo systemctl stop zentinel

# Rename new version
sudo systemctl start zentinel
```

## Troubleshooting

### Agent Not Starting

```bash
# Check socket
systemctl status zentinel-auth.socket

# Check service
systemctl status zentinel-auth.service

# Check logs
journalctl -u zentinel-auth -n 50

# Manual test
sudo -u zentinel /usr/local/bin/zentinel-auth-agent --socket /tmp/test.sock
```

### Permission Denied

```bash
# Check socket permissions
ls -la /var/run/zentinel/

# Fix ownership
sudo chown zentinel:zentinel /var/run/zentinel/*.sock
```

### Connection Refused

```bash
# Is the socket listening?
ss -l | grep zentinel

# Is the service running?
systemctl is-active zentinel-auth

# Try connecting manually
socat - UNIX-CONNECT:/var/run/zentinel/auth.sock
```

+++
title = "systemd Deployment"
weight = 3
+++

systemd is the recommended deployment method for production Sentinel installations on Linux. It provides robust process supervision, socket activation, resource limits, and integration with system logging.

## Overview

```
┌────────────────────────────────────────────────────────────┐
│                      systemd                               │
│  ┌─────────────────────────────────────────────────────┐  │
│  │              sentinel-agents.target                  │  │
│  │  ┌──────────────┐ ┌──────────────┐ ┌─────────────┐  │  │
│  │  │sentinel-auth │ │sentinel-waf  │ │sentinel-echo│  │  │
│  │  │   .service   │ │  .service    │ │  .service   │  │  │
│  │  └──────┬───────┘ └──────┬───────┘ └──────┬──────┘  │  │
│  │         │                │                │         │  │
│  │  ┌──────┴───────┐ ┌──────┴───────┐ ┌──────┴──────┐  │  │
│  │  │sentinel-auth │ │sentinel-waf  │ │sentinel-echo│  │  │
│  │  │   .socket    │ │  .socket     │ │  .socket    │  │  │
│  │  └──────────────┘ └──────────────┘ └─────────────┘  │  │
│  └─────────────────────────────────────────────────────┘  │
│                            │                               │
│                            ▼                               │
│               ┌────────────────────────┐                  │
│               │    sentinel.service    │                  │
│               └────────────────────────┘                  │
└────────────────────────────────────────────────────────────┘
```

## Installation

### Create User and Directories

```bash
# Create sentinel user
sudo useradd --system --no-create-home --shell /usr/sbin/nologin sentinel

# Create directories
sudo mkdir -p /etc/sentinel
sudo mkdir -p /var/run/sentinel
sudo mkdir -p /var/log/sentinel

# Set permissions
sudo chown -R sentinel:sentinel /etc/sentinel
sudo chown -R sentinel:sentinel /var/run/sentinel
sudo chown -R sentinel:sentinel /var/log/sentinel
```

### Install Binaries

```bash
# Download and install
curl -sSL https://sentinel.raskell.io/install.sh | sudo sh

# Or from source
cargo build --release
sudo cp target/release/sentinel /usr/local/bin/
sudo cp target/release/sentinel-echo-agent /usr/local/bin/
sudo cp target/release/sentinel-auth-agent /usr/local/bin/
```

## Unit Files

### Sentinel Proxy Service

```ini
# /etc/systemd/system/sentinel.service
[Unit]
Description=Sentinel Reverse Proxy
Documentation=https://sentinel.raskell.io/docs/
After=network-online.target sentinel-agents.target
Wants=network-online.target sentinel-agents.target

[Service]
Type=simple
User=sentinel
Group=sentinel
ExecStart=/usr/local/bin/sentinel --config /etc/sentinel/sentinel.kdl
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
ReadWritePaths=/var/run/sentinel /var/log/sentinel

# Resource limits
LimitNOFILE=65536
MemoryMax=1G

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=sentinel

[Install]
WantedBy=multi-user.target
```

### Agent Socket (Template)

```ini
# /etc/systemd/system/sentinel-agent@.socket
[Unit]
Description=Sentinel Agent Socket (%i)
PartOf=sentinel-agents.target

[Socket]
ListenStream=/var/run/sentinel/%i.sock
SocketUser=sentinel
SocketGroup=sentinel
SocketMode=0600

[Install]
WantedBy=sockets.target
```

### Agent Service (Template)

```ini
# /etc/systemd/system/sentinel-agent@.service
[Unit]
Description=Sentinel Agent (%i)
Documentation=https://sentinel.raskell.io/docs/agents/
Requires=sentinel-agent@%i.socket
After=sentinel-agent@%i.socket
PartOf=sentinel-agents.target

[Service]
Type=simple
User=sentinel
Group=sentinel
ExecStart=/usr/local/bin/sentinel-%i-agent --socket /var/run/sentinel/%i.sock
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
# /etc/systemd/system/sentinel-agents.target
[Unit]
Description=Sentinel Agents
Documentation=https://sentinel.raskell.io/docs/agents/

[Install]
WantedBy=multi-user.target
```

## Per-Agent Configuration

For agents with specific requirements, create dedicated unit files:

### Auth Agent

```ini
# /etc/systemd/system/sentinel-auth.socket
[Unit]
Description=Sentinel Auth Agent Socket

[Socket]
ListenStream=/var/run/sentinel/auth.sock
SocketUser=sentinel
SocketGroup=sentinel
SocketMode=0600

[Install]
WantedBy=sentinel-agents.target
```

```ini
# /etc/systemd/system/sentinel-auth.service
[Unit]
Description=Sentinel Auth Agent
Requires=sentinel-auth.socket
After=sentinel-auth.socket

[Service]
Type=simple
User=sentinel
Group=sentinel
ExecStart=/usr/local/bin/sentinel-auth-agent \
    --socket /var/run/sentinel/auth.sock \
    --config /etc/sentinel/auth.toml
Restart=on-failure
RestartSec=5

# Auth agent needs access to secrets
Environment="AUTH_SECRET_FILE=/etc/sentinel/secrets/auth.key"
ReadOnlyPaths=/etc/sentinel/secrets

MemoryMax=128M

[Install]
WantedBy=sentinel-agents.target
```

### WAF Agent (gRPC)

```ini
# /etc/systemd/system/sentinel-waf.service
[Unit]
Description=Sentinel WAF Agent
After=network-online.target

[Service]
Type=simple
User=sentinel
Group=sentinel
ExecStart=/usr/local/bin/sentinel-waf-agent \
    --grpc 127.0.0.1:50051 \
    --rules /etc/sentinel/waf/crs-rules
Restart=on-failure
RestartSec=5

# WAF may need more memory for rules
MemoryMax=512M

[Install]
WantedBy=sentinel-agents.target
```

## Sentinel Configuration

```kdl
// /etc/sentinel/sentinel.kdl

server {
    listen "0.0.0.0:80"
    listen "0.0.0.0:443" {
        tls {
            cert "/etc/sentinel/tls/cert.pem"
            key "/etc/sentinel/tls/key.pem"
        }
    }
}

admin {
    listen "127.0.0.1:9090"
}

agents {
    agent "auth" type="auth" {
        unix-socket "/var/run/sentinel/auth.sock"
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
sudo systemctl enable sentinel-auth.socket
sudo systemctl enable sentinel-waf.service
sudo systemctl enable sentinel-agents.target

# Start agents target (starts sockets, services start on demand)
sudo systemctl start sentinel-agents.target

# Enable and start Sentinel
sudo systemctl enable sentinel.service
sudo systemctl start sentinel.service
```

### Management

```bash
# Check status
sudo systemctl status sentinel
sudo systemctl status sentinel-auth
sudo systemctl status sentinel-waf

# View logs
sudo journalctl -u sentinel -f
sudo journalctl -u sentinel-auth -f

# Reload configuration (graceful)
sudo systemctl reload sentinel

# Restart
sudo systemctl restart sentinel

# Stop everything
sudo systemctl stop sentinel
sudo systemctl stop sentinel-agents.target
```

## Socket Activation

Socket activation provides several benefits:
- Agents start on-demand when first connection arrives
- Faster system boot (agents start lazily)
- systemd holds the socket during agent restarts (no connection loss)

```bash
# Check socket status
sudo systemctl status sentinel-auth.socket

# Socket is listening even if service isn't running
ss -l | grep sentinel
```

## Log Management

### journald Configuration

```ini
# /etc/systemd/journald.conf.d/sentinel.conf
[Journal]
SystemMaxUse=1G
MaxRetentionSec=7day
```

### Log Queries

```bash
# All Sentinel logs
journalctl -u 'sentinel*' --since today

# Just proxy logs
journalctl -u sentinel -f

# Agent logs with priority
journalctl -u sentinel-auth -p err

# JSON output for parsing
journalctl -u sentinel -o json | jq
```

### Forward to External System

```bash
# Export to file for shipping
journalctl -u sentinel -o json --since "1 hour ago" > /var/log/sentinel/export.json
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
cat /proc/$(pgrep -f sentinel)/limits
```

## Health Checks

### Systemd Watchdog

```ini
# /etc/systemd/system/sentinel.service.d/watchdog.conf
[Service]
WatchdogSec=30
```

Sentinel must notify systemd periodically:

```rust
// In Sentinel code
sd_notify::notify(false, &[sd_notify::NotifyState::Watchdog])?;
```

### External Health Checks

```bash
# Simple HTTP check
curl -f http://localhost:9090/health || systemctl restart sentinel

# As a systemd timer
# /etc/systemd/system/sentinel-healthcheck.timer
[Unit]
Description=Sentinel Health Check Timer

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
sudo cp sentinel-new /usr/local/bin/sentinel.new
sudo mv /usr/local/bin/sentinel.new /usr/local/bin/sentinel

# 2. Graceful restart
sudo systemctl reload sentinel
# or for full restart:
sudo systemctl restart sentinel

# 3. Verify
curl http://localhost:9090/health
```

### Blue-Green with Socket Activation

```bash
# Start new version on different port
sentinel --config /etc/sentinel/sentinel-new.kdl &

# Test new version
curl http://localhost:8081/health

# Switch traffic (update load balancer or DNS)
# Stop old version
sudo systemctl stop sentinel

# Rename new version
sudo systemctl start sentinel
```

## Troubleshooting

### Agent Not Starting

```bash
# Check socket
systemctl status sentinel-auth.socket

# Check service
systemctl status sentinel-auth.service

# Check logs
journalctl -u sentinel-auth -n 50

# Manual test
sudo -u sentinel /usr/local/bin/sentinel-auth-agent --socket /tmp/test.sock
```

### Permission Denied

```bash
# Check socket permissions
ls -la /var/run/sentinel/

# Fix ownership
sudo chown sentinel:sentinel /var/run/sentinel/*.sock
```

### Connection Refused

```bash
# Is the socket listening?
ss -l | grep sentinel

# Is the service running?
systemctl is-active sentinel-auth

# Try connecting manually
socat - UNIX-CONNECT:/var/run/sentinel/auth.sock
```

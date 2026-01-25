+++
title = "Bundle Installation"
weight = 1
+++

The `sentinel bundle` command provides a streamlined way to install Sentinel with its bundled agents. This is the recommended approach for production deployments on Linux servers.

## Overview

Instead of manually downloading and configuring each agent, the bundle command:

1. Downloads agent binaries from their official GitHub releases
2. Installs them to the appropriate system locations
3. Optionally generates configuration and systemd service files

```
┌─────────────────────────────────────────────────────────┐
│              sentinel bundle install                     │
│                                                         │
│  Reads lock file → Downloads agents → Installs binaries │
│                                                         │
│  Bundled agents:                                        │
│    • WAF (ModSecurity-based firewall)                  │
│    • Ratelimit (Token bucket limiting)                 │
│    • Denylist (IP/path blocking)                       │
└─────────────────────────────────────────────────────────┘
```

## Quick Start

```bash
# 1. Install Sentinel
curl -fsSL https://getsentinel.raskell.io | sh

# 2. Install bundled agents
sudo sentinel bundle install

# 3. Check status
sentinel bundle status

# 4. Configure and start
sudo systemctl start sentinel.target
```

## Commands Reference

### Install Agents

```bash
# Install all bundled agents
sudo sentinel bundle install

# Install with systemd services
sudo sentinel bundle install --systemd

# Install a specific agent only
sudo sentinel bundle install waf

# Preview without installing
sentinel bundle install --dry-run

# Force reinstall even if up to date
sudo sentinel bundle install --force

# Custom installation prefix
sudo sentinel bundle install --prefix /opt/sentinel

# Skip checksum verification
sudo sentinel bundle install --skip-verify
```

### Check Status

```bash
sentinel bundle status
```

Example output:

```
Sentinel Bundle Status
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Bundle version: 26.01_1
Install path:   /usr/local/bin

Agent           Installed    Expected     Status
─────────────────────────────────────────────────
denylist        0.2.0        0.2.0        ✓ up to date
ratelimit       0.2.0        0.2.0        ✓ up to date
waf             -            0.2.0        ✗ not installed

Total: 3 | Up to date: 2 | Outdated: 0 | Not installed: 1
```

### List Available Agents

```bash
# List agents
sentinel bundle list

# With download URLs
sentinel bundle list --verbose
```

### Check for Updates

```bash
# Check what's available
sentinel bundle update

# Apply updates
sentinel bundle update --apply
```

### Uninstall Agents

```bash
# Remove all agents
sudo sentinel bundle uninstall

# Remove specific agent
sudo sentinel bundle uninstall waf

# Preview
sentinel bundle uninstall --dry-run
```

## Bundled Agents

The bundle includes agents that cover common production use cases:

### WAF Agent

ModSecurity-based web application firewall with OWASP Core Rule Set support.

**Use cases:**
- SQL injection protection
- XSS prevention
- Request validation
- Security baseline

**Configuration:** `/etc/sentinel/agents/waf.yaml`

```yaml
socket:
  path: /var/run/sentinel/waf.sock

modsecurity:
  engine: "On"

crs:
  paranoia_level: 1
  inbound_anomaly_score_threshold: 5
```

### Ratelimit Agent

Token bucket rate limiting with flexible rule configuration.

**Use cases:**
- API rate limiting
- DDoS mitigation
- Fair usage enforcement
- Cost control

**Configuration:** `/etc/sentinel/agents/ratelimit.yaml`

```yaml
socket:
  path: /var/run/sentinel/ratelimit.sock

rules:
  - name: api_per_ip
    match:
      path_prefix: /api
    limit:
      requests_per_second: 100
      burst: 200
    key: client_ip
```

### Denylist Agent

Simple IP and path blocking for known bad actors.

**Use cases:**
- Block malicious IPs
- Block scanner paths
- Geographic restrictions
- Emergency blocking

**Configuration:** `/etc/sentinel/agents/denylist.yaml`

```yaml
socket:
  path: /var/run/sentinel/denylist.sock

ip_denylist:
  enabled: true

path_denylist:
  enabled: true
  patterns:
    - ".*\\.php$"
    - "/wp-admin.*"
```

## Configuration

After installing agents, configure Sentinel to use them.

### Add Agents to sentinel.kdl

```kdl
agents {
    agent "waf" {
        endpoint "unix:///var/run/sentinel/waf.sock"
        timeout-ms 100
        failure-mode "open"
    }

    agent "ratelimit" {
        endpoint "unix:///var/run/sentinel/ratelimit.sock"
        timeout-ms 50
        failure-mode "open"
    }

    agent "denylist" {
        endpoint "unix:///var/run/sentinel/denylist.sock"
        timeout-ms 20
        failure-mode "open"
    }
}
```

### Apply Agents to Routes

```kdl
routes {
    route "api" {
        priority "high"
        matches { path-prefix "/api" }
        upstream "backend"
        policies {
            // Order matters: check deny first, then rate limit, then WAF
            agents "denylist" "ratelimit" "waf"
        }
    }

    route "static" {
        priority "normal"
        matches { path-prefix "/static" }
        upstream "cdn"
        policies {
            // Static content only needs denylist
            agents "denylist"
        }
    }
}
```

## Systemd Integration

Install with systemd services for production:

```bash
# Install with systemd
sudo sentinel bundle install --systemd

# Reload systemd
sudo systemctl daemon-reload

# Enable the target (starts on boot)
sudo systemctl enable sentinel.target

# Start everything
sudo systemctl start sentinel.target
```

The `sentinel.target` groups all services:

```bash
# Check all services
sudo systemctl status sentinel.target

# View proxy logs
sudo journalctl -u sentinel -f

# View WAF logs
sudo journalctl -u sentinel-waf -f
```

### Service Dependencies

```
sentinel.target
├── sentinel.service        (proxy)
├── sentinel-waf.service    (WAF agent)
├── sentinel-ratelimit.service
└── sentinel-denylist.service
```

All agent services depend on `sentinel.service` and are part of `sentinel.target`.

## Installation Paths

### System-wide (requires root)

| Type | Path |
|------|------|
| Binaries | `/usr/local/bin/sentinel-{agent}-agent` |
| Configs | `/etc/sentinel/agents/{agent}.yaml` |
| Systemd | `/etc/systemd/system/sentinel-{agent}.service` |
| Runtime | `/var/run/sentinel/` |

### User-local (no root)

| Type | Path |
|------|------|
| Binaries | `~/.local/bin/sentinel-{agent}-agent` |
| Configs | `~/.config/sentinel/agents/{agent}.yaml` |
| Systemd | `~/.config/systemd/user/sentinel-{agent}.service` |

The command automatically detects whether to use system-wide or user-local paths.

## Version Management

Agent versions are coordinated via a lock file embedded in Sentinel:

```bash
# Check current versions
sentinel bundle status

# Check for updates
sentinel bundle update

# Update to latest
sentinel bundle install --force
```

The lock file ensures that all installed components are tested to work together.

## Troubleshooting

### Permission Denied

```bash
# Use sudo for system-wide installation
sudo sentinel bundle install

# Or use user-local paths
sentinel bundle install --prefix ~/.local
```

### Download Failed

Check network connectivity:

```bash
# Show download URLs
sentinel bundle list --verbose

# Test connectivity
curl -I https://github.com/raskell-io/sentinel-agent-waf/releases
```

### Agent Won't Start

Check logs and socket permissions:

```bash
# Check logs
sudo journalctl -u sentinel-waf -f

# Check socket directory
ls -la /var/run/sentinel/

# Ensure sentinel user owns the directory
sudo chown sentinel:sentinel /var/run/sentinel
```

### Version Mismatch

Force reinstall:

```bash
sudo sentinel bundle install --force
```

## Example: Complete Setup

```bash
# 1. Install Sentinel
curl -fsSL https://getsentinel.raskell.io | sh

# 2. Install bundled agents with systemd
sudo sentinel bundle install --systemd

# 3. Create configuration
sudo mkdir -p /etc/sentinel
sudo cat > /etc/sentinel/config.kdl << 'EOF'
system {
    worker-threads 0
}

listeners {
    listener "http" {
        address "0.0.0.0:8080"
        protocol "http"
    }
}

agents {
    agent "denylist" {
        endpoint "unix:///var/run/sentinel/denylist.sock"
        timeout-ms 20
        failure-mode "open"
    }
    agent "ratelimit" {
        endpoint "unix:///var/run/sentinel/ratelimit.sock"
        timeout-ms 50
        failure-mode "open"
    }
    agent "waf" {
        endpoint "unix:///var/run/sentinel/waf.sock"
        timeout-ms 100
        failure-mode "open"
    }
}

routes {
    route "default" {
        matches { path-prefix "/" }
        upstream "backend"
        policies {
            agents "denylist" "ratelimit" "waf"
        }
    }
}

upstreams {
    upstream "backend" {
        target "127.0.0.1:3000"
    }
}
EOF

# 4. Start everything
sudo systemctl daemon-reload
sudo systemctl enable sentinel.target
sudo systemctl start sentinel.target

# 5. Verify
curl localhost:8080/_builtin/health
sudo systemctl status sentinel.target
```

## See Also

- [Installation](/getting-started/installation/) - Installing Sentinel
- [Systemd Deployment](../systemd/) - Production systemd setup
- [Docker Compose](../docker-compose/) - Container deployment with agents
- [Configuration Reference](/configuration/agents/) - Agent configuration options

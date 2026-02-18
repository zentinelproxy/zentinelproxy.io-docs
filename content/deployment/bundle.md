+++
title = "Bundle Installation"
weight = 1
+++

The `zentinel bundle` command provides a streamlined way to install Zentinel with its bundled agents. This is the recommended approach for production deployments on Linux servers.

## Overview

Instead of manually downloading and configuring each agent, the bundle command:

1. Downloads agent binaries from their official GitHub releases
2. Installs them to the appropriate system locations
3. Optionally generates configuration and systemd service files

```
┌─────────────────────────────────────────────────────────┐
│              zentinel bundle install                     │
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
# 1. Install Zentinel
curl -fsSL https://get.zentinelproxy.io | sh

# 2. Install bundled agents
sudo zentinel bundle install

# 3. Check status
zentinel bundle status

# 4. Configure and start
sudo systemctl start zentinel.target
```

## Commands Reference

### Install Agents

```bash
# Install all bundled agents
sudo zentinel bundle install

# Install with systemd services
sudo zentinel bundle install --systemd

# Install a specific agent only
sudo zentinel bundle install waf

# Preview without installing
zentinel bundle install --dry-run

# Force reinstall even if up to date
sudo zentinel bundle install --force

# Custom installation prefix
sudo zentinel bundle install --prefix /opt/zentinel

# Skip checksum verification
sudo zentinel bundle install --skip-verify
```

### Check Status

```bash
zentinel bundle status
```

Example output:

```
Zentinel Bundle Status
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
zentinel bundle list

# With download URLs
zentinel bundle list --verbose
```

### Check for Updates

```bash
# Check what's available
zentinel bundle update

# Apply updates
zentinel bundle update --apply
```

### Uninstall Agents

```bash
# Remove all agents
sudo zentinel bundle uninstall

# Remove specific agent
sudo zentinel bundle uninstall waf

# Preview
zentinel bundle uninstall --dry-run
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

**Configuration:** `/etc/zentinel/agents/waf.yaml`

```yaml
socket:
  path: /var/run/zentinel/waf.sock

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

**Configuration:** `/etc/zentinel/agents/ratelimit.yaml`

```yaml
socket:
  path: /var/run/zentinel/ratelimit.sock

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

**Configuration:** `/etc/zentinel/agents/denylist.yaml`

```yaml
socket:
  path: /var/run/zentinel/denylist.sock

ip_denylist:
  enabled: true

path_denylist:
  enabled: true
  patterns:
    - ".*\\.php$"
    - "/wp-admin.*"
```

## Configuration

After installing agents, configure Zentinel to use them.

### Add Agents to zentinel.kdl

```kdl
agents {
    agent "waf" {
        endpoint "unix:///var/run/zentinel/waf.sock"
        timeout-ms 100
        failure-mode "open"
    }

    agent "ratelimit" {
        endpoint "unix:///var/run/zentinel/ratelimit.sock"
        timeout-ms 50
        failure-mode "open"
    }

    agent "denylist" {
        endpoint "unix:///var/run/zentinel/denylist.sock"
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
sudo zentinel bundle install --systemd

# Reload systemd
sudo systemctl daemon-reload

# Enable the target (starts on boot)
sudo systemctl enable zentinel.target

# Start everything
sudo systemctl start zentinel.target
```

The `zentinel.target` groups all services:

```bash
# Check all services
sudo systemctl status zentinel.target

# View proxy logs
sudo journalctl -u zentinel -f

# View WAF logs
sudo journalctl -u zentinel-waf -f
```

### Service Dependencies

```
zentinel.target
├── zentinel.service        (proxy)
├── zentinel-waf.service    (WAF agent)
├── zentinel-ratelimit.service
└── zentinel-denylist.service
```

All agent services depend on `zentinel.service` and are part of `zentinel.target`.

## Installation Paths

### System-wide (requires root)

| Type | Path |
|------|------|
| Binaries | `/usr/local/bin/zentinel-{agent}-agent` |
| Configs | `/etc/zentinel/agents/{agent}.yaml` |
| Systemd | `/etc/systemd/system/zentinel-{agent}.service` |
| Runtime | `/var/run/zentinel/` |

### User-local (no root)

| Type | Path |
|------|------|
| Binaries | `~/.local/bin/zentinel-{agent}-agent` |
| Configs | `~/.config/zentinel/agents/{agent}.yaml` |
| Systemd | `~/.config/systemd/user/zentinel-{agent}.service` |

The command automatically detects whether to use system-wide or user-local paths.

## Version Management

Agent versions are coordinated via a lock file embedded in Zentinel:

```bash
# Check current versions
zentinel bundle status

# Check for updates
zentinel bundle update

# Update to latest
zentinel bundle install --force
```

The lock file ensures that all installed components are tested to work together.

## Troubleshooting

### Permission Denied

```bash
# Use sudo for system-wide installation
sudo zentinel bundle install

# Or use user-local paths
zentinel bundle install --prefix ~/.local
```

### Download Failed

Check network connectivity:

```bash
# Show download URLs
zentinel bundle list --verbose

# Test connectivity
curl -I https://github.com/zentinelproxy/zentinel-agent-waf/releases
```

### Agent Won't Start

Check logs and socket permissions:

```bash
# Check logs
sudo journalctl -u zentinel-waf -f

# Check socket directory
ls -la /var/run/zentinel/

# Ensure zentinel user owns the directory
sudo chown zentinel:zentinel /var/run/zentinel
```

### Version Mismatch

Force reinstall:

```bash
sudo zentinel bundle install --force
```

## Example: Complete Setup

```bash
# 1. Install Zentinel
curl -fsSL https://get.zentinelproxy.io | sh

# 2. Install bundled agents with systemd
sudo zentinel bundle install --systemd

# 3. Create configuration
sudo mkdir -p /etc/zentinel
sudo cat > /etc/zentinel/config.kdl << 'EOF'
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
        endpoint "unix:///var/run/zentinel/denylist.sock"
        timeout-ms 20
        failure-mode "open"
    }
    agent "ratelimit" {
        endpoint "unix:///var/run/zentinel/ratelimit.sock"
        timeout-ms 50
        failure-mode "open"
    }
    agent "waf" {
        endpoint "unix:///var/run/zentinel/waf.sock"
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
sudo systemctl enable zentinel.target
sudo systemctl start zentinel.target

# 5. Verify
curl localhost:8080/_builtin/health
sudo systemctl status zentinel.target
```

## See Also

- [Installation](/getting-started/installation/) - Installing Zentinel
- [Systemd Deployment](../systemd/) - Production systemd setup
- [Docker Compose](../docker-compose/) - Container deployment with agents
- [Configuration Reference](/configuration/agents/) - Agent configuration options

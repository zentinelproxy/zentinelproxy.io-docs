+++
title = "Bundle Installation"
weight = 1
updated = 2026-02-24
+++

The `zentinel bundle` command provides a streamlined way to install Zentinel with its bundled agents. This is the recommended approach for production deployments on Linux servers.

## Overview

Instead of manually downloading and configuring each agent, the bundle command:

1. Downloads agent binaries from their official GitHub releases
2. Installs them to the appropriate system locations
3. Optionally generates configuration and systemd service files

```
┌─────────────────────────────────────────────────────────────────────┐
│                    zentinel bundle install                           │
│                                                                     │
│  Reads lock file → Downloads agents → Installs binaries             │
│                                                                     │
│  26 bundled agents across 7 categories:                             │
│    Core        ─ WAF, Denylist, Rate Limiter                        │
│    Security    ─ ZentinelSec, ModSecurity, IP Reputation,           │
│                  Bot Management, Content Scanner                    │
│    API         ─ GraphQL Security, gRPC Inspector, SOAP,            │
│                  API Deprecation                                    │
│    Protocol    ─ WebSocket Inspector, MQTT Gateway                  │
│    Scripting   ─ Lua, JS, WASM                                     │
│    Utility     ─ Transform, Audit Logger, Mock Server, Chaos,       │
│                  Image Optimization                                 │
│    Identity    ─ SPIFFE                                             │
└─────────────────────────────────────────────────────────────────────┘
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
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Bundle version: 26.02_14
Install path:   /usr/local/bin

Agent                Installed    Expected     Status
─────────────────────────────────────────────────────────────
api-deprecation      0.4.0        0.4.0        ✓ up to date
audit-logger         0.4.0        0.4.0        ✓ up to date
bot-management       0.4.0        0.4.0        ✓ up to date
chaos                0.4.0        0.4.0        ✓ up to date
content-scanner      0.4.0        0.4.0        ✓ up to date
denylist             0.3.0        0.3.0        ✓ up to date
graphql-security     0.4.0        0.4.0        ✓ up to date
grpc-inspector       0.4.0        0.4.0        ✓ up to date
image-optimization   0.1.0        0.1.0        ✓ up to date
ip-reputation        0.4.0        0.4.0        ✓ up to date
js                   0.3.0        0.3.0        ✓ up to date
lua                  0.3.0        0.3.0        ✓ up to date
mock-server          0.4.0        0.4.0        ✓ up to date
modsec               0.3.0        0.3.0        ✓ up to date
mqtt-gateway         0.4.0        0.4.0        ✓ up to date
ratelimit            0.3.0        0.3.0        ✓ up to date
soap                 0.4.0        0.4.0        ✓ up to date
spiffe               0.3.0        0.3.0        ✓ up to date
transform            0.4.0        0.4.0        ✓ up to date
waf                  0.3.0        0.3.0        ✓ up to date
wasm                 0.3.0        0.3.0        ✓ up to date
websocket-inspector  0.4.0        0.4.0        ✓ up to date
zentinelsec          0.3.0        0.3.0        ✓ up to date

Total: 23 | Up to date: 23 | Outdated: 0 | Not installed: 0
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

The bundle includes 23 agents across 7 categories covering common production use cases.

### Core Agents

#### WAF Agent (v0.3.0)

Pure Rust web application firewall with 285 detection rules, anomaly scoring, and API security.

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

#### Denylist Agent (v0.3.0)

Block requests based on IP addresses, CIDR ranges, or custom patterns with real-time updates.

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

#### Rate Limiter Agent (v0.3.0, deprecated)

Token bucket rate limiting with configurable windows and limits per route, IP, or custom keys.

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

### Security Agents

| Agent | Version | Description |
|-------|---------|-------------|
| **ZentinelSec** | v0.3.0 | Pure Rust ModSecurity-compatible WAF with full OWASP CRS — no C dependencies |
| **ModSecurity** | v0.3.0 | OWASP CRS via libmodsecurity with 800+ detection rules |
| **IP Reputation** | v0.4.0 | Threat intelligence with AbuseIPDB, file-based blocklists, Tor exit node detection |
| **Bot Management** | v0.4.0 | Multi-signal bot detection, known bot verification, behavioral tracking |
| **Content Scanner** | v0.4.0 | ClamAV-based malware scanning for file uploads |

### API Security Agents

| Agent | Version | Description |
|-------|---------|-------------|
| **GraphQL Security** | v0.4.0 | Query depth limiting, complexity analysis, introspection control |
| **gRPC Inspector** | v0.4.0 | Method authorization, rate limiting, metadata inspection |
| **SOAP** | v0.4.0 | Envelope validation, WS-Security, XXE prevention |
| **API Deprecation** | v0.4.0 | RFC 8594 Sunset headers, usage tracking, automatic redirects |

### Protocol Agents

| Agent | Version | Description |
|-------|---------|-------------|
| **WebSocket Inspector** | v0.4.0 | Content filtering, schema validation, attack detection for WebSocket frames |
| **MQTT Gateway** | v0.4.0 | Topic-based ACLs, client auth, payload inspection, QoS enforcement |

### Scripting Agents

| Agent | Version | Description |
|-------|---------|-------------|
| **Lua** | v0.3.0 | Custom Lua scripts for request/response processing |
| **JS** | v0.3.0 | JavaScript logic using QuickJS engine |
| **WASM** | v0.3.0 | WebAssembly modules for high-performance processing |

### Utility Agents

| Agent | Version | Description |
|-------|---------|-------------|
| **Transform** | v0.4.0 | URL rewriting, header manipulation, JSON body transforms |
| **Audit Logger** | v0.4.0 | Structured logging with PII redaction, compliance templates (SOC2, HIPAA, PCI, GDPR) |
| **Mock Server** | v0.4.0 | Configurable stub responses with templating and latency simulation |
| **Chaos** | v0.4.0 | Fault injection for resilience testing (latency, errors, timeouts) |
| **Image Optimization** | v0.1.0 | JPEG/PNG to WebP/AVIF conversion with content negotiation and caching |

### Identity Agents

| Agent | Version | Description |
|-------|---------|-------------|
| **SPIFFE** | v0.3.0 | SPIFFE/SPIRE workload identity for zero-trust service-to-service communication |

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

    agent "image-optimization" {
        endpoint "unix:///var/run/zentinel/image-optimization.sock"
        timeout-ms 500
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

    route "images" {
        priority "normal"
        matches { path-prefix "/images" }
        upstream "cdn"
        policies {
            agents "denylist" "image-optimization"
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
├── zentinel.service              (proxy)
├── zentinel-waf.service
├── zentinel-denylist.service
├── zentinel-ratelimit.service
├── zentinel-zentinelsec.service
├── zentinel-modsec.service
├── zentinel-ip-reputation.service
├── zentinel-bot-management.service
├── zentinel-content-scanner.service
├── zentinel-graphql-security.service
├── zentinel-grpc-inspector.service
├── zentinel-soap.service
├── zentinel-api-deprecation.service
├── zentinel-websocket-inspector.service
├── zentinel-mqtt-gateway.service
├── zentinel-lua.service
├── zentinel-js.service
├── zentinel-wasm.service
├── zentinel-transform.service
├── zentinel-audit-logger.service
├── zentinel-mock-server.service
├── zentinel-chaos.service
├── zentinel-image-optimization.service
└── zentinel-spiffe.service
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

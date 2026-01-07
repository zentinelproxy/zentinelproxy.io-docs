+++
title = "sentinel-stack"
weight = 2
+++

`sentinel-stack` is a lightweight launcher that runs Sentinel and its agents as a single command. It's designed for development and simple deployments where full process supervision isn't needed.

## Overview

```
sentinel-stack
    │
    ├── Spawns sentinel (proxy)
    ├── Spawns each configured agent
    ├── Monitors and restarts crashed processes
    └── Forwards signals for graceful shutdown
```

## Installation

`sentinel-stack` is included with Sentinel:

```bash
# Install via cargo
cargo install sentinel-stack

# Or download from releases
curl -sSL https://sentinel.raskell.io/install.sh | sh
```

## Quick Start

```bash
# Create a simple config
cat > sentinel.kdl << 'EOF'
server {
    listen "0.0.0.0:8080"
}

agents {
    agent "echo" type="custom" {
        command "sentinel-echo-agent" "--socket" "/tmp/echo.sock"
        unix-socket "/tmp/echo.sock"
        events "request_headers"
    }
}

upstreams {
    upstream "backend" {
        target "127.0.0.1:3000"
    }
}

routes {
    route "all" {
        matches { path-prefix "/" }
        upstream "backend"
        agents "echo"
    }
}
EOF

# Start everything
sentinel-stack --config sentinel.kdl
```

## Configuration

### Agent Commands

When using `sentinel-stack`, agents include a `command` directive:

```kdl
agents {
    agent "auth" type="auth" {
        // Command to spawn the agent
        command "sentinel-auth-agent" "--socket" "/tmp/auth.sock"

        // Connection details (same as standalone Sentinel)
        unix-socket "/tmp/auth.sock"
        events "request_headers"
        timeout-ms 100

        // Restart policy
        restart-policy "always"     // always, on-failure, never
        restart-delay-ms 1000       // Wait before restart
        max-restarts 10             // 0 = unlimited
    }

    agent "waf" type="waf" {
        // gRPC agent
        command "sentinel-waf-agent" "--grpc" "127.0.0.1:50051"
        grpc "http://127.0.0.1:50051"
        events "request_headers" "request_body"

        restart-policy "on-failure"
        restart-delay-ms 2000
    }

    agent "external" type="custom" {
        // No command = external agent (not managed by sentinel-stack)
        grpc "http://external-service:50051"
        events "request_headers"
    }
}
```

### Restart Policies

| Policy | Behavior |
|--------|----------|
| `always` | Always restart, regardless of exit code |
| `on-failure` | Restart only on non-zero exit code |
| `never` | Don't restart (useful for one-shot agents) |

### Environment Variables

Pass environment to agents:

```kdl
agent "auth" type="auth" {
    command "sentinel-auth-agent"

    env {
        AUTH_SECRET "${AUTH_SECRET}"
        LOG_LEVEL "debug"
        CONFIG_PATH "/etc/auth/config.toml"
    }
}
```

## CLI Reference

```bash
sentinel-stack [OPTIONS]

Options:
    -c, --config <PATH>     Config file path [default: sentinel.kdl]
    -l, --log-level <LVL>   Log level [default: info]
    --proxy-only            Start only the proxy (no agents)
    --agents-only           Start only agents (no proxy)
    --dry-run               Validate config and exit
    -h, --help              Print help
    -V, --version           Print version
```

### Examples

```bash
# Standard startup
sentinel-stack --config sentinel.kdl

# Debug logging
sentinel-stack -l debug

# Validate configuration
sentinel-stack --dry-run

# Start only proxy (agents managed externally)
sentinel-stack --proxy-only

# Start only agents (proxy managed externally)
sentinel-stack --agents-only
```

## Process Management

### Startup Sequence

1. Parse and validate configuration
2. Spawn agents in dependency order
3. Wait for agent sockets/ports to be ready
4. Start Sentinel proxy
5. Begin accepting traffic

### Shutdown Sequence

On SIGTERM or SIGINT:
1. Stop accepting new connections
2. Send SIGTERM to proxy (graceful drain)
3. Wait for in-flight requests (configurable timeout)
4. Send SIGTERM to agents
5. Exit

```kdl
stack {
    shutdown-timeout-seconds 30    // Max wait for graceful shutdown
    startup-timeout-seconds 10     // Max wait for agents to be ready
}
```

### Health Monitoring

`sentinel-stack` provides a combined health endpoint:

```bash
curl http://localhost:9090/stack/health
```

```json
{
  "status": "healthy",
  "proxy": {
    "status": "healthy",
    "uptime_seconds": 3600
  },
  "agents": {
    "auth": {"status": "healthy", "pid": 1234, "restarts": 0},
    "waf": {"status": "healthy", "pid": 1235, "restarts": 1}
  }
}
```

## Logging

All output is unified through `sentinel-stack`:

```bash
sentinel-stack --config sentinel.kdl 2>&1 | jq
```

```json
{"timestamp":"2025-12-29T10:00:00Z","level":"INFO","component":"stack","message":"Starting sentinel-stack"}
{"timestamp":"2025-12-29T10:00:00Z","level":"INFO","component":"agent:auth","message":"Agent started","pid":1234}
{"timestamp":"2025-12-29T10:00:00Z","level":"INFO","component":"agent:waf","message":"Agent started","pid":1235}
{"timestamp":"2025-12-29T10:00:00Z","level":"INFO","component":"proxy","message":"Listening on 0.0.0.0:8080"}
```

## Example Configurations

### Development Setup

```kdl
// dev.kdl - Simple development config
server {
    listen "127.0.0.1:8080"
}

admin {
    listen "127.0.0.1:9090"
}

agents {
    agent "echo" type="custom" {
        command "cargo" "run" "--release" "-p" "sentinel-echo-agent" "--" "--socket" "/tmp/echo.sock"
        unix-socket "/tmp/echo.sock"
        events "request_headers"
        restart-policy "always"
    }
}

upstreams {
    upstream "backend" {
        target "127.0.0.1:3000"
    }
}

routes {
    route "api" {
        matches { path-prefix "/" }
        upstream "backend"
        agents "echo"
    }
}
```

### Production-like Local

```kdl
// local-prod.kdl - Production-like but local
server {
    listen "0.0.0.0:8080"
}

admin {
    listen "127.0.0.1:9090"
}

stack {
    shutdown-timeout-seconds 30
}

agents {
    agent "auth" type="auth" {
        command "/usr/local/bin/sentinel-auth-agent" "--socket" "/tmp/auth.sock"
        unix-socket "/tmp/auth.sock"
        events "request_headers"
        timeout-ms 50
        failure-mode "closed"
        restart-policy "always"
        max-restarts 5
    }

    agent "waf" type="waf" {
        command "/usr/local/bin/sentinel-waf-agent" "--grpc" "127.0.0.1:50051"
        grpc "http://127.0.0.1:50051"
        events "request_headers" "request_body"
        timeout-ms 100
        failure-mode "open"
        restart-policy "on-failure"
    }
}

upstreams {
    upstream "api" {
        targets "127.0.0.1:3001" "127.0.0.1:3002"
        load-balancer "round-robin"
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

## When to Use sentinel-stack

**Good for:**
- Development and testing
- Single-server deployments
- Quick demos and prototypes
- CI/CD testing pipelines

**Consider alternatives for:**
- Production with strict uptime requirements (use systemd)
- Multi-server deployments (use Kubernetes)
- When you need advanced process supervision features
- When agents need different resource limits

## Migrating to Production

When moving from `sentinel-stack` to production deployment:

1. **Extract the config** — Remove `command`, `restart-policy`, `env` directives
2. **Create systemd units** — One per agent plus Sentinel
3. **Set up monitoring** — Prometheus/Grafana for metrics
4. **Configure logging** — journald or central logging

See [systemd deployment](../systemd/) for the production setup.

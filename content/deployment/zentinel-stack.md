+++
title = "zentinel-stack"
weight = 2
updated = 2026-10-18
+++

`zentinel-stack` is a lightweight launcher that runs Zentinel and its agents as a single command. It's designed for development and simple deployments where full process supervision isn't needed.

## Overview

```
zentinel-stack
    │
    ├── Spawns zentinel (proxy)
    ├── Spawns each configured agent
    ├── Monitors and restarts crashed processes
    └── Forwards signals for graceful shutdown
```

## Installation

`zentinel-stack` lives in the Zentinel repository (`crates/stack`) but is not
published to crates.io and is not part of the release archives, which ship
`zentinel`, `zentinel-gateway` and `zentinel-echo-agent`. Build it from source
(Rust 1.96 or later):

```bash
# Install straight from the repository
cargo install --locked --git https://github.com/zentinelproxy/zentinel zentinel-stack

# Or from a clone
git clone https://github.com/zentinelproxy/zentinel.git
cd zentinel
cargo build --release -p zentinel-stack
# binary: target/release/zentinel-stack
```

The proxy itself installs with `curl -fsSL https://get.zentinelproxy.io | sh`
(see [Installation](@/getting-started/installation.md)).

## Quick Start

```bash
# Create a simple config
cat > zentinel.kdl << 'EOF'
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
    agent "echo" type="custom" {
        command "zentinel-echo-agent" "--socket" "/tmp/echo.sock"
        unix-socket "/tmp/echo.sock"
        events "request_headers"
    }
}

upstreams {
    upstream "backend" {
        target "127.0.0.1:3000"
    }
}

filters {
    filter "echo" {
        type "agent"
        agent "echo"
    }
}

routes {
    route "all" {
        matches { path-prefix "/" }
        upstream "backend"
        filters "echo"
    }
}
EOF

# Start everything
zentinel-stack --config zentinel.kdl
```

## Configuration

### Agent Commands

When using `zentinel-stack`, agents include a `command` directive. These
process-management directives (`command`, `restart-policy`,
`restart-delay-ms`, `max-restarts`, `env`) are read only by `zentinel-stack`;
the proxy ignores them, and `zentinel lint` lists them as ignored settings.

<!-- fragment: command, restart-policy, restart-delay-ms, max-restarts and env
     are read by zentinel-stack (crates/stack/src/main.rs) and ignored by the
     proxy, so `zentinel lint` reports them as ignored settings. -->
```fragment,kdl
agents {
    agent "auth" type="auth" {
        // Command to spawn the agent
        command "zentinel-auth-agent" "--socket" "/tmp/auth.sock"

        // Connection details (same as standalone Zentinel)
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
        command "zentinel-waf-agent" "--grpc" "127.0.0.1:50051"
        grpc "http://127.0.0.1:50051"
        events "request_headers" "request_body"

        restart-policy "on-failure"
        restart-delay-ms 2000
    }

    agent "external" type="custom" {
        // No command = external agent (not managed by zentinel-stack)
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

Pass environment to agents. A value written exactly as `"${NAME}"` is
replaced with that environment variable of the `zentinel-stack` process:

<!-- fragment: command, restart-policy, restart-delay-ms, max-restarts and env
     are read by zentinel-stack (crates/stack/src/main.rs) and ignored by the
     proxy, so `zentinel lint` reports them as ignored settings. -->
```fragment,kdl
agent "auth" type="auth" {
    command "zentinel-auth-agent" "--socket" "/tmp/auth.sock"
    unix-socket "/tmp/auth.sock"

    env {
        AUTH_SECRET "${AUTH_SECRET}"
        LOG_LEVEL "debug"
        CONFIG_PATH "/etc/auth/config.toml"
    }
}
```

## CLI Reference

```bash
zentinel-stack [OPTIONS]

Options:
    -c, --config <PATH>     Config file path [default: zentinel.kdl]
    -l, --log-level <LVL>   Log level [default: info]
    --proxy-only            Start only the proxy (no agents)
    --agents-only           Start only agents (no proxy)
    --dry-run               Validate config and exit
    --shutdown-timeout <S>  Shutdown timeout in seconds [default: 30]
    --startup-timeout <S>   Startup timeout in seconds [default: 10]
    -h, --help              Print help
    -V, --version           Print version
```

### Examples

```bash
# Standard startup
zentinel-stack --config zentinel.kdl

# Debug logging
zentinel-stack -l debug

# Validate configuration
zentinel-stack --dry-run

# Start only proxy (agents managed externally)
zentinel-stack --proxy-only

# Start only agents (proxy managed externally)
zentinel-stack --agents-only
```

## Process Management

### Startup Sequence

1. Parse and validate configuration
2. Spawn agents in dependency order
3. Wait for agent sockets/ports to be ready
4. Start Zentinel proxy
5. Begin accepting traffic

### Shutdown Sequence

On SIGTERM or SIGINT:
1. Stop accepting new connections
2. Send SIGTERM to proxy (graceful drain)
3. Wait for in-flight requests (configurable timeout)
4. Send SIGTERM to agents
5. Exit

The timeouts are command-line flags, not configuration (there is no `stack`
block):

```bash
zentinel-stack --shutdown-timeout 30 --startup-timeout 10
```

### Health Monitoring

`zentinel-stack` does not serve a health endpoint of its own. It restarts
agents according to their `restart-policy` and logs each start, exit and
restart; use the proxy's own health and metrics endpoints for the traffic side.

## Logging

All output is unified through `zentinel-stack`:

```bash
zentinel-stack --config zentinel.kdl 2>&1 | jq
```

```json
{"timestamp":"2025-12-29T10:00:00Z","level":"INFO","component":"stack","message":"Starting zentinel-stack"}
{"timestamp":"2025-12-29T10:00:00Z","level":"INFO","component":"agent:auth","message":"Agent started","pid":1234}
{"timestamp":"2025-12-29T10:00:00Z","level":"INFO","component":"agent:waf","message":"Agent started","pid":1235}
{"timestamp":"2025-12-29T10:00:00Z","level":"INFO","component":"proxy","message":"Listening on 0.0.0.0:8080"}
```

## Example Configurations

### Development Setup

<!-- fragment: command, restart-policy, restart-delay-ms, max-restarts and env
     are read by zentinel-stack (crates/stack/src/main.rs) and ignored by the
     proxy, so `zentinel lint` reports them as ignored settings. -->
```fragment,kdl
// dev.kdl - Simple development config
system {
    worker-threads 0
}

listeners {
    listener "http" {
        address "127.0.0.1:8080"
        protocol "http"
    }
}

observability {
    metrics {
        enabled #true
        address "127.0.0.1:9090"
    }
}

agents {
    agent "echo" type="custom" {
        command "cargo" "run" "--release" "-p" "zentinel-echo-agent" "--" "--socket" "/tmp/echo.sock"
        unix-socket "/tmp/echo.sock"
        events "request_headers"
        restart-policy "always"
    }
}

filters {
    filter "echo" {
        type "agent"
        agent "echo"
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
        filters "echo"
    }
}
```

### Production-like Local

<!-- fragment: command, restart-policy, restart-delay-ms, max-restarts and env
     are read by zentinel-stack (crates/stack/src/main.rs) and ignored by the
     proxy, so `zentinel lint` reports them as ignored settings. -->
```fragment,kdl
// local-prod.kdl - Production-like but local
// Run with: zentinel-stack --config local-prod.kdl --shutdown-timeout 30
system {
    worker-threads 0
}

listeners {
    listener "http" {
        address "0.0.0.0:8080"
        protocol "http"
    }
}

observability {
    metrics {
        enabled #true
        address "127.0.0.1:9090"
    }
}

agents {
    agent "auth" type="auth" {
        command "/usr/local/bin/zentinel-auth-agent" "--socket" "/tmp/auth.sock"
        unix-socket "/tmp/auth.sock"
        events "request_headers"
        timeout-ms 50
        failure-mode "closed"
        restart-policy "always"
        max-restarts 5
    }

    agent "waf" type="waf" {
        command "/usr/local/bin/zentinel-waf-agent" "--grpc" "127.0.0.1:50051"
        grpc "http://127.0.0.1:50051"
        events "request_headers" "request_body"
        timeout-ms 100
        failure-mode "open"
        restart-policy "on-failure"
    }
}

filters {
    filter "auth" {
        type "agent"
        agent "auth"
    }
    filter "waf" {
        type "agent"
        agent "waf"
    }
}

upstreams {
    upstream "api" {
        target "127.0.0.1:3001"
        target "127.0.0.1:3002"
        load-balancing "round_robin"
        health-check {
            type "http" {
                path "/health"
            }
            interval-secs 5
        }
    }
}

routes {
    route "api" {
        matches { path-prefix "/api/" }
        upstream "api"
        filters "auth" "waf"
    }
}
```

## When to Use zentinel-stack

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

When moving from `zentinel-stack` to production deployment:

1. **Extract the config** — Remove `command`, `restart-policy`, `env` directives
2. **Create systemd units** — One per agent plus Zentinel
3. **Set up monitoring** — Prometheus/Grafana for metrics
4. **Configure logging** — journald or central logging

See [systemd deployment](../systemd/) for the production setup.

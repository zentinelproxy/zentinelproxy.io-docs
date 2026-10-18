+++
title = "Environment Variables"
weight = 2
updated = 2026-10-18
+++

Environment variables for configuring Zentinel and its agents.

## Zentinel Proxy

### Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `ZENTINEL_CONFIG` | Path to configuration file | None (uses embedded default) |

### Logging

| Variable | Description | Default |
|----------|-------------|---------|
| `RUST_LOG` | Log level filter (trace, debug, info, warn, error) | `info` |
| `ZENTINEL_LOG_FORMAT` | Log output format (`json` or `pretty`) | `json` |

**Examples:**

```bash
# Set log level
export RUST_LOG=debug
export RUST_LOG=zentinel=debug,pingora=info

# Use pretty format for development
export ZENTINEL_LOG_FORMAT=pretty
```

### Log Level Syntax

The `RUST_LOG` variable supports fine-grained control:

```bash
# Global level
RUST_LOG=debug

# Per-module level
RUST_LOG=zentinel=debug,pingora=warn

# With target filtering
RUST_LOG=zentinel::proxy=trace,zentinel::agents=debug
```

## Configuration Overrides

There are none: settings such as `worker-threads` and `max-connections` are
read only from the configuration file. (Earlier versions of this page listed
`ZENTINEL_WORKERS` and `ZENTINEL_MAX_CONNECTIONS`; nothing reads them.)

### Other variables the proxy reads

| Variable | Description |
|----------|-------------|
| `ZENTINEL_ZONE` (then `ZONE`, then `REGION`) | This proxy's zone for `locality_aware` load balancing |
| `ZENTINEL_API_URL` | Override the API endpoint `zentinel bundle` fetches the agent bundle from |

## Agent Environment Variables

### Echo Agent

| Variable | Description | Default |
|----------|-------------|---------|
| `ECHO_AGENT_SOCKET` | Unix socket path | `/tmp/echo-agent.sock` |
| `ECHO_AGENT_GRPC` | gRPC address (alternative to socket) | None |
| `ECHO_AGENT_LOG_LEVEL` | Log level | `info` |
| `ECHO_AGENT_PREFIX` | Header prefix for echo headers | `X-Echo-` |
| `ECHO_AGENT_VERBOSE` | Enable verbose output | `false` |

### Rate Limit Agent

| Variable | Description | Default |
|----------|-------------|---------|
| `RATELIMIT_AGENT_SOCKET` | Unix socket path | `/tmp/ratelimit-agent.sock` |
| `RATELIMIT_AGENT_CONFIG` | Rate limit configuration file | None |
| `RATELIMIT_AGENT_LOG_LEVEL` | Log level | `info` |
| `RATELIMIT_AGENT_DEFAULT_RPS` | Default requests per second | `100` |
| `RATELIMIT_AGENT_DEFAULT_BURST` | Default burst size | `200` |
| `RATELIMIT_AGENT_DRY_RUN` | Log decisions without enforcing | `false` |
| `RATELIMIT_AGENT_CLEANUP_INTERVAL` | Cleanup interval (seconds) | `60` |

### Custom Agents

When building custom agents using the agent template:

| Variable | Description | Default |
|----------|-------------|---------|
| `AGENT_SOCKET` | Unix socket path | `/tmp/{agent-name}.sock` |
| `AGENT_LOG_LEVEL` | Log level | `info` |

## Docker Environment

When running Zentinel in Docker, pass environment variables:

```bash
docker run -d \
  -e ZENTINEL_CONFIG=/etc/zentinel/zentinel.kdl \
  -e RUST_LOG=info \
  -e ZENTINEL_LOG_FORMAT=json \
  -v /path/to/config:/etc/zentinel \
  zentinel:latest
```

Docker Compose:

```yaml
services:
  zentinel:
    image: zentinel:latest
    environment:
      - ZENTINEL_CONFIG=/etc/zentinel/zentinel.kdl
      - RUST_LOG=info
      - ZENTINEL_LOG_FORMAT=json
    volumes:
      - ./config:/etc/zentinel:ro
```

## Kubernetes Environment

Use ConfigMaps and Secrets for environment variables:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: zentinel-config
data:
  RUST_LOG: "info"
  ZENTINEL_LOG_FORMAT: "json"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: zentinel
spec:
  template:
    spec:
      containers:
        - name: zentinel
          envFrom:
            - configMapRef:
                name: zentinel-config
```

## systemd Environment

For systemd services, use an environment file:

**/etc/zentinel/environment:**
```bash
ZENTINEL_CONFIG=/etc/zentinel/zentinel.kdl
RUST_LOG=info
ZENTINEL_LOG_FORMAT=json
```

**/etc/systemd/system/zentinel.service:**
```ini
[Service]
EnvironmentFile=/etc/zentinel/environment
ExecStart=/usr/local/bin/zentinel
```

## Precedence

Configuration values are resolved in this order (highest to lowest priority):

1. Command-line arguments
2. Environment variables
3. Configuration file values
4. Default values

## Debugging Environment Issues

Check which environment variables are set:

```bash
# Linux/macOS
env | grep -E '^(ZENTINEL|RUST_LOG)'

# Show effective configuration
zentinel --test --verbose --config zentinel.kdl
```

## Security Considerations

- Avoid storing secrets in environment variables when possible
- Use Docker/Kubernetes secrets for sensitive values
- Environment variables may be visible in process listings
- Consider using configuration files with appropriate permissions for secrets

## See Also

- [CLI Reference](../cli/) - Command-line options
- [Configuration](../../configuration/) - Configuration file format

+++
title = "Environment Variables"
weight = 2
+++

Environment variables for configuring Sentinel and its agents.

## Sentinel Proxy

### Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `SENTINEL_CONFIG` | Path to configuration file | None (uses embedded default) |

### Logging

| Variable | Description | Default |
|----------|-------------|---------|
| `RUST_LOG` | Log level filter (trace, debug, info, warn, error) | `info` |
| `SENTINEL_LOG_FORMAT` | Log output format (`json` or `pretty`) | `json` |

**Examples:**

```bash
# Set log level
export RUST_LOG=debug
export RUST_LOG=sentinel=debug,pingora=info

# Use pretty format for development
export SENTINEL_LOG_FORMAT=pretty
```

### Log Level Syntax

The `RUST_LOG` variable supports fine-grained control:

```bash
# Global level
RUST_LOG=debug

# Per-module level
RUST_LOG=sentinel=debug,pingora=warn

# With target filtering
RUST_LOG=sentinel::proxy=trace,sentinel::agents=debug
```

## Configuration Overrides

Some configuration settings can be overridden via environment variables. Environment variables take precedence over config file values.

| Variable | Config Setting | Description |
|----------|----------------|-------------|
| `SENTINEL_WORKERS` | `server.worker-threads` | Number of worker threads |
| `SENTINEL_MAX_CONNECTIONS` | `server.max-connections` | Maximum connections |

**Example:**

```bash
# Override worker threads regardless of config file
export SENTINEL_WORKERS=8
sentinel --config sentinel.kdl
```

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

When running Sentinel in Docker, pass environment variables:

```bash
docker run -d \
  -e SENTINEL_CONFIG=/etc/sentinel/sentinel.kdl \
  -e RUST_LOG=info \
  -e SENTINEL_LOG_FORMAT=json \
  -v /path/to/config:/etc/sentinel \
  sentinel:latest
```

Docker Compose:

```yaml
services:
  sentinel:
    image: sentinel:latest
    environment:
      - SENTINEL_CONFIG=/etc/sentinel/sentinel.kdl
      - RUST_LOG=info
      - SENTINEL_LOG_FORMAT=json
    volumes:
      - ./config:/etc/sentinel:ro
```

## Kubernetes Environment

Use ConfigMaps and Secrets for environment variables:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: sentinel-config
data:
  RUST_LOG: "info"
  SENTINEL_LOG_FORMAT: "json"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sentinel
spec:
  template:
    spec:
      containers:
        - name: sentinel
          envFrom:
            - configMapRef:
                name: sentinel-config
```

## systemd Environment

For systemd services, use an environment file:

**/etc/sentinel/environment:**
```bash
SENTINEL_CONFIG=/etc/sentinel/sentinel.kdl
RUST_LOG=info
SENTINEL_LOG_FORMAT=json
```

**/etc/systemd/system/sentinel.service:**
```ini
[Service]
EnvironmentFile=/etc/sentinel/environment
ExecStart=/usr/local/bin/sentinel
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
env | grep -E '^(SENTINEL|RUST_LOG)'

# Show effective configuration
sentinel --test --verbose --config sentinel.kdl
```

## Security Considerations

- Avoid storing secrets in environment variables when possible
- Use Docker/Kubernetes secrets for sensitive values
- Environment variables may be visible in process listings
- Consider using configuration files with appropriate permissions for secrets

## See Also

- [CLI Reference](../cli/) - Command-line options
- [Configuration](../../configuration/) - Configuration file format

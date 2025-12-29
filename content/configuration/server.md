+++
title = "Server"
weight = 2
+++

The `server` block configures global proxy settings including worker threads, connection limits, and process management.

## Basic Configuration

```kdl
server {
    worker-threads 0              // 0 = auto-detect CPU cores
    max-connections 10000
    graceful-shutdown-timeout-secs 30
}
```

## Options Reference

### Worker Threads

```kdl
server {
    worker-threads 0
}
```

| Value | Behavior |
|-------|----------|
| `0` | Auto-detect (number of CPU cores) |
| `1-N` | Fixed number of worker threads |

**Recommendations:**
- **General purpose**: `0` (auto-detect)
- **CPU-bound workloads**: Number of CPU cores
- **I/O-bound workloads**: 2× number of CPU cores
- **Testing**: `1` for predictable behavior

### Connection Limits

```kdl
server {
    max-connections 10000
}
```

Maximum total concurrent connections across all listeners. When reached, new connections are rejected.

**Sizing guidelines:**

| Deployment | Suggested Value |
|------------|-----------------|
| Development | 1000 |
| Small production | 10000 |
| Large production | 50000+ |

Memory impact: ~10KB per connection.

### Graceful Shutdown

```kdl
server {
    graceful-shutdown-timeout-secs 30
}
```

When Sentinel receives SIGTERM or SIGINT:

1. Stop accepting new connections
2. Wait for in-flight requests to complete
3. After timeout, forcefully close remaining connections

**Default**: 30 seconds

### Trace ID Format

```kdl
server {
    trace-id-format "tinyflake"  // or "uuid"
}
```

Format for request correlation IDs:

| Format | Example | Length | Notes |
|--------|---------|--------|-------|
| `tinyflake` | `2kF8xQw4BnM` | 11 chars | Default, operator-friendly |
| `uuid` | `550e8400-e29b-41d4-a716-446655440000` | 36 chars | Standard UUID v4 |

Trace IDs appear in:
- Request headers (`X-Correlation-Id`)
- Response headers
- Access logs
- Error logs

### Auto Reload

```kdl
server {
    auto-reload true
}
```

When enabled, Sentinel watches the configuration file and automatically reloads on changes.

**Default**: `false`

Reload triggers:
- File modification
- File creation (if watching a directory)

## Process Management

### Daemon Mode

```kdl
server {
    daemon true
    pid-file "/var/run/sentinel.pid"
}
```

Run Sentinel as a background daemon:
- Detaches from terminal
- Writes PID to file for process management

### User/Group

```kdl
server {
    user "sentinel"
    group "sentinel"
}
```

Drop privileges after binding to ports. Useful when binding to privileged ports (< 1024):

1. Start as root to bind port 443
2. Drop to unprivileged user for request handling

**Security best practice**: Always run as non-root in production.

### Working Directory

```kdl
server {
    working-directory "/var/lib/sentinel"
}
```

Change working directory after startup. Affects relative paths in configuration.

## Complete Example

```kdl
server {
    // Performance
    worker-threads 0
    max-connections 50000

    // Shutdown
    graceful-shutdown-timeout-secs 60

    // Observability
    trace-id-format "uuid"

    // Hot reload
    auto-reload true

    // Process management (production)
    daemon true
    pid-file "/var/run/sentinel.pid"
    user "sentinel"
    group "sentinel"
    working-directory "/var/lib/sentinel"
}
```

## Environment Variables

Server settings can be overridden via environment variables:

| Variable | Setting |
|----------|---------|
| `SENTINEL_WORKERS` | `worker-threads` |
| `SENTINEL_MAX_CONNECTIONS` | `max-connections` |

Environment variables take precedence over config file values.

## Default Values

| Setting | Default |
|---------|---------|
| `worker-threads` | `0` (auto) |
| `max-connections` | `10000` |
| `graceful-shutdown-timeout-secs` | `30` |
| `trace-id-format` | `tinyflake` |
| `auto-reload` | `false` |
| `daemon` | `false` |

## Tuning for Production

### High-Traffic Deployment

```kdl
server {
    worker-threads 0           // Use all cores
    max-connections 100000     // High connection limit
    graceful-shutdown-timeout-secs 120  // Long drain time
}
```

### Resource-Constrained Environment

```kdl
server {
    worker-threads 2           // Limited threads
    max-connections 5000       // Lower limit
    graceful-shutdown-timeout-secs 15   // Quick shutdown
}
```

## Signals

| Signal | Behavior |
|--------|----------|
| `SIGTERM` | Graceful shutdown |
| `SIGINT` | Graceful shutdown |
| `SIGHUP` | Reload configuration |
| `SIGUSR1` | Reopen log files |

## Next Steps

- [Listeners](../listeners/) - Network binding and TLS
- [Limits](../limits/) - Request and connection limits

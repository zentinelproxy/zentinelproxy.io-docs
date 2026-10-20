+++
title = "Server"
weight = 2
updated = 2026-10-20
+++

The `system` block (formerly `server`) configures global proxy settings including worker threads, shutdown and process management.

## Basic Configuration

```kdl
system {
    worker-threads 0              // 0 = auto-detect CPU cores
    graceful-shutdown-timeout-secs 30
}
```

## Options Reference

### Worker Threads

```kdl
system {
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

Zentinel does not limit the number of client connections. `system {
max-connections }` is accepted but not applied; from 26.10_5 `zentinel test`
and `zentinel lint` report it ("…is not applied and is being ignored"), and
the shipped configurations no longer set it. Bound load with
[rate limits](../filters/#rate-limiting), and cap connections in front of the
proxy (a load balancer) or with the file descriptor limit (`ulimit -n`,
systemd `LimitNOFILE=`).

### Graceful Shutdown

```kdl
system {
    graceful-shutdown-timeout-secs 30
}
```

When Zentinel receives SIGTERM or SIGINT:

1. Stop accepting new connections
2. Wait for in-flight requests to complete
3. After timeout, forcefully close remaining connections

**Default**: 30 seconds

### Trace ID Format

```kdl
system {
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
listeners {
    listener "http" {
        address "0.0.0.0:8080"
        protocol "http"
    }
}

system {
    auto-reload #true
}

routes {
    route "default" {
        matches { path-prefix "/" }
        upstream "backend"
    }
}

upstreams {
    upstream "backend" {
        target "127.0.0.1:3000"
    }
}

```

When enabled, Zentinel watches the configuration file and automatically reloads on changes.

**Default**: `false`

Reload triggers:
- File modification
- File creation (if watching a directory)

Once a second the proxy also compares the content of every file the
configuration reads, included files too, with what the last reload read. From
26.10_7 one edit gives one reload, and saving a file without changing its
content does not reload. See [Hot Reload](/configuration/file-format/#hot-reload).

## Process Management

### Daemon Mode

```kdl
listeners {
    listener "http" {
        address "0.0.0.0:8080"
        protocol "http"
    }
}

system {
    daemon #true
    pid-file "/var/run/zentinel.pid"
}

routes {
    route "default" {
        matches { path-prefix "/" }
        upstream "backend"
    }
}

upstreams {
    upstream "backend" {
        target "127.0.0.1:3000"
    }
}

```

Run Zentinel as a background daemon:
- Detaches from terminal
- Writes PID to file for process management

From 26.10_5, `daemon #true` in the configuration daemonizes the proxy, as the
`-d` / `--daemon` flag does; either one is enough. Before 26.10_5 the
configuration value was not read and only the flag worked. Under systemd or in
a container, leave both off: the supervisor expects the process to stay in the
foreground.

### User/Group

```kdl
system {
    user "zentinel"
    group "zentinel"
}
```

Drop privileges after binding to ports. Useful when binding to privileged ports (< 1024):

1. Start as root to bind port 443
2. Drop to unprivileged user for request handling

**Security best practice**: Always run as non-root in production.

### Working Directory

```kdl
system {
    working-directory "/var/lib/zentinel"
}
```

Change working directory after startup. Affects relative paths in configuration.

## Complete Example

```kdl
listeners {
    listener "http" {
        address "0.0.0.0:8080"
        protocol "http"
    }
}

system {
    // Performance
    worker-threads 0

    // Shutdown
    graceful-shutdown-timeout-secs 60

    // Observability
    trace-id-format "uuid"

    // Hot reload
    auto-reload #true

    // Process management (production)
    daemon #true
    pid-file "/var/run/zentinel.pid"
    user "zentinel"
    group "zentinel"
    working-directory "/var/lib/zentinel"
}

routes {
    route "default" {
        matches { path-prefix "/" }
        upstream "backend"
    }
}

upstreams {
    upstream "backend" {
        target "127.0.0.1:3000"
    }
}

```

## Environment Variables

There are no environment-variable overrides for `system` settings; set them
in the configuration file. The variables Zentinel reads are listed in
[Environment Variables](@/reference/env-vars.md) (for example
`ZENTINEL_CONFIG` for the configuration path).

## Default Values

| Setting | Default |
|---------|---------|
| `worker-threads` | `0` (auto) |
| `graceful-shutdown-timeout-secs` | `30` |
| `trace-id-format` | `tinyflake` |
| `auto-reload` | `false` |
| `daemon` | `false` |

## Tuning for Production

### High-Traffic Deployment

```kdl
system {
    worker-threads 0           // Use all cores
    graceful-shutdown-timeout-secs 120  // Long drain time
}
```

### Resource-Constrained Environment

```kdl
system {
    worker-threads 2           // Limited threads
    graceful-shutdown-timeout-secs 15   // Quick shutdown
}
```

## Signals

| Signal | Behavior |
|--------|----------|
| `SIGTERM` | Graceful shutdown |
| `SIGINT` | Graceful shutdown |
| `SIGHUP` | Reload configuration |

## Next Steps

- [Listeners](../listeners/) - Network binding and TLS
- [Limits](../limits/) - Request and connection limits

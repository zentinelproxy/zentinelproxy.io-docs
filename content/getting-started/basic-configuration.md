+++
title = "Basic Configuration"
weight = 5
updated = 2026-10-19
+++

Zentinel uses [KDL](https://kdl.dev) (KDL Document Language) as its primary configuration format. KDL is a human-friendly document language with a clean syntax that's easy to read and write.

Everything on this page describes release 26.10_5. Settings that are accepted but not applied are listed in [Known Limitations](/reference/known-limitations/).

## Minimal Configuration

Here's the simplest configuration that gets Zentinel running as a reverse proxy:

```kdl
system {
    worker-threads 0
}

listeners {
    listener "http" {
        address "0.0.0.0:8080"
        protocol "http"
    }
}

routes {
    route "default" {
        matches {
            path-prefix "/"
        }
        upstream "backend"
    }
}

upstreams {
    upstream "backend" {
        target "127.0.0.1:3000"
    }
}
```

This configuration:
- Starts Zentinel on port 8080
- Forwards all requests to a backend service on port 3000
- Uses automatic worker thread detection

Check a configuration before you run it. `zentinel test` loads and validates it and, from 26.10_5, warns about settings that are misspelled or in the wrong block (`--strict` makes them fatal); `zentinel lint` reports the same settings and adds best-practice advice:

```bash
zentinel test -c zentinel.kdl
zentinel lint -c zentinel.kdl
```

## Configuration Sections

A Zentinel configuration file consists of several top-level sections:

| Section | Required | Description |
|---------|----------|-------------|
| `system` | Yes | Global process settings. `server` is a deprecated alias: it still loads, with a deprecation warning |
| `listeners` | Yes | Network listeners (at least one) |
| `routes` | No | Request routing rules |
| `upstreams` | No | Backend server pools |
| `filters` | No | Request/response processing |
| `agents` | No | External processor connections |
| `limits` | No | Resource limits |
| `observability` | No | Metrics, logging, and tracing |

Without a `system` (or `server`) block the file does not load: `Missing required 'system' configuration block`.

## System Configuration

The `system` block controls global behavior:

```kdl
system {
    worker-threads 4              // 0 = auto-detect CPU cores
    graceful-shutdown-timeout-secs 30
}
```

### System Options

| Option | Default | Description |
|--------|---------|-------------|
| `worker-threads` | `0` | Number of worker threads (0 = auto) |
| `graceful-shutdown-timeout-secs` | `30` | Seconds to wait for connections to drain |
| `pid-file` | - | Path to PID file |
| `auto-reload` | `false` | Reload config on file changes |
| `daemon` | `false` | Run in the background, like the `-d` / `--daemon` flag. Read from the file from 26.10_5; before, only the flag worked |

`max-connections` is not applied: Zentinel does not cap client connections, and from 26.10_5 `zentinel test` and `lint` report the key.

## Listeners

Listeners define how Zentinel accepts incoming connections:

```kdl
listeners {
    listener "http" {
        address "0.0.0.0:8080"
        protocol "http"
        request-timeout-secs 60
        keepalive-timeout-secs 75
    }
}
```

### Listener Options

| Option | Default | Description |
|--------|---------|-------------|
| `address` | - | Socket address (required) |
| `protocol` | `http` | `http`, `https` or `h2`. `h3` is rejected at validation: there is no QUIC support. An `https` listener negotiates HTTP/2 through ALPN |
| `request-timeout-secs` | `60` | Request timeout |
| `keepalive-timeout-secs` | `75` | Keep-alive timeout |
| `default-route` | - | Fallback route if no match |

### HTTPS Listener

For TLS, add a `tls` block:

```kdl
listeners {
    listener "https" {
        address "0.0.0.0:443"
        protocol "https"

        tls {
            cert-file "/etc/zentinel/certs/server.crt"
            key-file "/etc/zentinel/certs/server.key"
            min-version "TLS1.2"
        }
    }
}
```

## Routes

Routes match incoming requests and direct them to upstreams:

```kdl
routes {
    route "health" {
        priority "critical"

        matches {
            path "/health"
        }

        builtin-handler "health"
    }

    route "api" {
        priority "high"

        matches {
            path-prefix "/api/"
        }

        upstream "api-backend"
    }

    route "static" {
        priority "normal"

        matches {
            path-prefix "/static/"
        }

        static-files {
            root "/var/www/static"
            compress #true
        }
    }
}
```

A static route serves files from `root` with the full request path, prefix included: `/static/app.css` is read from `/var/www/static/static/app.css`.

### Priority

When more than one route matches a request, the route with the higher priority wins. `priority` takes an integer or one of four names:

| Name | Value |
|------|-------|
| `"low"` | `10` |
| `"normal"` | `50` (the default) |
| `"high"` | `100` |
| `"critical"` | `1000` |

Names are case-insensitive. An unrecognised name is not an error: it is treated as `"normal"`, and from 26.10_5 `zentinel test` and `lint` report it (before, there was no warning). Use an integer when you need a value between the named ones, for example `priority 200`.

### Match Conditions

All conditions in a `matches` block must hold for the route to match. The exception is `host`: several `host` lines are alternatives, and one of them must match.

| Condition | Example | Description |
|-----------|---------|-------------|
| `path-prefix` | `"/api/"` | URL path prefix. `"/api/"` does not match `/api`; `"/api"` matches `/api` and `/api/...` but not `/apiv2` |
| `path` | `"/health"` | Exact path match |
| `path-regex` | `"^/v[0-9]+/"` | Regex path match |
| `host` | `"api.example.com"` | Host header (`"*.example.com"` for subdomains) |
| `method` | `"GET"` | HTTP method. Takes one value: in `method "GET" "POST"` only `GET` is kept |
| `header` | `"Authorization"` or `"X-Env" "beta"` | Header present, or header equal to the value (exact comparison, no wildcards) |
| `query-param` | `"key"` or `"key" "value"` | Query parameter present, or equal to the value |

### Service Types

| Type | Description |
|------|-------------|
| `web` | Traditional web service (default) |
| `api` | Route with an `api-schema` block (request validation) |
| `static` | Route with a `static-files` block |
| `builtin` | Route with a `builtin-handler` (`health`, `status`, `metrics`, `config`, `upstreams`, `not-found`, `cache-stats`, `cache-purge`) |
| `inference` | Route with an `inference` block |

The type is implied by the route's blocks, as listed above. An explicit `service-type` is applied where the blocks allow it: `service-type "api"` works on any route, while `static`, `builtin` and `inference` need their block. A value the blocks contradict keeps the implied type, and `zentinel lint` reports it. (Before 26.10_4, `service-type` was not read at all.)

A builtin route needs `builtin-handler`. `service-type "builtin"` on its own gives a route with no handler and no upstream, which answers every request with `500 Internal Server Error`.

## Upstreams

Upstreams define backend server pools:

```kdl
upstreams {
    upstream "backend" {
        target "10.0.1.10:8080" weight=3
        target "10.0.1.11:8080" weight=1

        load-balancing "weighted"

        health-check {
            type "http" {
                path "/health"
                expected-status 200
            }
            interval-secs 10
            timeout-secs 5
            healthy-threshold 2
            unhealthy-threshold 3
        }
    }
}
```

The default `round_robin` ignores `weight`: targets take turns regardless. To split traffic by weight, set `load-balancing "weighted"` as above.

### Load Balancing Algorithms

| Algorithm | Description |
|-----------|-------------|
| `round_robin` | Sequential distribution (default) |
| `weighted` | Distribution in proportion to target `weight` |
| `least_connections` | Fewest active connections |
| `ip_hash` | Client IP sticky sessions |
| `consistent_hash` | Consistent hashing |
| `p2c` | Power of Two Choices |

From 26.10_5 the names can be spelled with hyphens or underscores (`"least-connections"` or `"least_connections"`). An unrecognised name still falls back to `round_robin`, and `zentinel test` and `lint` report it. Before 26.10_5 a hyphenated name silently became `round_robin`, so use underscores on older releases. The full list is in [Upstreams](/configuration/upstreams/).

## Resource Limits

Control resource usage with the `limits` block:

```kdl
limits {
    max-header-size 8192
    max-header-count 100
    max-body-size 10485760    // 10MB
}
```

These names have no `-bytes` suffix. `max-header-size-bytes` and `max-body-size-bytes` are ignored in a configuration file; from 26.10_5 `zentinel test` and `zentinel lint` report them ("Did you mean 'max-body-size'?"). See [Limits](/configuration/limits/).

A request body over `max-body-size`, or over a route's `policies { max-body-size }`, is rejected with `413 Payload Too Large`. Before 26.10_5 it got a `500`, a route's own limit was not enforced, and `max-body-size` could not be set below 1048576 (1 MiB).

## Observability

Enable metrics:

```kdl
observability {
    metrics {
        enabled #true
        address "0.0.0.0:9090"
        path "/metrics"
    }
}
```

The proxy writes its own log to stdout/stderr as plain text. The level is `info`, or `debug` with `--verbose`; set `RUST_LOG` (for example `RUST_LOG=warn`) to choose another. `logging { level }` and `logging { format }` are accepted but do not change the output: a value other than `"info"` / `"json"` only produces an "Unwired feature" warning at startup.

> **Note:** Error logging to `/var/log/zentinel/error.log` is enabled by default at `warn` level. If the proxy cannot create `/var/log/zentinel` (for example when it runs as an unprivileged user), it logs `Failed to initialize log manager, file logging disabled` and continues without log files. See [Observability](/configuration/observability/) for the file locations.

## Complete Example

Here's a fuller configuration:

```kdl
system {
    worker-threads 0
    graceful-shutdown-timeout-secs 30
}

listeners {
    listener "http" {
        address "0.0.0.0:8080"
        protocol "http"
        request-timeout-secs 60
    }
}

routes {
    route "api" {
        priority "high"
        matches {
            path-prefix "/api/"
        }
        upstream "api-backend"
        policies {
            timeout-secs 30
        }
    }

    route "default" {
        priority "low"
        matches {
            path-prefix "/"
        }
        upstream "web-backend"
    }
}

upstreams {
    upstream "api-backend" {
        target "127.0.0.1:3000"
        load-balancing "round_robin"
        health-check {
            type "http" {
                path "/health"
            }
            interval-secs 10
        }
    }

    upstream "web-backend" {
        target "127.0.0.1:3001"
    }
}

limits {
    max-header-size 8192
    max-body-size 10485760
}

observability {
    metrics {
        enabled #true
        address "0.0.0.0:9090"
    }
}
```

## Next Steps

- [First Route](../first-route/) - Create your first routing rule
- [Installation](../installation/) - Install Zentinel
- [Configuration Reference](/configuration/) - Full configuration options
- [Known Limitations](/reference/known-limitations/) - Settings that are accepted but not applied

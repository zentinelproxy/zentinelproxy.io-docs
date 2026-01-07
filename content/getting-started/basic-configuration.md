+++
title = "Basic Configuration"
weight = 2
+++

Sentinel uses [KDL](https://kdl.dev) (KDL Document Language) as its primary configuration format. KDL is a human-friendly document language with a clean syntax that's easy to read and write.

## Minimal Configuration

Here's the simplest configuration that gets Sentinel running as a reverse proxy:

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
        targets {
            target {
                address "127.0.0.1:3000"
            }
        }
    }
}
```

This configuration:
- Starts Sentinel on port 8080
- Forwards all requests to a backend service on port 3000
- Uses automatic worker thread detection

## Configuration Sections

A Sentinel configuration file consists of several top-level sections:

| Section | Required | Description |
|---------|----------|-------------|
| `server` | Yes | Global server settings |
| `listeners` | Yes | Network listeners (at least one) |
| `routes` | No | Request routing rules |
| `upstreams` | No | Backend server pools |
| `filters` | No | Request/response processing |
| `agents` | No | External processor connections |
| `limits` | No | Resource limits |
| `observability` | No | Metrics, logging, and tracing |

## Server Configuration

The `server` block controls global behavior:

```kdl
system {
    worker-threads 4              // 0 = auto-detect CPU cores
    max-connections 10000         // Total connection limit
    graceful-shutdown-timeout-secs 30
}
```

### Server Options

| Option | Default | Description |
|--------|---------|-------------|
| `worker-threads` | `0` | Number of worker threads (0 = auto) |
| `max-connections` | `10000` | Maximum concurrent connections |
| `graceful-shutdown-timeout-secs` | `30` | Seconds to wait for connections to drain |
| `daemon` | `false` | Run as a background daemon |
| `pid-file` | - | Path to PID file |
| `auto-reload` | `false` | Reload config on file changes |

## Listeners

Listeners define how Sentinel accepts incoming connections:

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
| `protocol` | - | `http`, `https`, `h2`, or `h3` |
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
            cert-file "/etc/sentinel/certs/server.crt"
            key-file "/etc/sentinel/certs/server.key"
            min-version "TLS1.2"
        }
    }
}
```

## Routes

Routes match incoming requests and direct them to upstreams:

```kdl
routes {
    route "api" {
        priority "high"

        matches {
            path-prefix "/api/"
            method "GET" "POST" "PUT" "DELETE"
        }

        upstream "api-backend"
        service-type "api"
    }

    route "static" {
        priority "normal"

        matches {
            path-prefix "/static/"
        }

        service-type "static"
        static-files {
            root "/var/www/static"
            compress #true
        }
    }
}
```

### Match Conditions

| Condition | Example | Description |
|-----------|---------|-------------|
| `path-prefix` | `"/api/"` | URL path prefix |
| `path` | `"/health"` | Exact path match |
| `path-regex` | `"^/v[0-9]+/"` | Regex path match |
| `host` | `"api.example.com"` | Host header |
| `method` | `"GET" "POST"` | HTTP methods |
| `header` | `"Authorization" "Bearer *"` | Header match |
| `query-param` | `"key" "value"` | Query parameter |

### Service Types

| Type | Description |
|------|-------------|
| `web` | Traditional web service (default) |
| `api` | REST API with JSON error responses |
| `static` | Static file serving |
| `builtin` | Built-in handlers (health, metrics) |

## Upstreams

Upstreams define backend server pools:

```kdl
upstreams {
    upstream "backend" {
        targets {
            target {
                address "10.0.1.10:8080"
                weight 3
            }
            target {
                address "10.0.1.11:8080"
                weight 1
            }
        }

        load-balancing "round_robin"

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

### Load Balancing Algorithms

| Algorithm | Description |
|-----------|-------------|
| `round_robin` | Sequential distribution (default) |
| `least_connections` | Fewest active connections |
| `ip_hash` | Client IP sticky sessions |
| `consistent_hash` | Consistent hashing |
| `p2c` | Power of Two Choices |

## Resource Limits

Control resource usage with the `limits` block:

```kdl
limits {
    max-header-size-bytes 8192
    max-header-count 100
    max-body-size-bytes 10485760    // 10MB
    max-connections-per-client 100
}
```

## Observability

Enable metrics and logging:

```kdl
observability {
    metrics {
        enabled #true
        address "0.0.0.0:9090"
        path "/metrics"
    }

    logging {
        level "info"           // trace, debug, info, warn, error
        format "json"          // json or pretty
    }
}
```

## Complete Example

Here's a production-ready configuration:

```kdl
system {
    worker-threads 0
    max-connections 10000
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
        service-type "api"
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
        targets {
            target { address "127.0.0.1:3000" }
        }
        load-balancing "round_robin"
        health-check {
            type "http" {
                path "/health"
            }
            interval-secs 10
        }
    }

    upstream "web-backend" {
        targets {
            target { address "127.0.0.1:3001" }
        }
    }
}

limits {
    max-header-size-bytes 8192
    max-body-size-bytes 10485760
}

observability {
    metrics {
        enabled #true
        address "0.0.0.0:9090"
    }
    logging {
        level "info"
        format "json"
    }
}
```

## Next Steps

- [First Route](../first-route/) - Create your first routing rule
- [Installation](../installation/) - Install Sentinel
- [Configuration Reference](/configuration/overview/) - Full configuration options

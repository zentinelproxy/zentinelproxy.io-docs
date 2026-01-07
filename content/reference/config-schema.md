+++
title = "Configuration Schema"
weight = 5
+++

Quick reference for all Sentinel configuration options.

## Top-Level Blocks

```kdl
system { }       // Server settings
listeners { }    // Network listeners
routes { }       // Request routing
upstreams { }    // Backend servers
agents { }       // External processors
limits { }       // Request limits
```

## Server Block

```kdl
listeners {
    listener "http" {
        address "0.0.0.0:8080"
        protocol "http"
    }
}

system {
    worker-threads 0                      // 0 = auto (CPU cores)
    max-connections 10000
    graceful-shutdown-timeout-secs 30
    trace-id-format "tinyflake"           // or "uuid"
    auto-reload #false

    // Process management
    daemon #false
    pid-file "/var/run/sentinel.pid"
    user "sentinel"
    group "sentinel"
    working-directory "/var/lib/sentinel"
}

routes {
    route "default" {
        matches { path-prefix "/" }
        upstream "backend"
    }
}

upstreams {
    upstream "backend" {
        targets {
            target { address "127.0.0.1:3000" }
        }
    }
}
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `worker-threads` | int | `0` | Worker threads (0=auto) |
| `max-connections` | int | `10000` | Maximum connections |
| `graceful-shutdown-timeout-secs` | int | `30` | Shutdown timeout |
| `trace-id-format` | string | `tinyflake` | Trace ID format |
| `auto-reload` | bool | `false` | Watch config for changes |
| `daemon` | bool | `false` | Run as daemon |
| `pid-file` | path | - | PID file path |
| `user` | string | - | Drop privileges to user |
| `group` | string | - | Drop privileges to group |
| `working-directory` | path | - | Working directory |

## Listeners Block

```kdl
system {
    worker-threads 0
}

listeners {
    listener "id" {
        address "0.0.0.0:8080"
        protocol "http"                    // http, https, h2, h3
        request-timeout-secs 60
        keepalive-timeout-secs 75
        max-concurrent-streams 100
        default-route "fallback"

        tls {
            cert-file "/path/to/cert.pem"
            key-file "/path/to/key.pem"
            ca-file "/path/to/ca.pem"
            min-version "1.2"
            max-version "1.3"
            client-auth #false
            ocsp-stapling #true
            session-resumption #true
            cipher-suites "..."
        }
    }
}

routes {
    route "default" {
        matches { path-prefix "/" }
        upstream "backend"
    }
}

upstreams {
    upstream "backend" {
        targets {
            target { address "127.0.0.1:3000" }
        }
    }
}
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `address` | string | Required | Bind address (host:port) |
| `protocol` | string | Required | Protocol type |
| `request-timeout-secs` | int | `60` | Request timeout |
| `keepalive-timeout-secs` | int | `75` | Keep-alive timeout |
| `max-concurrent-streams` | int | `100` | HTTP/2 max streams |
| `default-route` | string | - | Default route ID |

### TLS Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `cert-file` | path | Required | Certificate file |
| `key-file` | path | Required | Private key file |
| `ca-file` | path | - | CA for client auth |
| `min-version` | string | `1.2` | Minimum TLS version |
| `max-version` | string | - | Maximum TLS version |
| `client-auth` | bool | `false` | Require client certs |
| `ocsp-stapling` | bool | `true` | Enable OCSP stapling |
| `session-resumption` | bool | `true` | Enable session tickets |
| `cipher-suites` | list | - | Allowed cipher suites |

## Routes Block

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
    route "id" {
        priority 100
        matches {
            path "/exact"
            path-prefix "/api/"
            path-regex "^/user/[0-9]+$"
            host "api.example.com"
            method "GET" "POST"
            header name="X-Key" value="..."
            query-param name="format" value="json"
        }
        upstream "backend"
        service-type "web"                 // web, api, static, builtin
        builtin-handler "health"           // For service-type=builtin
        filters "auth" "ratelimit"
        waf-enabled #false

        policies {
            timeout-secs 30
            max-body-size "10MB"
            failure-mode "closed"          // closed, open
            buffer-requests #false
            buffer-responses #false

            request-headers {
                set { "X-Header" "value" }
                add { "X-Header" "value" }
                remove "X-Internal"
            }
            response-headers {
                set { "X-Frame-Options" "DENY" }
                remove "Server"
            }
            rate-limit {
                requests-per-second 100
                burst 500
                key "client_ip"
            }
        }

        retry-policy {
            max-attempts 3
            timeout-ms 30000
            backoff-base-ms 100
            backoff-max-ms 10000
            retryable-status-codes 502 503 504
        }

        circuit-breaker {
            failure-threshold 5
            success-threshold 2
            timeout-seconds 30
            half-open-max-requests 1
        }

        static-files {
            root "/var/www"
            index "index.html"
            directory-listing #false
            cache-control "public, max-age=3600"
            compress #true
            fallback "index.html"
        }

        error-pages {
            default-format "json"
            pages {
                "404" { format "json" message "Not found" }
                "500" { format "html" template "/path/to/500.html" }
            }
        }
    }
}

upstreams {
    upstream "backend" {
        targets {
            target { address "127.0.0.1:3000" }
        }
    }
}
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `priority` | int | `0` | Route priority (higher first) |
| `matches` | block | Required | Match conditions |
| `upstream` | string | - | Target upstream ID |
| `service-type` | string | `web` | Service type |
| `builtin-handler` | string | - | Built-in handler name |
| `filters` | list | - | Filter chain |
| `waf-enabled` | bool | `false` | Enable WAF |

## Upstreams Block

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

upstreams {
    upstream "id" {
        targets {
            target {
                address "10.0.1.1:8080"
                weight 1
                max-requests 1000
                metadata { "zone" "us-east-1" }
            }
        }
        load-balancing "round_robin"

        health-check {
            type "http" {
                path "/health"
                expected-status 200
                host "backend.internal"
            }
            // Or: type "tcp"
            // Or: type "grpc" { service "grpc.health.v1.Health" }
            interval-secs 10
            timeout-secs 5
            healthy-threshold 2
            unhealthy-threshold 3
        }

        connection-pool {
            max-connections 100
            max-idle 20
            idle-timeout-secs 60
            max-lifetime-secs 3600
        }

        timeouts {
            connect-secs 10
            request-secs 60
            read-secs 30
            write-secs 30
        }

        tls {
            sni "backend.internal"
            client-cert "/path/to/cert.pem"
            client-key "/path/to/key.pem"
            ca-cert "/path/to/ca.pem"
            insecure-skip-verify #false
        }
    }
}

routes {
    route "default" {
        matches { path-prefix "/" }
        upstream "backend"
    }
}
```

### Load Balancing Algorithms

| Algorithm | Description |
|-----------|-------------|
| `round_robin` | Sequential rotation (default) |
| `least_connections` | Fewest active connections |
| `random` | Random selection |
| `ip_hash` | Client IP hash |
| `weighted` | Weighted random |
| `consistent_hash` | Consistent hashing |
| `power_of_two_choices` | Best of two random |
| `adaptive` | Response-time based |

## Limits Block

```kdl
limits {
    // Headers
    max-header-size-bytes 8192
    max-header-count 100
    max-header-name-bytes 256
    max-header-value-bytes 4096

    // Body
    max-body-size-bytes 10485760
    max-body-buffer-bytes 1048576
    max-body-inspection-bytes 1048576

    // Decompression
    max-decompression-ratio 100.0
    max-decompressed-size-bytes 104857600

    // Connections
    max-connections-per-client 100
    max-connections-per-route 1000
    max-total-connections 10000
    max-idle-connections-per-upstream 100

    // Requests
    max-in-flight-requests 10000
    max-in-flight-requests-per-worker 1000
    max-queued-requests 1000

    // Agents
    max-agent-queue-depth 100
    max-agent-body-bytes 1048576
    max-agent-response-bytes 10240

    // Rate limits
    max-requests-per-second-global 10000
    max-requests-per-second-per-client 100
    max-requests-per-second-per-route 1000

    // Memory
    max-memory-bytes 2147483648
    max-memory-percent 80.0
}
```

## Agents Block

```kdl
agents {
    agent "id" {
        type "auth"                        // auth, rate_limit, waf, custom

        transport "unix_socket" {
            path "/var/run/agent.sock"
        }
        // Or: transport "grpc" { address "127.0.0.1:50051" }

        timeout-ms 100
        failure-mode "closed"              // closed, open
        max-body-bytes 1048576
        events "on_request_headers" "on_response_headers"

        circuit-breaker {
            failure-threshold 5
            recovery-timeout-secs 30
        }
    }
}
```

## Complete Minimal Example

```kdl
system {
    worker-threads 0
    max-connections 10000
}

listeners {
    listener "http" {
        address "0.0.0.0:8080"
        protocol "http"
    }
}

routes {
    route "api" {
        matches {
            path-prefix "/api/"
        }
        upstream "backend"
    }
}

upstreams {
    upstream "backend" {
        targets {
            target { address "127.0.0.1:3000" }
        }
    }
}
```

## Complete Production Example

```kdl
system {
    worker-threads 0
    max-connections 50000
    graceful-shutdown-timeout-secs 60
    auto-reload #true
    daemon #true
    pid-file "/var/run/sentinel.pid"
    user "sentinel"
    group "sentinel"
}

listeners {
    listener "https" {
                tls {
                    cert-file "/etc/sentinel/certs/server.crt"
                    key-file "/etc/sentinel/certs/server.key"
                    min-version "1.2"
                }
        address "0.0.0.0:443"
        protocol "https"

    }

    listener "admin" {
        address "127.0.0.1:9090"
        protocol "http"
    }
}

routes {
    route "health" {
        priority 1000
        matches { path "/health" }
        service-type "builtin"
        builtin-handler "health"
    }

    route "api" {
        priority 100
        matches { path-prefix "/api/" }
        upstream "backend"
        retry-policy {
            max-attempts 3
            retryable-status-codes 502 503 504
        }
    }
}

upstreams {
    upstream "backend" {
        targets {
            target { address "10.0.1.1:8080" }
            target { address "10.0.1.2:8080" }
        }
        load-balancing "least_connections"
        health-check {
            type "http" { path "/health" expected-status 200 }
            interval-secs 10
        }
    }
}

limits {
    max-body-size-bytes 10485760
    max-requests-per-second-per-client 100
}

```

## See Also

- [Configuration Guide](../../configuration/) - Detailed configuration documentation
- [CLI Reference](../cli/) - Command-line options

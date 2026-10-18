+++
title = "Configuration Schema"
weight = 5
updated = 2026-10-18
+++

Quick reference for all Zentinel configuration options.

## Top-Level Blocks

```fragment,kdl
schema-version "1.0"
system { }          // required
listeners { }       // required
routes { }
upstreams { }
filters { }
agents { }
limits { }
cache { }
observability { }
rate-limits { }
namespace "id" { }  // one per namespace
include "other.kdl"
waf { }             // parsed, not wired: any mode but "off" is rejected
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
        default-route "default"            // id of a route below

        tls {
            cert-file "/path/to/cert.pem"
            key-file "/path/to/key.pem"
            ca-file "/path/to/ca.pem"
            min-version "TLS1.2"
            max-version "TLS1.3"
            client-auth #false
            ocsp-stapling #true
            session-resumption #true
            cipher-suite "TLS_AES_256_GCM_SHA384"
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
        target "127.0.0.1:3000"
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
| `cipher-suite` | string (repeatable) | - | Allowed cipher suite; repeat the node per suite |

### ACME Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `email` | string | **required** | Contact email for ACME account |
| `domains` | string[] | **required** | Domains to include in certificate |
| `server-url` | string | - | Custom ACME directory URL (e.g., ZeroSSL) |
| `staging` | bool | `false` | Use Let's Encrypt staging environment |
| `eab` | block | - | External Account Binding credentials |
| `storage` | path | `/var/lib/zentinel/acme` | Certificate storage directory |
| `renew-before-days` | u32 | `30` | Days before expiry to trigger renewal |
| `challenge-type` | string | `"http-01"` | Challenge type: `http-01` or `dns-01` |
| `key-type` | string | `"ecdsa-p256"` | Key type: `ecdsa-p256`, `ecdsa-p384` |
| `dns-provider` | block | - | DNS provider config (required for dns-01) |

### EAB Options

| Option | Type | Description |
|--------|------|-------------|
| `kid` | string | Key ID provided by the ACME CA |
| `hmac-key` | string | HMAC key (base64url-encoded) from the CA |

### DNS Provider Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `type` | string | **required** | Provider: `cloudflare`, `hetzner`, `webhook` |
| `credentials-file` | path | - | Path to credentials file |
| `credentials-env` | string | - | Environment variable with credentials |
| `api-timeout-secs` | u64 | `30` | API request timeout |
| `propagation` | block | - | DNS propagation check settings |

### Propagation Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `initial-delay-secs` | u64 | `10` | Wait before first propagation check |
| `check-interval-secs` | u64 | `5` | Interval between checks |
| `timeout-secs` | u64 | `120` | Max time to wait for propagation |
| `nameservers` | string[] | public DNS | DNS servers to query |

## Routes Block

Every route setting in one place. This is a reference listing, not a loadable
route: a route serves from `upstream`, `static-files` **or** a
`builtin-handler`, never several at once.

```fragment,kdl
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
            method "GET"                   // one method per node
            header "X-Key" "value"         // name, optional value
            query-param "format" "json"    // name, optional value
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
                key "client-ip"            // client-ip, path, route, client-ip-and-path, header:<name>
            }
        }

        retry-policy {
            max-attempts 3
        }

        cache {
            enabled #true
            default-ttl-secs 3600
        }

        // circuit-breaker belongs to an upstream or an agent, not a route

        static-files {
            root "/var/www"
            index "index.html"
            directory-listing #false
            cache-control "public, max-age=3600"
            compress #true
            fallback "index.html"
        }

        // error-pages is not configurable (no parser reads it as of 26.10_3)

        websocket #true
        websocket-inspection #false
    }
}

upstreams {
    upstream "backend" {
        target "127.0.0.1:3000"
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
    upstream "backend" {
        target "10.0.1.1:8080" weight=1   // address and weight only
        // Or: target { address "10.0.1.1:8080"; weight 1 }
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

As of 26.10_3 these names are read only by the multi-file (directory) loader.
A single-file configuration is parsed by `parse_limits_config`
(`crates/config/src/kdl/mod.rs`), which reads just `max-header-size`,
`max-header-count`, `max-body-size`, `max-connections-per-client`,
`max-total-connections` and `max-in-flight-requests`; the other keys below are
ignored there. See [Directive Index — Limits](../directives/#limits-directives).

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
    // max-memory-percent is not read by any parser
}
```

## Agents Block

```kdl
agents {
    agent "id" {
        type "auth"                        // auth, rate_limit, waf, custom

        unix-socket "/var/run/agent.sock"
        // Or: grpc "http://127.0.0.1:50051"

        timeout-ms 100
        failure-mode "closed"              // closed, open
        max-request-body-bytes 1048576
        events "request_headers" "response_headers"

        circuit-breaker {
            failure-threshold 5
            timeout-seconds 30
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
        target "127.0.0.1:3000"
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
    pid-file "/var/run/zentinel.pid"
    user "zentinel"
    group "zentinel"
}

listeners {
    listener "https" {
        address "0.0.0.0:443"
        protocol "https"
        tls {
            cert-file "/etc/zentinel/certs/server.crt"
            key-file "/etc/zentinel/certs/server.key"
            min-version "1.2"
        }
    }

    // 9090 is taken by the metrics server (observability.metrics.address)
    listener "admin" {
        address "127.0.0.1:9091"
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
        }
    }
}

upstreams {
    upstream "backend" {
        target "10.0.1.1:8080"
        target "10.0.1.2:8080"
        load-balancing "least_connections"
        health-check {
            type "http" { path "/health"; expected-status 200; }
            interval-secs 10
        }
    }
}

limits {
    max-body-size 10485760   // single-file key (see Limits Block above)
}

```

## See Also

- [Configuration Guide](../../configuration/) - Detailed configuration documentation
- [CLI Reference](../cli/) - Command-line options

+++
title = "Configuration"
weight = 3
sort_by = "weight"
template = "section.html"
+++

Sentinel uses KDL (a human-friendly document language) for configuration. This section covers all configuration options organized by component.

## Configuration Blocks

| Block | Purpose |
|-------|---------|
| [File Format](file-format/) | KDL syntax and file structure |
| [Server](server/) | Worker threads, process management, shutdown |
| [Listeners](listeners/) | Network binding, TLS, SNI, HTTP/2 |
| [Routes](routes/) | Request matching and routing rules |
| [Upstreams](upstreams/) | Backend pools, load balancing, health checks |
| [Limits](limits/) | Request limits, rate limiting, memory protection |
| [Filters](filters/) | Rate limiting, CORS, compression, geo-blocking |
| [Caching](cache/) | HTTP response caching configuration |
| [Observability](observability/) | Logging, metrics, and distributed tracing |
| [Agents](agents/) | External processing agent configuration |
| [WAF](waf/) | Web Application Firewall configuration |
| [Namespaces & Services](namespaces/) | Hierarchical organization and runtime isolation |

## Quick Example

```kdl
system {
    worker-threads 0
    max-connections 10000
    trace-id-format "tinyflake"
}

listeners {
    listener "https" {
        address "0.0.0.0:443"
        protocol "https"
        tls {
            cert-file "/etc/sentinel/certs/server.crt"
            key-file "/etc/sentinel/certs/server.key"
            min-version "1.2"
        }
    }
}

routes {
    route "api" {
        priority 100
        matches {
            path-prefix "/api/"
        }
        upstream "backend"
        filters "rate-limit" "cors"

        cache {
            enabled #true
            default-ttl-secs 60
        }
    }
}

upstreams {
    upstream "backend" {
        targets {
            target { address "10.0.1.1:8080" }
            target { address "10.0.1.2:8080" }
        }
        load-balancing "round_robin"
        health-check {
            type "http" {
                path "/health"
                expected-status 200
            }
        }
    }
}

filters {
    filter "rate-limit" {
        type "rate-limit"
        max-rps 100
        burst 20
        key "client-ip"
    }

    filter "cors" {
        type "cors"
        allowed-origins "https://example.com"
        allowed-methods "GET" "POST" "PUT" "DELETE"
    }
}

cache {
    enabled #true
    backend "memory"
    max-size 104857600
}

observability {
    logging {
        level "info"
        format "json"
    }
    metrics {
        enabled #true
        address "0.0.0.0:9090"
    }
}

limits {
    max-body-size-bytes 10485760
}
```

## Validation

Always validate configuration before applying:

```bash
sentinel --config sentinel.kdl --validate
```

## Hot Reload

Reload configuration without restart:

```bash
kill -HUP $(cat /var/run/sentinel.pid)
# or
curl -X POST http://localhost:9090/admin/reload
```

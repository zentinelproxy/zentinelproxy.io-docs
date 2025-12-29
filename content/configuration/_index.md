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
| [Listeners](listeners/) | Network binding, TLS, HTTP/2 |
| [Routes](routes/) | Request matching and routing rules |
| [Upstreams](upstreams/) | Backend pools, load balancing, health checks |
| [Limits](limits/) | Request limits, rate limiting, memory protection |

## Quick Example

```kdl
server {
    worker-threads 0
    max-connections 10000
}

listeners {
    listener "https" {
        address "0.0.0.0:443"
        protocol "https"
        tls {
            cert-file "/etc/sentinel/certs/server.crt"
            key-file "/etc/sentinel/certs/server.key"
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

limits {
    max-body-size-bytes 10485760
    max-requests-per-second-per-client 100
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

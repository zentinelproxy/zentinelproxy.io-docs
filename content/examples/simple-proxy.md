+++
title = "Simple Proxy"
weight = 1
updated = 2026-10-19
+++

A minimal reverse proxy configuration that forwards all traffic to a single backend server. This is the simplest Zentinel setup and a good starting point.

## Use Case

- Forward all requests to a backend application
- Add health checks for the upstream
- Basic observability with metrics

## Configuration

Create `zentinel.kdl`:

```kdl
// Simple Reverse Proxy
// Forwards all traffic to a single backend

system {
    worker-threads 0  // Auto-detect CPU cores
    graceful-shutdown-timeout-secs 30
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
        target "127.0.0.1:3000" weight=1

        health-check {
            type "http" {
                path "/health"
            }
            interval-secs 10
            timeout-secs 5
            unhealthy-threshold 3
            healthy-threshold 2
        }
    }
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

## Setup

### 1. Start a Backend Server

For testing, start a simple HTTP server:

```bash
# Python
python3 -m http.server 3000

# Node.js
npx http-server -p 3000

# Or use your own application on port 3000
```

### 2. Run Zentinel

```bash
zentinel -c zentinel.kdl
```

Expected output:

```
INFO zentinel: Starting Zentinel v25.12.0
INFO zentinel: Listener http bound to 0.0.0.0:8080
INFO zentinel: Metrics server listening on 0.0.0.0:9090
INFO zentinel: Upstream backend: 1 target(s) configured
```

## Testing

### Basic Request

```bash
curl -i http://localhost:8080/
```

### Check Headers

The response carries the request's trace ID:

```bash
curl -i http://localhost:8080/ | grep -i x-correlation-id
```

On the way to the backend, Zentinel keeps the client's `Host` header and adds:
- `X-Correlation-Id` and `X-Trace-Id` - the request's trace ID (taken from an incoming `X-Request-Id` or `X-Correlation-Id` if the client sent one, generated otherwise)
- `X-Forwarded-For` - the client's address
- `X-Forwarded-Proto` - `http` here (`https` on a TLS listener)
- `X-Forwarded-Host` - the host the client requested
- `X-Forwarded-By: Zentinel`

From 26.10_5 the `X-Forwarded-*` headers are set by Zentinel, and any the
client sent are replaced; client-sent `Forwarded` and `X-Real-IP` headers are
removed. If Zentinel runs behind a load balancer and the backend should see the
original client, list the load balancer in the listener's
[`trusted-proxies`](/configuration/listeners/#trusted-proxies). Releases before
26.10_5 send no `X-Forwarded-*` headers.

### Metrics

```bash
curl http://localhost:9090/metrics | grep zentinel
```

Key metrics:
- `zentinel_requests_total` - Total request count
- `zentinel_request_duration_seconds` - Latency histogram
- `zentinel_upstream_health` - Backend health status

## Customizations

### Add Request Timeout

```kdl
routes {
    route "default" {
        matches {
            path-prefix "/"
        }
        upstream "backend"
        policies {
            timeout-secs 30
        }
    }
}
```

### Add TLS

```kdl
listeners {
    listener "https" {
        address "0.0.0.0:8443"
        protocol "https"
        tls {
            cert-file "/etc/zentinel/cert.pem"
            key-file "/etc/zentinel/key.pem"
        }
    }
}
```

### HTTPS Backend

If your backend serves HTTPS, add a `tls` block to the upstream:

```kdl
upstreams {
    upstream "backend" {
        target "api.example.com:443" weight=1

        tls {
            sni "api.example.com"
        }

        health-check {
            type "http" {
                path "/health"
            }
            interval-secs 10
        }
    }
}
```

Without the `tls` block, Zentinel connects with plaintext HTTP regardless of the port number.

### Multiple Backend Instances

```kdl
upstreams {
    upstream "backend" {
        target "127.0.0.1:3000" weight=1
        target "127.0.0.1:3001" weight=1
        target "127.0.0.1:3002" weight=1

        load-balancing "round_robin"
    }
}
```

## Next Steps

- [Load Balancer](../load-balancer/) - Multiple backends with load balancing
- [API Gateway](../api-gateway/) - Add authentication and rate limiting
- [Observability](/examples/prometheus/) - Full monitoring stack

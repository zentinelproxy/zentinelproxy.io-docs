+++
title = "API Gateway"
weight = 2
+++

A complete API gateway configuration with versioned APIs, authentication, rate limiting, and proper error handling. This example shows how to build a production-ready API gateway.

## Use Case

- Route multiple API versions to different backends
- Authenticate requests with JWT or API keys
- Apply rate limiting per client
- Return JSON error responses
- Add security headers

## Architecture

```
                    ┌─────────────────┐
                    │    Sentinel     │
                    │   API Gateway   │
                    └────────┬────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
         ▼                   ▼                   ▼
    ┌─────────┐        ┌─────────┐        ┌─────────┐
    │ API v2  │        │ API v1  │        │ Auth    │
    │ :3000   │        │ :3001   │        │ :3002   │
    └─────────┘        └─────────┘        └─────────┘
```

## Configuration

Create `sentinel.kdl`:

```kdl
// API Gateway Configuration
// Production-ready API management

system {
    worker-threads 0
    graceful-shutdown-timeout-secs 30
}

listeners {
    listener "https" {
        address "0.0.0.0:8443"
        protocol "https"
        tls {
            cert-file "/etc/sentinel/certs/api.crt"
            key-file "/etc/sentinel/certs/api.key"
        }
    }
    // HTTP redirect to HTTPS
    listener "http" {
        address "0.0.0.0:8080"
        protocol "http"
        redirect-https true
    }
}

routes {
    // Health check - no auth required
    route "health" {
        priority 1000
        matches {
            path "/health"
        }
        service-type "builtin"
        builtin-handler "health"
    }

    // API v2 - current version
    route "api-v2" {
        priority 200
        matches {
            path-prefix "/api/v2/"
            method "GET" "POST" "PUT" "DELETE" "PATCH"
        }
        upstream "api-v2"
        agents ["auth" "ratelimit"]
        service-type "api"
        retry-policy {
            max-attempts 3
            retryable-status-codes 502 503 504
        }
        policies {
            timeout-secs 30
            max-body-size "10MB"
            request-headers {
                set {
                    "X-Api-Version" "2"
                }
            }
            response-headers {
                set {
                    "X-Content-Type-Options" "nosniff"
                    "X-Frame-Options" "DENY"
                    "X-XSS-Protection" "1; mode=block"
                }
                remove "Server" "X-Powered-By"
            }
        }
        error-pages {
            default-format "json"
        }
    }

    // API v1 - legacy, deprecated
    route "api-v1" {
        priority 100
        matches {
            path-prefix "/api/v1/"
        }
        upstream "api-v1"
        agents ["auth"]
        service-type "api"
        policies {
            timeout-secs 60
            response-headers {
                set {
                    "X-Deprecation-Warning" "API v1 is deprecated. Migrate to /api/v2/"
                    "Sunset" "2025-12-31"
                }
            }
        }
        error-pages {
            default-format "json"
        }
    }

    // OpenAPI documentation - public
    route "docs" {
        priority 50
        matches {
            path-prefix "/docs/"
        }
        service-type "static"
        static-files {
            root "/var/www/api-docs"
            index "index.html"
        }
    }
}

upstreams {
    upstream "api-v2" {
        targets {
            target { address "127.0.0.1:3000" weight 100 }
            target { address "127.0.0.1:3001" weight 100 }
        }
        load-balancing "round-robin"
        health-check {
            type "http" {
                path "/health"
                expected-status 200
            }
            interval-secs 5
            unhealthy-threshold 3
        }
    }

    upstream "api-v1" {
        targets {
            target { address "127.0.0.1:3010" }
        }
        health-check {
            type "http" {
                path "/health"
            }
            interval-secs 10
        }
    }
}

agents {
    agent "auth" {
        transport "unix_socket" {
            path "/var/run/sentinel/auth.sock"
        }
        events ["request_headers"]
        timeout-ms 100
        failure-mode "closed"
    }

    agent "ratelimit" {
        transport "unix_socket" {
            path "/var/run/sentinel/ratelimit.sock"
        }
        events ["request_headers"]
        timeout-ms 50
        failure-mode "open"
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
    tracing {
        enabled #true
        service-name "api-gateway"
        endpoint "http://localhost:4317"
    }
}
```

## Setup

### 1. Install Agents

```bash
cargo install sentinel-agent-auth sentinel-agent-ratelimit
```

### 2. Start Agents

```bash
# Auth agent with JWT validation
sentinel-agent-auth \
  --socket /var/run/sentinel/auth.sock \
  --jwt-secret "your-secret-key" \
  --jwt-issuer "api.example.com" &

# Rate limit agent
sentinel-agent-ratelimit \
  --socket /var/run/sentinel/ratelimit.sock \
  --requests-per-minute 100 \
  --burst 20 &
```

### 3. Start Backend Services

```bash
# Start API v2 instances
node api-v2/server.js --port 3000 &
node api-v2/server.js --port 3001 &

# Start API v1 instance
node api-v1/server.js --port 3010 &
```

### 4. Run Sentinel

```bash
sentinel -c sentinel.kdl
```

## Testing

### Health Check

```bash
curl http://localhost:8080/health
```

### API v2 with Authentication

```bash
# Get a token (from your auth service)
TOKEN="eyJhbGciOiJIUzI1NiIs..."

# Make authenticated request
curl -H "Authorization: Bearer $TOKEN" \
     https://localhost:8443/api/v2/users
```

### Rate Limiting

```bash
# Send 150 requests rapidly
for i in {1..150}; do
  curl -s -o /dev/null -w "%{http_code}\n" \
    -H "Authorization: Bearer $TOKEN" \
    https://localhost:8443/api/v2/users
done | sort | uniq -c
```

Expected output shows 429 responses after limit exceeded.

### API v1 Deprecation Headers

```bash
curl -I -H "Authorization: Bearer $TOKEN" \
     https://localhost:8443/api/v1/users
```

Response includes:
```
X-Deprecation-Warning: API v1 is deprecated. Migrate to /api/v2/
Sunset: 2025-12-31
```

## Customizations

### API Key Authentication

```bash
# Run auth agent with API keys
sentinel-agent-auth \
  --socket /var/run/sentinel/auth.sock \
  --api-keys-file /etc/sentinel/api-keys.json
```

### Per-Route Rate Limits

Create separate rate limit agents for different routes:

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

agents {
    agent "ratelimit-standard" type="custom" {
        unix-socket "/var/run/sentinel/ratelimit-standard.sock"
        events "request_headers"
        timeout-ms 50
    }

    agent "ratelimit-premium" type="custom" {
        unix-socket "/var/run/sentinel/ratelimit-premium.sock"
        events "request_headers"
        timeout-ms 50
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

### CORS Configuration

```kdl
route "api-v2" {
    policies {
        response-headers {
            set {
                "Access-Control-Allow-Origin" "https://app.example.com"
                "Access-Control-Allow-Methods" "GET, POST, PUT, DELETE"
                "Access-Control-Allow-Headers" "Authorization, Content-Type"
                "Access-Control-Max-Age" "86400"
            }
        }
    }
}
```

## Next Steps

- [Security](../security/) - Add WAF protection
- [Observability](../observability/) - Complete monitoring setup
- [Load Balancer](../load-balancer/) - Advanced load balancing

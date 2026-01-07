+++
title = "Security"
weight = 7
+++

Complete security configuration with WAF, authentication, rate limiting, and security headers.

## Use Case

- Protect against OWASP Top 10 attacks
- Authenticate and authorize requests
- Rate limit to prevent abuse
- Add security headers

## Architecture

```
                         ┌─────────────────┐
                         │    Sentinel     │
                         └────────┬────────┘
                                  │
         ┌────────────────────────┼────────────────────────┐
         │                        │                        │
         ▼                        ▼                        ▼
   ┌───────────┐           ┌───────────┐           ┌───────────┐
   │    WAF    │           │   Auth    │           │Rate Limit │
   │  Agent    │           │  Agent    │           │  Agent    │
   └───────────┘           └───────────┘           └───────────┘
```

## Configuration

Create `sentinel.kdl`:

```kdl
// Security Configuration
// WAF, authentication, and rate limiting

server {
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
            min-version "1.2"
            ciphers [
                "TLS_AES_256_GCM_SHA384"
                "TLS_CHACHA20_POLY1305_SHA256"
                "TLS_AES_128_GCM_SHA256"
            ]
        }
    }
    listener "http" {
        address "0.0.0.0:8080"
        protocol "http"
        redirect-https true
    }
}

routes {
    // Health check - no security
    route "health" {
        priority 1000
        matches { path "/health" }
        service-type "builtin"
        builtin-handler "health"
    }

    // Public endpoints - WAF only, no auth
    route "public" {
        priority 500
        matches {
            path-prefix "/public/"
        }
        agents ["waf" "ratelimit"]
        upstream "backend"
        policies {
            response-headers {
                set {
                    "X-Content-Type-Options" "nosniff"
                    "X-Frame-Options" "DENY"
                    "X-XSS-Protection" "1; mode=block"
                    "Strict-Transport-Security" "max-age=31536000; includeSubDomains"
                    "Content-Security-Policy" "default-src 'self'"
                    "Referrer-Policy" "strict-origin-when-cross-origin"
                    "Permissions-Policy" "geolocation=(), microphone=(), camera=()"
                }
                remove "Server" "X-Powered-By"
            }
        }
    }

    // API endpoints - full security
    route "api" {
        priority 200
        matches {
            path-prefix "/api/"
        }
        agents ["waf" "auth" "ratelimit"]
        upstream "backend"
        service-type "api"
        policies {
            timeout-secs 30
            max-body-size "10MB"
            buffer-requests true  // Required for WAF body inspection
            response-headers {
                set {
                    "X-Content-Type-Options" "nosniff"
                    "X-Frame-Options" "DENY"
                    "Cache-Control" "no-store"
                }
                remove "Server" "X-Powered-By"
            }
        }
        error-pages {
            default-format "json"
        }
    }

    // Admin endpoints - strict security
    route "admin" {
        priority 300
        matches {
            path-prefix "/admin/"
        }
        agents ["waf" "auth" "ratelimit-strict"]
        upstream "backend"
        policies {
            failure-mode "closed"
            request-headers {
                set { "X-Admin-Request" "true" }
            }
        }
    }
}

upstreams {
    upstream "backend" {
        targets {
            target { address "127.0.0.1:3000" }
        }
        health-check {
            type "http" { path "/health" }
            interval-secs 10
        }
    }
}

agents {
    // Web Application Firewall
    agent "waf" {
        transport "unix_socket" {
            path "/var/run/sentinel/waf.sock"
        }
        events ["request_headers" "request_body"]
        timeout-ms 100
        failure-mode "closed"
    }

    // Authentication
    agent "auth" {
        transport "unix_socket" {
            path "/var/run/sentinel/auth.sock"
        }
        events ["request_headers"]
        timeout-ms 50
        failure-mode "closed"
    }

    // Standard rate limiting
    agent "ratelimit" {
        transport "unix_socket" {
            path "/var/run/sentinel/ratelimit.sock"
        }
        events ["request_headers"]
        timeout-ms 20
        failure-mode "open"
    }

    // Strict rate limiting for admin
    agent "ratelimit-strict" {
        transport "unix_socket" {
            path "/var/run/sentinel/ratelimit-strict.sock"
        }
        events ["request_headers"]
        timeout-ms 20
        failure-mode "closed"
    }
}

observability {
    metrics {
        enabled true
        address "0.0.0.0:9090"
    }
    logging {
        level "info"
        format "json"
    }
}
```

## Agent Setup

### Install Agents

```bash
cargo install sentinel-agent-waf sentinel-agent-auth sentinel-agent-ratelimit
```

### Start WAF Agent

```bash
sentinel-agent-waf \
    --socket /var/run/sentinel/waf.sock \
    --paranoia-level 1 \
    --block-mode true \
    --sqli true \
    --xss true \
    --path-traversal true \
    --command-injection true &
```

### Start Auth Agent

```bash
# JWT authentication
sentinel-agent-auth \
    --socket /var/run/sentinel/auth.sock \
    --jwt-secret "your-256-bit-secret" \
    --jwt-issuer "api.example.com" \
    --jwt-audience "api" &
```

### Start Rate Limit Agents

```bash
# Standard: 100 req/min
sentinel-agent-ratelimit \
    --socket /var/run/sentinel/ratelimit.sock \
    --requests-per-minute 100 \
    --burst 20 &

# Strict: 10 req/min for admin
sentinel-agent-ratelimit \
    --socket /var/run/sentinel/ratelimit-strict.sock \
    --requests-per-minute 10 \
    --burst 2 &
```

## Testing

### Test WAF - SQL Injection

```bash
curl -i "http://localhost:8080/api/users?id=1' OR '1'='1"
```

Expected response:

```
HTTP/1.1 403 Forbidden
X-WAF-Blocked: true
X-WAF-Rule: 942100

{"error": "Request blocked by WAF"}
```

### Test WAF - XSS

```bash
curl -i "http://localhost:8080/api/search?q=<script>alert(1)</script>"
```

Expected response:

```
HTTP/1.1 403 Forbidden
X-WAF-Blocked: true
X-WAF-Rule: 941100
```

### Test Authentication

```bash
# Without token - should fail
curl -i http://localhost:8080/api/users

# With valid token
TOKEN=$(curl -s -X POST http://localhost:8080/public/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username":"user","password":"pass"}' | jq -r .token)

curl -H "Authorization: Bearer $TOKEN" http://localhost:8080/api/users
```

### Test Rate Limiting

```bash
# Send 150 requests rapidly
for i in {1..150}; do
  curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8080/public/test
done | sort | uniq -c
```

Expected output shows 429 responses after limit.

### Test Security Headers

```bash
curl -I https://localhost:8443/public/test
```

Expected headers:

```
Strict-Transport-Security: max-age=31536000; includeSubDomains
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Content-Security-Policy: default-src 'self'
```

## Advanced Configurations

### OWASP ModSecurity CRS

For full OWASP CRS support, use the ModSecurity agent:

```bash
# Install ModSecurity agent
cargo install sentinel-agent-modsec

# Download OWASP CRS
git clone https://github.com/coreruleset/coreruleset /etc/modsecurity/crs
cp /etc/modsecurity/crs/crs-setup.conf.example /etc/modsecurity/crs/crs-setup.conf

# Start ModSecurity agent
sentinel-agent-modsec \
    --socket /var/run/sentinel/waf.sock \
    --rules /etc/modsecurity/crs/crs-setup.conf \
    --rules "/etc/modsecurity/crs/rules/*.conf" &
```

### API Key Authentication

```bash
sentinel-agent-auth \
    --socket /var/run/sentinel/auth.sock \
    --api-keys-file /etc/sentinel/api-keys.json &
```

Create `/etc/sentinel/api-keys.json`:

```json
{
  "keys": {
    "sk_live_abc123": {
      "name": "Production Key",
      "roles": ["read", "write"],
      "rate_limit": 1000
    },
    "sk_test_xyz789": {
      "name": "Test Key",
      "roles": ["read"],
      "rate_limit": 100
    }
  }
}
```

### IP-Based Rate Limiting

```bash
sentinel-agent-ratelimit \
    --socket /var/run/sentinel/ratelimit.sock \
    --key-by "client_ip" \
    --requests-per-minute 100 &
```

### IP Denylist

```bash
cargo install sentinel-agent-denylist

sentinel-agent-denylist \
    --socket /var/run/sentinel/denylist.sock \
    --file /etc/sentinel/blocked-ips.txt \
    --cidr "10.0.0.0/8" "192.168.0.0/16" &
```

## Security Metrics

Key security metrics to monitor:

```promql
# WAF blocks per rule
sum by (rule) (rate(sentinel_agent_waf_blocks_total[5m]))

# Auth failures
rate(sentinel_agent_auth_failures_total[5m])

# Rate limit hits
rate(sentinel_agent_ratelimit_limited_total[5m])

# Blocked requests (all agents)
sum(rate(sentinel_requests_total{blocked="true"}[5m]))
```

## Incident Response

### Block Specific IP

```bash
# Add to denylist
echo "1.2.3.4" >> /etc/sentinel/blocked-ips.txt

# Reload denylist agent
kill -HUP $(pgrep sentinel-agent-denylist)
```

### Enable Detect-Only Mode

For investigating false positives without blocking:

```bash
sentinel-agent-waf \
    --socket /var/run/sentinel/waf.sock \
    --block-mode false &  # Detect only, don't block
```

Check logs for `X-WAF-Detected` headers.

## Next Steps

- [Observability](../observability/) - Monitor security events
- [API Gateway](../api-gateway/) - Complete API management
- [Microservices](../microservices/) - Secure service mesh

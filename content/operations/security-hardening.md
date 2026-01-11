+++
title = "Security Hardening"
weight = 5
+++

Best practices for securing Sentinel deployments in production.

## Security Baseline

### Defense in Depth

Sentinel follows a defense-in-depth approach:

1. **Network layer**: Firewall rules, network segmentation
2. **Transport layer**: TLS, certificate validation
3. **Application layer**: Header validation, rate limiting, WAF
4. **Host layer**: File permissions, process isolation

### Secure Defaults

Sentinel ships with secure defaults:

```kdl
security {
    // Fail closed on errors by default
    failure-mode "closed"

    // Enforce request limits
    limits {
        max-header-size 8192
        max-header-count 100
        max-body-size 10485760  // 10MB
        max-uri-length 8192
    }

    // Enforce timeouts
    timeouts {
        request-header-secs 30
        request-body-secs 60
        response-header-secs 60
        response-body-secs 120
    }
}
```

## TLS Configuration

### Minimum TLS Requirements

```kdl
system {
    worker-threads 0
}

listeners {
    listener "https" {
        address "0.0.0.0:443"
        protocol "https"

        tls {
            cert-file "/etc/sentinel/certs/server.crt"
            key-file "/etc/sentinel/certs/server.key"

            // Minimum TLS 1.2 (TLS 1.3 preferred)
            min-version "1.2"

            // Strong cipher suites only
            ciphers "TLS_AES_256_GCM_SHA384" "TLS_AES_128_GCM_SHA256" "TLS_CHACHA20_POLY1305_SHA256" "ECDHE-ECDSA-AES256-GCM-SHA384" "ECDHE-RSA-AES256-GCM-SHA384"

            // OCSP stapling
            ocsp-stapling #true
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

### Certificate Requirements

**Server Certificates**:
- Minimum 2048-bit RSA or 256-bit ECDSA
- SHA-256 or stronger signature algorithm
- Valid DNS names in SAN (Subject Alternative Name)
- Certificate chain complete (including intermediates)

**Validation**:
```bash
# Check certificate details
openssl x509 -in server.crt -noout -text | grep -A2 "Public-Key\|Signature Algorithm"

# Verify certificate chain
openssl verify -CAfile ca-chain.crt server.crt

# Test TLS configuration
openssl s_client -connect localhost:443 -tls1_2 </dev/null 2>/dev/null | grep "Cipher is"
```

### HSTS Validation

Sentinel automatically warns if TLS is enabled but no HSTS (HTTP Strict Transport Security) header is configured:

```bash
sentinel --config sentinel.kdl --validate
# Warning: TLS is enabled but no HSTS header is configured
```

To resolve this warning, add the `Strict-Transport-Security` header to your routes:

```kdl
routes {
    route "default" {
        matches { path-prefix "/" }
        upstream "backend"
        policies {
            response-headers {
                set {
                    "Strict-Transport-Security" "max-age=31536000; includeSubDomains"
                }
            }
        }
    }
}
```

Or use a headers filter:

```kdl
filters {
    filter "security-headers" {
        type "headers"
        response {
            set {
                "Strict-Transport-Security" "max-age=31536000; includeSubDomains"
            }
        }
    }
}
```

**HSTS Settings:**

| Directive | Meaning |
|-----------|---------|
| `max-age=31536000` | Browser remembers HTTPS-only for 1 year |
| `includeSubDomains` | Apply to all subdomains |
| `preload` | Request inclusion in browser preload lists |

### mTLS for Upstreams

Configure client certificates for backend authentication:

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
        matches { path-prefix "/" }
        upstream "secure-backend"
    }
}

upstreams {
    upstream "secure-backend" {
        targets {
            target { address "10.0.0.1:8443" }
        }
        tls {
            sni "backend.internal"
            client-cert "/etc/sentinel/certs/client.crt"
            client-key "/etc/sentinel/certs/client.key"
            ca-cert "/etc/sentinel/certs/backend-ca.crt"
        }
    }
}
```

See [mTLS to Upstreams](/configuration/upstreams/#mtls) for detailed configuration.

## Header Security

### Security Response Headers

Security headers can be configured using response header policies in your routes:

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
        matches { path-prefix "/" }
        upstream "backend"
        policies {
            response-headers {
                set {
                    "X-Frame-Options" "DENY"
                    "X-Content-Type-Options" "nosniff"
                    "X-XSS-Protection" "1; mode=block"
                    "Referrer-Policy" "strict-origin-when-cross-origin"
                    "Content-Security-Policy" "default-src 'self'"
                    "Strict-Transport-Security" "max-age=31536000; includeSubDomains"
                    "Permissions-Policy" "geolocation=(), microphone=(), camera=()"
                }
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

### Header Sanitization

Remove sensitive headers using response and request header policies:

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
        matches { path-prefix "/" }
        upstream "backend"
        policies {
            // Remove server identification from responses
            response-headers {
                remove "Server" "X-Powered-By" "X-AspNet-Version"
            }
            // Remove internal routing headers from requests
            request-headers {
                remove "X-Forwarded-For" "X-Real-IP"
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

### Request Validation

Request validation can be implemented using WAF agents. See [Agents](/configuration/agents/) for configuration details.

## Access Control

IP-based access control and GeoIP blocking can be implemented using agents. See [Agents](/configuration/agents/) for details on building custom access control agents.

### Route-Level Access Control

Admin routes can be protected by requiring authentication via agents:

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
    route "admin" {
        matches { path-prefix "/admin/" }
        agents "auth"
        upstream "admin-backend"
    }
}

upstreams {
    upstream "admin-backend" {
        targets {
            target { address "127.0.0.1:3001" }
        }
    }
}

agents {
    agent "auth" type="auth" {
        unix-socket "/var/run/sentinel/auth.sock"
        events "request_headers"
        timeout-ms 50
        failure-mode "closed"
    }
}
```

## Rate Limiting

Rate limiting is implemented via agents. Configure a rate limiting agent for your routes:

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
    route "api" {
        matches { path-prefix "/api/" }
        agents "ratelimit"
        upstream "api-backend"
    }

    route "login" {
        matches { path "/auth/login" }
        agents "ratelimit-strict"
        upstream "auth-backend"
    }
}

upstreams {
    upstream "api-backend" {
        targets {
            target { address "127.0.0.1:3000" }
        }
    }
    upstream "auth-backend" {
        targets {
            target { address "127.0.0.1:3001" }
        }
    }
}

agents {
    // Standard rate limiting: 100 req/min
    agent "ratelimit" type="rate_limit" {
        unix-socket "/var/run/sentinel/ratelimit.sock"
        events "request_headers"
        timeout-ms 20
        failure-mode "open"
    }

    // Strict rate limiting for login: 5 req/min
    agent "ratelimit-strict" type="rate_limit" {
        unix-socket "/var/run/sentinel/ratelimit-strict.sock"
        events "request_headers"
        timeout-ms 20
        failure-mode "closed"
    }
}
```

## Security Logging

### Event Logging

Configure logging via the observability block:

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
```

Security events are logged automatically when agents block requests or when rate limits are triggered. Monitor these via your log aggregation system.

### Log Rotation

```bash
# /etc/logrotate.d/sentinel
/var/log/sentinel/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0640 sentinel sentinel
    postrotate
        kill -USR1 $(cat /var/run/sentinel.pid) 2>/dev/null || true
    endscript
}
```

## File System Security

### Directory Structure

```
/etc/sentinel/
├── config.kdl              # 0640 sentinel:sentinel
├── certs/
│   ├── server.crt          # 0644 sentinel:sentinel
│   ├── server.key          # 0600 sentinel:sentinel
│   ├── client.crt          # 0644 sentinel:sentinel
│   └── client.key          # 0600 sentinel:sentinel
└── geoip/
    └── GeoLite2-Country.mmdb  # 0644 sentinel:sentinel

/var/log/sentinel/          # 0750 sentinel:sentinel
/var/run/sentinel/          # 0755 sentinel:sentinel
```

### Permission Hardening

```bash
#!/bin/bash
SENTINEL_USER="sentinel"
SENTINEL_GROUP="sentinel"

# Configuration
chown -R root:$SENTINEL_GROUP /etc/sentinel
chmod 750 /etc/sentinel
chmod 640 /etc/sentinel/config.kdl

# Certificates
chmod 644 /etc/sentinel/certs/*.crt
chmod 600 /etc/sentinel/certs/*.key

# Logs
chown -R $SENTINEL_USER:$SENTINEL_GROUP /var/log/sentinel
chmod 750 /var/log/sentinel
```

### Systemd Security Options

```ini
# /etc/systemd/system/sentinel.service
[Service]
User=sentinel
Group=sentinel

# Security hardening
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=/var/log/sentinel /var/run/sentinel
ReadOnlyPaths=/etc/sentinel

# Capabilities
CapabilityBoundingSet=CAP_NET_BIND_SERVICE
AmbientCapabilities=CAP_NET_BIND_SERVICE

# System call filtering
SystemCallFilter=@system-service
SystemCallFilter=~@privileged @resources

# Memory protection
MemoryDenyWriteExecute=yes
```

## Network Security

### Firewall Configuration

```bash
# Allow incoming HTTP/HTTPS
iptables -A INPUT -p tcp --dport 80 -j ACCEPT
iptables -A INPUT -p tcp --dport 443 -j ACCEPT

# Allow metrics (internal only)
iptables -A INPUT -p tcp --dport 9090 -s 10.0.0.0/8 -j ACCEPT
iptables -A INPUT -p tcp --dport 9090 -j DROP

# Rate limit new connections
iptables -A INPUT -p tcp --syn -m limit --limit 100/s --limit-burst 200 -j ACCEPT
iptables -A INPUT -p tcp --syn -j DROP
```

## Security Checklist

### Pre-Deployment

**TLS Configuration**:
- [ ] TLS 1.2 minimum version enforced
- [ ] Strong cipher suites only
- [ ] Valid certificates installed
- [ ] Private keys have restricted permissions (0600)
- [ ] HSTS enabled (see [HSTS Validation](#hsts-validation) below)

**Access Control**:
- [ ] Admin endpoints restricted to internal IPs
- [ ] Rate limiting configured
- [ ] Request size limits configured

**Headers**:
- [ ] Security headers configured
- [ ] Server identification headers removed

**Logging**:
- [ ] Security events logged
- [ ] Log rotation configured

**System**:
- [ ] Run as non-root user
- [ ] File permissions hardened
- [ ] Systemd security options enabled
- [ ] Firewall rules configured

### Regular Security Tasks

| Task | Frequency |
|------|-----------|
| Review security logs | Daily |
| Check certificate expiry | Weekly |
| Update GeoIP database | Monthly |
| Security scan | Monthly |
| Audit configuration | Monthly |

## Security Scanning

```bash
# TLS configuration scan
testssl.sh --severity HIGH https://your-domain.com

# HTTP security headers check
curl -s -D- https://your-domain.com -o /dev/null | \
    grep -i "strict\|content-security\|x-frame"

# Check SSL Labs rating
# https://www.ssllabs.com/ssltest/
```

## See Also

- [TLS Configuration](../../configuration/listeners/#tls) - Listener TLS settings
- [mTLS to Upstreams](../../configuration/upstreams/#mtls) - Client certificate authentication
- [Rate Limiting](../../configuration/limits/) - Rate limiting configuration
- [Troubleshooting](../troubleshooting/) - Diagnosing security issues

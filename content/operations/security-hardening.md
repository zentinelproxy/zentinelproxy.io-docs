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
listeners {
    listener "https" {
        address "0.0.0.0:443"

        tls {
            cert "/etc/sentinel/certs/server.crt"
            key "/etc/sentinel/certs/server.key"

            // Minimum TLS 1.2 (TLS 1.3 preferred)
            min-version "1.2"

            // Strong cipher suites only
            ciphers [
                "TLS_AES_256_GCM_SHA384"
                "TLS_AES_128_GCM_SHA256"
                "TLS_CHACHA20_POLY1305_SHA256"
                "ECDHE-ECDSA-AES256-GCM-SHA384"
                "ECDHE-RSA-AES256-GCM-SHA384"
            ]

            // OCSP stapling
            ocsp-stapling true
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

### mTLS for Upstreams

Configure client certificates for backend authentication:

```kdl
upstreams {
    upstream "secure-backend" {
        target "10.0.0.1:8443"

        tls {
            sni "backend.internal"
            client-cert "/etc/sentinel/certs/client.crt"
            client-key "/etc/sentinel/certs/client.key"
            ca-cert "/etc/sentinel/certs/backend-ca.crt"
            insecure-skip-verify false
        }
    }
}
```

See [mTLS to Upstreams](/configuration/upstreams/#mtls) for detailed configuration.

## Header Security

### Security Response Headers

```kdl
policies {
    security-headers {
        x-frame-options "DENY"
        x-content-type-options "nosniff"
        x-xss-protection "1; mode=block"
        referrer-policy "strict-origin-when-cross-origin"
        content-security-policy "default-src 'self'"
        strict-transport-security "max-age=31536000; includeSubDomains"
        permissions-policy "geolocation=(), microphone=(), camera=()"
    }
}
```

### Header Sanitization

Remove sensitive headers:

```kdl
policies {
    header-sanitization {
        // Remove server identification
        remove-response-headers [
            "Server"
            "X-Powered-By"
            "X-AspNet-Version"
        ]

        // Remove internal routing headers from requests
        remove-request-headers [
            "X-Forwarded-For"  // Will be set by Sentinel
            "X-Real-IP"
        ]
    }
}
```

### Request Validation

```kdl
policies {
    request-validation {
        // Block requests with suspicious patterns
        block-paths [
            "*.php"
            "*/.git/*"
            "*/.env"
        ]

        // Require specific headers
        require-headers ["Host", "User-Agent"]
    }
}
```

## Access Control

### IP-Based Access Control

```kdl
policies {
    ip-access-control {
        default-action "allow"

        allow [
            "10.0.0.0/8"
            "192.168.0.0/16"
        ]

        block [
            "0.0.0.0/8"
            "169.254.0.0/16"
        ]
    }
}
```

### GeoIP Blocking

```kdl
policies {
    geo-access-control {
        database "/etc/sentinel/geoip/GeoLite2-Country.mmdb"
        allow-countries ["US", "CA", "GB", "DE", "FR"]
        action "block"
    }
}
```

### Route-Level Access Control

```kdl
routes {
    route "admin" {
        matches { path-prefix "/admin/" }

        policies {
            ip-access-control {
                allow ["10.0.0.0/8"]
                default-action "block"
            }
            require-headers ["Authorization"]
        }

        upstream "admin-backend"
    }
}
```

## Rate Limiting

### Global Rate Limits

```kdl
policies {
    global-rate-limit {
        requests-per-second 10000
        burst 1000
        max-connections 50000
        max-connections-per-ip 100
    }
}
```

### Per-Route Rate Limits

```kdl
routes {
    route "api" {
        matches { path-prefix "/api/" }

        policies {
            rate-limit {
                key "client_ip"
                requests-per-second 100
                burst 50
                action "block"
                status-code 429
            }
        }

        upstream "api-backend"
    }

    route "login" {
        matches { path "/auth/login" }

        policies {
            rate-limit {
                key "client_ip"
                requests-per-second 5
                burst 10
                action "block"
            }
        }

        upstream "auth-backend"
    }
}
```

## Security Logging

### Event Logging

```kdl
logging {
    security-log {
        path "/var/log/sentinel/security.log"
        format "json"

        events [
            "rate_limit_triggered"
            "ip_blocked"
            "geo_blocked"
            "waf_blocked"
            "auth_failure"
            "tls_handshake_failure"
        ]

        include-headers ["User-Agent", "X-Forwarded-For"]
        include-client-ip true
        include-request-id true
    }

    audit-log {
        path "/var/log/sentinel/audit.log"
        format "json"

        events [
            "config_reload"
            "upstream_health_change"
            "circuit_breaker_state_change"
        ]
    }
}
```

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
- [ ] HSTS enabled

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

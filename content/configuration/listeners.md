+++
title = "Listeners"
weight = 3
+++

The `listeners` block defines network endpoints where Sentinel accepts incoming connections. Each listener binds to an address, specifies a protocol, and optionally configures TLS.

## Basic Configuration

```kdl
listeners {
    listener "http" {
        address "0.0.0.0:8080"
        protocol "http"
    }

    listener "https" {
        address "0.0.0.0:443"
        protocol "https"
        tls {
            cert-file "/etc/sentinel/certs/server.crt"
            key-file "/etc/sentinel/certs/server.key"
        }
    }
}
```

## Listener Options

### Address

```kdl
listener "api" {
    address "0.0.0.0:8080"
}
```

Socket address in `host:port` format:

| Format | Example | Use Case |
|--------|---------|----------|
| All interfaces | `0.0.0.0:8080` | Production, accept from anywhere |
| Localhost only | `127.0.0.1:8080` | Admin endpoints, local testing |
| IPv6 all | `[::]:8080` | IPv6 networks |
| IPv6 localhost | `[::1]:8080` | IPv6 local only |
| Specific interface | `10.0.1.5:8080` | Multi-homed servers |

### Protocol

```kdl
listener "secure" {
    protocol "https"
}
```

| Protocol | Description | TLS Required |
|----------|-------------|--------------|
| `http` | Plain HTTP/1.1 | No |
| `https` | HTTP/1.1 over TLS | Yes |
| `h2` | HTTP/2 (with TLS via ALPN) | Yes |
| `h3` | HTTP/3 (QUIC) | Yes |

### Timeouts

```kdl
listener "api" {
    address "0.0.0.0:8080"
    protocol "http"
    request-timeout-secs 60
    keepalive-timeout-secs 75
}
```

| Setting | Default | Description |
|---------|---------|-------------|
| `request-timeout-secs` | `60` | Maximum time to receive complete request |
| `keepalive-timeout-secs` | `75` | Idle connection timeout |

**Timeout recommendations:**

| Scenario | Request Timeout | Keep-Alive |
|----------|-----------------|------------|
| API traffic | 30-60s | 60-120s |
| File uploads | 300s+ | 75s |
| WebSocket upgrade | 60s | 3600s+ |
| Internal services | 10-30s | 30s |

### HTTP/2 Settings

```kdl
listener "h2" {
    address "0.0.0.0:443"
    protocol "h2"
    max-concurrent-streams 100
    tls {
        cert-file "/etc/sentinel/certs/server.crt"
        key-file "/etc/sentinel/certs/server.key"
    }
}
```

| Setting | Default | Description |
|---------|---------|-------------|
| `max-concurrent-streams` | `100` | Maximum concurrent HTTP/2 streams per connection |

### Default Route

```kdl
listener "api" {
    address "0.0.0.0:8080"
    protocol "http"
    default-route "fallback"
}
```

Route to use when no other route matches. If not set and no route matches, Sentinel returns 404.

## TLS Configuration

### Basic TLS

```kdl
listener "https" {
    address "0.0.0.0:443"
    protocol "https"
    tls {
        cert-file "/etc/sentinel/certs/server.crt"
        key-file "/etc/sentinel/certs/server.key"
    }
}
```

### TLS Options Reference

```kdl
tls {
    // Required
    cert-file "/path/to/cert.pem"
    key-file "/path/to/key.pem"

    // Version control
    min-version "1.2"        // Minimum: 1.0, 1.1, 1.2, 1.3
    max-version "1.3"        // Maximum TLS version

    // Client authentication (mTLS)
    ca-file "/path/to/ca.pem"
    client-auth true

    // Performance
    session-resumption true  // TLS session tickets
    ocsp-stapling true       // OCSP stapling

    // Cipher control (optional)
    cipher-suites "TLS_AES_256_GCM_SHA384" "TLS_CHACHA20_POLY1305_SHA256"
}
```

### TLS Version

| Version | Status | Notes |
|---------|--------|-------|
| `1.0` | Deprecated | Avoid unless required for legacy clients |
| `1.1` | Deprecated | Avoid unless required for legacy clients |
| `1.2` | **Default minimum** | Good balance of compatibility and security |
| `1.3` | Recommended | Best performance and security |

**Production recommendation:**

```kdl
tls {
    min-version "1.2"
    max-version "1.3"
}
```

### Client Authentication (mTLS)

For mutual TLS, require clients to present certificates:

```kdl
listener "internal-api" {
    address "0.0.0.0:8443"
    protocol "https"
    tls {
        cert-file "/etc/sentinel/certs/server.crt"
        key-file "/etc/sentinel/certs/server.key"
        ca-file "/etc/sentinel/certs/client-ca.crt"
        client-auth true
    }
}
```

Client certificates are validated against the CA certificate. Failed validation results in TLS handshake failure.

### Session Resumption

```kdl
tls {
    session-resumption true  // Default: true
}
```

Enables TLS session tickets for faster reconnections. Reduces handshake overhead for returning clients.

**Security note:** Session tickets are encrypted with server-side keys that rotate automatically.

### OCSP Stapling

```kdl
tls {
    ocsp-stapling true  // Default: true
}
```

Server fetches and staples OCSP responses, proving certificate validity without clients contacting the CA.

Benefits:
- Faster TLS handshakes
- Better client privacy
- Reduced CA load

### Custom Cipher Suites

```kdl
tls {
    cipher-suites "TLS_AES_256_GCM_SHA384" "TLS_CHACHA20_POLY1305_SHA256"
}
```

Override default cipher suite selection. Leave empty to use secure defaults.

**TLS 1.3 cipher suites:**
- `TLS_AES_256_GCM_SHA384`
- `TLS_AES_128_GCM_SHA256`
- `TLS_CHACHA20_POLY1305_SHA256`

**TLS 1.2 cipher suites (recommended):**
- `TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384`
- `TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256`
- `TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305_SHA256`

## SNI (Server Name Indication)

Serve different certificates based on the hostname the client requests. This enables hosting multiple domains on a single IP address.

### Basic SNI Configuration

```kdl
listener "https" {
    address "0.0.0.0:443"
    protocol "https"
    tls {
        // Default certificate (when no SNI match)
        cert-file "/etc/sentinel/certs/default.crt"
        key-file "/etc/sentinel/certs/default.key"

        // Additional certificates for SNI
        additional-certs {
            sni-cert {
                hostnames "example.com" "www.example.com"
                cert-file "/etc/sentinel/certs/example.crt"
                key-file "/etc/sentinel/certs/example.key"
            }

            sni-cert {
                hostnames "api.example.com"
                cert-file "/etc/sentinel/certs/api.crt"
                key-file "/etc/sentinel/certs/api.key"
            }

            sni-cert {
                hostnames "*.staging.example.com"
                cert-file "/etc/sentinel/certs/staging-wildcard.crt"
                key-file "/etc/sentinel/certs/staging-wildcard.key"
            }
        }
    }
}
```

### SNI Hostname Patterns

| Pattern | Matches |
|---------|---------|
| `example.com` | Exact match only |
| `www.example.com` | Exact match only |
| `*.example.com` | Any single subdomain (e.g., `api.example.com`, `www.example.com`) |
| `*.*.example.com` | Two subdomain levels |

### SNI Resolution Order

1. Exact hostname match
2. Wildcard pattern match (most specific wins)
3. Default certificate

### Multi-Domain Example

```kdl
listener "https" {
    address "0.0.0.0:443"
    protocol "https"
    tls {
        // Default for unmatched hostnames
        cert-file "/etc/sentinel/certs/default.crt"
        key-file "/etc/sentinel/certs/default.key"

        additional-certs {
            // Production domains
            sni-cert {
                hostnames "myapp.com" "www.myapp.com"
                cert-file "/etc/sentinel/certs/myapp.crt"
                key-file "/etc/sentinel/certs/myapp.key"
            }

            // API subdomain with separate cert
            sni-cert {
                hostnames "api.myapp.com"
                cert-file "/etc/sentinel/certs/api.myapp.crt"
                key-file "/etc/sentinel/certs/api.myapp.key"
            }

            // Customer domains
            sni-cert {
                hostnames "customer1.myapp.com" "customer1-custom.com"
                cert-file "/etc/sentinel/certs/customer1.crt"
                key-file "/etc/sentinel/certs/customer1.key"
            }

            // Wildcard for all other subdomains
            sni-cert {
                hostnames "*.myapp.com"
                cert-file "/etc/sentinel/certs/wildcard.myapp.crt"
                key-file "/etc/sentinel/certs/wildcard.myapp.key"
            }
        }
    }
}
```

### Certificate Hot Reload

All SNI certificates are reloaded during configuration reload:

```bash
# Update certificates
cp new-cert.crt /etc/sentinel/certs/example.crt
cp new-key.key /etc/sentinel/certs/example.key

# Reload configuration (graceful)
kill -HUP $(cat /var/run/sentinel.pid)
```

Connections in progress continue with old certificates. New connections use updated certificates.

## Multiple Listeners

Run multiple listeners for different purposes:

```kdl
listeners {
    // Public HTTPS
    listener "public" {
        address "0.0.0.0:443"
        protocol "https"
        request-timeout-secs 30
        tls {
            cert-file "/etc/sentinel/certs/public.crt"
            key-file "/etc/sentinel/certs/public.key"
            min-version "1.2"
        }
    }

    // HTTP redirect to HTTPS
    listener "http-redirect" {
        address "0.0.0.0:80"
        protocol "http"
        default-route "https-redirect"
    }

    // Admin interface (localhost only)
    listener "admin" {
        address "127.0.0.1:9090"
        protocol "http"
    }

    // Internal mTLS API
    listener "internal" {
        address "10.0.0.5:8443"
        protocol "https"
        tls {
            cert-file "/etc/sentinel/certs/internal.crt"
            key-file "/etc/sentinel/certs/internal.key"
            ca-file "/etc/sentinel/certs/internal-ca.crt"
            client-auth true
        }
    }
}
```

## Certificate Management

### Certificate Formats

Sentinel accepts PEM-encoded certificates and keys:

```
/etc/sentinel/certs/
├── server.crt      # Certificate (PEM)
├── server.key      # Private key (PEM)
├── chain.crt       # Intermediate certificates (optional)
└── ca.crt          # CA certificate for client auth
```

### Full Chain Certificates

For proper certificate chain validation, include intermediates in the cert file:

```bash
cat server.crt intermediate.crt > fullchain.crt
```

Then reference the full chain:

```kdl
tls {
    cert-file "/etc/sentinel/certs/fullchain.crt"
    key-file "/etc/sentinel/certs/server.key"
}
```

### Certificate Reload

Certificates are reloaded on configuration reload (SIGHUP):

```bash
# Update certificates, then reload
cp new-cert.crt /etc/sentinel/certs/server.crt
cp new-key.key /etc/sentinel/certs/server.key
kill -HUP $(cat /var/run/sentinel.pid)
```

## Complete Example

```kdl
listeners {
    // Production HTTPS with modern TLS
    listener "https" {
        address "0.0.0.0:443"
        protocol "https"
        request-timeout-secs 60
        keepalive-timeout-secs 120
        max-concurrent-streams 200

        tls {
            cert-file "/etc/sentinel/certs/fullchain.crt"
            key-file "/etc/sentinel/certs/server.key"
            min-version "1.2"
            max-version "1.3"
            ocsp-stapling true
            session-resumption true
        }
    }

    // HTTP to HTTPS redirect
    listener "http" {
        address "0.0.0.0:80"
        protocol "http"
        request-timeout-secs 5
        default-route "redirect-https"
    }

    // Admin and metrics (internal only)
    listener "admin" {
        address "127.0.0.1:9090"
        protocol "http"
        request-timeout-secs 10
    }
}
```

## Default Values

| Setting | Default |
|---------|---------|
| `request-timeout-secs` | `60` |
| `keepalive-timeout-secs` | `75` |
| `max-concurrent-streams` | `100` |
| `tls.min-version` | `1.2` |
| `tls.ocsp-stapling` | `true` |
| `tls.session-resumption` | `true` |
| `tls.client-auth` | `false` |

## Troubleshooting

### Port Already in Use

```
Error: Address already in use (os error 98)
```

Another process is using the port:

```bash
# Find what's using the port
lsof -i :8080
# or
ss -tlnp | grep 8080
```

### Permission Denied (Privileged Ports)

```
Error: Permission denied (os error 13)
```

Ports below 1024 require root or capabilities:

```bash
# Option 1: Run as root (not recommended)
sudo sentinel

# Option 2: Grant capability (recommended)
sudo setcap cap_net_bind_service=+ep /usr/local/bin/sentinel

# Option 3: Use user/group in config
server {
    user "sentinel"
    group "sentinel"
}
```

### Certificate Issues

```
Error: Invalid certificate chain
```

- Verify certificate format is PEM
- Include intermediate certificates in cert file
- Check certificate dates: `openssl x509 -in cert.crt -noout -dates`
- Verify key matches certificate: `openssl x509 -noout -modulus -in cert.crt | md5sum` vs `openssl rsa -noout -modulus -in key.key | md5sum`

## Next Steps

- [Routes](../routes/) - Request routing rules
- [Upstreams](../upstreams/) - Backend server configuration

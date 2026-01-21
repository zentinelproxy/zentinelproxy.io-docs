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
system {
    worker-threads 0
}

listeners {
    listener "http" {
        address "0.0.0.0:8080"
        protocol "http"
    }
}

tls {
    // Required
    cert-file "/path/to/cert.pem"
    key-file "/path/to/key.pem"

    // Version control
    min-version "1.2"        // Minimum: 1.0, 1.1, 1.2, 1.3
    max-version "1.3"        // Maximum TLS version

    // Client authentication (mTLS)
    ca-file "/path/to/ca.pem"
    client-auth #true

    // Performance
    session-resumption #true  // TLS session tickets
    ocsp-stapling #true       // OCSP stapling

    // Cipher control (optional)
    cipher-suites "TLS_AES_256_GCM_SHA384" "TLS_CHACHA20_POLY1305_SHA256"
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
        client-auth #true
    }
}
```

Client certificates are validated against the CA certificate. Failed validation results in TLS handshake failure.

### Session Resumption

```kdl
system {
    worker-threads 0
}

listeners {
    listener "http" {

        tls {
            session-resumption #true  // Default: true
        }
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

```

Enables TLS session tickets for faster reconnections. Reduces handshake overhead for returning clients.

**Security note:** Session tickets are encrypted with server-side keys that rotate automatically.

### OCSP Stapling

```kdl
system {
    worker-threads 0
}

listeners {
    listener "http" {

        tls {
            ocsp-stapling #true  // Default: true
        }
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

## ACME (Automatic Certificate Management)

Sentinel supports automatic TLS certificate management using the ACME protocol (RFC 8555). This eliminates manual certificate management by automatically requesting, validating, and renewing certificates from Let's Encrypt.

### Basic ACME Configuration

```kdl
listener "https" {
    address "0.0.0.0:443"
    protocol "https"
    tls {
        acme {
            email "admin@example.com"
            domains "example.com" "www.example.com"
        }
    }
}
```

With ACME enabled, Sentinel will:
1. Create or restore a Let's Encrypt account
2. Request certificates for configured domains
3. Complete HTTP-01 domain validation automatically
4. Store certificates securely on disk
5. Renew certificates before expiration
6. Hot-reload certificates without proxy restart

### ACME Options Reference

```kdl
listener "https" {
    address "0.0.0.0:443"
    protocol "https"
    tls {
        acme {
            // Required
            email "admin@example.com"
            domains "example.com" "www.example.com"

            // Optional
            staging false                           // Use staging environment for testing
            storage "/var/lib/sentinel/acme"        // Certificate storage directory
            renew-before-days 30                    // Days before expiry to renew
        }
    }
}
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `email` | string | **required** | Contact email for Let's Encrypt account |
| `domains` | string[] | **required** | Domains to include in certificate |
| `staging` | bool | `false` | Use Let's Encrypt staging environment |
| `storage` | path | `/var/lib/sentinel/acme` | Directory for certificates and credentials |
| `renew-before-days` | u32 | `30` | Days before expiry to trigger renewal |
| `challenge-type` | string | `"http-01"` | Challenge type: `http-01` or `dns-01` |
| `dns-provider` | block | - | DNS provider config (required for `dns-01`) |

### HTTP-01 Challenge (Default)

ACME uses HTTP-01 challenges to validate domain ownership. Sentinel automatically handles these challenges by serving responses at `/.well-known/acme-challenge/`.

**Requirements:**
- Port 80 must be accessible from the internet
- DNS must point to the server running Sentinel
- Firewall must allow incoming HTTP traffic

For HTTP-01 challenges to work, you typically need an HTTP listener on port 80:

```kdl
listeners {
    // HTTP listener for ACME challenges (and optional redirect)
    listener "http" {
        address "0.0.0.0:80"
        protocol "http"
    }

    // HTTPS listener with ACME
    listener "https" {
        address "0.0.0.0:443"
        protocol "https"
        tls {
            acme {
                email "admin@example.com"
                domains "example.com"
            }
        }
    }
}
```

### DNS-01 Challenge (For Wildcard Certificates)

DNS-01 challenges validate domain ownership by creating TXT records in DNS. This is **required for wildcard certificates** and works even when port 80 is not accessible.

```kdl
listener "https" {
    address "0.0.0.0:443"
    protocol "https"
    tls {
        acme {
            email "admin@example.com"
            domains "example.com" "*.example.com"
            challenge-type "dns-01"

            dns-provider {
                type "hetzner"
                credentials-file "/etc/sentinel/secrets/hetzner-dns.json"
                api-timeout-secs 30

                propagation {
                    initial-delay-secs 10
                    check-interval-secs 5
                    timeout-secs 120
                    nameservers "8.8.8.8" "1.1.1.1"
                }
            }
        }
    }
}
```

**DNS-01 Flow:**
1. Sentinel creates a TXT record at `_acme-challenge.example.com`
2. Waits for DNS propagation (checks against configured nameservers)
3. Notifies Let's Encrypt to validate
4. Cleans up TXT records after validation

**Supported DNS Providers:**

| Provider | Type | Description |
|----------|------|-------------|
| Hetzner | `hetzner` | Hetzner DNS API |
| Webhook | `webhook` | Generic webhook for custom integrations |

#### Hetzner DNS Provider

```kdl
dns-provider {
    type "hetzner"
    credentials-file "/etc/sentinel/secrets/hetzner.json"
    // or
    credentials-env "HETZNER_DNS_TOKEN"
}
```

Credential file format:
```json
{"token": "your-hetzner-dns-api-token"}
```

#### Webhook Provider (Custom DNS)

For custom DNS integrations, use the webhook provider:

```kdl
dns-provider {
    type "webhook"
    url "https://dns-api.internal/v1"
    auth-header "X-API-Key"
    credentials-file "/etc/sentinel/secrets/webhook.json"
}
```

The webhook provider makes HTTP calls:
- `POST /records` - Create TXT record (returns `{"record_id": "..."}`)
- `DELETE /records/{record_id}` - Delete record
- `GET /domains/{domain}/supported` - Check domain support

#### DNS Provider Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `type` | string | **required** | Provider type: `hetzner`, `webhook` |
| `credentials-file` | path | - | Path to credentials JSON file |
| `credentials-env` | string | - | Environment variable with credentials |
| `api-timeout-secs` | u64 | `30` | API request timeout |
| `url` | string | - | Webhook URL (webhook provider only) |
| `auth-header` | string | - | Auth header name (webhook provider only) |

#### Propagation Check Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `initial-delay-secs` | u64 | `10` | Wait before first DNS check |
| `check-interval-secs` | u64 | `5` | Interval between checks |
| `timeout-secs` | u64 | `120` | Max time to wait for propagation |
| `nameservers` | string[] | public DNS | DNS servers to query |

#### Credential File Formats

**Token format (Hetzner, simple webhooks):**
```json
{"token": "your-api-token"}
```

**Key/Secret format:**
```json
{"api_key": "your-key", "api_secret": "your-secret"}
```

**Plain text (entire file is the token):**
```
your-api-token
```

Security: Credential files should have mode `0600` or `0400`.

### Staging Environment

Use Let's Encrypt's staging environment for testing to avoid rate limits:

```kdl
tls {
    acme {
        email "admin@example.com"
        domains "example.com"
        staging true  // Uses staging, certificates won't be trusted by browsers
    }
}
```

**Rate limits (production):**
- 50 certificates per registered domain per week
- 5 duplicate certificates per week
- 300 new orders per account per 3 hours

Staging has much higher limits for testing.

### Certificate Storage

ACME stores certificates and account credentials on disk:

```
/var/lib/sentinel/acme/
├── credentials.json      # ACME account credentials (keep secure)
├── account.json          # Account metadata
└── domains/
    └── example.com/
        ├── cert.pem      # Certificate chain
        ├── key.pem       # Private key (mode 0600)
        └── meta.json     # Expiry, issued date, domains
```

**Security:**
- Storage directory created with mode `0700`
- Private keys stored with mode `0600`
- Keep `credentials.json` secure—it contains your account private key

### Certificate Renewal

Certificates are automatically renewed when they're within `renew-before-days` of expiration:

- Default renewal window: 30 days before expiry
- Renewal checks run every 12 hours
- Let's Encrypt certificates are valid for 90 days
- After renewal, certificates are hot-reloaded without restart

### Combining ACME with Manual Certificates

You can use ACME alongside manually managed certificates:

```kdl
listener "https" {
    address "0.0.0.0:443"
    protocol "https"
    tls {
        // Manual certificates (takes precedence if both exist)
        cert-file "/etc/sentinel/certs/manual.crt"
        key-file "/etc/sentinel/certs/manual.key"

        // ACME for automatic management
        acme {
            email "admin@example.com"
            domains "auto.example.com"
        }

        // SNI for domain-specific certificates
        additional-certs {
            sni-cert {
                hostnames "api.example.com"
                cert-file "/etc/sentinel/certs/api.crt"
                key-file "/etc/sentinel/certs/api.key"
            }
        }
    }
}
```

When both ACME and manual certificates are configured, manual certificates are used if present. ACME certificates are stored and used as fallback or for specified domains.

### Multi-Domain Certificates

Request a single certificate covering multiple domains:

```kdl
tls {
    acme {
        email "admin@example.com"
        domains "example.com" "www.example.com" "api.example.com" "cdn.example.com"
    }
}
```

All domains must pass HTTP-01 validation and point to the server.

### ACME Troubleshooting

#### Challenge Failed

```
Error: ACME challenge validation failed for domain 'example.com'
```

- Verify DNS points to this server: `dig +short example.com`
- Ensure port 80 is accessible from the internet
- Check firewall allows incoming HTTP traffic
- Verify no other service is handling `/.well-known/acme-challenge/`

#### Rate Limit Exceeded

```
Error: Rate limit exceeded
```

- Wait for the rate limit window to reset (typically 1 week)
- Use `staging true` for testing
- Consolidate multiple domains into one certificate request

#### Storage Permission Denied

```
Error: Permission denied writing to storage directory
```

- Ensure the Sentinel process has write access to the storage directory
- Check directory ownership: `chown sentinel:sentinel /var/lib/sentinel/acme`
- Verify parent directories exist and are accessible

#### Certificate Not Renewing

Check the Sentinel logs for renewal status. Renewals are attempted:
- Every 12 hours (check interval)
- When certificate is within `renew-before-days` of expiry

Manually trigger a reload to force renewal check:
```bash
kill -HUP $(cat /var/run/sentinel.pid)
```

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
            client-auth #true
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
system {
    worker-threads 0
}

listeners {
    // Production HTTPS with modern TLS
    listener "https" {

                tls {
                    cert-file "/etc/sentinel/certs/fullchain.crt"
                    key-file "/etc/sentinel/certs/server.key"
                    min-version "1.2"
                    max-version "1.3"
                    ocsp-stapling #true
                    session-resumption #true
                }
        address "0.0.0.0:443"
        protocol "https"
        request-timeout-secs 60
        keepalive-timeout-secs 120
        max-concurrent-streams 200

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
| `tls.acme.staging` | `false` |
| `tls.acme.storage` | `/var/lib/sentinel/acme` |
| `tls.acme.renew-before-days` | `30` |
| `tls.acme.challenge-type` | `"http-01"` |
| `tls.acme.dns-provider.api-timeout-secs` | `30` |
| `tls.acme.dns-provider.propagation.initial-delay-secs` | `10` |
| `tls.acme.dns-provider.propagation.check-interval-secs` | `5` |
| `tls.acme.dns-provider.propagation.timeout-secs` | `120` |

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
system {
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

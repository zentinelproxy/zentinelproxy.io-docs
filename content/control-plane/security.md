+++
title = "Security"
weight = 7
+++

WAF, auth policies, bundle signing, and encryption in the Zentinel Control Plane.

## Web Application Firewall

~60 built-in rules based on the OWASP Core Rule Set (CRS).

### Rule Categories

| Category | Rule IDs | Description |
|----------|----------|-------------|
| SQL Injection | CRS-942xxx | libinjection, tautologies, union-based, blind |
| XSS | CRS-941xxx | Script tags, event handlers, JS URIs, DOM vectors |
| Local File Inclusion | CRS-930xxx | Path traversal, OS file access, null bytes |
| Remote File Inclusion | CRS-931xxx | URL params, PHP wrappers, off-domain refs |
| Remote Code Execution | CRS-932xxx | Command injection, PowerShell, Shellshock |
| Scanner Detection | CRS-913xxx | Vulnerability scanners, bot detection |
| Protocol Violations | CRS-920xxx | Invalid HTTP, smuggling, URI length |
| Data Leak Prevention | CRS-950xxx | Credit cards, SSNs, SQL errors |

### WAF Policies

Group rules with configuration: mode (`block`/`detect_only`/`challenge`), sensitivity (`low`-`paranoid`), default action, enabled categories, body/header/URI size limits.

Per-rule overrides supported (e.g., disable a false-positive rule).

### WAF Analytics

- Event tracking: every blocked/logged request recorded
- 14-day statistical baselines (computed hourly)
- Z-score anomaly detection (>2.5σ) for spikes, new vectors, IP bursts

## Auth Policies

Authentication policies for services, enforced by the proxy at request time:

| Type | Description |
|------|-------------|
| `jwt` | JWT validation — issuer, audience, algorithms, JWKS URL |
| `api_key` | API key from headers or query params |
| `basic` | HTTP Basic Authentication |
| `oauth2` | Token introspection |
| `oidc` | OpenID Connect with discovery |
| `composite` | Combine policies with AND/OR logic |

## Bundle Signing

Ed25519 cryptographic signing for integrity and authenticity:

1. Generate key pair
2. Compiler signs bundle archive during compilation
3. Nodes/operators verify against public key
4. Key ID in signature enables rotation

Verify via API:

```bash
curl http://localhost:4000/api/v1/projects/my-project/bundles/:id/verify \
  -H "Authorization: Bearer $API_KEY"
```

## Encryption at Rest

All sensitive data encrypted with AES-256-GCM:

| Data | AAD |
|------|-----|
| TLS private keys | `"zentinel-cert-key"` |
| Signing keys | `"ZentinelCp.Auth.Encryption"` |
| Secret values | `"zentinel-secret"` |
| ACME account keys | `"zentinel-cert-key"` |

Key derived from `secret_key_base` via SHA256. Each value has unique 12-byte IV + 16-byte auth tag.

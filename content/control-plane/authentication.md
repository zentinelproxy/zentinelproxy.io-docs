+++
title = "Authentication"
weight = 3
+++

Authentication and authorization mechanisms in the Zentinel Control Plane.

## Overview

| Method | Used By | Header |
|--------|---------|--------|
| Session (cookie) | Web UI users | Browser cookie |
| API key | Operators, CI/CD | `Authorization: Bearer <key>` |
| Static node key | Proxy nodes (simple) | `X-Zentinel-Node-Key: <key>` |
| JWT | Proxy nodes (recommended) | `Authorization: Bearer <jwt>` |

## API Key Authentication

API keys authenticate operator and CI/CD requests to the REST API.

### Key Properties

- 32 bytes of cryptographically random data, Base64-URL encoded
- SHA256 hash stored — raw key shown **once** at creation
- Optional project scoping and expiration date

### Scopes

| Scope | Access |
|-------|--------|
| `nodes:read` | List nodes, view details, stats |
| `nodes:write` | Register, delete, drift operations |
| `bundles:read` | List, view, download, verify, SBOM |
| `bundles:write` | Create, assign, revoke |
| `rollouts:read` | List, view rollout details |
| `rollouts:write` | Create, pause, resume, cancel, rollback |
| `services:read` | List services, upstreams, certs, etc. |
| `services:write` | Create/update/delete services |
| `api_keys:admin` | Manage API keys |

Keys with no scopes have full access (backward compatibility).

### Lifecycle

```text
Created (active) → Revoked (immediate) → Deleted
                 → Expired (auto, past expires_at)
```

## Node Authentication

### Static Node Key

Generated at registration (32 bytes, Base64-URL). Simple shared secret:

```bash
curl -X POST http://cp:4000/api/v1/nodes/$NODE_ID/heartbeat \
  -H "X-Zentinel-Node-Key: $NODE_KEY" \
  -H "Content-Type: application/json" \
  -d '{"health": {"cpu_percent": 45}}'
```

### JWT Token (Recommended)

Exchange the static key for a short-lived JWT (12-hour expiry):

```bash
curl -X POST http://cp:4000/api/v1/nodes/$NODE_ID/token \
  -H "X-Zentinel-Node-Key: $NODE_KEY"
```

```json
{"token": "eyJ...", "expires_at": "2026-02-21T19:00:00Z"}
```

JWT claims: `sub` (node ID), `prj` (project), `org` (organization), `kid` (signing key ID), `exp` (expiration).

Algorithm: Ed25519 (EDDSA). Signing keys managed per organization.

## TOTP Multi-Factor Authentication

Optional TOTP-based MFA:

1. Generate secret + QR code at `/profile`
2. Scan with authenticator app
3. 10 single-use recovery codes generated
4. Login requires TOTP code after password

## SSO Integration

### OIDC (OpenID Connect)

Authorization Code with PKCE. Configure: `client_id`, `client_secret`, `issuer`, `authorize_url`, `token_url`, `userinfo_url`, `scopes`, `group_mapping`.

### SAML 2.0

Configure: `idp_metadata_url`, `idp_sso_url`, `idp_cert_pem`, `sp_entity_id`, `assertion_consumer_service_url`, `group_mapping`.

### Just-In-Time Provisioning

First SSO login auto-creates user account and org membership with role from group mapping:

```json
{
  "engineering-admins": "admin",
  "engineering": "operator",
  "default": "reader"
}
```

## User Roles

| Role | Permissions |
|------|-------------|
| `admin` | Full org control — members, projects, signing keys, API keys |
| `operator` | Manage projects, bundles, rollouts, services, nodes |
| `reader` | Read-only access |

Roles are per-organization and hierarchical: admin > operator > reader.

## Rate Limiting

Token-bucket rate limiting on API endpoints:

- Keyed by API key ID or client IP
- Response headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`
- 429 response with `retry_after` when exceeded

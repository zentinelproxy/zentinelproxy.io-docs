+++
title = "Configuration"
weight = 5
+++

Service definitions, upstreams, TLS, middlewares, and environment variables for the Zentinel Control Plane.

## Services

Services are the primary configuration unit. Each maps an HTTP route path to a backend.

### Route Types

| Mode | Description |
|------|-------------|
| **Upstream URL** | Forward to a single backend |
| **Upstream Group** | Load-balanced pool of backends |
| **Redirect** | HTTP redirect |
| **Static Response** | Fixed status + body |

### Service Types

| Type | Description |
|------|-------------|
| `standard` | HTTP/HTTPS reverse proxy (default) |
| `inference` | LLM inference proxy (OpenAI, Anthropic, generic) |
| `grpc` | gRPC proxy |
| `websocket` | WebSocket with upgrade support |
| `graphql` | GraphQL-aware proxy |
| `streaming` | SSE / streaming proxy |

### Options

Timeout, retry policy, caching, rate limiting, health checks, CORS, compression, path rewriting, traffic splitting, access control, security headers, request/response transforms.

Services can attach: **certificates** (TLS), **auth policies**, **WAF policies**, **OpenAPI specs**.

## Upstream Groups

Load-balanced pools with algorithms: `round_robin`, `least_conn`, `ip_hash`, `consistent_hash`, `weighted`, `random`.

Targets have: host, port, weight, max_connections, enabled flag.

Features: health checks, sticky sessions (cookie-based), circuit breaker (closed/open/half_open), trust stores for backend TLS verification.

## TLS Certificates

Upload PEM cert + key + optional CA chain. Private keys encrypted at rest (AES-256-GCM).

Status tracking: `active`, `expiring_soon`, `expired`, `revoked`.

### ACME / Let's Encrypt

Automatic renewal via HTTP-01 challenges at `/.well-known/acme-challenge/:token`.

### Internal CA

Per-project internal CA for mTLS. CA certificates included in compiled bundles automatically.

## Middlewares

Reusable config blocks attached to services with per-service ordering and config overrides:

`rate_limit`, `cache`, `cors`, `compression`, `headers`, `access_control`, `security`, `path_rewrite`, `request_transform`, `response_transform`, `auth`, `custom`.

## Secrets

Encrypted at rest (AES-256-GCM). Never exposed in API responses. Environment-scoped with rotation tracking.

## GitOps Integration

Link a project to a Git repository. Push to configured branch triggers automatic bundle compilation.

| Setting | Description |
|---------|-------------|
| `repository` | Owner/repo (e.g., `acme/proxy-config`) |
| `branch` | Target branch (default: `main`) |
| `config_path` | KDL config file path (default: `zentinel.kdl`) |

Supported: GitHub, GitLab, Bitbucket, Gitea, generic webhooks.

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Prod | — | PostgreSQL connection (`ecto://user:pass@host:5432/db`) |
| `SECRET_KEY_BASE` | Prod | — | Phoenix secret (generate: `mix phx.gen.secret`) |
| `PHX_HOST` | Prod | `localhost` | Public hostname |
| `PORT` | No | `4000` | HTTP port |
| `S3_BUCKET` | Yes | `zentinel-bundles` | Bundle storage bucket |
| `S3_ENDPOINT` | Yes | `http://localhost:9000` | S3/MinIO endpoint |
| `S3_ACCESS_KEY_ID` | Yes | — | S3 access key |
| `S3_SECRET_ACCESS_KEY` | Yes | — | S3 secret key |
| `S3_REGION` | No | `us-east-1` | S3 region |
| `ZENTINEL_BINARY` | No | `zentinel` | Path to zentinel CLI |
| `GITHUB_WEBHOOK_SECRET` | No | — | GitHub webhook HMAC secret |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | No | — | OpenTelemetry endpoint |
| `FORCE_SSL` | No | `false` | Redirect HTTP → HTTPS |
| `POOL_SIZE` | No | `10` | DB connection pool size |

## Bundle Signing

Optional Ed25519 signing for bundle integrity:

```elixir
config :zentinel_cp, :bundle_signing,
  enabled: true,
  private_key_path: "/secrets/signing-key.pem",
  public_key_path: "/secrets/signing-key.pub",
  key_id: "key-2024-01"
```

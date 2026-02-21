+++
title = "API Reference"
weight = 4
+++

REST API, Node API, and GraphQL endpoints for the Zentinel Control Plane.

Base URL: `/api/v1`

## Authentication

| Consumer | Method | Header |
|----------|--------|--------|
| Operator / CI | API key | `Authorization: Bearer <api_key>` |
| Node (simple) | Static key | `X-Zentinel-Node-Key: <key>` |
| Node (recommended) | JWT | `Authorization: Bearer <jwt>` |
| Webhooks | HMAC signature | Provider-specific |

## Operator API

All under `/api/v1/projects/:project_slug/`.

### Bundles

```text
POST   /bundles              Create bundle (bundles:write)
GET    /bundles              List bundles (bundles:read)
GET    /bundles/:id          Get bundle (bundles:read)
GET    /bundles/:id/download Presigned S3 URL (bundles:read)
POST   /bundles/:id/assign   Assign to nodes (bundles:write)
POST   /bundles/:id/revoke   Prevent distribution (bundles:write)
GET    /bundles/:id/verify   Verify signature (bundles:read)
GET    /bundles/:id/sbom     CycloneDX SBOM (bundles:read)
```

**Create bundle example:**

```bash
curl -X POST http://localhost:4000/api/v1/projects/my-project/bundles \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"config_source": "route \"/api/*\" {\n  upstream \"http://api:8080\"\n}", "version": "1.0.0"}'
```

### Rollouts

```text
POST   /rollouts                    Create (rollouts:write)
GET    /rollouts                    List (rollouts:read)
GET    /rollouts/:id                Get with progress (rollouts:read)
POST   /rollouts/:id/pause          Pause (rollouts:write)
POST   /rollouts/:id/resume         Resume (rollouts:write)
POST   /rollouts/:id/cancel         Cancel (rollouts:write)
POST   /rollouts/:id/rollback       Rollback (rollouts:write)
POST   /rollouts/:id/swap-slot      Blue-green swap (rollouts:write)
POST   /rollouts/:id/advance-traffic Canary advance (rollouts:write)
```

**Create rollout example:**

```bash
curl -X POST http://localhost:4000/api/v1/projects/my-project/rollouts \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "bundle_id": "BUNDLE_UUID",
    "strategy": "rolling",
    "batch_size": 2,
    "target_selector": {"type": "all"},
    "health_gates": {"heartbeat_healthy": true, "max_error_rate": 5.0}
  }'
```

### Nodes

```text
GET    /nodes                List (nodes:read)
GET    /nodes/:id            Get details (nodes:read)
GET    /nodes/stats          Fleet statistics (nodes:read)
DELETE /nodes/:id            Deregister (nodes:write)
```

### Services

```text
GET    /services              List
POST   /services              Create
GET    /services/:id          Get
PUT    /services/:id          Update
DELETE /services/:id          Delete
PUT    /services/reorder      Batch reorder
```

### Additional Resources

Standard CRUD under `/api/v1/projects/:project_slug/`:

| Resource | Path |
|----------|------|
| Upstream Groups | `upstream-groups` |
| Certificates | `certificates` |
| Auth Policies | `auth-policies` |
| Middlewares | `middlewares` |
| Secrets | `secrets` |
| Drift | `drift` |
| API Keys | `/api/v1/api-keys` (not project-scoped) |

## Node API

Endpoints for Zentinel proxy instances.

### Register

```bash
curl -X POST http://localhost:4000/api/v1/projects/my-project/nodes/register \
  -H "Content-Type: application/json" \
  -d '{"name": "proxy-1", "labels": {"region": "us-east-1"}, "version": "1.5.0"}'
```

Response: `{"node_id": "uuid", "node_key": "base64-key", "poll_interval_s": 5}`

### Heartbeat

```text
POST /api/v1/nodes/:id/heartbeat
```

Body: `{version, ip, hostname, health, metrics, active_bundle_id, staged_bundle_id}`

### Poll for Bundle

```text
GET /api/v1/nodes/:id/bundles/latest
```

Returns bundle metadata + presigned S3 download URL, or **204** if no update.

### Token Exchange

```text
POST /api/v1/nodes/:id/token
```

Exchange static node key for JWT (12-hour expiry).

### Metrics & Events

```text
POST /api/v1/nodes/:id/metrics      Push service metrics
POST /api/v1/nodes/:id/waf-events   Push WAF events
POST /api/v1/nodes/:id/events       Push operational events
POST /api/v1/nodes/:id/config       Push runtime config
```

## Webhooks

GitOps triggers with HMAC signature verification:

```text
POST /api/v1/webhooks/github
POST /api/v1/webhooks/gitlab
POST /api/v1/webhooks/bitbucket
POST /api/v1/webhooks/gitea
POST /api/v1/webhooks/generic
```

## GraphQL

```text
POST /api/v1/graphql     (Authorization: Bearer <api_key>)
```

Full query, mutation, and subscription support via Absinthe.

## Health Endpoints

```text
GET /health     Liveness (no auth)
GET /ready      Readiness (no auth)
GET /metrics    Prometheus (no auth)
GET /api/docs   Interactive API docs (Scalar)
```

## Error Format

```json
{"error": "description", "details": "optional"}
```

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 204 | No Content |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden (insufficient scope) |
| 404 | Not Found |
| 422 | Validation failure |
| 429 | Rate limited |

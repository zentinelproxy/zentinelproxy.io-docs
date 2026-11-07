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

Endpoints for Zentinel proxy instances. All endpoints except registration require node authentication via either `X-Zentinel-Node-Key: <key>` or `Authorization: Bearer <jwt>`.

See the [Proxy Registration guide](../proxy-registration/) for a complete walkthrough.

### Register

```text
POST /api/v1/projects/:project_slug/nodes/register
```

**Auth:** None

| Parameter | Required | Description |
|-----------|----------|-------------|
| `name` | Yes | Unique name within the project (1–100 chars, alphanumeric + `_` `.` `-`) |
| `labels` | No | Key-value metadata for rollout targeting |
| `version` | No | Proxy version string |
| `ip` | No | Node IP (auto-detected if omitted) |
| `hostname` | No | Node hostname |
| `capabilities` | No | Feature capabilities array |
| `metadata` | No | Additional JSON metadata |

```bash
curl -X POST http://localhost:4000/api/v1/projects/my-project/nodes/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "proxy-us-east-1",
    "labels": {"env": "production", "region": "us-east-1"},
    "version": "1.0.0",
    "ip": "10.0.1.50",
    "hostname": "proxy-us-east-1.internal"
  }'
```

**201 Created:**

```json
{
  "node_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "node_key": "liPd5OsMRw8cr-yKFRwAr6O3zmqOdFUcfuY8W-XTiJE",
  "poll_interval_s": 30
}
```

> The `node_key` is returned **only once**. Store it securely.

**Error responses:**

| Code | Body |
|------|------|
| 404 | `{"error": "Project not found"}` |
| 422 | `{"error": {"name": ["can't be blank"]}}` |
| 422 | `{"error": {"project_id": ["has already been taken"]}}` (duplicate name) |

---

### Heartbeat

```text
POST /api/v1/nodes/:node_id/heartbeat
```

**Auth:** Node

| Parameter | Required | Description |
|-----------|----------|-------------|
| `health` | No | Health metrics object (e.g. `cpu_percent`, `memory_percent`) |
| `metrics` | No | Operational metrics object |
| `active_bundle_id` | No | UUID of the currently running bundle |
| `staged_bundle_id` | No | UUID of the staged (downloaded) bundle |
| `version` | No | Proxy version string |
| `ip` | No | Node IP (defaults to client IP) |
| `hostname` | No | Node hostname |
| `metadata` | No | Additional JSON metadata |

```bash
curl -X POST http://localhost:4000/api/v1/nodes/$NODE_ID/heartbeat \
  -H "X-Zentinel-Node-Key: $NODE_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "health": {"cpu_percent": 12.5, "memory_percent": 45.0},
    "metrics": {"requests_per_second": 1500},
    "active_bundle_id": "bundle-uuid",
    "version": "1.0.0"
  }'
```

**200 OK:**

```json
{
  "status": "ok",
  "node_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "last_seen_at": "2026-02-23T18:17:56Z"
}
```

Nodes that stop heartbeating for 120 seconds are marked `offline`.

---

### Poll for Bundle

```text
GET /api/v1/nodes/:node_id/bundles/latest
```

**Auth:** Node

```bash
curl http://localhost:4000/api/v1/nodes/$NODE_ID/bundles/latest \
  -H "X-Zentinel-Node-Key: $NODE_KEY"
```

**200 OK — update available:**

```json
{
  "bundle_id": "bundle-uuid",
  "version": "v1.2.3",
  "checksum": "sha256:abc123...",
  "size_bytes": 51200,
  "download_url": "https://s3.../bundle.tar.zst?X-Amz-...",
  "traffic_weight": null,
  "poll_after_s": 30
}
```

**200 OK — no update:**

```json
{
  "no_update": true,
  "poll_after_s": 30
}
```

> **Note:** This endpoint always returns `200`. The `no_update` field indicates no new bundle is pending.

---

### Token Exchange

```text
POST /api/v1/nodes/:node_id/token
```

**Auth:** Node (static key or existing JWT)

Exchange a static node key for a short-lived JWT (12-hour TTL), signed with Ed25519.

```bash
curl -X POST http://localhost:4000/api/v1/nodes/$NODE_ID/token \
  -H "X-Zentinel-Node-Key: $NODE_KEY"
```

**200 OK:**

```json
{
  "token": "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCIsImtpZCI6InNrXy4uLiJ9...",
  "token_type": "Bearer",
  "expires_at": "2026-02-24T06:30:00Z",
  "expires_in": 43200
}
```

**Error responses:**

| Code | Body |
|------|------|
| 422 | `{"error": "Node's project is not assigned to an organization."}` |
| 503 | `{"error": "No signing key configured for this organization. Contact your administrator."}` |

---

### Events

```text
POST /api/v1/nodes/:node_id/events
```

**Auth:** Node

Report operational events — single or batch.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `event_type` | Yes | One of: `config_reload`, `bundle_switch`, `error`, `startup`, `shutdown`, `warning`, `info` |
| `severity` | No | `debug`, `info` (default), `warn`, `error` |
| `message` | Yes | Event description |
| `metadata` | No | Additional JSON metadata |

**Single event:**

```bash
curl -X POST http://localhost:4000/api/v1/nodes/$NODE_ID/events \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "startup",
    "severity": "info",
    "message": "Proxy started successfully"
  }'
```

**Batch events** (wrap in `events` array):

```bash
curl -X POST http://localhost:4000/api/v1/nodes/$NODE_ID/events \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "events": [
      {"event_type": "bundle_switch", "severity": "info", "message": "Switched to bundle v1.2.3"},
      {"event_type": "info", "severity": "info", "message": "All upstreams healthy"}
    ]
  }'
```

**201 Created:**

```json
{"status": "ok", "count": 1}
```

**422 — invalid event_type:**

```json
{"error": {"event_type": ["is invalid"]}}
```

---

### Runtime Config

```text
POST /api/v1/nodes/:node_id/config
```

**Auth:** Node

| Parameter | Required | Description |
|-----------|----------|-------------|
| `config_kdl` | Yes | KDL configuration string |

```bash
curl -X POST http://localhost:4000/api/v1/nodes/$NODE_ID/config \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"config_kdl": "route \"/api/*\" { upstream \"http://api:8080\" }"}'
```

**200 OK:**

```json
{
  "status": "ok",
  "config_hash": "b5b95950cf0f3997b35e3745f16425d24974f71bf58b6fb5a4bf8a509194d81e"
}
```

---

### Metrics

```text
POST /api/v1/nodes/:node_id/metrics
```

**Auth:** Node

Push service-level metrics and request logs.

| Field | Required | Description |
|-------|----------|-------------|
| `metrics[].service_id` | Yes | Service UUID |
| `metrics[].project_id` | Yes | Project UUID |
| `metrics[].period_start` | No | ISO 8601 timestamp (defaults to now) |
| `metrics[].period_seconds` | No | Aggregation window (default: 60) |
| `metrics[].request_count` | No | Total requests |
| `metrics[].error_count` | No | Error count |
| `metrics[].latency_p50_ms` | No | P50 latency |
| `metrics[].latency_p95_ms` | No | P95 latency |
| `metrics[].latency_p99_ms` | No | P99 latency |
| `metrics[].status_2xx` | No | 2xx response count |
| `metrics[].status_3xx` | No | 3xx response count |
| `metrics[].status_4xx` | No | 4xx response count |
| `metrics[].status_5xx` | No | 5xx response count |
| `request_logs[].service_id` | Yes | Service UUID |
| `request_logs[].project_id` | Yes | Project UUID |
| `request_logs[].timestamp` | Yes | ISO 8601 with microseconds |
| `request_logs[].method` | Yes | HTTP method |
| `request_logs[].path` | Yes | Request path |
| `request_logs[].status` | Yes | HTTP status code |
| `request_logs[].latency_ms` | Yes | Latency in milliseconds |

```bash
curl -X POST http://localhost:4000/api/v1/nodes/$NODE_ID/metrics \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "metrics": [{
      "service_id": "SERVICE_UUID",
      "project_id": "PROJECT_UUID",
      "period_start": "2026-02-23T10:00:00Z",
      "period_seconds": 60,
      "request_count": 1500,
      "error_count": 3,
      "status_2xx": 1450,
      "status_4xx": 47,
      "status_5xx": 3
    }],
    "request_logs": [{
      "service_id": "SERVICE_UUID",
      "project_id": "PROJECT_UUID",
      "timestamp": "2026-02-23T10:00:00Z",
      "method": "GET",
      "path": "/api/health",
      "status": 200,
      "latency_ms": 5
    }]
  }'
```

**200 OK:**

```json
{
  "status": "ok",
  "metrics_ingested": 1,
  "logs_ingested": 1
}
```

---

### WAF Events

```text
POST /api/v1/nodes/:node_id/waf-events
```

**Auth:** Node

Push WAF event data. The `events` array is required.

| Field | Required | Description |
|-------|----------|-------------|
| `events[].rule_type` | Yes | Rule category (e.g. `crs`) |
| `events[].rule_id` | Yes | Rule identifier (e.g. `942100`) |
| `events[].action` | Yes | Action taken (`blocked`, `logged`, `challenged`) |
| `events[].severity` | Yes | `low`, `medium`, `high`, `critical` |
| `events[].client_ip` | No | Client IP address |
| `events[].method` | No | HTTP method |
| `events[].path` | No | Request path |
| `events[].matched_data` | No | Data that triggered the rule |
| `events[].timestamp` | No | ISO 8601 (defaults to now) |
| `events[].service_id` | No | Service UUID |
| `events[].metadata` | No | Additional JSON metadata |

```bash
curl -X POST http://localhost:4000/api/v1/nodes/$NODE_ID/waf-events \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "events": [{
      "rule_type": "crs",
      "rule_id": "942100",
      "action": "blocked",
      "severity": "high",
      "client_ip": "1.2.3.4",
      "method": "POST",
      "path": "/login",
      "timestamp": "2026-02-23T10:00:00Z",
      "matched_data": "1 OR 1=1",
      "metadata": {"category": "sql_injection"}
    }]
  }'
```

**200 OK:**

```json
{
  "status": "ok",
  "events_ingested": 1
}
```

**400 — missing events array:**

```json
{"error": "Expected 'events' list in request body"}
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

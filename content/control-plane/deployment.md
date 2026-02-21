+++
title = "Deployment"
weight = 6
+++

Docker deployment and rollout strategies for the Zentinel Control Plane.

## Docker Compose

### Services

| Service | Image | Ports |
|---------|-------|-------|
| `app` | Built from Dockerfile | 4000 |
| `postgres` | `postgres:17` | 5432 |
| `minio` | `minio/minio` | 9000, 9001 |
| `minio-init` | `minio/mc` | — |

### Dockerfile

Multi-stage build: `hexpm/elixir:1.19.5-erlang-28.3.1-debian-bookworm` base. Compiles Elixir + assets (esbuild, Tailwind), creates OTP release. Runtime runs as non-root user `zentinel` with healthcheck at `/health`.

### Production Checklist

- [ ] Generate unique `SECRET_KEY_BASE` (`mix phx.gen.secret`)
- [ ] Change default admin password
- [ ] Use managed PostgreSQL
- [ ] Configure S3 with proper IAM
- [ ] Set `PHX_HOST` to public domain
- [ ] Set `FORCE_SSL=true`
- [ ] Set up backup strategy
- [ ] Configure monitoring (scrape `GET /metrics`)

## Rollout Strategies

### Rolling (Default)

Deploy in fixed-size batches with health gate checks between each.

```json
{
  "strategy": "rolling",
  "batch_size": 2,
  "health_gates": {"heartbeat_healthy": true, "max_error_rate": 5.0}
}
```

### Canary

Gradually increase traffic with statistical analysis:

```json
{
  "strategy": "canary",
  "canary_steps": [5, 25, 50, 100],
  "health_gates": {"heartbeat_healthy": true, "max_error_rate": 2.0}
}
```

### Blue-Green

Deploy to standby slot, shift traffic, validate, swap:

```json
{
  "strategy": "blue_green",
  "health_gates": {"heartbeat_healthy": true}
}
```

### All at Once

Simultaneous deployment to all target nodes:

```json
{"strategy": "all_at_once"}
```

## Health Gates

Evaluated between rollout batches:

| Gate | Type | Description |
|------|------|-------------|
| `heartbeat_healthy` | Boolean | All batch nodes heartbeating |
| `max_error_rate` | Float % | Error rate below threshold |
| `max_latency_ms` | Integer | P99 latency below threshold |
| `max_cpu_percent` | Float % | CPU below threshold |
| `max_memory_percent` | Float % | Memory below threshold |

## Target Selectors

| Selector | Description |
|----------|-------------|
| `{"type": "all"}` | All project nodes |
| `{"type": "labels", "labels": {...}}` | Nodes matching labels |
| `{"type": "node_ids", "node_ids": [...]}` | Specific nodes |
| `{"type": "groups", "group_ids": [...]}` | Nodes in groups |

## Rollout Controls

| Action | Endpoint | Effect |
|--------|----------|--------|
| Pause | `POST /rollouts/:id/pause` | Stop progression |
| Resume | `POST /rollouts/:id/resume` | Continue from pause |
| Cancel | `POST /rollouts/:id/cancel` | Stop, no revert |
| Rollback | `POST /rollouts/:id/rollback` | Revert to previous |
| Swap slot | `POST /rollouts/:id/swap-slot` | Blue-green finalize |
| Advance | `POST /rollouts/:id/advance-traffic` | Canary next step |

## Approval Workflow

- Configurable per project and environment
- Configurable approval count (default: 1)
- No self-approval
- Rejection requires comment

## Freeze Windows

Time-based deployment freezes. Project-wide or environment-scoped. Block rollout creation during defined periods.

## Scheduled Rollouts

Set `scheduled_at` (ISO 8601) when creating a rollout. Respects freeze windows and approval requirements.

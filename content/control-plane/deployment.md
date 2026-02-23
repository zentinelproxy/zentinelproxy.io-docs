+++
title = "Deployment"
weight = 7
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

## Standalone Docker

For environments with existing PostgreSQL and S3-compatible storage where only the control plane container is needed.

### Prerequisites

- PostgreSQL 15+ (managed or self-hosted)
- S3-compatible storage (AWS S3, MinIO, DigitalOcean Spaces, etc.)
- Docker

### Pull or Build the Image

```bash
# Build from source
docker build -t zentinel-cp .
```

### Run Migrations and Seed

Before first startup, run migrations and seed the default admin user:

```bash
docker run --rm \
  -e DATABASE_URL="ecto://user:pass@db-host:5432/zentinel_cp" \
  -e SECRET_KEY_BASE="$(openssl rand -base64 48)" \
  zentinel-cp bin/zentinel_cp eval "ZentinelCp.Release.migrate()"

docker run --rm \
  -e DATABASE_URL="ecto://user:pass@db-host:5432/zentinel_cp" \
  -e SECRET_KEY_BASE="$(openssl rand -base64 48)" \
  zentinel-cp bin/zentinel_cp eval "ZentinelCp.Release.seed()"
```

### Start the Control Plane

```bash
docker run -d \
  --name zentinel-cp \
  -p 4000:4000 \
  -e DATABASE_URL="ecto://user:pass@db-host:5432/zentinel_cp" \
  -e SECRET_KEY_BASE="$(mix phx.gen.secret)" \
  -e PHX_HOST="cp.example.com" \
  -e S3_ENDPOINT="https://s3.amazonaws.com" \
  -e S3_BUCKET="zentinel-bundles" \
  -e S3_ACCESS_KEY_ID="AKIA..." \
  -e S3_SECRET_ACCESS_KEY="..." \
  -e S3_REGION="us-east-1" \
  -e FORCE_SSL="true" \
  zentinel-cp
```

The entrypoint automatically runs migrations on startup, so the separate migration step is only needed if you want to run migrations independently.

### Healthcheck

```bash
curl -f http://localhost:4000/health
```

### Rollback Migrations

```bash
docker run --rm \
  -e DATABASE_URL="ecto://user:pass@db-host:5432/zentinel_cp" \
  -e SECRET_KEY_BASE="any-value" \
  zentinel-cp bin/zentinel_cp eval "ZentinelCp.Release.rollback(ZentinelCp.Repo, 20240101000000)"
```

Replace the version number with the migration timestamp to roll back to.

## From Source (Bare Metal)

Build and run a native OTP release without Docker.

### Prerequisites

- Elixir 1.16+ and Erlang/OTP 26+
- PostgreSQL 15+
- S3-compatible storage
- `zentinel` CLI binary (for bundle validation)
- Node.js (for asset compilation)

### Build the Release

```bash
git clone https://github.com/zentinelproxy/zentinel-control-plane.git
cd zentinel-control-plane

export MIX_ENV=prod

mix deps.get --only prod
mix compile
mix assets.deploy
mix release
```

The release is built to `_build/prod/rel/zentinel_cp/`.

### Run Migrations and Seed

```bash
export DATABASE_URL="ecto://user:pass@localhost:5432/zentinel_cp"
export SECRET_KEY_BASE="$(mix phx.gen.secret)"

_build/prod/rel/zentinel_cp/bin/zentinel_cp eval "ZentinelCp.Release.migrate()"
_build/prod/rel/zentinel_cp/bin/zentinel_cp eval "ZentinelCp.Release.seed()"
```

### Start the Server

```bash
export DATABASE_URL="ecto://user:pass@localhost:5432/zentinel_cp"
export SECRET_KEY_BASE="your-secret-key-base"
export PHX_HOST="cp.example.com"
export S3_ENDPOINT="https://s3.amazonaws.com"
export S3_BUCKET="zentinel-bundles"
export S3_ACCESS_KEY_ID="AKIA..."
export S3_SECRET_ACCESS_KEY="..."
export ZENTINEL_BINARY="/usr/local/bin/zentinel"

PHX_SERVER=true _build/prod/rel/zentinel_cp/bin/zentinel_cp start
```

### systemd Service

Create `/etc/systemd/system/zentinel-cp.service`:

```ini
[Unit]
Description=Zentinel Control Plane
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=exec
User=zentinel
Group=zentinel
WorkingDirectory=/opt/zentinel-cp
ExecStart=/opt/zentinel-cp/bin/zentinel_cp start
ExecStop=/opt/zentinel-cp/bin/zentinel_cp stop
Restart=on-failure
RestartSec=5

Environment=PHX_SERVER=true
Environment=PORT=4000
Environment=PHX_HOST=cp.example.com
Environment=FORCE_SSL=true
Environment=POOL_SIZE=10
Environment=ZENTINEL_BINARY=/usr/local/bin/zentinel

EnvironmentFile=/etc/zentinel-cp/env

[Install]
WantedBy=multi-user.target
```

Store secrets in `/etc/zentinel-cp/env` (mode `0600`):

```bash
DATABASE_URL=ecto://zentinel:password@localhost:5432/zentinel_cp
SECRET_KEY_BASE=your-secret-key-base-here
S3_ENDPOINT=https://s3.amazonaws.com
S3_BUCKET=zentinel-bundles
S3_ACCESS_KEY_ID=AKIA...
S3_SECRET_ACCESS_KEY=...
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable zentinel-cp
sudo systemctl start zentinel-cp
sudo journalctl -u zentinel-cp -f
```

## Connecting Proxies

After deployment, see the [Proxy Registration](../proxy-registration/) guide for connecting zentinel proxy instances to the control plane.

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

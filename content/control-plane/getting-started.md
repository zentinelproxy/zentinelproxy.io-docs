+++
title = "Getting Started"
weight = 1
+++

Get the Zentinel Control Plane running locally and deploy your first configuration bundle.

## Prerequisites

**Docker Compose (recommended):** Only [Docker](https://docs.docker.com/get-docker/) required — all dependencies included.

**Local development:**
- Elixir 1.16+ and Erlang/OTP 26+ (managed via [mise](https://mise.jdx.dev/))
- Docker — for MinIO (bundle storage)
- `zentinel` CLI binary — for configuration validation

## Docker Compose

Start the full stack with one command:

```bash
git clone https://github.com/zentinelproxy/zentinel-control-plane.git
cd zentinel-control-plane
docker compose up
```

This starts:

| Service | Port | Purpose |
|---------|------|---------|
| Control Plane | `4000` | Web UI and API |
| PostgreSQL 17 | `5432` | Database |
| MinIO | `9000` (API), `9001` (console) | Bundle storage |

The control plane automatically runs database migrations and seeds the database on first startup.

Open **http://localhost:4000** to access the web UI.

MinIO console at **http://localhost:9001** (credentials: `minioadmin` / `minioadmin`).

To tear down (including data):

```bash
docker compose down -v
```

## Local Development

For hot-reloading and SQLite (no external databases):

```bash
git clone https://github.com/zentinelproxy/zentinel-control-plane.git
cd zentinel-control-plane

mise install          # Install Elixir/Erlang
mise run setup        # Fetch deps, create DB, migrate, seed
mise run dev          # Start dev server at localhost:4000
```

## Default Credentials

On first startup, a default admin account is created:

| Field | Value |
|-------|-------|
| **Email** | `admin@localhost` |
| **Password** | `changeme123456` |
| **Role** | `admin` |

> **Important:** Change these credentials immediately in any non-development environment.

### Creating Your Own User

**Via the web UI:** Navigate to `/register`.

**Via the console:**

```bash
# Local development
mise run console

# Docker
docker compose exec app bin/zentinel_cp eval '
  ZentinelCp.Accounts.register_user(%{
    email: "you@example.com",
    password: "your-secure-password-here"
  })
'
```

Password requirements: minimum 12 characters, maximum 72 characters. Hashed with Argon2.

### User Roles

| Role | Permissions |
|------|-------------|
| `admin` | Full org control — manage members, projects, signing keys, API keys |
| `operator` | Manage projects, bundles, rollouts, services, nodes |
| `reader` | Read-only access to all resources |

Roles are per-organization. A user can hold different roles in different orgs.

## First Steps

### 1. Create an Organization

Navigate to **Organizations > New Organization**. Enter a name — a URL-safe slug is generated automatically. Organizations are the top-level tenant boundary.

### 2. Create a Project

From the org dashboard, click **New Project**. Projects group related proxy configurations, nodes, bundles, and rollouts.

### 3. Configure Services

Navigate to **Services > New Service**. Define a route path and upstream:

- **Name**: e.g., "API Backend"
- **Route Path**: e.g., `/api/*`
- **Upstream URL**: e.g., `http://api.internal:8080`

### 4. Compile a Bundle

Navigate to **Bundles > New Bundle**. Enter KDL configuration or generate from your services. Compilation runs in the background — the bundle transitions from `compiling` to `compiled` when ready.

Or via the API:

```bash
curl -X POST http://localhost:4000/api/v1/projects/my-project/bundles \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"config_source": "route \"/api/*\" {\n  upstream \"http://api:8080\"\n}"}'
```

### 5. Register a Node

Register a Zentinel proxy instance:

```bash
curl -X POST http://localhost:4000/api/v1/projects/my-project/nodes/register \
  -H "Content-Type: application/json" \
  -d '{"name": "proxy-1", "labels": {"env": "dev"}}'
```

Store the returned `node_key` — it is shown only once.

### 6. Deploy with a Rollout

Navigate to **Rollouts > New Rollout**. Select the compiled bundle, choose a strategy (rolling, canary, blue-green, all-at-once), configure health gates, and start.

## Environment Variables

Key variables for Docker deployment:

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | `ecto://zentinel:zentinel@postgres:5432/zentinel_cp` | PostgreSQL connection |
| `SECRET_KEY_BASE` | Set in compose | Phoenix secret key |
| `S3_ENDPOINT` | `http://minio:9000` | MinIO endpoint |
| `S3_BUCKET` | `zentinel-bundles` | Bundle storage bucket |
| `PORT` | `4000` | HTTP listen port |

See [Configuration](../configuration/) for the full list of environment variables.

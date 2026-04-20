+++
title = "Architecture"
weight = 2
+++

System design, components, and data flow of the Zentinel Control Plane.

## System Overview

```text
┌─────────────────────────────────────────────────────────────┐
│                    Control Plane (Phoenix)                   │
├─────────────┬─────────────┬─────────────┬──────────────────┤
│  REST API   │  LiveView   │  Compiler   │  Rollout Engine  │
│  (JSON)     │  UI (WS)    │  (Oban)     │  (Oban, 5s tick) │
├─────────────┴─────────────┴─────────────┴──────────────────┤
│  Events & Notifications  │  Observability  │  Analytics     │
│  (Slack, PD, Teams, WH)  │  (SLOs, Alerts) │  (WAF, Reqs)  │
└──────┬──────┬─────────────┴───────┬─────┴────────┬─────────┘
       │      │                     │              │
       │   ┌──┴─────────────┐   ┌──┴──────────────┘
       │   │  PostgreSQL     │   │  MinIO / S3
       │   │  (SQLite dev)   │   │  (Bundle Storage)
       │   └─────────────────┘   └────────────────────
       │
┌──────┴──────────────────────────────────────────────────────┐
│                      Zentinel Nodes                          │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐        │
│  │ Node 1  │  │ Node 2  │  │ Node 3  │  │ Node N  │  ...   │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘        │
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### REST API

Three consumer classes:

| Consumer | Auth | Base Path |
|----------|------|-----------|
| **Operator** | API key | `/api/v1/projects/:slug/` |
| **Node** | Node key / JWT | `/api/v1/nodes/:id/` |
| **Webhook** | HMAC signature | `/api/v1/webhooks/` |

### LiveView UI

Real-time web interface over WebSocket. Org-scoped routes: `/orgs/:org_slug/projects/:project_slug/...`. Covers dashboards, node management, bundle diff viewer, rollout tracking, service editor, topology graph, WAF dashboard, SLOs, alerts, and audit logs.

### Compiler Service

Runs as an Oban background job (`CompileWorker`):

1. Validates KDL config via `zentinel validate`
2. Assembles `.tar.zst` archive (config, manifest, CA certs, plugins)
3. Uploads to S3-compatible storage
4. Signs with Ed25519 (optional)
5. Generates CycloneDX 1.5 SBOM
6. Scores risk against previous bundle

### Rollout Engine

Self-rescheduling Oban worker (`TickWorker`), ticks every 5 seconds per active rollout.

| Strategy | Behavior |
|----------|----------|
| Rolling | Fixed-size batches with health checks between each |
| Canary | Progressive traffic ramp with statistical analysis |
| Blue-Green | Standby slot deployment, traffic shift, swap |
| All at Once | Simultaneous deployment to all nodes |

Health gates between batches: heartbeat status, error rate, P99 latency, CPU%, memory%.

## Data Flow

### Bundle Deployment

```text
Operator creates bundle → CompileWorker validates + assembles + uploads
    → Bundle status: "compiled"
    → Operator creates rollout
    → Approval workflow (if configured)
    → TickWorker deploys in batches
    → Nodes poll, download from S3, activate, report via heartbeat
```

### Node Communication

Pull-based model — nodes initiate all communication:

| Operation | Endpoint | Frequency |
|-----------|----------|-----------|
| Registration | `POST /projects/:slug/nodes/register` | Once |
| Heartbeat | `POST /nodes/:id/heartbeat` | Every 10-30s |
| Bundle poll | `GET /nodes/:id/bundles/latest` | Every 5-30s |
| JWT refresh | `POST /nodes/:id/token` | On expiry |
| Metrics | `POST /nodes/:id/metrics` | Periodic |
| WAF events | `POST /nodes/:id/waf-events` | Periodic |

## Multi-Tenancy

```text
Organization
├── Members (admin, operator, reader)
├── Signing Keys (Ed25519 for JWT)
├── SSO Providers (OIDC, SAML)
└── Projects
    ├── Environments (dev → staging → production)
    ├── Nodes, Bundles, Rollouts
    ├── Services, Upstream Groups, Certificates
    ├── Auth Policies, WAF Policies, Middlewares
    ├── Plugins, Secrets
    ├── Notifications, SLOs, Alerts
    └── Audit Logs
```

## Background Jobs

Powered by [Oban](https://hexdocs.pm/oban/). Queues: `default` (10), `rollouts` (5), `maintenance` (2).

| Worker | Schedule | Purpose |
|--------|----------|---------|
| CompileWorker | On demand | Bundle validation and assembly |
| TickWorker | Every 5s | Rollout state machine |
| StalenessWorker | Periodic | Mark offline nodes (120s threshold) |
| DriftWorker | Every 30s | Config drift detection |
| SliWorker | Every 5 min | SLI computation |
| AlertEvaluator | Every 30s | Alert rule evaluation |
| RollupWorker | Hourly | Metric aggregation |
| WafBaselineWorker | Hourly | WAF statistical baselines |
| WafAnomalyWorker | Every 15 min | Z-score anomaly detection |

## Database & Storage

- **Database**: PostgreSQL (production), SQLite (development) — transparent via Ecto
- **Storage**: S3-compatible — path: `bundles/{project_id}/{bundle_id}.tar.zst`
- **Downloads**: Presigned S3 URLs (no proxy through control plane)

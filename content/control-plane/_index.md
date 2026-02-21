+++
title = "Control Plane"
weight = 7
sort_by = "weight"
template = "section.html"
+++

The Zentinel Control Plane is a fleet management system for Zentinel reverse proxies. It provides centralized configuration compilation, safe rollout orchestration, node lifecycle tracking, and comprehensive observability.

## Overview

The control plane sits between operators and the Zentinel proxy fleet. It compiles KDL proxy configurations into immutable bundles, distributes them to nodes via a pull-based model, and orchestrates safe deployments with health-gated rollout strategies.

```text
┌─────────────────────────────────────────────────────┐
│              Control Plane (Phoenix)                 │
│  ┌──────────┐  ┌──────────┐  ┌───────────────┐     │
│  │ LiveView │  │ REST API │  │ Rollout Engine │     │
│  │   UI     │  │ + GraphQL│  │    (Oban)      │     │
│  └────┬─────┘  └─────┬────┘  └───────┬───────┘     │
│       └───────────────┴───────────────┘             │
│           │                       │                 │
│    ┌──────┴────────┐    ┌────────┴────────┐         │
│    │  PostgreSQL   │    │   MinIO / S3    │         │
│    │  (SQLite dev) │    │ (Bundle Storage)│         │
│    └───────────────┘    └─────────────────┘         │
└──────────────────────┬──────────────────────────────┘
                       │
         ┌─────────────┴─────────────┐
         │     Zentinel Node Fleet    │
         │  ┌────┐ ┌────┐ ┌────┐     │
         │  │ N1 │ │ N2 │ │ N3 │ ... │
         │  └────┘ └────┘ └────┘     │
         └───────────────────────────┘
```

## Key Capabilities

| Capability | Description |
|------------|-------------|
| **Configuration Management** | Define services, upstreams, TLS, middlewares, and auth policies via UI or API |
| **Bundle Compilation** | Validate KDL config, assemble `.tar.zst` archives, sign with Ed25519, generate SBOMs |
| **Rollout Orchestration** | Rolling, canary, blue-green, and all-at-once strategies with health gates |
| **Node Fleet Management** | Registration, heartbeats, drift detection, label-based grouping |
| **WAF** | ~60 OWASP CRS rules with per-policy overrides and anomaly detection |
| **Observability** | SLOs, alert rules, Prometheus metrics, OpenTelemetry tracing |
| **Integrations** | GitOps webhooks, Slack/PagerDuty/Teams notifications, GraphQL API |

## Tech Stack

Built with Elixir/Phoenix, LiveView for real-time UI, Oban for background jobs, PostgreSQL (production) or SQLite (development), and S3-compatible storage for bundles.

## In This Section

| Page | Description |
|------|-------------|
| [Getting Started](getting-started/) | Installation, default credentials, first project |
| [Architecture](architecture/) | System design, components, data flow |
| [Authentication](authentication/) | API keys, node auth, SSO, MFA |
| [API Reference](api/) | REST API endpoints with curl examples |
| [Configuration](configuration/) | Services, upstreams, TLS, env vars |
| [Deployment](deployment/) | Docker setup, rollout strategies, health gates |
| [Security](security/) | WAF rules, auth policies, bundle signing |
| [Observability](observability/) | Prometheus, SLOs, alerts, tracing, notifications |

+++
title = "Observability"
weight = 8
+++

Monitoring, metrics, alerting, tracing, and notifications for the Zentinel Control Plane.

## Prometheus Metrics

Exposed at `GET /metrics` (no auth). Powered by PromEx.

| Category | Examples |
|----------|---------|
| BEAM VM | Memory, process count, scheduler utilization |
| Phoenix | Request count, duration, status codes |
| Ecto | Query count, duration, queue time |
| Oban | Job count, duration, state transitions |
| Zentinel | Node counts, drift events, SLO status, active rollouts |

```yaml
# Scrape config
scrape_configs:
  - job_name: zentinel-control-plane
    static_configs:
      - targets: ['localhost:4000']
    metrics_path: /metrics
    scrape_interval: 15s
```

## SLOs / SLIs

Define availability, latency, and error rate targets:

- Rolling or calendar-based windows
- Error budget tracking
- `SliWorker` computes every 5 minutes

## Alert Rules

Metric-based and SLO burn-rate alerts:

- Severity: `critical`, `warning`, `info`
- Grace periods to avoid flapping
- `AlertEvaluator` runs every 30 seconds
- Alerts route to notification channels

## Service Analytics

Per-service metrics from nodes: request counts, error counts, latency percentiles (P50/P95/P99), bandwidth, status code distribution.

Hourly/daily rollups via `RollupWorker`. Configurable retention.

## WAF Analytics

- Every blocked/logged request tracked: rule ID, client IP, path, matched data
- 14-day statistical baselines (hourly computation)
- Z-score anomaly detection (>2.5σ): spikes, new attack vectors, IP bursts

## OpenTelemetry

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT=http://collector:4318
```

Traces wrap: bundle compilation, rollout ticks, webhook processing, node heartbeats.

## Node Monitoring

- **Heartbeats**: Every 10-30s with health metrics, bundle IDs, version
- **Staleness**: Nodes marked `offline` after 120s without heartbeat
- **Drift detection**: `DriftWorker` (every 30s) compares `active_bundle_id` vs `expected_bundle_id`
- **Auto-remediation**: Optional automatic bundle reassignment
- **Node groups**: Label-based grouping for rollout targeting

## Notification Channels

| Channel | Description |
|---------|-------------|
| Slack | Webhook messages |
| PagerDuty | Incident creation |
| Microsoft Teams | Webhook messages |
| Email | Swoosh mailer |
| Generic Webhook | Custom HTTP POST |

### Event Routing

Pattern-based rules: `rollout.*`, `bundle.*`, `drift.*`, `security.*`, `waf.*`, `alert.*`.

Delivery with exponential backoff retries and dead-letter queue.

## Audit Logging

Immutable HMAC chain:

- All mutations logged with actor, resource, action, timestamp
- Chain verification via `GET /api/v1/audit/verify`
- Periodic checkpoints for integrity validation
- Exportable via API

## Health Endpoints

```text
GET /health    Liveness (200 if running)
GET /ready     Readiness (200 if DB ready)
GET /metrics   Prometheus metrics
```

No authentication. Suitable for load balancer health checks.

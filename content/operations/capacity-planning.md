+++
title = "Capacity Planning"
weight = 6
+++

Guide for sizing and scaling Sentinel deployments.

## Resource Requirements

### Minimum Requirements

| Resource | Minimum | Recommended | Notes |
|----------|---------|-------------|-------|
| CPU | 2 cores | 4+ cores | Scales linearly with request rate |
| Memory | 512 MB | 2 GB+ | Depends on connection count |
| Disk | 1 GB | 10 GB | Logs, certificates, GeoIP DB |
| Network | 100 Mbps | 1 Gbps+ | Based on traffic volume |

### Resource Consumption Model

**CPU Usage**:
- TLS handshakes: ~2ms CPU per handshake
- Request processing: ~0.1ms CPU per request (proxy-only)
- WAF inspection: ~1-5ms CPU per request (when enabled)
- Compression: ~0.5-2ms CPU per MB compressed

**Memory Usage**:
- Base process: ~50 MB
- Per connection: ~2-8 KB (idle) / ~16-64 KB (active)
- Per worker thread: ~8 MB
- Request buffering: configurable via `max-body-size`
- Connection pool: ~1 KB per pooled connection

## Sizing Guidelines

### Small Deployment

**Traffic**: < 1,000 requests/second

```kdl
server {
    worker-threads 2
    max-connections 5000
}

connection-pool {
    max-connections 100
    max-idle 20
}
```

**Resources**: 2 cores, 1 GB RAM

### Medium Deployment

**Traffic**: 1,000 - 10,000 requests/second

```kdl
server {
    worker-threads 4
    max-connections 20000
}

connection-pool {
    max-connections 200
    max-idle 50
}
```

**Resources**: 4 cores, 4 GB RAM per instance, 3 instances for HA

### Large Deployment

**Traffic**: 10,000 - 100,000 requests/second

```kdl
server {
    worker-threads 0  // Use all available cores
    max-connections 50000
}

connection-pool {
    max-connections 500
    max-idle 100
    idle-timeout-secs 120
}

rate-limit {
    backend "redis" {
        endpoints ["redis://redis-cluster:6379"]
    }
}
```

**Resources**: 8+ cores, 16 GB RAM per instance, 5+ instances across regions

## Performance Characteristics

### Request Processing Latency

| Component | Latency (p50) | Latency (p99) |
|-----------|---------------|---------------|
| TCP accept | < 0.1 ms | < 0.5 ms |
| TLS handshake (new) | 2-5 ms | 10-20 ms |
| TLS handshake (resumed) | 0.5-1 ms | 2-5 ms |
| Header parsing | < 0.1 ms | < 0.5 ms |
| Route matching | < 0.05 ms | < 0.2 ms |
| Upstream selection | < 0.01 ms | < 0.05 ms |
| Agent call (if enabled) | 1-5 ms | 10-50 ms |
| **Proxy overhead (total)** | **0.5-2 ms** | **5-15 ms** |

### Throughput Limits

| Scenario | Approximate Limit | Bottleneck |
|----------|-------------------|------------|
| Simple proxy (HTTP) | 50,000 RPS/core | CPU |
| TLS termination | 10,000 new conn/s/core | CPU (crypto) |
| Large body (1MB) | 1-8 Gbps | Network/Memory |
| WAF enabled | 5,000-10,000 RPS/core | Agent latency |

### Connection Limits Formula

```
Max Connections = Available Memory (MB) / Memory per Connection (KB) * 1024

Example:
4096 MB / 16 KB * 1024 = 262,144 connections (theoretical max)
Practical max: ~50% of theoretical for headroom
```

## Capacity Metrics

### Key Metrics to Monitor

```bash
# Current request rate
curl -s localhost:9090/metrics | grep 'requests_total'

# Active connections
curl -s localhost:9090/metrics | grep 'open_connections'

# Connection pool utilization
curl -s localhost:9090/metrics | grep 'connection_pool'

# Memory usage
curl -s localhost:9090/metrics | grep 'process_resident_memory_bytes'

# Request latency percentiles
curl -s localhost:9090/metrics | grep 'request_duration.*quantile'
```

### Capacity Thresholds

| Metric | Warning | Critical | Action |
|--------|---------|----------|--------|
| CPU utilization | > 70% | > 85% | Scale horizontally |
| Memory utilization | > 75% | > 90% | Increase memory or scale |
| Connection count | > 70% max | > 85% max | Increase limits or scale |
| p99 latency | > 100ms | > 500ms | Investigate or scale |
| Error rate | > 0.1% | > 1% | Investigate upstream/config |

### Prometheus Alerting Rules

```yaml
groups:
  - name: sentinel-capacity
    rules:
      - alert: SentinelHighCPU
        expr: rate(process_cpu_seconds_total{job="sentinel"}[5m]) > 0.7
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Sentinel CPU usage > 70%"

      - alert: SentinelConnectionsHigh
        expr: sentinel_open_connections / sentinel_max_connections > 0.7
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "Sentinel approaching connection limit"

      - alert: SentinelLatencyHigh
        expr: histogram_quantile(0.99, rate(sentinel_request_duration_seconds_bucket[5m])) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Sentinel p99 latency > 100ms"
```

## Scaling Strategies

### Vertical Scaling

**When to use**: Quick fix, single-instance deployments

```kdl
// Increase worker threads (if CPU-bound)
server {
    worker-threads 8  // Increase from 4
}

// Increase connection limits (if connection-bound)
server {
    max-connections 50000  // Increase from 20000
}
```

**Limits**:
- Single machine limits (typically 64 cores, 256 GB RAM)
- Single point of failure
- Diminishing returns above 8-16 cores for proxy workloads

### Horizontal Scaling

**When to use**: Production deployments, high availability

```
                 Load Balancer
                      │
      ┌───────────────┼───────────────┐
      │               │               │
 ┌────▼────┐    ┌────▼────┐    ┌────▼────┐
 │Sentinel │    │Sentinel │    │Sentinel │
 │   #1    │    │   #2    │    │   #3    │
 └─────────┘    └─────────┘    └─────────┘
```

**Scaling Formula**:
```
Instances = (Peak RPS × Safety Factor) / RPS per Instance

Example:
Peak RPS: 50,000
Safety Factor: 1.5
RPS per Instance: 15,000 (with WAF)

Instances = (50,000 × 1.5) / 15,000 = 5 instances
```

### Auto-Scaling (Kubernetes)

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: sentinel-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: sentinel
  minReplicas: 3
  maxReplicas: 20
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Pods
      pods:
        metric:
          name: sentinel_requests_per_second
        target:
          type: AverageValue
          averageValue: "10000"
```

## Load Testing

### Baseline Test

```bash
# Simple throughput test with wrk
wrk -t12 -c400 -d30s http://sentinel:8080/health

# Latency-focused test
wrk -t4 -c50 -d60s --latency http://sentinel:8080/api/endpoint
```

### Capacity Test Script

```bash
#!/bin/bash
# Find maximum sustainable throughput

for CONNECTIONS in 100 500 1000 2000 5000 10000; do
    echo "Testing with $CONNECTIONS connections..."

    wrk -t12 -c$CONNECTIONS -d60s --latency http://sentinel:8080/api \
        > results-${CONNECTIONS}c.txt 2>&1

    # Check for errors or degradation
    RPS=$(grep "Requests/sec" results-${CONNECTIONS}c.txt | awk '{print $2}')
    P99=$(grep "99%" results-${CONNECTIONS}c.txt | awk '{print $2}')

    echo "$CONNECTIONS connections: $RPS RPS, p99=$P99"
    sleep 30  # Cool down
done
```

## Capacity Planning Process

### 1. Gather Requirements

- Peak requests per second
- Average request/response size
- TLS termination required?
- WAF/Agent processing?
- Growth projections
- SLA requirements (availability, latency)

### 2. Calculate Base Capacity

**Rules of Thumb**:
- 1 core ≈ 10,000-50,000 simple proxy RPS
- TLS halves throughput
- WAF reduces throughput by 50-70%
- Minimum 3 instances for HA

### 3. Size and Validate

- Load test with expected peak traffic
- Verify p99 latency within SLA
- Test failover scenarios (N-1 capacity)
- Validate auto-scaling triggers

### 4. Document and Review

- Capacity limits and headroom
- Scaling thresholds
- Review schedule (quarterly or 25% traffic increase)

## Quick Reference

### Common Bottlenecks

| Symptom | Likely Bottleneck | Solution |
|---------|-------------------|----------|
| High CPU, low connections | Processing capacity | Add cores/instances |
| High connections, low CPU | Connection limits | Increase limits, optimize keepalive |
| High p99, moderate CPU | Upstream latency | Optimize upstreams |
| Errors under load | Resource exhaustion | Scale up/out |

### Capacity Rules of Thumb

1. **CPU**: 1 core ≈ 10,000-50,000 simple proxy RPS
2. **Memory**: 16 KB per active connection (more with WAF)
3. **TLS**: Halves throughput, 10K new connections/sec/core
4. **WAF**: Reduces throughput by 50-70%
5. **Instances**: Minimum 3 for HA, N+1 for maintenance

## See Also

- [Deployment Architecture](../../deployment/architecture/) - Deployment patterns
- [Monitoring](../../deployment/monitoring/) - Metrics and alerting
- [Performance Tuning](../troubleshooting/#performance-issues) - Optimization tips
- [Metrics Reference](../../reference/metrics/) - Available metrics

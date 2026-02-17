+++
title = "Incident Response"
weight = 4
+++

Procedures for responding to production incidents affecting Zentinel.

## Incident Classification

### Severity Levels

| Severity | Description | Response Time | Examples |
|----------|-------------|---------------|----------|
| **SEV1** | Complete outage, all traffic affected | Immediate (< 5 min) | Proxy down, all upstreams unreachable |
| **SEV2** | Partial outage, significant traffic affected | < 15 min | Multiple routes failing, > 10% error rate |
| **SEV3** | Degraded performance, limited impact | < 1 hour | Elevated latency, single upstream unhealthy |
| **SEV4** | Minor issue, minimal user impact | < 4 hours | Non-critical feature degraded |

### Escalation Matrix

| Severity | Primary | Secondary | Management |
|----------|---------|-----------|------------|
| SEV1 | On-call engineer | Team lead | Director (if > 30 min) |
| SEV2 | On-call engineer | Team lead | - |
| SEV3 | On-call engineer | - | - |
| SEV4 | Next business day | - | - |

## Initial Response

### First 5 Minutes Checklist

- [ ] Acknowledge incident in alerting system
- [ ] Assess severity using classification above
- [ ] Open incident channel
- [ ] Declare incident commander if SEV1/SEV2
- [ ] Begin gathering initial diagnostics

### Quick Diagnostic Commands

```bash
# Check proxy health
curl -sf http://localhost:8080/health && echo "OK" || echo "UNHEALTHY"

# Check ready status
curl -sf http://localhost:8080/ready && echo "READY" || echo "NOT READY"

# Get current error rate (last 5 min)
curl -s localhost:9090/metrics | grep 'requests_total' | \
    awk '/5[0-9][0-9]/ {sum+=$2} END {print "5xx errors:", sum}'

# Check process status
systemctl status zentinel

# Check recent logs for errors
journalctl -u zentinel --since "5 minutes ago" | grep -i error | tail -20

# Check upstream health
curl -s localhost:9090/metrics | grep upstream_health

# Check circuit breakers
curl -s localhost:9090/metrics | grep circuit_breaker_state
```

### Initial Triage Decision Tree

```
Is the proxy process running?
├─ NO → Go to: Process Crash Procedure
└─ YES
    └─ Is the health endpoint responding?
        ├─ NO → Go to: Health Check Failure Procedure
        └─ YES
            └─ Are all upstreams healthy?
                ├─ NO → Go to: Upstream Failure Procedure
                └─ YES
                    └─ Is error rate elevated?
                        ├─ YES → Go to: High Error Rate Procedure
                        └─ NO → Go to: Performance Degradation Procedure
```

## Incident Procedures

### Process Crash

**Symptoms**: Zentinel process not running, connections refused

**Immediate Actions**:
```bash
# 1. Attempt restart
systemctl restart zentinel

# 2. Check if it stays up
sleep 5 && systemctl status zentinel

# 3. If still failing, check logs for crash reason
journalctl -u zentinel --since "10 minutes ago" | tail -100

# 4. Check for resource exhaustion
dmesg | grep -i "oom\|killed" | tail -10
free -h
df -h /var /tmp
```

**Common Causes & Fixes**:

| Cause | Diagnostic | Fix |
|-------|------------|-----|
| OOM killed | `dmesg \| grep oom` shows zentinel | Increase memory limits |
| Config error | Logs show parse/validation error | Restore previous config |
| Disk full | `df -h` shows 100% | Clear logs, increase disk |
| Port conflict | Logs show "address in use" | Kill conflicting process |
| Certificate expired | TLS handshake errors | Renew certificates |

**Rollback**:
```bash
# Restore last known good config
cp /etc/zentinel/config.kdl.backup /etc/zentinel/config.kdl
systemctl restart zentinel
```

### Upstream Failure

**Symptoms**: Specific routes returning 502/503, upstream health metrics showing 0

**Immediate Actions**:
```bash
# 1. Identify unhealthy upstreams
curl -s localhost:9090/metrics | grep 'upstream_health{' | grep ' 0'

# 2. Check upstream connectivity from proxy host
nc -zv upstream-host 8080

# 3. Check DNS resolution
dig +short backend.service.internal

# 4. Check network path
traceroute -n <upstream_ip>
```

**Mitigation Options**:

1. **Remove unhealthy targets temporarily** - edit config to comment out the target and reload
2. **Adjust health check thresholds** - increase `unhealthy-threshold` or `timeout-secs`
3. **Enable failover upstream** - add `fallback-upstream` to the route

### High Error Rate

**Symptoms**: > 1% 5xx error rate, elevated latency

**Immediate Actions**:
```bash
# 1. Identify error distribution by route
curl -s localhost:9090/metrics | grep 'requests_total.*status="5' | sort -t'"' -k4

# 2. Check for specific error types
journalctl -u zentinel --since "5 minutes ago" | \
    grep -oP 'error[^,]*' | sort | uniq -c | sort -rn | head

# 3. Check upstream latency
curl -s localhost:9090/metrics | grep 'upstream_request_duration.*quantile="0.99"'
```

**Error Type Actions**:

| Error | Cause | Action |
|-------|-------|--------|
| 502 Bad Gateway | Upstream returning invalid response | Check upstream application logs |
| 503 Service Unavailable | All targets unhealthy or circuit breaker open | Follow Upstream Failure procedure |
| 504 Gateway Timeout | Upstream not responding in time | Increase timeout temporarily |
| 500 Internal Server Error | Proxy internal error | Check proxy logs, restart if persistent |

### Memory Exhaustion

**Symptoms**: High memory usage, slow responses, potential OOM

**Immediate Actions**:
```bash
# 1. Check current memory usage
curl -s localhost:9090/metrics | grep process_resident_memory_bytes

# 2. Check connection count
curl -s localhost:9090/metrics | grep open_connections

# 3. Check request queue depth
curl -s localhost:9090/metrics | grep pending_requests
```

**Mitigation**:
```kdl
// Reduce connection limits immediately
limits {
    max-connections 5000
    max-connections-per-client 50
}
```

Then reload with `kill -HUP $(cat /var/run/zentinel.pid)`.

### TLS/Certificate Issues

**Symptoms**: TLS handshake failures, certificate errors in logs

**Diagnostic Commands**:
```bash
# Check certificate expiration
openssl x509 -in /etc/zentinel/certs/server.crt -noout -dates

# Verify certificate chain
openssl verify -CAfile /etc/zentinel/certs/ca.crt /etc/zentinel/certs/server.crt

# Check certificate matches key
diff <(openssl x509 -in server.crt -noout -modulus) \
     <(openssl rsa -in server.key -noout -modulus)

# Test TLS connection
openssl s_client -connect localhost:443 -servername your.domain.com </dev/null
```

**Certificate Renewal**:
```bash
# Deploy new certificate
cp /path/to/new/cert.crt /etc/zentinel/certs/server.crt
cp /path/to/new/key.key /etc/zentinel/certs/server.key
chmod 600 /etc/zentinel/certs/server.key

# Reload (zero-downtime)
kill -HUP $(cat /var/run/zentinel.pid)
```

### DDoS/Attack Response

**Symptoms**: Massive traffic spike, resource exhaustion

**Immediate Actions**:
```bash
# Identify top client IPs
journalctl -u zentinel --since "5 minutes ago" -o json | \
    jq -r '.client_ip' | sort | uniq -c | sort -rn | head -20

# Check for attack patterns
journalctl -u zentinel --since "5 minutes ago" | \
    grep -oP 'path="[^"]*"' | sort | uniq -c | sort -rn | head -20
```

**Mitigation**:

1. Enable aggressive rate limiting in config
2. Block attacking IPs via firewall: `iptables -A INPUT -s $ATTACKER_IP -j DROP`
3. Reduce resource limits to preserve availability

## Post-Incident

### Immediate Actions (< 1 hour after resolution)

- [ ] Update status page to "Resolved"
- [ ] Send all-clear communication
- [ ] Document timeline in incident channel
- [ ] Preserve logs and metrics snapshots
- [ ] Schedule post-mortem (SEV1/SEV2: within 48 hours)

### Log Preservation

```bash
INCIDENT_ID="INC-$(date +%Y%m%d)-001"
mkdir -p /var/log/zentinel/incidents/$INCIDENT_ID

# Save logs
journalctl -u zentinel --since "1 hour ago" > \
    /var/log/zentinel/incidents/$INCIDENT_ID/zentinel.log

# Save metrics snapshot
curl -s localhost:9090/metrics > \
    /var/log/zentinel/incidents/$INCIDENT_ID/metrics.txt

# Save config at time of incident
cp /etc/zentinel/config.kdl /var/log/zentinel/incidents/$INCIDENT_ID/
```

### Post-Mortem Template

```markdown
# Incident Post-Mortem: [INCIDENT_ID]

## Summary
- **Date**: YYYY-MM-DD
- **Duration**: X hours Y minutes
- **Severity**: SEVN
- **Impact**: [Brief description of user impact]

## Timeline
| Time (UTC) | Event |
|------------|-------|
| HH:MM | First alert triggered |
| HH:MM | Incident declared |
| HH:MM | Root cause identified |
| HH:MM | Mitigation applied |
| HH:MM | Full resolution |

## Root Cause
[Detailed explanation]

## Action Items
| Action | Owner | Due Date | Status |
|--------|-------|----------|--------|
| [Action item] | [Owner] | YYYY-MM-DD | Open |

## Lessons Learned
- What went well:
- What could be improved:
```

## Quick Reference

### Critical Commands

```bash
# Health check
curl -sf localhost:8080/health

# Reload config
kill -HUP $(cat /var/run/zentinel.pid)

# Graceful restart
systemctl restart zentinel

# View errors
journalctl -u zentinel | grep ERROR | tail -20

# Check upstreams
curl -s localhost:9090/metrics | grep upstream_health
```

### Key Metrics to Check First

1. `zentinel_requests_total{status="5xx"}` - Error count
2. `zentinel_upstream_health` - Upstream availability
3. `zentinel_request_duration_seconds` - Latency
4. `zentinel_open_connections` - Connection count
5. `zentinel_circuit_breaker_state` - Circuit breaker status

## See Also

- [Troubleshooting](../troubleshooting/) - Common issue resolution
- [Health Monitoring](../health-monitoring/) - Health checks and alerting
- [Metrics Reference](../../reference/metrics/) - Available metrics

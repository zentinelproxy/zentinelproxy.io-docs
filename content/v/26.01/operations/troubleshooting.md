+++
title = "Troubleshooting"
weight = 1
+++

Guide to diagnosing and resolving common Sentinel issues.

## Quick Diagnostics

### Check Service Status

```bash
# Is Sentinel running?
ps aux | grep sentinel
systemctl status sentinel

# Check listening ports
ss -tlnp | grep sentinel
lsof -i :8080

# View recent logs
journalctl -u sentinel -n 100
tail -f /var/log/sentinel/error.log
```

### Test Configuration

```bash
# Validate configuration
sentinel --test --config sentinel.kdl

# Test with verbose output
sentinel --test --verbose --config sentinel.kdl
```

### Check Connectivity

```bash
# Test listener
curl -v http://localhost:8080/health

# Test upstream directly
curl -v http://backend-server:8080/health

# Check DNS resolution
dig backend.internal
```

## Common Issues

### Startup Failures

#### "Address already in use"

```
Error: Address already in use (os error 98)
```

**Cause:** Another process is using the port.

**Solution:**
```bash
# Find what's using the port
lsof -i :8080
# or
ss -tlnp | grep 8080

# Kill the process or change Sentinel's port
```

#### "Permission denied" on privileged ports

```
Error: Permission denied (os error 13)
```

**Cause:** Ports below 1024 require root or capabilities.

**Solution:**
```bash
# Option 1: Grant capability
sudo setcap cap_net_bind_service=+ep /usr/local/bin/sentinel

# Option 2: Use port >= 1024 and redirect
iptables -t nat -A PREROUTING -p tcp --dport 80 -j REDIRECT --to-port 8080

# Option 3: Use systemd socket activation
```

#### "Configuration file not found"

```
Error: Configuration error: Failed to load configuration file
```

**Solution:**
```bash
# Check file exists and permissions
ls -la /etc/sentinel/sentinel.kdl

# Verify path
sentinel --test --config /etc/sentinel/sentinel.kdl
```

### Connection Issues

#### 502 Bad Gateway

**Symptoms:** All requests return 502.

**Diagnosis:**
```bash
# Check upstream health
curl http://localhost:9090/admin/upstreams

# Test upstream directly
curl -v http://upstream-host:port/health

# Check logs for upstream errors
grep "upstream" /var/log/sentinel/error.log
```

**Common causes:**
1. Upstream server not running
2. Firewall blocking connection
3. DNS resolution failure
4. Wrong upstream address/port

**Solutions:**
```bash
# Verify upstream is accessible
nc -zv upstream-host 8080

# Check firewall
iptables -L -n | grep 8080

# Verify DNS
dig upstream.internal
```

#### 503 Service Unavailable

**Symptoms:** Intermittent 503 errors.

**Diagnosis:**
```bash
# Check circuit breaker status
curl http://localhost:9090/admin/upstreams

# Check connection limits
curl http://localhost:9090/metrics | grep connections
```

**Common causes:**
1. Circuit breaker open
2. All upstreams unhealthy
3. Connection limit reached
4. Rate limit exceeded

**Solutions:**
```kdl
// Increase connection limits
limits {
    max-total-connections 20000
    max-connections-per-client 200
}

// Adjust circuit breaker
routes {
    route "api" {
        circuit-breaker {
            failure-threshold 10    // More tolerant
            timeout-seconds 60      // Longer recovery
        }
    }
}
```

#### 504 Gateway Timeout

**Symptoms:** Requests timeout after delay.

**Diagnosis:**
```bash
# Check upstream response time
time curl http://upstream-host:8080/endpoint

# Check timeout settings
grep timeout sentinel.kdl
```

**Solutions:**
```kdl
// Increase timeouts for slow endpoints
routes {
    route "slow-api" {
        policies {
            timeout-secs 120
        }
    }
}

upstreams {
    upstream "backend" {
        timeouts {
            request-secs 120
            read-secs 60
        }
    }
}
```

### TLS/Certificate Issues

#### "Invalid certificate chain"

```bash
# Verify certificate
openssl x509 -in /etc/sentinel/certs/server.crt -noout -text

# Check certificate chain
openssl verify -CAfile ca.crt server.crt

# Test TLS connection
openssl s_client -connect localhost:443 -servername example.com
```

#### "Certificate expired"

```bash
# Check expiration
openssl x509 -in server.crt -noout -dates

# Check days until expiration
openssl x509 -in server.crt -noout -enddate
```

#### Key/cert mismatch

```bash
# Compare modulus
openssl x509 -noout -modulus -in server.crt | md5sum
openssl rsa -noout -modulus -in server.key | md5sum
# These should match
```

### Performance Issues

#### High Latency

**Diagnosis:**
```bash
# Check P99 latency
curl -s http://localhost:9090/metrics | grep request_duration

# Profile request
curl -w "@curl-format.txt" http://localhost:8080/api/endpoint
```

**curl-format.txt:**
```
     time_namelookup:  %{time_namelookup}s\n
        time_connect:  %{time_connect}s\n
     time_appconnect:  %{time_appconnect}s\n
    time_pretransfer:  %{time_pretransfer}s\n
       time_redirect:  %{time_redirect}s\n
  time_starttransfer:  %{time_starttransfer}s\n
          time_total:  %{time_total}s\n
```

**Common causes and solutions:**

| Cause | Solution |
|-------|----------|
| DNS resolution slow | Use IP addresses or local DNS cache |
| TLS handshake slow | Enable session resumption |
| Connection establishment | Increase connection pool |
| Upstream slow | Add caching, optimize backend |
| Body too large | Stream instead of buffer |

#### High Memory Usage

**Diagnosis:**
```bash
# Check memory metrics
curl -s http://localhost:9090/metrics | grep memory

# Check process memory
ps aux | grep sentinel
cat /proc/$(pgrep sentinel)/status | grep Vm
```

**Solutions:**
```kdl
// Reduce buffer sizes
limits {
    max-body-buffer-bytes 524288      // 512KB
    max-body-inspection-bytes 524288
}

// Reduce connection pool
upstreams {
    upstream "backend" {
        connection-pool {
            max-connections 50
            max-idle 10
        }
    }
}

// Set memory limit
limits {
    max-memory-percent 70.0
}
```

#### High CPU Usage

**Diagnosis:**
```bash
# Check CPU metrics
curl -s http://localhost:9090/metrics | grep cpu

# Profile with perf (Linux)
perf top -p $(pgrep sentinel)
```

**Solutions:**
```kdl
// Adjust worker threads
server {
    worker-threads 4  // Match CPU cores
}

// Reduce logging
// Set RUST_LOG=warn in environment

// Disable unnecessary features
routes {
    route "api" {
        policies {
            buffer-requests false
            buffer-responses false
        }
    }
}
```

## Debug Mode

### Enable Debug Logging

```bash
# Via environment
RUST_LOG=debug sentinel --config sentinel.kdl

# Module-specific debug
RUST_LOG=sentinel::proxy=debug,sentinel::agents=trace sentinel --config sentinel.kdl

# Pretty format for development
SENTINEL_LOG_FORMAT=pretty RUST_LOG=debug sentinel --config sentinel.kdl
```

### Log Analysis

```bash
# Find errors
grep -i error /var/log/sentinel/*.log

# Find specific correlation ID
grep "2kF8xQw4BnM" /var/log/sentinel/*.log

# Count errors by type
grep "error" /var/log/sentinel/error.log | jq -r '.error_type' | sort | uniq -c

# Find slow requests (>1s)
jq 'select(.duration_ms > 1000)' /var/log/sentinel/access.log
```

### Request Tracing

Every request has a correlation ID in `X-Correlation-Id` header:

```bash
# Make request and get correlation ID
curl -i http://localhost:8080/api/endpoint
# X-Correlation-Id: 2kF8xQw4BnM

# Search logs by ID
grep "2kF8xQw4BnM" /var/log/sentinel/*.log | jq .
```

### Metrics Analysis

```bash
# Dump all metrics
curl http://localhost:9090/metrics > metrics.txt

# Check error rates
curl -s http://localhost:9090/metrics | grep -E "requests_total.*status=\"5"

# Check upstream health
curl -s http://localhost:9090/metrics | grep circuit_breaker
```

## Health Check Failures

### Sentinel Health Check

```bash
# Basic health
curl http://localhost:9090/health

# Detailed status
curl http://localhost:9090/status
```

### Upstream Health Check Failures

**Diagnosis:**
```bash
# Check upstream status
curl http://localhost:9090/admin/upstreams

# Test health endpoint directly
curl -v http://upstream:8080/health
```

**Common causes:**
1. Health endpoint returns non-200
2. Health check timeout too short
3. Health endpoint path wrong
4. Upstream overloaded

**Solutions:**
```kdl
upstreams {
    upstream "backend" {
        health-check {
            type "http" {
                path "/health"           // Verify path
                expected-status 200
            }
            timeout-secs 10              // Increase timeout
            unhealthy-threshold 5        // More tolerant
        }
    }
}
```

## Agent Issues

### Agent Connection Failed

```
Agent error: auth - connection refused
```

**Diagnosis:**
```bash
# Check agent is running
ps aux | grep agent

# Check socket exists
ls -la /var/run/sentinel/*.sock

# Test socket connection
nc -U /var/run/sentinel/auth.sock
```

**Solutions:**
```bash
# Start agent
systemctl start sentinel-auth-agent

# Check socket permissions
chmod 660 /var/run/sentinel/auth.sock
chown sentinel:sentinel /var/run/sentinel/auth.sock
```

### Agent Timeouts

**Diagnosis:**
```bash
# Check agent latency metrics
curl -s http://localhost:9090/metrics | grep agent_latency

# Check timeout count
curl -s http://localhost:9090/metrics | grep agent_timeout
```

**Solutions:**
```kdl
agents {
    agent "auth" {
        timeout-ms 200               // Increase timeout
        circuit-breaker {
            failure-threshold 10     // More tolerant
        }
    }
}
```

## Configuration Reload Issues

### Reload Failed

```bash
# Check reload status
journalctl -u sentinel | grep -i reload

# Validate new config before reload
sentinel --test --config sentinel.kdl

# Manual reload
kill -HUP $(cat /var/run/sentinel.pid)
```

### Config Validation Errors

```bash
# Get detailed validation errors
sentinel --test --verbose --config sentinel.kdl 2>&1

# Common issues:
# - Route references undefined upstream
# - Duplicate route/upstream IDs
# - Invalid regex in path-regex
# - Missing required fields
```

## Getting Help

### Collect Diagnostic Information

```bash
# System info
uname -a
cat /etc/os-release

# Sentinel version
sentinel --version

# Configuration (sanitized)
cat sentinel.kdl | grep -v -E "(key|password|secret)"

# Recent logs
journalctl -u sentinel --since "1 hour ago"

# Metrics snapshot
curl http://localhost:9090/metrics > metrics.txt
```

### Log Locations

| Platform | Location |
|----------|----------|
| systemd | `journalctl -u sentinel` |
| Docker | `docker logs sentinel` |
| Kubernetes | `kubectl logs -l app=sentinel` |
| Custom | Check `working-directory` in config |

## See Also

- [Health Monitoring](../health-monitoring/) - Health checks and monitoring
- [Metrics Reference](../../reference/metrics/) - Available metrics
- [Error Codes](../../reference/error-codes/) - Error types and codes

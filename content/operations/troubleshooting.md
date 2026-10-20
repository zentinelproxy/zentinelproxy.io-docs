+++
title = "Troubleshooting"
weight = 1
updated = 2026-10-20
+++

Guide to diagnosing and resolving common Zentinel issues.

## Quick Diagnostics

### Check Service Status

```bash
# Is Zentinel running?
ps aux | grep zentinel
systemctl status zentinel

# Check listening ports
ss -tlnp | grep zentinel
lsof -i :8080

# View recent logs
journalctl -u zentinel -n 100
tail -f /var/log/zentinel/error.log
```

### Test Configuration

```bash
# Validate configuration
zentinel --test --config zentinel.kdl

# Find settings that are being ignored (misspelled or misplaced keys)
zentinel lint --config zentinel.kdl

# Test with verbose output
zentinel --test --verbose --config zentinel.kdl
```

If a setting seems to have no effect, run `zentinel test` or `lint` first. KDL accepts any name, so a typo in an optional setting is not an error: the proxy runs on the default and the check passes, but from 26.10_5 both `zentinel test` and `lint` print "is being ignored" for it (`zentinel test --strict` fails). Before 26.10_5 only `lint` reported it. `-t` / `--test` prints the warnings too but has no `--strict`.

If neither reports anything and the setting still does nothing, check [Known Limitations](/reference/known-limitations/). It lists settings the current release accepts but does not apply, and behaviour that differs from what the configuration suggests, with workarounds.

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

# Kill the process or change Zentinel's port
```

#### "Permission denied" on privileged ports

```
Error: Permission denied (os error 13)
```

**Cause:** Ports below 1024 require root or capabilities.

**Solution:**
```bash
# Option 1: Grant capability
sudo setcap cap_net_bind_service=+ep /usr/local/bin/zentinel

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
ls -la /etc/zentinel/zentinel.kdl

# Verify path
zentinel --test --config /etc/zentinel/zentinel.kdl
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
grep "upstream" /var/log/zentinel/error.log
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
# Check circuit breaker and target health
curl http://localhost:9090/admin/upstreams

# Look for health-check failures in the log
journalctl -u zentinel | grep -i health
```

**Common causes:**
1. Circuit breaker open
2. Every target of the upstream is failing its health check. From 26.10_5, failing targets are taken out of rotation, and when none is left Zentinel answers 503 instead of trying them. Check the health-check `path`, `expected-status` and `host` against what the backend returns.

3. From 26.10_6, the request was over `limits { max-in-flight-requests }`, globally or in its namespace. That `503` carries `Retry-After: 1`, and the proxy logs `Request refused: max-in-flight-requests reached` at `WARN`. See [Limits](/configuration/limits/#concurrency-limits).

Rate limits answer with their `status-code` (default `429`). Connections over `max-total-connections` or `max-connections-per-client` are closed before a request is read, so they show up as resets, not as `503`.

**Solutions:**
```kdl
// Adjust the upstream circuit breaker and health check
upstreams {
    upstream "backend" {
        target "10.0.1.10:8080"
        circuit-breaker {
            failure-threshold 10    // More tolerant
            timeout-seconds 60      // Longer recovery
        }
        health-check {
            type "http" {
                path "/health"
                expected-status 200
            }
            unhealthy-threshold 5   // More tolerant
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
grep timeout zentinel.kdl
```

**Solutions:**
```kdl
// Increase timeouts for slow endpoints
routes {
    route "slow-api" {
        matches { path-prefix "/reports/" }
        upstream "backend"
        policies {
            timeout-secs 120
        }
    }
}

upstreams {
    upstream "backend" {
        target "10.0.1.10:8080"
        timeouts {
            request-secs 120
            read-secs 60
        }
    }
}
```

### Redirect Loops

**Symptoms:** Browser shows "too many redirects" or curl returns `ERR_TOO_MANY_REDIRECTS`. The backend keeps redirecting between HTTP and HTTPS or between `www` and non-`www`.

**Common causes:**

1. **Missing upstream `tls` block** - Your backend expects HTTPS (port 443), but Zentinel is connecting with plaintext HTTP. The backend sees an HTTP request and redirects to HTTPS, creating an infinite loop.

2. **Host header mismatch** - Your backend checks the `Host` header and redirects to a canonical domain (e.g., `www.example.com`), but Zentinel forwards a different `Host` value.

3. **`X-Forwarded-Proto` says `http`** - The backend checks the protocol and issues an HTTPS redirect because it doesn't know the client already connected over HTTPS. This happens when TLS ends at a load balancer in front of Zentinel, or on releases before 26.10_5.

**Solution for cause 1 (most common):**

Add a `tls` block to your upstream when connecting to an HTTPS backend:

```kdl
upstreams {
    upstream "backend" {
        target "api.example.com:443"
        // Required when the backend serves HTTPS
        tls {
            sni "api.example.com"
        }
    }
}
```

Without the `tls` block, Zentinel connects with plaintext HTTP even to port 443. The backend's TLS listener receives garbage data and either resets the connection (502) or, if it has an HTTP-to-HTTPS redirect, creates a redirect loop.

**Solution for cause 2:**

Set the correct `Host` header in your route policies:

```kdl
routes {
    route "api" {
        matches { path-prefix "/" }
        upstream "backend"
        policies {
            request-headers {
                set {
                    "Host" "www.example.com"
                }
            }
        }
    }
}
```

**Solution for cause 3:**

From 26.10_5, Zentinel sets `X-Forwarded-Proto` to `https` for requests that arrived on a TLS listener and to `http` otherwise. If TLS ends at a load balancer that forwards plain HTTP to Zentinel, list the load balancer in the listener's [`trusted-proxies`](/configuration/listeners/#trusted-proxies) so its `X-Forwarded-Proto: https` is kept instead of replaced:

```fragment,kdl
listener "public" {
    address "0.0.0.0:8080"
    protocol "http"
    trusted-proxies "10.0.0.0/8"
}
```

Before 26.10_5, Zentinel did not send `X-Forwarded-Proto` at all. On those releases, or to force a value, set it on the route:

```kdl
routes {
    route "api" {
        matches { path-prefix "/" }
        upstream "backend"
        policies {
            request-headers {
                set {
                    "X-Forwarded-Proto" "https"
                }
            }
        }
    }
}
```

**Debugging redirect loops:**

```bash
# Follow redirects and show each step
curl -v -L --max-redirs 5 http://localhost:8080/

# Check what the backend returns when accessed directly
curl -v https://api.example.com:443/

# Enable debug logging to see upstream connections
RUST_LOG=zentinel::proxy=debug zentinel --config zentinel.kdl
```

### TLS/Certificate Issues

#### "Invalid certificate chain"

```bash
# Verify certificate
openssl x509 -in /etc/zentinel/certs/server.crt -noout -text

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
ps aux | grep zentinel
cat /proc/$(pgrep zentinel)/status | grep Vm
```

**Solutions:**
```kdl
// Cap request bodies (bodies may be buffered for agent inspection)
limits {
    max-body-size 1048576   // 1MB
}

// Reduce connection pool
upstreams {
    upstream "backend" {
        target "10.0.1.10:8080"
        connection-pool {
            max-connections 50
            max-idle 10
        }
    }
}

// There is no memory cap setting: max-memory-percent and max-memory-bytes
// are not read. Cap memory with the service manager instead
// (systemd MemoryMax=, a container memory limit).
```

#### High CPU Usage

**Diagnosis:**
```bash
# Check CPU metrics
curl -s http://localhost:9090/metrics | grep cpu

# Profile with perf (Linux)
perf top -p $(pgrep zentinel)
```

**Solutions:**
```kdl
listeners {
    listener "http" {
        address "0.0.0.0:8080"
        protocol "http"
    }
}

// Adjust worker threads
system {
    worker-threads 4  // Match CPU cores
}

// Reduce logging
// Set RUST_LOG=warn in environment

upstreams {
    upstream "backend" {
        target "127.0.0.1:3000"
    }
}
```

## Debug Mode

### Enable Debug Logging

```bash
# Via environment
RUST_LOG=debug zentinel --config zentinel.kdl

# Module-specific debug
RUST_LOG=zentinel::proxy=debug,zentinel::agents=trace zentinel --config zentinel.kdl

# Pretty format for development
ZENTINEL_LOG_FORMAT=pretty RUST_LOG=debug zentinel --config zentinel.kdl
```

### Log Analysis

```bash
# Find errors
grep -i error /var/log/zentinel/*.log

# Find specific correlation ID
grep "2kF8xQw4BnM" /var/log/zentinel/*.log

# Count errors by type
grep "error" /var/log/zentinel/error.log | jq -r '.error_type' | sort | uniq -c

# Find slow requests (>1s)
jq 'select(.duration_ms > 1000)' /var/log/zentinel/access.log
```

### Request Tracing

Every request has a correlation ID in `X-Correlation-Id` header:

```bash
# Make request and get correlation ID
curl -i http://localhost:8080/api/endpoint
# X-Correlation-Id: 2kF8xQw4BnM

# Search logs by ID
grep "2kF8xQw4BnM" /var/log/zentinel/*.log | jq .
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

### Zentinel Health Check

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
        target "10.0.1.10:8080"
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
ls -la /var/run/zentinel/*.sock

# Test socket connection
nc -U /var/run/zentinel/auth.sock
```

**Solutions:**
```bash
# Start agent
systemctl start zentinel-auth-agent

# Check socket permissions
chmod 660 /var/run/zentinel/auth.sock
chown zentinel:zentinel /var/run/zentinel/auth.sock
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
        unix-socket "/var/run/zentinel/auth.sock"
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
journalctl -u zentinel | grep -i reload

# Validate new config before reload
zentinel --test --config zentinel.kdl

# Manual reload
kill -HUP $(cat /var/run/zentinel.pid)
```

### Config Validation Errors

```bash
# Get detailed validation errors
zentinel --test --verbose --config zentinel.kdl 2>&1

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

# Zentinel version
zentinel --version

# Configuration (sanitized)
cat zentinel.kdl | grep -v -E "(key|password|secret)"

# Recent logs
journalctl -u zentinel --since "1 hour ago"

# Metrics snapshot
curl http://localhost:9090/metrics > metrics.txt
```

### Log Locations

| Platform | Location |
|----------|----------|
| systemd | `journalctl -u zentinel` |
| Docker | `docker logs zentinel` |
| Kubernetes | `kubectl logs -l app=zentinel` |
| Custom | Check `working-directory` in config |

## See Also

- [Health Monitoring](../health-monitoring/) - Health checks and monitoring
- [Metrics Reference](../../reference/metrics/) - Available metrics
- [Error Codes](../../reference/error-codes/) - Error types and codes

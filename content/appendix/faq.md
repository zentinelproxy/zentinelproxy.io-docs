+++
title = "FAQ"
weight = 2
+++

Frequently asked questions about Sentinel.

## General

### What is Sentinel?

Sentinel is a high-performance reverse proxy and load balancer built on [Pingora](https://github.com/cloudflare/pingora), Cloudflare's Rust-based proxy framework. It provides HTTP/1.1, HTTP/2, and HTTP/3 support with features like load balancing, health checks, TLS termination, and extensible request processing through agents.

### How does Sentinel compare to nginx?

| Aspect | Sentinel | nginx |
|--------|----------|-------|
| Language | Rust | C |
| Config format | KDL | nginx.conf |
| Hot reload | SIGHUP | `nginx -s reload` |
| Memory safety | Guaranteed | Manual |
| HTTP/3 | Native | Requires patch |
| Extensibility | Agents (external) | Modules (compiled) |

Sentinel offers memory safety guarantees and a more modern configuration format, while nginx has a larger ecosystem and longer track record.

### How does Sentinel compare to Envoy?

Both are modern proxies with similar capabilities. Sentinel uses KDL configuration files while Envoy uses YAML/JSON and xDS APIs. Sentinel is lighter weight and simpler to configure for common use cases, while Envoy offers more extensive observability and service mesh features.

### Is Sentinel production-ready?

Sentinel is under active development. Check the [changelog](../changelog/) for the current version and stability status. For production deployments, thoroughly test your specific use case and monitor the GitHub repository for updates.

## Configuration

### Where should I put the configuration file?

The default location is `/etc/sentinel/sentinel.kdl`. You can specify a different path with `--config`:

```bash
sentinel --config /path/to/sentinel.kdl
```

Or set the `SENTINEL_CONFIG` environment variable.

### How do I validate my configuration?

Use the `--test` flag to validate without starting the server:

```bash
sentinel --test --config sentinel.kdl
```

Add `--verbose` for detailed validation output.

### How do I reload configuration without downtime?

Send a `SIGHUP` signal to the Sentinel process:

```bash
kill -HUP $(cat /var/run/sentinel.pid)
# or
systemctl reload sentinel
```

Sentinel validates the new configuration before applying it. If validation fails, the old configuration remains active.

### Can I use environment variables in configuration?

Currently, environment variables are not interpolated in KDL configuration files. Use separate configuration files for different environments or generate configuration programmatically.

## Networking

### What ports does Sentinel use?

By default:
- **8080** - HTTP traffic (configurable)
- **8443** - HTTPS traffic (configurable)
- **9090** - Admin/metrics endpoint (configurable)

All ports are configurable in the `listeners` block.

### How do I bind to port 80 or 443?

Ports below 1024 require elevated privileges. Options:

1. **Linux capabilities** (recommended):
   ```bash
   sudo setcap cap_net_bind_service=+ep /usr/local/bin/sentinel
   ```

2. **iptables redirect**:
   ```bash
   iptables -t nat -A PREROUTING -p tcp --dport 80 -j REDIRECT --to-port 8080
   ```

3. **Run as root** (not recommended for production)

### Does Sentinel support WebSockets?

Yes. WebSocket connections are proxied transparently when using HTTP/1.1. Ensure your route doesn't have policies that buffer the request body.

### Does Sentinel support gRPC?

Yes. Sentinel can proxy gRPC traffic over HTTP/2. Configure your listener with `protocol "h2"` or `protocol "https"` and ensure the upstream supports HTTP/2.

## TLS

### What TLS versions are supported?

Sentinel supports TLS 1.2 and TLS 1.3. Configure minimum version in the listener:

```kdl
listeners {
    listener "https" {
        tls {
            min-version "1.2"  // or "1.3"
        }
    }
}
```

### How do I configure mTLS (client certificates)?

Enable client authentication in the TLS block:

```kdl
listeners {
    listener "https" {
        tls {
            cert-file "/path/to/server.crt"
            key-file "/path/to/server.key"
            ca-file "/path/to/client-ca.crt"
            client-auth true
        }
    }
}
```

### How do I rotate certificates without downtime?

Update the certificate files on disk and send `SIGHUP` to reload:

```bash
cp new-cert.crt /etc/sentinel/certs/server.crt
cp new-key.key /etc/sentinel/certs/server.key
kill -HUP $(cat /var/run/sentinel.pid)
```

## Load Balancing

### What load balancing algorithms are available?

- `round_robin` - Sequential rotation (default)
- `least_connections` - Server with fewest active connections
- `random` - Random selection
- `ip_hash` - Consistent hashing by client IP
- `weighted` - Weighted random selection
- `consistent_hash` - Consistent hashing for cache affinity
- `power_of_two_choices` - Best of two random choices
- `adaptive` - Response-time based selection

### How do I configure sticky sessions?

Use `ip_hash` or `consistent_hash` load balancing:

```kdl
upstreams {
    upstream "backend" {
        load-balancing "ip_hash"
        targets {
            target { address "10.0.1.1:8080" }
            target { address "10.0.1.2:8080" }
        }
    }
}
```

### How do I drain a server for maintenance?

Set its weight to 0 or remove it from the configuration and reload:

```kdl
// Before
target { address "10.0.1.1:8080" weight=1 }

// Draining
target { address "10.0.1.1:8080" weight=0 }
```

Existing connections will complete; new requests go to other servers.

## Health Checks

### Why is my upstream marked unhealthy?

Check the admin endpoint for details:

```bash
curl http://localhost:9090/admin/upstreams
```

Common causes:
- Health endpoint returning non-200 status
- Health check timeout too short
- Network/firewall blocking health checks
- Upstream server overloaded

### How do I disable health checks?

Remove the `health-check` block from the upstream configuration. Without health checks, Sentinel assumes all targets are healthy.

### Can I use different health check paths for different servers?

Health check configuration applies to all targets in an upstream. If servers need different health endpoints, create separate upstreams.

## Performance

### How many worker threads should I use?

Set `worker-threads 0` (the default) to auto-detect based on CPU cores. For most workloads, one thread per core is optimal. Reduce threads if memory is constrained.

### How do I increase connection limits?

Adjust limits in the configuration:

```kdl
server {
    max-connections 50000
}

limits {
    max-connections-per-client 200
    max-total-connections 50000
}
```

Also increase OS limits:
```bash
ulimit -n 65535
```

### Why am I seeing high latency?

Common causes:
1. **Upstream slow** - Check upstream response times directly
2. **DNS resolution** - Use IP addresses or local DNS cache
3. **TLS handshakes** - Enable session resumption
4. **Connection establishment** - Increase connection pool size
5. **Request buffering** - Disable if not needed

See [Troubleshooting](../../operations/troubleshooting/) for diagnostics.

## Agents

### What are agents used for?

Agents handle request processing tasks that require external logic or state:
- **Authentication** - Validate tokens, check sessions
- **Rate limiting** - Distributed rate limiting with shared state
- **WAF** - Web application firewall inspection
- **Custom logic** - Any request/response transformation

### How do agents communicate with Sentinel?

Agents connect via:
- **Unix sockets** (recommended for local agents)
- **gRPC** (for remote or containerized agents)

### What happens if an agent fails?

Depends on the `failure-mode` setting:
- `closed` (default) - Reject the request (fail-safe)
- `open` - Allow the request to proceed (fail-open)

Circuit breakers prevent repeated failures from overwhelming agents.

## Troubleshooting

### How do I enable debug logging?

Set the `RUST_LOG` environment variable:

```bash
RUST_LOG=debug sentinel --config sentinel.kdl

# Module-specific debugging
RUST_LOG=sentinel::proxy=debug sentinel --config sentinel.kdl
```

### Where are the logs?

| Deployment | Location |
|------------|----------|
| systemd | `journalctl -u sentinel` |
| Docker | `docker logs sentinel` |
| Kubernetes | `kubectl logs -l app=sentinel` |

### How do I trace a specific request?

Every request has a correlation ID in the `X-Correlation-Id` response header. Search logs by this ID:

```bash
curl -i http://localhost:8080/api/endpoint
# Note the X-Correlation-Id header

grep "abc123xyz" /var/log/sentinel/*.log
```

## Migration

### How do I migrate from nginx?

See the [Migration Guide](../../operations/migration/#from-nginx) for detailed configuration mapping and examples.

### How do I migrate from HAProxy?

See the [Migration Guide](../../operations/migration/#from-haproxy) for detailed configuration mapping and examples.

### Can I run Sentinel alongside my existing proxy?

Yes. Run Sentinel on a different port and gradually shift traffic:

```bash
# Sentinel on 8080, nginx on 80
# Test: curl http://localhost:8080/api/endpoint
# Compare: diff <(curl -s nginx/api) <(curl -s sentinel/api)
```

## See Also

- [Glossary](../glossary/) - Term definitions
- [Troubleshooting](../../operations/troubleshooting/) - Diagnostic guides
- [Configuration](../../configuration/) - Full configuration reference


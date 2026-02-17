+++
title = "Reference"
weight = 10
sort_by = "weight"
template = "section.html"
+++

Quick reference documentation for Zentinel operations and troubleshooting.

## Reference Guides

| Guide | Description |
|-------|-------------|
| [CLI Reference](cli/) | Command-line options and usage |
| [Environment Variables](env-vars/) | Environment variable configuration |
| [Error Codes](error-codes/) | HTTP status codes and error responses |
| [Metrics Reference](metrics/) | Prometheus metrics for monitoring |
| [Configuration Schema](config-schema/) | Quick reference for all config options |

## Quick Links

**Starting Zentinel:**
```bash
zentinel --config zentinel.kdl
zentinel --test --config zentinel.kdl  # Validate config
```

**Signals:**
- `SIGHUP` - Reload configuration
- `SIGTERM` / `SIGINT` - Graceful shutdown

**Key Environment Variables:**
- `ZENTINEL_CONFIG` - Configuration file path
- `RUST_LOG` - Log level (debug, info, warn, error)
- `ZENTINEL_LOG_FORMAT` - Log format (json, pretty)

**Metrics Endpoint:**
```bash
curl http://localhost:9090/metrics
```

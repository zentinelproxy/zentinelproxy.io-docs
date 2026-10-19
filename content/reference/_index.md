+++
title = "Reference"
weight = 9
sort_by = "weight"
template = "section.html"

[extra]
# The body already links every child page; skip the theme's auto-generated list.
hide_children = true
+++

Quick reference documentation for Zentinel operations and troubleshooting.

## Reference Guides

| Guide | Description |
|-------|-------------|
| [Directive Index](directives/) | Alphabetical index of all configuration directives |
| [Configuration Schema](config-schema/) | Quick reference for all config options |
| [CLI Reference](cli/) | Command-line options and usage |
| [Environment Variables](env-vars/) | Environment variable configuration |
| [Error Codes](error-codes/) | HTTP status codes and error responses |
| [Metrics Reference](metrics/) | Prometheus metrics for monitoring |
| [Known Limitations](known-limitations/) | Settings that are accepted but not applied in the current release |

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

**Metrics Endpoint:**
```bash
curl http://localhost:9090/metrics
```

+++
title = "Operations"
weight = 7
sort_by = "weight"
template = "section.html"
+++

Guides for operating, monitoring, and maintaining Sentinel in production.

## Operations Guides

| Guide | Description |
|-------|-------------|
| [Troubleshooting](troubleshooting/) | Diagnosing and resolving common issues |
| [Health Monitoring](health-monitoring/) | Health checks, probes, and alerting |
| [Migration Guide](migration/) | Migrating from nginx, HAProxy, Traefik |
| [Incident Response](incident-response/) | Procedures for handling production incidents |
| [Security Hardening](security-hardening/) | Best practices for securing deployments |
| [Capacity Planning](capacity-planning/) | Sizing and scaling guidelines |
| [Upgrade Guide](upgrade-guide/) | Upgrade and migration procedures |

## Quick Diagnostics

```bash
# Check if Sentinel is running
systemctl status sentinel

# Validate configuration
sentinel --test --config sentinel.kdl

# View health status
curl http://localhost:9090/health

# Check upstream health
curl http://localhost:9090/admin/upstreams
```

## Key Signals

- `SIGHUP` - Reload configuration
- `SIGTERM` / `SIGINT` - Graceful shutdown


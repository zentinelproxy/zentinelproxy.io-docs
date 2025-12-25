# Summary

[Introduction](./introduction.md)

# Getting Started

- [Installation](./getting-started/installation.md)
- [Quick Start](./getting-started/quick-start.md)
- [Basic Configuration](./getting-started/basic-configuration.md)
- [First Route](./getting-started/first-route.md)

# Core Concepts

- [Architecture Overview](./concepts/architecture.md)
  - [Pingora Foundation](./concepts/pingora.md)
  - [Request Flow](./concepts/request-flow.md)
  - [Component Design](./concepts/components.md)
- [Routing System](./concepts/routing.md)
  - [Route Matching](./concepts/route-matching.md)
  - [Priority Rules](./concepts/route-priority.md)
  - [Path Variables](./concepts/path-variables.md)

# Configuration

- [Configuration Overview](./configuration/overview.md)
- [KDL Configuration Format](./configuration/kdl-format.md)
- [Server Configuration](./configuration/server.md)
  - [Listeners](./configuration/listeners.md)
  - [TLS Settings](./configuration/tls.md)
  - [Performance Tuning](./configuration/performance.md)
- [Routes Configuration](./configuration/routes.md)
  - [Basic Routes](./configuration/basic-routes.md)
  - [Advanced Routing](./configuration/advanced-routing.md)
  - [Route Groups](./configuration/route-groups.md)
- [Upstream Configuration](./configuration/upstreams.md)
  - [Load Balancing](./configuration/load-balancing.md)
  - [Health Checks](./configuration/health-checks.md)
  - [Connection Pools](./configuration/connection-pools.md)

# Service Types

- [Service Types Overview](./service-types/overview.md)
- [Web Applications](./service-types/web.md)
  - [HTML Error Pages](./service-types/web-error-pages.md)
  - [Session Handling](./service-types/web-sessions.md)
  - [SPA Support](./service-types/spa-support.md)
- [REST APIs](./service-types/api.md)
  - [JSON Validation](./service-types/api-validation.md)
  - [Schema Management](./service-types/api-schemas.md)
  - [Error Responses](./service-types/api-errors.md)
  - [OpenAPI Integration](./service-types/openapi.md)
- [Static Files](./service-types/static.md)
  - [File Serving](./service-types/file-serving.md)
  - [Caching Headers](./service-types/caching.md)
  - [Directory Listing](./service-types/directory-listing.md)
  - [Security Features](./service-types/static-security.md)

# Features

- [Error Handling](./features/error-handling.md)
  - [Custom Error Pages](./features/custom-error-pages.md)
  - [Error Templates](./features/error-templates.md)
  - [Format Negotiation](./features/content-negotiation.md)
- [Request/Response Processing](./features/processing.md)
  - [Headers Manipulation](./features/headers.md)
  - [Request Rewriting](./features/rewriting.md)
  - [Response Filtering](./features/filtering.md)
- [Observability](./features/observability.md)
  - [Logging](./features/logging.md)
  - [Metrics](./features/metrics.md)
  - [Tracing](./features/tracing.md)
- [Security](./features/security.md)
  - [Rate Limiting](./features/rate-limiting.md)
  - [Authentication](./features/authentication.md)
  - [Authorization](./features/authorization.md)
  - [CORS](./features/cors.md)

# Advanced Topics

- [HTTP/3 Support](./advanced/http3.md)
  - [QUIC Protocol](./advanced/quic.md)
  - [0-RTT Configuration](./advanced/0-rtt.md)
  - [Migration Guide](./advanced/http3-migration.md)
- [Performance Optimization](./advanced/performance.md)
  - [Caching Strategies](./advanced/caching-strategies.md)
  - [Connection Management](./advanced/connections.md)
  - [Memory Usage](./advanced/memory.md)
- [High Availability](./advanced/high-availability.md)
  - [Failover](./advanced/failover.md)
  - [Circuit Breakers](./advanced/circuit-breakers.md)
  - [Retry Policies](./advanced/retry.md)
- [Custom Extensions](./advanced/extensions.md)
  - [Writing Middleware](./advanced/middleware.md)
  - [Custom Handlers](./advanced/custom-handlers.md)
  - [Plugin System](./advanced/plugins.md)

# Deployment

- [Deployment Overview](./deployment/overview.md)
- [Docker Deployment](./deployment/docker.md)
  - [Building Images](./deployment/docker-build.md)
  - [Docker Compose](./deployment/docker-compose.md)
  - [Kubernetes](./deployment/kubernetes.md)
- [Systemd Service](./deployment/systemd.md)
- [Configuration Management](./deployment/config-management.md)
- [Rolling Updates](./deployment/rolling-updates.md)
- [Monitoring Setup](./deployment/monitoring.md)

# Operations

- [Health Checks](./operations/health-checks.md)
- [Backup & Recovery](./operations/backup.md)
- [Troubleshooting](./operations/troubleshooting.md)
  - [Common Issues](./operations/common-issues.md)
  - [Debug Mode](./operations/debug-mode.md)
  - [Performance Issues](./operations/perf-issues.md)
- [Migration Guide](./operations/migration.md)
  - [From Nginx](./operations/from-nginx.md)
  - [From HAProxy](./operations/from-haproxy.md)
  - [From Traefik](./operations/from-traefik.md)

# API Reference

- [Configuration Schema](./reference/config-schema.md)
- [Environment Variables](./reference/env-vars.md)
- [Command Line Options](./reference/cli.md)
- [Error Codes](./reference/error-codes.md)
- [Metrics Reference](./reference/metrics.md)

# Examples

- [Example Configurations](./examples/configurations.md)
  - [Simple Proxy](./examples/simple-proxy.md)
  - [Load Balancer](./examples/load-balancer.md)
  - [API Gateway](./examples/api-gateway.md)
  - [Static Site](./examples/static-site.md)
  - [Mixed Services](./examples/mixed-services.md)
- [Integration Examples](./examples/integrations.md)
  - [With Prometheus](./examples/prometheus.md)
  - [With Grafana](./examples/grafana.md)
  - [With Jaeger](./examples/jaeger.md)

# Development

- [Building from Source](./development/building.md)
- [Development Setup](./development/setup.md)
- [Testing](./development/testing.md)
  - [Unit Tests](./development/unit-tests.md)
  - [Integration Tests](./development/integration-tests.md)
  - [Load Testing](./development/load-testing.md)
- [Contributing](./development/contributing.md)
  - [Code Style](./development/code-style.md)
  - [Pull Request Process](./development/pr-process.md)
  - [Release Process](./development/releases.md)

# Appendices

- [Glossary](./appendix/glossary.md)
- [FAQ](./appendix/faq.md)
- [Changelog](./appendix/changelog.md)
- [License](./appendix/license.md)
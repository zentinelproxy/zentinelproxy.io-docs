+++
title = "Introduction"
weight = 0
sort_by = "weight"
template = "section.html"
+++
Welcome to **Zentinel** documentation version **26.02**.

> **Note**: You are viewing an archived version of the documentation. For the latest documentation, visit the [current version](/).

---

Welcome to **Zentinel**, a high-performance **reverse proxy** platform built on [Cloudflare's Pingora](https://github.com/cloudflare/pingora) framework. Zentinel extends Pingora's robust foundation with enterprise-grade features designed for modern web infrastructure.

## Key Features

### High Performance
- Built on Pingora's async Rust foundation
- Memory-safe architecture with zero-copy operations
- Efficient connection pooling and keep-alive management
- Optimized for both throughput and latency

### Service-Type Awareness
Zentinel understands different service types and optimizes behavior accordingly:

- **Web Applications**: HTML error pages, session handling, SPA support
- **REST APIs**: JSON schema validation, structured error responses, OpenAPI integration
- **Static Files**: Direct file serving, automatic MIME types, caching headers

### Advanced Routing
- Flexible path-based and host-based routing
- Route priorities and groups
- Path variables and pattern matching
- Per-route configuration overrides

### Comprehensive Error Handling
- Service-type-specific error formats (HTML, JSON, XML, Text)
- Custom error page templates with variable substitution
- Graceful fallbacks for connection failures
- Detailed error tracking with request IDs

### Observability
- Structured logging with configurable levels
- Prometheus-compatible metrics
- Distributed tracing support
- Health check endpoints

### Security Features
- Path traversal protection for static files
- Request validation and sanitization
- Rate limiting capabilities
- TLS/SSL with modern cipher suites
- HTTP/3 preparation with QUIC support (ready for activation)

### Configuration
- Human-friendly KDL configuration format
- Hot reload without downtime
- Environment variable substitution
- Comprehensive validation on startup

## Why Zentinel?

### Production-Ready
Zentinel is designed for production use from the ground up. Every feature is implemented with reliability, performance, and operational excellence in mind.

### Type-Safe and Memory-Safe
Written in Rust, Zentinel eliminates entire classes of bugs common in traditional proxies, including buffer overflows, use-after-free errors, and data races.

### Cloud-Native
Built for modern cloud environments with support for:
- Container deployments (Docker, Kubernetes)
- Horizontal scaling
- Service mesh integration
- Dynamic configuration

### Developer-Friendly
- Clear, expressive configuration
- Comprehensive error messages
- Extensive documentation
- Example configurations for common use cases

## Use Cases

Zentinel excels in various deployment scenarios:

- **API Gateway**: Validate requests, transform responses, implement rate limiting
- **Static Content Delivery**: Serve files directly with optimal caching headers
- **Load Balancer**: Distribute traffic across multiple upstream servers
- **Web Application Proxy**: Handle sessions, provide custom error pages, support SPAs
- **Microservices Router**: Route requests to different services based on paths
- **Edge Proxy**: Terminate SSL, implement security policies, cache responses

## Architecture Highlights

Zentinel leverages Pingora's battle-tested architecture while adding its own innovations:

```text
Client Request
     ↓
[TLS Termination]
     ↓
[Route Matching] ← Service Type Detection
     ↓
[Request Processing]
     ├─→ Static File Serving (no upstream)
     ├─→ API Validation → Upstream
     └─→ Web App Processing → Upstream
     ↓
[Response Processing]
     ├─→ Error Page Generation
     ├─→ Header Manipulation
     └─→ Caching Headers
     ↓
Client Response
```

## Getting Started

This documentation will guide you through:

1. **[Installation](./getting-started/installation.md)** — Get Zentinel up and running
2. **[Quick Start](./getting-started/quick-start.md)** — Your first proxy configuration
3. **[Core Concepts](./concepts/architecture.md)** — Understand how Zentinel works
4. **[Configuration](./configuration/file-format.md)** — Master the configuration system
5. **[Features](./features/)** — Explore all capabilities
6. **[Deployment](./deployment/docker.md)** — Deploy to production

## Documentation Structure

- **[Getting Started](./getting-started/)** — Installation and basic setup
- **[Core Concepts](./concepts/)** — Fundamental architecture and design principles
- **[Configuration](./configuration/)** — Detailed configuration reference
- **[Features](./features/)** — Complete feature list with code references
- **[Agents](./agents/)** — External agent system for extensibility
- **[Operations](./operations/)** — Production management and troubleshooting
- **[Deployment](./deployment/)** — Container and cloud deployment guides
- **[Control Plane](./control-plane/)** — Fleet management, rollouts, and observability
- **[Examples](./examples/)** — Real-world configuration examples
- **[Reference](./reference/)** — Metrics, CLI, and API documentation
- **[Development](./development/)** — Contributing to Zentinel

## Community

- 💬 **[Discussions](https://github.com/zentinelproxy/zentinel/discussions)** — Questions, ideas, show & tell
- 🐛 **[Issues](https://github.com/zentinelproxy/zentinel/issues)** — Bug reports and feature requests
- 📦 **[GitHub](https://github.com/zentinelproxy/zentinel)** — Source code and releases

Contributions are welcome! See our [Contributing Guide](./development/contributing.md) to get started.

## Version Information

This documentation covers Zentinel release **26.02** (archived). For the latest updates and changes, see the [Changelog](./appendix/changelog.md). For details on the versioning scheme, see [Versioning](./appendix/versioning.md).

## License

Zentinel is open-source software licensed under the Apache License, Version 2.0. See the [License](./appendix/license.md) page for details.

---

Ready to get started? Head to the [Installation Guide](./getting-started/installation.md) to begin your journey with Zentinel!

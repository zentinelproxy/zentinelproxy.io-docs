+++
title = "Versioning"
weight = 2
+++

How Sentinel versions work, mapping between release and crate versions, and changelogs.

## Dual Versioning Scheme

Sentinel uses two versioning systems for different purposes:

| System | Format | Example | Used For |
|--------|--------|---------|----------|
| **Release Version** | CalVer (`YY.MM`) | `26.01` | Documentation, downloads, public announcements |
| **Crate Version** | SemVer (`MAJOR.MINOR.PATCH`) | `0.1.0` | Cargo.toml, crates.io, dependency management |

### Release Version (CalVer)

Public-facing releases use [Calendar Versioning](https://calver.org/) in `YY.MM` format:

- `26.01` = January 2026
- `25.12` = December 2025

This provides:
- Clear indication of release age
- No implied stability promises beyond the release notes
- Simple chronological ordering

### Crate Version (SemVer)

Rust crates published to crates.io use [Semantic Versioning](https://semver.org/):

```
MAJOR.MINOR.PATCH

0.1.0  - Initial development
0.2.0  - New features (pre-1.0, may have breaking changes)
1.0.0  - First stable release
1.1.0  - New features, backwards compatible
1.1.1  - Bug fixes only
2.0.0  - Breaking changes
```

## Version Mapping

This table maps public release versions to their corresponding crate versions:

| Release | Crate Version | Protocol | Release Date | Status |
|---------|---------------|----------|--------------|--------|
| **26.01** | `0.3.0` | `0.2.0` | 2026-01-XX | Current |
| **25.12** | `0.2.0` | `0.1.0` | 2025-12-15 | Previous |
| — | `0.1.0` | `0.1.0` | 2025-11-01 | Internal |

### Finding Your Version

**From the binary:**

```bash
sentinel --version
# sentinel 0.3.0 (release 26.01)
```

**From Cargo.toml:**

```toml
[dependencies]
sentinel = "0.3"
sentinel-agent-protocol = "0.2"
```

**From the documentation URL:**

- `/docs/` — Current release (26.01)
- `/docs/v/25.12/` — Previous release

---

## Changelogs

### Release 26.01

**Crate version:** `0.3.0`
**Protocol version:** `0.2.0`
**Release date:** January 2026

#### Added

- **Traffic Mirroring / Shadow Traffic**
  - Fire-and-forget async request duplication to shadow upstreams
  - Percentage-based sampling (0-100%) for controlled traffic mirroring
  - Header-based filtering for targeted shadow requests
  - Optional request body buffering with configurable size limits
  - Independent failure domain (shadow failures don't affect clients)
  - Zero latency impact on primary request path
  - Separate connection pools for shadow upstreams
  - Prometheus metrics: `shadow_requests_total`, `shadow_errors_total`, `shadow_latency_seconds`

- **API Schema Validation**
  - JSON Schema validation for API routes (requests and responses)
  - OpenAPI 3.0 and Swagger 2.0 specification support
  - Inline JSON Schema definitions in KDL configuration
  - Strict mode to reject additional properties
  - Structured validation error responses with field-level details
  - Support for complex nested schemas and arrays

- WebSocket frame inspection support in agent protocol
- Graceful shutdown improvements
- Connection draining during rolling updates

#### Changed

- Improved upstream health check reliability
- Reduced memory usage for idle connections

#### Security

- Removed archived agents with unsafe FFI code (Lua, WAF, auth, denylist, ratelimit)
- Replaced `unreachable!()` panics with proper error handling in agent-protocol
- Added `WrongConnectionType` error variant for better error handling

---

### Release 25.12

**Crate version:** `0.2.0`
**Protocol version:** `0.1.0`
**Release date:** December 2025

#### Added

- **Core Proxy**
  - HTTP/1.1 and HTTP/2 support
  - HTTPS with TLS 1.2/1.3
  - Configurable listeners (multiple ports, protocols)
  - Request/response header manipulation

- **Routing**
  - Path-based routing with prefix, exact, and regex matching
  - Host-based virtual hosting
  - Method-based routing
  - Header-based routing conditions

- **Upstreams**
  - Multiple backend targets with load balancing
  - Round-robin and random load balancing strategies
  - Active health checks (HTTP, TCP)
  - Passive health monitoring with circuit breaker
  - Connection pooling

- **Agent System**
  - Unix socket transport for local agents
  - gRPC transport for remote agents
  - Request/response lifecycle hooks
  - WebSocket frame inspection hooks
  - Fail-open mode for agent failures
  - Agent timeout configuration

- **Observability**
  - Prometheus metrics endpoint
  - Structured JSON logging
  - Request tracing with correlation IDs
  - OpenTelemetry integration

- **Configuration**
  - KDL configuration format
  - Environment variable substitution
  - Configuration validation
  - Hot reload via SIGHUP

---

## Upgrade Guides

### From 25.12 to 26.01

No breaking changes. Direct upgrade supported.

```bash
# Stop current version
systemctl stop sentinel

# Install new version
curl -Lo /usr/local/bin/sentinel \
    https://github.com/raskell-io/sentinel/releases/download/26.01/sentinel
chmod +x /usr/local/bin/sentinel

# Validate configuration
sentinel validate -c /etc/sentinel/sentinel.kdl

# Start new version
systemctl start sentinel
```

**New features to consider:**

- [Traffic Mirroring](/configuration/routes/#shadow) for canary deployments
- [Schema Validation](/configuration/routes/#schema-validation) for API routes

---

## Compatibility Matrix

### Agent Compatibility

| Sentinel Release | Protocol | Compatible Agent Versions |
|------------------|----------|---------------------------|
| 26.01 | `0.2.0` | Agents built with protocol `0.2.x` |
| 25.12 | `0.1.0` | Agents built with protocol `0.1.x` |

### Rust Toolchain

| Sentinel Release | Minimum Rust Version | Recommended |
|------------------|----------------------|-------------|
| 26.01 | 1.75.0 | 1.83.0+ |
| 25.12 | 1.70.0 | 1.75.0+ |

---

## Release Schedule

Sentinel follows a monthly release cadence:

- **Feature releases:** First week of each month
- **Patch releases:** As needed for security or critical bugs
- **LTS releases:** TBD (planned for first stable major version)

### Version Support

| Release | Status | Security Fixes Until |
|---------|--------|----------------------|
| 26.01 | Current | Active development |
| 25.12 | Previous | 26.03 (3 months) |
| Older | EOL | No support |

---

## See Also

- [Release Process](/development/releases/) — How releases are made
- [GitHub Releases](https://github.com/raskell-io/sentinel/releases) — Download binaries
- [crates.io](https://crates.io/crates/sentinel) — Rust crate registry

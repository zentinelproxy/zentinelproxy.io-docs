+++
title = "Versioning"
weight = 2
+++

How Sentinel versions work, mapping between release and crate versions, and changelogs.

> **Note:** You are viewing documentation for release **25.12**. See the [latest documentation](/) for the current release.

## Dual Versioning Scheme

Sentinel uses two versioning systems for different purposes:

| System | Format | Example | Used For |
|--------|--------|---------|----------|
| **Release Version** | CalVer (`YY.MM`) | `25.12` | Documentation, downloads, public announcements |
| **Crate Version** | SemVer (`MAJOR.MINOR.PATCH`) | `0.2.0` | Cargo.toml, crates.io, dependency management |

### Release Version (CalVer)

Public-facing releases use [Calendar Versioning](https://calver.org/) in `YY.MM` format:

- `25.12` = December 2025
- `25.11` = November 2025

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
| **25.12** | `0.2.0` | `0.1.0` | 2025-12-15 | This version |
| — | `0.1.0` | `0.1.0` | 2025-11-01 | Internal |

### Finding Your Version

**From the binary:**

```bash
sentinel --version
# sentinel 0.2.0 (release 25.12)
```

**From Cargo.toml:**

```toml
[dependencies]
sentinel = "0.2"
sentinel-agent-protocol = "0.1"
```

**From the documentation URL:**

- `/docs/` — Current release
- `/docs/v/25.12/` — This release

---

## Changelog

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

## Compatibility Matrix

### Agent Compatibility

| Sentinel Release | Protocol | Compatible Agent Versions |
|------------------|----------|---------------------------|
| 25.12 | `0.1.0` | Agents built with protocol `0.1.x` |

### Rust Toolchain

| Sentinel Release | Minimum Rust Version | Recommended |
|------------------|----------------------|-------------|
| 25.12 | 1.70.0 | 1.75.0+ |

---

## Release Schedule

Sentinel follows a monthly release cadence:

- **Feature releases:** First week of each month
- **Patch releases:** As needed for security or critical bugs

### Version Support

| Release | Status | Security Fixes Until |
|---------|--------|----------------------|
| 25.12 | Previous | 26.03 (3 months) |

---

## See Also

- [Release Process](/development/releases/) — How releases are made
- [GitHub Releases](https://github.com/raskell-io/sentinel/releases) — Download binaries
- [crates.io](https://crates.io/crates/sentinel) — Rust crate registry

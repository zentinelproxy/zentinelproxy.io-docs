+++
title = "Versioning"
weight = 2
+++

How Sentinel versions work, mapping between release and crate versions, and changelogs.

## Dual Versioning Scheme

Sentinel uses two versioning systems for different audiences:

| System | Format | Example | Audience | Used For |
|--------|--------|---------|----------|----------|
| **Release Version** | CalVer (`YY.MM_PATCH`) | `26.01_0` | Operators, enterprise, docs | Downloads, release tags, LTS windows, support contracts |
| **Crate Version** | SemVer (`MAJOR.MINOR.PATCH`) | `0.3.0` | Library consumers | Cargo.toml, crates.io, dependency management |

**CalVer is the primary version.** When you deploy Sentinel, report issues, reference documentation, or verify supply chain artifacts, use the CalVer release version. SemVer exists solely for Rust's package ecosystem.

### Release Version (CalVer)

All public-facing releases use [Calendar Versioning](https://calver.org/) in `YY.MM_PATCH` format:

```
YY.MM_PATCH

26.01_0  - January 2026, first release
26.01_1  - January 2026, first patch
26.02_0  - February 2026, first release
```

- **`YY.MM`** identifies the release series (e.g., `26.01` = January 2026)
- **`_PATCH`** increments for bug fixes and security patches within a series

This provides:
- **Age at a glance** — `25.06_3` tells you the release is from June 2025
- **LTS windows tied to the calendar** — an LTS branch like `26.01 LTS` receives security backports for 12 months, through January 2027
- **Upgrade urgency** — if you're running `25.06_3` and the current release is `26.01_0`, you're 7 months behind

### Crate Version (SemVer)

Rust crates published to crates.io use [Semantic Versioning](https://semver.org/). This is an implementation detail for library consumers using Sentinel crates as dependencies. Operators do not need to track SemVer.

```
MAJOR.MINOR.PATCH

0.1.0  - Initial development
0.2.0  - New features (pre-1.0, may have breaking changes)
1.0.0  - First stable release
1.1.0  - New features, backwards compatible
1.1.1  - Bug fixes only
2.0.0  - Breaking changes
```

### Which Version Do I Use?

| Context | Use |
|---------|-----|
| Downloading binaries | CalVer (`26.01_0`) |
| Docker image tags | CalVer (`ghcr.io/raskell-io/sentinel:26.01_0`) |
| Filing issues / support tickets | CalVer |
| Verifying supply chain signatures | CalVer (matches release tag) |
| LTS / support contracts | CalVer series (`26.01 LTS`) |
| Cargo.toml dependencies | SemVer (`sentinel = "0.3"`) |
| crates.io | SemVer |

## Version Mapping

This table maps CalVer release versions to their corresponding crate versions:

| Release (CalVer) | Crate Version (SemVer) | Protocol | Release Date | Status |
|---------|---------------|----------|--------------|--------|
| **26.02_0** | `0.4.5` | `0.2.0` | 2026-01-29 | Current |
| **26.01_0** | `0.2.0` | `0.2.0` | 2026-01-01 | Previous |
| **25.12_0** | `0.1.0` | `0.1.0` | 2025-12-15 | Archive |
| — | `0.1.0` | `0.1.0` | 2025-11-01 | Internal |

### Finding Your Version

**From the binary:**

```bash
sentinel --version
# sentinel 26.02_0 (0.4.5)
```

The CalVer release version is shown first, with the crate SemVer in parentheses.

**From Docker:**

```bash
docker inspect ghcr.io/raskell-io/sentinel:26.02_0 --format '{{ index .Config.Labels "org.opencontainers.image.version" }}'
# 26.02_0
```

**From the documentation URL:**

- `/docs/` — Current release (26.02)
- `/docs/v/26.01/` — Previous release
- `/docs/v/25.12/` — Archive

---

## Changelogs

For the full changelog with all patch releases, see [Changelog](../changelog/).

### Release 26.02

**Crate version:** `0.4.5`
**Release date:** January 2026

#### Added

- **Supply chain security for release pipeline**
  - SBOM generation in CycloneDX 1.5 and SPDX 2.3 formats
  - Binary signing with Sigstore cosign (keyless, GitHub Actions OIDC)
  - Container image signing with cosign and SBOM attestation
  - SLSA v1.0 provenance (Build Level 3)
- Per-request allocation reduction in hot path
- DNS-01 ACME challenge support for wildcard certificates
- Agent Protocol v2 connection pooling, load balancing, reverse connections
- Sticky load balancing algorithm

#### Changed

- Major dependency updates (opentelemetry, prost, tonic, tungstenite, sysinfo, and more)

#### Fixed

- Prevent single connection failure from permanently marking upstream target unhealthy
- Security vulnerability fixes via pingora fork

---

### Release 26.01

**Crate version:** `0.2.0` -- `0.3.0`
**Release date:** January 2026

#### Added

- **Traffic Mirroring / Shadow Traffic**
  - Fire-and-forget async request duplication to shadow upstreams
  - Percentage-based sampling (0-100%) for controlled traffic mirroring

- **API Schema Validation**
  - JSON Schema validation for API routes (requests and responses)
  - OpenAPI 3.0 and Swagger 2.0 specification support

- WebSocket frame inspection support in agent protocol
- Graceful shutdown improvements
- Connection draining during rolling updates

#### Changed

- Improved upstream health check reliability
- Reduced memory usage for idle connections

#### Security

- Removed archived agents with unsafe FFI code (Lua, WAF, auth, denylist, ratelimit)
- Replaced `unreachable!()` panics with proper error handling in agent-protocol

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

### From 26.01 to 26.02

No breaking changes. Direct upgrade supported.

```bash
# Stop current version
systemctl stop sentinel

# Install new version
VERSION="26.02_0"
curl -Lo /usr/local/bin/sentinel \
    "https://github.com/raskell-io/sentinel/releases/download/${VERSION}/sentinel-${VERSION}-linux-amd64.tar.gz"
tar -xzf "sentinel-${VERSION}-linux-amd64.tar.gz"
chmod +x sentinel && sudo mv sentinel /usr/local/bin/

# Validate configuration
sentinel validate -c /etc/sentinel/sentinel.kdl

# Start new version
systemctl start sentinel
```

**New features to consider:**

- [Supply Chain Security](/docs/operations/supply-chain/) -- verify binary and container authenticity
- DNS-01 ACME challenges for wildcard certificates
- Agent Protocol v2 connection pooling

### From 25.12 to 26.01

No breaking changes. Direct upgrade supported.

**New features to consider:**

- [Traffic Mirroring](/configuration/routes/#shadow) for canary deployments
- [Schema Validation](/configuration/routes/#schema-validation) for API routes

---

## Compatibility Matrix

### Agent Compatibility

| Sentinel Release | Protocol | Compatible Agent Versions |
|------------------|----------|---------------------------|
| 26.02 | `0.2.0` | Agents built with protocol `0.2.x` |
| 26.01 | `0.2.0` | Agents built with protocol `0.2.x` |
| 25.12 | `0.1.0` | Agents built with protocol `0.1.x` |

### Rust Toolchain

| Sentinel Release | Minimum Rust Version | Recommended |
|------------------|----------------------|-------------|
| 26.02 | 1.85.0 | 1.85.0+ |
| 26.01 | 1.75.0 | 1.83.0+ |
| 25.12 | 1.70.0 | 1.75.0+ |

---

## Release Schedule

Sentinel follows a monthly release cadence:

- **Feature releases:** First week of each month (e.g., `26.02_0`)
- **Patch releases:** As needed for security or critical bugs (e.g., `26.01_1`, `26.01_2`)

### Community Support

| Release | Status | Security Fixes Until |
|---------|--------|----------------------|
| 26.02 | Current | Active development |
| 26.01 | Previous | 26.04 (3 months) |
| 25.12 | EOL | No support |

Community releases receive security patches for **3 months** after the next release series ships.

### Enterprise LTS

Enterprise customers receive long-term support branches designated by their CalVer series:

| LTS Branch | Based On | Security Fixes Until | Config Stability |
|------------|----------|----------------------|------------------|
| 26.01 LTS | `26.01_0` | January 2027 (12 months) | Guaranteed |

LTS branches receive:
- **Security backports** for 12 months from the initial release
- **Configuration compatibility** — no breaking config changes within the LTS window
- **Patch releases** on the same CalVer series (e.g., `26.01_1`, `26.01_2`, ...)
- **Early security advisories** before public disclosure

LTS is available through the [Enterprise Builds](/support/) offering. See [Supply Chain Security](/docs/operations/supply-chain/) for verification procedures.

---

## See Also

- [Release Process](/development/releases/) — How releases are made
- [GitHub Releases](https://github.com/raskell-io/sentinel/releases) — Download binaries
- [crates.io](https://crates.io/crates/sentinel) — Rust crate registry

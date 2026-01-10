+++
title = "Changelog"
weight = 1
+++

All notable changes to Sentinel and official agents.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Crate versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> **Note:** Sentinel uses dual versioning. See [Versioning](../versioning/) for how crate versions (0.1.0) map to release versions (26.01).

## Sentinel Proxy

### [Unreleased]

#### Added
- **Traffic Mirroring / Shadow Traffic** (v0.3.0)
  - Fire-and-forget async request duplication to shadow upstreams
  - Percentage-based sampling (0-100%) for controlled traffic mirroring
  - Header-based filtering for targeted shadow requests
  - Optional request body buffering with configurable size limits
  - Independent failure domain (shadow failures don't affect clients)
  - Zero latency impact on primary request path
  - Separate connection pools for shadow upstreams
  - Prometheus metrics: `shadow_requests_total`, `shadow_errors_total`, `shadow_latency_seconds`
  - Complete documentation and examples for canary deployments
- **API Schema Validation**
  - JSON Schema validation for API routes (requests and responses)
  - OpenAPI 3.0 and Swagger 2.0 specification support
  - Inline JSON Schema definitions in KDL configuration
  - Strict mode to reject additional properties
  - Structured validation error responses with field-level details
  - Support for complex nested schemas and arrays
  - JSON Schema Draft 7 features (types, formats, patterns, etc.)
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
- Improved error handling in agent connection management

---

### [1.0.0] - 2024-12-15

Initial stable release.

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

### [0.9.0] - 2024-11-01

Release candidate.

#### Added
- gRPC transport for remote agents
- WebSocket proxying support
- Connection draining on shutdown

#### Changed
- Improved configuration error messages
- Optimized header parsing performance

#### Fixed
- Memory leak in long-lived connections
- Race condition in health check scheduler

---

### [0.8.0] - 2024-10-01

#### Added
- Active health checks for upstreams
- Circuit breaker pattern
- Request body buffering control

#### Changed
- Default timeout increased to 60 seconds
- Improved TLS certificate loading

---

## Official Agents

### sentinel-agent-waf

#### [1.0.0] - 2024-12-15

Initial release.

- Native Rust regex-based WAF
- SQL injection detection
- XSS detection (script tags, event handlers, javascript: URIs)
- Path traversal detection (plain and URL-encoded)
- Command injection detection
- Scanner/bot detection via User-Agent
- Request and response body inspection
- Configurable paranoia levels (1-4)
- Path exclusions
- Block mode and detect-only mode

---

### sentinel-agent-modsec

#### [1.0.0] - 2024-12-15

Initial release.

- libmodsecurity 3.x integration
- Full OWASP Core Rule Set (CRS) support
- Custom SecRule support
- Anomaly scoring mode
- Configurable paranoia levels
- Rule exclusions by ID or tag
- Request and response body inspection

---

### sentinel-agent-auth

#### [1.0.0] - 2024-12-15

Initial release.

- JWT validation (HS256, RS256, ES256)
- API key authentication
- Basic authentication
- Path-based authentication requirements
- Custom claim validation
- Token refresh handling
- Multiple issuer support

---

### sentinel-agent-ratelimit

#### [1.0.0] - 2024-12-15

Initial release.

- Per-client rate limiting (by IP, header, or JWT claim)
- Sliding window algorithm
- Configurable burst allowance
- Multiple rate limit tiers
- Response headers (RateLimit-*, Retry-After)
- Path-based limit overrides

---

### sentinel-agent-js

#### [1.0.0] - 2024-12-15

Initial release.

- Custom JavaScript policy scripts
- Rhai JavaScript runtime
- Request inspection API
- Response header manipulation
- Decision types: allow, block, redirect
- Error handling with fail-open mode
- Script hot reloading

---

### sentinel-agent-ai-gateway

#### [1.0.0] - 2024-12-20

Initial release.

- OpenAI and Anthropic API support
- Prompt injection detection
- PII detection (email, SSN, phone, credit card, IP)
- Jailbreak attempt detection
- Model allowlist validation
- Token limits and cost estimation
- Per-client rate limiting
- JSON schema validation (optional)

---

### sentinel-agent-websocket-inspector

#### [1.0.0] - 2024-12-28

Initial release.

- WebSocket frame inspection
- XSS detection in text frames
- SQL injection detection
- Command injection detection
- Custom regex pattern matching
- JSON schema validation
- Per-connection rate limiting
- Message size limits
- Fragmented message handling
- Block mode and detect-only mode

---

## Protocol

### sentinel-agent-protocol

#### [0.1.0] - 2024-12-15

Initial release.

- Agent protocol definition
- Unix socket transport
- gRPC transport
- Request/response events
- WebSocket frame events
- Agent decisions (Allow, Block, Redirect, etc.)
- WebSocket decisions (Allow, Drop, Close)
- AgentClient and AgentServer helpers for testing

---

## Upgrading

### From 0.9.x to 1.0.0

No breaking changes. Direct upgrade supported.

```bash
# Stop current version
systemctl stop sentinel

# Install new version
curl -Lo /usr/local/bin/sentinel \
    https://github.com/raskell-io/sentinel/releases/download/v1.0.0/sentinel
chmod +x /usr/local/bin/sentinel

# Validate configuration
sentinel validate -c /etc/sentinel/sentinel.kdl

# Start new version
systemctl start sentinel
```

### From 0.8.x to 0.9.x

Configuration changes required:

1. **Health check syntax changed**:
   ```kdl
   // Old (0.8.x)
   upstream "backend" {
       health-check "/health"
   }

   // New (0.9.x)
   upstream "backend" {
       health-check {
           path "/health"
           interval-secs 10
       }
   }
   ```

2. **Agent socket paths**:
   - Default path changed from `/tmp/sentinel-*.sock` to `/var/run/sentinel/*.sock`

---

## Links

- [GitHub Releases](https://github.com/raskell-io/sentinel/releases)
- [Migration Guides](../migration/)
- [Release Process](/development/releases/)

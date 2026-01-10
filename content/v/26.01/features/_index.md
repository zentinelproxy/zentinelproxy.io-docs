+++
title = "Features"
weight = 15
sort_by = "weight"
template = "section.html"
description = "Complete feature list for Sentinel reverse proxy"
+++

Sentinel is a next-generation reverse proxy built on [Cloudflare's Pingora](https://github.com/cloudflare/pingora) framework. This page provides a comprehensive overview of all features available in the current version.

<div class="feature-version-notice">

**Version:** This feature list reflects Sentinel v26.01. Features may vary between versions.

</div>

---

## Core Architecture

### Built on Pingora
<small class="source-ref">[`crates/proxy/src/main.rs`](https://github.com/raskell-io/sentinel/blob/main/crates/proxy/src/main.rs)</small>

- Battle-tested foundation from Cloudflare
- Async Rust with Tokio runtime
- Memory-safe architecture with zero-copy operations
- Work-stealing thread pool for optimal CPU utilization

### Performance Optimizations
<small class="source-ref">[`crates/proxy/src/memory_cache.rs`](https://github.com/raskell-io/sentinel/blob/main/crates/proxy/src/memory_cache.rs)</small>

- **jemalloc allocator** for improved memory allocation
- **Lock-free data structures** (DashMap) for concurrent access
- **Connection pooling** with configurable keepalive (default: 256 connections)
- **Memory-mapped file serving** for large files (>10MB)
- **Route match caching** with atomic operations

---

## Configuration

### Multiple Formats
<small class="source-ref">[`crates/config/src/lib.rs`](https://github.com/raskell-io/sentinel/blob/main/crates/config/src/lib.rs)</small>

- **KDL** — Human-friendly primary format
- **JSON** — Machine-readable alternative
- **TOML** — Familiar to Rust developers

### Hot Reload
<small class="source-ref">[`crates/proxy/src/reload/`](https://github.com/raskell-io/sentinel/tree/main/crates/proxy/src/reload)</small>

- SIGHUP signal triggers reload
- File watcher for automatic reload
- Atomic configuration swap
- Full validation before applying
- Rollback on error
- Zero request drops during reload

### Validation & Linting
<small class="source-ref">[`crates/proxy/src/main.rs`](https://github.com/raskell-io/sentinel/blob/main/crates/proxy/src/main.rs)</small>

- `sentinel test` — Syntax validation
- `sentinel validate` — Full validation with connectivity checks
- `sentinel lint` — Best practice recommendations
- Schema versioning (current: 1.0)
- Network connectivity checks (optional)
- Certificate validation
- Agent endpoint reachability checks

### Environment Variables

- `SENTINEL_CONFIG` for configuration path
- Variable substitution in config files
- Embedded default configuration fallback

---

## Routing

### Path Matching
<small class="source-ref">[`crates/proxy/src/routing.rs`](https://github.com/raskell-io/sentinel/blob/main/crates/proxy/src/routing.rs)</small>

- **Prefix matching** — `/api/` matches `/api/users`
- **Exact matching** — `/health` matches only `/health`
- **Regex matching** — Full regular expression support
- **Path variables** — Extract dynamic segments

### Host Matching

- Exact host matching
- Wildcard subdomains (`*.example.com`)
- Multiple hosts per route

### Advanced Matching

- **Header matching** — Presence and value checks
- **Method filtering** — GET, POST, PUT, DELETE, etc.
- **Query parameter matching**
- **Priority-based evaluation** — Highest priority wins
- **Default route fallback**

### Scope-Aware Routing
<small class="source-ref">[`crates/proxy/src/scoped_routing.rs`](https://github.com/raskell-io/sentinel/blob/main/crates/proxy/src/scoped_routing.rs)</small>

- Hierarchical routing (global → namespace → service)
- Visibility rules between scopes
- Qualified ID resolution

---

## Load Balancing

### Algorithms
<small class="source-ref">[`crates/proxy/src/upstream/`](https://github.com/raskell-io/sentinel/tree/main/crates/proxy/src/upstream)</small>

- **Round Robin** — Default, simple rotation
- **Power of Two Choices (P2C)** — Random selection with load comparison
- **Consistent Hash** — Session persistence via request attributes
- **Least Tokens Queued** — Optimized for inference/LLM workloads
- **Adaptive** — Based on response times
- **Weighted** — Per-target weight configuration

### Health Checking
<small class="source-ref">[`crates/proxy/src/health.rs`](https://github.com/raskell-io/sentinel/blob/main/crates/proxy/src/health.rs)</small>

- **Active checks** — HTTP, TCP, gRPC probes
- **Passive checks** — Circuit breaker based
- Configurable check intervals
- Consecutive success/failure thresholds
- Response time averaging
- Automatic target ejection

### Connection Management

- Configurable pool size per upstream
- Keep-alive connection reuse
- HTTP/2 stream multiplexing (default: 100 streams)
- H2 ping intervals for connection health

### Timeouts

- Connection timeout
- Read/write timeouts
- Request header timeout
- Request body timeout
- Per-upstream configuration

---

## Service Discovery

### Backend Sources
<small class="source-ref">[`crates/proxy/src/discovery.rs`](https://github.com/raskell-io/sentinel/blob/main/crates/proxy/src/discovery.rs)</small>

- **Static** — Fixed list of backends (default)
- **DNS** — A/AAAA record resolution with refresh
- **DNS SRV** — Service records with port discovery
- **Consul** — HashiCorp Consul catalog integration
- **Kubernetes** — Native endpoints discovery
- **File-based** — Watch configuration files for changes

---

## Service Types

### Web Applications

- HTML error pages
- Session handling support
- SPA routing with fallback

### REST APIs

- JSON error responses
- JSON Schema validation
- OpenAPI specification support
- Request/response validation

### Static Files

- Direct file serving without upstream
- Automatic MIME type detection
- Configurable caching headers

### Inference / LLM
<small class="source-ref">[`crates/proxy/src/inference/`](https://github.com/raskell-io/sentinel/tree/main/crates/proxy/src/inference)</small>

- **Token-based rate limiting** — Limit by tokens per minute, not just requests
- **Multi-provider support** — OpenAI, Anthropic, and generic API adapters
- **Model-aware load balancing** — Route based on queue depth and throughput
- **Token budget tracking** — Per-tenant cumulative usage with period-based limits (hourly/daily/monthly)
- **Budget alerts** — Configurable thresholds (80%, 90%, 95%) with logging
- **Budget enforcement** — Block requests when budget exhausted, with Retry-After headers
- **Cost attribution** — Per-model pricing with input/output token differentiation
- **Cost metrics** — Track spending by model, route, and tenant via Prometheus

### Built-in Handlers
<small class="source-ref">[`crates/proxy/src/builtin_handlers.rs`](https://github.com/raskell-io/sentinel/blob/main/crates/proxy/src/builtin_handlers.rs)</small>

- `/status` — Service status
- `/health` — Health check endpoint
- `/metrics` — Prometheus metrics
- `/upstreams` — Upstream health status
- `/cache-purge` — Cache management

---

## Static File Serving

### Core Features
<small class="source-ref">[`crates/proxy/src/static_files/mod.rs`](https://github.com/raskell-io/sentinel/blob/main/crates/proxy/src/static_files/mod.rs)</small>

- High-performance file serving
- Memory-mapped serving for large files (>10MB threshold)
- In-memory caching for small files (<1MB)
- Directory listing (configurable)
- Index file support
- Configurable root directory

### Range Requests

- HTTP 206 Partial Content support
- Resumable downloads
- Video seeking support

### Compression

- On-the-fly gzip compression
- On-the-fly Brotli compression
- Content negotiation (Accept-Encoding)
- Pre-computed compression variants in cache

### SPA Support

- Fallback routing for client-side routing
- Configurable fallback path

---

## Caching

### HTTP Response Cache
<small class="source-ref">[`crates/proxy/src/cache.rs`](https://github.com/raskell-io/sentinel/blob/main/crates/proxy/src/cache.rs)</small>

- Pingora-based cache infrastructure
- Per-route cache configuration
- Cache-Control header parsing
- TTL calculation from upstream headers
- In-memory storage (default)
- LRU eviction strategy
- Configurable size (default: 100MB)
- Thundering herd prevention (cache locks)

### Memory Cache
<small class="source-ref">[`crates/proxy/src/memory_cache.rs`](https://github.com/raskell-io/sentinel/blob/main/crates/proxy/src/memory_cache.rs)</small>

- S3-FIFO + TinyLFU eviction algorithm
- Route matching result caching
- Configuration fragment caching
- Compiled regex pattern caching
- Configurable max items (default: 10,000)
- Hit/miss rate tracking

---

## Protocol Support

### HTTP Versions

- **HTTP/1.1** — Full support
- **HTTP/2** — Over TLS, configurable max streams
- **HTTP/3 / QUIC** — Infrastructure ready (optional feature)

### WebSocket
<small class="source-ref">[`crates/proxy/src/websocket/`](https://github.com/raskell-io/sentinel/tree/main/crates/proxy/src/websocket)</small>

- RFC 6455 compliant
- HTTP 101 Upgrade handling
- Frame parsing and encoding
- Frame masking/unmasking
- Configurable max frame size
- **Frame inspection** — Individual frames sent to agents for security analysis
- Per-route WebSocket enablement

---

## Security

### TLS / SSL
<small class="source-ref">[`crates/proxy/src/tls.rs`](https://github.com/raskell-io/sentinel/blob/main/crates/proxy/src/tls.rs)</small>

- SNI-based certificate selection
- Multiple certificates per listener
- Wildcard certificate support (`*.api.example.com`)
- Default certificate fallback
- Certificate hot-reload on SIGHUP
- OCSP stapling
- Modern cipher suites

### Mutual TLS (mTLS)

- Client certificate verification
- Custom CA certificate loading
- Per-listener client auth configuration

### Rate Limiting
<small class="source-ref">[`crates/proxy/src/rate_limit.rs`](https://github.com/raskell-io/sentinel/blob/main/crates/proxy/src/rate_limit.rs)</small>

- **Local rate limiting** — Per-instance, lock-free
- **Distributed rate limiting** — Redis-based (optional feature)
- **Memcached rate limiting** — Alternative distributed backend
- Token bucket algorithm
- Configurable burst size
- Multiple key types: client IP, API key, user, custom
- Actions: Reject, Delay, Challenge
- Per-route policies
- Scope-aware limits (per namespace/service)

### GeoIP Filtering
<small class="source-ref">[`crates/proxy/src/geo_filter.rs`](https://github.com/raskell-io/sentinel/blob/main/crates/proxy/src/geo_filter.rs)</small>

- MaxMind GeoLite2/GeoIP2 support (.mmdb)
- IP2Location support (.bin)
- Blocklist and allowlist modes
- Log-only mode for monitoring
- IP→Country caching with TTL
- Fail-open/fail-closed configuration
- X-GeoIP-Country header injection
- Database auto-reload on file change

### Decompression Protection
<small class="source-ref">[`crates/proxy/src/decompression.rs`](https://github.com/raskell-io/sentinel/blob/main/crates/proxy/src/decompression.rs)</small>

- Zip bomb prevention via ratio limiting
- Supported: gzip, deflate, brotli
- Configurable max compression ratio (default: 100x)
- Configurable max output size (default: 10MB)
- Incremental checking during decompression

### Request Validation
<small class="source-ref">[`crates/proxy/src/validation.rs`](https://github.com/raskell-io/sentinel/blob/main/crates/proxy/src/validation.rs)</small>

- JSON Schema validation for API routes
- OpenAPI specification support
- Request and response validation
- Schema compilation and caching

---

## Circuit Breakers

### Per-Upstream Breakers
<small class="source-ref">[`crates/common/src/circuit_breaker.rs`](https://github.com/raskell-io/sentinel/blob/main/crates/common/src/circuit_breaker.rs)</small>

- Configurable failure threshold
- Configurable success threshold
- Timeout before half-open state
- Half-open max requests
- State tracking: Closed → Open → Half-Open → Closed

### Scope-Aware Breakers
<small class="source-ref">[`crates/proxy/src/scoped_circuit_breaker.rs`](https://github.com/raskell-io/sentinel/blob/main/crates/proxy/src/scoped_circuit_breaker.rs)</small>

- Per-namespace circuit breakers
- Per-service circuit breakers
- Independent failure tracking
- Metrics per breaker

---

## Observability

### Access Logging
<small class="source-ref">[`crates/proxy/src/logging.rs`](https://github.com/raskell-io/sentinel/blob/main/crates/proxy/src/logging.rs)</small>

- **JSON format** — Structured, machine-readable
- **Combined Log Format** — Apache-compatible
- Trace ID correlation
- Fields: timestamp, method, path, status, latency, client IP, user-agent, upstream, instance ID

### Metrics
<small class="source-ref">[`crates/config/src/observability.rs`](https://github.com/raskell-io/sentinel/blob/main/crates/config/src/observability.rs)</small>

- Prometheus-compatible endpoint
- Configurable address and path
- Per-route latency histograms
- Status code distributions
- Upstream health metrics
- Retry metrics
- Agent latency metrics
- Circuit breaker state metrics
- Cache hit/miss rates
- Optional high-cardinality metrics

### Distributed Tracing
<small class="source-ref">[`crates/proxy/src/otel.rs`](https://github.com/raskell-io/sentinel/blob/main/crates/proxy/src/otel.rs)</small>

- **OpenTelemetry (OTLP)** integration
- W3C Trace Context propagation (traceparent/tracestate)
- Export to Jaeger, Tempo, or any OTLP backend
- Configurable sampling rates (default: 10%)
- Request lifecycle spans
- Semantic conventions compliance

### Request Correlation

- Trace ID generation (TinyFlake or UUID)
- Request ID propagation
- X-Request-Id header injection
- Cross-service correlation

---

## Traffic Management

### Traffic Mirroring / Shadowing
<small class="source-ref">[`crates/proxy/src/shadow.rs`](https://github.com/raskell-io/sentinel/blob/main/crates/proxy/src/shadow.rs)</small>

- Fire-and-forget request duplication
- Sampling-based mirroring (0-100%)
- Header-based selective mirroring
- Optional request body buffering
- Async execution (non-blocking to primary)
- Per-route shadow configuration
- Comprehensive shadow traffic metrics

### Retry Policies

- Configurable max retries
- Backoff strategies
- Idempotency key support
- Per-route retry configuration

### Header Manipulation
<small class="source-ref">[`crates/config/src/filters.rs`](https://github.com/raskell-io/sentinel/blob/main/crates/config/src/filters.rs)</small>

- Request header add/modify/remove
- Response header add/modify/remove
- Custom header injection (X-Request-Id, X-Trace-Id)
- Header-based routing conditions

---

## External Agents

### Agent Protocol
<small class="source-ref">[`crates/agent-protocol/src/`](https://github.com/raskell-io/sentinel/tree/main/crates/agent-protocol/src)</small>

- SPOE-inspired external agent system
- **Unix Domain Sockets** — Default transport
- **gRPC** — Alternative transport
- Protocol Buffers with auto-generated bindings

### Agent Events

- `on_request_headers` — Request phase inspection
- `on_request_body_chunk` — Streaming request bodies
- `on_response_headers` — Response phase inspection
- `on_response_body_chunk` — Streaming response bodies
- `on_log` — Final audit logging
- WebSocket frame inspection events

### Agent Decisions

- **ALLOW** — Pass request through
- **BLOCK** — Return custom status code
- **REDIRECT** — Send redirect response
- **CHALLENGE** — Authentication challenge

### Agent Mutations

- Add/modify/remove request headers
- Add/modify/remove response headers
- Set routing metadata
- Audit tags and metadata

### Per-Agent Configuration
<small class="source-ref">[`crates/proxy/src/agents/`](https://github.com/raskell-io/sentinel/tree/main/crates/proxy/src/agents)</small>

- Individual circuit breakers
- Concurrency limits (queue isolation)
- Configurable timeouts
- Failure mode: fail-open or fail-closed
- Body streaming modes: Buffer, Stream, Hybrid
- Max body size limits

### Reference Agents

- **Echo agent** — Request debugging
- **Denylist agent** — IP blocking

---

## Multi-Tenancy

### Namespace Support
<small class="source-ref">[`crates/config/src/namespace.rs`](https://github.com/raskell-io/sentinel/blob/main/crates/config/src/namespace.rs)</small>

- Hierarchical organization (global → namespace → service)
- Resource scoping and visibility
- Per-namespace rate limits
- Per-namespace circuit breakers
- Per-namespace policies
- Resource export for inter-namespace access

---

## Error Handling

### Custom Error Pages
<small class="source-ref">[`crates/proxy/src/errors/mod.rs`](https://github.com/raskell-io/sentinel/blob/main/crates/proxy/src/errors/mod.rs)</small>

- Per-service-type error formats
- Multiple formats: HTML, JSON, Text, XML
- Per-status-code custom pages
- Template-based with variable substitution
- Request ID injection
- Custom headers in error responses

---

## Resource Limits

### Global Limits
<small class="source-ref">[`crates/common/src/limits.rs`](https://github.com/raskell-io/sentinel/blob/main/crates/common/src/limits.rs)</small>

- Max header size
- Max header count
- Max request body size
- Max decompression ratio
- Max connections per upstream
- Max in-flight requests per worker
- Connection limits per client

### Per-Route Limits

- Body size limits
- Timeout overrides
- Rate limit policies

---

## Operational Features

### Graceful Shutdown

- Connection draining on SIGTERM/SIGINT
- Configurable timeout (default: 30s)
- Request completion before shutdown
- Agent queue draining

### CLI Commands

- `sentinel run` — Start the proxy
- `sentinel test` — Validate configuration syntax
- `sentinel validate` — Full validation with checks
- `sentinel lint` — Best practice recommendations

### Feature Flags (Compile-time)

- `distributed-rate-limit` — Redis-based rate limiting
- `distributed-rate-limit-memcached` — Memcached rate limiting
- `kubernetes` — Kubernetes service discovery
- `validation` — Extended configuration validation

---

## Filters & Pipelines

### Filter System
<small class="source-ref">[`crates/config/src/filters.rs`](https://github.com/raskell-io/sentinel/blob/main/crates/config/src/filters.rs)</small>

- Named filter instances (reusable)
- Execution phases: Request, Response, Both
- Chain execution order
- Per-filter failure modes

### Built-in Filters

- Rate limit filters
- Header manipulation filters
- Agent filters
- Compression filters

---

<div class="feature-footer">

## Feature Requests

Have a feature idea? We'd love to hear it!

- [Start a Discussion](https://github.com/raskell-io/sentinel/discussions)
- [Open an Issue](https://github.com/raskell-io/sentinel/issues)

</div>

+++
title = "Pingora Foundation"
weight = 4
+++

Sentinel is built on [Cloudflare's Pingora](https://github.com/cloudflare/pingora), a battle-tested HTTP proxy framework written in Rust. This page explains what Pingora provides and how Sentinel extends it.

## What is Pingora?

Pingora is an open-source proxy framework that Cloudflare uses to handle **over 1 trillion requests per day**. It provides:

- **High-performance async HTTP handling** using Tokio
- **Connection pooling** to upstream servers
- **TLS termination** with modern cipher suites
- **HTTP/1.1 and HTTP/2** support
- **Zero-copy buffer management** for efficiency
- **Graceful shutdown and upgrades**

Sentinel uses Pingora as its foundation, adding routing, load balancing, agent coordination, and configuration management on top.

## Why Pingora?

| Requirement | Pingora Solution |
|-------------|------------------|
| **Performance** | Handles millions of requests/sec with low latency |
| **Safety** | Written in Rust with memory safety guarantees |
| **Production-proven** | Powers Cloudflare's global edge network |
| **Extensibility** | Clean trait-based architecture for customization |
| **Operational** | Built-in graceful restart and upgrade support |

### Compared to Alternatives

| Framework | Language | Trade-offs |
|-----------|----------|------------|
| **Pingora** | Rust | Best performance + safety, smaller ecosystem |
| **Envoy** | C++ | Feature-rich but complex, memory safety concerns |
| **HAProxy** | C | Mature but harder to extend, no memory safety |
| **Nginx** | C | Ubiquitous but module development is challenging |

## Core Pingora Concepts

### Server and Services

Pingora applications start with a `Server` that manages one or more services:

```rust
// Create Pingora server with options
let mut server = Server::new(Some(pingora_opt))?;
server.bootstrap();

// Create HTTP proxy service
let proxy_service = http_proxy_service(&server.configuration, proxy);

// Add listeners
proxy_service.add_tcp("0.0.0.0:8080");

// Register service and run
server.add_service(proxy_service);
server.run_forever();
```

The server handles:
- Worker process management
- Signal handling (SIGHUP, SIGTERM)
- Graceful restarts and upgrades
- Daemonization

### Session

A `Session` represents a single HTTP request/response cycle. It provides access to:

```rust
// Request information
session.req_header()        // HTTP request headers
session.req_header_mut()    // Mutable access for modifications
session.client_addr()       // Client IP address

// Response information
session.response_written()  // Response after sending

// Body handling
session.read_request_body() // Read request body chunks
session.write_response_body() // Write response body
```

### HttpPeer

An `HttpPeer` represents an upstream server connection target:

```rust
let peer = HttpPeer::new(
    ("backend.example.com", 8080),  // Address
    false,                           // TLS enabled
    "backend.example.com".into()     // SNI hostname
);

// Connection options
peer.options.connection_timeout = Some(Duration::from_secs(5));
peer.options.read_timeout = Some(Duration::from_secs(30));
```

Pingora maintains connection pools to peers for efficiency.

## The ProxyHttp Trait

The `ProxyHttp` trait is the heart of Pingora's extensibility. Sentinel implements this trait to inject custom logic at each stage of request processing:

```rust
#[async_trait]
impl ProxyHttp for SentinelProxy {
    type CTX = RequestContext;

    // Create per-request context
    fn new_ctx(&self) -> Self::CTX {
        RequestContext::new()
    }

    // Select upstream server
    async fn upstream_peer(
        &self,
        session: &mut Session,
        ctx: &mut Self::CTX,
    ) -> Result<Box<HttpPeer>, Box<Error>>;

    // Process request before forwarding
    async fn request_filter(
        &self,
        session: &mut Session,
        ctx: &mut Self::CTX,
    ) -> Result<bool, Box<Error>>;

    // Process response before returning
    async fn response_filter(
        &self,
        session: &mut Session,
        upstream_response: &mut ResponseHeader,
        ctx: &mut Self::CTX,
    ) -> Result<(), Box<Error>>;

    // Final logging after request completes
    async fn logging(
        &self,
        session: &mut Session,
        error: Option<&Error>,
        ctx: &mut Self::CTX,
    );
}
```

### Request Context

Each request gets its own context that persists throughout the lifecycle:

```rust
pub struct RequestContext {
    pub trace_id: String,
    pub start_time: Instant,
    pub route_id: Option<String>,
    pub upstream: Option<String>,
    pub client_ip: String,
    pub method: String,
    pub path: String,
    pub upstream_attempts: u32,
    // ... more fields
}
```

## How Sentinel Uses Pingora

### 1. Route Matching (`upstream_peer`)

When a request arrives, Sentinel matches it to a route and selects an upstream:

```
Request arrives
     │
     ▼
┌────────────────────┐
│ Parse request info │
│ (method, path,     │
│  host, headers)    │
└────────┬───────────┘
         │
         ▼
┌────────────────────┐
│ Match against      │
│ compiled routes    │
└────────┬───────────┘
         │
         ▼
┌────────────────────┐
│ Select peer from   │
│ upstream pool      │
└────────┬───────────┘
         │
         ▼
    Return HttpPeer
```

### 2. Request Processing (`request_filter`)

Before forwarding, Sentinel applies filters and calls agents:

```rust
async fn request_filter(&self, session: &mut Session, ctx: &mut Self::CTX)
    -> Result<bool, Box<Error>>
{
    // Handle static files and builtins
    if route.service_type == ServiceType::Static {
        return self.handle_static_route(session, ctx).await;
    }

    // Enforce limits
    if headers.len() > config.limits.max_header_count {
        return Err(Error::explain("Too many headers"));
    }

    // Add tracing headers
    req_header.insert_header("X-Correlation-Id", &ctx.trace_id)?;
    req_header.insert_header("X-Forwarded-By", "Sentinel")?;

    // Call external agents
    self.process_agents(session, ctx).await?;

    Ok(false)  // Continue to upstream
}
```

Returning `Ok(true)` short-circuits processing (response already sent).
Returning `Ok(false)` continues to the upstream.

### 3. Response Processing (`response_filter`)

After receiving the upstream response:

```rust
async fn response_filter(
    &self,
    session: &mut Session,
    upstream_response: &mut ResponseHeader,
    ctx: &mut Self::CTX,
) -> Result<(), Box<Error>> {
    // Add security headers
    upstream_response.insert_header("X-Content-Type-Options", "nosniff")?;
    upstream_response.insert_header("X-Frame-Options", "DENY")?;

    // Add correlation ID
    upstream_response.insert_header("X-Correlation-Id", &ctx.trace_id)?;

    // Record metrics
    self.metrics.record_request(
        ctx.route_id.as_deref().unwrap_or("unknown"),
        &ctx.method,
        upstream_response.status.as_u16(),
        ctx.elapsed(),
    );

    // Update health status
    self.passive_health.record_outcome(&upstream, success).await;

    Ok(())
}
```

### 4. Logging (`logging`)

After the response is sent to the client:

```rust
async fn logging(&self, session: &mut Session, error: Option<&Error>, ctx: &mut Self::CTX) {
    // Decrement active request counter
    self.reload_coordinator.dec_requests();

    // Write structured access log
    let entry = AccessLogEntry {
        timestamp: Utc::now().to_rfc3339(),
        trace_id: ctx.trace_id.clone(),
        method: ctx.method.clone(),
        path: ctx.path.clone(),
        status: session.response_written().map(|r| r.status.as_u16()),
        duration_ms: ctx.elapsed().as_millis(),
        // ...
    };

    self.log_manager.log_access(&entry);
}
```

## Connection Pooling

Pingora automatically pools connections to upstream servers:

```
┌─────────────────────────────────────────────────────────┐
│                   Sentinel Proxy                         │
│  ┌───────────────────────────────────────────────────┐  │
│  │              Connection Pool Manager               │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌───────────┐ │  │
│  │  │ backend-1   │  │ backend-2   │  │ backend-3 │ │  │
│  │  │ ┌─┐┌─┐┌─┐   │  │ ┌─┐┌─┐┌─┐   │  │ ┌─┐┌─┐    │ │  │
│  │  │ │C││C││C│   │  │ │C││C││C│   │  │ │C││C│    │ │  │
│  │  │ └─┘└─┘└─┘   │  │ └─┘└─┘└─┘   │  │ └─┘└─┘    │ │  │
│  │  └─────────────┘  └─────────────┘  └───────────┘ │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
           │                 │                │
           ▼                 ▼                ▼
      ┌─────────┐       ┌─────────┐       ┌─────────┐
      │ Backend │       │ Backend │       │ Backend │
      │    1    │       │    2    │       │    3    │
      └─────────┘       └─────────┘       └─────────┘
```

Benefits:
- **Reduced latency** - Reuses existing TCP connections
- **Lower resource usage** - Fewer connections to manage
- **Connection limits** - Prevents overwhelming backends

## Graceful Operations

### Hot Restart

Pingora supports zero-downtime restarts:

```
┌──────────────┐     SIGUSR2      ┌──────────────┐
│  Old Worker  │ ───────────────▶ │  New Worker  │
│  (draining)  │                  │  (starting)  │
└──────┬───────┘                  └──────┬───────┘
       │                                  │
       │  Existing connections            │  New connections
       │  finish gracefully               │  accepted
       ▼                                  ▼
   [exit when done]              [fully operational]
```

### Graceful Shutdown

On SIGTERM/SIGINT:

1. Stop accepting new connections
2. Wait for in-flight requests (with timeout)
3. Close connection pools
4. Exit cleanly

Sentinel extends this with reload coordination:

```rust
pub struct GracefulReloadCoordinator {
    active_requests: AtomicUsize,
    max_drain_time: Duration,
}

impl GracefulReloadCoordinator {
    pub fn inc_requests(&self) { /* ... */ }
    pub fn dec_requests(&self) { /* ... */ }
    pub async fn wait_for_drain(&self) { /* ... */ }
}
```

## Error Handling

Pingora uses a typed error system:

```rust
pub enum ErrorType {
    InvalidHTTPHeader,
    ConnectTimedout,
    ConnectRefused,
    ConnectNoRoute,
    ReadError,
    WriteError,
    // ... many more
}
```

Sentinel maps these to appropriate HTTP responses:

| Error Type | HTTP Status | Response |
|------------|-------------|----------|
| `ConnectTimedout` | 504 | Gateway Timeout |
| `ConnectRefused` | 502 | Bad Gateway |
| `ReadError` | 502 | Bad Gateway |
| `InvalidHTTPHeader` | 400 | Bad Request |

## Performance Characteristics

Pingora's architecture enables:

| Metric | Typical Value |
|--------|---------------|
| Requests/sec (per core) | 100,000+ |
| P99 latency overhead | < 1ms |
| Memory per connection | ~10KB |
| Connection reuse rate | > 95% |

## Dependencies

Sentinel uses these Pingora crates:

```toml
[dependencies]
pingora = { version = "0.6", features = ["proxy", "lb"] }
pingora-core = "0.6"
pingora-http = "0.6"
pingora-proxy = "0.6"
pingora-load-balancing = "0.6"
pingora-timeout = "0.6"
```

## Next Steps

- [Architecture Overview](../architecture/) - High-level design
- [Component Design](../components/) - Sentinel's crate structure
- [Request Flow](../request-flow/) - Detailed request lifecycle

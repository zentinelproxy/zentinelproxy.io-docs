+++
title = "Comparison with Alternatives"
weight = 6
+++

How Sentinel compares to other popular reverse proxies and load balancers.

## Overview

Sentinel occupies a unique position in the reverse proxy landscape. Rather than competing directly with established proxies on feature breadth, it focuses on security-first design, operational predictability, and an extensible agent architecture.

| Feature | Sentinel | Envoy | HAProxy | Nginx | Traefik | Caddy |
|---------|----------|-------|---------|-------|---------|-------|
| **Language** | Rust | C++ | C | C | Go | Go |
| **Memory Safety** | Yes | No | No | No | Yes | Yes |
| **Configuration** | KDL | YAML/xDS | Config file | Config file | YAML/Labels | Caddyfile/JSON |
| **Hot Reload** | Yes | Yes (xDS) | Yes | Yes (SIGHUP) | Yes (auto) | Yes (API) |
| **Extension Model** | External agents | Filters (C++/Wasm) | Lua/SPOE | Modules/Lua | Plugins (Go) | Modules (Go) |
| **Auto HTTPS** | Planned | No | No | No | Yes | Yes |
| **Primary Use Case** | Security gateway | Service mesh | Load balancing | Web server/proxy | Cloud-native edge | Simple web server |

## Sentinel vs Envoy

### Architecture Philosophy

**Envoy** is designed as a universal data plane for service mesh architectures. It provides extensive protocol support, advanced traffic management, and deep observability through a filter chain architecture.

**Sentinel** is designed as a security-focused edge proxy with an external agent model. Rather than embedding security logic in filters, agents run as isolated processes that can be updated, rate-limited, or disabled independently.

### When to Choose Envoy

- Building a service mesh with Istio, Consul, or similar
- Need extensive protocol support (gRPC, MongoDB, Redis, etc.)
- Require xDS-based dynamic configuration from a control plane
- Want a mature, battle-tested proxy at massive scale

### When to Choose Sentinel

- Need a security gateway with WAF, auth, and rate limiting
- Want isolated security agents that can fail independently
- Prefer explicit configuration over dynamic control planes
- Value memory safety and predictable resource usage
- Building custom security controls with the agent protocol

### Configuration Comparison

**Envoy** (YAML):
```yaml
static_resources:
  listeners:
    - name: listener_0
      address:
        socket_address:
          address: 0.0.0.0
          port_value: 8080
      filter_chains:
        - filters:
            - name: envoy.filters.network.http_connection_manager
              typed_config:
                "@type": type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
                stat_prefix: ingress_http
                route_config:
                  name: local_route
                  virtual_hosts:
                    - name: backend
                      domains: ["*"]
                      routes:
                        - match:
                            prefix: "/"
                          route:
                            cluster: backend_cluster
  clusters:
    - name: backend_cluster
      type: STRICT_DNS
      load_assignment:
        cluster_name: backend_cluster
        endpoints:
          - lb_endpoints:
              - endpoint:
                  address:
                    socket_address:
                      address: backend
                      port_value: 3000
```

**Sentinel** (KDL):
```kdl
listeners {
    listener "http" {
        address "0.0.0.0:8080"
        protocol "http"
    }
}

routes {
    route "default" {
        matches {
            path-prefix "/"
        }
        upstream "backend"
    }
}

upstreams {
    upstream "backend" {
        targets {
            target { address "backend:3000" }
        }
    }
}
```

### Extension Model

**Envoy filters** are compiled into the binary (C++) or loaded as Wasm modules. They run in-process and have access to the full request/response lifecycle.

**Sentinel agents** are external processes that communicate via Unix sockets or gRPC. This provides:
- Process isolation (agent crash doesn't crash proxy)
- Independent deployment and updates
- Language flexibility (any language that speaks the protocol)
- Resource limits per agent

## Sentinel vs HAProxy

### Architecture Philosophy

**HAProxy** is the gold standard for high-performance TCP/HTTP load balancing. It's known for reliability, performance, and a powerful ACL system for traffic management.

**Sentinel** shares HAProxy's focus on reliability but adds a security-first architecture with external agents for policy enforcement.

### When to Choose HAProxy

- Pure load balancing with extreme performance requirements
- Need advanced health checking and connection management
- TCP-level proxying (databases, message queues)
- Established operational expertise with HAProxy

### When to Choose Sentinel

- Security controls are a primary requirement
- Want to implement custom policies without Lua
- Need process isolation for security components
- Prefer Rust's memory safety guarantees

### Configuration Comparison

**HAProxy**:
```
frontend http_front
    bind *:8080
    default_backend http_back

backend http_back
    balance roundrobin
    server backend1 127.0.0.1:3000 check
    server backend2 127.0.0.1:3001 check
```

**Sentinel** (KDL):
```kdl
listeners {
    listener "http" {
        address "0.0.0.0:8080"
        protocol "http"
    }
}

routes {
    route "default" {
        matches { path-prefix "/" }
        upstream "backend"
    }
}

upstreams {
    upstream "backend" {
        targets {
            target { address "127.0.0.1:3000" }
            target { address "127.0.0.1:3001" }
        }
        load-balancing "round_robin"
        health-check {
            path "/health"
            interval-secs 10
        }
    }
}
```

### Extension Comparison

| Aspect | HAProxy | Sentinel |
|--------|---------|----------|
| Scripting | Lua (embedded) | External agents |
| External calls | SPOE protocol | Agent protocol |
| Isolation | In-process | Process-level |
| Hot reload | Requires restart | Independent |

## Sentinel vs Nginx

### Architecture Philosophy

**Nginx** started as a high-performance web server and evolved into a versatile reverse proxy. It excels at serving static content, SSL termination, and basic proxying with an extensive module ecosystem.

**Sentinel** is purpose-built as a security-focused reverse proxy without web server capabilities. It focuses on the proxy use case with deep integration for security agents.

### When to Choose Nginx

- Serving static files alongside proxying
- Need extensive third-party module ecosystem
- Using OpenResty for Lua-based customization
- Established Nginx operational expertise

### When to Choose Sentinel

- Security controls are the primary requirement
- Want isolated, updateable security components
- Prefer explicit configuration over complex conditionals
- Need static file serving with SPA support (`fallback` for try_files equivalent)

### Configuration Comparison

**Nginx**:
```nginx
upstream backend {
    server 127.0.0.1:3000;
    server 127.0.0.1:3001;
}

server {
    listen 8080;

    location / {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

**Sentinel** (KDL):
```kdl
listeners {
    listener "http" {
        address "0.0.0.0:8080"
        protocol "http"
    }
}

routes {
    route "default" {
        matches { path-prefix "/" }
        upstream "backend"
    }
}

upstreams {
    upstream "backend" {
        targets {
            target { address "127.0.0.1:3000" }
            target { address "127.0.0.1:3001" }
        }
    }
}
```

### Security Features

| Feature | Nginx | Sentinel |
|---------|-------|----------|
| WAF | ModSecurity module | Native WAF agent |
| Rate limiting | ngx_http_limit_req | Rate limit agent |
| Authentication | Third-party modules | Auth agent |
| Custom logic | Lua/njs | Any language via agents |

## Sentinel vs Traefik

### Architecture Philosophy

**Traefik** is a modern, cloud-native edge router designed for automatic service discovery and configuration. It excels in dynamic environments like Docker and Kubernetes where services come and go frequently.

**Sentinel** focuses on explicit configuration and security-first design. While it supports service discovery (Consul, Kubernetes), it emphasizes predictable behavior over automatic configuration.

### When to Choose Traefik

- Heavy use of Docker labels for configuration
- Need automatic Let's Encrypt certificate provisioning
- Kubernetes Ingress controller use case
- Prefer dynamic, auto-discovered configuration

### When to Choose Sentinel

- Security agents are a primary requirement
- Want explicit, auditable configuration
- Need process isolation for security components
- Building custom security policies with agents
- Require token-aware rate limiting for LLM/inference workloads

### Configuration Comparison

**Traefik** (Docker labels):
```yaml
services:
  app:
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.app.rule=Host(`app.example.com`)"
      - "traefik.http.services.app.loadbalancer.server.port=3000"
```

**Traefik** (File):
```yaml
http:
  routers:
    app:
      rule: "Host(`app.example.com`)"
      service: app
  services:
    app:
      loadBalancer:
        servers:
          - url: "http://127.0.0.1:3000"
```

**Sentinel** (KDL):
```kdl
listeners {
    listener "http" {
        address "0.0.0.0:8080"
        protocol "http"
    }
}

routes {
    route "app" {
        matches {
            host "app.example.com"
        }
        upstream "app"
    }
}

upstreams {
    upstream "app" {
        targets {
            target { address "127.0.0.1:3000" }
        }
    }
}
```

### Key Differences

| Aspect | Traefik | Sentinel |
|--------|---------|----------|
| Configuration | Dynamic (labels, API) | Explicit (KDL files) |
| Let's Encrypt | Built-in | Planned |
| Forward Auth | Middleware | Agent-based |
| Extension model | Plugins (Go) | Agents (any language) |
| Isolation | In-process | Process-level |

## Sentinel vs Caddy

### Architecture Philosophy

**Caddy** is known for its simplicity and automatic HTTPS. It pioneered zero-config TLS with built-in Let's Encrypt integration and uses a human-friendly Caddyfile syntax.

**Sentinel** shares Caddy's focus on simplicity but prioritizes security extensibility over automatic configuration. The agent model provides flexibility that Caddy's module system cannot match for security use cases.

### When to Choose Caddy

- Want zero-config automatic HTTPS
- Simple static file serving with automatic TLS
- Prefer minimal configuration
- Need the extensive Caddy module ecosystem

### When to Choose Sentinel

- Need isolated security agents (WAF, auth, rate limiting)
- Building custom security controls
- Want process-level isolation for extensions
- Require inference/LLM-specific features (token counting, model routing)
- Need distributed rate limiting across instances

### Configuration Comparison

**Caddy** (Caddyfile):
```
app.example.com {
    reverse_proxy localhost:3000
}

static.example.com {
    root * /var/www/public
    file_server
}
```

**Sentinel** (KDL):
```kdl
listeners {
    listener "https" {
        address "0.0.0.0:443"
        tls {
            cert-path "/etc/sentinel/certs/app.crt"
            key-path "/etc/sentinel/certs/app.key"
        }
    }
}

routes {
    route "app" {
        matches { host "app.example.com" }
        upstream "backend"
    }

    route "static" {
        matches { host "static.example.com" }
        service-type "static"
        static-files {
            root "/var/www/public"
            fallback "index.html"
        }
    }
}

upstreams {
    upstream "backend" {
        targets {
            target { address "localhost:3000" }
        }
    }
}
```

### Key Differences

| Aspect | Caddy | Sentinel |
|--------|-------|----------|
| Automatic HTTPS | Built-in | Planned |
| Configuration | Caddyfile/JSON | KDL |
| Extension model | Modules (Go) | Agents (any language) |
| Isolation | In-process | Process-level |
| Static files | Built-in | Built-in with SPA fallback |

## Agent Protocol Comparison

Beyond proxy-level comparisons, it's important to understand how Sentinel's Agent Protocol V2 compares to extension mechanisms in other proxies. This is critical for security use cases where external processing is required.

### Agent Protocol V2 vs Envoy ext_proc

[Envoy's External Processing filter](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_filters/ext_proc_filter) (ext_proc) is the closest analog to Sentinel's agent protocol. Both enable external services to inspect and modify requests/responses.

| Aspect | Envoy ext_proc | Sentinel Agent Protocol V2 |
|--------|---------------|---------------------------|
| **Transport** | gRPC only | gRPC, UDS Binary, Reverse Connections |
| **Connection model** | Per-request stream | Pooled connections (reused) |
| **Default timeout** | 200ms | Configurable (30s default) |
| **Flow control** | [In development](https://github.com/envoyproxy/envoy/issues/33319) | Implemented (pause/resume) |
| **Body streaming** | Full duplex available | Zero-copy with MessagePack (62 GiB/s) |
| **Binary encoding** | Protobuf | MessagePack + JSON |
| **Typical added latency** | 1-6ms | ~230ns hot path |
| **Circuit breaker** | Via Envoy config | Built into protocol |
| **NAT traversal** | Not supported | Reverse connections |

**Where Sentinel wins:**

- **3 transport options** — ext_proc is gRPC-only; Sentinel supports UDS for same-host deployment (0.4ms vs 1.2ms latency) and reverse connections for agents behind NAT/firewalls
- **Connection pooling** — ext_proc creates a new gRPC stream per request; Sentinel reuses pooled connections with configurable strategies (RoundRobin, LeastConnections, HealthBased)
- **Flow control** — ext_proc is [still developing this](https://github.com/envoyproxy/envoy/issues/33319); Sentinel has working pause/resume signals with backpressure
- **Performance** — Sentinel's hot path completes in ~230ns; ext_proc typically adds 1-6ms
- **Simpler configuration** — KDL vs complex protobuf/YAML with Envoy's filter chain

**Where ext_proc wins:**

- Mature ecosystem, battle-tested at massive scale
- Native Envoy integration (no separate proxy)
- Larger community and more documentation
- Part of the CNCF ecosystem

### Agent Protocol V2 vs HAProxy SPOE

[HAProxy's Stream Processing Offload Engine](https://www.haproxy.com/blog/extending-haproxy-with-the-stream-processing-offload-engine) (SPOE) enables external agents to process traffic. It uses a custom binary protocol (SPOP) over TCP.

| Aspect | HAProxy SPOE | Sentinel Agent Protocol V2 |
|--------|-------------|---------------------------|
| **Protocol** | Custom binary (SPOP) | gRPC + MessagePack + JSON |
| **Matured in** | HAProxy 1.8 (2017) | 2025-2026 |
| **Encoding** | Custom binary | Industry-standard formats |
| **Body access** | Limited (header-focused) | Full streaming (62 GiB/s) |
| **Connection model** | Persistent TCP | Pooled with affinity tracking |
| **Language support** | C, Go, Python, Lua | Any (standard protocols) |
| **Metrics** | Via HAProxy stats | Built-in Prometheus export |
| **Circuit breaker** | Via HAProxy config | Built into protocol |

**Where Sentinel wins:**

- **Standard protocols** — gRPC and MessagePack vs custom binary; easier to implement agents in any language with existing libraries
- **Full body streaming** — SPOE is primarily designed for header inspection; Sentinel has zero-copy body chunks with 62 GiB/s throughput
- **Built-in observability** — Protocol-level metrics (counters, histograms, gauges) with native Prometheus export
- **Modern features** — Health-based load balancing, connection affinity for streaming requests, NAT traversal

**Where SPOE wins:**

- Tight HAProxy integration with minimal overhead
- Very lightweight for header-only inspection use cases
- Battle-tested in production for 7+ years
- Simpler mental model for basic use cases

### Agent Protocol V2 vs NGINX njs

[NGINX njs](https://nginx.org/en/docs/njs/) is a JavaScript runtime embedded in NGINX for request processing. Unlike external agents, njs runs in-process.

| Aspect | NGINX njs | Sentinel Agent Protocol V2 |
|--------|----------|---------------------------|
| **Execution model** | In-process JavaScript | External process (any language) |
| **Isolation** | None (crash = NGINX crash) | Full process isolation |
| **Language** | JavaScript (ES2023 with QuickJS) | Any (Rust, Go, Python, etc.) |
| **Memory** | Shared with NGINX | Separate process memory |
| **Body streaming** | Callback-based | True streaming with backpressure |
| **Garbage collection** | Yes (QuickJS GC) | Language-dependent (none for Rust) |
| **Hot reload** | Requires NGINX reload | Independent agent updates |
| **Throughput** | Limited by JS overhead | 62 GiB/s body streaming |

**Where Sentinel wins:**

- **Process isolation** — A buggy or crashing agent cannot take down the proxy; njs errors can crash NGINX
- **Language flexibility** — Write agents in Rust, Go, Python, Java, or any language; njs is JavaScript-only
- **Independent scaling** — Scale agents separately from the proxy; njs scales with NGINX workers
- **True streaming** — Flow control and backpressure vs JavaScript callbacks
- **No GC pauses** — Rust agents have no garbage collection; [njs/QuickJS has GC overhead](https://blog.nginx.org/blog/quickjs-engine-support-for-njs)
- **Performance** — 62 GiB/s body throughput vs JavaScript processing overhead

**Where njs wins:**

- Zero network overhead (in-process execution)
- Simpler deployment (no separate service to manage)
- Good for lightweight transformations and header manipulation
- [Context reuse](https://blog.nginx.org/blog/quickjs-engine-support-for-njs) minimizes per-request overhead
- Familiar JavaScript syntax

### Protocol Feature Matrix

| Feature | Sentinel V2 | Envoy ext_proc | HAProxy SPOE | NGINX njs |
|---------|:-----------:|:--------------:|:------------:|:---------:|
| Process isolation | ✓ | ✓ | ✓ | ✗ |
| Multiple transports | ✓ (3) | ✗ (gRPC only) | ✗ (TCP only) | N/A |
| Connection pooling | ✓ | ✗ | ✓ | N/A |
| Flow control | ✓ | 🚧 In progress | ✓ | N/A |
| Body streaming | ✓ Zero-copy | ✓ | Limited | Callbacks |
| Binary encoding | ✓ MessagePack | Protobuf | Custom | N/A |
| Circuit breaker | ✓ Built-in | Via Envoy | Via HAProxy | ✗ |
| NAT traversal | ✓ Reverse conn | ✗ | ✗ | N/A |
| Any language | ✓ | ✓ | ✓ | ✗ JS only |
| Metrics export | ✓ Prometheus | Via Envoy | Via HAProxy | ✗ |
| Connection affinity | ✓ | ✗ | ✗ | N/A |

### Performance Comparison

Based on benchmarks run on the same hardware:

| Metric | Sentinel V2 | Typical ext_proc | SPOE | njs |
|--------|-------------|------------------|------|-----|
| Hot path latency | ~230ns | 1-6ms | ~500μs | ~100μs |
| Body throughput | 62 GiB/s | N/A | Limited | ~1 GiB/s |
| Connection overhead | Pooled | Per-request | Persistent | None |
| Serialization | 150-560ns | Protobuf | Custom | N/A |

**Note**: These numbers are indicative. Actual performance depends on workload, configuration, and hardware.

### When to Use Each

| Use Case | Recommended |
|----------|-------------|
| Security gateway with WAF/auth | **Sentinel V2** |
| Service mesh sidecar | Envoy ext_proc |
| Simple header inspection | HAProxy SPOE |
| Lightweight request transforms | NGINX njs |
| High-throughput body processing | **Sentinel V2** |
| Agents behind NAT/firewall | **Sentinel V2** |
| Maximum ecosystem maturity | Envoy ext_proc |
| Minimal operational complexity | NGINX njs |

---

## Sentinel Unique Features

Beyond standard proxy capabilities, Sentinel offers features designed for modern workloads:

### Inference/LLM Gateway

Sentinel has first-class support for LLM and inference workloads:

| Feature | Description |
|---------|-------------|
| **Token-aware rate limiting** | Rate limit by tokens (not just requests) using tiktoken |
| **Token budgets** | Daily/monthly cumulative token limits per client |
| **Cost tracking** | Per-request cost attribution ($) |
| **Model-based routing** | Route `gpt-4*` to OpenAI, `claude-*` to Anthropic |
| **Streaming token counting** | Count tokens in SSE responses |
| **Least-tokens load balancing** | Route to backend with lowest token queue |

No other reverse proxy offers these capabilities natively.

### External Agent Architecture

Sentinel's agent model provides unique isolation guarantees:

| Capability | Benefit |
|------------|---------|
| **Process isolation** | Agent crash never takes down proxy |
| **Language flexibility** | Write agents in Python, Go, Rust, TypeScript, Elixir |
| **Independent deployment** | Update agents without proxy restart |
| **Resource limits** | Per-agent concurrency limits and circuit breakers |
| **WASM sandbox** | In-process agents with Wasmtime isolation |

### Distributed Rate Limiting

Native support for distributed rate limiting across instances:

- Redis backend (feature: `distributed-rate-limit`)
- Memcached backend (feature: `distributed-rate-limit-memcached`)
- Graceful degradation to local limits if backend fails

### Service Discovery

Built-in discovery for dynamic environments:

- Consul integration
- Kubernetes service discovery (feature: `kubernetes`)
- DNS resolution with TTL

### Security Features

- **GeoIP filtering** - Block/allow by country (MaxMind, IP2Location)
- **Decompression bomb protection** - Ratio limits (max 100x, 10MB output)
- **Guardrails** - Prompt injection detection for LLM workloads
- **PII detection** - Identify and mask sensitive data

## Feature Comparison Matrix

### Core Proxy Features

| Feature | Sentinel | Envoy | HAProxy | Nginx | Traefik | Caddy |
|---------|:--------:|:-----:|:-------:|:-----:|:-------:|:-----:|
| HTTP/1.1 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| HTTP/2 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| HTTP/3 (QUIC) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| WebSocket | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| gRPC | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| TCP proxy | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| TLS termination | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| mTLS | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Static files | ✓ | - | - | ✓ | ✓ | ✓ |
| SPA fallback (try_files) | ✓ | - | - | ✓ | - | ✓ |

### Load Balancing

| Feature | Sentinel | Envoy | HAProxy | Nginx | Traefik | Caddy |
|---------|:--------:|:-----:|:-------:|:-----:|:-------:|:-----:|
| Round robin | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Least connections | ✓ | ✓ | ✓ | ✓ | - | ✓ |
| Consistent hashing | ✓ | ✓ | ✓ | ✓ | - | - |
| Weighted | ✓ | ✓ | ✓ | ✓ | ✓ | - |
| Least tokens (LLM) | ✓ | - | - | - | - | - |
| Adaptive (latency) | ✓ | ✓ | - | - | - | - |
| Active health checks | ✓ | ✓ | ✓ | ✓* | ✓ | ✓ |
| Passive health checks | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Circuit breakers | ✓ | ✓ | - | - | ✓ | - |

*Nginx Plus only for active health checks

### Security & Extensions

| Feature | Sentinel | Envoy | HAProxy | Nginx | Traefik | Caddy |
|---------|:--------:|:-----:|:-------:|:-----:|:-------:|:-----:|
| External agents | ✓ | - | SPOE | - | - | - |
| WASM extensions | ✓ | ✓ | - | - | ✓ | - |
| Rate limiting | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Distributed rate limit | ✓ | - | - | - | - | - |
| Token-aware rate limit | ✓ | - | - | - | - | - |
| Forward auth | Planned | - | - | - | ✓ | ✓ |
| JWT validation | ✓ | ✓ | Lua | Module | ✓ | ✓ |
| GeoIP filtering | ✓ | - | - | Module | - | - |
| WAF (OWASP CRS) | Agent | - | SPOE | Module | - | - |

### Observability

| Feature | Sentinel | Envoy | HAProxy | Nginx | Traefik | Caddy |
|---------|:--------:|:-----:|:-------:|:-----:|:-------:|:-----:|
| Prometheus metrics | ✓ | ✓ | ✓ | Module | ✓ | ✓ |
| Distributed tracing | ✓ | ✓ | ✓ | Module | ✓ | ✓ |
| Access logs | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Structured logging | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

### Operations

| Feature | Sentinel | Envoy | HAProxy | Nginx | Traefik | Caddy |
|---------|:--------:|:-----:|:-------:|:-----:|:-------:|:-----:|
| Hot reload config | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Zero-downtime restart | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Auto HTTPS (ACME) | Planned | - | - | - | ✓ | ✓ |
| Dynamic config (API) | ✓ | ✓ (xDS) | ✓ | Plus | ✓ | ✓ |
| Graceful shutdown | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Service discovery | ✓ | ✓ | ✓ | Plus | ✓ | - |

## Memory Safety

A key differentiator for Sentinel is memory safety through Rust:

| Proxy | Language | Memory Safe | CVEs (2020-2024) |
|-------|----------|:-----------:|:----------------:|
| Sentinel | Rust | ✓ | 0 |
| Envoy | C++ | - | 30+ |
| HAProxy | C | - | 15+ |
| Nginx | C | - | 25+ |
| Traefik | Go | ✓ | 5+ |
| Caddy | Go | ✓ | 3+ |

Memory safety eliminates entire classes of vulnerabilities:
- Buffer overflows
- Use-after-free
- Double-free
- Null pointer dereferences

## Performance Characteristics

All six proxies are capable of handling high traffic loads. The primary differences are:

| Aspect | Sentinel | Envoy | HAProxy | Nginx | Traefik | Caddy |
|--------|----------|-------|---------|-------|---------|-------|
| Latency | Low | Low | Very low | Low | Low | Low |
| Throughput | High | High | Very high | High | High | High |
| Memory usage | Predictable | Higher | Very low | Low | Moderate | Moderate |
| CPU efficiency | High | High | Very high | High | High | High |

**Note**: Benchmark results vary significantly based on workload, configuration, and hardware. Always benchmark with your specific use case.

### Agent Overhead

Sentinel's agent model adds latency for agent calls:
- Unix socket: ~50-200µs per agent
- gRPC: ~200-500µs per agent

This overhead is acceptable for security use cases where the alternative is in-process complexity or external service calls.

## Migration Paths

### From Nginx to Sentinel

1. Map `server` blocks to `listeners`
2. Convert `location` blocks to `routes`
3. Translate `upstream` blocks
4. Replace modules with agents

See the [Migration Guide](/operations/migration/) for detailed examples.

### From HAProxy to Sentinel

1. Map `frontend` to `listeners`
2. Convert `backend` to `upstreams`
3. Translate ACLs to route matching
4. Replace Lua/SPOE with agents

### From Envoy to Sentinel

1. Simplify listener configuration
2. Convert clusters to upstreams
3. Replace filters with agents
4. Remove xDS dependency (if applicable)

### From Traefik to Sentinel

1. Convert routers to `routes` blocks
2. Map services to `upstreams`
3. Replace middlewares with agents
4. Move from Docker labels to KDL files
5. Replace automatic HTTPS with manual certs (ACME support planned)

### From Caddy to Sentinel

1. Convert Caddyfile blocks to KDL
2. Map `reverse_proxy` to routes + upstreams
3. Move from automatic HTTPS to manual certs (ACME support planned)
4. Replace modules with agents for security policies

## Summary

Choose **Sentinel** when:
- Security is a primary concern
- You want isolated, updateable security components
- Memory safety matters for your threat model
- You prefer explicit, readable configuration
- Building custom security policies
- Need LLM/inference gateway features (token limiting, model routing)

Choose **Envoy** when:
- Building a service mesh
- Need extensive protocol support
- Using xDS-based control planes
- Require Wasm extensibility

Choose **HAProxy** when:
- Maximum performance is critical
- Pure load balancing use case
- Deep TCP-level control needed
- Established HAProxy expertise

Choose **Nginx** when:
- Serving static files alongside proxying
- Need the extensive module ecosystem
- Using OpenResty/Lua extensively
- Established Nginx expertise

Choose **Traefik** when:
- Heavy Docker/Kubernetes environment
- Want automatic service discovery
- Need built-in Let's Encrypt support
- Prefer dynamic, label-based configuration

Choose **Caddy** when:
- Want zero-config automatic HTTPS
- Simple use case with minimal configuration
- Need the Caddy module ecosystem
- Prefer Caddyfile simplicity

## Next Steps

- [Architecture](../architecture/) - Understand Sentinel's design
- [Agents](/agents/) - Explore the agent ecosystem
- [Migration Guide](/operations/migration/) - Migrate from other proxies

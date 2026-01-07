+++
title = "Comparison with Alternatives"
weight = 6
+++

How Sentinel compares to other popular reverse proxies and load balancers.

## Overview

Sentinel occupies a unique position in the reverse proxy landscape. Rather than competing directly with established proxies on feature breadth, it focuses on security-first design, operational predictability, and an extensible agent architecture.

| Feature | Sentinel | Envoy | HAProxy | Nginx |
|---------|----------|-------|---------|-------|
| **Language** | Rust | C++ | C | C |
| **Memory Safety** | Yes (Rust) | No | No | No |
| **Configuration** | KDL | YAML/xDS | Config file | Config file |
| **Hot Reload** | Yes | Yes (xDS) | Yes | Yes (SIGHUP) |
| **Extension Model** | External agents | Filters (C++/Wasm) | Lua/SPOE | Modules/Lua |
| **Primary Use Case** | Security gateway | Service mesh | Load balancing | Web server/proxy |

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

- Pure reverse proxy (no static file serving needed)
- Security controls are the primary requirement
- Want isolated, updateable security components
- Prefer explicit configuration over complex conditionals

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

## Feature Comparison Matrix

### Core Proxy Features

| Feature | Sentinel | Envoy | HAProxy | Nginx |
|---------|:--------:|:-----:|:-------:|:-----:|
| HTTP/1.1 | ✓ | ✓ | ✓ | ✓ |
| HTTP/2 | ✓ | ✓ | ✓ | ✓ |
| HTTP/3 (QUIC) | Planned | ✓ | ✓ | ✓ |
| WebSocket | ✓ | ✓ | ✓ | ✓ |
| gRPC | ✓ | ✓ | ✓ | ✓ |
| TCP proxy | ✓ | ✓ | ✓ | ✓ |
| TLS termination | ✓ | ✓ | ✓ | ✓ |
| mTLS | ✓ | ✓ | ✓ | ✓ |

### Load Balancing

| Feature | Sentinel | Envoy | HAProxy | Nginx |
|---------|:--------:|:-----:|:-------:|:-----:|
| Round robin | ✓ | ✓ | ✓ | ✓ |
| Least connections | ✓ | ✓ | ✓ | ✓ |
| Random | ✓ | ✓ | ✓ | ✓ |
| Weighted | ✓ | ✓ | ✓ | ✓ |
| Consistent hashing | ✓ | ✓ | ✓ | ✓ |
| Active health checks | ✓ | ✓ | ✓ | ✓* |
| Passive health checks | ✓ | ✓ | ✓ | ✓ |

*Nginx Plus only for active health checks

### Security Features

| Feature | Sentinel | Envoy | HAProxy | Nginx |
|---------|:--------:|:-----:|:-------:|:-----:|
| Native WAF | ✓ (agent) | - | - | - |
| ModSecurity | ✓ (agent) | - | ✓ (SPOE) | ✓ (module) |
| Rate limiting | ✓ (agent) | ✓ | ✓ | ✓ |
| JWT validation | ✓ (agent) | ✓ | ✓ (Lua) | ✓ (module) |
| CORS | ✓ | ✓ | ✓ | ✓ |
| Request filtering | ✓ (agent) | ✓ | ✓ | ✓ |

### Observability

| Feature | Sentinel | Envoy | HAProxy | Nginx |
|---------|:--------:|:-----:|:-------:|:-----:|
| Prometheus metrics | ✓ | ✓ | ✓ | ✓* |
| Distributed tracing | ✓ | ✓ | ✓ | ✓* |
| Access logs | ✓ | ✓ | ✓ | ✓ |
| Structured logging | ✓ | ✓ | ✓ | ✓ |

*Requires additional modules

### Operations

| Feature | Sentinel | Envoy | HAProxy | Nginx |
|---------|:--------:|:-----:|:-------:|:-----:|
| Hot reload config | ✓ | ✓ | ✓ | ✓ |
| Zero-downtime restart | ✓ | ✓ | ✓ | ✓ |
| Dynamic config (API) | ✓ | ✓ (xDS) | ✓ | ✓* |
| Graceful shutdown | ✓ | ✓ | ✓ | ✓ |

*Nginx Plus only

## Memory Safety

A key differentiator for Sentinel is memory safety through Rust:

| Proxy | Language | Memory Safe | CVEs (2020-2024) |
|-------|----------|:-----------:|:----------------:|
| Sentinel | Rust | ✓ | 0 |
| Envoy | C++ | - | 30+ |
| HAProxy | C | - | 15+ |
| Nginx | C | - | 25+ |

Memory safety eliminates entire classes of vulnerabilities:
- Buffer overflows
- Use-after-free
- Double-free
- Null pointer dereferences

## Performance Characteristics

All four proxies are capable of handling high traffic loads. The primary differences are:

| Aspect | Sentinel | Envoy | HAProxy | Nginx |
|--------|----------|-------|---------|-------|
| Latency | Low | Low | Very low | Low |
| Throughput | High | High | Very high | High |
| Memory usage | Predictable | Higher | Very low | Low |
| CPU efficiency | High | High | Very high | High |

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

## Summary

Choose **Sentinel** when:
- Security is a primary concern
- You want isolated, updateable security components
- Memory safety matters for your threat model
- You prefer explicit, readable configuration
- Building custom security policies

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

## Next Steps

- [Architecture](../architecture/) - Understand Sentinel's design
- [Agents](/agents/) - Explore the agent ecosystem
- [Migration Guide](/operations/migration/) - Migrate from other proxies

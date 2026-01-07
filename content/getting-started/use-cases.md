+++
title = "Use Cases"
weight = 5
+++

Sentinel is a secure, high-performance reverse proxy with programmable security controls. Here are common scenarios where Sentinel excels, from enterprise deployments to personal projects.

## Reverse Proxy & Load Balancer

The most fundamental use case: distribute traffic across multiple backend servers with health checking and failover.

```kdl
listeners {
    listener "https" {
        address "0.0.0.0:443"
        protocol "https"
        tls {
            cert "/etc/sentinel/certs/server.crt"
            key "/etc/sentinel/certs/server.key"
        }
    }
}

routes {
    route "app" {
        matches {
            path-prefix "/"
        }
        upstream "app-servers"
    }
}

upstreams {
    upstream "app-servers" {
        target "app-1:8080" weight=1
        target "app-2:8080" weight=1
        target "app-3:8080" weight=1
        load-balancing "round_robin"
        health-check {
            path "/health"
            interval-secs 10
            timeout-secs 5
            healthy-threshold 2
            unhealthy-threshold 3
        }
    }
}
```

**Benefits:**
- TLS termination at the edge
- Automatic failover when backends go down
- Multiple load balancing algorithms (round robin, least connections, consistent hashing)
- Built-in metrics and observability

## API Gateway

Protect and manage your APIs with authentication, rate limiting, and request validation.

```kdl
routes {
    route "api" {
        matches {
            path-prefix "/api/v1"
        }
        upstream "api-backend"
        filters "auth-filter" "rate-limit-filter"
    }
}

agents {
    agent "auth" type="auth" {
        unix-socket "/var/run/sentinel/auth.sock"
        config {
            jwt-secret "${JWT_SECRET}"
            required-claims "sub" "exp"
        }
    }

    agent "ratelimit" type="ratelimit" {
        unix-socket "/var/run/sentinel/ratelimit.sock"
        config {
            requests-per-minute 100
            burst 20
        }
    }
}
```

**Benefits:**
- Centralized authentication across all API endpoints
- Per-client rate limiting to prevent abuse
- Request/response transformation capabilities

## Microservices Ingress

Route traffic to multiple backend services based on path, host, or headers.

```kdl
routes {
    route "users" {
        matches {
            path-prefix "/users"
        }
        upstream "users-service"
    }

    route "orders" {
        matches {
            path-prefix "/orders"
        }
        upstream "orders-service"
    }

    route "products" {
        matches {
            path-prefix "/products"
        }
        upstream "products-service"
    }
}

upstreams {
    upstream "users-service" {
        target "users-1:8080" weight=1
        target "users-2:8080" weight=1
        load-balancing "round_robin"
        health-check {
            path "/health"
            interval-secs 10
        }
    }
    // ... other upstreams
}
```

**Benefits:**
- Single entry point for all services
- Automatic health checks and failover
- Consistent TLS termination and observability

## Web Application Firewall

Protect web applications from OWASP Top 10 attacks including SQL injection, XSS, and path traversal.

```kdl
system {
    worker-threads 0
}

listeners {
    listener "http" {
        address "0.0.0.0:8080"
        protocol "http"
    }
}

routes {
    route "web" {
        matches {
            path-prefix "/"
        }
        upstream "web-backend"
        filters "waf-filter"
    }
}

agents {
    agent "waf" type="waf" {
        unix-socket "/var/run/sentinel/waf.sock"
        events "request_headers" "request_body"
        config {
            paranoia-level 2
            sqli #true
            xss #true
            path-traversal true
            block-mode true
            exclude-paths "/health" "/metrics"
        }
    }
}

upstreams {
    upstream "backend" {
        targets {
            target { address "127.0.0.1:3000" }
        }
    }
}
```

**Benefits:**
- Block attacks before they reach your application
- Configurable paranoia levels for different environments
- Native Rust regex engine for high performance

## AI/LLM Gateway

Secure AI API traffic with prompt injection detection, PII filtering, and usage controls.

```kdl
system {
    worker-threads 0
}

listeners {
    listener "http" {
        address "0.0.0.0:8080"
        protocol "http"
    }
}

routes {
    route "ai" {
        matches {
            path-prefix "/v1/chat"
        }
        upstream "openai-api"
        filters "ai-gateway-filter"
    }
}

agents {
    agent "ai-gateway" type="ai-gateway" {
        unix-socket "/var/run/sentinel/ai-gateway.sock"
        events "request_headers" "request_body"
        config {
            detect-prompt-injection #true
            detect-pii #true
            allowed-models "gpt-4" "gpt-3.5-turbo"
            max-tokens 4096
            rate-limit-tokens 100000
        }
    }
}

upstreams {
    upstream "backend" {
        targets {
            target { address "127.0.0.1:3000" }
        }
    }
}

```

**Benefits:**
- Prevent prompt injection and jailbreak attempts
- Detect and redact PII before it reaches the LLM
- Enforce model allowlists and token budgets

## Static Site + API

Serve static files with automatic compression while proxying API requests to backends.

```kdl
system {
    worker-threads 0
}

listeners {
    listener "http" {
        address "0.0.0.0:8080"
        protocol "http"
    }
}

routes {
    route "static" {
        priority "high"
        matches {
            path-regex "\\.(html|css|js|png|jpg|svg|woff2?)$"
        }
        service-type "static" {
            root "/var/www/html"
            compression #true
            cache-control "public, max-age=86400"
        }
    }

    route "api" {
        matches {
            path-prefix "/api"
        }
        upstream "api-backend"
    }

    route "spa-fallback" {
        priority "low"
        matches {
            path-prefix "/"
        }
        service-type "static" {
            root "/var/www/html"
            fallback "/index.html"
        }
    }
}

upstreams {
    upstream "backend" {
        targets {
            target { address "127.0.0.1:3000" }
        }
    }
}

```

**Benefits:**
- Serve static assets with optimal caching
- SPA fallback for client-side routing
- No need for separate static file server

## Zero-Trust Security

Implement defense-in-depth with multiple security agents in sequence.

```kdl
filters {
    filter "security-chain" {
        type "agent"
        agent "denylist"
        agent "waf"
        agent "auth"
    }
}

routes {
    route "secure" {
        matches {
            path-prefix "/"
        }
        upstream "backend"
        filters "security-chain"
    }
}

agents {
    agent "denylist" type="denylist" {
        unix-socket "/var/run/sentinel/denylist.sock"
        config {
            block-ips "10.0.0.0/8"
            block-countries "XX" "YY"
        }
    }

    agent "waf" type="waf" {
        unix-socket "/var/run/sentinel/waf.sock"
        config {
            paranoia-level 3
        }
    }

    agent "auth" type="auth" {
        unix-socket "/var/run/sentinel/auth.sock"
        config {
            provider "oidc"
            issuer "https://auth.example.com"
        }
    }
}
```

**Benefits:**
- Layered security controls
- Each agent focuses on one concern
- Fail-closed by default

## Custom Logic with Rust SDK

Build custom agents in Rust with the [Sentinel Agent SDK](https://github.com/raskell-io/sentinel-agent-sdk):

```rust
use sentinel_agent_sdk::prelude::*;

struct TenantAgent;

#[async_trait]
impl Agent for TenantAgent {
    async fn on_request(&self, request: &Request) -> Decision {
        // Add tenant context from subdomain
        let tenant = request.host()
            .and_then(|h| h.split('.').next())
            .unwrap_or("default");

        Decision::allow()
            .add_request_header("X-Tenant-ID", tenant)
    }

    async fn on_response(&self, _request: &Request, response: &Response) -> Decision {
        if response.is_html() {
            Decision::allow()
                .add_response_header("X-Content-Type-Options", "nosniff")
                .add_response_header("X-Frame-Options", "DENY")
        } else {
            Decision::allow()
        }
    }
}
```

**Benefits:**
- Native performance
- Type-safe request/response access
- Fluent decision builder API
- Built-in CLI and logging

## Custom Logic with JavaScript

Alternatively, use JavaScript for simpler logic or rapid prototyping:

```kdl
agents {
    agent "custom" type="js" {
        unix-socket "/var/run/sentinel/js.sock"
        script "/etc/sentinel/scripts/custom.js"
    }
}
```

```javascript
// /etc/sentinel/scripts/custom.js
function onRequest(request) {
    const host = request.headers["host"] || "";
    const tenant = host.split(".")[0];

    return {
        decision: "allow",
        addRequestHeaders: { "X-Tenant-ID": tenant }
    };
}
```

**Benefits:**
- No compilation needed
- Hot-reload without proxy restart
- Familiar syntax for web developers

## Homelab & Self-Hosted Services

Run a single proxy in front of all your self-hosted services with subdomain routing.

```kdl
listeners {
    listener "https" {
        address "0.0.0.0:443"
        protocol "https"
        tls {
            cert "/etc/sentinel/certs/wildcard.crt"
            key "/etc/sentinel/certs/wildcard.key"
        }
    }
}

routes {
    route "jellyfin" {
        matches { host "jellyfin.home.lan" }
        upstream "jellyfin"
    }

    route "nextcloud" {
        matches { host "cloud.home.lan" }
        upstream "nextcloud"
    }

    route "homeassistant" {
        matches { host "ha.home.lan" }
        upstream "homeassistant"
    }

    route "grafana" {
        matches { host "grafana.home.lan" }
        upstream "grafana"
    }
}

upstreams {
    upstream "jellyfin" { target "192.168.1.10:8096" }
    upstream "nextcloud" { target "192.168.1.11:80" }
    upstream "homeassistant" { target "192.168.1.12:8123" }
    upstream "grafana" { target "192.168.1.13:3000" }
}
```

**Benefits:**
- Single entry point for all your services
- TLS termination with your own certs or Let's Encrypt
- Low memory footprint (~50MB) - runs great on a Raspberry Pi
- Simple config - no complex YAML or templating

## Choosing the Right Agents

| Use Case | Recommended Agents |
|----------|-------------------|
| Load Balancing | (none needed - just routing) |
| API Protection | auth, ratelimit, waf |
| Web Application | waf, denylist |
| AI/LLM APIs | ai-gateway, ratelimit |
| Microservices | auth, ratelimit |
| Custom Logic (Rust) | [SDK](https://github.com/raskell-io/sentinel-agent-sdk) |
| Custom Logic (Scripting) | js, lua, wasm |
| Full OWASP CRS | modsec |
| Homelab | (none needed - just routing) |

## What's Next?

- Explore the [Agents](/agents/) section for detailed agent documentation
- See [Examples](/examples/) for complete, runnable configurations
- Read [Configuration Reference](/configuration/) for all options

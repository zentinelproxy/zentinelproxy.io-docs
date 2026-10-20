+++
title = "Namespaces"
weight = 17
updated = 2026-10-20
+++

Organize resources using namespaces for multi-tenant or microservice architectures. This example shows hierarchical configuration with namespace-scoped resources, service definitions, and cross-namespace exports.

{% callout(type="info", title="From 26.10_7") %}
This example is served as written from 26.10_7. Before, its namespace and
service routes were never matched (none of the namespaces has a listener
bound to it), and routes using a namespace's own upstream got `500`. It is the
same configuration as
[`config/examples/namespaces.kdl`](https://github.com/zentinelproxy/zentinel/blob/main/config/examples/namespaces.kdl)
in the Zentinel repository.
{% end %}

## Use Case

- Multi-tenant deployments with isolated configurations
- Microservice architectures with service-specific settings
- Shared platform services across namespaces
- Hierarchical policy inheritance
- Cross-namespace resource sharing via exports

## Architecture

```
                        ┌─────────────────────────┐
                        │       Global Scope      │
                        │  - listeners            │
                        │  - shared upstreams     │
                        │  - global filters       │
                        └───────────┬─────────────┘
                                    │
         ┌──────────────────────────┼──────────────────────────┐
         │                          │                          │
         ▼                          ▼                          ▼
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│ namespace       │       │ namespace       │       │ namespace       │
│ "platform"      │       │ "storefront"    │       │ "analytics"     │
│                 │       │                 │       │                 │
│ ┌─────────────┐ │       │ ┌─────────────┐ │       │ ┌─────────────┐ │
│ │ user-svc    │ │◄──────┤ │ catalog-svc │ │       │ │ ingest-svc  │ │
│ │ notify-svc  │ │exports│ │ cart-svc    │ │       │ │ query-svc   │ │
│ └─────────────┘ │       │ │ checkout    │ │       │ └─────────────┘ │
│                 │       │ └─────────────┘ │       │                 │
│ exports:        │       │                 │       │ exports:        │
│  - platform-auth│       │                 │       │  - ingestion    │
└─────────────────┘       └─────────────────┘       └─────────────────┘
```

## Configuration

Create `zentinel.kdl`:

```kdl
// Example: Namespaces and Hierarchical Configuration
//
// This example demonstrates how to organize resources using namespaces
// for multi-tenant or microservice architectures with:
// - Namespace-scoped resources (routes, upstreams, agents, filters)
// - Service definitions within namespaces
// - Resource exports for sharing across namespaces
// - Hierarchical scope resolution (service → namespace → exports → global)
//
// None of these namespaces or services has a listener of its own, so all of
// their routes are served on the global listeners below, matched together
// with the global routes by priority. A namespace or service that declares a
// listener (or a top-level listener with `namespace "..."`) is served only
// there. Scoped routes and upstreams appear in logs and metrics under their
// qualified ids, e.g. `platform:users-api`, `platform:user-service`.

system {
    worker-threads 4
}

// =============================================================================
// Global listeners (serve the global routes and every namespace's routes)
// =============================================================================
listeners {
    listener "http" {
        address "0.0.0.0:8080"
        protocol "http"
        request-timeout-secs 60
    }

    listener "https" {
        address "0.0.0.0:8443"
        protocol "https"

        tls {
            cert-file "/etc/zentinel/certs/wildcard.crt"
            key-file "/etc/zentinel/certs/wildcard.key"
            min-version "TLS1.2"
        }
    }
}

// =============================================================================
// Global upstreams (available to all namespaces)
// =============================================================================
upstreams {
    // Shared authentication service
    upstream "auth-service" {
        target "auth.internal:8080" weight=1
        target "auth.internal:8081" weight=1

        load-balancing "round_robin"

        health-check {
            type "http" {
                path "/health"
                expected-status 200
            }
            interval-secs 10
        }
    }

    // Shared logging/analytics service
    upstream "analytics" {
        target "analytics.internal:8080" weight=1

        load-balancing "round_robin"
    }
}

// =============================================================================
// Global filters (available to all namespaces)
// =============================================================================
filters {
    filter "global-rate-limit" {
        type "rate-limit"
        max-rps 1000
        burst 2000
        key "client-ip"
        on-limit "reject"
    }

    filter "global-cors" {
        type "cors"
    }
}

// =============================================================================
// Global agents (available to all namespaces)
// =============================================================================
agents {
    agent "waf-agent" {
        type "waf"
        grpc address="http://localhost:50051"
        events "request_headers" "request_body"
        timeout-ms 200
        failure-mode "closed"
    }
}

// =============================================================================
// Namespace: Platform (shared platform services)
// =============================================================================
namespace "platform" {
    // Namespace-level limits
    limits {
        max-body-size 10485760  // 10MB
        max-connections-per-client 50
    }

    // Namespace-scoped upstreams
    upstreams {
        upstream "user-service" {
            target "users.platform.internal:8080" weight=1
            target "users.platform.internal:8081" weight=1

            load-balancing "least_connections"

            health-check {
                type "http" {
                    path "/health"
                }
                interval-secs 10
            }
        }

        upstream "notification-service" {
            target "notifications.platform.internal:8080" weight=1

            load-balancing "round_robin"
        }
    }

    // Namespace-scoped filters
    filters {
        filter "platform-auth" {
            type "agent"
            agent "auth-agent"
            timeout-ms 100
            failure-mode "closed"
        }
    }

    // Namespace-scoped agents
    agents {
        agent "auth-agent" {
            type "auth"
            grpc address="http://localhost:50052"
            events "request_headers"
            timeout-ms 100
            failure-mode "closed"
        }
    }

    // Namespace-level routes
    routes {
        route "users-api" {
            priority "high"

            matches {
                host "api.example.com"
                path-prefix "/users"
            }

            upstream "user-service"

            filters "platform-auth" "global-rate-limit"

            policies {
                timeout-secs 30
                failure-mode "closed"
            }
        }

        route "notifications-api" {
            priority "normal"

            matches {
                host "api.example.com"
                path-prefix "/notifications"
            }

            upstream "notification-service"

            filters "platform-auth"

            policies {
                timeout-secs 10
            }
        }
    }

    // Export resources for use by other namespaces
    exports {
        // Allow other namespaces to use user-service
        upstreams "user-service"
        // Allow other namespaces to use platform auth
        filters "platform-auth"
        agents "auth-agent"
    }

    // Service within the platform namespace
    // User management service
    service "user-management" {
        // A service's limits apply to its routes, within the
        // namespace's (the smallest value wins).
        limits {
            max-in-flight-requests 500
        }

        routes {
            route "user-crud" {
                priority "high"

                matches {
                    host "users.example.com"
                    path-prefix "/api"
                    method "GET" "POST" "PUT" "DELETE"
                }

                // Reference namespace upstream
                upstream "user-service"

                policies {
                    timeout-secs 30
                }
            }

            route "user-avatar" {
                priority "normal"

                matches {
                    host "users.example.com"
                    path-prefix "/avatars"
                }

                upstream "user-service"

                policies {
                    timeout-secs 60
                    max-body-size "10MB"  // Override for uploads
                }
            }
        }
    }
}

// =============================================================================
// Namespace: Storefront (e-commerce tenant)
// =============================================================================
namespace "storefront" {
    limits {
        max-body-size 52428800  // 50MB for product images
        max-connections-per-client 100
    }

    // Namespace-scoped filters
    filters {
        filter "waf-agent" {
            type "agent"
            agent "waf-agent"
            timeout-ms 200
            failure-mode "closed"
        }
    }

    upstreams {
        upstream "catalog-service" {
            target "catalog.storefront.internal:8080" weight=1
            target "catalog.storefront.internal:8081" weight=1

            load-balancing "round_robin"
        }

        upstream "cart-service" {
            target "cart.storefront.internal:8080" weight=1

            load-balancing "ip_hash"  // Session affinity
        }

        upstream "checkout-service" {
            target "checkout.storefront.internal:8080" weight=1

            load-balancing "round_robin"
        }
    }

    routes {
        route "catalog" {
            priority "high"

            matches {
                host "shop.example.com"
                path-prefix "/catalog"
            }

            upstream "catalog-service"

            // Use exported platform auth
            filters "platform:platform-auth"

            policies {
                timeout-secs 10
                cache {
                    enabled #true
                    ttl-secs 300
                }
            }
        }

        route "cart" {
            priority "high"

            matches {
                host "shop.example.com"
                path-prefix "/cart"
            }

            upstream "cart-service"

            filters "platform:platform-auth"

            policies {
                timeout-secs 30
                failure-mode "closed"
            }
        }

        route "checkout" {
            priority "critical"

            matches {
                host "shop.example.com"
                path-prefix "/checkout"
            }

            upstream "checkout-service"

            // Full security for checkout
            filters "platform:platform-auth" "waf-agent"

            policies {
                timeout-secs 60
                failure-mode "closed"
            }
        }
    }

    service "product-api" {
        routes {
            route "products" {
                matches {
                    host "api.shop.example.com"
                    path-prefix "/products"
                }

                upstream "catalog-service"

                policies {
                    timeout-secs 10
                }
            }
        }
    }
}

// =============================================================================
// Namespace: Analytics (internal analytics platform)
// =============================================================================
namespace "analytics" {
    limits {
        max-body-size 104857600  // 100MB for data ingestion
    }

    upstreams {
        upstream "ingestion" {
            target "ingest.analytics.internal:8080" weight=1
            target "ingest.analytics.internal:8081" weight=1
            target "ingest.analytics.internal:8082" weight=1

            load-balancing "least_connections"

            connection-pool {
                max-connections 200
                max-idle 50
            }
        }

        upstream "query" {
            target "query.analytics.internal:8080" weight=1

            load-balancing "round_robin"

            timeouts {
                request-secs 300  // Long timeout for queries
            }
        }
    }

    routes {
        route "ingest" {
            priority "high"

            matches {
                host "analytics.internal"
                path-prefix "/ingest"
                method "POST"
            }

            upstream "ingestion"

            policies {
                timeout-secs 30
                max-body-size "100MB"
                failure-mode "open"  // Don't block on ingestion failure
            }
        }

        route "query" {
            priority "normal"

            matches {
                host "analytics.internal"
                path-prefix "/query"
            }

            upstream "query"

            // Use exported platform auth
            filters "platform:platform-auth"

            policies {
                timeout-secs 300
                failure-mode "closed"
            }
        }
    }

    // Export ingestion for other namespaces
    exports {
        upstreams "ingestion"
    }
}

// =============================================================================
// Global routes (matched with the namespace routes above, by priority)
// =============================================================================
routes {
    route "health" {
        priority "critical"

        matches {
            path "/health"
        }

        builtin-handler "health"
    }

    route "metrics" {
        priority "critical"

        matches {
            path "/metrics"
        }

        builtin-handler "metrics"
    }

    // Catch-all fallback
    route "fallback" {
        priority "low"

        matches {
            path-prefix "/"
        }

        builtin-handler "not-found"
    }
}

observability {
    metrics {
        enabled #true
        address "0.0.0.0:9090"
        path "/metrics"
        // Namespace labels added to all metrics
    }

    logging {
        level "info"
        format "json"

        access-log {
            enabled #true
            file "/var/log/zentinel/access.log"
            // Namespace and service fields included in logs
        }
    }
}
```

## Key Concepts

### Which Listener Serves a Route

None of the namespaces or services above has a listener of its own, so all of
their routes are served on the two global listeners, matched together with the
global routes by priority, then specificity. A namespace or service that
declares a listener (or a top-level listener with `namespace "..."`) is served
only there, and such a listener never serves global routes. See
[Which listener serves a route](/configuration/namespaces/#which-listener-serves-a-route).

Scoped routes and upstreams appear in logs and metrics under their qualified
ids, for example `platform:users-api`, `platform:user-management:user-crud` and
`platform:user-service`.

### Scope Resolution

Resources are resolved in this order:
1. **Service scope** - Check current service first
2. **Namespace scope** - Check containing namespace
3. **Exported resources** - Check what other namespaces export
4. **Global scope** - Check global definitions

A qualified reference such as `platform:platform-auth` is used as written.

### Cross-Namespace References

Reference exported resources using `namespace:resource` syntax:

```fragment,kdl
// In a storefront route
filters "platform:platform-auth"  // Use auth from platform namespace
```

### Exports

Namespaces explicitly declare which resources other namespaces can use:

```fragment,kdl
// inside namespace "platform" { }
exports {
    upstreams "user-service"
    filters "platform-auth"
    agents "auth-agent"
}
```

### Limit Inheritance

A namespace's `limits` apply to requests on its routes, together with the
global block, and from 26.10_7 a service's `limits` (here
`user-management`'s `max-in-flight-requests 500`) apply within the
namespace's: the smallest body and header limits win, and
`max-in-flight-requests` has its own counter in each scope. The connection
keys (`max-connections-per-client` above) count only connections on a scope's
own listeners, so in this example, where the namespaces are served on the
global listeners, they do not apply. See
[Limits: Namespace Limits](/configuration/limits/#namespace-limits).

## Setup

### 1. Start Zentinel

```bash
zentinel -c zentinel.kdl
```

### 2. Verify Configuration

```bash
# Validate config, including scoped listeners that cannot be bound
zentinel test --strict -c zentinel.kdl

# Also check that upstreams and agents are reachable
zentinel validate -c zentinel.kdl
```

## Testing

### Platform Routes

```bash
# Users API
curl -H "Host: api.example.com" \
     http://localhost:8080/users/123

# Notifications API
curl -H "Host: api.example.com" \
     http://localhost:8080/notifications
```

### Storefront Routes

```bash
# Catalog with caching
curl -H "Host: shop.example.com" \
     http://localhost:8080/catalog/products

# Cart with auth
curl -H "Host: shop.example.com" \
     -H "Authorization: Bearer $TOKEN" \
     http://localhost:8080/cart/items
```

### Analytics Routes

```bash
# Data ingestion
curl -X POST \
     -H "Host: analytics.internal" \
     -H "Content-Type: application/json" \
     -d '{"events": [...]}' \
     http://localhost:8080/ingest

# Query with auth
curl -H "Host: analytics.internal" \
     -H "Authorization: Bearer $TOKEN" \
     http://localhost:8080/query?q=SELECT...
```

## Customizations

### Namespace-Specific Rate Limits

A namespace has no rate-limit setting of its own. Define a `rate-limit` filter
in the namespace and attach it to its routes; it is counted separately from
filters of the same name in other scopes, with buckets per route:

```kdl
namespace "premium-tenant" {
    filters {
        filter "tenant-rate-limit" {
            type "rate-limit"
            max-rps 10000  // Higher limits for premium
            burst 20000
            key "client-ip"
        }
    }

    upstreams {
        upstream "backend" {
            target "127.0.0.1:3000"
        }
    }

    routes {
        route "api" {
            matches {
                path-prefix "/premium/"
            }
            upstream "backend"
            filters "tenant-rate-limit"
        }
    }
}
```

### Service-Level Circuit Breakers

Circuit breakers belong to upstreams, not routes:

```fragment,kdl
// inside namespace "..." { }
service "critical-api" {
    upstreams {
        upstream "main" {
            target "10.0.5.10:8080"
            circuit-breaker {
                failure-threshold 3
                success-threshold 2
                timeout-seconds 30
            }
        }
    }
    routes {
        route "main" {
            matches { path-prefix "/critical/" }
            upstream "main"
        }
    }
}
```

## Next Steps

- [Distributed Rate Limiting](../distributed-rate-limit/) - Add rate limiting
- [Mixed Services](../mixed-services/) - Microservices routing
- [API Gateway](../api-gateway/) - Complete API management

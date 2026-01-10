+++
title = "Namespaces"
weight = 17
+++

Organize resources using namespaces for multi-tenant or microservice architectures. This example shows hierarchical configuration with namespace-scoped resources, service definitions, and cross-namespace exports.

## Use Case

- Multi-tenant deployments with isolated configurations
- Microservice architectures with service-specific settings
- Shared platform services across namespaces
- Hierarchical limit and policy inheritance
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

Create `sentinel.kdl`:

```kdl
// Namespaces and Hierarchical Configuration
// Multi-tenant architecture with scoped resources

system {
    worker-threads 4
    max-connections 20000
}

// =============================================================================
// Global listeners (shared across all namespaces)
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
            cert-file "/etc/sentinel/certs/wildcard.crt"
            key-file "/etc/sentinel/certs/wildcard.key"
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

        load-balancing "round-robin"

        health-check {
            type "http" {
                path "/health"
                expected-status 200
            }
            interval-secs 10
        }
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
        unix-socket path="/var/run/sentinel/waf.sock"
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
        max-body-size-bytes 10485760  // 10MB
        max-connections-per-client 50
    }

    // Namespace-scoped upstreams
    upstreams {
        upstream "user-service" {
            target "users.platform.internal:8080" weight=1
            target "users.platform.internal:8081" weight=1

            load-balancing "least-connections"

            health-check {
                type "http" {
                    path "/health"
                }
                interval-secs 10
            }
        }

        upstream "notification-service" {
            target "notifications.platform.internal:8080" weight=1

            load-balancing "round-robin"
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
            unix-socket path="/var/run/sentinel/platform-auth.sock"
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
        upstreams "user-service"
        filters "platform-auth"
        agents "auth-agent"
    }

    // Service within the platform namespace
    service "user-management" {
        // Service-specific limits override namespace limits
        limits {
            max-body-size-bytes 5242880  // 5MB
        }

        routes {
            route "user-crud" {
                priority "high"

                matches {
                    host "users.example.com"
                    path-prefix "/api"
                    method "GET" "POST" "PUT" "DELETE"
                }

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
        max-body-size-bytes 52428800  // 50MB for product images
        max-connections-per-client 100
    }

    upstreams {
        upstream "catalog-service" {
            target "catalog.storefront.internal:8080" weight=1
            target "catalog.storefront.internal:8081" weight=1

            load-balancing "round-robin"
        }

        upstream "cart-service" {
            target "cart.storefront.internal:8080" weight=1

            load-balancing "ip-hash"  // Session affinity
        }

        upstream "checkout-service" {
            target "checkout.storefront.internal:8080" weight=1

            load-balancing "round-robin"
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
        max-body-size-bytes 104857600  // 100MB for data ingestion
    }

    upstreams {
        upstream "ingestion" {
            target "ingest.analytics.internal:8080" weight=1
            target "ingest.analytics.internal:8081" weight=1
            target "ingest.analytics.internal:8082" weight=1

            load-balancing "least-connections"

            connection-pool {
                max-connections 200
                max-idle 50
            }
        }

        upstream "query" {
            target "query.analytics.internal:8080" weight=1

            load-balancing "round-robin"

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
// Global routes (match after namespace routes)
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
            file "/var/log/sentinel/access.log"
            // Namespace and service fields included in logs
        }
    }
}
```

## Key Concepts

### Scope Resolution

Resources are resolved in this order:
1. **Service scope** - Check current service first
2. **Namespace scope** - Check containing namespace
3. **Global scope** - Check global definitions

### Cross-Namespace References

Reference exported resources using `namespace:resource` syntax:

```kdl
// In storefront namespace
filters "platform:platform-auth"  // Use auth from platform namespace
```

### Exports

Namespaces explicitly declare which resources other namespaces can use:

```kdl
exports {
    upstreams "user-service"
    filters "platform-auth"
    agents "auth-agent"
}
```

### Limit Inheritance

Limits cascade down with overrides:
- Global limits apply to all
- Namespace limits override global for that namespace
- Service limits override namespace for that service

## Setup

### 1. Start Sentinel

```bash
sentinel -c sentinel.kdl
```

### 2. Verify Configuration

```bash
# Validate config
sentinel validate -c sentinel.kdl

# Show resolved routes
sentinel routes -c sentinel.kdl
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
}
```

### Service-Level Circuit Breakers

```kdl
service "critical-api" {
    routes {
        route "main" {
            circuit-breaker {
                failure-threshold 3
                success-threshold 2
                timeout-seconds 30
            }
        }
    }
}
```

## Next Steps

- [Distributed Rate Limiting](../distributed-rate-limit/) - Add rate limiting
- [Mixed Services](../mixed-services/) - Microservices routing
- [API Gateway](../api-gateway/) - Complete API management

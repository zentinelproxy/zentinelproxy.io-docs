+++
title = "Namespaces & Services"
weight = 11
updated = 2026-10-20
+++

Namespaces and services provide hierarchical organization for Zentinel configuration, enabling multi-tenant deployments with runtime isolation.

{% callout(type="info", title="Served end to end from 26.10_7") %}
Before 26.10_7 namespaces were only partly wired: a namespace's routes were
served only on a top-level listener with `namespace "<id>"`, a route that used
a namespace-local upstream got `500 "Upstream pool not found"`, service routes
were never served, and the `listeners`/`listener` blocks inside namespaces and
services were never bound. From 26.10_7 all of this works as described on this
page.
{% end %}

## Overview

Zentinel supports three scope levels:

| Scope | Description | Use Case |
|-------|-------------|----------|
| **Global** | Root-level resources visible everywhere | Shared infrastructure |
| **Namespace** | Grouped resources with isolation | Teams, environments, domains |
| **Service** | Fine-grained resources within a namespace | Individual microservices |

## Basic Namespace

```kdl
namespace "api" {
    upstreams {
        upstream "backend" {
            target "10.0.1.1:8080"
        }
    }

    routes {
        route "main" {
            matches {
                path-prefix "/api/"
            }
            upstream "backend"
        }
    }
}
```

## Namespace with Limits

A namespace's `limits` block is applied to requests on the namespace's routes,
and from 26.10_7 a service's `limits` block to requests on the service's
routes, within the namespace's. Both take the same six keys as the global
block:

- body and header limits: the smallest of the global, the namespace, the
  service and the route's `policies { max-body-size }` applies; a key a scope
  does not set leaves the enclosing value in force;
- `max-in-flight-requests`: the namespace has its own counter inside the
  global limit, and a service its own inside the namespace's;
- `max-total-connections` and `max-connections-per-client`: counted only for
  the connections on the scope's own listeners, in addition to the global
  limits.

Before 26.10_7 a service's `limits` block was reported as ignored; before
26.10_6 neither was applied. There is no `max-requests-per-second-*` key: to
limit request rates, use a [`rate-limit` filter](../filters/#rate-limiting) or
a route's `policies { rate-limit }` (see [Rate Limiting](#rate-limiting)). See
[Limits: Namespace Limits](../limits/#namespace-limits).

A namespace can declare its own `limits` block:

```kdl
namespace "public-api" {
    limits {
        max-body-size 1048576  // 1MB
    }

    upstreams {
        upstream "api-backend" {
            target "127.0.0.1:3000"
        }
    }

    routes {
        route "public" {
            matches {
                path-prefix "/v1/"
            }
            upstream "api-backend"
        }
    }
}

namespace "internal-api" {
    limits {
        max-body-size 104857600  // 100MB
    }

    upstreams {
        upstream "internal-backend" {
            target "127.0.0.1:4000"
        }
    }

    routes {
        route "internal" {
            matches {
                path-prefix "/internal/"
            }
            upstream "internal-backend"
        }
    }
}
```

## Services Within Namespaces

Services provide finer-grained isolation within a namespace:

```kdl
namespace "payments" {
    limits {
        max-body-size 10485760  // 10MB default
    }

    // Shared upstream for the namespace
    upstreams {
        upstream "shared-db" {
            target "127.0.0.1:5432"
        }
    }

    service "checkout" {

        listener {
            address "0.0.0.0:8443"
            protocol "https"
            tls {
                cert-file "/etc/zentinel/certs/checkout.crt"
                key-file "/etc/zentinel/certs/checkout.key"
            }
        }

        upstreams {
            upstream "checkout-backend" {
                target "checkout-1:8080"
                target "checkout-2:8080"
            }
        }

        routes {
            route "process" {
                matches {
                    path-prefix "/checkout/"
                }
                upstream "checkout-backend"
            }
        }
    }

    service "refunds" {

        upstreams {
            upstream "refunds-backend" {
                target "127.0.0.1:3002"
            }
        }

        routes {
            route "process" {
                matches {
                    path-prefix "/refunds/"
                }
                upstream "refunds-backend"
            }
        }
    }
}
```

## Which Listener Serves a Route

A listener belongs to a scope: the global one, a namespace (a listener in the
namespace's `listeners` block, or a top-level listener with
`namespace "<id>"`), or a service (the service's `listener` block). From
26.10_7:

- A route is served on the listeners of the nearest scope that has one: its
  own, then its parent's, then the global listeners that are not bound to a
  namespace. A namespace or service without a listener is therefore served on
  the global listeners.
- A scope with a listener of its own is served only there, not on the global
  listeners. A service route of such a service gets `404` on the global
  listener.
- A listener bound to a namespace or service never serves global routes.
- All routes served on one listener are matched together, by priority and then
  specificity, as in one `routes` block.

Listeners declared inside a namespace or service are bound under qualified ids:
`ns:id` for a namespace's `listener "id"`, and `ns:svc:id` for a service's
`listener` block (`ns:svc:service-listener` when the block sets no `id`). A listener that cannot be bound (an invalid
address, an address another listener or the metrics server already uses, or an
id that collides) is reported by `zentinel test` as "is being ignored", and
`test --strict` fails on it. Its scope's routes are then not served at all,
not moved to the global listeners. A port that is valid but cannot be opened
when the proxy starts (a privileged port, for example) stops startup.

Scoped routes appear in logs and metrics under their qualified ids:
`ns:route` for a namespace's route, `ns:svc:route` for a service's.

## Scope Resolution

When a route references an upstream, filter or agent, Zentinel resolves it in
order:

1. **Service scope** - Resources in the same service
2. **Namespace scope** - Resources in the parent namespace
3. **Exported resources** - Resources exported from other namespaces
4. **Global scope** - Root-level resources

A qualified reference (`ns:name`, `ns:svc:name`) is used as written and names
that resource directly; see [Qualified References](#qualified-references).

### Resolution Example

```kdl
// Global upstream (available everywhere)
upstreams {
    upstream "shared-auth" {
        target "auth:8080"
    }
}

namespace "api" {
    // Namespace-level upstream
    upstreams {
        upstream "backend" {
            target "api-backend:8080"
        }
    }

    routes {
        route "main" {
            upstream "backend"      // Resolves to api:backend
        }
        route "auth" {
            upstream "shared-auth"  // Resolves to global shared-auth
        }
    }

    service "users" {
        upstreams {
            upstream "backend" {  // Shadows namespace backend
                target "users-backend:8080"
            }
        }

        routes {
            route "list" {
                upstream "backend"  // Resolves to api:users:backend
            }
        }
    }
}
```

## Qualified References

Use qualified names to explicitly reference resources from other scopes:

```kdl
namespace "frontend" {
    routes {
        route "api-proxy" {
            matches {
                path-prefix "/api/"
            }
            // Explicit reference to 'api' namespace
            upstream "api:backend"
        }
    }
}
```

### Reference Formats

| Format | Scope | Example |
|--------|-------|---------|
| `name` | Current scope chain | `upstream "backend"` |
| `namespace:name` | Specific namespace | `upstream "api:backend"` |
| `namespace:service:name` | Specific service | `upstream "api:users:backend"` |

## Exporting Resources

Make namespace resources available globally:

```kdl
namespace "infrastructure" {
    upstreams {
        upstream "redis" {
            target "redis:6379"
        }
        upstream "postgres" {
            target "postgres:5432"
        }
    }

    // Export these upstreams for use by other namespaces
    exports {
        upstreams "redis" "postgres"
    }
}

namespace "api" {
    routes {
        route "cached" {
            upstream "redis"  // Resolves via export
        }
    }
}
```

### Export Configuration

Inside a `namespace` block:

```fragment,kdl
exports {
    upstreams "upstream-1" "upstream-2"
    agents "auth-agent"
    filters "rate-limit" "cors"
}
```

## Runtime Isolation

Each namespace/service has isolated:

### Rate Limiting

There is no rate-limit setting on a namespace or service itself. Write a
`rate-limit` filter (or a route's `policies { rate-limit }`) inside the scope
and attach it to the scope's routes. From 26.10_7 the filter and its routes
are keyed by their qualified ids, so a filter is counted separately from a
same-named filter in another scope. Buckets are kept per route: a filter
attached to several routes gives each route its own buckets, so a limit hit in
`api:public:public` does not affect `api:partner:partner`, and there is no
single bucket for a whole namespace:

```kdl
namespace "api" {
    filters {
        filter "public-limit" {
            type "rate-limit"
            max-rps 50
            burst 50
            key "client-ip"
        }
        filter "partner-limit" {
            type "rate-limit"
            max-rps 200
            burst 200
            key "header:X-Partner-Id"
        }
    }

    upstreams {
        upstream "backend" {
            target "127.0.0.1:3000"
        }
    }

    service "public" {
        routes {
            route "public" {
                matches {
                    path-prefix "/public/"
                }
                upstream "backend"
                filters "public-limit"
            }
        }
    }

    service "partner" {
        routes {
            route "partner" {
                matches {
                    path-prefix "/partner/"
                }
                upstream "backend"
                filters "partner-limit"
            }
        }
    }
}
```

### Circuit Breakers

Circuit breakers are isolated per scope. An upstream failure in one namespace does not trip circuit breakers in other namespaces.

```kdl
namespace "critical" {
    upstreams {
        upstream "backend" {
            target "10.0.5.1:8080"
            health-check {
                type "http" { path "/health" }
            }
            circuit-breaker {
                failure-threshold 3
                success-threshold 2
                timeout-seconds 30
            }
        }
    }
}

namespace "best-effort" {
    upstreams {
        upstream "backend" {
            target "10.0.6.1:8080"
            circuit-breaker {
                failure-threshold 10  // More tolerant
                timeout-seconds 10
            }
        }
    }
}
```

### Metrics

Scoped routes and upstreams appear in the ordinary metrics under their
qualified ids, so a namespace or service can be selected by prefix:

```
zentinel_requests_total{route="api:users:list", method="GET", status="200"}
zentinel_request_duration_seconds_bucket{route="payments:checkout:process", method="POST", le="0.1"}
```

```promql
sum(rate(zentinel_requests_total{route=~"payments:.*"}[5m])) by (route)
```

The `zentinel_scoped_*` metrics (with `namespace` and `service` labels) are
not emitted.

### Access Logs

From 26.10_7 the access log's `namespace` and `service` fields are filled from
the route the request matched (empty for a global route), and `route_id` and
`upstream` are the qualified ids:

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "trace_id": "2kF8xQw4BnM",
  "method": "POST",
  "path": "/checkout/process",
  "status": 200,
  "namespace": "payments",
  "service": "checkout",
  "route_id": "payments:checkout:process",
  "upstream": "payments:checkout:checkout-backend"
}
```

## Migration from Flat Configuration

Existing flat configurations continue to work unchanged. All resources are treated as global scope.

### Before (Flat)

```kdl
upstreams {
    upstream "api-backend" {
        target "127.0.0.1:3000"
    }
    upstream "web-backend" {
        target "127.0.0.1:3001"
    }
}

routes {
    route "api" {
        matches { path-prefix "/api/" }
        upstream "api-backend"
    }
    route "web" {
        matches { path-prefix "/" }
        upstream "web-backend"
    }
}
```

### After (Namespaced)

```kdl
// Shared infrastructure remains global
upstreams {
    upstream "shared-auth" {
        target "127.0.0.1:4000"
    }
}

namespace "api" {
    upstreams {
        upstream "backend" {
            target "127.0.0.1:3000"  // Renamed from api-backend
        }
    }

    routes {
        route "main" {
            matches { path-prefix "/api/" }
            upstream "backend"
            // Can still access global: upstream "shared-auth"
        }
    }
}

namespace "web" {
    upstreams {
        upstream "backend" {
            target "127.0.0.1:3001"  // Same local name, different scope
        }
    }

    routes {
        route "main" {
            matches { path-prefix "/" }
            upstream "backend"
        }
    }
}
```

## Complete Example

```kdl
// Global configuration
system {
    worker-threads 0
    trace-id-format "tinyflake"
}

listeners {
    listener "http" {
        address "0.0.0.0:8080"
        protocol "http"
    }
}

// Global shared resources
upstreams {
    upstream "auth-service" {
        target "auth-1:8080"
        target "auth-2:8080"
        load-balancing "round_robin"
    }
}

// API namespace
namespace "api" {
    limits {
        max-body-size 10485760
    }

    upstreams {
        upstream "backend" {
            target "api-1:8080"
            target "api-2:8080"
        }
    }

    routes {
        route "main" {
            matches {
                path-prefix "/api/v1/"
            }
            upstream "backend"
        }

        route "auth" {
            matches {
                path-prefix "/api/auth/"
            }
            upstream "auth-service"  // Global
        }
    }

    service "users" {

        upstreams {
            upstream "users-backend" {
                target "users-1:8080"
            }
        }

        routes {
            route "crud" {
                matches {
                    path-prefix "/api/v1/users/"
                }
                upstream "users-backend"
            }
        }
    }

    exports {
        upstreams "backend"
    }
}

// Web namespace
namespace "web" {
    listeners {
        listener "https" {
            address "0.0.0.0:443"
            protocol "https"
            tls {
                cert-file "/etc/zentinel/certs/web.crt"
                key-file "/etc/zentinel/certs/web.key"
            }
        }
    }

    upstreams {
        upstream "frontend" {
            target "web-1:3000"
        }
    }

    routes {
        route "static" {
            matches {
                path-prefix "/"
            }
            upstream "frontend"
        }

        route "api-proxy" {
            matches {
                path-prefix "/api/"
            }
            upstream "api:backend"  // Cross-namespace reference
        }
    }
}

// Observability
observability {
    metrics {
        enabled #true
        address "0.0.0.0:9090"
    }
}
```

## Validation

Zentinel validates namespace configuration:

- Unique IDs within each scope
- Valid cross-namespace references
- No circular dependencies in exports
- Reserved character (`:`) not used in resource IDs

From 26.10_7, `zentinel test` also reports as "is being ignored" a scoped
listener that cannot be bound, and a scoped resource whose qualified id is
already the id of a top-level one (a global route named `api:main` next to
route `main` of namespace `api`):

```bash
zentinel test --strict -c zentinel.kdl
```

## Best Practices

### Naming Conventions

```kdl
// Use descriptive, hierarchical names
namespace "payments" {
    upstreams {
        upstream "backend" {
            target "127.0.0.1:3000"
        }
    }
}
namespace "users" {
    upstreams {
        upstream "backend" {
            target "127.0.0.1:3001"
        }
    }
}
```

### Scope Organization

| Level | Use For |
|-------|---------|
| Global | Shared infrastructure (auth, logging, metrics) |
| Namespace | Team boundaries, environments, domains |
| Service | Individual microservices, isolated workloads |

### When to Use Services

Use services when you need:
- Dedicated listeners with separate TLS certificates
- Separate rate-limit filters for subcomponents
- Fine-grained circuit breaker isolation
- Separate metrics dashboards

### Export Sparingly

Only export resources that genuinely need cross-namespace access:

```kdl
namespace "infrastructure" {
    upstreams {
        upstream "redis" {
            target "127.0.0.1:6379"
        }
        upstream "postgres" {
            target "127.0.0.1:5432"
        }
        upstream "internal-tool" {
            target "127.0.0.1:9000"  // Don't export
        }
    }

    exports {
        upstreams "redis" "postgres"  // Only shared infra
    }
}
```

## Next Steps

- [Limits](../limits/) - Request size limits
- [Upstreams](../upstreams/) - Backend pool configuration
- [Routes](../routes/) - Request matching and routing

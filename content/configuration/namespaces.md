+++
title = "Namespaces & Services"
weight = 11
updated = 2026-02-19
+++

Namespaces and services provide hierarchical organization for Zentinel configuration, enabling multi-tenant deployments with runtime isolation.

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
            targets {
                target { address "10.0.1.1:8080" }
            }
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

Each namespace can have its own limits for isolation:

```kdl
namespace "public-api" {
    limits {
        max-body-size-bytes 1048576  // 1MB
        max-requests-per-second-global 1000
        max-requests-per-second-per-client 50
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
        max-body-size-bytes 104857600  // 100MB
        max-requests-per-second-global 10000
        // No per-client limit for internal services
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
        max-body-size-bytes 10485760  // 10MB default
    }

    // Shared upstream for the namespace
    upstreams {
        upstream "shared-db" {
            target "127.0.0.1:5432"
        }
    }

    service "checkout" {
        limits {
            max-requests-per-second-global 500
        }

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
                targets {
                    target { address "checkout-1:8080" }
                    target { address "checkout-2:8080" }
                }
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
        limits {
            max-requests-per-second-global 100  // Lower limit for refunds
        }

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

## Scope Resolution

When a route references an upstream, Zentinel resolves it in order:

1. **Service scope** - Resources in the same service
2. **Namespace scope** - Resources in the parent namespace
3. **Exported resources** - Resources exported from other namespaces
4. **Global scope** - Root-level resources

### Resolution Example

```kdl
// Global upstream (available everywhere)
upstreams {
    upstream "shared-auth" {
        targets { target { address "auth:8080" } }
    }
}

namespace "api" {
    // Namespace-level upstream
    upstreams {
        upstream "backend" {
            targets { target { address "api-backend:8080" } }
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
                targets { target { address "users-backend:8080" } }
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
            targets { target { address "redis:6379" } }
        }
        upstream "postgres" {
            targets { target { address "postgres:5432" } }
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

```kdl
exports {
    upstreams "upstream-1" "upstream-2"
    agents "auth-agent"
    filters "rate-limit" "cors"
}
```

## Runtime Isolation

Each namespace/service has isolated:

### Rate Limiting

```kdl
namespace "api" {
    limits {
        max-requests-per-second-global 5000
    }

    service "public" {
        limits {
            max-requests-per-second-global 1000
            max-requests-per-second-per-client 50
        }
    }

    service "partner" {
        limits {
            max-requests-per-second-global 2000
            max-requests-per-second-per-client 200
        }
    }
}
```

Rate limits are enforced independently per scope. A rate limit hit in `api:public` does not affect `api:partner`.

### Circuit Breakers

Circuit breakers are isolated per scope. An upstream failure in one namespace does not trip circuit breakers in other namespaces.

```kdl
namespace "critical" {
    upstreams {
        upstream "backend" {
            health-check {
                type "http" { path "/health" }
            }
            circuit-breaker {
                failure-threshold 3
                success-threshold 2
                timeout-secs 30
            }
        }
    }
}

namespace "best-effort" {
    upstreams {
        upstream "backend" {
            circuit-breaker {
                failure-threshold 10  // More tolerant
                timeout-secs 10
            }
        }
    }
}
```

### Metrics

Scoped metrics include `namespace` and `service` labels:

```
zentinel_scoped_requests_total{namespace="api", service="users", route="list", status="200"}
zentinel_scoped_request_duration_seconds{namespace="api", service="users", route="list"}
zentinel_scoped_rate_limit_hits_total{namespace="api", service="public", route="main"}
zentinel_scoped_circuit_breaker_state{namespace="payments", service="checkout", upstream="backend"}
```

### Access Logs

Access logs include scope information in JSON format:

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "trace_id": "2kF8xQw4BnM",
  "method": "POST",
  "path": "/checkout/process",
  "status": 200,
  "namespace": "payments",
  "service": "checkout",
  "route_id": "process",
  "upstream": "checkout-backend"
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
        upstream "api-backend"
    }
    route "web" {
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
        targets {
            target { address "auth-1:8080" }
            target { address "auth-2:8080" }
        }
        load-balancing "round_robin"
    }
}

// API namespace
namespace "api" {
    limits {
        max-body-size-bytes 10485760
        max-requests-per-second-global 10000
    }

    upstreams {
        upstream "backend" {
            targets {
                target { address "api-1:8080" }
                target { address "api-2:8080" }
            }
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
        limits {
            max-requests-per-second-per-client 100
        }

        upstreams {
            upstream "users-backend" {
                targets {
                    target { address "users-1:8080" }
                }
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
            targets {
                target { address "web-1:3000" }
            }
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

```bash
zentinel --config zentinel.kdl --validate
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
- Independent rate limits for subcomponents
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

- [Limits](../limits/) - Configure per-scope limits
- [Upstreams](../upstreams/) - Backend pool configuration
- [Routes](../routes/) - Request matching and routing

+++
title = "Migration Guide"
weight = 3
+++

Guides for migrating to Sentinel from other reverse proxies.

## Migration Overview

### General Steps

1. **Audit current configuration** - Document routes, upstreams, TLS settings
2. **Create Sentinel config** - Translate configuration to KDL
3. **Test in parallel** - Run Sentinel alongside existing proxy
4. **Gradual cutover** - Shift traffic incrementally
5. **Monitor and validate** - Compare metrics and behavior
6. **Decommission old proxy** - Remove after validation period

### Key Differences

| Feature | nginx | HAProxy | Traefik | Sentinel |
|---------|-------|---------|---------|----------|
| Config format | nginx.conf | haproxy.cfg | YAML/TOML | KDL |
| Hot reload | `nginx -s reload` | `kill -USR2` | Automatic | `SIGHUP` |
| Health checks | `upstream` block | `option httpchk` | Built-in | `health-check` block |
| Load balancing | `upstream` | `balance` | `loadBalancer` | `load-balancing` |

## From nginx

### Basic Proxy

**nginx:**
```nginx
upstream backend {
    server 10.0.1.1:8080;
    server 10.0.1.2:8080;
}

server {
    listen 80;
    server_name api.example.com;

    location /api/ {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

**Sentinel:**
```kdl
listeners {
    listener "http" {
        address "0.0.0.0:80"
        protocol "http"
    }
}

routes {
    route "api" {
        matches {
            host "api.example.com"
            path-prefix "/api/"
        }
        upstream "backend"
        policies {
            request-headers {
                set {
                    "X-Real-IP" "${client_ip}"
                }
            }
        }
    }
}

upstreams {
    upstream "backend" {
        targets {
            target { address "10.0.1.1:8080" }
            target { address "10.0.1.2:8080" }
        }
    }
}
```

### TLS Termination

**nginx:**
```nginx
server {
    listen 443 ssl http2;
    server_name api.example.com;

    ssl_certificate /etc/nginx/ssl/server.crt;
    ssl_certificate_key /etc/nginx/ssl/server.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;

    location / {
        proxy_pass http://backend;
    }
}
```

**Sentinel:**
```kdl
listeners {
    listener "https" {
        address "0.0.0.0:443"
        protocol "https"
        tls {
            cert-file "/etc/sentinel/certs/server.crt"
            key-file "/etc/sentinel/certs/server.key"
            min-version "1.2"
        }
    }
}
```

### Load Balancing

**nginx:**
```nginx
upstream backend {
    least_conn;
    server 10.0.1.1:8080 weight=3;
    server 10.0.1.2:8080 weight=2;
    server 10.0.1.3:8080 weight=1;
}
```

**Sentinel:**
```kdl
upstreams {
    upstream "backend" {
        targets {
            target { address "10.0.1.1:8080" weight=3 }
            target { address "10.0.1.2:8080" weight=2 }
            target { address "10.0.1.3:8080" weight=1 }
        }
        load-balancing "least_connections"  // or "weighted"
    }
}
```

### Rate Limiting

**nginx:**
```nginx
limit_req_zone $binary_remote_addr zone=api:10m rate=100r/s;

location /api/ {
    limit_req zone=api burst=200 nodelay;
    proxy_pass http://backend;
}
```

**Sentinel:**
```kdl
routes {
    route "api" {
        matches {
            path-prefix "/api/"
        }
        upstream "backend"
        policies {
            rate-limit {
                requests-per-second 100
                burst 200
                key "client_ip"
            }
        }
    }
}
```

### nginx Mapping Table

| nginx | Sentinel |
|-------|----------|
| `listen 80` | `address "0.0.0.0:80"` |
| `server_name` | `matches { host "..." }` |
| `location /path` | `matches { path-prefix "/path" }` |
| `location = /exact` | `matches { path "/exact" }` |
| `location ~ regex` | `matches { path-regex "regex" }` |
| `proxy_pass` | `upstream "name"` |
| `upstream { }` | `upstreams { upstream "name" { } }` |
| `least_conn` | `load-balancing "least_connections"` |
| `ip_hash` | `load-balancing "ip_hash"` |
| `proxy_connect_timeout` | `timeouts { connect-secs }` |
| `proxy_read_timeout` | `timeouts { read-secs }` |
| `proxy_set_header` | `policies { request-headers { set { } } }` |

## From HAProxy

### Basic Configuration

**HAProxy:**
```
frontend http_front
    bind *:80
    default_backend http_back

backend http_back
    balance roundrobin
    server server1 10.0.1.1:8080 check
    server server2 10.0.1.2:8080 check
```

**Sentinel:**
```kdl
listeners {
    listener "http" {
        address "0.0.0.0:80"
        protocol "http"
        default-route "api"
    }
}

routes {
    route "api" {
        matches {
            path-prefix "/"
        }
        upstream "backend"
    }
}

upstreams {
    upstream "backend" {
        targets {
            target { address "10.0.1.1:8080" }
            target { address "10.0.1.2:8080" }
        }
        load-balancing "round_robin"
        health-check {
            type "http" {
                path "/health"
                expected-status 200
            }
        }
    }
}
```

### ACLs and Routing

**HAProxy:**
```
frontend http_front
    bind *:80

    acl is_api path_beg /api/
    acl is_static path_beg /static/

    use_backend api_back if is_api
    use_backend static_back if is_static
    default_backend default_back
```

**Sentinel:**
```kdl
routes {
    route "api" {
        priority 100
        matches {
            path-prefix "/api/"
        }
        upstream "api-backend"
    }

    route "static" {
        priority 100
        matches {
            path-prefix "/static/"
        }
        service-type "static"
        static-files {
            root "/var/www/static"
        }
    }

    route "default" {
        priority 1
        matches {
            path-prefix "/"
        }
        upstream "default-backend"
    }
}
```

### Health Checks

**HAProxy:**
```
backend http_back
    option httpchk GET /health
    http-check expect status 200
    server server1 10.0.1.1:8080 check inter 10s fall 3 rise 2
```

**Sentinel:**
```kdl
upstreams {
    upstream "backend" {
        health-check {
            type "http" {
                path "/health"
                expected-status 200
            }
            interval-secs 10
            unhealthy-threshold 3
            healthy-threshold 2
        }
    }
}
```

### HAProxy Mapping Table

| HAProxy | Sentinel |
|---------|----------|
| `frontend` | `listeners { listener }` |
| `backend` | `upstreams { upstream }` |
| `bind *:80` | `address "0.0.0.0:80"` |
| `balance roundrobin` | `load-balancing "round_robin"` |
| `balance leastconn` | `load-balancing "least_connections"` |
| `balance source` | `load-balancing "ip_hash"` |
| `server ... weight N` | `target { weight=N }` |
| `option httpchk` | `health-check { type "http" }` |
| `inter 10s` | `interval-secs 10` |
| `fall 3` | `unhealthy-threshold 3` |
| `rise 2` | `healthy-threshold 2` |
| `acl ... path_beg` | `matches { path-prefix }` |
| `acl ... hdr(host)` | `matches { host }` |
| `use_backend ... if` | Route with matching conditions |

## From Traefik

### Basic Configuration

**Traefik (YAML):**
```yaml
entryPoints:
  web:
    address: ":80"
  websecure:
    address: ":443"

http:
  routers:
    api:
      rule: "PathPrefix(`/api/`)"
      service: api-service
      entryPoints:
        - web

  services:
    api-service:
      loadBalancer:
        servers:
          - url: "http://10.0.1.1:8080"
          - url: "http://10.0.1.2:8080"
```

**Sentinel:**
```kdl
listeners {
    listener "http" {
        address "0.0.0.0:80"
        protocol "http"
    }
    listener "https" {
        address "0.0.0.0:443"
        protocol "https"
        tls {
            cert-file "/etc/sentinel/certs/server.crt"
            key-file "/etc/sentinel/certs/server.key"
        }
    }
}

routes {
    route "api" {
        matches {
            path-prefix "/api/"
        }
        upstream "api-service"
    }
}

upstreams {
    upstream "api-service" {
        targets {
            target { address "10.0.1.1:8080" }
            target { address "10.0.1.2:8080" }
        }
    }
}
```

### Middleware to Policies

**Traefik:**
```yaml
http:
  middlewares:
    rate-limit:
      rateLimit:
        average: 100
        burst: 200
    headers:
      customRequestHeaders:
        X-Custom-Header: "value"

  routers:
    api:
      rule: "PathPrefix(`/api/`)"
      middlewares:
        - rate-limit
        - headers
      service: api-service
```

**Sentinel:**
```kdl
routes {
    route "api" {
        matches {
            path-prefix "/api/"
        }
        upstream "api-service"
        policies {
            rate-limit {
                requests-per-second 100
                burst 200
            }
            request-headers {
                set {
                    "X-Custom-Header" "value"
                }
            }
        }
    }
}
```

### Traefik Mapping Table

| Traefik | Sentinel |
|---------|----------|
| `entryPoints` | `listeners` |
| `routers` | `routes` |
| `services` | `upstreams` |
| `loadBalancer.servers` | `targets` |
| `rule: PathPrefix(...)` | `matches { path-prefix }` |
| `rule: Host(...)` | `matches { host }` |
| `rule: Headers(...)` | `matches { header }` |
| `middlewares` | `policies`, `filters` |
| `healthCheck` | `health-check` |

## Validation Checklist

### Before Migration

- [ ] Document all routes and backends
- [ ] Export current TLS certificates
- [ ] Note rate limits and timeouts
- [ ] Record health check configurations
- [ ] Capture baseline metrics

### After Migration

- [ ] All routes accessible
- [ ] TLS working correctly
- [ ] Health checks passing
- [ ] Load balancing functioning
- [ ] Rate limits enforced
- [ ] Metrics comparable to baseline
- [ ] Error rates normal
- [ ] Latency acceptable

### Parallel Running

```bash
# Run Sentinel on different port
sentinel --config sentinel.kdl  # Listens on 8080

# Test both proxies
curl http://localhost:80/api/test    # Old proxy
curl http://localhost:8080/api/test  # Sentinel

# Compare responses
diff <(curl -s old-proxy/api/test) <(curl -s sentinel/api/test)
```

## See Also

- [Configuration](../../configuration/) - Full configuration reference
- [Troubleshooting](../troubleshooting/) - Common issues
- [Quick Start](../../getting-started/quick-start/) - Getting started guide

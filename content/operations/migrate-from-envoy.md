+++
title = "Migrating from Envoy"
weight = 4
description = "Map an Envoy static configuration to Zentinel listeners, routes, upstreams, filters and agents."
+++

This guide maps an Envoy v3 static configuration (`static_resources`) to Zentinel. Read the [Migration Guide](../migration/) first for the general process: audit, translate, run in parallel, shift traffic gradually.

## Concepts

| Envoy | Zentinel |
|-------|----------|
| Listener + `http_connection_manager` | `listener` with `protocol "http"` or `"https"`. There is no separate connection manager |
| `filter_chains` with `DownstreamTlsContext` | `tls` block on the listener; per-hostname certificates as `sni` blocks |
| `route_config.virtual_hosts` | No equivalent object. Put the virtual host's `domains` into a `host` match on each route |
| Route | `route` with a `matches` block |
| Cluster | `upstream` |
| `load_assignment` endpoints | `target` entries |
| HTTP filters (`ext_authz`, `jwt_authn`, `lua`, `wasm`, …) | [Filters](/configuration/filters/) for built-in behaviour, [agents](/agents/) for external processing |
| xDS (LDS, RDS, CDS, EDS, ADS) | No xDS. Configuration is a KDL file, reloaded on `SIGHUP`; upstream targets can come from [service discovery](/configuration/upstreams/#service-discovery); fleets can use the [Control Plane](/control-plane/) |
| Admin interface | [Metrics](/reference/metrics/) endpoint and `zentinel` CLI |

Two structural differences matter most:

- **Routes are global.** Envoy scopes routes to a listener's route configuration. Zentinel evaluates every route for requests on every listener, unless a listener is assigned a [namespace](/configuration/namespaces/). Host matches do the job of virtual hosts.
- **Routes are ordered by priority, not position.** Envoy takes the first matching route in a virtual host. Zentinel picks the matching route with the highest `priority` and prefers more specific matches when priorities are equal; set `priority` explicitly where order matters. See [Route Evaluation Order](/configuration/routes/#route-evaluation-order).

## Listeners and TLS

**Envoy:**

```yaml
static_resources:
  listeners:
    - name: https
      address:
        socket_address: { address: 0.0.0.0, port_value: 8443 }
      filter_chains:
        - filter_chain_match:
            server_names: ["api.example.com"]
          transport_socket:
            name: envoy.transport_sockets.tls
            typed_config:
              "@type": type.googleapis.com/envoy.extensions.transport_sockets.tls.v3.DownstreamTlsContext
              common_tls_context:
                tls_params:
                  tls_minimum_protocol_version: TLSv1_2
                tls_certificates:
                  - certificate_chain: { filename: /etc/envoy/certs/api.crt }
                    private_key: { filename: /etc/envoy/certs/api.key }
          filters:
            - name: envoy.filters.network.http_connection_manager
              # ...
```

**Zentinel:**

```kdl
system {
    worker-threads 0
}

listeners {
    listener "https" {
        address "0.0.0.0:8443"
        protocol "https"
        tls {
            cert-file "/etc/zentinel/certs/default.crt"
            key-file "/etc/zentinel/certs/default.key"
            min-version "1.2"

            sni {
                hostnames "api.example.com"
                cert-file "/etc/zentinel/certs/api.crt"
                key-file "/etc/zentinel/certs/api.key"
            }
        }
    }
}
```

The certificate in the `tls` block is the default for clients whose SNI matches no `sni` block. TLS listeners offer HTTP/2 and HTTP/1.1 through ALPN; there is no setting to match Envoy's `codec_type`. Zentinel can also obtain certificates itself through [ACME](/configuration/listeners/).

## Routes

**Envoy:**

```yaml
route_config:
  virtual_hosts:
    - name: api
      domains: ["api.example.com"]
      routes:
        - match:
            prefix: "/api/"
            headers:
              - name: x-beta
                string_match: { exact: "true" }
          route: { cluster: api_v2, prefix_rewrite: "/" }
        - match: { prefix: "/api/" }
          route:
            cluster: api
            prefix_rewrite: "/"
            timeout: 30s
            retry_policy:
              retry_on: "5xx"
              num_retries: 2
          request_headers_to_add:
            - header: { key: x-gateway, value: envoy }
          request_headers_to_remove: ["x-internal-debug"]
    - name: www
      domains: ["www.example.com"]
      routes:
        - match: { prefix: "/" }
          redirect: { host_redirect: example.com, https_redirect: true }
```

**Zentinel:**

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

filters {
    filter "strip-api-prefix" {
        type "url-rewrite"
        replace-prefix-match "/"
    }
    filter "api-request-headers" {
        type "headers"
        phase "request"
        set {
            "X-Gateway" "zentinel"
        }
        remove "X-Internal-Debug"
    }
    filter "www-to-apex" {
        type "redirect"
        scheme "https"
        hostname "example.com"
        status-code 301
    }
}

routes {
    route "api-beta" {
        priority 200
        matches {
            host "api.example.com"
            path-prefix "/api/"
            header "x-beta" "true"
        }
        upstream "api-v2"
        filters "strip-api-prefix"
    }
    route "api" {
        priority 100
        matches {
            host "api.example.com"
            path-prefix "/api/"
        }
        upstream "api"
        filters "strip-api-prefix" "api-request-headers"
        policies {
            timeout-secs 30
        }
        retry-policy {
            max-attempts 3
            retryable-status-codes 502 503 504
        }
    }
    route "www" {
        matches {
            host "www.example.com"
        }
        filters "www-to-apex"
    }
}

upstreams {
    upstream "api" {
        target "10.0.0.1:8080"
        target "10.0.0.2:8080"
    }
    upstream "api-v2" {
        target "10.0.1.1:8080"
    }
}
```

All conditions in one `matches` block must hold. To express Envoy's "any of these routes", write one route per alternative.

### Route mapping

| Envoy | Zentinel |
|-------|----------|
| `domains: ["api.example.com"]` | `host "api.example.com"` in `matches` (wildcards such as `"*.example.com"` work) |
| `match.prefix` | `path-prefix` |
| `match.path` | `path` |
| `match.safe_regex` | `path-regex` |
| `headers` with `exact` | `header "name" "value"` |
| `headers` with `present_match` | `header "name"` |
| `headers` with `prefix`, `suffix`, `safe_regex`, `invert_match` | No equivalent |
| `query_parameters` with `exact` | `query-param "name" "value"` |
| `route.cluster` | `upstream` |
| `route.weighted_clusters` | No split between upstreams. If the clusters run the same service, put all endpoints in one upstream with `weight=` on each target |
| `prefix_rewrite` | `url-rewrite` filter with `replace-prefix-match` |
| `regex_rewrite` | No equivalent |
| `host_rewrite_literal` | `url-rewrite` filter with `hostname` |
| `redirect` | `redirect` filter (`scheme`, `hostname`, `port`, `replace-full-path` or `replace-prefix-match`, `status-code`) |
| `direct_response` | No general equivalent; see [built-in handlers](/configuration/routes/#service-types) for health and status endpoints |
| `timeout` | `policies { timeout-secs }`. Zentinel's value bounds each wait for upstream data, not the whole request |
| `retry_policy.num_retries` | `retry-policy { max-attempts }`, which counts the first attempt (`num_retries: 2` is `max-attempts 3`) |
| `retry_policy.retry_on: 5xx` | `retryable-status-codes`; nothing is retried on status unless listed. See [Retry Policy](/configuration/routes/#retry-policy) |
| `request_mirror_policies` | [`shadow`](/configuration/routes/#traffic-mirroring-shadow-traffic) block on the route |
| `request_headers_to_add` / `_to_remove` | `headers` filter with `phase "request"`, or route `policies { request-headers }` |
| `response_headers_to_add` / `_to_remove` | `headers` filter with `phase "response"`, or route `policies { response-headers }` |

## Clusters

**Envoy:**

```yaml
clusters:
  - name: api
    type: STATIC
    connect_timeout: 1s
    lb_policy: LEAST_REQUEST
    load_assignment:
      cluster_name: api
      endpoints:
        - lb_endpoints:
            - endpoint: { address: { socket_address: { address: 10.0.0.1, port_value: 8080 } } }
              load_balancing_weight: 3
            - endpoint: { address: { socket_address: { address: 10.0.0.2, port_value: 8080 } } }
              load_balancing_weight: 1
    health_checks:
      - timeout: 2s
        interval: 10s
        healthy_threshold: 2
        unhealthy_threshold: 3
        http_health_check: { path: /health }
  - name: payments
    type: STRICT_DNS
    lb_policy: ROUND_ROBIN
    load_assignment:
      cluster_name: payments
      endpoints:
        - lb_endpoints:
            - endpoint: { address: { socket_address: { address: payments.internal, port_value: 443 } } }
    transport_socket:
      name: envoy.transport_sockets.tls
      typed_config:
        "@type": type.googleapis.com/envoy.extensions.transport_sockets.tls.v3.UpstreamTlsContext
        sni: payments.internal
```

**Zentinel:**

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
    route "api" {
        matches {
            path-prefix "/api/"
        }
        upstream "api"
    }
    route "payments" {
        matches {
            path-prefix "/payments/"
        }
        upstream "payments"
    }
}

upstreams {
    upstream "api" {
        target "10.0.0.1:8080" weight=3
        target "10.0.0.2:8080" weight=1
        load-balancing "power_of_two_choices"
        timeouts {
            connect-secs 1
        }
        health-check {
            type "http" {
                path "/health"
                expected-status 200
            }
            interval-secs 10
            timeout-secs 2
            healthy-threshold 2
            unhealthy-threshold 3
        }
    }
    upstream "payments" {
        discovery "dns" {
            hostname "payments.internal"
            port 443
            refresh-interval 30
        }
        tls {
            sni "payments.internal"
        }
    }
}
```

### Cluster mapping

| Envoy | Zentinel |
|-------|----------|
| `type: STATIC` endpoints | `target "ip:port"` |
| `type: STRICT_DNS` / `LOGICAL_DNS` | [`discovery "dns"`](/configuration/upstreams/#dns-discovery) |
| EDS | [`discovery "kubernetes"`, `"consul"` or `"file"`](/configuration/upstreams/#service-discovery) |
| `load_balancing_weight` | `weight=` on the target |
| `lb_policy: ROUND_ROBIN` | `load-balancing "round_robin"` (or `"weighted"` when targets have weights) |
| `lb_policy: LEAST_REQUEST` | `load-balancing "power_of_two_choices"`, the same two-random-choices algorithm, or `"least_connections"` |
| `lb_policy: RANDOM` | `load-balancing "random"` |
| `lb_policy: RING_HASH` | `load-balancing "consistent_hash"` |
| `lb_policy: MAGLEV` | `load-balancing "maglev"` |
| `connect_timeout` | `timeouts { connect-secs }` |
| `health_checks` with `http_health_check` | `health-check { type "http" { path expected-status } }` |
| `health_checks` with `grpc_health_check` | `health-check { type "grpc" }` |
| `health_checks` with `tcp_health_check` | `health-check { type "tcp" }` |
| `outlier_detection` | No passive ejection. The upstream [`circuit-breaker`](/configuration/upstreams/#circuit-breaker) stops traffic after consecutive failures, for the whole upstream rather than per host |
| `circuit_breakers.thresholds` (`max_connections`, `max_requests`, …) | No equivalent. Connection pool limits are not enforced in the current release |
| `UpstreamTlsContext` | `tls` block on the upstream (`sni`, client certificate, CA). See [Upstream TLS](/configuration/upstreams/#upstream-tls) |
| `typed_extension_protocol_options` with HTTP/2 | `http-version { min-version 2 }` (TLS upstreams only) |
| `common_http_protocol_options.idle_timeout` | `connection-pool { idle-timeout-secs }` |

A misspelled `load-balancing` value falls back to round robin without an error, so check the spelling against [the list of algorithms](/configuration/upstreams/#algorithms).

## HTTP filters

| Envoy filter | Zentinel |
|--------------|----------|
| `envoy.filters.http.router` | Implicit |
| `local_ratelimit` | [`rate-limit` filter](/configuration/filters/#rate-limiting) |
| `ratelimit` (global, with a rate limit service) | `rate-limit` filter with the Redis or Memcached backend ([distributed rate limiting](/configuration/filters/#distributed-rate-limiting-with-redis)) |
| `ext_authz` | An `auth` [agent](/configuration/agents/). Agents speak the Zentinel agent protocol, not the `ext_authz` gRPC API, so the authorization service needs an agent in front of it or a rewrite |
| `jwt_authn` | The [auth agent](/agents/), which validates JWTs |
| `rbac` | The [policy agent](/agents/) |
| `lua` / `wasm` | The Lua and WASM agents, or a custom agent from an [SDK](/agents/) |
| `compressor` | [`compress` filter](/configuration/filters/#compression-filter) |
| `cors` | [`cors` filter](/configuration/filters/#cors-filter) |
| `fault` | No built-in equivalent |
| `header_to_metadata`, `grpc_json_transcoder`, and other specialised filters | No built-in equivalent; implement as an agent if needed |

{% callout(type="warning", title="CORS filter options") %}
In 26.10_3 the KDL parser does not read the `cors` filter's options: every `cors` filter behaves as its defaults, allowing any origin with credentials disabled. Do not rely on it to restrict origins; set the `Access-Control-*` headers from the application or with a `headers` filter until this is fixed.
{% end %}

## Converting automatically

[`zentinel-convert`](https://github.com/zentinelproxy/zentinel-convert) reads an Envoy v3 static configuration (YAML or JSON) and writes a Zentinel KDL file. Treat its output as a first draft: it is an early tool, and several Envoy features are dropped or translated loosely.

```bash
cargo install --git https://github.com/zentinelproxy/zentinel-convert
zentinel-convert convert --format envoy envoy.yaml -o zentinel.kdl
zentinel-convert analyze --format envoy envoy.yaml   # warnings and agent suggestions only
```

Always pass `--format envoy`: Envoy and Traefik both use YAML, and format detection can pick Traefik. Before using the output, check at least these, which the converter does not carry over:

- Listener TLS: certificate and key paths are not copied, so `tls { }` is empty
- Upstream TLS (`transport_socket` on clusters)
- `weighted_clusters`: only the first cluster is used
- Header matches: `prefix`, `suffix` and regex matches become exact matches; `invert_match` and `query_parameters` are ignored
- `https_redirect`: the redirect keeps the original scheme
- `retry_policy`, `outlier_detection`, and most circuit breaker thresholds
- `cors`, `lua`, `wasm` and other HTTP filters it does not recognise, which it drops without a warning
- Request and response header changes from virtual hosts become a `headers` filter that is not attached to any route

Validate the result with `zentinel test -c zentinel.kdl` and `zentinel lint -c zentinel.kdl`, then compare behaviour against Envoy with real traffic before cutting over.

## See also

- [Migration Guide](../migration/): process, nginx, HAProxy and Traefik
- [Migrating from Caddy](../migrate-from-caddy/)
- [Routes](/configuration/routes/), [Upstreams](/configuration/upstreams/), [Filters](/configuration/filters/)

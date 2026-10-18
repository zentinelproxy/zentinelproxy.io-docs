+++
title = "Migrating from Caddy"
weight = 5
description = "Map a Caddyfile to Zentinel listeners, ACME certificates, routes, upstreams, static files and filters."
+++

This guide maps a Caddyfile to Zentinel. Read the [Migration Guide](../migration/) first for the general process: audit, translate, run in parallel, shift traffic gradually.

## Concepts

| Caddy | Zentinel |
|-------|----------|
| Site block (`example.com { ... }`) | A `host` match on each route. Routes are not grouped by site |
| Site address port / scheme | `listener` blocks, declared explicitly |
| Automatic HTTPS | [ACME](/configuration/listeners/#acme-automatic-certificate-management) on the HTTPS listener, plus a redirect route on the HTTP listener |
| Directives inside a site | Route settings, [filters](/configuration/filters/) and [agents](/agents/) |
| Matchers (`@name`, `/path*`) | The route's `matches` block |
| `handle` / `route` ordering | Route `priority`; the highest-priority matching route wins |
| Snippets and `import` | No macros. Define a filter once and reference it by name from several routes |
| Admin API, `caddy reload` | `SIGHUP` or `systemctl reload zentinel` reloads the file |

The biggest difference is that **Caddy does a lot implicitly** that Zentinel needs spelled out: listening on 80 and 443, obtaining certificates, redirecting HTTP to HTTPS, and choosing directive order. Zentinel does nothing it is not configured to do.

## A typical site

**Caddy:**

```caddyfile
example.com, www.example.com {
    encode gzip zstd

    header Strict-Transport-Security "max-age=31536000; includeSubDomains"

    handle_path /api/* {
        reverse_proxy 10.0.0.1:8080 10.0.0.2:8080 {
            lb_policy least_conn
            health_uri /health
            health_interval 10s
        }
    }

    handle {
        root * /var/www/site
        file_server
    }
}
```

**Zentinel:**

```kdl
system {
    worker-threads 0
}

listeners {
    listener "http" {
        address "0.0.0.0:80"
        protocol "http"
        namespace "plain-http"
    }
    listener "https" {
        address "0.0.0.0:443"
        protocol "https"
        tls {
            acme {
                email "admin@example.com"
                domains "example.com" "www.example.com"
            }
        }
    }
}

// Port 80 only redirects. ACME HTTP-01 challenges are answered
// before routing, so they still work on this listener.
namespace "plain-http" {
    filters {
        filter "to-https" {
            type "redirect"
            scheme "https"
            status-code 308
        }
    }
    routes {
        route "to-https" {
            matches {
                path-prefix "/"
            }
            filters "to-https"
        }
    }
}

filters {
    filter "compress" {
        type "compress"
    }
    filter "hsts" {
        type "headers"
        phase "response"
        set {
            "Strict-Transport-Security" "max-age=31536000; includeSubDomains"
        }
    }
    filter "strip-api" {
        type "url-rewrite"
        replace-prefix-match "/"
    }
}

routes {
    route "api" {
        priority 100
        matches {
            host "example.com"
            path-prefix "/api/"
        }
        upstream "api"
        filters "strip-api" "compress" "hsts"
    }
    route "api-www" {
        priority 100
        matches {
            host "www.example.com"
            path-prefix "/api/"
        }
        upstream "api"
        filters "strip-api" "compress" "hsts"
    }
    route "site" {
        matches {
            path-prefix "/"
        }
        service-type "static"
        static-files {
            root "/var/www/site"
        }
    }
}

upstreams {
    upstream "api" {
        target "10.0.0.1:8080"
        target "10.0.0.2:8080"
        load-balancing "least_connections"
        health-check {
            type "http" {
                path "/health"
                expected-status 200
            }
            interval-secs 10
            timeout-secs 5
            healthy-threshold 2
            unhealthy-threshold 3
        }
    }
}
```

Things to note in this translation:

- **Two listeners and a redirect.** Caddy creates both and redirects automatically. In Zentinel, routes apply to every listener unless the listener has a [namespace](/configuration/namespaces/), so the port-80 listener gets its own namespace containing only the redirect. Without it, the redirect route would also match HTTPS requests and loop.
- **One host per `matches` block.** All conditions in a `matches` block must hold, so two `host` conditions can never both match. Write one route per hostname, or leave `host` out when the listener serves only this site (as the `site` route does).
- **`handle_path` strips the prefix; `path-prefix` does not.** The `url-rewrite` filter with `replace-prefix-match "/"` does the stripping.
- **`file_server` paths.** `static-files` appends the full request path to `root`, as Caddy's `root` + `file_server` does.
- **Static routes answer before response filters run**, so the `compress` and `hsts` filters are attached only to the proxied route. `static-files` compresses on its own (`compress` defaults to on). If static responses need extra headers such as HSTS, serve the files from a small upstream web server instead.

## Directive mapping

| Caddy | Zentinel |
|-------|----------|
| `reverse_proxy <upstreams...>` | `upstream` on the route, with one `target` per upstream address |
| `reverse_proxy` with `https://` upstreams or `transport http { tls }` | `tls` block on the upstream (`sni`, CA, client certificate). See [Upstream TLS](/configuration/upstreams/#upstream-tls) |
| `lb_policy round_robin` | `load-balancing "round_robin"` |
| `lb_policy weighted_round_robin` | `weight=` on targets with `load-balancing "weighted"` |
| `lb_policy least_conn` | `load-balancing "least_connections"` |
| `lb_policy random` | `load-balancing "random"` |
| `lb_policy random_choose 2` | `load-balancing "power_of_two_choices"` |
| `lb_policy ip_hash` / `client_ip_hash` | `load-balancing "ip_hash"` |
| `lb_policy cookie` | `load-balancing "sticky" { cookie-name "..." }` |
| `lb_policy first` | No equivalent |
| `health_uri`, `health_interval`, `health_timeout`, `health_status` | `health-check { type "http" { path expected-status } interval-secs timeout-secs }` |
| `fail_duration`, `max_fails` (passive health) | No per-target passive health. The upstream [`circuit-breaker`](/configuration/upstreams/#circuit-breaker) stops traffic after consecutive failures |
| `dial_timeout` | `timeouts { connect-secs }` on the upstream |
| `header_up` | `headers` filter with `phase "request"`, or route `policies { request-headers }` |
| `header_down` | `headers` filter with `phase "response"`, or route `policies { response-headers }` |
| `handle`, `route` | Separate routes, ordered with `priority` |
| `handle_path /prefix/*` | `path-prefix "/prefix/"` plus a `url-rewrite` filter with `replace-prefix-match "/"` |
| `uri strip_prefix` | `url-rewrite` filter with `replace-prefix-match` |
| `rewrite <to>` | `url-rewrite` filter with `replace-full-path` (static replacement only; no placeholders) |
| `redir <to> [code]` | `redirect` filter (`scheme`, `hostname`, `port`, `replace-full-path`, `status-code`) |
| `root` + `file_server` | Route with `service-type "static"` and `static-files { root }`. `browse` is `directory-listing #true` |
| `try_files {path} /index.html` | `static-files { fallback "index.html" }` for single-page apps |
| `encode gzip zstd` | `compress` filter. The encoding follows the client's `Accept-Encoding` |
| `header` | `headers` filter with `phase "response"` |
| `request_header` | `headers` filter with `phase "request"` |
| `respond` | No general equivalent; see [built-in handlers](/configuration/routes/#service-types) for health and status endpoints |
| `basicauth` / `basic_auth` | The [auth agent](/agents/) |
| `forward_auth` | An `auth` [agent](/configuration/agents/) in front of your authorization service |
| `rate_limit` (plugin) | [`rate-limit` filter](/configuration/filters/#rate-limiting) |
| `tls internal` | No internal CA. Use certificates from your own CA with `cert-file` / `key-file` |
| `tls cert.pem key.pem` | `tls { cert-file key-file }` on the listener |
| `tls { dns cloudflare ... }` | ACME with `challenge-type "dns-01"` and a [DNS provider](/configuration/listeners/#dns-01-challenge-for-wildcard-certificates) |
| `log` | [Access logs](/configuration/observability/) |
| `php_fastcgi` | No FastCGI support. Run PHP behind an HTTP server (for example PHP-FPM behind a small nginx or FrankenPHP) and proxy to it |
| `metrics` | [Prometheus metrics](/reference/metrics/) are built in |

## Converting automatically

[`zentinel-convert`](https://github.com/zentinelproxy/zentinel-convert) reads a Caddyfile (not Caddy's JSON configuration) and writes a Zentinel KDL file. Treat the output as a first draft: it is an early tool, and much of a typical Caddyfile is translated loosely or not at all.

```bash
cargo install --git https://github.com/zentinelproxy/zentinel-convert
zentinel-convert convert --format caddy Caddyfile -o zentinel.kdl
zentinel-convert analyze --format caddy Caddyfile   # warnings and agent suggestions only
```

Check at least these in the output:

- No ACME, no port-80 listener and no HTTP-to-HTTPS redirect are generated; HTTPS listeners get an empty `tls { }`
- `handle_path` does not strip the prefix, and `handle /path` loses its path
- `reverse_proxy /path/* ...` does not use the path as a matcher
- Single-line named matchers (`@name path /x/*`) are not recognised; the block form `@name { ... }` is
- `redir` ignores `permanent` and matchers placed after the directive name
- `header` blocks with several headers produce nothing
- `basicauth` credentials are not carried over
- `lb_policy` values other than `round_robin`, `least_conn`, `ip_hash` and `random` become round robin
- `route`, `rewrite`, `uri`, `try_files`, `php_fastcgi` and a site-level `root` are reported as unhandled

Validate the result with `zentinel test -c zentinel.kdl` and `zentinel lint -c zentinel.kdl`, then compare behaviour against Caddy with real traffic before cutting over.

## See also

- [Migration Guide](../migration/): process, nginx, HAProxy and Traefik
- [Migrating from Envoy](../migrate-from-envoy/)
- [Listeners](/configuration/listeners/) (TLS and ACME), [Routes](/configuration/routes/), [Filters](/configuration/filters/)
- [Static Site example](/examples/static-site/)

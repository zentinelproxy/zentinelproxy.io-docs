+++
title = "Limits"
weight = 6
updated = 2026-10-19
+++

The `limits` block bounds the size of requests. This page describes what a
single configuration file (`zentinel -c zentinel.kdl`) reads, which is the only
form the `zentinel` command can load
([#541](https://github.com/zentinelproxy/zentinel/issues/541)).

{% callout(type="warning", title="Six keys, no -bytes suffix") %}
A `limits` block in a configuration file reads exactly these keys:
`max-header-size`, `max-header-count`, `max-body-size`,
`max-connections-per-client`, `max-total-connections` and
`max-in-flight-requests`. The `-bytes` spellings (`max-body-size-bytes`,
`max-header-size-bytes`) and every other key once listed here
(`max-header-value-bytes`, `max-decompression-ratio`,
`max-requests-per-second-*`, `max-agent-*`, `max-memory-bytes`, ...) belong to
the directory-configuration parser and are ignored. From 26.10_5,
`zentinel test` and `zentinel lint` report them as "is being ignored", with
"Did you mean 'max-body-size'?" for the `-bytes` names. Before 26.10_5 nothing
reported them, so a limit written with `-bytes` silently ran at the default.
{% end %}

## Basic Configuration

```kdl
limits {
    max-header-size 8192         // total size of all request headers, bytes
    max-header-count 100         // number of request headers
    max-body-size 10485760       // request body, bytes (10 MiB)
}
```

| Setting | Default | Applied |
|---------|---------|---------|
| `max-header-size` | `8192` | Yes |
| `max-header-count` | `100` | Yes |
| `max-body-size` | `10485760` (10 MiB) | Yes; see [Body Limits](#body-limits) |
| `max-connections-per-client` | `100` | **No**, see [Connection Limits](#connection-limits) |
| `max-total-connections` | `10000` | **No** |
| `max-in-flight-requests` | `10000` | **No** |

The same six keys are accepted in a namespace's or service's `limits` block,
but the proxy does not apply namespace and service limits
([#542](https://github.com/zentinelproxy/zentinel/issues/542)).

## Header Limits

```kdl
limits {
    max-header-size 8192    // sum of header name and value lengths
    max-header-count 100
}
```

Both are checked after the request is matched to a route, before agents run and
before an upstream is contacted. A value of 1 MiB (`1048576`) or more turns the
check off. A request over either limit is refused and counted in
`zentinel_blocked_requests_total` with `reason="header_size_exceeded"` or
`reason="header_count_exceeded"`.

**Security note:** Large header limits can be exploited for denial-of-service.
Keep the defaults unless you have specific requirements.

| Environment | `max-header-size` | `max-header-count` |
|-------------|-------------------|--------------------|
| Production | 4096-8192 | 50-100 |
| Development | 16384 | 200 |
| API Gateway | 8192 | 100 |

## Body Limits

The global `max-body-size` and a route's `policies { max-body-size }` both
apply. The effective limit for a request is the **smaller** of the two.

```kdl
limits {
    max-body-size 104857600     // 100 MiB: the largest body any route accepts
}

routes {
    route "upload" {
        matches {
            path-prefix "/upload/"
        }
        upstream "storage"
        policies {
            max-body-size "100MB"
        }
    }

    route "api" {
        matches {
            path-prefix "/api/"
        }
        upstream "backend"
        policies {
            max-body-size "1MB"
        }
    }
}
```

A route cannot raise the limit above the global one: with the default global
limit of 10 MiB, `max-body-size "100MB"` on a route still refuses bodies over
10 MiB. Set the global limit to the largest body any route needs, and lower it
per route. The route value accepts a plain byte count or a size such as
`"512KB"` or `"1MB"`.

A request over the limit gets **`413 Payload Too Large`**:

- a declared `Content-Length` over the limit is refused before the body is read
  and before any upstream is contacted;
- a chunked body is counted as it streams and refused when it crosses the limit;
- on routes that read the whole body first (API schema validation), the same
  limit applies to that read.

Refused bodies count in `zentinel_blocked_requests_total` with
`reason="body_size_exceeded"`. They are client errors: they do not count
against the upstream's circuit breaker.

**Before 26.10_5:** a route's `max-body-size` was not enforced; a body over the
global limit got `500 Internal Server Error`, and three such requests could open
the circuit breaker of a healthy upstream; and in a single file a
`max-body-size` below 1 MiB failed validation (`max_body_buffer_bytes cannot
exceed max_body_size_bytes`). From 26.10_5 any value loads.

| Use Case | Recommended Size |
|----------|------------------|
| API endpoints | 1-10 MB |
| File uploads | 100 MB - 1 GB |
| JSON APIs | 1-5 MB |
| Form submissions | 1-10 MB |

The size of request bodies sent to an agent is set on the agent, with
`max-request-body-bytes`; see [Agents](../agents/).

## Connection Limits

`max-connections-per-client`, `max-total-connections` and
`max-in-flight-requests` are read and range-checked, but nothing in the proxy
applies them: Zentinel does not limit client connections or concurrent requests
([#542](https://github.com/zentinelproxy/zentinel/issues/542)). Bound load
with [rate limits](../filters/#rate-limiting), and cap connections in front of
the proxy (a load balancer) or with the operating system's file descriptor
limit:

```bash
ulimit -n                  # Current soft limit
cat /proc/sys/fs/file-max  # System limit
```

## Rate Limiting

Rate limits are not set in `limits`. Use a `rate-limit` filter on a route, or
the top-level `rate-limits` block for a default and a server-wide limit; see
[Filters: Rate Limiting](../filters/#rate-limiting). Both are token buckets:
`burst` is the bucket size and `max-rps` the refill rate.

The `max-requests-per-second-global`, `-per-client` and `-per-route` keys are
read only from directory configurations. Earlier versions of this page said
their bucket held ten times the per-second limit; it holds one second's worth
(1×), and namespace and service limits are not applied at all
([#542](https://github.com/zentinelproxy/zentinel/issues/542)).

## Memory Limits

There is no memory limit. `max-memory-bytes` and `max-memory-percent` are not
read from a configuration file, and nothing in the proxy would enforce them.
Bound memory with the process supervisor (for example systemd `MemoryMax=` or a
container memory limit).

## Profile Presets

### Development

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

limits {
    // Permissive for testing
    max-header-size 16384
    max-header-count 200
    max-body-size 104857600  // 100 MiB
}

routes {
    route "default" {
        matches { path-prefix "/" }
        upstream "backend"
    }
}

upstreams {
    upstream "backend" {
        target "127.0.0.1:3000"
    }
}
```

### Production (Conservative)

```kdl
limits {
    max-header-size 4096
    max-header-count 50
    max-body-size 1048576  // 1 MiB
}

filters {
    filter "per-client" {
        type "rate-limit"
        max-rps 100
        burst 100
        key "client-ip"
    }
}
```

### High-Traffic API

```kdl
limits {
    max-header-size 8192
    max-header-count 100
    max-body-size 10485760  // 10 MiB
}

rate-limits {
    global {
        max-rps 1000      // per client
        burst 1000
        key "client-ip"
    }
}
```

## Bounds Outside the `limits` Block

The `limits` block above bounds individual requests and connections. Several
other resource bounds live elsewhere in the config — in `system`, in an
upstream's `connection-pool`, and on each agent. They are easy to overlook
precisely because they are not in `limits`, and they are the ones that decide
how the proxy behaves when it runs out of something.

```kdl
system {
    route-cache-size 1000
}

upstreams {
    upstream "backend" {
        target "10.0.0.1:8080"
        connection-pool {
            max-connections 100
            max-idle 20
        }
    }
}

agents {
    agent "waf" {
        unix-socket "/var/run/zentinel/waf.sock"
        max-concurrent-calls 100
    }
}
```

| Setting | Block | Default | Bounds |
|---------|-------|---------|--------|
| `route-cache-size` | `system` | `1000` | Cached route-match entries |
| `max-connections` | `connection-pool` | `100` | Connections per upstream target |
| `max-idle` | `connection-pool` | `20` | Idle connections kept per target |
| `max-concurrent-calls` | `agent` | `100` | In-flight calls to one agent |

`system { max-connections }` is not in this list: Zentinel does not limit
client connections, and from 26.10_5 `zentinel test` and `lint` report the key
as not applied.

**A `0` here means unbounded, not disabled.** A `connection-pool` with
`max-connections 0` accumulates connections against a slow upstream until the process runs out of
them. If you want a component effectively off, give it a small number rather
than zero.

**`max-idle` above `max-connections` is unreachable.** The idle bound is capped
by the total, so the larger number silently has no effect.

## Checking Bounds with `zentinel lint`

`zentinel lint` inspects a config for bounds that are missing, unreachable, or
so generous they are indistinguishable from unbounded:

```bash
zentinel lint --config /etc/zentinel/zentinel.kdl
```

It reports, among other things:

| Condition | Why it is flagged |
|-----------|-------------------|
| `route-cache-size` above `1000000` | Entries are keyed by method, host, path and any matched headers or query parameters, so a large cache on varied traffic holds a lot of memory for little hit rate |
| pool `max-connections` is `0` | The pool is unbounded against a slow upstream |
| pool `max-connections` above `10000` | More than most origins accept; the real limit becomes the origin's, and it surfaces as errors rather than backpressure |
| pool `max-idle` above `max-connections` | The idle bound can never be reached |
| `max-concurrent-calls` is `0` | Unbounded in-flight calls to a single agent |
| `max-concurrent-calls` above `10000` | Far past what an agent process will service |
| route `max-body-size` above 128 MB | With buffering that is held in memory per concurrent request |

These are warnings, not errors — a config that trips them still starts. They
mark places where behaviour under load will not match what the file appears to
say.

### Keys no parser reads

`zentinel lint` also reports settings inside a known block that nothing reads:

```
⚠  'failure_mode' is not a setting in the 'policies' block and is being
   ignored. Did you mean 'failure-mode'?
⚠  'connect-seconds' is not a setting in the 'timeouts' block and is being
   ignored. Did you mean 'connect-secs'?
```

KDL accepts any key inside a block, so a misspelling produces no parse error —
the setting is simply discarded, and the proxy runs on the default while your
config file says otherwise. That is how `ratelimit` (missing a hyphen) can
silently disable rate limiting on a route.

Checked blocks are those with a fixed set of valid keys, `limits` among them.
Blocks that legitimately hold
arbitrary keys — a JSON schema's properties, header maps — are not inspected,
so this check stays quiet on valid configuration.

Settings inside `mcp` and `a2a` blocks go further and are refused at load time
rather than warned about, since a discarded key in a security policy is not
something to discover later. See [Agentic Protocols](../agentic/).

**Run it in CI.** The failure these catch shows up under load, which is the
worst time to find out. From 26.10_5, `zentinel test` also prints the "is
being ignored" warnings, and `zentinel test --strict` fails on them; the bounds
checks in the table above are reported only by `zentinel lint`.

## Default Values Summary

| Setting | Default | Applied |
|---------|---------|---------|
| `max-header-size` | 8192 | Yes |
| `max-header-count` | 100 | Yes |
| `max-body-size` | 10485760 (10 MiB) | Yes |
| `max-connections-per-client` | 100 | No |
| `max-total-connections` | 10000 | No |
| `max-in-flight-requests` | 10000 | No |
| Rate limits | None | See [Filters](../filters/#rate-limiting) |
| Memory limit | None | No such setting |

## Monitoring Limits

Requests refused by a limit are counted in `zentinel_blocked_requests_total`,
labelled by `reason`: `header_size_exceeded`, `header_count_exceeded`,
`body_size_exceeded` and, for rate limits, `rate_limited`. Each refusal is
also logged at `WARN` with the trace ID, the limit and the actual value, for
example `Request body size limit exceeded`.

## Troubleshooting

### 413 Payload Too Large

The request body exceeds the effective limit, the smaller of the global
`limits { max-body-size }` and the route's `policies { max-body-size }`:

```bash
grep -n max-body-size zentinel.kdl
```

Raise the global limit to the largest body you accept, then set lower limits
per route. Before 26.10_5, an over-limit body got `500` instead of `413`.

### 429 Too Many Requests

A rate limit refused the request. `Retry-After` says when the next token is
available:

```bash
curl -I https://api.example.com/endpoint
# Retry-After: 1
```

Raise `max-rps` or `burst` on the filter, or throttle the client.

## Next Steps

- [Server Configuration](../server/) - Worker threads and global settings
- [Upstreams](../upstreams/) - Connection pool settings

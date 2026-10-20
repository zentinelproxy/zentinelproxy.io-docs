+++
title = "Performance Tuning"
weight = 9
description = "Which proxy settings affect throughput and latency, what they do, and when to change them."
+++

Zentinel's defaults suit most deployments. Change a setting only when a measurement points at it: use the [metrics](/reference/metrics/) and a [load test](/development/load-testing/) before and after each change, and change one thing at a time.

This page covers only settings the proxy acts on. Some keys are accepted by the parser but have no effect at runtime yet; they are listed under [Settings with no effect](#settings-with-no-effect) so you don't spend time tuning them.

## Worker threads

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
```

| Key | Default | Effect |
|-----|---------|--------|
| `worker-threads` | `0` | Number of Pingora worker threads. `0` uses the number of logical CPUs the process sees. Work stealing between threads is always on |

**When to change it:**

- **Containers with CPU limits.** Set `worker-threads` to match the CPU limit (rounded up), so the thread count does not depend on how the runtime reports CPUs.
- **Hosts shared with agents or other services.** Leave some cores free. Agents run in separate processes and compete for the same CPUs, especially CPU-heavy ones such as WAF engines.
- **Dedicated hosts.** Keep `0`.

More threads than cores adds context switching and does not add throughput.

## Downstream connections

These settings apply to client connections and are set per listener.

```kdl
system {
    worker-threads 0
}

listeners {
    listener "https" {
        address "0.0.0.0:443"
        protocol "https"
        request-timeout-secs 60
        keepalive-timeout-secs 75
        keepalive-max-requests 1000
        tls {
            cert-file "/etc/zentinel/certs/server.crt"
            key-file "/etc/zentinel/certs/server.key"
        }
    }
}
```

| Key | Default | Effect |
|-----|---------|--------|
| `keepalive-timeout-secs` | `75` | How long an idle client connection is kept open between requests |
| `keepalive-max-requests` | unlimited | Requests served on one client connection before it is closed. Applies to all listeners: the smallest value set on any listener wins |
| `request-timeout-secs` | `60` | Read timeout on the client connection, applied once the request headers have been read. It limits the gap between reads, not the total time to receive a request |

**When to change them:**

- **Behind a load balancer** that keeps connections open (AWS ALB, Google Cloud LB, HAProxy), set `keepalive-timeout-secs` *higher* than the load balancer's idle timeout. If Zentinel closes first, the load balancer can send a request on a connection that is being closed and return a 502.
- **Many short-lived clients** (public traffic, mobile): lower `keepalive-timeout-secs` (for example 15–30) to free idle connections sooner.
- **Rebalancing long-lived clients**: set `keepalive-max-requests` so that clients reconnect from time to time and spread across instances after a scale-out.
- **Slow uploads**: raise `request-timeout-secs` if clients stall between chunks for longer than the default.

### HTTP/2 to clients

TLS listeners (`protocol "https"` or `"h2"`) advertise `h2` and `http/1.1` through ALPN, so HTTP/2-capable clients use HTTP/2 without further configuration. Plaintext HTTP/2 (h2c) is not supported on listeners. HTTP/2 stream limits cannot be configured.

## Upstream connections

### Connection reuse

Zentinel keeps idle upstream connections in a pool and reuses them for later requests to the same target. This avoids a TCP (and TLS) handshake per request, which is usually the largest single latency saving available.

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
    route "default" {
        matches {
            path-prefix "/"
        }
        upstream "backend"
    }
}

upstreams {
    upstream "backend" {
        target "10.0.1.1:8080"
        target "10.0.1.2:8080"
        connection-pool {
            idle-timeout-secs 60
        }
    }
}
```

| Key | Default | Effect |
|-----|---------|--------|
| `connection-pool { idle-timeout-secs }` | `60` | How long an idle upstream connection stays in the pool |

The pool holds up to 256 idle connections in total, and upstream TCP keepalive probes are sent after 60 seconds of idleness (every 10 seconds, 3 probes). Neither is configurable.

**When to change it:** keep `idle-timeout-secs` *below* the backend's own keep-alive timeout (for example, Node.js defaults to 5 seconds, nginx to 75, Gunicorn to 2). If the backend closes an idle connection first, the next request that picks it from the pool fails and has to be retried. For backends with very short keep-alive timeouts, either raise the backend's timeout or lower `idle-timeout-secs` to match.

### Timeouts

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
    route "reports" {
        matches {
            path-prefix "/reports/"
        }
        upstream "backend"
        policies {
            timeout-secs 120
        }
    }
    route "default" {
        matches {
            path-prefix "/"
        }
        upstream "backend"
    }
}

upstreams {
    upstream "backend" {
        target "10.0.1.1:8080"
        timeouts {
            connect-secs 2
            read-secs 30
            write-secs 30
        }
    }
}
```

| Key | Default | Effect |
|-----|---------|--------|
| `timeouts { connect-secs }` | `10` | TCP connect timeout. Connect plus TLS handshake is additionally capped at 10 seconds in total |
| `timeouts { read-secs }` | `30` | Maximum wait for data from the upstream, per read |
| `timeouts { write-secs }` | `30` | Maximum wait when sending to the upstream, per write |
| route `policies { timeout-secs }` | unset | Overrides `read-secs` for one route |

**When to change them:**

- **Lower `connect-secs`** (1–3 seconds) for backends on the same network. A dead target then fails fast and a [retry policy](/configuration/routes/) can try another target, instead of the client waiting 10 seconds.
- **Raise the read timeout per route**, not per upstream, for slow endpoints such as report generation or LLM inference, so that a hung request elsewhere is still cut off quickly.
- Streaming responses (server-sent events, long polling) need a read timeout longer than the longest gap between events.

### HTTP/2 to upstreams

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
    route "default" {
        matches {
            path-prefix "/"
        }
        upstream "grpc-backend"
    }
}

upstreams {
    upstream "grpc-backend" {
        target "10.0.2.1:443"
        tls {
            sni "grpc.internal"
        }
        http-version {
            min-version 2
            max-version 2
            h2-ping-interval 30
        }
    }
}
```

| Key | Default | Effect |
|-----|---------|--------|
| `http-version { min-version }` | `1` | With `max-version`, selects the ALPN protocols offered to TLS upstreams |
| `http-version { max-version }` | `2` | `1`/`2`: offer `h2` and `http/1.1`. `2`/`2`: require HTTP/2. `1`/`1`: HTTP/1.1 only |
| `http-version { h2-ping-interval }` | `0` (off) | Seconds between HTTP/2 PING frames on idle upstream connections |

HTTP/2 to upstreams only works over TLS: an upstream without a `tls` block is always spoken to over HTTP/1.1. With the defaults, a TLS upstream that supports HTTP/2 is used over HTTP/2.

**When to change them:**

- **gRPC backends**: set `min-version 2` so that a backend which does not negotiate HTTP/2 fails clearly instead of being spoken to over HTTP/1.1.
- **Backends with HTTP/2 bugs or per-connection limits**: set `max-version 1`.
- **Long-lived HTTP/2 connections through NAT or firewalls** that drop idle flows: set `h2-ping-interval` below their idle timeout.

## Request limits

The `limits` block bounds request headers and bodies. Header limits are checked before the request is sent upstream. From 26.10_5, a body whose `Content-Length` is over the limit is refused before any of it is read or an upstream is contacted; a chunked body is counted as it streams through, so part of an oversized chunked body may already have been forwarded when the request is cut off. A route's `policies { max-body-size }` can lower the limit for that route. Rejections are counted in `zentinel_blocked_requests_total` with the reason `header_count_exceeded`, `header_size_exceeded`, or `body_size_exceeded`.

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
    max-header-size 16384
    max-header-count 100
    max-body-size 52428800
}
```

| Key | Default | Effect |
|-----|---------|--------|
| `max-header-size` | `8192` | Total bytes of all request header names and values. Values of 1 MiB or more disable the check |
| `max-header-count` | `100` | Number of request headers. Values of 1,048,576 or more disable the check |
| `max-body-size` | `10485760` (10 MiB) | Request body bytes, counted as the body streams through |

{% callout(type="warning", title="Key names and status codes") %}
Use the key names shown above. The spellings `max-header-size-bytes` and `max-body-size-bytes` are not read and leave the defaults in place; from 26.10_5 `zentinel test` and `zentinel lint` report them. From 26.10_5 a body over the limit gets `413 Payload Too Large` (before: `500`); a request over a header limit still gets `500` rather than `431`.
{% end %}

**When to change them:**

- **Large cookies or JWTs** in headers: raise `max-header-size`. 16–32 KiB covers most single-sign-on setups.
- **File uploads**: raise `max-body-size` to the largest upload you accept. Bodies are streamed to the upstream, so a higher limit does not by itself increase memory use; agents that inspect bodies have their own size limits (see [Body Processing](/configuration/agents/#body-processing)).
- **APIs that only take small JSON bodies**: lower `max-body-size` to reject oversized requests early.

## Compression

A `compress` filter enables response compression for eligible responses, using the encoding the client accepts, at a fixed level of 6. The only setting that changes its behaviour is `min-size`: responses smaller than that are sent uncompressed, because the framing overhead outweighs the saving. The default is 1024 bytes. See [Compression Filter](/configuration/filters/#compression-filter).

Compression costs CPU on every eligible response. If CPU is the bottleneck and clients are on fast networks, apply the filter only on routes that serve large text responses.

## Route matching cache

| Key | Default | Effect |
|-----|---------|--------|
| `system { route-cache-size }` | `1000` | Number of recent request-to-route matches that are cached |

Raise it for configurations with many routes and a large set of distinct request paths that repeat (for example, a few thousand hot API paths).

## Settings with no effect

The parser accepts these keys, but the proxy does not act on them in the current release. Setting them changes nothing.

| Key | Note |
|-----|------|
| `system { max-connections }` | Not applied. From 26.10_6 cap client connections with `limits { max-total-connections }` |
| listener `max-concurrent-streams` | HTTP/2 stream limits are not configurable |
| `connection-pool { max-connections max-idle max-lifetime-secs }` | Pool size is fixed and connections have no maximum lifetime |
| `timeouts { request-secs }` | There is no total-request deadline; use read timeouts |
| `http-version { max-h2-streams }` | Not applied to upstream connections |
| `compress` filter `level` and `algorithms` | The level is fixed at 6 and the encoding follows the client's `Accept-Encoding` |

`system { daemon }` and route `policies { max-body-size }` had no effect before
26.10_5; from 26.10_5 both are applied. `limits { max-connections-per-client
max-total-connections max-in-flight-requests }` had no effect before 26.10_6;
from 26.10_6 they are enforced (see [Limits](/configuration/limits/#concurrency-limits)).

## See also

- [Capacity Planning](../capacity-planning/)
- [Upstreams](/configuration/upstreams/)
- [Listeners](/configuration/listeners/)
- [Limits](/configuration/limits/)
- [Metrics Reference](/reference/metrics/)

+++
title = "Known Limitations"
weight = 6
description = "Settings Zentinel accepts but does not apply, and behaviour that differs from what the configuration suggests"
updated = 2026-10-20
+++

This page lists what release **26.10_6** accepts in a configuration but does not
apply, and where its behaviour differs from what you would reasonably expect.
Each entry links the tracking issue where there is one, and gives a workaround
where one exists. Entries are removed when a release fixes them; the
[Changelog](/appendix/changelog/) says when.

Two habits catch most of these early:

- Run `zentinel test --strict -c FILE` (or `-c DIR`) before every deploy or
  reload. It fails
  on settings that are misspelled, in the wrong block, or not applied; plain
  `zentinel test` prints them as warnings, and `zentinel lint` adds
  best-practice advice.
- After starting the proxy, read the `WARN` lines it logs at startup. Several of
  the cases below are logged there and nowhere else.

## Checking a configuration

**An include "diamond" is rejected.** Two files that both include the same
third file fail to load with a circular-include error, although nothing is
circular. [#553](https://github.com/zentinelproxy/zentinel/issues/553).
*Workaround:* include the shared file from one place only.

**The top-level `cache` block reads `max-size` and `lock-timeout`.** The
spellings `max-size-bytes` and `lock-timeout-secs` in that block are ignored,
and `zentinel test` does not report them yet.
[#553](https://github.com/zentinelproxy/zentinel/issues/553).
*Workaround:* use the names on [Cache](/configuration/cache/).

**No environment variable substitution.** `${VAR}` is kept as literal text.
`zentinel test` rejects it in a listener address, an upstream target and the
metrics address; elsewhere it is used as written.
*Workaround:* render the file before starting the proxy, for example with
`envsubst`.

**`./zentinel.kdl` is not picked up automatically.** Without `-c` or
`ZENTINEL_CONFIG`, the proxy starts with its embedded default configuration
(listening on `0.0.0.0`), whatever files are in the working directory.
*Workaround:* always pass `-c`.

## Requests and responses

**A request over a header limit gets `500`**, not `431`. See
[Limits](/configuration/limits/#header-limits).

## Agents

**The agent filter's `inspect-body` and `max-body-bytes` are not applied.**
They are parsed and not read at request time, and `zentinel test` does not
report them yet. [#553](https://github.com/zentinelproxy/zentinel/issues/553).
*Workaround:* control body inspection on the agent block, with `events` and
`max-request-body-bytes`.

## Rate limiting

**Release binaries limit per instance with `backend "redis"` or
`"memcached"`.** The official release binaries and container images are built
without the distributed rate-limit features, so these backends fall back to a
local bucket on each instance; the proxy logs a warning when it builds the
limiter. *Workaround:* build from source with
`--features distributed-rate-limit`. See
[Filters: Distributed Rate Limiting](/configuration/filters/#distributed-rate-limiting).

## Upstreams and health checks

**Host-name targets without a health check use only the first resolved
address.** There is no fallback to the other addresses, so a `localhost` target
that resolves to `::1` first fails against an IPv4-only backend. The name is
also resolved with a blocking lookup on the request path, which holds a worker
thread for the duration of each DNS query.
[#554](https://github.com/zentinelproxy/zentinel/issues/554).
*Workaround:* configure a `health-check` on the upstream (the proxy then dials
the first healthy address), use IP addresses, or use `discovery "dns"`.

## Namespaces

**Namespaces are only partly wired.** Routes inside a `service` are never
served, on any listener. A namespace's own routes are served only on a listener
bound to it with `namespace "<id>"`, and a route there that uses a
namespace-local upstream gets `500 "Upstream pool not found"`; only global
upstreams work. Scoped route matching and scoped rate limits are built but not
used on the request path.
[#548](https://github.com/zentinelproxy/zentinel/issues/548).
*Workaround:* define upstreams globally, bind a listener to each namespace, and
put service routes in the namespace. See [Namespaces](/configuration/namespaces/).

## Listeners and TLS

**HTTP/3 is not implemented.** A listener with `protocol "h3"` is rejected at
validation. An `https` listener serves HTTP/1.1 and HTTP/2 (through ALPN).

**`max-concurrent-streams` on a listener is not applied.** The proxy logs an
"Unwired feature" warning at startup. See
[Listeners](/configuration/listeners/).


## Process, logging and resource limits

**`logging { level format }` does not change the proxy's output.** The log goes
to stdout/stderr as plain text at `info`, or `debug` with `--verbose`. A value
other than `"info"`/`"json"` produces an "Unwired feature" warning. The
`ZENTINEL_LOG_FORMAT` environment variable has no effect on the proxy either.
*Workaround:* set `RUST_LOG` (for example `RUST_LOG=warn`). See
[Observability](/configuration/observability/).

**`system { max-connections }` is not applied.** `zentinel test` and `lint`
report it. Cap client connections with `limits { max-total-connections }`
(enforced from 26.10_6). More settings of this kind are in
[Performance Tuning: Settings with no effect](/operations/performance-tuning/#settings-with-no-effect).

**With `auto-reload`, one edit can trigger two reloads**, one from the file
watcher and one from the poll fallback. Both load the same configuration. For a
single-file configuration the poll fallback only watches the entry file, so a
change to an included file is missed when the watcher misses it.
[#553](https://github.com/zentinelproxy/zentinel/issues/553).
*Workaround:* send `SIGHUP` after changing an included file if a reload does
not appear in the log.

## Documented elsewhere

These are described on the page for the feature:

| Limitation | Where |
|------------|-------|
| The top-level `waf` block is not wired into the proxy; any `mode` but `"off"` is rejected | [WAF](/configuration/waf/) |
| `reverse-listener` (agents dialing in) is not read from KDL | [Reverse Connections](/agents/v2/reverse-connections/) |
| `mime-types` for static files is not configurable | [Directive Index](/reference/directives/#mime-types) |
| Compress filter `content-types` is not configurable | [Directive Index](/reference/directives/#content-types) |
| CORS filter settings are not read; the filter uses defaults | [Directive Index](/reference/directives/) |
| Target `max-requests` and `metadata` are ignored | [Upstreams](/configuration/upstreams/) |
| Locality-aware fallback strategy is not configurable | [Upstreams](/configuration/upstreams/#locality-aware) |
| `max-memory-percent` is not implemented | [Limits](/configuration/limits/) |
| Cache `backend "hybrid"` falls back to memory ([#90](https://github.com/zentinelproxy/zentinel/issues/90)) | [Cache](/configuration/cache/) |
| WebSocket ping interval/timeout and maximum message size are not configurable ([#369](https://github.com/zentinelproxy/zentinel/issues/369)) | [WebSocket example](/examples/websocket/) |
| Upstream connection draining and slow start are not configurable | [Load Balancer example](/examples/load-balancer/#connection-draining-and-slow-start) |
| Request hedging is not configurable | [Mixed Services example](/examples/mixed-services/#request-hedging) |
| Agent connect timeouts and retries are not configurable | [Deployment Architecture](/deployment/architecture/) |
| Connection pool, `timeouts { request-secs }`, `http-version { max-h2-streams }` and other parsed-only keys | [Performance Tuning](/operations/performance-tuning/#settings-with-no-effect) |

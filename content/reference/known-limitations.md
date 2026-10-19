+++
title = "Known Limitations"
weight = 6
description = "Settings Zentinel accepts but does not apply, and behaviour that differs from what the configuration suggests"
updated = 2026-10-19
+++

This page lists what release **26.10_5** accepts in a configuration but does not
apply, and where its behaviour differs from what you would reasonably expect.
Each entry links the tracking issue where there is one, and gives a workaround
where one exists. Entries are removed when a release fixes them; the
[Changelog](/appendix/changelog/) says when.

Two habits catch most of these early:

- Run `zentinel test --strict -c FILE` before every deploy or reload. It fails
  on settings that are misspelled, in the wrong block, or not applied; plain
  `zentinel test` prints them as warnings, and `zentinel lint` adds
  best-practice advice.
- After starting the proxy, read the `WARN` lines it logs at startup. Several of
  the cases below are logged there and nowhere else.

## Checking a configuration

**Directory configurations cannot be loaded.** `zentinel -c <dir>` and
`zentinel test -c <dir>` fail with "Is a directory": the multi-file loader is
not reachable from the command line, and neither are the settings only it reads
(the `-bytes` `limits` names, `max-requests-per-second-*`, `max-memory-bytes`,
...). [#541](https://github.com/zentinelproxy/zentinel/issues/541).
*Workaround:* use a single configuration file. See
[Limits](/configuration/limits/) for the keys it reads.

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

**Error pages cannot be configured.** No parser reads `error-pages`, so there
are no templates and no per-status pages. What clients receive for each kind of
error is listed under [Error Pages](/configuration/routes/#error-pages).
[#542](https://github.com/zentinelproxy/zentinel/issues/542).

**A request over a header limit gets `500`**, not `431`. See
[Limits](/configuration/limits/#header-limits).

## Agents

**The agent filter's `timeout-ms` and `phase` are not applied.** They are
parsed and not read at request time; the agent block's `timeout-ms` applies.
[#542](https://github.com/zentinelproxy/zentinel/issues/542).
*Workaround:* set `timeout-ms` on the agent block.

## Rate limiting

**Redis and memcached rate limiting ignore `burst`.** The distributed backends
count requests per fixed one-second window; only the local limiter is a token
bucket. [#543](https://github.com/zentinelproxy/zentinel/issues/543).

**Rate limiters are not rebuilt on reload.** After `SIGHUP`, a changed
`rate-limit` filter, `rate-limits { default-rps }` or `global` limit keeps its
old values. [#543](https://github.com/zentinelproxy/zentinel/issues/543).
*Workaround:* restart the proxy after changing a rate limit. `pgrep zentinel`
also matches agent processes such as `zentinel-echo-agent`; use
`pgrep -x zentinel` when sending signals.

## Upstreams and health checks

**Targets given as a host name are not health-checked.**
`target "backend.internal:80"` is never probed, so it stays in rotation whatever
its state. [#544](https://github.com/zentinelproxy/zentinel/issues/544).
*Workaround:* use IP addresses for targets that need health checks, or
`discovery "dns"`, whose resolved addresses are probed.

**An unknown sticky-session `fallback` becomes round robin** without a warning
from `test` or `lint`.
[#542](https://github.com/zentinelproxy/zentinel/issues/542).

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

**Connection limits are not enforced.** Zentinel does not limit client
connections or concurrent requests. `limits { max-connections-per-client
max-total-connections max-in-flight-requests }` are accepted and do nothing,
without a warning; `system { max-connections }` is reported by `zentinel test`
and `lint` as not applied.
[#542](https://github.com/zentinelproxy/zentinel/issues/542).
*Workaround:* use a rate-limit filter to bound per-client load, and the
operating system's limits for connections. More settings of this kind are in
[Performance Tuning: Settings with no effect](/operations/performance-tuning/#settings-with-no-effect).

**Namespace and service `limits` are not applied.** Every request is held to the
global `limits` block and its route's `policies { max-body-size }`.
[#542](https://github.com/zentinelproxy/zentinel/issues/542).
*Workaround:* set `max-body-size` in the routes' `policies`, and rate-limit
filters on the routes.

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

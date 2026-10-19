+++
title = "Known Limitations"
weight = 6
description = "Settings Zentinel accepts but does not apply, and behaviour that differs from what the configuration suggests"
updated = 2026-10-19
+++

This page lists what release **26.10_3** accepts in a configuration but does not
apply, and where its behaviour differs from what you would reasonably expect.
Each entry links the tracking issue where there is one, and gives a workaround
where one exists. Entries are removed when a release fixes them; the
[Changelog](/appendix/changelog/) says when.

Two habits catch most of these early:

- Run `zentinel lint -c FILE` as well as `zentinel test`. Only `lint` reports
  settings that are misspelled or in the wrong block.
- After starting the proxy, read the `WARN` lines it logs at startup. Several of
  the cases below are logged there and nowhere else.

## Checking a configuration

**`zentinel test` does not report ignored settings.** A misspelled or misplaced
key (`adress`, `timeout-sec`) passes `test` and `--test`; the proxy runs with the
default. Only `zentinel lint` reports it.
[#523](https://github.com/zentinelproxy/zentinel/issues/523).
*Workaround:* run `zentinel lint` before every deploy or reload.

**Unknown values fall back to a default without a warning.** Neither `test` nor
`lint` reports these ([#521](https://github.com/zentinelproxy/zentinel/issues/521)):

| You write | The proxy uses |
|-----------|----------------|
| `load-balancing "least-connections"` (hyphen) or any unknown name | `round_robin` |
| `health-check { type "htttp" { ... } }` | a TCP check |
| `priority "urgent"` | `50` (`"normal"`) |
| `builtin-handler "helth"` | no handler: the route answers `500` |
| `method "GET" "POST"` in `matches` | `GET` only |
| `path-prefix "/api" host "a.com"` on one line in `matches` | `path-prefix` only |

*Workaround:* use the exact names from the reference pages (underscores for
load-balancing algorithms; `low`, `normal`, `high`, `critical` for priority, which
are 10, 50, 100 and 1000), one `method` per route, one condition per line.

**`limits` key names differ between a single file and a directory.** In a single
configuration file only `max-header-size`, `max-header-count`, `max-body-size`,
`max-connections-per-client`, `max-total-connections` and
`max-in-flight-requests` are read. The `-bytes` names (`max-body-size-bytes`,
`max-header-size-bytes`, ...) are read only when the configuration is a
directory, and in a single file they are ignored without a lint warning. See
[Limits](/configuration/limits/).
*Workaround:* in a single file, use the names without `-bytes`.

**`max-body-size` below 1 MiB fails validation** in a single file, with
`max_body_buffer_bytes cannot exceed max_body_size_bytes`: the body buffer
defaults to 1 MiB and cannot be set from a single file.

**No environment variable substitution.** `${VAR}` is kept as literal text. In
a listener `address` it passes `zentinel test`, then the proxy panics at
startup. [#520](https://github.com/zentinelproxy/zentinel/issues/520).
*Workaround:* render the file before starting the proxy, for example with
`envsubst`.

**`service-type` is not read.** A route's type comes from its blocks
(`static-files`, `builtin-handler`, `api-schema`, `inference`; otherwise `web`),
so `service-type "api"` alone leaves a route `web`. From the next release an
explicit `service-type` is applied where the route's blocks allow it. See
[Service Types](/configuration/routes/#service-types).

**`./zentinel.kdl` is not picked up automatically.** Without `-c` or
`ZENTINEL_CONFIG`, the proxy starts with its embedded default configuration
(listening on `0.0.0.0`), whatever files are in the working directory.
*Workaround:* always pass `-c`.

## Requests and responses

**No `X-Forwarded-For`, `X-Forwarded-Proto`, `X-Forwarded-Host` or
`Forwarded` header is sent to upstreams.** Backends see the proxy as the client.
The proxy adds only `X-Correlation-Id`, `X-Trace-Id` and `X-Forwarded-By:
Zentinel`. [#515](https://github.com/zentinelproxy/zentinel/issues/515).
*Workaround:* for the protocol, set `"X-Forwarded-Proto" "https"` in
`policies { request-headers { set { ... } } }` on routes of an HTTPS listener.
There is none for the client IP.

**Request body limits.** A route's `policies { max-body-size }` is not enforced.
The global `limits { max-body-size }` is, but a request over it gets
`500 Internal Server Error` instead of `413`. [#517](https://github.com/zentinelproxy/zentinel/issues/517).
*Workaround:* use the global limit.

**Error pages cannot be configured.** No parser reads `error-pages`, so there
are no templates and no per-status pages. What clients receive for each kind of
error is listed under [Error Pages](/configuration/routes/#error-pages).

**Upstream error responses get the proxy's `Content-Type`.** For an upstream
`4xx`/`5xx` the body is passed through, but `Content-Type` is replaced:
`text/html; charset=utf-8` on `web` and `static` routes, `application/json` on
`api`, `builtin` and `inference` routes. A JSON error from a backend behind a
`web` route reaches the client labelled `text/html`.
[#522](https://github.com/zentinelproxy/zentinel/issues/522).

**The "no route matched" response is mislabelled.** It is `404` with the body
`{"error":"404 Internal Server Error","trace_id":""}`: the reason text is wrong
and the trace ID is empty. [#525](https://github.com/zentinelproxy/zentinel/issues/525).
*Workaround:* end the route list with a catch-all route (`path-prefix "/"`) or
set the listener's `default-route`.

**A request schema that does not compile turns validation off.** The proxy logs
`Failed to initialize schema validator for route <id>` at startup and forwards
requests unchecked. A `required` with a single name (`required "email"`) is one
way to get there: it becomes a string, not a list, and the schema is rejected.
[#524](https://github.com/zentinelproxy/zentinel/issues/524). See [API Schema Validation](/configuration/routes/#api-schema-validation).
*Workaround:* check the startup log after changing a schema.

## Rate limiting

**`rate-limits { default-rps default-burst }` is not applied.** Routes without
their own limit are not limited. `lint` is silent.
[#518](https://github.com/zentinelproxy/zentinel/issues/518).
*Workaround:* attach a `type "rate-limit"` filter to each route, or use
`rate-limits { global { ... } }`. See [Filters](/configuration/filters/).

## Health checks and reload

**A reload does not start health checks.** After `SIGHUP`, upstreams that
gained or changed a `health-check` are not probed. A fresh start also probes
every target twice per interval.
[#516](https://github.com/zentinelproxy/zentinel/issues/516).
*Workaround:* restart the proxy after adding or changing a health check.
`pgrep zentinel` also matches agent processes such as `zentinel-echo-agent`; use
`pgrep -x zentinel` when sending signals.

## Listeners and TLS

**HTTP/3 is not implemented.** A listener with `protocol "h3"` is rejected at
validation. An `https` listener serves HTTP/1.1 and HTTP/2 (through ALPN).

**`max-concurrent-streams` on a listener is not applied.** The proxy logs an
"Unwired feature" warning at startup. See
[Listeners](/configuration/listeners/).

**The "Unwired feature" warnings for `cipher-suite` and TLS `max-version` are
wrong.** Both settings are applied: with `max-version "TLS1.2"` a TLS 1.3-only
client is refused, and with one `cipher-suite` a client offering only another
suite fails the handshake. The warnings can be ignored.
[#526](https://github.com/zentinelproxy/zentinel/issues/526). (Write
`cipher-suite` once per suite; the plural `cipher-suites` is rejected.)

## Process, logging and resource limits

**`logging { level format }` does not change the proxy's output.** The log goes
to stdout/stderr as plain text at `info`, or `debug` with `--verbose`. A value
other than `"info"`/`"json"` produces an "Unwired feature" warning. The
`ZENTINEL_LOG_FORMAT` environment variable has no effect on the proxy either.
*Workaround:* set `RUST_LOG` (for example `RUST_LOG=warn`). See
[Observability](/configuration/observability/).

**Connection limits are not enforced.** `system { max-connections }` and
`limits { max-connections-per-client max-total-connections
max-in-flight-requests }` are accepted and do nothing. `system { daemon }` is
not read either; use the `-d` / `--daemon` flag.
[#527](https://github.com/zentinelproxy/zentinel/issues/527).
*Workaround:* use a rate-limit filter to bound per-client load, and the
operating system's limits for connections. More settings of this kind are in
[Performance Tuning: Settings with no effect](/operations/performance-tuning/#settings-with-no-effect).

## Installation

**Release tarball binaries are not executable.** `zentinel`,
`zentinel-gateway` and `zentinel-echo-agent` in the release archives have mode
`0644`, so a manual install fails with "permission denied". The install script
is not affected. [#519](https://github.com/zentinelproxy/zentinel/issues/519).
*Workaround:* `chmod +x zentinel` before moving it into place.

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

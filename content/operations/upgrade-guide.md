+++
title = "Upgrade Guide"
weight = 10
updated = 2026-10-26
+++

How to move a Zentinel deployment to a newer release, and which releases change behaviour you may depend on.

## How versions work

Zentinel releases use calendar versioning: `YY.MM_N`, for example `26.10_3` is the third release of October 2026. The release number is what you install, pin and report. Each release also has a crate version (SemVer, for example `0.6.46`), which matters only if you depend on the Rust crates. See [Versioning](/appendix/versioning/) for the full scheme and release history.

A CalVer number says when a release was cut, not how risky it is. A `_N` release can contain a breaking change: 26.08_2 changed the listener TLS schema. Read the [changes table](#breaking-and-behaviour-changing-releases) below for every release between your version and the target, not only the newest one.

To see what is running:

```bash
zentinel --version
# zentinel 0.6.45 (release 26.10_3, commit 07c2f6d)
```

Use the `release` field. The crate version printed by the binary can be one lower than the version published to crates.io for the same release (see the note at the top of the [changelog](https://github.com/zentinelproxy/zentinel/blob/main/CHANGELOG.md)).

## Upgrade procedure

### 1. Read the changes

Check the [table below](#breaking-and-behaviour-changing-releases) and the [Changelog](/appendix/changelog/) for every release after the one you run. Entries marked as fixes can still change behaviour: several 26.08 and 26.09 releases made settings take effect that had been parsed and ignored.

### 2. Validate your configuration with the new binary

Download the new release next to the current one and check your existing configuration with it before you replace anything:

```bash
VERSION=26.10_3
curl -fsSLO "https://github.com/zentinelproxy/zentinel/releases/download/${VERSION}/zentinel-${VERSION}-linux-amd64.tar.gz"
curl -fsSLO "https://github.com/zentinelproxy/zentinel/releases/download/${VERSION}/zentinel-${VERSION}-linux-amd64.tar.gz.sha256"
sha256sum -c "zentinel-${VERSION}-linux-amd64.tar.gz.sha256"
mkdir "zentinel-${VERSION}" && tar -xzf "zentinel-${VERSION}-linux-amd64.tar.gz" -C "zentinel-${VERSION}"

# Parse and validate offline
"./zentinel-${VERSION}/zentinel" test -c /etc/zentinel/zentinel.kdl

# Also check that upstreams, agents and certificates are reachable from this host
"./zentinel-${VERSION}/zentinel" validate -c /etc/zentinel/zentinel.kdl

# Report settings that parse but have no effect
"./zentinel-${VERSION}/zentinel" lint -c /etc/zentinel/zentinel.kdl
```

Release archives are also signed; see [Supply Chain Security](../supply-chain/) to verify signatures and provenance. Container users run the same checks inside the new image:

```bash
docker run --rm -v /etc/zentinel:/etc/zentinel:ro \
  ghcr.io/zentinelproxy/zentinel:26.10_3 test -c /etc/zentinel/zentinel.kdl
```

Fix anything `test` rejects before going further. New `lint` warnings after an upgrade usually mean a setting was already being ignored, not that it broke.

### 3. Roll out instance by instance

Configuration changes alone do not need a new process: `SIGHUP` (or `systemctl reload zentinel`) reloads the configuration file and certificates, and a configuration that fails to load is rejected while the running one stays in place. Listeners are the exception: they are bound at startup, so changes to listeners need a restart.

A new binary needs a restart. On `SIGTERM`, Zentinel stops accepting connections and drains in-flight requests for up to `graceful-shutdown-timeout-secs` (default 30) before exiting. To upgrade without dropping traffic, run more than one instance behind a load balancer and replace them one at a time:

1. Take one instance out of the load balancer, or let its readiness check fail.
2. Stop it, replace the binary or image, and start it.
3. Check its logs and [metrics](/reference/metrics/) (error rate, upstream health, agent errors) under real traffic.
4. Continue with the next instance.

For Kubernetes, change the image tag and let the Deployment's rolling update do this; see [Rolling Updates](/deployment/rolling-updates/). For a single host with systemd, see [systemd Deployment](/deployment/systemd/).

Upgrade agents separately from the proxy. The proxy and agents talk the [v2 agent protocol](/agents/v2/), and a proxy upgrade does not require new agent versions unless the release notes say so.

### 4. Roll back if needed

Keep the previous binary or image tag and a copy of the configuration you ran with it. Rolling back is the same procedure in reverse: replace the binary, restart instance by instance.

If you changed the configuration for the new release (for example the 26.08_2 TLS schema), the old binary will not load the new configuration. Roll back the configuration together with the binary.

### Building from source

Source builds need the Rust version pinned in the repository's `rust-toolchain.toml`: **Rust 1.96** since 26.10_3 (1.95 before). Prebuilt binaries and container images are not affected. See [Building from Source](/development/building/).

## Breaking and behaviour-changing releases

Releases not listed here are dependency, security or documentation updates with no configuration or behaviour change you need to act on. Newest first.

| Release | Type | What changes | What to do |
|---------|------|--------------|------------|
| **26.10_8** | Behaviour | **An agent's `config { }` block is delivered, on every connection** (first, pooled, reconnect). Before, it never reached the agent. An agent that rejects its config or does not answer is not used and its filters follow their `failure-mode`. gRPC agents need a build against `zentinel-agent-protocol` 0.6.51 | Check that every `config { }` block says what you mean: fields it leaves out can replace an agent's flags with defaults (ai-gateway, waf, modsec, graphql-security, denylist), and agents that reset state on configure now do so per connection. Use waf and modsec **0.4.1** (idempotent, merging). The auth agent refuses configs that enable SAML, mTLS or token exchange. See [Agent-Specific Configuration](/configuration/agents/#agent-specific-configuration) |
| **26.10_8** | Behaviour | **Agent decisions are enforced in every phase.** Challenge fails closed (`401` with `WWW-Authenticate` from a `www-authenticate` parameter, else `403`; a `body` parameter is the response body), Redirect redirects (it answered `500`), response-phase blocks are enforced, a filter that names an agent that is not loaded fails instead of passing. The filter's `failure-mode` (else the route's, default `closed`) now decides on every path; the `agent` block's value applies only to WebSocket frames | Agents that used to be passed by now decide: review routes whose agents return Challenge or Redirect, and set `failure-mode` on every agent filter. A body agent on a route at the default now refuses on body and response failures where it used to pass them when the agent itself was `"open"`. See [Failure Mode](/configuration/agents/#failure-mode) |
| **26.10_8** | Behaviour | Request bodies go to every agent subscribed to `request_body`, with or without a `waf` block; in buffer and hybrid mode the body is held back from the upstream until the agents allow it; `request-body-mode "stream"`/`"hybrid:N"` are honoured. A body that cannot be decompressed follows the body agents' `failure-mode` (`400`); a request-headers dispatch failure answers `503` instead of `500` | Set `inspect-request-body #false` to keep bodies from agents. The upstream still sees the request line and headers before the body decision ([#608](https://github.com/zentinelproxy/zentinel/issues/608)). See [Body Streaming Modes](/configuration/agents/#body-streaming-modes) |
| **26.10_8** | Behaviour | New `connect-timeout-ms` (default 5000): startup waits at most the longest connect timeout plus 5 s and no longer blocks on a silent agent. Daemon mode (`-d`) works: signals, agents, health checks and metrics run in the daemon; a `user` without a `group` switches to that user's primary group; a broken config exits 1 in the foreground | Nothing to change unless you relied on startup blocking until every agent answered. Daemon deployments now honour `SIGHUP` and `SIGTERM` |
| **26.10_8** | Behaviour | A configured audit log that cannot be opened stops startup; each log file is opened on its own; **a config without an `error-log` block no longer writes `/var/log/zentinel/error.log`** (entries still go to stdout). A reload with an invalid `path-regex` is rejected and rollbacks are applied. `zentinel bundle install` pins rebuilt, smoke-tested agents, starts them on the socket it writes into `agents.kdl`, and no longer writes per-agent YAML files; `ratelimit` left the bundle | Add `error-log {}` to keep the file. Rerun `zentinel bundle install` and include the generated `agents.kdl` (see [Bundle Installation](/deployment/bundle/)); delete the old YAML files it points out |
| **26.10_7** | Behaviour | Namespaces and services are served end to end. A namespace or service without a listener of its own is now served on the global listeners (before, never); listeners inside namespaces and services are bound; routes using a namespace's own upstream work; service `limits` apply. Scoped route ids in logs and metrics are qualified (`ns:route`, `ns:svc:route`). A scoped route with an invalid `path-regex` is left out and reported instead of stopping startup | Check that no namespace is now exposed on a public listener by accident: give it a listener of its own (or a top-level listener with `namespace "..."`) to keep it off the global ones. A privileged port or a failing ACME issuance on a scoped listener can now stop startup. Update dashboards and alerts that match scoped route ids. See [Which listener serves a route](/configuration/namespaces/#which-listener-serves-a-route) |
| **26.10_7** | Behaviour | A route's `error-pages` also replace the proxy's own refusals on that route (rate limits, `max-in-flight-requests`, geo, prompt injection, WebSocket not enabled, no usable upstream, agent blocks without a body), keeping `Retry-After` and `X-RateLimit-*`. An agent block that carries its own body in the request-body phase now sends that body as `text/plain` instead of the generic JSON | Review pages for `429`, `503` and `403`: clients that parsed the old plain-text or JSON refusal bodies get the page. See [Which errors a page replaces](/configuration/routes/#which-errors-a-page-replaces) |
| **26.10_7** | Behaviour | Agent filter `inspect-body #false` and `max-body-bytes` are applied (a body over `max-body-bytes` gets `413` from a fail-closed agent). The top-level `cache` block reads `max-size-bytes` and `lock-timeout-secs` (before, dropped and the defaults used). An include diamond loads. Auto-reload reloads once per edit, sees included files outside the watched directory, and no longer reloads on a save without changes | Check agent filters that set these keys, and `cache` blocks that used the `-bytes`/`-secs` spellings: their values now take effect |
| **26.10_7** | Behaviour | A host-name target falls back across its resolved addresses: one that refuses a connection is skipped for 30 s and the request is retried on another, which uses one `retry-policy` attempt. DNS answers are cached and refreshed in the background | Nothing to change. The retry goes back through target selection, so with several targets it can land on another one. See [Host-name Targets](/configuration/upstreams/#host-name-targets) |
| **26.10_6** | Behaviour | `limits { max-in-flight-requests max-total-connections max-connections-per-client }` are enforced; before they were parsed and ignored. Unset means unlimited (the documented defaults never applied) and `0` means unlimited. Over `max-in-flight-requests` a request gets `503` with `Retry-After: 1`; over a connection limit the connection is closed. The starter configuration older installs keep at `/etc/zentinel/zentinel.kdl` sets `max-connections-per-client 100`, counted per TCP peer. Namespace `limits` are applied to the namespace's routes | **Behind a load balancer or NAT:** list it in the listener's [`trusted-proxies`](/configuration/listeners/#trusted-proxies), which exempts it from `max-connections-per-client` (the proxy logs an `INFO` note at startup when a per-client limit is set without `trusted-proxies`), or remove the line. Check `max-total-connections` and `max-in-flight-requests` against peak load. See [Limits](/configuration/limits/#concurrency-limits) |
| **26.10_6** | Behaviour | Route `error-pages` blocks are read: a page replaces the upstream's and the proxy's response for its status. Agent filter `timeout-ms` applies (it can only shorten the agent's); `phase` on an agent filter is reported as ignored | Review `error-pages` blocks that were ignored until now; check agent filters whose `timeout-ms` is shorter than the agent's |
| **26.10_6** | Behaviour | Rate limiters are rebuilt on reload. Redis and memcached backends are used and run the same token bucket as the local limiter, but only in binaries built with `--features distributed-rate-limit`; the release binaries still limit per instance and log a warning | Builds with the feature: expect limits to be shared across instances, so per-instance values set to compensate are now too strict |
| **26.10_6** | Behaviour | Host-name targets are health-checked (every resolved address, every probe cycle); with a check, the proxy dials the first healthy address. An early `SIGHUP` no longer stops a starting proxy | Check health-check paths on host-name targets, which were never probed before |
| **26.10_6** | Tooling | `-c <dir>` and `ZENTINEL_CONFIG=<dir>` load a directory. `test --strict` and `lint` check every file read, included ones too, so a typo in an included file now fails `--strict` | Run `zentinel test --strict` before upgrading |
| **26.10_5** | Behaviour | Zentinel sends `X-Forwarded-For`, `-Proto` and `-Host`, replacing client-sent ones, and drops client-sent `Forwarded` and `X-Real-IP`, unless the peer is in the listener's new `trusted-proxies`. The client IP for rate limits, geo filters, `ip_hash`, agents and logs follows the same rule | **Behind a load balancer:** list it in [`trusted-proxies`](/configuration/listeners/#trusted-proxies), or backends see its address and `client-ip` rate limits count it as one client |
| **26.10_5** | Behaviour | Failing health checks take targets out of rotation; with all failing, requests get `503`. Health checks follow reloads, and discovery-backed upstreams are probed. The HTTP check honours `expected-status` and `timeout-secs` and sends `Host` | Check health-check `path`, `expected-status` and `host` against what each backend answers before upgrading |
| **26.10_5** | Behaviour | Rate limiting: `burst` is the token-bucket size (default `10`, so `max-rps 100` without `burst` admits 10 at once); `rate-limits { default-rps }` applies to routes without a limit; `global { key }` and `header:<name>` keys work; `client-ip` buckets are per client (they were shared) | Set `burst` where clients send in bursts; expect `429`s from `default-rps` |
| **26.10_5** | Behaviour | Upstream error responses pass through unchanged; route `policies { max-body-size }` is enforced (the smaller of route and global applies); an over-limit body gets `413` (was `500`) | Raise the global `max-body-size` if a route needs a larger limit than it |
| **26.10_5** | Tooling | `zentinel test` prints "is being ignored" warnings, and `test --strict` fails on them. `method "GET" "POST"` matches both; `system { daemon #true }` daemonizes; `system { max-connections }` is reported as not applied; a `${` in a listener address is rejected. In directory configurations an unknown agent `failure-mode` is a load error | Run `zentinel test --strict` with the new binary; under systemd or in containers, make sure `daemon` is not set |
| **26.10_3** | Build | Building from source needs Rust 1.96 | Update the toolchain for source builds |
| **26.10_2** | Behaviour | ACME renewal follows the CA's ARI renewal window when the CA offers one, so certificates can renew earlier than `renew-before-days` (never later) | Nothing, unless you monitor renewal timing |
| **26.09_6** | Behaviour | Pingora 0.9.0: hop-by-hop request headers (`Connection`, `Keep-Alive`, `TE`, `Upgrade`, `Proxy-Authorization`, …) are no longer forwarded; only WebSocket upgrades pass, other `Upgrade` requests such as `h2c` do not; requests that nominate `Host` or forwarding headers in `Connection`, or carry ambiguous authorities, are rejected | Check upstreams that relied on `Proxy-Authorization` or non-WebSocket upgrades |
| **26.09_4** | Behaviour | An agent that was unreachable at startup, or restarted later, is reconnected. Before, traffic for it was passed through uninspected (with `failure-mode "open"`) until the proxy restarted. Multiplexed MCP tool calls now use the route's retry policy, connection pool and upstream TLS | Expect agents to start acting on traffic they were silently skipping |
| **26.09_2** | Behaviour | `health-check` blocks probe upstreams. They never sent a probe before. Probe results took targets out of rotation only from 26.10_5 | Check that health-check paths and expected statuses are right |
| **26.08_13** | Behaviour | `discovery "dns-srv"` resolves SRV records with their ports and weights (before: the bare domain on port 80) | Check which backends are selected after the upgrade |
| **26.08_11** | Behaviour | Upstream `discovery` blocks resolve and route. Before, such upstreams routed nowhere | Remove static `target` workarounds next to `discovery`, or both are used |
| **26.08_10** | Behaviour | `tracing { enabled #false }` disables tracing. Before, tracing ran whenever the block was present | Check configurations that set it, and anything that consumes their spans |
| **26.08_7 – 26.08_9** | Tooling | `zentinel lint` reports keys that parse and are ignored, across all configuration blocks | Nothing at runtime; clean up reported keys |
| **26.08_6** | Behaviour | Listener `namespace` and per-listener timeouts are applied on wildcard binds (`0.0.0.0`, `[::]`). Before, such listeners served the global route set | Check wildcard listeners that set `namespace` |
| **26.08_5** | **Breaking** | Route `buffer-requests` and `buffer-responses` are removed; they never had an effect and are now reported as unknown keys. MCP and A2A route policy is enforced (it was ignored in 26.08_4) | Remove the two keys; review MCP/A2A allow and deny lists |
| **26.08_4** | **Breaking** | Settings that were parsed and discarded take effect: `upstream.timeouts`, `connection-pool { idle-timeout-secs }`, route `policies` (`failure-mode`, `timeout-secs`, `rate-limit`), distributed rate-limit fallback and TTL, WAF rule exclusions. `retry-policy.max-attempts` now bounds request retries. Host matching is case-insensitive. `client-auth` without `ca-file`, and listeners with `protocol "h3"`, refuse to start | Review timeouts and route policies; remove `h3` listeners; add `ca-file` to mTLS listeners |
| **26.08_3** | Behaviour | Listener TLS settings are applied: per-SNI certificates, `client-auth`, `min-version` / `max-version`, `cipher-suite`, `session-resumption`. Before, they only produced startup warnings | Check that listeners with `client-auth` should require client certificates |
| **26.08_2** | **Breaking** | Listener TLS schema: repeated `sni { }` blocks replace `additional-certs`, repeated `cipher-suite "NAME"` replaces `cipher-suites { }`; unknown keys inside `tls` and `sni` are rejected. `retry-policy` accepts only `max-attempts`. Route match conditions without a valid value, and invalid `shadow` percentages, are errors | Rewrite `tls` blocks ([migration example](/appendix/changelog/#26-08-2)); remove other `retry-policy` keys |
| **26.06_1** | Behaviour | With `observability { metrics { enabled } }`, metrics are served by a dedicated listener on the metrics `address` (default `0.0.0.0:9090`) | Make sure the port is free and reachable only where intended |
| **26.05_4** | Config | Shipped and embedded configurations use `system { }`. The old `server { }` block is still accepted with a deprecation warning | Rename `server` to `system` |
| **26.02_18** | **Breaking** | Agent protocol v1 is removed; `protocol-version` is a no-op | Use v2 agents ([migration](/agents/v2/migration/)) |

## See also

- [Changelog](/appendix/changelog/)
- [Versioning](/appendix/versioning/)
- [Rolling Updates](/deployment/rolling-updates/)
- [Supply Chain Security](../supply-chain/)
- [Troubleshooting](../troubleshooting/)

+++
title = "Upgrade Guide"
weight = 10
updated = 2026-10-18
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
| **26.10_3** | Build | Building from source needs Rust 1.96 | Update the toolchain for source builds |
| **26.10_2** | Behaviour | ACME renewal follows the CA's ARI renewal window when the CA offers one, so certificates can renew earlier than `renew-before-days` (never later) | Nothing, unless you monitor renewal timing |
| **26.09_6** | Behaviour | Pingora 0.9.0: hop-by-hop request headers (`Connection`, `Keep-Alive`, `TE`, `Upgrade`, `Proxy-Authorization`, …) are no longer forwarded; only WebSocket upgrades pass, other `Upgrade` requests such as `h2c` do not; requests that nominate `Host` or forwarding headers in `Connection`, or carry ambiguous authorities, are rejected | Check upstreams that relied on `Proxy-Authorization` or non-WebSocket upgrades |
| **26.09_4** | Behaviour | An agent that was unreachable at startup, or restarted later, is reconnected. Before, traffic for it was passed through uninspected (with `failure-mode "open"`) until the proxy restarted. Multiplexed MCP tool calls now use the route's retry policy, connection pool and upstream TLS | Expect agents to start acting on traffic they were silently skipping |
| **26.09_2** | Behaviour | `health-check` blocks probe upstreams. They never sent a probe before, so every target counted as healthy | Check that health-check paths and expected statuses are right; wrong ones now take targets out of rotation |
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

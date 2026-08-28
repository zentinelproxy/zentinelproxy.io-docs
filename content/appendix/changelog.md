+++
title = "Changelog"
weight = 1
updated = 2026-08-24
+++

All notable changes to Zentinel are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Zentinel uses [CalVer](https://calver.org/) (`YY.MM_PATCH`) for releases and
[SemVer](https://semver.org/) for crate versions on crates.io. CalVer is the
primary, operator-facing version. See [Versioning](../versioning/) for details.

## Release Overview

| CalVer | Crate Version | Date | Highlights |
|--------|---------------|------|------------|
| [26.08_8](#26-08-8) | 0.6.31 | 2026-08-28 | Configuration checking reaches the remaining blocks and the browser playground, which was running a different set of checks entirely; an agent's `type` is read as a child node as well as a property |
| [26.08_7](#26-08-7) | 0.6.30 | 2026-08-27 | `zentinel lint` reports settings that parse but are read by nothing: run-together lines, and keys written into the wrong one of two same-named blocks |
| [26.08_6](#26-08-6) | 0.6.29 | 2026-08-27 | Listener `namespace` isolation and per-listener timeouts now work on wildcard binds — both were silently ignored on `0.0.0.0` listeners; certificate reloads report what changed instead of only counts |
| [26.08_5](#26-08-5) | 0.6.28 | 2026-08-24 | MCP and A2A policy is now **enforced** — it was parsed and ignored in 26.08_4; `cargo install zentinel-proxy` works again; **breaking**: dead buffering fields removed |
| [26.08_4](#26-08-4) | 0.6.27 | 2026-08-23 | Native MCP and A2A support; settings that were parsed and discarded now take effect (upstream timeouts, route policies, `failure-mode`); certificate folders; agent and mTLS authentication hardening |
| [26.08_3](#26-08-3) | 0.6.26 | 2026-08-22 | Per-SNI certificates, mTLS and TLS hardening settings now reach the listener |
| [26.08_2](#26-08-2) | 0.6.25 | 2026-08-22 | ACME DNS-01 idempotency; **breaking** listener TLS config schema |
| [26.08_1](#26-08-1) | 0.6.24 | 2026-08-08 | Security: rustls 0.23.43 hardening; dependency maintenance (pem 4.0, base64 0.23, jsonschema 0.49, validator 0.21, async-memcached 0.7) |
| [26.07_4](#26-07-4) | 0.6.23 | 2026-07-30 | Dependency maintenance: wasmtime 47, quinn-proto 0.11.16, maxminddb 0.30, rust-minor batch (17 updates) |
| [26.07_3](#26-07-3) | 0.6.22 | 2026-07-18 | Security: serde_with 3.21 (GHSA-7gcf-g7xr-8hxj); tokio-tungstenite 0.30, jsonschema 0.48 |
| [26.07_2](#26-07-2) | 0.6.21 | 2026-07-06 | Dependency maintenance: quick-xml 0.41, cmov 0.5.4, rust-minor batch |
| [26.07_1](#26-07-1) | 0.6.20 | 2026-07-01 | Dependency maintenance: maxminddb 0.29, wasmtime 46, rust-minor batch (12 updates) |
| [26.06_3](#26-06-3) | 0.6.18 | 2026-06-23 | Multi-file KDL block merging, circuit-breaker recovery fix, counter underflow guard |
| [26.06_2](#26-06-2) | 0.6.17 | 2026-06-16 | Agent body limits and bounded limiter state, route-level retry-policy parsing, Pingora 0.8.1 |
| [26.06_1](#26-06-1) | 0.6.16 | 2026-06-07 | Standalone Prometheus metrics server, per-listener route sets, non-root Docker fix |
| [26.05_4](#26-05-4) | 0.6.15 | 2026-05-12 | OpenTelemetry 0.32 stack, sysinfo 0.39, Rust toolchain 1.95 |
| [26.05_3](#26-05-3) | — (not released) | 2026-05-05 | Embedded config uses `system` block, ACME hickory-resolver 0.26 fix |
| [26.05_2](#26-05-2) | 0.6.13 | 2026-05-03 | Install script provisions systemd unit, system user, and starter config |
| [26.05_1](#26-05-1) | 0.6.12 | 2026-05-01 | Per-SNI ACME certificates for multi-tenant TLS |
| [26.04_7](#26-04-7) | 0.6.11 | 2026-04-28 | Security: rand unsoundness fix in zentinel-sim (GHSA-cq8v-f236-94qc) |
| [26.04_6](#26-04-6) | 0.6.10 | 2026-04-25 | Security: openssl 0.10.78 (4 high-severity), rand 0.8.6; ACME schema docs |
| [26.04_5](#26-04-5) | 0.6.9 | 2026-04-20 | Configurable ACME certificate key type (ECDSA P-256/P-384) |
| [26.04_4](#26-04-4) | 0.6.8 | 2026-04-19 | Cloudflare DNS-01, custom ACME directory URLs, EAB, SAN renewal fix |
| [26.04_3](#26-04-3) | 0.6.7 | 2026-04-16 | Security: rand unsoundness across pingora fork, aes 0.9; Rust 1.94.1 |
| [26.04_2](#26-04-2) | 0.6.6 | 2026-04-10 | Security: wasmtime 43.0.1 (critical aarch64 sandbox escape, CVE-2026-34971) |
| [26.04_1](#26-04-1) | 0.6.4 | 2026-04-09 | Numeric route priorities, host extraction fix, GLIBC fix, Gateway API conformance CI |
| [26.03_1](#26-03-1) | 0.5.12 | 2026-03-01 | March release, image optimization agent v0.2.0 |
| [26.02_5](#26-02-5) | 0.5.11 | 2026-02-27 | `include` directive support in single-file config loading |
| [26.02_4](#26-02-4) | 0.4.10 | 2026-02-04 | Install script fix, CI workflows, Pingora fork security fix |
| [26.02_3](#26-02-3) | 0.4.9 | 2026-02-03 | First-time user smoke tests, protocol-version config, docs refresh |
| [26.02_1](#26-02-1) | 0.4.7 | 2026-02-02 | Pingora 0.7 upgrade, drop fork, major dependency sweep |
| [26.02_0](#26-02-0) | 0.4.5 | 2026-01-29 | Supply chain security: SBOM, cosign signing, SLSA provenance |
| [26.01_11](#26-01-11) | 0.4.5 | 2026-01-29 | Per-request allocation reduction in hot path |
| [26.01_10](#26-01-10) | 0.4.3 | 2026-01-27 | Security fixes, dependency updates |
| [26.01_9](#26-01-9) | 0.4.2 | 2026-01-21 | Sticky load balancing, install script UX |
| [26.01_8](#26-01-8) | 0.4.1 | 2026-01-21 | Dependency updates (prost, tonic, tungstenite, sysinfo) |
| [26.01_7](#26-01-7) | 0.4.0 | 2026-01-21 | DNS-01 ACME challenge support |
| [26.01_6](#26-01-6) | 0.3.1 | 2026-01-14 | Agent Protocol v2 connection pooling |
| [26.01_4](#26-01-4) | 0.3.0 | 2026-01-11 | Agent Protocol v2, WASM runtime |
| [26.01_3](#26-01-3) | 0.2.3 | 2026-01-05 | Bug fixes |
| [26.01_0](#26-01-0) | 0.2.0 | 2026-01-01 | First CalVer release |
| [25.12](#25-12) | 0.1.x | 2025-12 | Initial public releases |

---

## 26.08_8

**Date:** 2026-08-28
**Crate version:** 0.6.31

> Configuration checking only — nothing about how the proxy handles traffic changes. As in 26.08_7: if `zentinel lint` starts warning about a configuration you have been running, the setting was already being ignored. The warning is new, the behaviour is not, and nothing that loaded before will fail to load.

### Added
- **Checking extended to the remaining configuration blocks**, thirty-five in total: `health-check` and its per-type settings, the inference `readiness` block and its four sub-blocks, `agent` and its transport blocks, an agent transport's `tls`, the global `rate-limits` block, and rate-limit filters. See [Upstreams](../../configuration/upstreams/) and [Agents](../../configuration/agents/).
- **Settings are checked against the block they are actually in.** Several block names mean more than one thing: `cache` configures storage at the top level and policy inside a route; `tls` means one thing on a listener, another on an upstream and a third on an agent transport; `type "http"` and `type "grpc"` accept different health-check settings. Each is checked against its own list rather than a merged one, and a setting in the wrong place is told where it belongs rather than offered a spelling suggestion:

  ```
  'disk-path' is a setting of the top-level 'cache' block, not of a 'route'
  block's 'cache' block, so it is ignored here.
  ```

- **The [configuration playground](../../getting-started/playground/) runs the same checks as the CLI.** It had reported only topology warnings, so a configuration could look clean in the browser while `zentinel lint` reported settings the proxy ignores. The checks need nothing but the configuration text, but sat behind a build flag that pulls in the async runtime and X.509 parsing and cannot compile for WebAssembly; that flag now gates only the checks which genuinely need it.

### Fixed
- **An agent's `type` written as a child node was ignored.** The documented form is a property — `agent "waf" type="waf"` — and a `type "waf"` child node instead produced an agent type of `Custom(<id>)` rather than the type named. Both forms are now read, the same way `unix-socket`, `grpc` and `http` already accept either a child node or a bare argument. The agent type appears in logs and via the config endpoint and affects no routing or security decision, so nothing changes beyond those reporting it correctly.

---

## 26.08_7

**Date:** 2026-08-27
**Crate version:** 0.6.30

> Configuration checking only — nothing about how the proxy handles traffic changes. `zentinel lint` reports more of the configuration that parses cleanly and then does nothing. If it warns about a config you have been running, the setting was already being ignored: the warning is new, the behaviour is not. No config that loaded before will fail to load.

### Added
- **Settings swallowed by a run-together line are reported.** KDL separates settings by a newline or a `;`. Written on one line with neither, `listener "public" { address "0.0.0.0:8080" namespace "iso" }` is not two settings — it is a single `address` node carrying three arguments, and `namespace` never reaches the parser at all. The config loads, validates and starts without it. The check reports an argument after the first whose value names a setting of the same block, so a setting that legitimately takes a list (`hostnames "a.com" "b.com"`) is unaffected. See [Listeners](../../configuration/listeners/).
- **Settings written into the wrong one of two same-named blocks are reported, with where they belong.** Block names are not unique. The top-level `cache` block configures the storage backend (`backend`, `disk-path`); a route's `cache` block configures that route's policy (`default-ttl-secs`). They share a single setting between them, so storage settings placed in a route's cache block parse and do nothing — a silently empty cache directory. `tls` has the same split, meaning one thing on a listener and another on an upstream. The warning names the block the setting belongs to rather than guessing at a spelling:

  ```
  'disk-path' is a setting of the top-level 'cache' block, not of a 'route'
  block's 'cache' block, so it is ignored here.
  ```

- **Unknown-setting checking now covers eleven more blocks:** `listener`, both `cache` blocks, `sni`, `sni-certs`, `acme`, `eab`, `upstream`, an upstream's `tls`, and `target`. See [Cache](../../configuration/cache/) and [Upstreams](../../configuration/upstreams/).

### Fixed
- **`verify` in the inference-routing example did nothing.** Two upstream `tls` blocks in the shipped `inference-routing.kdl` example set `verify #true`. No parser reads it — upstream certificate verification is controlled by `insecure-skip-verify` and is on by default — so the example got the behaviour it intended by accident while stating it in a setting that has never existed. Found by the new checks on their first run against the shipped configurations.

---

## 26.08_6

**Date:** 2026-08-27
**Crate version:** 0.6.29

> **If you set `namespace` on a listener bound to `0.0.0.0` or `[::]`, it was doing nothing.** The listener served the *global* route set instead of its namespace's, with no warning, log line or validation error. `namespace` is an isolation control, so this failed in the permissive direction: routes an operator believed were scoped away were reachable. Concrete binds such as `127.0.0.1:9000` were unaffected, which is why this survived — the documented admin-listener example is loopback-bound.
>
> **Check any wildcard-bound listener that carries a `namespace` before upgrading:** it begins enforcing isolation for the first time, so routes that have been served from the global set will stop being reachable there. The same listeners' `request-timeout-secs` and `keepalive-timeout-secs` also begin taking effect, having run on defaults until now.

### Fixed
- **Listener `namespace` is enforced on wildcard binds.** Namespace route sets were stored against the *configured* bind address and looked up by the address the connection actually arrived on. A connection accepted on `0.0.0.0:443` reports the concrete interface it landed on — `203.0.113.5:443` — and never `0.0.0.0:443`, so the lookup could not match and the request fell through to the global route set. Resolution now compares parsed socket addresses: exact binds by equality, wildcard binds by port across the address families that bind can accept, with IPv4-mapped addresses normalised so a dual-stack listener resolves both families alike. A concrete bind takes precedence over a wildcard bind on the same port. See [Listeners](../../configuration/listeners/).
- **Per-listener `request-timeout-secs` and `keepalive-timeout-secs` apply on wildcard binds.** The same comparison meant a config setting either on a `0.0.0.0` listener validated cleanly and then ran on the defaults.

### Added
- **Certificate reloads report what changed.** A reload logged counts and a bare success line, which cannot answer whether anything actually changed: a renewal covers the same hostnames as the certificate it replaces, so every count stays identical. Reloads now log `added`, `removed` and `replaced` hostnames, where `replaced` names a hostname whose certificate changed and carries the SHA-256 fingerprints on both sides — the same digest `openssl x509 -fingerprint -sha256` prints. A rescan that changed nothing says so explicitly, and the default certificate participates as `<default>`. See [Knowing what a reload changed](../../configuration/listeners/#knowing-what-a-reload-changed).

---

## 26.08_5

**Date:** 2026-08-24
**Crate version:** 0.6.28

> **If you configured `mcp` or `a2a` in 26.08_4, it did nothing.** The blocks parsed, validated and rejected unknown keys — and no request was ever checked against them. A route declaring `tools { allow "get_weather" }` permitted every tool there is. That is fixed here, which means these routes begin enforcing policy for the first time: **check your allow and deny lists say what you intend before upgrading.**
>
> Also breaking: `buffer-requests` and `buffer-responses` are removed. Neither ever had any effect, so nothing changes behaviourally, but a config setting them is now reported by `zentinel lint` as a key nothing reads.

### Fixed
- **MCP and A2A route policy is enforced.** Policy runs during body handling, resolved from the JSON-RPC envelope, with the body accumulated across chunks and judged once at end of stream — never on a partial envelope, and before anything reaches an upstream. Denials return 403 with an operator-readable reason. Allowed requests record the method and tool resolved *from the body*, so metrics describe what the upstream will execute rather than what a header claimed. Accumulation stops at 1 MiB, past which `on-uninspectable-body` decides rather than a truncated prefix being judged as the whole request. See [Agentic Protocols](../../configuration/agentic/).
- **`cargo install zentinel-proxy` works again.** `cargo publish` strips git sources, so the published crate resolved `pingora-core` from crates.io — upstream, without the fork's TLS hook — and failed to compile. Broken in 0.6.26 and 0.6.27. The fork's affected crates are now published under `zentinel-pingora-*` names and depended on by version.
- **`workers` was read by nothing** — the parser reads `worker-threads`, so two shipped configs ran on the default worker count while the file said otherwise.
- **`circuit-breaker` inside a `route` block did nothing.** Circuit breakers are configured per upstream and per agent. Eight occurrences across five shipped configs, including the default `zentinel.kdl`, are removed.

### Added
- **Unknown-key checking covers `route`, `system` and `server`.** A misspelled key inside those blocks was accepted and discarded; `zentinel lint` now names it and suggests the intended spelling.

### Changed
- **BREAKING — `buffer-requests` and `buffer-responses` removed.** No KDL key set them and nothing read them, so they could never be anything but `false`. No behaviour changes.
- Dependency maintenance: wasmtime 48, `jsonschema` 0.50, rust-minor batch.

---

## 26.08_4

**Date:** 2026-08-23
**Crate version:** 0.6.27

> **Read this before deploying.** A number of settings in this release were previously parsed and then discarded, and now take effect. Nothing about your configuration files changes — but configurations you have been running will start behaving the way they read, which for some deployments is a change in behavior even though nothing was edited.
>
> Affected: every `upstream.timeouts` setting, `connection-pool.idle-timeout-secs` and `max-lifetime-secs`, route `policies` (including `failure-mode`, `timeout-secs` and `rate-limit`), the distributed rate-limit fallback and TTL settings, and WAF rule exclusions. Separately, `retry-policy.max-attempts` changes meaning, host matching becomes case-insensitive, and two configurations that previously started with a warning now refuse to start: `client-auth` without a `ca-file`, and a listener with `protocol "h3"`.

### Added
- **Native MCP and A2A awareness.** Routes can carry an `mcp` or `a2a` block, and the proxy inspects the JSON-RPC envelope: per-method and per-tool allow/deny lists, resolved against the request body. MCP's Streamable HTTP transport mirrors the method and tool name into `Mcp-Method` and `Mcp-Name` headers so intermediaries can route without parsing bodies — taken at face value that is a bypass, since a header saying `read_file` can accompany a body calling `delete_everything`. Zentinel resolves policy from the body and refuses a request whose headers disagree with it. Requests claiming a protocol revision older than `2026-07-28` are refused by default. See [Agentic Protocols](../../configuration/agentic/).
- **`zentinel lint` reports config keys that no parser reads.** A misspelled key in a nested KDL block was accepted and discarded, so `failure_mode` with an underscore silently disabled a policy while the config file said otherwise. The lint now names the key and suggests the intended spelling.
- **Certificate folders.** An `sni-certs` block points at a directory, and every certificate/key pair found there is registered with the hostnames from its own CN and SANs. `reload-mode` selects `off`, `interval` or `watch`.
- **`retry-policy` gains `retryable-status-codes`, `backoff`, `max-backoff`, `per-attempt-timeout` and `retry-non-idempotent`.** Nothing is retried on a status code unless configured, and `POST` is not replayed without opting in.

### Fixed
- **Upstream timeouts, connection-pool bounds and route policies are applied.** These were parsed and discarded, so every deployment ran on defaults regardless of what its configuration said.
- **`failure-mode "open"` works.** The field was never populated, pinning every route to fail-closed — routes deliberately set to fail open would block traffic when an agent died.
- **Agent `require-auth` verifies the token.** It previously checked only that a token was present, so any non-empty string authenticated.
- **`client-auth` without a `ca-file` refuses to start.** It previously logged a warning and served ordinary TLS, so a listener configured for mutual TLS would pass validation and then accept unauthenticated clients.

### Changed
- **`retry-policy.max-attempts` now means request retries, not peer selections.** Re-check the value if you set it.
- **Host matching is case-insensitive**, per RFC 9110.
- **`protocol "h3"` is rejected at load time.** HTTP/3 was never served; the listener silently fell back to HTTPS.

---

## 26.08_3

**Date:** 2026-08-22
**Crate version:** 0.6.26

> Closes the gap 26.08_2 warned about. **Re-check that your configuration says what you intend before upgrading** — a listener that previously ignored `client-auth` will now require and verify client certificates.

### Fixed
- **Per-SNI certificates are served.** A client is now sent the certificate matching the SNI hostname it requested, with wildcard matching and fallback to the default. Previously every client received the primary certificate regardless of the name requested.
- **`client-auth` (mTLS) is enforced.** The listener requests and verifies client certificates against `ca-file`. Previously it did neither, so a listener configured for mTLS accepted unauthenticated connections.
- **`min-version`, `max-version`, `cipher-suite` and `session-resumption` are applied.** The listener previously used Pingora's built-in intermediate profile and ignored all four.
- **Certificates reload on SIGHUP.** ACME renewals previously reached disk but not the listener.

### Changed
- The startup warnings added in 26.08_2 for unapplied TLS settings are removed — there is nothing left for them to warn about.

---

## 26.08_2

**Date:** 2026-08-22
**Crate version:** 0.6.25

> **Contains a breaking configuration change** (listener TLS schema, below). Released as a SemVer patch, so pinning `0.6` will pick it up: check your listener `tls` blocks before upgrading. Configs using `additional-certs` or `cipher-suites` will fail to load.

### Changed
- **BREAKING — listener TLS config schema.** SNI certificates now use repeated `sni { ... }` blocks instead of `additional-certs { cert ... }`, and cipher suites use repeated `cipher-suite "NAME"` nodes instead of a `cipher-suites { ... }` list. Unknown nodes inside `tls` and `sni` blocks are now rejected at parse time (previously silently ignored), with descriptive errors and legacy-syntax hints, so a config can no longer imply TLS behavior the proxy never applies.
- Route match conditions with a missing or non-string value are now a hard error rather than being silently skipped.

### Fixed
- **ACME DNS-01 is idempotent.** Creating a TXT record behaves as an *ensure* operation across the Cloudflare, Hetzner and webhook providers, so a stale `_acme-challenge` record left by a failed run no longer breaks issuance on restart. Only exact value matches are reused — the previous heuristic could select an unrelated record and delete it during cleanup.
- **DNS-01 propagation is visible.** An empty `propagation.nameservers` list now falls back to public resolvers instead of silently failing every lookup at `TRACE` level.

---

## 26.08_1

**Date:** 2026-08-08
**Crate version:** 0.6.24

Dependency-only release. No proxy behavior, configuration schema, or agent protocol changes.

### Security
- **`rustls` 0.23.42 → 0.23.43** — upstream hardens session-ticket age arithmetic and the PSK binder suffix calculation, and tightens QUIC cipher-suite and TLS-version checks. No CVE was assigned and no Zentinel-specific exposure was identified; taken as defense in depth for the TLS listener path.

### Changed
- **Dependency updates:** `pem` 4.0, `base64` 0.23.1, `jsonschema` 0.49.5, `validator` 0.21, `async-memcached` 0.7, `http` 1.5, `redis` 1.5, `toml` 1.1.4

---

## 26.07_4

**Date:** 2026-07-30
**Crate version:** 0.6.23

### Changed
- **Dependency updates:** wasmtime group 46 → 47, `quinn-proto` 0.11.16, `maxminddb` 0.30, rust-minor batch (17 updates) including `tokio` 1.53.1, `hyper` 1.11.0, `serde` 1.0.229, `clap` 4.6.4

---

## 26.07_3

**Date:** 2026-07-18
**Crate version:** 0.6.22

### Security
- **`serde_with` 3.18.0 → 3.21.0** — fixes GHSA-7gcf-g7xr-8hxj, a serialization panic (DoS) in `KeyValueMap`. Zentinel's exposure was low (transitive via `ip2location`, no `KeyValueMap` usage); resolved regardless.

### Changed
- **Dependency updates:** `tokio-tungstenite` 0.30, `jsonschema` 0.48.1, rust-minor batches including `tokio` 1.53, `rustls` 0.23.42, `uuid` 1.24, `redis` 1.4.1

---

## 26.07_2

**Date:** 2026-07-06
**Crate version:** 0.6.21

### Changed
- **Dependency updates:** `quick-xml` 0.41, `cmov` 0.5.4, rust-minor batch (`html-escape`, `jsonschema`, `rand`, `xxhash-rust`)

---

## 26.07_1

**Date:** 2026-07-01
**Crate version:** 0.6.20

### Changed
- **Dependency updates:** `maxminddb` 0.29, wasmtime group 45 → 46, rust-minor batch (12 updates)

---

## 26.06_3

**Date:** 2026-06-23
**Crate version:** 0.6.18

### Added
- **Merge duplicate top-level blocks across included KDL files** — `listeners`, `routes`, `upstreams`, `filters`, and `agents` blocks now merge across `include`d files instead of the last file silently winning; duplicate IDs are rejected at parse time. Singleton blocks (`system`/`server`/`waf`) keep last-wins semantics but now warn on duplicates.

### Fixed
- **Upstream circuit breaker now recovers from the open state** — a breaker that tripped open could remain open instead of transitioning to half-open and recovering once the backend healed
- Guard active request/connection counters against underflow

### Changed
- **Dependency updates:** `tiktoken-rs` 0.12, rust-minor batch

---

## 26.06_2

**Date:** 2026-06-16
**Crate version:** 0.6.17

### Added
- **Agent request/response body limits are now enforced** — agent body inspection honors the configured `max-request-body-bytes` / `max-response-body-bytes`, and per-key rate-limiter state is bounded so it can no longer grow without limit
- **Route-level `retry-policy` parsing** — the `retry-policy` block inside a `route` is now parsed instead of being silently dropped. `max-attempts` is honored; `timeout-ms`, `backoff-base-ms`, `backoff-max-ms`, and `retryable-status-codes` are parsed but not yet applied at runtime (each logs "parsed, but not implemented")

### Fixed
- **Bound hidden unbounded state and run pool maintenance** — the agent-pool maintenance loop was never spawned, per-request correlation affinity could leak, and `max_series` was not enforced

### Security
- **Pingora 0.8.0 → 0.8.1** — bounded default HTTP/2 server limits to mitigate memory exhaustion, plus upstream dependency bumps resolving RUSTSEC-2026-0098 / RUSTSEC-2026-0099 (`rustls-webpki`)

### Changed
- **Dependency updates:** rust-minor batch (9 updates), `alpine` Docker base 3.24

---

## 26.06_1

**Date:** 2026-06-07
**Crate version:** 0.6.16

### Added
- **Standalone Prometheus metrics server** — when `observability.metrics.enabled` is set, the proxy binds a dedicated HTTP listener on `observability.metrics.address` (default `0.0.0.0:9090`) and serves the Prometheus exposition format at `observability.metrics.path` (default `/metrics`). Previously `address` was parsed but never consumed, so nothing bound the port
- **Per-listener route sets** — a listener may serve a distinct set of routes via a `namespace "<id>"` field. Requests arriving on that listener are matched only against the named namespace's routes, with no fallback to the global set

### Fixed
- **Default Docker image starts cleanly as a non-root user** — the distroless images now ship `/var/log/zentinel` and `/var/lib/zentinel` owned by uid/gid 65532, and the bundled container config logs to stdout/stderr
- **Upstream `target` syntax is now identical across single-file and multi-file configs** — the two KDL parsers previously accepted disjoint target syntaxes, so a config copied between layouts (or from the docs) could fail with "requires at least one target"

### Changed
- **Dependency updates:** `tikv-jemallocator` 0.7, `openssl` 0.10.80, `quick-xml` 0.40.1, wasmtime group, `busybox` Docker base 1.38, rust-minor batches

---

## 26.05_4

**Date:** 2026-05-12
**Crate version:** 0.6.15

### Changed
- **OpenTelemetry 0.31 → 0.32** — `opentelemetry`, `opentelemetry_sdk`, and `opentelemetry-otlp` bumped as a coordinated stack; bumping individually leaves two versions of `opentelemetry` in the dependency graph and breaks trait resolution at the proxy boundary
- **Rust toolchain 1.94.1 → 1.95.0** — required by `sysinfo` 0.39
- **Dependency updates:** `sysinfo` 0.39.1, `openssl` 0.10.79, `opentelemetry-semantic-conventions` 0.32, rust-minor batches

---

## 26.05_3

**Date:** 2026-05-05
**Crate version:** — never tagged; changes first shipped in 26.05_4 (`0.6.15`)

### Fixed
- **Embedded default configuration no longer emits a deprecation warning on first run** — the fallback configuration baked into the binary declared a `server { ... }` block; switched to `system { ... }` so fresh containers and binaries with no external config start cleanly
- **ACME DNS propagation checker** adapted to the `hickory-resolver` 0.26 API, restoring DNS-01 challenge verification

### Changed
- **Bundled KDL configurations use the `system` block** — sweeps the deprecated `server { ... }` keyword in the installer drop-in and the bundled examples. Pure keyword rename; the parser still accepts both
- **Dependency updates:** `hickory-resolver` 0.26.1

---

## 26.05_2

**Date:** 2026-05-03
**Crate version:** 0.6.13

### Added
- **Systemd service bootstrap in the install script** — the install script now installs a systemd unit, a sysusers snippet, and a starter config at `/etc/zentinel/zentinel.kdl` on Linux hosts running systemd. Service enable and start are opt-in via `--enable-service` (or `ZENTINEL_ENABLE_SERVICE=1`). An existing config file is preserved on re-install

---

## 26.05_1

**Date:** 2026-05-01
**Crate version:** 0.6.12

### Added
- **Per-SNI ACME certificates for multi-tenant TLS** — each `sni { ... }` block may carry its own `acme { ... }` configuration, so distinct hostnames on one listener can obtain and renew independent certificates

### Changed
- **Dependency updates**

---

## 26.04_7

**Date:** 2026-04-28
**Crate version:** 0.6.11

### Security
- **`rand` 0.9.2 → 0.9.4 in `zentinel-sim`** — closes [GHSA-cq8v-f236-94qc](https://github.com/advisories/GHSA-cq8v-f236-94qc), an unsoundness issue affecting `rand::rng()` with a custom logger

---

## 26.04_6

**Date:** 2026-04-25
**Crate version:** 0.6.10

### Security
- **`openssl` 0.10.77 → 0.10.78** — fixes four high-severity vulnerabilities: buffer overflows in `Deriver::derive` and `MdCtxRef::digest_final`, AES key-wrap bounds, and unchecked PSK/cookie callback lengths leaking memory to peers
- **`rand` 0.8.5 → 0.8.6** — unsoundness fix

### Documentation
- ACME configuration schema — documented `server-url`, `eab`, `key-type`, and `cloudflare` options

---

## 26.04_5

**Date:** 2026-04-20
**Crate version:** 0.6.9

### Added
- **Configurable ACME certificate key type** via `key-type`, supporting `ecdsa-p256` (default) and `ecdsa-p384`. Invalid values produce a clear config parse error

---

## 26.04_4

**Date:** 2026-04-19
**Crate version:** 0.6.8

### Added
- **Cloudflare DNS-01 provider** for ACME challenges, enabling wildcard certificate issuance via the Cloudflare DNS API v4, with zone ID caching
- **Custom ACME directory URLs** via `server-url`, supporting non-Let's Encrypt CAs such as ZeroSSL and Step-ca
- **External Account Binding (EAB)** for ACME account creation, required by providers like ZeroSSL; configured via an `eab { kid "..." hmac-key "..." }` block

### Fixed
- **SAN certificate renewal loop** — the renewal scheduler iterated every domain in a multi-domain certificate, triggering redundant renewals. It now checks only the primary domain

---

## 26.04_3

**Date:** 2026-04-16
**Crate version:** 0.6.7

### Security
- **`rand` unsoundness advisory** — updates the pingora fork to `rand` 0.9 across all pingora crates, plus direct and transitive bumps
- **`aes` 0.8 → 0.9** — migrates to cipher 0.5

### Changed
- Rust toolchain and MSRV raised to 1.94.1
- **Dependency updates:** `jsonschema` 0.46, `tiktoken-rs` 0.11

---

## 26.04_2

**Date:** 2026-04-10
**Crate version:** 0.6.6

### Security
- **`wasmtime` 43.0.0 → 43.0.1** — resolves 10 advisories, including **CVE-2026-34971**, a critical sandbox escape on aarch64 caused by miscompiled guest heap access in Cranelift, plus six medium-severity issues (out-of-bounds memory access, host panics) and three low-severity ones

---

## 26.04_1

**Date:** 2026-04-09
**Crate version:** 0.6.4

### Changed
- **Numeric route priorities** — `priority` now accepts integers and named aliases
- **Route matcher host extraction fix** — HTTP/2 and relative-URI support
- **Docker image GLIBC fix** — pinned to ubuntu-22.04
- **Gateway API conformance CI restored** — 42/235 baseline
- **Dependency updates:** sha2 0.11, hmac 0.13, tokio 1.51, hyper 1.9, wasmtime 43

---

## 26.03_1

**Date:** 2026-03-01
**Crate version:** 0.5.12

### Changed
- **Image optimization agent v0.2.0** — Content-Type header is now set correctly during response header phase (proxy commits headers before body filtering). Conversion fallback paths restore original Content-Type. Cache directory defaults to `~/.cache/zentinel/image-optimization` instead of requiring root access. Fixed event name `response_body` → `response_body_chunk` in agent manifest.

---

## 26.02_5

**Date:** 2026-02-27
**Crate version:** 0.5.11

### Added
- **`include` directive in single-file config** — `include "routes/*.kdl"` now works directly in `zentinel.kdl` when loaded via `Config::from_file()` or `zentinel --config`. Previously, include directives only worked through the multi-file loader (`--config-dir`). Includes support glob patterns, relative path resolution, recursive expansion, and circular include detection.

### Changed
- **Improved error message for `include` in raw KDL** — When `include` is encountered via `Config::from_kdl()` (raw string parsing), the error now explains to use `Config::from_file()` instead of showing the generic "unknown block" message.

---

## 26.02_4

**Date:** 2026-02-04
**Crate version:** 0.4.10

### Fixed
- **Install script** — `get_latest_version()` now queries `/releases` and selects the first release with actual binary assets, instead of relying on `/releases/latest` which could point to a release without binaries ([#67](https://github.com/zentinelproxy/zentinel/issues/67)).
- **Release workflow** — Version bump push to `main` now falls back to creating a PR when blocked by branch protection.
- **16 rustdoc warnings** — Fixed bare URLs, unclosed HTML tags, unresolved type references, and private module links across 10 files.
- **Clippy warnings** — Resolved warnings and migrated to updated dependency APIs.
- **`_build.yml` header comment** — Fixed misleading "Called by" reference.

### Changed
- **Pingora switched to fork** — All Pingora dependencies now point to `raskell-io/pingora` fork (rev `5847d5e`) which disables the prometheus protobuf default feature, removing the RUSTSEC-2024-0437 vulnerability.
- **Dependency updates:**
  - `cargo update` — 61 packages updated to latest compatible versions
  - reqwest 0.12 → 0.13 (feature renames: `rustls-tls` → `rustls`, `query` now opt-in)
  - jsonschema 0.40 → 0.41 (performance improvements)
  - bytes 1.9 → 1.11.1 (integer overflow fix)

### Added
- **CI workflow** (`.github/workflows/ci.yml`) — Formatting, clippy, tests, and docs checks on PRs and pushes to main.
- **Weekly audit workflow** (`.github/workflows/audit.yml`) — Runs `cargo audit` weekly, creates/updates GitHub issues on vulnerabilities.
- **Cargo audit ignore list** (`.cargo/audit.toml`) — Documented ignores for upstream-only advisories (daemonize, derivative, fxhash, rustls-pemfile).
- **Branch protection** — Required status checks (Formatting, Clippy, Tests, Documentation) on main.

---

## 26.02_3

**Date:** 2026-02-03
**Crate version:** 0.4.9

### Added
- **First-time user smoke tests** — Self-contained integration tests (`test_first_time_waf.sh`, `test_first_time_lua.sh`) that validate building Zentinel + an agent from source, wiring them together, and verifying end-to-end behavior. WAF test covers 8 scenarios (SQLi, XSS, path traversal, fail-open, recovery); Lua test covers 4 (header injection, blocking, fail-open).
- **`protocol-version` KDL config** — Agent blocks now accept `protocol-version "v2"` to explicitly select Protocol v2 for gRPC agents, instead of always defaulting to v1.
- **Makefile targets** — `test-first-time`, `test-first-time-waf`, `test-first-time-lua` for running smoke tests.

### Fixed
- **Example configs** — All configs in `config/examples/` now pass `zentinel test` validation.
- **Install script** — Removed stale linux-arm64 block, fixed sudo fallback.

### Changed
- **README** — Replaced Inference Gateway section with Use Cases overview; updated feature table with caching, WebSocket, hot reload details; linked to full features page.

---

## 26.02_1

**Date:** 2026-02-02
**Crate version:** 0.4.7

### Changed
- **Pingora 0.6 → 0.7** — Upgraded to upstream Pingora 0.7.0, removing the `raskell-io/pingora` security fork and all 16 `[patch.crates-io]` overrides. Zentinel now builds against upstream Pingora with zero patches.
  - `ForcedInvalidationKind` renamed to `ForcedFreshness` in cache layer
  - `range_header_filter` now accepts `max_multipart_ranges` parameter (defaults to 200)
- **Major dependency updates:**
  - thiserror 1.x → 2.0
  - redis 0.27 → 1.0 (distributed rate limiting)
  - criterion 0.6 → 0.8 (benchmarking)
  - instant-acme 0.7 → 0.8 (ACME client rewritten for new builder/stream API)
  - jsonschema 0.18 → 0.40 (validation module rewritten for new API: `JSONSchema` → `Validator`, `compile` → `draft7::new`)
  - quick-xml 0.37 → 0.39 (data masking agent: `unescape()` → `decode()`)
  - async-memcached 0.5 → 0.6
  - tiktoken-rs 0.6 → 0.9
  - sysinfo 0.37 → 0.38

### Security
- **Resolved all three security issues** previously requiring a Pingora fork:
  - [RUSTSEC-2026-0002](https://rustsec.org/advisories/RUSTSEC-2026-0002.html): `lru` crate vulnerability (fixed in upstream Pingora 0.7)
  - `atty` unmaintained dependency removed (fixed in upstream Pingora 0.7)
  - `protobuf` uncontrolled recursion bounded (fixed in upstream Pingora 0.7)

### Removed
- `[patch.crates-io]` section with 16 git overrides pointing to `raskell-io/pingora` fork

See the [blog post](https://zentinelproxy.io/blog/pingora-0-7-upgrade/) for a detailed writeup.

---

## 26.02_0

**Date:** 2026-01-29
**Crate version:** 0.4.5

### Added
- **Supply chain security for release pipeline**
  - SBOM generation in CycloneDX 1.5 and SPDX 2.3 formats via `cargo-sbom`
  - Binary signing with Sigstore cosign (keyless, GitHub Actions OIDC)
  - Container image signing with cosign and SBOM attestation via syft
  - SLSA v1.0 provenance via `slsa-github-generator` (Build Level 3)
  - Sigstore bundles (`.bundle`), SBOMs (`.cdx.json`, `.spdx.json`), and SLSA provenance (`.intoto.jsonl`) attached to every GitHub release
  - Supply chain verification commands in release notes

See [Supply Chain Security](/operations/supply-chain/) for verification procedures.

---

## 26.01_11

**Date:** 2026-01-29
**Crate version:** 0.4.5

### Changed
- **Performance:** Reduce per-request allocations in hot path
- **Performance:** Avoid cloning header modification maps per request
- **Performance:** Optimize agent header map construction

---

## 26.01_10

**Date:** 2026-01-27
**Crate version:** 0.4.3

### Fixed
- Prevent single connection failure from permanently marking upstream target unhealthy
- Update code for rand 0.9 and hickory-resolver 0.25 API changes
- Use pingora fork to resolve remaining security vulnerabilities

### Security
- Resolve dependabot security alerts

### Changed
- **Dependency updates:**
  - opentelemetry_sdk 0.27 → 0.31
  - opentelemetry-otlp 0.27 → 0.31
  - hickory-resolver 0.24 → 0.25
  - rand 0.8 → 0.9
  - wasmtime 40.0 → 41.0
  - notify 6.1 → 8.2
  - validator 0.18 → 0.20
  - nix 0.29 → 0.31
  - webpki-roots 0.26 → 1.0

---

## 26.01_9

**Date:** 2026-01-21
**Crate version:** 0.4.2

### Added
- Sticky load balancing algorithm support in simulation framework

### Changed
- Improved install script user experience

---

## 26.01_8

**Date:** 2026-01-21
**Crate version:** 0.4.1

### Changed
- **Dependency updates** with breaking change fixes:
  - prost 0.13 → 0.14 (with tonic ecosystem upgrade to 0.14)
  - tonic 0.12 → 0.14 (TLS features renamed: `tls` → `tls-ring`, `tls-roots` → `tls-native-roots`)
  - tungstenite 0.24 → 0.28 (`Message::Text` now uses `Utf8Bytes`)
  - sysinfo 0.31 → 0.37 (`RefreshKind::new()` → `RefreshKind::nothing()`)
  - toml 0.8 → 0.9
  - brotli 7.0 → 8.0
  - directories 5.0 → 6.0
  - signal-hook 0.3 → 0.4
  - jsonschema 0.17 → 0.18
  - ip2location 0.5 → 0.6
  - tokio-tungstenite 0.24 → 0.28
- GitHub Actions updates: checkout v6, github-script v8, docker/build-push-action v6

### Fixed
- WebSocket test compatibility with tungstenite 0.28 API changes
- System metrics collection with sysinfo 0.37 API changes

---

## 26.01_7

**Date:** 2026-01-21
**Crate version:** 0.4.0

### Added
- **DNS-01 ACME challenge support** for wildcard certificate issuance
  - Modular DNS provider system with `DnsProvider` trait
  - Hetzner DNS provider implementation
  - Generic webhook provider for custom DNS integrations
  - DNS propagation checking with configurable nameservers
  - Secure credential loading from files or environment variables
- New configuration options for DNS-01 challenges:
  - `challenge-type` option in ACME config (`http-01` or `dns-01`)
  - `dns-provider` block with provider-specific settings
  - `propagation` block for DNS propagation check tuning
- Integration tests for DNS providers using wiremock

### Changed
- ACME scheduler now supports both HTTP-01 and DNS-01 renewal flows
- ACME client extended with `create_order_dns01()` method

---

## 26.01_6

**Date:** 2026-01-14
**Crate version:** 0.3.1

### Added
- Agent Protocol v2 with connection pooling and load balancing
- Reverse connection support for NAT traversal
- gRPC transport with bidirectional streaming
- Request cancellation support
- Prometheus metrics export for agent pools

### Changed
- Improved agent health tracking with circuit breakers
- Better error messages for configuration validation

### Fixed
- Connection leak in agent pool under high load
- Race condition in route matching cache

---

## 26.01_4

**Date:** 2026-01-11
**Crate version:** 0.3.0

### Added
- Initial Agent Protocol v2 implementation
- Binary UDS transport for lower latency
- Connection pooling with multiple strategies (RoundRobin, LeastConnections, HealthBased)
- WASM agent runtime using Wasmtime

### Changed
- Agent protocol documentation reorganized into v1/ and v2/

---

## 26.01_3

**Date:** 2026-01-05
**Crate version:** 0.2.3

See [GitHub Release](https://github.com/zentinelproxy/zentinel/releases/tag/26.01_3).

---

## 26.01_0

**Date:** 2026-01-01
**Crate version:** 0.2.0

First release using CalVer tagging.

See [GitHub Release](https://github.com/zentinelproxy/zentinel/releases/tag/26.01_0).

---

## 25.12

**Crate versions:** 0.1.0 -- 0.1.8
**Releases:** 25.12_0 through 25.12_19

Initial public release series. Core proxy, routing, upstreams, agent system, observability, and KDL configuration.

See [GitHub Releases](https://github.com/zentinelproxy/zentinel/releases?q=25.12) for individual release notes.

---

## Links

- [GitHub Releases](https://github.com/zentinelproxy/zentinel/releases)
- [Versioning](../versioning/) -- CalVer/SemVer scheme, LTS windows, version mapping
- [Supply Chain Security](/operations/supply-chain/) -- Verify binary and container authenticity

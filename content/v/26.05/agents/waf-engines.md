+++
title = "WAF Engines"
weight = 5
updated = 2026-03-04
+++

Zentinel ships three WAF agents, each with different trade-offs in detection approach, rule ecosystem, and operational requirements. This guide helps you choose the right one for your deployment.

- **WAF** — Pure Rust, 285 hand-tuned rules with anomaly scoring, statistical classification, API security, and bot detection.
- **ZentinelSec** — Pure Rust reimplementation of ModSecurity with full OWASP CRS support, 10-30x faster than the C++ original.
- **ModSecurity** — C libmodsecurity wrapper providing maximum CRS compatibility for existing ModSecurity deployments.

## Quick comparison

| Feature | WAF | ZentinelSec | ModSecurity |
|---------|-----|-------------|-------------|
| Detection approach | Compiled pattern matchers + statistical classification | SecLang rule engine (pure Rust) | SecLang rule engine (C libmodsecurity) |
| Detection rules | 285 | 800+ CRS | 800+ CRS |
| SecLang support | No | Yes | Yes |
| Anomaly scoring | Built-in | Via CRS | Via CRS |
| API security | GraphQL, JWT, schema validation | No | No |
| Bot detection | Behavioral + TLS fingerprinting | No | UA only |
| Dependencies | Pure Rust | Pure Rust | libmodsecurity (C) |
| Binary size | ~6 MB | ~10 MB | ~50 MB |
| Throughput | 1.6M req/s | 6.2M req/s | 207K req/s |
| Latency (p99) | <5 µs | <1 µs | ~15 ms |

## WAF agent

The WAF agent is a purpose-built Rust WAF with 285 detection rules compiled directly into the binary. It combines pattern matching with anomaly scoring — cumulative risk scores with configurable thresholds — and n-gram-based statistical classification to reduce false positives compared to pattern-only approaches. It also includes API security features (GraphQL protection, JWT validation, OpenAPI/GraphQL schema validation), bot detection with TLS fingerprinting, sensitive data detection, and virtual patching for known CVEs (Log4Shell, Spring4Shell, Shellshock).

No rule files are needed. Detection logic is compiled in, which gives it the lowest startup time and smallest binary (~6 MB).

```kdl
agents {
    agent "waf" type="waf" {
        unix-socket "/var/run/zentinel/waf.sock"
        events "request_headers" "request_body"
        timeout-ms 50
        failure-mode "closed"
    }
}
```

See the [WAF agent registry page](https://registry.zentinelproxy.io/agents/waf/) for the full feature list and configuration options.

## ZentinelSec agent

ZentinelSec is a pure Rust reimplementation of the ModSecurity rule engine, powered by [zentinel-modsec](https://github.com/zentinelproxy/zentinel-modsec). It parses and evaluates standard SecLang `SecRule` directives — including `@detectSQLi`, `@detectXSS`, `@contains`, and `@rx` operators — with zero C dependencies. It supports the full OWASP Core Rule Set (800+ rules) and benchmarks at 10-30x the performance of the C++ libmodsecurity.

Install it with `cargo install` or `zentinel bundle install zentinelsec` — no system libraries required.

```kdl
agents {
    agent "zentinelsec" type="waf" {
        unix-socket "/var/run/zentinel/zentinelsec.sock"
        events "request_headers" "request_body"
        timeout-ms 100
        failure-mode "closed"
    }
}
```

Load CRS rules by passing them to the agent binary:

```bash
zentinel-zentinelsec-agent \
  --socket /var/run/zentinel/zentinelsec.sock \
  --rules /etc/modsecurity/crs/crs-setup.conf \
  --rules "/etc/modsecurity/crs/rules/*.conf"
```

See the [ZentinelSec registry page](https://registry.zentinelproxy.io/agents/zentinelsec/) for performance benchmarks and configuration options.

## ModSecurity agent

The ModSecurity agent wraps [libmodsecurity](https://github.com/owasp-modsecurity/ModSecurity) (the C library behind ModSecurity v3) via Rust FFI bindings. It provides maximum compatibility with existing ModSecurity deployments and the OWASP CRS, including libinjection-based operators.

This agent requires libmodsecurity >= 3.0.13 installed on your system (`brew install modsecurity` on macOS, `apt install libmodsecurity-dev` on Ubuntu/Debian).

```kdl
agents {
    agent "modsec" type="waf" {
        unix-socket "/var/run/zentinel/modsec.sock"
        events "request_headers" "request_body"
        timeout-ms 200
        failure-mode "closed"
    }
}
```

Load CRS rules by passing them to the agent binary:

```bash
zentinel-modsec-agent \
  --socket /var/run/zentinel/modsec.sock \
  --rules /etc/modsecurity/crs/crs-setup.conf \
  --rules "/etc/modsecurity/crs/rules/*.conf"
```

See the [ModSecurity registry page](https://registry.zentinelproxy.io/agents/modsec/) for prerequisites and configuration options.

## Detection accuracy

We tested all three engines with [wafworth](https://github.com/zentinelproxy/wafworth), an open-source WAF testing framework, using 598 test cases across 18 OWASP-aligned categories. All three engines ran the same 67-rule baseline in direct-deny mode (no anomaly scoring, no full CRS).

| Metric | WAF | ZentinelSec | ModSecurity |
|--------|:---:|:---:|:---:|
| Detection rate | **43.1%** | 38.7% | 32.1% |
| False-positive rate | 9.0% | **2.5%** | **2.5%** |
| Precision | 94.9% | **98.4%** | 98.1% |
| F1 score | **59.2%** | 55.5% | 48.4% |
| Balanced accuracy | 67.0% | **68.1%** | 64.8% |
| p95 latency | **2.8 ms** | 3.1 ms | 2.9 ms |

> **Note:** Detection rates of 32-43% reflect the 67-rule baseline, not full CRS. A full CRS PL1 deployment would likely score 60-80% detection with a 1-3% FP rate. See the [full blog post](/blog/waf-agent-comparison/) for methodology, per-category breakdowns, and detailed analysis.

Key takeaways:

- **WAF** had the highest raw detection rate (43.1%) due to compiled-in pattern matchers for CVE signatures, scanner fingerprints, and path traversal. However, it also had the highest false-positive rate (9.0%).
- **ZentinelSec** achieved the best balanced accuracy (68.1%) and lowest false-positive rate (2.5%), making it the safest choice when both detection and operational impact matter. Its pure Rust `@detectSQLi` implementation caught 66.7% of SQLi tests — nearly double the WAF agent's 37.5%.
- **ModSecurity** trailed ZentinelSec slightly despite using the same rules, revealing differences in operator implementation between the Rust and C engines.
- All three engines add less than 3 ms at p95, well below the latency of a typical upstream backend.

## Decision guide

**Use WAF when** you need API security features (GraphQL protection, JWT validation, schema validation), bot detection with TLS fingerprinting, or threat intelligence integration. It provides the broadest detection surface out of the box with zero rule files, making it ideal for teams that want a single agent covering web attacks, API abuse, and automated threats.

**Use ZentinelSec when** you need full OWASP CRS compatibility without C dependencies. It offers the best balanced accuracy (lowest false positives while maintaining strong detection), easy deployment via `cargo install`, and 10-30x better performance than C libmodsecurity. This is the recommended default for production deployments focused on CRS compliance.

**Use ModSecurity when** you have existing ModSecurity/SecLang deployments with complex custom rules that depend on libmodsecurity-specific features, or when maximum compatibility with the C implementation is required for compliance reasons.

> **Note:** You can run multiple WAF agents simultaneously on different routes. For example, use the WAF agent on API routes for GraphQL/JWT protection and ZentinelSec with full CRS on your web application routes.

## Configuration reference

- [WAF configuration block](../configuration/waf/) — Global WAF settings: engine selection, rule sets, body inspection, paranoia levels
- [Agent configuration](../configuration/agents/) — Agent transport, pooling, circuit breakers, timeouts, and failure modes

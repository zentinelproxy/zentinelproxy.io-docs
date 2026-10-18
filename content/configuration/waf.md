+++
title = "WAF"
weight = 10
updated = 2026-10-18
+++

The `waf` block configures Zentinel's Web Application Firewall (WAF) settings. WAF protection is implemented via external agents, but this block provides global WAF configuration including engine selection, rule sets, and body inspection policies.

{% callout(type="warning", title="The top-level waf block is not wired into the proxy (26.10_3)") %}
The proxy runs no WAF engine from the `waf` block: no request is inspected or
blocked because of it. To keep that from passing silently, configuration validation
**rejects a `waf` block whose `mode` is anything other than `"off"`** — and
`mode` defaults to `"prevention"`, so every example on this page except an
explicit `mode "off"` fails to load with *"WAF mode is set to 'prevention' but
the WAF engine is not yet wired into the proxy runtime"*.

WAF protection today comes from a **WAF agent** attached to routes through a
filter — see [Integration with Agents](#integration-with-agents) below and
[WAF Engines](/agents/waf-engines/). `engine`, `audit-log` and `ruleset` are
parsed but used by nothing; the examples for them are shown as fragments and
cannot be used as they stand.

The one part the proxy does use is [`body-inspection`](#body-inspection): it
decides whether request bodies are buffered (and optionally decompressed) for
the agents on a route. It only takes effect inside a `waf` block, so write it
with `mode "off"`.
{% end %}

## Basic Configuration

```fragment,kdl
waf {
    engine "coraza"
    mode "prevention"
    audit-log #true

    ruleset {
        custom-rules-dir "/etc/zentinel/waf/crs"
        paranoia-level 2
    }

    body-inspection {
        inspect-request-body #true
        max-inspection-bytes 1048576
    }
}
```

## Engine Selection

Zentinel supports multiple WAF engines via external agents:

```fragment,kdl
waf {
    engine "coraza"  // Default, recommended
}
```

| Engine | Description |
|--------|-------------|
| `coraza` | Modern, Go-based WAF engine (default) |
| `modsecurity` | libModSecurity-based engine |
| `custom` | Custom engine implementation |

### Custom Engine

For custom WAF implementations:

```fragment,kdl
waf {
    engine "my-custom-waf"
}
```

The engine name is passed to your WAF agent, which can use it to select the appropriate implementation.

## WAF Mode

Control how the WAF handles detected threats:

```fragment,kdl
waf {
    mode "prevention"  // Block malicious requests
}
```

| Mode | Behavior |
|------|----------|
| `off` | WAF disabled |
| `detection` | Log threats but allow requests through |
| `prevention` | Block malicious requests (default) |

### Detection Mode

Use detection mode when first deploying WAF to assess impact:

```fragment,kdl
waf {
    mode "detection"
    audit-log #true  // Log all detections
}
```

Review audit logs to tune rules before switching to prevention mode.

## Audit Logging

Enable detailed logging of WAF decisions:

```fragment,kdl
waf {
    audit-log #true
}
```

Audit logs include:
- Matched rules and their IDs
- Request details (headers, body excerpts)
- Decision (allow/block)
- Tags and scores

Logs are written in JSON format to the configured log output.

## Rule Set Configuration

### Basic Ruleset

```fragment,kdl
waf {
    ruleset {
        custom-rules-dir "/etc/zentinel/waf/crs"
        paranoia-level 1
    }
}
```

### CRS Version and Custom Rules

The ZentinelSec engine loads and evaluates the stock OWASP Core Rule Set v4. Configure the Core Rule Set version and custom rules directory:

```fragment,kdl
waf {
    ruleset {
        crs-version "4.0"
        custom-rules-dir "/etc/zentinel/waf/custom-rules"
        paranoia-level 2
    }
}
```

### Paranoia Level

The paranoia level controls rule sensitivity:

```fragment,kdl
waf {
    ruleset {
        paranoia-level 2
    }
}
```

| Level | Description | Use Case |
|-------|-------------|----------|
| `1` | Basic protection, minimal false positives | Production, general traffic |
| `2` | Standard protection | Most applications |
| `3` | Strict protection, more false positives | High-security applications |
| `4` | Maximum protection, highest false positives | Maximum security environments |

**Recommendation:** Start with level 1 or 2, then increase based on your false positive tolerance.

### Rule Exclusions

Exclude specific rules to reduce false positives:

```fragment,kdl
waf {
    ruleset {
        custom-rules-dir "/etc/zentinel/waf/crs"
        paranoia-level 2

        // Exclude by rule ID (global scope)
        exclusion "942100" "942200" scope="global"

        // Exclude for specific paths
        exclusion "941100" scope="path=/api/upload"

        // Exclude for specific hosts
        exclusion "920350" scope="host=internal.example.com"
    }
}
```

#### Exclusion Scopes

| Scope | Description |
|-------|-------------|
| `global` | Exclude rule everywhere |
| `path=<pattern>` | Exclude for a specific URL path |
| `host=<hostname>` | Exclude for a specific host |

## Body Inspection

Configure how request and response bodies are inspected:

```kdl
waf {
    mode "off"  // required: any other mode fails validation (see above)
    body-inspection {
        inspect-request-body #true
        inspect-response-body #false
        max-inspection-bytes 1048576
        content-types "application/json" "application/x-www-form-urlencoded" "text/xml"
        decompress #true
        max-decompression-ratio 100
    }
}
```

### Body Inspection Options

| Option | Default | Description |
|--------|---------|-------------|
| `inspect-request-body` | `true` | Inspect request bodies |
| `inspect-response-body` | `false` | Inspect response bodies |
| `max-inspection-bytes` | `1048576` | Maximum bytes to buffer for inspection |
| `content-types` | See below | Content types eligible for inspection, as arguments (`content-types "application/json" "text/xml"`) |
| `decompress` | `false` | Decompress bodies before inspection |
| `max-decompression-ratio` | `100` | Max compression ratio (zip bomb protection) |

### Default Content Types

When not specified, these content types are inspected:
- `application/x-www-form-urlencoded`
- `multipart/form-data`
- `application/json`
- `application/xml`
- `text/xml`

### Decompression Security

When `decompress` is enabled:

```kdl
waf {
    mode "off"
    body-inspection {
        decompress #true
        max-decompression-ratio 50  // Reject if compressed/decompressed ratio > 50x
    }
}
```

This protects against zip bomb attacks by limiting the decompression ratio.

## Complete Example

```fragment,kdl
waf {
    engine "coraza"
    mode "prevention"
    audit-log #true

    ruleset {
        crs-version "4.0"
        custom-rules-dir "/etc/zentinel/waf/custom-rules"
        paranoia-level 2
        anomaly-threshold 5

        // API endpoints that accept raw data
        exclusion "942100" "942200" "942260" scope="path=/api/webhooks"

        // Large file upload endpoint
        exclusion "920350" scope="path=/api/upload"
    }

    body-inspection {
        inspect-request-body #true
        inspect-response-body #false
        max-inspection-bytes 5242880
        content-types "application/json" "application/xml" "multipart/form-data"
        decompress #true
        max-decompression-ratio 100
    }
}
```

## Integration with Agents

Requests are inspected by a WAF agent. Define the agent, wrap it in an `agent`
filter, and list the filter on each route that should be inspected:

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

agents {
    agent "waf-agent" type="waf" {
        unix-socket "/var/run/zentinel/waf.sock"
        events "request_headers" "request_body"
        timeout-ms 200
        failure-mode "closed"
    }
}

filters {
    filter "waf" {
        type "agent"
        agent "waf-agent"
    }
}

routes {
    route "api" {
        matches { path-prefix "/api/" }
        upstream "backend"
        filters "waf"
    }
}

upstreams {
    upstream "backend" {
        target "127.0.0.1:3000"
    }
}
```

Rule sets, paranoia level and exclusions are configured in the agent itself
(its own configuration or the agent's `config` block); see
[WAF Engines](/agents/waf-engines/) and [Agents](../agents/).

## Metrics

The proxy exports no WAF-specific metrics. Calls to a WAF agent are covered by
the agent metrics (`zentinel_agent_requests_total`,
`zentinel_agent_latency_seconds`, `zentinel_agent_timeouts_total`); see
[Metrics](/reference/metrics/). Detection details are reported by the agent.

## Default Values

| Setting | Default |
|---------|---------|
| `engine` | `coraza` |
| `mode` | `prevention` |
| `audit-log` | `true` |
| `ruleset.crs-version` | `3.3.4` |
| `ruleset.paranoia-level` | `1` |
| `ruleset.anomaly-threshold` | `5` |
| `body-inspection.inspect-request-body` | `true` |
| `body-inspection.max-inspection-bytes` | `1048576` |
| `body-inspection.decompress` | `false` |
| `body-inspection.max-decompression-ratio` | `100` |

## See Also

- [Agents](../agents/) - WAF agent configuration
- [Security Hardening](../../operations/security-hardening/) - Security best practices
- [Filters](../filters/) - Filter chain configuration

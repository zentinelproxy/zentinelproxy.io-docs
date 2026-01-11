+++
title = "WAF"
weight = 10
+++

The `waf` block configures Sentinel's Web Application Firewall (WAF) settings. WAF protection is implemented via external agents, but this block provides global WAF configuration including engine selection, rule sets, and body inspection policies.

## Basic Configuration

```kdl
waf {
    engine "coraza"
    mode "prevention"
    audit-log #true

    ruleset {
        paths "/etc/sentinel/waf/crs"
        paranoia-level 2
    }

    body-inspection {
        inspect-request-body #true
        max-body-inspection-bytes 1048576
    }
}
```

## Engine Selection

Sentinel supports multiple WAF engines via external agents:

```kdl
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

```kdl
waf {
    engine "my-custom-waf"
}
```

The engine name is passed to your WAF agent, which can use it to select the appropriate implementation.

## WAF Mode

Control how the WAF handles detected threats:

```kdl
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

```kdl
waf {
    mode "detection"
    audit-log #true  // Log all detections
}
```

Review audit logs to tune rules before switching to prevention mode.

## Audit Logging

Enable detailed logging of WAF decisions:

```kdl
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

```kdl
waf {
    ruleset {
        paths "/etc/sentinel/waf/crs"
        paranoia-level 1
    }
}
```

### Multiple Rule Paths

Load rules from multiple directories:

```kdl
waf {
    ruleset {
        paths "/etc/sentinel/waf/crs" "/etc/sentinel/waf/custom"
        paranoia-level 2
    }
}
```

Rules are loaded in order. Custom rules in later paths can override earlier ones.

### Paranoia Level

The paranoia level controls rule sensitivity:

```kdl
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

```kdl
waf {
    ruleset {
        paths "/etc/sentinel/waf/crs"
        paranoia-level 2

        exclusions {
            // Exclude by rule ID
            rule-exclusion {
                rule-ids 942100 942200
                scope "global"
            }

            // Exclude for specific paths
            rule-exclusion {
                rule-ids 941100
                scope "path"
                paths "/api/upload" "/api/import"
            }

            // Exclude for specific parameters
            rule-exclusion {
                rule-ids 942100
                scope "parameter"
                parameters "content" "body" "raw_data"
            }
        }
    }
}
```

#### Exclusion Scopes

| Scope | Description |
|-------|-------------|
| `global` | Exclude rule everywhere |
| `path` | Exclude for specific URL paths |
| `parameter` | Exclude for specific request parameters |

## Body Inspection

Configure how request and response bodies are inspected:

```kdl
waf {
    body-inspection {
        inspect-request-body #true
        inspect-response-body #false
        max-body-inspection-bytes 1048576
        content-types "application/json" "application/x-www-form-urlencoded" "text/xml"
        decompress #true
        max-decompression-ratio 100.0
    }
}
```

### Body Inspection Options

| Option | Default | Description |
|--------|---------|-------------|
| `inspect-request-body` | `false` | Inspect request bodies |
| `inspect-response-body` | `false` | Inspect response bodies |
| `max-body-inspection-bytes` | `1048576` | Maximum bytes to buffer for inspection |
| `content-types` | See below | Content types eligible for inspection |
| `decompress` | `false` | Decompress bodies before inspection |
| `max-decompression-ratio` | `100.0` | Max compression ratio (zip bomb protection) |

### Default Content Types

When not specified, these content types are inspected:
- `application/json`
- `application/x-www-form-urlencoded`
- `text/xml`
- `application/xml`
- `text/plain`

### Decompression Security

When `decompress` is enabled:

```kdl
waf {
    body-inspection {
        decompress #true
        max-decompression-ratio 50.0  // Reject if compressed/decompressed ratio > 50x
    }
}
```

This protects against zip bomb attacks by limiting the decompression ratio.

## Complete Example

```kdl
waf {
    engine "coraza"
    mode "prevention"
    audit-log #true

    ruleset {
        paths "/etc/sentinel/waf/crs" "/etc/sentinel/waf/custom-rules"
        paranoia-level 2

        exclusions {
            // API endpoints that accept raw data
            rule-exclusion {
                rule-ids 942100 942200 942260
                scope "path"
                paths "/api/webhooks" "/api/import"
            }

            // Large file upload endpoint
            rule-exclusion {
                rule-ids 920350
                scope "path"
                paths "/api/upload"
            }
        }
    }

    body-inspection {
        inspect-request-body #true
        inspect-response-body #false
        max-body-inspection-bytes 5242880  // 5MB
        content-types "application/json" "application/xml" "multipart/form-data"
        decompress #true
        max-decompression-ratio 100.0
    }
}
```

## Integration with Agents

The `waf` block configures global settings. To actually process requests through WAF, configure a WAF agent:

```kdl
waf {
    engine "coraza"
    mode "prevention"
    ruleset {
        paths "/etc/sentinel/waf/crs"
        paranoia-level 2
    }
}

agents {
    agent "waf-agent" type="waf" {
        unix-socket "/var/run/sentinel/waf.sock"
        events "request_headers" "request_body"
        timeout-ms 200
        failure-mode "closed"
    }
}

routes {
    route "api" {
        matches { path-prefix "/api/" }
        upstream "backend"
        agents "waf-agent"
    }
}
```

The WAF configuration is passed to the agent on startup. The agent uses these settings to configure its rule engine.

## Metrics

WAF operations are tracked via Prometheus metrics:

| Metric | Labels | Description |
|--------|--------|-------------|
| `sentinel_waf_requests_total` | `mode`, `decision` | Total WAF evaluations |
| `sentinel_waf_blocked_total` | `rule_id` | Blocked requests by rule |
| `sentinel_waf_detection_total` | `rule_id` | Detections (all modes) |
| `sentinel_waf_latency_seconds` | | WAF evaluation latency |

## Default Values

| Setting | Default |
|---------|---------|
| `engine` | `coraza` |
| `mode` | `prevention` |
| `audit-log` | `false` |
| `ruleset.paranoia-level` | `1` |
| `body-inspection.inspect-request-body` | `false` |
| `body-inspection.max-body-inspection-bytes` | `1048576` |
| `body-inspection.decompress` | `false` |
| `body-inspection.max-decompression-ratio` | `100.0` |

## See Also

- [Agents](../agents/) - WAF agent configuration
- [Security Hardening](../../operations/security-hardening/) - Security best practices
- [Filters](../filters/) - Filter chain configuration

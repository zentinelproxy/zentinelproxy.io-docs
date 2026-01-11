+++
title = "Configuration Playground"
weight = 6
+++

Try Sentinel configurations in your browser without installing anything.

## What is the Playground?

The Sentinel Configuration Playground is a browser-based tool that lets you:

- **Validate configurations** - Check syntax and catch errors before deploying
- **Simulate routing** - Test which route matches a given request
- **Trace decisions** - Understand why routes matched (or didn't match)
- **Preview policies** - See applied timeouts, rate limits, and caching
- **Inspect agent hooks** - Visualize which agents would fire and in what order

The playground runs entirely in your browser using WebAssembly - no data is sent to any server.

## Try It

Visit the playground at:

**[sentinel.raskell.io/playground](https://sentinel.raskell.io/playground)**

## Quick Example

### 1. Enter a Configuration

Paste or type your KDL configuration:

```kdl
server { }

listeners {
    listener "http" {
        address "0.0.0.0:8080"
    }
}

routes {
    route "api" {
        matches {
            path-prefix "/api/"
        }
        upstream "backend"
    }

    route "health" {
        priority "high"
        matches {
            path "/health"
        }
        service-type "builtin"
        builtin-handler "health"
    }

    route "static" {
        priority "low"
        matches {
            path-prefix "/"
        }
        upstream "static-backend"
    }
}

upstreams {
    upstream "backend" {
        targets {
            target { address "api.internal:8080" }
            target { address "api.internal:8081" }
        }
        load-balancing "round-robin"
    }

    upstream "static-backend" {
        targets {
            target { address "static.internal:80" }
        }
    }
}
```

### 2. Validate

Click **Validate** to check your configuration. You'll see:

- **Errors** - Syntax issues or invalid values (must fix)
- **Warnings** - Potential misconfigurations (review recommended)
- **Effective Config** - Your config with all defaults applied

### 3. Simulate a Request

Enter request details:

| Field | Example |
|-------|---------|
| Method | `GET` |
| Host | `example.com` |
| Path | `/api/users` |
| Headers | `authorization: Bearer token123` |
| Query | `page=1&limit=10` |

Click **Simulate** to see:

- **Matched Route** - Which route handles this request
- **Match Trace** - Step-by-step evaluation of each route
- **Applied Policies** - Timeouts, rate limits, buffering settings
- **Upstream Selection** - Which backend target would receive the request
- **Agent Hooks** - Which agents would process this request

## Understanding the Match Trace

The match trace shows how Sentinel evaluates routes:

```
Route: health (priority: high)
├─ path = "/health" → FAILED (request path is "/api/users")
└─ Result: NO MATCH

Route: api (priority: normal)
├─ path-prefix = "/api/" → PASSED
└─ Result: MATCHED ✓

Route: static (priority: low)
└─ Skipped: Higher priority route already matched
```

This helps you debug routing issues and understand the evaluation order.

## Validation Checks

The playground validates:

| Check | Description |
|-------|-------------|
| Syntax | KDL parsing and structure |
| Required fields | Listeners, routes, upstreams |
| References | Upstream and agent references exist |
| Duplicates | No duplicate route or upstream IDs |
| Policy conflicts | Incompatible settings |

### Example Warnings

```
⚠ ROUTE_NO_UPSTREAM
  Route 'api' has no upstream defined

⚠ UNDEFINED_UPSTREAM
  Route 'web' references undefined upstream 'missing-backend'

⚠ SHADOW_NO_BODY_BUFFER
  Shadow config on POST route without buffer_body=true;
  request bodies won't be mirrored
```

## Route Priority Simulation

Test how priority affects route matching:

```kdl
routes {
    # High priority - matches first
    route "maintenance" {
        priority "high"
        matches {
            header "X-Maintenance" "true"
        }
        upstream "maintenance-backend"
    }

    # Normal priority
    route "api" {
        matches {
            path-prefix "/api/"
        }
        upstream "api-backend"
    }

    # Low priority - catch-all
    route "fallback" {
        priority "low"
        matches {
            path-prefix "/"
        }
        upstream "web-backend"
    }
}
```

Simulate requests with different headers to see priority in action.

## Load Balancer Simulation

The playground simulates deterministic load balancing:

```kdl
upstreams {
    upstream "backend" {
        targets {
            target { address "10.0.0.1:8080" weight 3 }
            target { address "10.0.0.2:8080" weight 2 }
            target { address "10.0.0.3:8080" weight 1 }
        }
        load-balancing "weighted"
    }
}
```

For algorithms like `round-robin` and `weighted`, the simulation shows which target would be selected based on the request's cache key.

For stateful algorithms (`least-connections`, `peak-ewma`), the simulation explains that actual selection depends on runtime state.

## Agent Hook Visualization

See which agents would process a request:

```kdl
routes {
    route "api" {
        matches {
            path-prefix "/api/"
        }
        upstream "backend"
        filters ["rate-limit", "auth"]
        waf-enabled #true
    }
}

filters {
    filter "rate-limit" {
        type "agent"
        agent "rate-limiter"
        timeout-ms 50
    }

    filter "auth" {
        type "agent"
        agent "auth-service"
        timeout-ms 100
        failure-mode "closed"
    }
}
```

The simulation shows:

```
Agent Hooks:
1. rate-limiter (on_request_headers, timeout: 50ms, fail: open)
2. auth-service (on_request_headers, timeout: 100ms, fail: closed)
3. waf (on_request_headers, timeout: 500ms, fail: closed)
4. waf (on_request_body, timeout: 1000ms, max: 1MB)
```

## Use Cases

### Debugging Route Mismatches

When requests aren't routed as expected:

1. Paste your production config
2. Enter the problematic request details
3. Review the match trace to see which condition failed

### Testing Configuration Changes

Before deploying config updates:

1. Paste your new config
2. Validate for errors
3. Simulate critical request paths
4. Verify expected routing behavior

### Learning KDL Syntax

The playground provides immediate feedback on syntax errors with helpful hints:

```
Error at line 12, column 5:
  Expected node name, found '}'

Hint: Did you forget to close a previous block?
```

### Sharing Configurations

The playground URL includes your configuration, so you can share links for:

- Bug reports with reproduction configs
- Documentation examples
- Team configuration reviews

## Limitations

The playground simulates routing logic but cannot:

- Make actual HTTP requests
- Test real upstream connectivity
- Simulate runtime state (active connections, latencies)
- Execute agent logic
- Test TLS certificates

For full integration testing, use Sentinel's `--dry-run` mode or a staging environment.

## Building from Source

The playground is built from the `sentinel-playground-wasm` crate:

```bash
# Install wasm-pack
cargo install wasm-pack

# Build the WASM module
cd crates/playground-wasm
wasm-pack build --target web

# Output is in pkg/
ls pkg/
# sentinel_playground_wasm.js
# sentinel_playground_wasm_bg.wasm
# sentinel_playground_wasm.d.ts
```

## API Reference

For embedding the playground or building tools, the WASM module exports:

| Function | Description |
|----------|-------------|
| `validate(kdl)` | Validate config, returns errors/warnings/effective config |
| `simulate(kdl, request)` | Simulate routing, returns match decision and trace |
| `get_normalized_config(kdl)` | Get config with all defaults applied |
| `create_sample_request(method, host, path)` | Create a request object for simulation |
| `get_version()` | Get the playground version |

### JavaScript Example

```javascript
import init, { validate, simulate } from 'sentinel-playground-wasm';

await init();

// Validate
const validation = validate(configKdl);
if (!validation.valid) {
    console.error('Errors:', validation.errors);
}

// Simulate
const request = JSON.stringify({
    method: 'GET',
    host: 'example.com',
    path: '/api/users',
    headers: {},
    query_params: {}
});

const decision = simulate(configKdl, request);
console.log('Matched:', decision.matched_route?.id);
console.log('Trace:', decision.match_trace);
```

## Next Steps

- [Basic Configuration](../basic-configuration/) - Learn the full configuration syntax
- [First Route](../first-route/) - Configure your first routing rules
- [Configuration Reference](/configuration/) - Complete configuration options

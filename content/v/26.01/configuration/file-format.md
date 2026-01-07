+++
title = "File Format"
weight = 1
+++

Sentinel uses [KDL](https://kdl.dev/) as its primary configuration format. KDL is a human-friendly document language that's easy to read, write, and diff.

## Why KDL?

| Feature | Benefit |
|---------|---------|
| **Human-readable** | Clean syntax without excessive punctuation |
| **Git-friendly** | Diffs are clear and meaningful |
| **Typed values** | Numbers, strings, booleans, null |
| **Comments** | Both line (`//`) and block (`/* */`) |
| **Hierarchical** | Natural nesting for configuration blocks |

## Basic Syntax

### Nodes

KDL documents are made of nodes. Each node has a name and optional values/properties:

```kdl
// Simple node
server

// Node with a value
worker-threads 4

// Node with a property
listener "http" address="0.0.0.0:8080"

// Node with children (block)
server {
    worker-threads 4
    max-connections 10000
}
```

### Values and Properties

**Values** are positional arguments:
```kdl
route "api"           // "api" is a value
targets "10.0.0.1" "10.0.0.2"  // Multiple values
```

**Properties** are named with `=`:
```kdl
target address="10.0.0.1" weight=5
health-check type="http" interval-secs=10
```

### Data Types

```kdl
// Strings (quoted)
name "my-service"

// Numbers (integer or float)
port 8080
weight 1.5

// Booleans
enabled true
disabled false

// Null
optional-field null
```

### Comments

```kdl
// Line comment

/* Block comment
   spanning multiple
   lines */

server {
    worker-threads 4  // Inline comment
}
```

## File Structure

A typical Sentinel configuration has these top-level blocks:

```kdl
// Server settings
server {
    // ...
}

// Network listeners
listeners {
    // ...
}

// Request routing
routes {
    // ...
}

// Backend servers
upstreams {
    // ...
}

// External agents (optional)
agents {
    // ...
}

// Request/response limits
limits {
    // ...
}

// Logging and metrics (optional)
observability {
    // ...
}
```

## Schema Versioning

Sentinel configurations include a schema version for compatibility checking. This helps catch configuration issues when upgrading Sentinel.

```kdl
// Declare schema version at the top of your config
schema-version "1.0"

server {
    // ...
}
```

### Version Format

Schema versions use `major.minor` format:

| Version | Meaning |
|---------|---------|
| `1.0` | Initial stable schema |
| `1.1` | Minor additions (backward compatible) |
| `2.0` | Major changes (may require migration) |

### Compatibility Behavior

| Config Version vs Sentinel | Result |
|---------------------------|--------|
| Exact match | ✓ Loads normally |
| Config older but supported | ✓ Loads normally |
| Config newer than Sentinel | ⚠ Loads with warning (some features may not work) |
| Config older than minimum | ✗ Rejected with error |
| Invalid format | ✗ Rejected with error |

### Omitting Version

If `schema-version` is not specified, Sentinel assumes the current version. For production deployments, explicitly specifying the version is recommended:

```kdl
// Explicit version (recommended for production)
schema-version "1.0"

server { /* ... */ }
```

This ensures configuration files remain compatible when upgrading Sentinel, and provides clear error messages if migration is needed.

## Complete Example

```kdl
// Sentinel Configuration
// Production API Gateway

schema-version "1.0"

server {
    worker-threads 0          // 0 = auto-detect CPU cores
    max-connections 10000
    graceful-shutdown-timeout-secs 30
}

listeners {
    listener "https" {
        address "0.0.0.0:443"
        protocol "https"
        tls {
            cert-file "/etc/sentinel/certs/server.crt"
            key-file "/etc/sentinel/certs/server.key"
            min-version "1.2"
        }
    }

    listener "admin" {
        address "127.0.0.1:9090"
        protocol "http"
    }
}

routes {
    route "api" {
        priority 100
        matches {
            path-prefix "/api/"
            method "GET" "POST" "PUT" "DELETE"
        }
        upstream "backend"
        agents "auth" "ratelimit"
    }

    route "health" {
        priority 1000
        matches {
            path "/health"
        }
        service-type "builtin"
        builtin-handler "health"
    }
}

upstreams {
    upstream "backend" {
        targets {
            target { address "10.0.1.1:8080" weight=3 }
            target { address "10.0.1.2:8080" weight=2 }
            target { address "10.0.1.3:8080" weight=1 }
        }
        load-balancing "weighted_round_robin"
        health-check {
            type "http"
            path "/health"
            interval-secs 10
            timeout-secs 5
        }
    }
}

agents {
    agent "auth" {
        type "auth"
        transport "unix_socket" {
            path "/var/run/sentinel/auth.sock"
        }
        timeout-ms 100
        failure-mode "closed"
    }

    agent "ratelimit" {
        type "rate_limit"
        transport "unix_socket" {
            path "/var/run/sentinel/ratelimit.sock"
        }
        timeout-ms 50
        failure-mode "open"
    }
}

limits {
    max-header-size-bytes 8192
    max-header-count 100
    max-body-size-bytes 10485760  // 10MB
}
```

## Alternative Formats

Sentinel also supports JSON and TOML for programmatic generation:

### JSON

```json
{
  "server": {
    "worker_threads": 4,
    "max_connections": 10000
  },
  "listeners": [
    {
      "id": "http",
      "address": "0.0.0.0:8080",
      "protocol": "http"
    }
  ]
}
```

### TOML

```toml
[server]
worker_threads = 4
max_connections = 10000

[[listeners]]
id = "http"
address = "0.0.0.0:8080"
protocol = "http"
```

File format is auto-detected by extension:
- `.kdl` → KDL
- `.json` → JSON
- `.toml` → TOML

## Multi-File Configuration

For complex deployments, split configuration across multiple files:

```
/etc/sentinel/
├── sentinel.kdl        # Main config (includes others)
├── routes/
│   ├── api.kdl
│   ├── static.kdl
│   └── admin.kdl
├── upstreams/
│   ├── backend.kdl
│   └── cache.kdl
└── agents/
    └── security.kdl
```

Use directory loading:

```bash
sentinel --config-dir /etc/sentinel/
```

Or explicit includes in your main config:

```kdl
// sentinel.kdl
include "routes/*.kdl"
include "upstreams/*.kdl"
include "agents/*.kdl"
```

## Validation

Validate configuration before applying:

```bash
# Check syntax and semantics
sentinel --config sentinel.kdl --validate

# Dry-run mode
sentinel --config sentinel.kdl --dry-run
```

Common validation errors:

| Error | Cause |
|-------|-------|
| Route references unknown upstream | Typo in upstream name |
| No listeners defined | Missing `listeners` block |
| Invalid socket address | Wrong format (need `host:port`) |
| Duplicate route ID | Two routes with same name |

## Hot Reload

Sentinel supports configuration reload without restart:

```bash
# Send SIGHUP to reload
kill -HUP $(cat /var/run/sentinel.pid)

# Or use the admin endpoint
curl -X POST http://localhost:9090/admin/reload
```

Reload behavior:
1. Parse new configuration
2. Validate syntax and semantics
3. If valid, atomically swap configuration
4. If invalid, keep old configuration and log error

## Next Steps

- [Server Configuration](../server/) - Server block settings
- [Listeners](../listeners/) - Network binding and TLS
- [Routes](../routes/) - Request routing

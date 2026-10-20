+++
title = "File Format"
weight = 1
updated = 2026-10-20
+++

Zentinel uses [KDL](https://kdl.dev/) as its primary configuration format. KDL is a human-friendly document language that's easy to read, write, and diff.

## Why KDL?

| Feature | Benefit |
|---------|---------|
| **Human-readable** | Clean syntax without excessive punctuation |
| **Git-friendly** | Diffs are clear and meaningful |
| **Typed values** | Numbers, strings, booleans, #null |
| **Comments** | Both line (`//`) and block (`/* */`) |
| **Hierarchical** | Natural nesting for configuration blocks |

## Basic Syntax

### Nodes

KDL documents are made of nodes. Each node has a name and optional values/properties:

```
// Simple node
my-node

// Node with a value
my-setting 4

// Node with a property
my-check type="http" interval-secs=10

// Node with children (block)
my-config {
    my-setting 4
    max-items 10000
}
```

### Values and Properties

**Values** are positional arguments:
```fragment,kdl
node-name "api"           // "api" is a value
multi-value "10.0.0.1" "10.0.0.2"  // Multiple values
```

**Properties** are named with `=`:
```fragment,kdl
target "10.0.0.1:8080" weight=5
agent "waf" type="waf" { /* ... */ }
```

### Data Types

```kdl
// Example showing KDL data types in Zentinel config

system {
    // Numbers (integer)
    worker-threads 4
    graceful-shutdown-timeout-secs 30
}

listeners {
    listener "http" {
        // Strings (quoted)
        address "0.0.0.0:8080"
        protocol "http"
    }
}

routes {
    route "default" {
        // Booleans (#true, #false)
        websocket #false

        matches { path-prefix "/" }
        upstream "backend"
    }
}

upstreams {
    upstream "backend" {
        target "127.0.0.1:3000" weight=1.5

        // Null values (#null)
        health-check #null
    }
}
```

### Comments

```kdl
// Line comment

/* Block comment
   spanning multiple
   lines */

system {
    worker-threads 4  // Inline comment
}
```

## File Structure

A typical Zentinel configuration has these top-level blocks:

```kdl
// System settings (use "system", not "server")
system {
    // ...
}

// Network listeners
listeners {
    listener "http" { address "0.0.0.0:8080" }
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

// Hierarchical organization (optional)
namespace "api" {
    limits { /* namespace-scoped limits */ }
    listeners { /* namespace-scoped listeners */ }
    upstreams { /* namespace-scoped upstreams */ }
    routes { /* namespace-scoped routes */ }
    agents { /* namespace-scoped agents */ }

    // Fine-grained isolation within namespace
    service "payments" {
        limits { /* service-scoped limits */ }
        listener "service-listener" { address "0.0.0.0:8081" }
        upstreams { /* service-scoped upstreams */ }
        routes { /* service-scoped routes */ }
    }
}
```

> **Note:** The `server` block name is deprecated but still supported for backward compatibility. Use `system` for new configurations.

## Schema Versioning

Zentinel configurations include a schema version for compatibility checking. This helps catch configuration issues when upgrading Zentinel.

```kdl
// Declare schema version at the top of your config
schema-version "1.0"

system {
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

| Config Version vs Zentinel | Result |
|---------------------------|--------|
| Exact match | ✓ Loads normally |
| Config older but supported | ✓ Loads normally |
| Config newer than Zentinel | ⚠ Loads with warning (some features may not work) |
| Config older than minimum | ✗ Rejected with error |
| Invalid format | ✗ Rejected with error |

### Omitting Version

If `schema-version` is not specified, Zentinel assumes the current version. For production deployments, explicitly specifying the version is recommended:

```kdl
// Explicit version (recommended for production)
schema-version "1.0"

system { /* ... */ }
```

This ensures configuration files remain compatible when upgrading Zentinel, and provides clear error messages if migration is needed.

## Complete Example

```kdl
// Zentinel Configuration
// Production API Gateway

schema-version "1.0"

system {
    worker-threads 0          // 0 = auto-detect CPU cores
    graceful-shutdown-timeout-secs 30
}

listeners {
    listener "https" {
        address "0.0.0.0:443"
        protocol "https"
        tls {
            cert-file "/etc/zentinel/certs/server.crt"
            key-file "/etc/zentinel/certs/server.key"
            min-version "1.2"
        }
    }

    listener "admin" {
        address "127.0.0.1:9901"  // 9090 is the metrics server's default port
        protocol "http"
    }
}

routes {
    route "api" {
        priority 100
        matches {
            path-prefix "/api/"
        }
        upstream "backend"
        filters "auth" "ratelimit"  // agents attach through filters
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
        target "10.0.1.1:8080" weight=3
        target "10.0.1.2:8080" weight=2
        target "10.0.1.3:8080" weight=1
        load-balancing "weighted_round_robin"
        health-check {
            type "http" {
                path "/health"
            }
            interval-secs 10
            timeout-secs 5
        }
    }
}

filters {
    filter "auth" {
        type "agent"
        agent "auth"
        failure-mode "closed"
    }
    filter "ratelimit" {
        type "agent"
        agent "ratelimit"
        failure-mode "open"
    }
}

agents {
    agent "auth" {
        type "auth"
        unix-socket "/tmp/zentinel/auth.sock"
        timeout-ms 100
        failure-mode "closed"
    }

    agent "ratelimit" {
        type "rate_limit"
        unix-socket "/tmp/zentinel/ratelimit.sock"
        timeout-ms 50
        failure-mode "open"
    }
}

limits {
    max-header-size 8192
    max-header-count 100
    max-body-size 10485760  // 10MB
}
```

## Alternative Formats

Zentinel also supports JSON and TOML for programmatic generation:

### JSON

```json
{
  "system": {
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
[system]
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

A configuration can be split across several KDL files in two ways: an entry
file that pulls in the others with `include`, or a directory passed to `-c`.
Both are read as one document by the same parser, so a block means the same
thing whichever file it is in.

```
/etc/zentinel/
├── zentinel.kdl        # system, limits, include "..."
├── listeners/
│   └── http.kdl
├── routes/
│   ├── api.kdl
│   └── static.kdl
└── upstreams/
    └── backends.kdl
```

Each file holds ordinary top-level blocks (`listeners { }`, `routes { }`,
`upstreams { }`, ...). A complete example is in the repository under
[`config/example-multi-file`](https://github.com/zentinelproxy/zentinel/tree/main/config/example-multi-file).

### Loading a Directory

From 26.10_6, every command that takes `-c` accepts a directory, and so does
`ZENTINEL_CONFIG`:

```bash
zentinel test --strict -c /etc/zentinel/
zentinel lint -c /etc/zentinel/
zentinel validate -c /etc/zentinel/
zentinel -c /etc/zentinel/
ZENTINEL_CONFIG=/etc/zentinel/ zentinel run
```

There is no separate `--config-dir` flag. Before 26.10_6, `-c <dir>` failed
with "Is a directory"; use the entry file (`-c /etc/zentinel/zentinel.kdl`)
on those releases.

How a directory is read:

- Every `*.kdl` file below the directory is found, recursively, and read in
  path order.
- A file that another file in the directory includes is read once, through
  that `include`, not a second time on its own. So the layout above (an entry
  file with `include "routes/*.kdl"`) and a `conf.d`-style folder of
  standalone files both load.
- A file reached from two entry files, or a circular include, is an error.
  From 26.10_7 a "diamond" below one entry file (two files that both include
  a third) loads, and the shared file is read once; see
  [Include Behavior](#include-behavior).
- Hidden files and folders are skipped: editor lock files such as
  `.#zentinel.kdl`, `.git`, and the `..data` folder of a Kubernetes ConfigMap
  mount, whose files would otherwise be read twice. So are files whose name
  contains `.example.` or `.bak`, or ends in `~`.
- The `environments/` folder is skipped. Its files are alternatives to one
  another (`staging.kdl`, `production.kdl`), and the command line has no way
  to choose one.
- A singleton block written in two files (`system`, `limits`, ...) is taken
  from the file read last, with a warning. A listener, route, upstream, filter
  or agent ID defined in two files is an error.

`zentinel test --strict` and `zentinel lint` check every file that is read,
included ones too, and name the file in each finding:

```
/etc/zentinel/routes/api.kdl: 'timeout-sec' is not a setting in the 'policies'
block and is being ignored. Did you mean 'timeout-secs'?
```

Before 26.10_6 only the file named with `-c` was checked, so a misspelled key
in an included file passed `--strict`, even for a single-file configuration.

### Include Behavior

The `include` directive is expanded before the configuration is parsed, so
included files can contain any top-level blocks (`routes`, `upstreams`,
`agents`, etc.).

**Glob patterns** — Include paths support glob patterns (`*`, `**`, `?`). Matched files are sorted alphabetically for deterministic ordering.

**Relative paths** — Patterns are resolved relative to the directory of the file containing the `include` directive. This means included files can themselves include other files using paths relative to their own location.

**Recursive includes** — Included files can contain their own `include` directives, which are expanded recursively.

**Each file is read once** — From 26.10_7 a file reached a second time through includes (a "diamond": two included files that both include a third) is read only the first time, so its routes and upstreams are defined once. Before 26.10_7 a diamond was rejected as a circular include.

**Circular include detection** — Only a file that includes itself, directly or through other files, is an error. The error names the chain of files that leads back to it (`Circular include detected: '/etc/zentinel/b.kdl' includes itself ('zentinel.kdl' -> '/etc/zentinel/b.kdl' -> '/etc/zentinel/c.kdl' -> '/etc/zentinel/b.kdl')`). In a [configuration directory](#loading-a-directory), a file reached from two entry files is still an error.

**No-match behavior** — If a glob pattern matches no files, Zentinel logs a warning but continues loading. This allows optional includes like `include "overrides/*.kdl"` where the directory may be empty.

```kdl
// routes/api.kdl — included file contains a top-level block
routes {
    route "api" {
        matches {
            path-prefix "/api"
        }
        upstream "backend"
    }
}
```

## Validation

Validate configuration before applying:

```bash
# Parse and validate; --strict also fails on settings that are ignored
zentinel test --strict -c zentinel.kdl

# Also check that upstreams, agents and certificates are reachable
zentinel validate -c zentinel.kdl

# Best-practice warnings
zentinel lint -c zentinel.kdl
```

Each command takes a file or a directory.

Common validation errors:

| Error | Cause |
|-------|-------|
| Route references unknown upstream | Typo in upstream name |
| No listeners defined | Missing `listeners` block |
| Invalid socket address | Wrong format (need `host:port`) |
| Duplicate route ID | Two routes with same name |

## Hot Reload

Zentinel reloads its configuration without a restart on `SIGHUP`:

```bash
kill -HUP $(pgrep -x zentinel)
```

From 26.10_6 a `SIGHUP` that arrives while the proxy is still starting is
queued, and the reload runs once the proxy is ready. Before, an early `SIGHUP`
could terminate a starting proxy (for example a configuration-management run
that reloads right after starting the service). `SIGTERM` and `SIGINT` still
stop a starting proxy at once.

With `system { auto-reload #true }` it also reloads when the configuration
changes on disk. For a directory configuration it watches the whole directory,
recursively. Once a second it also compares the content of every file the
configuration reads, includes too, with what the last reload read, which
catches filesystems that do not deliver change events and included files
outside the watched directory.

From 26.10_7 one edit gives one reload, and saving a file without changing its
content (a `touch`) does not reload. Before 26.10_7 one edit could trigger two
reloads, and for a single-file configuration the poll looked only at the entry
file, so a change to an included file outside its directory could be missed.

Reload behavior:
1. Parse new configuration
2. Validate syntax and semantics
3. If valid, atomically swap configuration
4. If invalid, keep old configuration and log error

## Next Steps

- [Server Configuration](../server/) - Server block settings
- [Listeners](../listeners/) - Network binding and TLS
- [Routes](../routes/) - Request routing
- [Namespaces & Services](../namespaces/) - Hierarchical organization

+++
title = "Routing System"
weight = 6
+++

Sentinel's routing system determines how incoming requests are matched to configured routes. This page covers match conditions, priority rules, and performance optimizations.

## Overview

```
                     Incoming Request
                           │
                           ▼
                  ┌─────────────────┐
                  │  Route Matcher  │
                  │                 │
                  │  ┌───────────┐  │
                  │  │   Cache   │◀─┼── Cache hit? Return immediately
                  │  └───────────┘  │
                  │        │        │
                  │        ▼        │
                  │  ┌───────────┐  │
                  │  │ Compiled  │  │
                  │  │  Routes   │  │
                  │  │ (sorted)  │  │
                  │  └───────────┘  │
                  └────────┬────────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
              ▼            ▼            ▼
         Route A      Route B      Route C
         (pri:100)    (pri:50)     (pri:10)
              │            │            │
              │       ✓ First Match     │
              │            │            │
              └────────────┴────────────┘
                           │
                           ▼
                    Return RouteMatch
```

## Route Configuration

Routes are defined in your configuration file:

```kdl
routes {
    route "api-users" {
        priority 100

        matches {
            path-prefix "/api/users"
            method "GET" "POST" "PUT" "DELETE"
        }

        upstream "user-service"
        service-type "api"
    }

    route "static-assets" {
        priority 50

        matches {
            path-prefix "/static/"
        }

        service-type "static"
        static-files {
            root "/var/www/static"
        }
    }

    route "catch-all" {
        priority 1

        matches {
            path-prefix "/"
        }

        upstream "default-backend"
    }
}
```

## Match Conditions

Routes can match on multiple criteria. All conditions must match (AND logic).

### Path Matching

#### Exact Path

Matches the exact path string:

```kdl
matches {
    path "/api/health"
}
```

| Request Path | Match? |
|--------------|--------|
| `/api/health` | Yes |
| `/api/health/` | No |
| `/api/healthcheck` | No |

#### Path Prefix

Matches paths starting with the prefix:

```kdl
matches {
    path-prefix "/api/"
}
```

| Request Path | Match? |
|--------------|--------|
| `/api/` | Yes |
| `/api/users` | Yes |
| `/api/users/123` | Yes |
| `/apiv2/users` | No |

#### Path Regex

Matches paths against a regular expression:

```kdl
matches {
    path-regex "/users/[0-9]+/profile"
}
```

| Request Path | Match? |
|--------------|--------|
| `/users/123/profile` | Yes |
| `/users/456/profile` | Yes |
| `/users/abc/profile` | No |

**Common regex patterns:**

| Pattern | Description |
|---------|-------------|
| `/api/v[0-9]+/.*` | Versioned API paths |
| `/users/[0-9]+` | Numeric user IDs |
| `/.*/health` | Health endpoints at any level |
| `/[a-z]{2}/.*` | Two-letter locale prefix |

### Host Matching

Match based on the `Host` header:

#### Exact Host

```kdl
matches {
    host "api.example.com"
}
```

#### Wildcard Host

Matches subdomains:

```kdl
matches {
    host "*.example.com"
}
```

| Host Header | Match? |
|-------------|--------|
| `api.example.com` | Yes |
| `www.example.com` | Yes |
| `example.com` | No |
| `deep.sub.example.com` | No (single level only) |

#### Host Regex

For complex host patterns:

```kdl
matches {
    host-regex "^(api|www)\\.example\\.(com|io)$"
}
```

### Method Matching

Match specific HTTP methods:

```kdl
matches {
    method "GET" "POST"
}
```

| Request Method | Match? |
|----------------|--------|
| `GET` | Yes |
| `POST` | Yes |
| `PUT` | No |
| `DELETE` | No |

### Header Matching

#### Header Presence

Match if header exists (any value):

```kdl
matches {
    header "Authorization"
}
```

#### Header Value

Match if header has specific value:

```kdl
matches {
    header "X-Api-Version" value="2"
}
```

| Headers | Match? |
|---------|--------|
| `X-Api-Version: 2` | Yes |
| `X-Api-Version: 1` | No |
| (no header) | No |

### Query Parameter Matching

#### Parameter Presence

```kdl
matches {
    query-param "debug"
}
```

| URL | Match? |
|-----|--------|
| `/api?debug=true` | Yes |
| `/api?debug=` | Yes |
| `/api?debug` | Yes |
| `/api?other=value` | No |

#### Parameter Value

```kdl
matches {
    query-param "version" value="2"
}
```

| URL | Match? |
|-----|--------|
| `/api?version=2` | Yes |
| `/api?version=1` | No |

## Combining Conditions

Multiple conditions are combined with AND logic:

```kdl
route "admin-api" {
    matches {
        path-prefix "/admin/"
        method "GET" "POST"
        header "X-Admin-Token"
        host "admin.example.com"
    }
    upstream "admin-service"
}
```

This route only matches if:
- Path starts with `/admin/` **AND**
- Method is GET or POST **AND**
- `X-Admin-Token` header is present **AND**
- Host is `admin.example.com`

## Priority System

When multiple routes could match, priority determines the winner.

### Priority Levels

```kdl
route "high-priority" {
    priority 100    // Evaluated first
}

route "normal-priority" {
    priority 50     // Evaluated second
}

route "low-priority" {
    priority 10     // Evaluated last
}
```

Higher numbers = higher priority = evaluated first.

### Named Priority Levels

You can also use named levels:

| Name | Numeric Value |
|------|---------------|
| `critical` | 1000 |
| `high` | 100 |
| `normal` | 50 (default) |
| `low` | 10 |
| `background` | 1 |

```kdl
route "critical-health" {
    priority critical
    matches { path "/-/health" }
}
```

### Priority Example

```
Request: GET /api/users/123
         Host: api.example.com

Routes evaluated in order:
┌────────────────────────────────────────────────────────────┐
│ 1. route "api-user-detail" pri=100                         │
│    matches: path-regex "/api/users/[0-9]+"                 │
│    Result: ✓ MATCH → Selected!                             │
├────────────────────────────────────────────────────────────┤
│ 2. route "api-users" pri=80                                │
│    matches: path-prefix "/api/users"                       │
│    Result: (not evaluated - already matched)               │
├────────────────────────────────────────────────────────────┤
│ 3. route "api-catchall" pri=50                             │
│    matches: path-prefix "/api/"                            │
│    Result: (not evaluated - already matched)               │
└────────────────────────────────────────────────────────────┘
```

## Specificity Tie-Breaking

When routes have the same priority, specificity breaks ties:

```
Specificity Scores:
┌─────────────────────────────────────┐
│ Match Type          │ Score         │
├─────────────────────┼───────────────┤
│ Exact path          │ 1000          │
│ Path regex          │ 500           │
│ Path prefix         │ 100           │
│ Host                │ 50            │
│ Header (with value) │ 30            │
│ Header (presence)   │ 20            │
│ Query param (value) │ 25            │
│ Query param (pres.) │ 15            │
│ Method              │ 10            │
└─────────────────────────────────────┘
```

**Example:**

```kdl
// Both have priority 50

route "specific" {
    priority 50
    matches {
        path "/api/users"        // +1000
        method "GET"             // +10
    }
    // Total specificity: 1010
}

route "general" {
    priority 50
    matches {
        path-prefix "/api/"      // +100
    }
    // Total specificity: 100
}
```

For request `GET /api/users`, the "specific" route wins due to higher specificity.

## Route Compilation

Routes are compiled at startup for efficient matching:

```
Configuration                    Compiled
┌──────────────────┐            ┌──────────────────────────┐
│ route "api" {    │            │ CompiledRoute {          │
│   matches {      │   ────▶    │   id: "api",             │
│     path-prefix  │            │   priority: 50,          │
│       "/api/"    │            │   matchers: [            │
│     method       │            │     PathPrefix("/api/"), │
│       "GET"      │            │     Method(["GET"]),     │
│   }              │            │   ],                     │
│ }                │            │   specificity: 110,      │
└──────────────────┘            │ }                        │
                                └──────────────────────────┘
```

**What's compiled:**
- Regex patterns are pre-compiled
- Host wildcards are parsed
- Routes are sorted by priority
- Specificity scores are calculated

## Route Cache

Sentinel caches route matches for performance:

```
┌───────────────────────────────────────────────────────────┐
│                     Route Cache                            │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ Cache Key: "{method}:{host}:{path}"                 │  │
│  │                                                     │  │
│  │ "GET:api.example.com:/users/123" → route-id: "api"  │  │
│  │ "POST:api.example.com:/login"    → route-id: "auth" │  │
│  │ "GET:www.example.com:/about"     → route-id: "web"  │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                           │
│  Max Size: 1000 entries                                   │
│  Eviction: LRU (Least Recently Used)                      │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

**Cache behavior:**

1. **Cache hit**: Return route immediately (no evaluation)
2. **Cache miss**: Evaluate all routes, cache the result
3. **Eviction**: When full, remove least recently used entries
4. **Invalidation**: Cache clears on configuration reload

### When Caching Doesn't Help

Cache is bypassed when requests vary significantly:
- Random query parameters in cache key
- Unique paths (e.g., UUIDs in path)
- Many different hosts

## Default Route

Configure a catch-all route for unmatched requests:

```kdl
routes {
    // Specific routes first
    route "api" {
        priority 100
        matches { path-prefix "/api/" }
        upstream "api-service"
    }

    // Default route (lowest priority)
    route "default" {
        priority 1
        matches { path-prefix "/" }
        upstream "default-backend"
    }
}
```

Or specify a default route explicitly:

```kdl
routing {
    default-route "fallback"
}

routes {
    route "fallback" {
        upstream "default-backend"
    }
}
```

## No Match Behavior

When no route matches and no default is configured:

```json
{
  "status": 404,
  "error": "no_route",
  "message": "No route matched request",
  "path": "/unknown/path",
  "trace_id": "abc-123"
}
```

## Best Practices

### 1. Order by Specificity

Put more specific routes before general ones:

```kdl
// Good: Specific first
route "user-profile" { priority 100; matches { path-regex "/users/[0-9]+/profile" } }
route "user-detail"  { priority 90;  matches { path-regex "/users/[0-9]+" } }
route "users-list"   { priority 80;  matches { path-prefix "/users" } }
route "api-catchall" { priority 50;  matches { path-prefix "/api/" } }
```

### 2. Use Exact Paths When Possible

Exact paths are faster and more predictable:

```kdl
// Prefer this for known endpoints
route "health" {
    matches { path "/-/health" }
}

// Over regex for simple cases
route "health" {
    matches { path-regex "^/-/health$" }  // Slower
}
```

### 3. Limit Regex Complexity

Simple regexes match faster:

```kdl
// Fast
matches { path-regex "/users/[0-9]+" }

// Slower (backtracking)
matches { path-regex "/users/.*?/profile/.*" }
```

### 4. Use Priority Gaps

Leave gaps for future routes:

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

// Example priority values with gaps for future insertion
routes {
    route "critical" {
        priority 1000
        matches { path-prefix "/critical" }
        upstream "backend"
    }
    route "high" {
        priority 100    // Gap allows 101-999
        matches { path-prefix "/high" }
        upstream "backend"
    }
    route "normal" {
        priority 50     // Gap allows 51-99
        matches { path-prefix "/normal" }
        upstream "backend"
    }
    route "low" {
        priority 10     // Gap allows 11-49
        matches { path-prefix "/low" }
        upstream "backend"
    }
    route "default" {
        priority 1
        matches { path-prefix "/" }
        upstream "backend"
    }
}

upstreams {
    upstream "backend" {
        targets {
            target { address "127.0.0.1:3000" }
        }
    }
}
```

### 5. Avoid Overlapping Routes

Overlapping routes with same priority cause confusion:

```kdl
// Avoid: Both could match /api/users, same priority
route "api-a" { priority 50; matches { path-prefix "/api/" } }
route "api-b" { priority 50; matches { path-prefix "/api/users" } }

// Better: Different priorities
route "api-users" { priority 60; matches { path-prefix "/api/users" } }
route "api-other" { priority 50; matches { path-prefix "/api/" } }
```

## Debugging Routes

### Test Route Matching

Use the CLI to test which route matches:

```bash
sentinel route-test --path "/api/users/123" --method GET --host api.example.com
```

Output:
```
Matched route: api-users
  Priority: 100
  Specificity: 610
  Upstream: user-service

Evaluated routes:
  1. api-users (pri=100, spec=610) ✓ MATCHED
  2. api-catchall (pri=50, spec=100) - (not evaluated)
  3. default (pri=1, spec=100) - (not evaluated)
```

### View Compiled Routes

```bash
sentinel routes --compiled
```

### Monitor Cache Performance

```bash
sentinel stats routes
```

```
Route Cache Statistics:
  Entries: 847/1000
  Hit Rate: 94.2%
  Evictions: 12,453

Top Cached Routes:
  1. api-users: 45,231 hits
  2. static-assets: 23,456 hits
  3. health: 12,345 hits
```

## Performance Characteristics

| Operation | Complexity | Typical Time |
|-----------|------------|--------------|
| Cache lookup | O(1) | < 1μs |
| Route evaluation (no cache) | O(n) | 10-100μs |
| Regex match | O(m) | 1-10μs per regex |
| Cache insert | O(1) | < 1μs |
| LRU eviction | O(1) | < 1μs |

Where:
- n = number of routes
- m = path length

## Next Steps

- [Request Lifecycle](../request-flow/) - See routing in context
- [Basic Configuration](/getting-started/basic-configuration/) - Configuration syntax
- [First Route](/getting-started/first-route/) - Getting started with routes

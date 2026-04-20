+++
title = "Caching"
weight = 7
updated = 2026-02-19
+++

Zentinel provides HTTP response caching to reduce upstream load and improve response times. Caching is configured at two levels: global storage settings and per-route caching policies.

## Global Cache Storage

Configure the cache storage backend at the server level:

```kdl
cache {
    enabled #true
    backend "memory"           // Storage backend
    max-size 104857600         // 100MB total cache size
    eviction-limit 104857600   // When to start evicting
    lock-timeout 10            // Seconds (thundering herd protection)
}
```

### Storage Backends

| Backend | Description | Use Case |
|---------|-------------|----------|
| `memory` | In-memory LRU cache (default) | Single instance, low latency |
| `disk` | Disk-based cache | Large cache, persistence across restarts |
| `hybrid` | Memory + disk tiered cache | Hot data in memory, cold on disk |

#### Memory Backend

Fast, in-memory caching using LRU eviction:

```kdl
cache {
    enabled #true
    backend "memory"
    max-size 209715200         // 200MB
    eviction-limit 104857600   // Start evicting at 100MB
    lock-timeout 10
}
```

#### Disk Backend

Persistent disk-based caching that survives proxy restarts. Cache entries are stored as files on disk using a sharded directory layout for performance:

```kdl
cache {
    enabled #true
    backend "disk"
    max-size 1073741824        // 1GB
    disk-path "/var/cache/zentinel"
    disk-shards 16             // Parallelism
    lock-timeout 10
}
```

**Directory layout:**

```
/var/cache/zentinel/
├── shard-00/
│   ├── 00/
│   │   ├── <key>.meta       // Response metadata (headers, freshness)
│   │   └── <key>.body       // Response body
│   ├── 01/
│   │   └── ...
│   ├── ...
│   ├── ff/
│   └── tmp/                  // Temporary files during writes
├── shard-01/
│   └── ...
├── ...
├── shard-0f/
└── eviction/                 // LRU eviction state (persisted)
```

Each shard contains 256 hex-prefix subdirectories to prevent too many files in a single directory. The number of shards is configurable via `disk-shards` (default: 16).

**Crash safety:** All writes use atomic temp-file-then-rename, so a crash during a write never leaves a corrupted cache entry. Orphaned temporary files from previous crashes are cleaned up automatically on startup.

**Eviction state:** The LRU eviction manager's state is saved to `<disk-path>/eviction/` on shutdown and restored on startup, so the proxy knows which entries to evict first without scanning access patterns from scratch.

> **Note:** `disk-path` is required when using the `disk` backend. The proxy will fail to start if it is not set.

#### Hybrid Backend

Two-tier caching with memory for hot data:

```kdl
cache {
    enabled #true
    backend "hybrid"
    max-size 1073741824        // 1GB total
    disk-path "/var/cache/zentinel"
    disk-shards 16
    lock-timeout 15
}
```

> **Not yet implemented.** Configuring `backend "hybrid"` currently falls back to the memory backend with a warning logged at startup. `disk-path` is still required in the config so that switching to hybrid in a future release requires no config changes. Track progress in [#90](https://github.com/zentinelproxy/zentinel/issues/90).

### Global Cache Options

| Option | Default | Description |
|--------|---------|-------------|
| `enabled` | `true` | Enable caching globally |
| `backend` | `memory` | Storage backend |
| `max-size` | `104857600` (100MB) | Maximum cache size in bytes |
| `eviction-limit` | None | Size at which to start evicting entries |
| `lock-timeout` | `10` | Cache lock timeout in seconds |
| `disk-path` | None | Path for disk cache (required for disk/hybrid) |
| `disk-shards` | `16` | Number of disk cache shards |

## Per-Route Caching

Enable and configure caching for specific routes:

```kdl
route "api" {
    matches {
        path-prefix "/api/v1/"
    }
    upstream "backend"

    cache {
        enabled #true
        default-ttl-secs 3600
        max-size-bytes 10485760
        stale-while-revalidate-secs 60
        stale-if-error-secs 300
        cacheable-methods "GET" "HEAD"
    }
}
```

### Route Cache Options

| Option | Default | Description |
|--------|---------|-------------|
| `enabled` | `false` | Enable caching for this route |
| `default-ttl-secs` | `3600` | Default TTL if no Cache-Control header |
| `max-size-bytes` | `10485760` (10MB) | Maximum cacheable response size |
| `cache-private` | `false` | Cache responses with `Cache-Control: private` |
| `stale-while-revalidate-secs` | `60` | Serve stale while revalidating in background |
| `stale-if-error-secs` | `300` | Serve stale on upstream error |
| `exclude-extensions` | `[]` | File extensions to skip caching (without dot) |
| `exclude-paths` | `[]` | Path glob patterns to skip caching |

### Cacheable Methods

Specify which HTTP methods are cacheable:

```kdl
cache {
    enabled #true
    cacheable-methods "GET" "HEAD"
}
```

Default: `GET`, `HEAD`

### Cacheable Status Codes

Specify which response status codes are cacheable:

```kdl
cache {
    enabled #true
    cacheable-status-codes 200 203 204 206 300 301 308 404 405 410 414 501
}
```

Default: `200`, `203`, `204`, `206`, `300`, `301`, `308`, `404`, `405`, `410`, `414`, `501`

### Vary Headers

Headers that affect cache key:

```kdl
cache {
    enabled #true
    vary-headers "Accept-Encoding" "Accept-Language"
}
```

When specified, these headers become part of the cache key, allowing different cached responses for different header values.

### Ignoring Query Parameters

Parameters to exclude from cache key:

```kdl
cache {
    enabled #true
    ignore-query-params "utm_source" "utm_medium" "utm_campaign" "_"
}
```

Useful for ignoring tracking parameters or cache-busting tokens.

### Excluding Extensions

Exclude specific file extensions from caching. This is useful for broad routes (e.g., `path-prefix "/"`) where most content should be cached but dynamic file types should not:

```kdl
cache {
    enabled #true
    default-ttl-secs 3600
    exclude-extensions "php" "html" "asp"
}
```

Extensions are specified without the leading dot. The check is case-insensitive.

### Excluding Paths

Exclude specific paths from caching using glob patterns (`*`, `**`, `?`):

```kdl
cache {
    enabled #true
    default-ttl-secs 3600
    exclude-paths "/wp-admin/**" "/login" "/api/auth/**"
}
```

| Pattern | Matches |
|---------|---------|
| `/login` | Exact path `/login` |
| `/admin/*` | One level under `/admin/` (e.g., `/admin/users`) |
| `/api/auth/**` | Any depth under `/api/auth/` (e.g., `/api/auth/oauth/callback`) |
| `/files/*.tmp` | `.tmp` files directly under `/files/` |

Requests matching an excluded extension or path are bypassed from caching and forwarded directly to the upstream. The cache status for these requests is reported as `BYPASS`.

## Stale Content Handling

### Stale-While-Revalidate

Serve stale content while fetching fresh content in the background:

```kdl
cache {
    enabled #true
    default-ttl-secs 3600
    stale-while-revalidate-secs 60
}
```

When a cached response expires:
1. Immediately serve the stale response
2. Trigger background revalidation
3. Update cache when fresh response arrives

### Stale-If-Error

Serve stale content when upstream returns an error:

```kdl
cache {
    enabled #true
    stale-if-error-secs 300
}
```

When upstream returns 5xx or times out:
1. Check if stale content exists within grace period
2. Serve stale if available
3. Return error if no stale content

## Cache Lock (Thundering Herd Protection)

The `lock-timeout` prevents multiple requests from simultaneously fetching the same uncached resource:

```kdl
cache {
    lock-timeout 10    // Seconds to wait for cache lock
}
```

When a cache miss occurs:
1. First request acquires the lock and fetches from upstream
2. Subsequent requests wait for the lock (up to timeout)
3. All waiting requests receive the cached response
4. If lock times out, request proceeds to upstream

## Complete Examples

### API Caching

```kdl
// Global cache storage
cache {
    enabled #true
    backend "memory"
    max-size 536870912     // 512MB
    lock-timeout 5
}

routes {
    // Cache API responses
    route "api" {
        matches {
            path-prefix "/api/v1/"
            method "GET"
        }
        upstream "api-backend"

        cache {
            enabled #true
            default-ttl-secs 60
            max-size-bytes 1048576      // 1MB per response
            stale-while-revalidate-secs 30
            stale-if-error-secs 120
            vary-headers "Authorization"
            ignore-query-params "callback" "_"
        }
    }

    // Don't cache mutations
    route "api-mutations" {
        matches {
            path-prefix "/api/v1/"
            method "POST" "PUT" "DELETE" "PATCH"
        }
        upstream "api-backend"
        // No cache block = caching disabled
    }
}
```

### Static Asset Caching

```kdl
cache {
    enabled #true
    backend "disk"
    max-size 10737418240   // 10GB
    disk-path "/var/cache/zentinel/static"
    disk-shards 32
}

routes {
    route "static-assets" {
        matches {
            path-prefix "/assets/"
        }
        upstream "cdn-origin"

        cache {
            enabled #true
            default-ttl-secs 86400      // 24 hours
            max-size-bytes 52428800     // 50MB per file
            stale-if-error-secs 86400   // Serve stale for 24h on error
            cacheable-methods "GET" "HEAD"
        }
    }
}
```

### Multi-Tenant Caching

```kdl
cache {
    enabled #true
    backend "memory"
    max-size 1073741824    // 1GB
}

routes {
    route "tenant-api" {
        matches {
            path-prefix "/api/"
        }
        upstream "backend"

        cache {
            enabled #true
            default-ttl-secs 300
            vary-headers "X-Tenant-ID" "Accept-Language"
        }
    }
}
```

## Cache Behavior

### Cache Key Generation

The cache key is generated from:
1. Request method (if cacheable)
2. Request path
3. Query parameters (excluding ignored ones)
4. Vary headers (if configured)

### Cache-Control Directives

Zentinel respects Cache-Control headers from upstream:

| Directive | Behavior |
|-----------|----------|
| `no-store` | Never cache response |
| `no-cache` | Cache but revalidate before use |
| `private` | Don't cache (unless `cache-private` enabled) |
| `max-age=N` | Cache for N seconds |
| `s-maxage=N` | Override max-age for shared caches |
| `must-revalidate` | Don't serve stale content |

### Cache Invalidation

Caches are automatically invalidated:
- When TTL expires
- On configuration reload (optional)
- Via admin endpoint (if enabled)

```bash
# Purge all cached content
curl -X POST http://localhost:9090/admin/cache/purge

# Purge specific path
curl -X POST http://localhost:9090/admin/cache/purge?path=/api/v1/users
```

## Metrics

Cache-related metrics:

| Metric | Description |
|--------|-------------|
| `zentinel_cache_hits_total` | Total cache hits |
| `zentinel_cache_misses_total` | Total cache misses |
| `zentinel_cache_size_bytes` | Current cache size |
| `zentinel_cache_entries` | Number of cached entries |
| `zentinel_cache_evictions_total` | Total evictions |
| `zentinel_cache_stale_served_total` | Stale responses served |

## Best Practices

1. **Set appropriate TTLs**: Match TTL to data freshness requirements
2. **Use stale-while-revalidate**: Improve perceived performance
3. **Configure vary headers carefully**: Too many = cache fragmentation
4. **Monitor cache hit rate**: Low hit rate indicates misconfiguration
5. **Size cache appropriately**: Undersized cache = frequent evictions
6. **Use disk cache for large content**: Keep memory for small, hot data

## Next Steps

- [Routes](../routes/) - Configuring route-level caching
- [Upstreams](../upstreams/) - Upstream configuration
- [Observability](../observability/) - Monitoring cache performance

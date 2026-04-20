+++
title = "Image Optimization"
weight = 17
updated = 2026-02-24
+++

Automatically convert JPEG and PNG images to WebP or AVIF on the fly using the image optimization agent. The agent negotiates the best format from the client's `Accept` header, caches converted images on disk, and falls back to the original on any error.

## Use Case

- Reduce image payload size by 30-80% with modern formats
- Serve WebP to Chrome/Firefox/Safari and AVIF where supported
- Cache converted images to avoid repeated CPU work
- No changes needed to origin servers or image pipelines
- Graceful fallback — the agent never makes a response worse

## Architecture

```
                    ┌─────────────────┐
                    │    Clients      │
                    │  Accept: webp   │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │    Zentinel     │
                    │                 │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
         ┌─────────┐   ┌─────────┐   ┌──────────┐
         │  Image  │   │ Static  │   │   API    │
         │  Origin │   │ Assets  │   │ Backend  │
         └─────────┘   └─────────┘   └──────────┘
                             │
                    ┌────────▼────────┐
                    │  Image Opt      │
                    │  Agent          │
                    │  ┌───────────┐  │
                    │  │ FS Cache  │  │
                    │  └───────────┘  │
                    └─────────────────┘
```

## Prerequisites

Install the image optimization agent:

```bash
# Via bundle (recommended)
zentinel bundle install image-optimization

# Or via cargo
cargo install zentinel-agent-image-optimization
```

## Configuration

Create `zentinel.kdl`:

```kdl
// Image Optimization Example
// Converts JPEG/PNG responses to WebP/AVIF with caching

system {
    workers 4
}

listeners {
    listener "http" {
        address "0.0.0.0:8080"
    }
}

agents {
    agent "image-opt" type="custom" {
        unix-socket "/tmp/image-optimization.sock"
        events "request_headers" "response_headers" "response_body" "request_complete"

        timeout-ms 5000
        failure-mode "open"

        config {
            "formats" ["webp", "avif"]
            "quality" { "webp" 80; "avif" 70 }
            "max_input_size_bytes" 10485760
            "max_pixel_count" 25000000
            "eligible_content_types" ["image/jpeg", "image/png"]
            "passthrough_patterns" ["\\.gif$", "\\.svg$", "\\.ico$"]
            "cache" {
                "enabled" true
                "directory" "/var/cache/zentinel/image-optimization"
                "max_size_bytes" 1073741824
                "ttl_secs" 86400
            }
        }
    }
}

upstreams {
    upstream "origin" {
        target "127.0.0.1:9000"
    }
}

routes {
    route "images" {
        matches { path-prefix "/" }
        upstream "origin"
        agents "image-opt"
    }
}
```

## Running

Start the agent and proxy:

```bash
# Terminal 1: Start the image optimization agent
zentinel-image-optimization-agent \
    --socket /tmp/image-optimization.sock \
    --log-level info

# Terminal 2: Start Zentinel
zentinel -c zentinel.kdl
```

## Testing

```bash
# Request a JPEG — should receive WebP if your client supports it
curl -H "Accept: image/webp,image/*" \
     -o optimized.webp \
     -D - \
     http://localhost:8080/photo.jpg

# Check response headers
# Content-Type: image/webp
# X-Image-Optimized: webp
# X-Image-Original-Size: 245760
# Vary: Accept

# Request again — should be a cache hit
curl -H "Accept: image/webp,image/*" \
     -o cached.webp \
     -D - \
     http://localhost:8080/photo.jpg
# X-Image-Optimized: cache-hit

# Request without WebP support — original passes through
curl -H "Accept: image/jpeg" \
     -o original.jpg \
     -D - \
     http://localhost:8080/photo.jpg
# Content-Type: image/jpeg (unchanged)

# Request AVIF
curl -H "Accept: image/avif,image/webp,image/*" \
     -o optimized.avif \
     -D - \
     http://localhost:8080/photo.jpg
# Content-Type: image/avif
# X-Image-Optimized: avif
```

## Customization

### WebP Only (Fastest)

If you don't need AVIF support:

```kdl
config {
    "formats" ["webp"]
    "quality" { "webp" 85 }
}
```

### Skip Large Images

Lower the size limits to avoid spending CPU on hero images:

```kdl
config {
    "max_input_size_bytes" 5242880
    "max_pixel_count" 10000000
}
```

### Exclude Specific Paths

Skip images that are already optimized or served from a CDN:

```kdl
config {
    "passthrough_patterns" ["\\.gif$", "\\.svg$", "/cdn/", "/thumbnails/"]
}
```

### gRPC Transport

For higher throughput or remote deployment:

```kdl
agent "image-opt" type="custom" {
    grpc "http://image-opt-service:50060"
    events "request_headers" "response_headers" "response_body" "request_complete"

    timeout-ms 5000
    failure-mode "open"
}
```

```bash
zentinel-image-optimization-agent --grpc 0.0.0.0:50060
```

## Response Headers

| Header | Example | Description |
|--------|---------|-------------|
| `Content-Type` | `image/webp` | Converted format |
| `X-Image-Optimized` | `webp`, `avif`, `cache-hit` | Conversion result |
| `X-Image-Original-Size` | `245760` | Original size in bytes |
| `Vary` | `Accept` | Downstream caches vary by format |

## Related Examples

- [Static Site](../static-site/) — Serve and optimize static assets
- [HTTP Caching](../http-caching/) — Combine with HTTP response caching
- [Load Balancer](../load-balancer/) — Optimize images across multiple origins

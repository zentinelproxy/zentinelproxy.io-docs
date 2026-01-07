+++
title = "Static Site"
weight = 4
+++

Serve static files with Sentinel including caching, compression, SPA support, and CDN-like features.

## Use Case

- Serve static websites and assets
- Host Single Page Applications (SPAs)
- Provide CDN-like caching and compression
- Combine static files with API backend

## Configuration

Create `sentinel.kdl`:

```kdl
// Static Site Configuration
// High-performance static file serving

server {
    worker-threads 0
    graceful-shutdown-timeout-secs 30
}

listeners {
    listener "https" {
        address "0.0.0.0:8443"
        protocol "https"
        tls {
            cert-file "/etc/sentinel/certs/site.crt"
            key-file "/etc/sentinel/certs/site.key"
        }
    }
    listener "http" {
        address "0.0.0.0:8080"
        protocol "http"
        redirect-https true
    }
}

routes {
    // Health check
    route "health" {
        priority 1000
        matches {
            path "/health"
        }
        service-type "builtin"
        builtin-handler "health"
    }

    // Immutable assets (hashed filenames) - long cache
    route "assets-immutable" {
        priority 200
        matches {
            path-regex "^/assets/.*\\.[a-f0-9]{8}\\.(js|css|woff2?)$"
        }
        service-type "static"
        static-files {
            root "/var/www/site"
            cache-control "public, max-age=31536000, immutable"
            compress true
        }
    }

    // Regular assets - moderate cache
    route "assets" {
        priority 150
        matches {
            path-prefix "/assets/"
        }
        service-type "static"
        static-files {
            root "/var/www/site"
            cache-control "public, max-age=86400"
            compress true
        }
    }

    // Images and media - long cache
    route "images" {
        priority 150
        matches {
            path-prefix "/images/"
        }
        service-type "static"
        static-files {
            root "/var/www/site"
            cache-control "public, max-age=604800"
        }
    }

    // Favicon and robots
    route "root-files" {
        priority 100
        matches {
            path "/favicon.ico"
        }
        service-type "static"
        static-files {
            root "/var/www/site"
            cache-control "public, max-age=86400"
        }
    }

    route "robots" {
        priority 100
        matches {
            path "/robots.txt"
        }
        service-type "static"
        static-files {
            root "/var/www/site"
            cache-control "public, max-age=86400"
        }
    }

    // SPA - catch-all with fallback to index.html
    route "spa" {
        priority 1
        matches {
            path-prefix "/"
            method "GET"
        }
        service-type "static"
        static-files {
            root "/var/www/site"
            index "index.html"
            fallback "index.html"  // SPA routing
            cache-control "no-cache"
            compress true
        }
        policies {
            response-headers {
                set {
                    "X-Content-Type-Options" "nosniff"
                    "X-Frame-Options" "DENY"
                    "X-XSS-Protection" "1; mode=block"
                    "Referrer-Policy" "strict-origin-when-cross-origin"
                }
            }
        }
    }
}

observability {
    metrics {
        enabled true
        address "0.0.0.0:9090"
    }
    logging {
        level "info"
        format "json"
    }
}
```

## Directory Structure

```
/var/www/site/
├── index.html
├── favicon.ico
├── robots.txt
├── assets/
│   ├── main.a1b2c3d4.js      # Hashed (immutable)
│   ├── main.a1b2c3d4.css
│   ├── vendor.e5f6g7h8.js
│   └── fonts/
│       └── inter.woff2
└── images/
    ├── logo.png
    └── hero.jpg
```

## Setup

### 1. Create Site Directory

```bash
sudo mkdir -p /var/www/site
sudo chown $USER:$USER /var/www/site
```

### 2. Deploy Your Site

```bash
# Example: Copy a built React/Vue/Next.js app
cp -r dist/* /var/www/site/

# Or a static site generator output
cp -r public/* /var/www/site/
```

### 3. Run Sentinel

```bash
sentinel -c sentinel.kdl
```

## Testing

### Basic Request

```bash
curl -I http://localhost:8080/
```

Expected response:

```
HTTP/1.1 200 OK
Content-Type: text/html
Cache-Control: no-cache
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
```

### Immutable Asset Caching

```bash
curl -I http://localhost:8080/assets/main.a1b2c3d4.js
```

Expected:

```
HTTP/1.1 200 OK
Content-Type: application/javascript
Cache-Control: public, max-age=31536000, immutable
Content-Encoding: gzip
```

### SPA Routing

```bash
# Direct page access
curl http://localhost:8080/dashboard

# Returns index.html (fallback for SPA routing)
```

### Compression

```bash
curl -H "Accept-Encoding: gzip, br" -I http://localhost:8080/assets/main.js
```

Check for `Content-Encoding: gzip` or `Content-Encoding: br`.

## Static Site with API Backend

Combine static file serving with API proxying:

```kdl
routes {
    // API routes - proxy to backend
    route "api" {
        priority 500
        matches {
            path-prefix "/api/"
        }
        upstream "api-backend"
        service-type "api"
    }

    // WebSocket for real-time features
    route "ws" {
        priority 400
        matches {
            path "/ws"
        }
        upstream "api-backend"
    }

    // Static files - SPA
    route "spa" {
        priority 1
        matches {
            path-prefix "/"
        }
        service-type "static"
        static-files {
            root "/var/www/site"
            fallback "index.html"
        }
    }
}

upstreams {
    upstream "api-backend" {
        targets {
            target { address "127.0.0.1:3000" }
        }
    }
}
```

## Multi-Site Hosting

Host multiple sites on the same Sentinel instance:

```kdl
routes {
    // Site A
    route "site-a" {
        priority 100
        matches {
            host "site-a.example.com"
            path-prefix "/"
        }
        service-type "static"
        static-files {
            root "/var/www/site-a"
            fallback "index.html"
        }
    }

    // Site B
    route "site-b" {
        priority 100
        matches {
            host "site-b.example.com"
            path-prefix "/"
        }
        service-type "static"
        static-files {
            root "/var/www/site-b"
            fallback "index.html"
        }
    }

    // Default site
    route "default" {
        priority 1
        matches {
            path-prefix "/"
        }
        service-type "static"
        static-files {
            root "/var/www/default"
        }
    }
}
```

## Customizations

### Directory Listing

```kdl
static-files {
    root "/var/www/files"
    directory-listing true
}
```

### Custom 404 Page

```kdl
route "spa" {
    service-type "static"
    static-files {
        root "/var/www/site"
        fallback "404.html"
    }
    error-pages {
        pages {
            "404" {
                format "html"
                template "/var/www/site/404.html"
            }
        }
    }
}
```

### Content Security Policy

```kdl
route "spa" {
    policies {
        response-headers {
            set {
                "Content-Security-Policy" "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'"
            }
        }
    }
}
```

### Brotli Compression

```kdl
static-files {
    root "/var/www/site"
    compress true
    compression-level 6
    compression-types "text/html" "text/css" "application/javascript" "application/json"
}
```

## Performance Tips

1. **Use hashed filenames** for assets to enable immutable caching
2. **Precompress files** (`.gz`, `.br`) for faster response times
3. **Separate routes** for different cache policies
4. **Enable HTTP/2** for multiplexing
5. **Use CDN** in front of Sentinel for global distribution

## Next Steps

- [API Gateway](../api-gateway/) - Add backend APIs
- [Security](../security/) - Add WAF protection
- [Observability](../observability/) - Monitor traffic

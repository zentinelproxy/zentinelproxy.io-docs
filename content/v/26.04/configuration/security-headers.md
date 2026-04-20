+++
title = "Security Headers"
weight = 8
updated = 2026-02-22
+++

Zentinel does not inject any response headers by default. Security headers are configured explicitly via `response-headers` policies on your routes or via a reusable `headers` filter. This gives you full control over which headers are set and what values they use.

## Adding Security Headers

### Per-Route Policy

The simplest way to add headers to a specific route:

```kdl
route "app" {
    matches {
        path-prefix "/"
    }
    upstream "backend"

    policies {
        response-headers {
            set {
                "X-Content-Type-Options" "nosniff"
                "X-Frame-Options" "SAMEORIGIN"
                "Referrer-Policy" "strict-origin-when-cross-origin"
                "Permissions-Policy" "geolocation=(), microphone=(), camera=()"
            }
        }
    }
}
```

### Reusable Headers Filter

For headers shared across multiple routes, define a `headers` filter once and reference it by name:

```kdl
filters {
    filter "security-headers" {
        type "headers"
        phase "response"
        set {
            "X-Content-Type-Options" "nosniff"
            "X-Frame-Options" "SAMEORIGIN"
            "Referrer-Policy" "strict-origin-when-cross-origin"
            "Permissions-Policy" "geolocation=(), microphone=(), camera=()"
        }
    }
}

routes {
    route "api" {
        matches { path-prefix "/api/" }
        upstream "api-backend"
        filters "security-headers"
    }

    route "app" {
        matches { path-prefix "/" }
        upstream "app-backend"
        filters "security-headers"
    }
}
```

### Removing Headers

Strip headers that leak server information:

```kdl
policies {
    response-headers {
        remove "Server" "X-Powered-By" "X-AspNet-Version" "X-AspNetMvc-Version"
    }
}
```

## Recommended Headers

### Content-Type Options

Prevents browsers from MIME-sniffing a response away from the declared `Content-Type`. Always safe to set.

```kdl
"X-Content-Type-Options" "nosniff"
```

| Value | Behavior |
|-------|----------|
| `nosniff` | Browser trusts the declared Content-Type; blocks style/script loads with wrong MIME type |

**Recommendation:** Set on all routes.

### Frame Options

Controls whether the page can be embedded in an `<iframe>`, `<frame>`, or `<object>`. Protects against clickjacking attacks.

```kdl
"X-Frame-Options" "SAMEORIGIN"
```

| Value | Behavior |
|-------|----------|
| `DENY` | Page cannot be embedded in any frame |
| `SAMEORIGIN` | Page can only be framed by pages on the same origin |

**Recommendation:** Use `SAMEORIGIN` unless you are certain no iframes are needed. Use `DENY` only for pages that should never be embedded (e.g., login forms, admin panels). If you need to allow specific external origins to frame your content, use `Content-Security-Policy` with `frame-ancestors` instead (see below).

> `X-Frame-Options` is superseded by CSP `frame-ancestors` in modern browsers, but setting both provides coverage for older clients.

### Referrer Policy

Controls how much referrer information is sent with requests originating from your pages.

```kdl
"Referrer-Policy" "strict-origin-when-cross-origin"
```

| Value | Behavior |
|-------|----------|
| `no-referrer` | Never send referrer |
| `same-origin` | Send full URL for same-origin, nothing for cross-origin |
| `strict-origin` | Send origin only (no path), nothing over downgrade (HTTPS to HTTP) |
| `strict-origin-when-cross-origin` | Full URL for same-origin, origin-only for cross-origin, nothing on downgrade |

**Recommendation:** `strict-origin-when-cross-origin` is a good default. Use `no-referrer` for sensitive pages.

### Strict Transport Security (HSTS)

Tells browsers to only connect via HTTPS. Only effective when served over HTTPS.

```kdl
"Strict-Transport-Security" "max-age=31536000; includeSubDomains"
```

| Directive | Meaning |
|-----------|---------|
| `max-age=31536000` | Remember HTTPS-only for 1 year |
| `includeSubDomains` | Apply to all subdomains |
| `preload` | Request inclusion in browser preload lists ([hstspreload.org](https://hstspreload.org)) |

**Recommendation:** Set on all HTTPS routes. Start with a short `max-age` (e.g., `300`) and increase once confirmed working. Only add `preload` if you are committed to HTTPS permanently — it is difficult to undo.

> Zentinel warns during config validation if TLS is enabled but no HSTS header is configured.

### Content Security Policy (CSP)

Controls which resources the browser is allowed to load. This is the most powerful — and most complex — security header.

```kdl
"Content-Security-Policy" "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; frame-ancestors 'self'"
```

Common directives:

| Directive | Controls |
|-----------|----------|
| `default-src` | Fallback for all resource types |
| `script-src` | JavaScript sources |
| `style-src` | CSS sources |
| `img-src` | Image sources |
| `font-src` | Font sources |
| `connect-src` | Fetch, XHR, WebSocket targets |
| `frame-ancestors` | Who can embed this page (replaces `X-Frame-Options`) |
| `form-action` | Where forms can submit to |
| `upgrade-insecure-requests` | Automatically upgrade HTTP to HTTPS |

**Recommendation:** Start with a report-only policy to identify violations before enforcing:

```kdl
"Content-Security-Policy-Report-Only" "default-src 'self'; report-uri /csp-report"
```

Once tuned, switch to `Content-Security-Policy` to enforce.

### Permissions Policy

Controls which browser features (camera, microphone, geolocation, etc.) can be used on the page.

```kdl
"Permissions-Policy" "geolocation=(), microphone=(), camera=(), payment=(), usb=()"
```

| Syntax | Meaning |
|--------|---------|
| `feature=()` | Disable for all origins |
| `feature=(self)` | Allow for same origin only |
| `feature=(self "https://example.com")` | Allow for same origin and specific origin |
| `feature=*` | Allow for all origins |

**Recommendation:** Disable all features you don't use. This limits the attack surface if your page is compromised.

### Cross-Origin Headers

These headers control cross-origin resource sharing and isolation:

```kdl
// Prevent your resources from being embedded cross-origin
"Cross-Origin-Resource-Policy" "same-origin"

// Isolate the browsing context (required for SharedArrayBuffer)
"Cross-Origin-Opener-Policy" "same-origin"

// Block cross-origin no-cors requests to your resources
"Cross-Origin-Embedder-Policy" "require-corp"
```

**Recommendation:** Set `Cross-Origin-Resource-Policy: same-origin` for APIs. The opener and embedder policies are mainly needed for applications that use `SharedArrayBuffer` or want full site isolation.

## XSS Protection (Deprecated)

The `X-XSS-Protection` header is **deprecated** and should not be used. Modern browsers have removed their XSS auditor, and the header is a no-op. In older browsers, it can actually [introduce vulnerabilities](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/X-XSS-Protection).

Use `Content-Security-Policy` instead for XSS protection.

## Complete Example

A production-ready configuration with security headers for a typical web application:

```kdl
filters {
    filter "security-headers" {
        type "headers"
        phase "response"
        set {
            "X-Content-Type-Options" "nosniff"
            "X-Frame-Options" "SAMEORIGIN"
            "Referrer-Policy" "strict-origin-when-cross-origin"
            "Strict-Transport-Security" "max-age=31536000; includeSubDomains"
            "Permissions-Policy" "geolocation=(), microphone=(), camera=(), payment=()"
            "Content-Security-Policy" "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self'; connect-src 'self'; frame-ancestors 'self'"
            "Cross-Origin-Resource-Policy" "same-origin"
        }
        remove "Server" "X-Powered-By"
    }
}

routes {
    route "app" {
        matches { path-prefix "/" }
        upstream "backend"
        filters "security-headers"
    }
}
```

### API-Specific Headers

APIs typically need different CSP and framing policies:

```kdl
filters {
    filter "api-security-headers" {
        type "headers"
        phase "response"
        set {
            "X-Content-Type-Options" "nosniff"
            "X-Frame-Options" "DENY"
            "Referrer-Policy" "no-referrer"
            "Strict-Transport-Security" "max-age=31536000; includeSubDomains"
            "Content-Security-Policy" "default-src 'none'; frame-ancestors 'none'"
            "Cross-Origin-Resource-Policy" "same-origin"
        }
        remove "Server" "X-Powered-By"
    }
}
```

## Verifying Headers

After configuring, verify your headers are set correctly:

```bash
# Check response headers
curl -sI https://your-domain.com | grep -iE "x-content|x-frame|referrer|strict|content-security|permissions"

# Online scanner (checks against OWASP recommendations)
# https://securityheaders.com
```

## See Also

- [Security Hardening](/operations/security-hardening/) — Full production hardening guide
- [Filters](/configuration/filters/) — Reusable filter definitions
- [Routes](/configuration/routes/) — Route-level policies

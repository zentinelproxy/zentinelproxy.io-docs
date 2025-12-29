+++
title = "Quick Start"
weight = 0
+++

Get Sentinel up and running in under 5 minutes.

## 1. Install Sentinel

Run the install script:

```bash
curl -fsSL https://getsentinel.raskell.io | sh
```

Add to your PATH if needed:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Verify it works:

```bash
sentinel --version
```

## 2. Create a Configuration File

Create `sentinel.kdl` in your current directory:

```kdl
server {
    worker-threads 0
}

listeners {
    listener "http" {
        address "0.0.0.0:8080"
        protocol "http"
    }
}

routes {
    route "api" {
        matches {
            path-prefix "/api/"
        }
        upstream "api-backend"
    }

    route "default" {
        priority "low"
        matches {
            path-prefix "/"
        }
        upstream "web-backend"
    }
}

upstreams {
    upstream "api-backend" {
        targets {
            target { address "127.0.0.1:3000" }
        }
    }

    upstream "web-backend" {
        targets {
            target { address "127.0.0.1:3001" }
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

## 3. Start a Test Backend

For testing, start a simple backend server:

```bash
# Using Python (port 3000)
python3 -m http.server 3000 &

# Or using Node.js
npx http-server -p 3000 &
```

## 4. Run Sentinel

```bash
sentinel -c sentinel.kdl
```

You should see:

```
INFO sentinel starting up
INFO listener http listening on 0.0.0.0:8080
INFO metrics server listening on 0.0.0.0:9090
```

## 5. Test It

In a new terminal:

```bash
# Test the proxy
curl http://localhost:8080/

# Check metrics
curl http://localhost:9090/metrics
```

## What's Happening

1. **Listener** accepts HTTP connections on port 8080
2. **Router** matches requests against route rules:
   - `/api/*` requests go to `api-backend` (port 3000)
   - All other requests go to `web-backend` (port 3001)
3. **Upstream** forwards requests to your backend servers
4. **Metrics** are exposed on port 9090 for monitoring

## Add Health Checks

Update your config to add health checks:

```kdl
upstreams {
    upstream "api-backend" {
        targets {
            target { address "127.0.0.1:3000" }
        }
        health-check {
            type "http" {
                path "/health"
            }
            interval-secs 10
            unhealthy-threshold 3
        }
    }
}
```

Reload the configuration:

```bash
# Send SIGHUP to reload
kill -HUP $(pgrep sentinel)
```

## Add TLS

For HTTPS, generate certificates and update the config:

```bash
# Generate self-signed cert for testing
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes \
  -subj "/CN=localhost"
```

```kdl
listeners {
    listener "https" {
        address "0.0.0.0:8443"
        protocol "https"
        tls {
            cert-file "cert.pem"
            key-file "key.pem"
        }
    }
}
```

Test with:

```bash
curl -k https://localhost:8443/
```

## Next Steps

- [Basic Configuration](../basic-configuration/) - Detailed configuration reference
- [First Route](../first-route/) - Deep dive into routing
- [Service Types](/service-types/overview/) - Learn about API, web, and static modes
- [Health Checks](/features/health-checks/) - Configure upstream monitoring

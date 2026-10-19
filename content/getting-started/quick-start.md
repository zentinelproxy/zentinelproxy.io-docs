+++
title = "Quick Start"
weight = 2
updated = 2026-10-19
+++

Get Zentinel routing traffic to two local backends, check its configuration, add a health check and serve HTTPS. Every command on this page can be run as written, in order, on Linux or macOS. You need `curl`, `python3` and `openssl`.

## 1. Install Zentinel

```bash
curl -fsSL https://get.zentinelproxy.io | sh
```

The script installs to `/usr/local/bin`. If that directory is not writable it runs `sudo`, which may ask for your password; if `sudo` fails, it installs to `~/.local/bin` instead. In that case, add that directory to your `PATH`:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Check it works:

```bash
zentinel --version
```

To install from a release archive instead, see [Installation](../installation/).

## 2. Start two test backends

Make a working directory with one page for each backend, so you can see which one answered:

```bash
mkdir -p zentinel-quickstart && cd zentinel-quickstart
mkdir -p demo/api-backend/api demo/web-backend
echo "hello from the API backend" > demo/api-backend/api/index.html
echo "hello from the web backend" > demo/web-backend/index.html

python3 -m http.server 3000 --bind 127.0.0.1 --directory demo/api-backend &
python3 -m http.server 3001 --bind 127.0.0.1 --directory demo/web-backend &
```

## 3. Write the configuration

Create `zentinel.kdl`:

```kdl
system {
    worker-threads 0
}

listeners {
    listener "http" {
        address "127.0.0.1:8080"
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
        target "127.0.0.1:3000"
    }

    upstream "web-backend" {
        target "127.0.0.1:3001"
    }
}

observability {
    metrics {
        enabled #true
        address "127.0.0.1:9090"
    }
}
```

`worker-threads 0` means one worker per CPU core. The addresses bind to `127.0.0.1` so nothing is exposed beyond your machine; use `0.0.0.0` to accept connections from elsewhere.

## 4. Check the configuration

Zentinel has two checks, and you want both:

```bash
zentinel test -c zentinel.kdl
zentinel lint -c zentinel.kdl
```

`test` loads the configuration exactly as the proxy would and fails on anything that stops it starting: syntax errors, a missing required setting, a route pointing at an upstream that doesn't exist.

`lint` also reports **settings that are being ignored**. KDL accepts any name, so a misspelled optional setting is not an error: the proxy runs on the default and `test` says the file is fine. Only `lint` tells you. For example, `interval-sec 5` where `interval-secs` was meant:

```fragment,kdl
health-check {
    interval-sec 5    // typo: ignored, the default interval applies
}
```

```
$ zentinel test -c zentinel.kdl
zentinel: configuration file zentinel.kdl test is successful
$ zentinel lint -c zentinel.kdl
  ⚠  'interval-sec' is not a setting in the 'health-check' block and is being ignored. Did you mean 'interval-secs'?
```

For the configuration above, `lint` prints only best-practice advice: no timeouts or retry policy on the routes, no health checks. That's expected for a first config, and the next steps fix some of it. Run `lint` whenever you change the file.

## 5. Run Zentinel

```bash
zentinel -c zentinel.kdl
```

Among the startup lines you should see:

```
INFO zentinel_proxy::metrics_server: Metrics server listening address=127.0.0.1:9090 path=/metrics
INFO zentinel: HTTP listening on: 127.0.0.1:8080
```

A warning that the log manager could not create `/var/log/zentinel` is harmless here: file logging is disabled and logs go to the terminal. Always pass `-c`. Without it, Zentinel ignores any `zentinel.kdl` in the current directory and starts with a built-in default configuration.

## 6. Send requests

In a second terminal:

```bash
curl http://localhost:8080/api/
# hello from the API backend

curl http://localhost:8080/
# hello from the web backend

curl -s http://localhost:9090/metrics | head
```

What happened:

1. The **listener** accepted the connection on port 8080.
2. The **router** compared the path with each route. `/api/` matched `path-prefix "/api/"` on the `api` route. Everything else fell through to `default`, which is `priority "low"` so it is tried last.
3. The route's **upstream** forwarded the request to that backend.

Note that `path-prefix "/api/"` does not match `/api` without the trailing slash.

## 7. Add a health check

Replace the `api-backend` upstream with:

```kdl
upstreams {
    upstream "api-backend" {
        target "127.0.0.1:3000"
        health-check {
            type "http" {
                path "/api/"
            }
            interval-secs 5
            unhealthy-threshold 3
        }
    }

    upstream "web-backend" {
        target "127.0.0.1:3001"
    }
}
```

Every 5 seconds Zentinel requests `/api/` from the backend, and after 3 failures in a row it stops sending traffic there. Run `zentinel lint -c zentinel.kdl` again, then **restart** Zentinel (Ctrl-C, then `zentinel -c zentinel.kdl`). The log shows `Started active health checking`.

> Zentinel reloads its configuration on `SIGHUP`, but a reload does not yet start health checks for upstreams it changed ([#516](https://github.com/zentinelproxy/zentinel/issues/516)), so restart after adding or changing one.

## 8. Serve HTTPS

Create a self-signed certificate for testing:

```bash
openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 365 -nodes \
  -subj "/CN=localhost"
```

Add a second listener next to the first one:

```kdl
listeners {
    listener "http" {
        address "127.0.0.1:8080"
        protocol "http"
    }

    listener "https" {
        address "127.0.0.1:8443"
        protocol "https"
        tls {
            cert-file "cert.pem"
            key-file "key.pem"
        }
    }
}
```

Restart Zentinel, then:

```bash
curl -k https://localhost:8443/api/
# hello from the API backend
```

`-k` tells curl to accept the self-signed certificate. For real certificates, see [TLS](/configuration/listeners/) and automatic certificates with ACME.

## Proxy to an HTTPS backend

If your backend serves HTTPS (e.g., an external API on port 443), add a `tls` block to the upstream:

```kdl
system {
    worker-threads 0
}

listeners {
    listener "http" {
        address "127.0.0.1:8080"
        protocol "http"
    }
}

routes {
    route "default" {
        matches { path-prefix "/" }
        upstream "api-backend"
    }
}

upstreams {
    upstream "api-backend" {
        target "api.example.com:443"
        tls {
            sni "api.example.com"
        }
    }
}
```

> **Important:** Without the `tls` block, Zentinel connects with plaintext HTTP regardless of the port number. This causes 502 errors or redirect loops when the backend expects HTTPS. See [Upstream TLS](/configuration/upstreams/#upstream-tls) for full details.

## Cleaning up

Stop Zentinel with Ctrl-C, then stop the two backends:

```bash
kill %1 %2
```

## Troubleshooting

### "command not found: zentinel"

The install directory isn't in your `PATH`:

```bash
ls /usr/local/bin/zentinel ~/.local/bin/zentinel 2>/dev/null

# If it is in ~/.local/bin, add this to ~/.bashrc or ~/.zshrc:
export PATH="$HOME/.local/bin:$PATH"
```

### A setting seems to have no effect

Run `zentinel lint -c zentinel.kdl` and look for "is being ignored". A misspelled or misplaced setting is dropped without an error, and only `lint` reports it.

### "Address already in use" when starting

Another process is using one of the ports (8080, 8443 or 9090):

```bash
lsof -i :8080
```

Stop that process, or change the port in `zentinel.kdl`.

### 503 Service Unavailable

Zentinel is running but cannot reach the backend for that route. Check that the backend is up:

```bash
curl http://127.0.0.1:3000/api/
curl http://127.0.0.1:3001/
```

### "test is successful" but the proxy behaves differently

Check that you passed the same file to both: `zentinel test -c zentinel.kdl` and `zentinel -c zentinel.kdl`. Without `-c`, both use the built-in default configuration.

## Next Steps

- [First Route](../first-route/): matching, priorities and route policies in depth
- [Your First Agent](../first-agent/): run an agent, attach it to a route and see what happens when it stops
- [Basic Configuration](../basic-configuration/): the blocks every configuration has
- [Upstreams](/configuration/upstreams/): load balancing, health checks and connection pools
- [Agents](/agents/): add WAF, authentication and rate limiting

+++
title = "Your First Agent"
weight = 4
updated = 2026-10-19
+++

Run an agent next to Zentinel, attach it to a route and see what it changes in the request your backend receives. Then stop the agent and see what Zentinel does without it. This page continues from the [Quick Start](../quick-start/): same `zentinel-quickstart` directory, backends on ports 3000 and 3001, listener on `127.0.0.1:8080`. Every command can be run as written, in order, on Linux or macOS.

## What an agent is

An agent is a separate process that Zentinel calls while it handles a request. Zentinel sends it an event, such as "these are the request headers", over gRPC or a Unix socket, and the agent answers with a decision: allow the request, block it, or allow it with changes such as added headers. Zentinel's security features (WAF, authentication, rate limiting and others) are built this way, so they run, crash and get updated separately from the proxy. See [Agents](/agents/) for the list of transports and the protocol, and [Agent Pipeline](/concepts/agent-pipeline/) for how several agents on one route are combined.

This guide uses the echo agent, which ships in the Zentinel release archive. It allows every request and adds `X-Echo-*` headers to it, so you can see that it ran.

## 1. Show the headers your backend receives

If the Quick Start is still running, stop Zentinel with Ctrl-C and the backends with `kill %1 %2`. Then, in the `zentinel-quickstart` directory, create `show-headers.py`, a backend that answers every request with the request headers it received:

```python
from http.server import BaseHTTPRequestHandler, HTTPServer

class ShowHeaders(BaseHTTPRequestHandler):
    def do_GET(self):
        body = "".join(f"{name}: {value}\n" for name, value in self.headers.items()).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

HTTPServer(("127.0.0.1", 3000), ShowHeaders).serve_forever()
```

Start it on port 3000 in place of the API backend, and the web backend on 3001 as before:

```bash
python3 show-headers.py &
python3 -m http.server 3001 --bind 127.0.0.1 --directory demo/web-backend &
```

Replace `zentinel.kdl` with the Quick Start configuration, without the health check and HTTPS listener:

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

Start Zentinel:

```bash
zentinel -c zentinel.kdl
```

In a second terminal:

```bash
curl http://localhost:8080/api/
```

```
Host: localhost:8080
User-Agent: curl/8.7.1
Accept: */*
X-Correlation-Id: VAbGZ77itpQ
X-Forwarded-By: Zentinel
X-Trace-Id: VAbGZ77itpQ
```

The first three headers come from curl, the last three from Zentinel. The ID differs on every request.

## 2. Get the echo agent

The install script installs only `zentinel`. The echo agent is in the release archive for your platform. In the second terminal, from the `zentinel-quickstart` directory, download the archive for the release you have installed and extract the agent:

```bash
release=$(zentinel --version | sed 's/.*release \([^,]*\),.*/\1/')
os=$(uname -s | tr '[:upper:]' '[:lower:]')
arch=$(uname -m | sed 's/x86_64/amd64/; s/aarch64/arm64/')
curl -fsSL "https://github.com/zentinelproxy/zentinel/releases/download/${release}/zentinel-${release}-${os}-${arch}.tar.gz" \
  | tar -xz ./zentinel-echo-agent
chmod +x zentinel-echo-agent
./zentinel-echo-agent --version
```

The `chmod` is needed because the binaries in the archive are not marked executable.

## 3. Start the agent

Still in the second terminal, start the agent as a gRPC server on localhost:

```bash
./zentinel-echo-agent --grpc 127.0.0.1:50051
```

It logs in JSON. Among the first lines:

```
{"timestamp":"...","level":"INFO","fields":{"message":"Echo agent ready and listening on gRPC"},"target":"zentinel_echo_agent"}
{"timestamp":"...","level":"INFO","fields":{"message":"gRPC agent server v2 listening","agent_id":"echo-agent","address":"127.0.0.1:50051"},"target":"zentinel_agent_protocol::v2::server"}
```

Leave it running.

## 4. Attach the agent to the `api` route

Agents are connected to routes in three steps: declare the agent in an `agents` block, wrap it in a filter of `type "agent"`, and list the filter on the route. Replace `zentinel.kdl` with:

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

agents {
    agent "echo" type="custom" {
        grpc "http://127.0.0.1:50051"
        events "request_headers"
        timeout-ms 100
    }
}

filters {
    filter "echo-headers" {
        type "agent"
        agent "echo"
        failure-mode "closed"
    }
}

routes {
    route "api" {
        matches {
            path-prefix "/api/"
        }
        upstream "api-backend"
        filters "echo-headers"
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

What the new parts do:

- `agent "echo" type="custom"` names the agent. The type is a label; `custom` fits an agent that is not a WAF, auth or rate-limit agent.
- `grpc "http://127.0.0.1:50051"` is where the agent listens. `http://` means gRPC without TLS, which is fine on localhost. For a Unix socket, use `unix-socket "/path/to.sock"` instead.
- `events "request_headers"` sends the agent the request headers, and nothing else. Bodies and responses are separate events.
- `timeout-ms 100` is how long Zentinel waits for each answer. The default is 1000.
- The filter `echo-headers` puts the agent on any route that lists it. `failure-mode "closed"` is explained in step 6.
- `filters "echo-headers"` on the `api` route is what makes Zentinel call the agent. The `default` route does not list it, so requests to `/` never reach the agent.

Check the file and restart Zentinel (Ctrl-C in the first terminal, then start it again):

```bash
zentinel test -c zentinel.kdl
zentinel lint -c zentinel.kdl
zentinel -c zentinel.kdl
```

`lint` should report only the same best-practice advice as in the Quick Start. In Zentinel's log you should see it connect:

```
INFO zentinel_agent_protocol::v2::client: v2 handshake successful agent_id=echo protocol_version=2
INFO zentinel_proxy::agents::manager: Agent initialization complete initialized=1 failed=0 total=1
```

## 5. See what the agent changed

Open a third terminal and send the same request as before:

```bash
curl http://localhost:8080/api/
```

```
Host: localhost:8080
User-Agent: curl/8.7.1
Accept: */*
X-Correlation-Id: VBDP3uQxR6X
X-Forwarded-By: Zentinel
X-Echo-Agent: echo-agent/1.0
X-Echo-Correlation-Id: VBDP3uQxR6X
X-Echo-Request-Num: 1
X-Echo-Method: GET
X-Echo-Path: /api/
X-Trace-Id: VBDP3uQxR6X
```

The five `X-Echo-*` headers were added by the agent. Zentinel sent it the method, path, headers and correlation ID, the agent answered "allow, and set these headers", and Zentinel applied that before forwarding the request. `X-Echo-Request-Num` counts the requests the agent has seen.

A WAF agent works the same way, except that its answer is sometimes "block". An auth agent may answer "allow, and set `X-User-Id`".

## 6. Stop the agent

Stop the agent with Ctrl-C in the second terminal, then in the third terminal:

```bash
curl -i http://localhost:8080/api/
```

```
HTTP/1.1 503 Service Unavailable
Content-Type: text/plain
Content-Length: 19
Date: Mon, 19 Oct 2026 07:07:25 GMT
Connection: close

Service unavailable
```

The request never reached the backend. The filter has `failure-mode "closed"`: if Zentinel cannot get an answer from the agent, it refuses the request. The log says why:

```
WARN zentinel_proxy::proxy::handlers: Request blocked by agent correlation_id=VBinCT1Hjam agent_id="echo" status=503
```

`curl http://localhost:8080/` still answers, because the `default` route has no agent.

Now let requests through when the agent is down. In `zentinel.kdl`, change the filter to:

```kdl
filters {
    filter "echo-headers" {
        type "agent"
        agent "echo"
        failure-mode "open"
    }
}
```

Check it and restart Zentinel (Ctrl-C, then):

```bash
zentinel lint -c zentinel.kdl
zentinel -c zentinel.kdl
```

With the agent still stopped:

```bash
curl -i http://localhost:8080/api/
```

```
HTTP/1.0 200 OK
Server: BaseHTTP/0.6 Python/3.9.6
Date: Mon, 19 Oct 2026 07:11:18 GMT
Content-Type: text/plain
Content-Length: 135
X-Correlation-Id: VFj5baJnfdc
Connection: keep-alive

Host: localhost:8080
User-Agent: curl/8.7.1
Accept: */*
X-Correlation-Id: VFj5baJnfdc
X-Forwarded-By: Zentinel
X-Trace-Id: VFj5baJnfdc
```

The request was forwarded as if the route had no agent: 200, and no `X-Echo-*` headers. Zentinel logs an error for every request the agent missed (`Parallel agent call failed ... filter_failure_mode=Open`), so the outage is visible in the log but not to clients.

To bring the agent back, start it again in the second terminal:

```bash
./zentinel-echo-agent --grpc 127.0.0.1:50051
```

Then restart Zentinel in the first terminal (Ctrl-C, then `zentinel -c zentinel.kdl`), and the `X-Echo-*` headers are back:

```bash
curl -s http://localhost:8080/api/ | grep X-Echo-Agent
# X-Echo-Agent: echo-agent/1.0
```

> In release 26.10_3, Zentinel does not reconnect to an agent that was stopped and started again while Zentinel kept running. Requests keep failing (503 with `closed`, no agent headers with `open`) until Zentinel is restarted; a `SIGHUP` reload is not enough. An agent that was not running when Zentinel *started* is connected later on its own, the first retry after about 10 seconds, then backing off to one attempt every two minutes. Restarting Zentinel after the agent is up is the quick way in both cases. Tracked in [#528](https://github.com/zentinelproxy/zentinel/issues/528).

### Which failure mode to choose

| Mode | Agent unreachable | Agent slower than `timeout-ms` | Choose it when |
|------|-------------------|--------------------------------|----------------|
| `closed` | 503 | 504 | letting a request through unchecked is worse than refusing it: WAF, authentication, authorization |
| `open` | forwarded without the agent | forwarded without the agent | the agent adds something optional: logging, analytics, header enrichment. Rate limiting is often run open so that a limiter outage does not take the API down |

Where Zentinel reads the setting for a request:

1. `failure-mode` on the agent filter, if set.
2. Otherwise `failure-mode` in the route's `policies` block.
3. Otherwise `closed`.

The `failure-mode` setting inside an `agent` block does not decide this. An agent block with `failure-mode "open"` and a filter without one still answers 503 when the agent is down.

The filter accepts exactly `"open"` or `"closed"`. Any other value, such as `"fail-open"`, is dropped without an error or a `lint` warning, and the route's mode applies, which is `closed` unless you set it.

## Unix sockets on macOS

To run the agent on a Unix socket instead of gRPC, start it with `--socket` and use `unix-socket` in the agent block:

```fragment,kdl
agent "echo" type="custom" {
    unix-socket "/tmp/zentinel-echo.sock"
    events "request_headers"
}
```

Keep the socket path short. macOS allows 104 bytes for a Unix socket path (Linux 108). With a longer path, the echo agent logs `Echo agent ready and listening on Unix socket` and then exits with:

```
Error: Failed to run echo agent server

Caused by:
    0: IO error: path must be shorter than SUN_LEN
```

`zentinel test` and `zentinel lint` do not check the length, so the configuration passes, and with `failure-mode "closed"` every request on the route then gets a 503. A socket inside a deeply nested project directory reaches the limit quickly; a path such as `/tmp/zentinel-echo.sock` does not.

## Cleaning up

Stop Zentinel and the agent with Ctrl-C, then stop the two backends in the first terminal:

```bash
kill %1 %2
```

## Next Steps

- [Agents configuration](/configuration/agents/): transports, events, timeouts, circuit breakers, TLS to agents, and example WAF, auth and rate-limit agent blocks
- [Filters](/configuration/filters/): the agent filter next to the built-in ones, such as the `rate-limit` filter that needs no agent
- [WAF Engines](/agents/waf-engines/): choosing between the three WAF agents
- [Bundle Installation](/deployment/bundle/): `zentinel bundle` installs the bundled agents (WAF, auth, rate limiter, denylist and others). `zentinel bundle list` shows what is in the bundle
- [Agent Pipeline](/concepts/agent-pipeline/): what happens when a route has several agents
- [Building agents](/agents/v2/api/): the API for writing your own

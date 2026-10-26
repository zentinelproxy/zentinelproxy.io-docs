+++
title = "Bundle Installation"
weight = 1
updated = 2026-10-26
+++

`zentinel bundle` installs the agents Zentinel is released with: it downloads
each agent's release binary, verifies it, puts it next to the proxy and writes
the `agents { }` block that wires the proxy to it. It is the recommended way to
run agents on a Linux or macOS host.

{% callout(type="info", title="From 26.10_8") %}
Before 26.10_8 `bundle install` pinned agent releases that could not complete
the agent-protocol handshake, wrote a YAML file per agent that no agent read,
and left the proxy's configuration to you, so the agents listened on their
built-in defaults while the documented KDL pointed elsewhere. From 26.10_8
every bundled agent is built from its tag and smoke-tested behind a real
Zentinel before it is published, and the install starts each agent on exactly
the socket or address it writes into `agents.kdl`. Binaries up to 0.6.50
(26.10_7) keep their compiled-in lock and still install the old releases: run
the bundle command of the Zentinel you deploy.
{% end %}

## Overview

`zentinel bundle install` does five things:

1. Reads the version lock compiled into the binary (`bundle-versions.lock`:
   the bundle version, and for every agent its release, repository and the
   platforms it is published for).
2. Downloads each agent's archive from its GitHub release and checks it
   against the published `.sha256`.
3. Installs the binary as `zentinel-<name>-agent` in the bin directory.
4. Writes `agents.kdl` in the config directory: an `agents { }` block with one
   entry per installed agent, on the socket or address the agent is started
   on.
5. With `--systemd`, writes one unit per agent that starts it that way.

```
┌─────────────────────────────────────────────────────────────────────┐
│                    zentinel bundle install                          │
│                                                                     │
│  Reads lock file → Downloads + verifies → Installs binaries         │
│                  → Writes agents.kdl (+ systemd units)              │
│                                                                     │
│  24 bundled agents across 7 categories:                             │
│    Core        ─ WAF, Denylist                                      │
│    Security    ─ ZentinelSec, ModSecurity, IP Reputation,           │
│                  Bot Management, Content Scanner, AI Gateway        │
│    API         ─ GraphQL Security, gRPC Inspector, SOAP,            │
│                  API Deprecation                                    │
│    Protocol    ─ WebSocket Inspector, MQTT Gateway                  │
│    Scripting   ─ Lua, JS, WASM                                      │
│    Utility     ─ Transform, Audit Logger, Mock Server, Chaos,       │
│                  Image Optimization                                 │
│    Identity    ─ SPIFFE, Auth                                       │
└─────────────────────────────────────────────────────────────────────┘
```

The `ratelimit` agent is no longer in the bundle: rate limiting is built into
Zentinel (`policies { rate-limit { ... } }`, see
[Rate Limiting](/configuration/filters/#rate-limiting)). `zentinel bundle
install ratelimit` says so instead of installing it; `zentinel bundle
uninstall ratelimit` still removes a copy installed earlier.

## Quick Start

```bash
# 1. Install Zentinel
curl -fsSL https://get.zentinelproxy.io | sh

# 2. Install the bundled agents, with a systemd unit for each
sudo zentinel bundle install --systemd

# 3. Wire them into the proxy: the install prints this line
echo 'include "/etc/zentinel/agents/agents.kdl"' | sudo tee -a /etc/zentinel/zentinel.kdl

# 4. Start the agents, then the proxy
sudo systemctl daemon-reload
sudo systemctl enable --now zentinel-waf.service zentinel-denylist.service
sudo systemctl restart zentinel.service

# 5. Check
zentinel bundle status
```

Installing agents does not send traffic through them: a route only calls an
agent through a `filter` that names it. See [Wiring agents into the
proxy](#wiring-agents-into-the-proxy).

## Commands Reference

### Install Agents

```bash
# Install all bundled agents
sudo zentinel bundle install

# Also write a systemd unit per agent
sudo zentinel bundle install --systemd

# Install one agent only (agents.kdl still lists every installed agent)
sudo zentinel bundle install waf

# Preview: what would be installed, and the command each agent is started with
zentinel bundle install --dry-run

# Reinstall even if the installed version is up to date
sudo zentinel bundle install --force

# Install under a prefix (bin/, etc/zentinel/agents/, run/zentinel/, lib/systemd/system/)
zentinel bundle install --prefix /opt/zentinel

# Skip checksum verification (not recommended)
sudo zentinel bundle install --skip-verify
```

After installing, the command prints the path of `agents.kdl`, the `include`
line to add to `zentinel.kdl`, and either the `systemctl` commands to start the
units or the command line each agent is started with.

### Check Status

```bash
zentinel bundle status      # -v adds the paths in use
```

```
Zentinel Bundle Status
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Bundle version: 26.10_02
Install path:   /usr/local/bin

Agent           Installed    Expected     Status
───────────────────────────────────────────────────────
ai-gateway      0.3.0        0.3.0        ✓ up to date
api-deprecation 0.5.0        0.5.0        ✓ up to date
audit-logger    0.5.0        0.5.0        ✓ up to date
auth            0.3.0        0.3.0        ✓ up to date
bot-management  0.5.0        0.5.0        ✓ up to date
...
waf             0.4.1        0.4.1        ✓ up to date
wasm            -            0.4.0        ✗ not installed
zentinelsec     0.4.0        0.4.0        ✓ up to date

Total: 24 | Up to date: 23 | Outdated: 0 | Not installed: 1
```

### List Available Agents

```bash
zentinel bundle list

# With repository, binary name, transport, required file and download URL
zentinel bundle list --verbose
```

### Check for Updates

```bash
# Compare the compiled-in lock with the published one, agent by agent
zentinel bundle update

# Same, and print the install command to apply them
zentinel bundle update --apply
```

`bundle update` reads the current lock from
[`api.zentinelproxy.io/v1/bundle/`](https://api.zentinelproxy.io/v1/bundle/)
(falling back to `bundle-versions.lock` on Zentinel's `main` branch) and lists
every agent whose version differs from the one your binary pins. Applying an
update is `zentinel bundle install --force`.

### Uninstall Agents

```bash
sudo zentinel bundle uninstall            # all agents
sudo zentinel bundle uninstall waf        # one agent
zentinel bundle uninstall --dry-run       # preview
```

Uninstalling removes binaries only; configuration files and `agents.kdl` are
left in place.

## What the Install Writes

### Binaries

`<bin dir>/zentinel-<name>-agent`, one per agent, executable.

### agents.kdl

`<config dir>/agents.kdl` is a complete top-level `agents { }` block for every
bundled agent whose binary is installed, each on the socket or address the
agent is started on. It is rewritten on every install, so install agents one
at a time if you like: the file always lists all of them. Pull it into
`zentinel.kdl` with `include` (see [Includes](/configuration/file-format/#include-behavior))
or paste the block in.

```fragment,kdl
// Generated by `zentinel bundle install` (bundle 26.10_02); rerunning it
// overwrites this file. Use it from zentinel.kdl with
//
//     include "/etc/zentinel/agents/agents.kdl"
//
// and send a route's traffic through an agent with a filter:
//
//     filters { filter "waf" { type "agent"; agent "waf"; } }
//     routes { route "app" { filters "waf"; ... } }
//
// `events` defaults to request headers only: add "request_body" (and the
// response events) for agents that inspect bodies.
agents {
    // waf 0.4.1, started as:
    //   /usr/local/bin/zentinel-waf-agent --socket /run/zentinel-agents/waf.sock
    agent "waf" {
        unix-socket "/run/zentinel-agents/waf.sock"
        failure-mode "open"
    }

    // zentinelsec 0.4.0, started as:
    //   /usr/local/bin/zentinel-zentinelsec-agent --grpc-address 127.0.0.1:50151
    agent "zentinelsec" {
        grpc address="http://127.0.0.1:50151"
        failure-mode "open"
    }

    // lua 0.4.0, started as:
    //   /usr/local/bin/zentinel-lua-agent --socket /run/zentinel-agents/lua.sock --script /etc/zentinel/agents/lua.lua
    // It does not start until /etc/zentinel/agents/lua.lua exists.
    agent "lua" {
        unix-socket "/run/zentinel-agents/lua.sock"
        failure-mode "open"
    }
    ...
}
```

Every generated entry carries `failure-mode "open"`, but on an `agent` block
that setting only applies to WebSocket frames: what decides a request when the
agent is unreachable is the `failure-mode` on the **filter** that calls it,
then the route's, and `closed` when neither is set. So an installed agent that
is not running refuses the requests of every filter that names it until you
set `failure-mode "open"` on that filter, and `zentinel test --strict` reports
the generated line as ignored until the filter sets a mode (see [Failure
Mode](/configuration/agents/#failure-mode)). Add `timeout-ms`, `events` or a
`config { }` block to an entry as the agent's README describes, in
`zentinel.kdl` rather than in the generated file, which the next install
rewrites.

### How each agent is started

Every bundled agent takes the same command line (agent protocol v2):

| Agent | Started with |
|-------|--------------|
| Most agents | `--socket <socket dir>/<name>.sock`, wired in as `unix-socket "<same path>"` |
| `zentinelsec` | `--grpc-address 127.0.0.1:50151`, wired in as `grpc address="http://127.0.0.1:50151"`. Its release only serves gRPC |
| `lua`, `js` | the socket, plus `--script <config dir>/lua.lua` or `js.js` |
| `wasm` | the socket, plus `--module <config dir>/wasm.wasm` |

The scripting agents do not start without their file. The install does not
invent one (the format is the agent's; see the agent's README): it prints the
path to create, and the systemd unit carries a matching `ConditionPathExists=`
so the unit waits quietly until the file exists.

Agents that take a configuration file of their own (`--config`, YAML for most)
are started without one. Add the flag to the generated unit's `ExecStart=`
or to your own supervisor's command line, as the agent's README describes. A
file in the config directory that an earlier `bundle install` wrote (a
`<name>.yaml` with a `socket:` block) is not read by any agent; the install
points such files out, and you can delete them.

## Installation Paths

The install is system-wide when run as root (or when every directory below is
writable), user-local otherwise, and under a prefix with `--prefix`.

| | System-wide (root) | User-local | `--prefix DIR` |
|---|---|---|---|
| Binaries | `/usr/local/bin/` | `~/.local/bin/` | `DIR/bin/` |
| `agents.kdl`, agent files | `/etc/zentinel/agents/` | `~/.config/zentinel/agents/` | `DIR/etc/zentinel/agents/` |
| Sockets | `/run/zentinel-agents/` | `~/.local/state/zentinel/run/` | `DIR/run/zentinel/` |
| systemd units | `/etc/systemd/system/` | `~/.config/systemd/user/` | `DIR/lib/systemd/system/` |

The socket directory is created with mode `0750` (system-wide, owned by the
installing user and group) or `0700` (otherwise). A system-wide install does
not use `/run/zentinel`: that is the proxy unit's `RuntimeDirectory=`, which
systemd deletes whenever the proxy stops, and agent sockets in it would vanish
with it. The user-local socket directory is deliberately not
`$XDG_RUNTIME_DIR`: its path is written into the proxy's configuration, so it
has to be the same in every session and survive a logout.

Unix socket paths are limited to 103 bytes. The install warns when a prefix
makes a socket path longer than that; use a shorter `--prefix`.

## Wiring Agents into the Proxy

`agents.kdl` makes the proxy connect to the agents. Traffic reaches an agent
only through a filter on a route:

```kdl
agents {
    agent "waf" {
        unix-socket "/run/zentinel-agents/waf.sock"
        failure-mode "open"
    }
    agent "denylist" {
        unix-socket "/run/zentinel-agents/denylist.sock"
        failure-mode "open"
    }
    agent "image-optimization" {
        unix-socket "/run/zentinel-agents/image-optimization.sock"
        failure-mode "open"
    }
}

filters {
    filter "denylist" {
        type "agent"
        agent "denylist"
        failure-mode "closed"
    }
    filter "waf" {
        type "agent"
        agent "waf"
        failure-mode "closed"
    }
    filter "image-optimization" {
        type "agent"
        agent "image-optimization"
        failure-mode "open"
    }
}

routes {
    route "api" {
        priority "high"
        matches { path-prefix "/api" }
        upstream "backend"
        // Order matters: check the denylist first, then the WAF
        filters "denylist" "waf"
    }

    route "images" {
        priority "normal"
        matches { path-prefix "/images" }
        upstream "cdn"
        filters "denylist" "image-optimization"
    }
}

upstreams {
    upstream "backend" {
        target "127.0.0.1:3000"
    }
    upstream "cdn" {
        target "127.0.0.1:3001"
    }
}
```

In your own `zentinel.kdl` the `agents { }` block comes from the include, and
the rest is yours. Agents that inspect bodies need `events` on their entry
(the default is request headers only); the agent's README says which. From
26.10_8 an agent's `config { }` block is delivered on every connection, see
[Agent-Specific Configuration](/configuration/agents/#agent-specific-configuration).

## Systemd Integration

`bundle install --systemd` writes `zentinel-<name>.service` per installed
agent. Rerunning the install overwrites them.

```bash
sudo zentinel bundle install --systemd
sudo systemctl daemon-reload
sudo systemctl enable --now zentinel-waf.service zentinel-denylist.service
sudo journalctl -u zentinel-waf -f
```

A **system-wide** install gets system units that run as `zentinel` (the
proxy's user, so the proxy may connect to the sockets) with the socket
directory as a preserved `RuntimeDirectory=` shared by every agent unit,
`Before=zentinel.service` (the proxy connects to its agents at startup) and
`WantedBy=multi-user.target`. There is no umbrella target: enable the units
you use.

A **user-local** install gets user units (`systemctl --user daemon-reload`,
`systemctl --user enable --now zentinel-waf.service`), without `User=` (a
user manager cannot switch users) and without `ProtectHome=` (it would hide a
binary in `~/.local/bin`). A **prefix** install writes the units under
`DIR/lib/systemd/system/`; link them into `~/.config/systemd/user/` to use
them as user units.

Each unit is a plain `Type=simple` service with `Restart=on-failure`,
`NoNewPrivileges=true` and `RUST_LOG=info`; system units add
`ProtectSystem=strict`, `ProtectHome=true`, `PrivateTmp=true` and a
`RestrictAddressFamilies=` of Unix and IP sockets. The install prints exactly
which `systemctl` commands to run.

## Bundled Agents

The versions are pinned in the lock compiled into your binary: `zentinel
bundle list` prints them, and
[`api.zentinelproxy.io/v1/bundle/`](https://api.zentinelproxy.io/v1/bundle/)
serves the current one. Each agent's options are in its README, linked from
the [Agent Registry](https://registry.zentinelproxy.io/).

| Category | Agent | What it does |
|----------|-------|--------------|
| Core | `waf` | Pure Rust web application firewall with anomaly scoring and API security rules |
| Core | `denylist` | Blocks by IP, CIDR, path and User-Agent patterns, with lists updated at runtime |
| Security | `zentinelsec` | Pure Rust ModSecurity-compatible engine running the OWASP CRS, no C dependencies (gRPC) |
| Security | `modsec` | OWASP CRS through libmodsecurity |
| Security | `ip-reputation` | Threat intelligence: AbuseIPDB, file-based blocklists, Tor exit nodes |
| Security | `bot-management` | Multi-signal bot scoring and known-bot verification |
| Security | `content-scanner` | ClamAV malware scanning of uploads |
| Security | `ai-gateway` | Prompt and response policy for LLM traffic |
| API | `graphql-security` | Query depth and complexity limits, introspection control |
| API | `grpc-inspector` | Method authorization, metadata inspection |
| API | `soap` | Envelope validation, WS-Security, XXE prevention |
| API | `api-deprecation` | RFC 8594 `Sunset` headers, redirects and blocks for retired endpoints |
| Protocol | `websocket-inspector` | Frame filtering and schema validation for WebSocket traffic |
| Protocol | `mqtt-gateway` | Topic ACLs, client auth and payload inspection for MQTT |
| Scripting | `lua`, `js`, `wasm` | Your own request/response logic in Lua, JavaScript (QuickJS) or WebAssembly; each needs its script or module file |
| Utility | `transform` | URL rewriting, header manipulation, JSON body transforms |
| Utility | `audit-logger` | Structured audit logging with PII redaction and compliance templates |
| Utility | `mock-server` | Stub responses with templating and latency simulation |
| Utility | `chaos` | Fault injection: latency, errors, timeouts |
| Utility | `image-optimization` | JPEG/PNG to WebP/AVIF with content negotiation |
| Identity | `spiffe` | SPIFFE/SPIRE workload identity for service-to-service calls |
| Identity | `auth` | JWT, Basic and API-key authentication |

The `policy` and `data-masking` agents have no release yet and are not in the
bundle. No agent is published for `darwin-x86_64`; on that platform
`bundle install` says so instead of reporting a download error.

## Version Management

The lock (`bundle-versions.lock` in the Zentinel repository, embedded in the
binary at build time) names, for every agent, a release that exists for every
platform listed for it; CI requests each asset before the lock can change.
Your Zentinel release therefore installs a set of agents that was tested
together.

```bash
zentinel bundle status            # installed vs. pinned, per agent
zentinel bundle update            # pinned vs. the published lock
sudo zentinel bundle install --force   # move to the pinned versions
```

Set `ZENTINEL_BUNDLE_DOWNLOAD_URL` to replace `https://github.com` in the asset
URLs when you mirror the releases.

## Troubleshooting

### Permission denied

```bash
sudo zentinel bundle install          # system-wide
zentinel bundle install               # user-local: ~/.local/bin, ~/.config/zentinel/agents
zentinel bundle install --prefix ~/zentinel
```

The install checks that every directory it will create is writable before it
starts, and falls back to user-local paths when one is not.

### Download failed

```bash
zentinel bundle list --verbose        # the exact URL per agent and platform
curl -I https://github.com/zentinelproxy/zentinel-agent-waf/releases
```

A checksum mismatch fails the install for that agent; `--skip-verify` installs
it anyway and reports it as unverified.

### An agent does not start

```bash
sudo journalctl -u zentinel-waf -f                 # its log
sudo systemctl cat zentinel-waf.service            # the command line it runs
ls -la /run/zentinel-agents/                       # sockets present?
zentinel bundle install --dry-run                  # the command each agent is started with
```

The scripting agents wait for their file (`ConditionPathExists=` in the unit:
`systemctl status` shows the unit as inactive with a condition failed, not as
failed). The proxy logs `Failed to connect to agent` with the path it tried;
compare it with the agent's `--socket`. Both come from `agents.kdl` and the
unit, so they differ only if one of them was edited.

### The proxy refuses requests with 503

A filter with `failure-mode "closed"` whose agent is not reachable refuses the
request. Check the agent's unit, and that the proxy runs as a user that may
open the socket (`zentinel`, group `zentinel`, on a system-wide install).

### Version mismatch

```bash
sudo zentinel bundle install --force
```

## Example: Complete Setup

```bash
# 1. Install Zentinel
curl -fsSL https://get.zentinelproxy.io | sh

# 2. Install the agents with systemd units
sudo zentinel bundle install --systemd

# 3. Write the proxy configuration
sudo mkdir -p /etc/zentinel
sudo tee /etc/zentinel/zentinel.kdl > /dev/null << 'KDL'
system {
    worker-threads 0
}

listeners {
    listener "http" {
        address "0.0.0.0:8080"
        protocol "http"
    }
}

include "/etc/zentinel/agents/agents.kdl"

filters {
    filter "denylist" {
        type "agent"
        agent "denylist"
        failure-mode "closed"
    }
    filter "waf" {
        type "agent"
        agent "waf"
        failure-mode "closed"
    }
}

routes {
    route "default" {
        matches { path-prefix "/" }
        upstream "backend"
        filters "denylist" "waf"
    }
}

upstreams {
    upstream "backend" {
        target "127.0.0.1:3000"
    }
}
KDL

# 4. Check the configuration, then start the agents and the proxy
zentinel test --strict -c /etc/zentinel/zentinel.kdl
sudo systemctl daemon-reload
sudo systemctl enable --now zentinel-denylist.service zentinel-waf.service
sudo systemctl enable --now zentinel.service

# 5. Verify
curl localhost:8080/_builtin/health
zentinel bundle status
```

## See Also

- [Installation](/getting-started/installation/) - Installing Zentinel
- [Systemd Deployment](../systemd/) - Production systemd setup for the proxy
- [Docker Compose](../docker-compose/) - Container deployment with agents
- [Agents](/configuration/agents/) - Agent configuration, events, `config { }` delivery
- [Agent Registry](https://registry.zentinelproxy.io/) and
  [API reference](https://api.zentinelproxy.io/reference/) - the bundle lock
  and every agent's metadata as JSON

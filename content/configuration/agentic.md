+++
title = "Agentic Protocols"
weight = 12
updated = 2026-09-02
+++

Zentinel understands the Model Context Protocol (MCP) and Agent2Agent (A2A)
natively. A route carrying either can declare which methods and tools are
permitted, and the proxy enforces that by reading the JSON-RPC envelope.

Both protocols are JSON-RPC 2.0 over HTTP POST, with Server-Sent Events for
streaming responses. What differs is how much a proxy can safely believe
without opening the body — and for MCP the answer is less than it first
appears.

## MCP

```kdl
routes {
    route "mcp" {
        matches {
            path-prefix "/mcp"
        }
        upstream "mcp-server"

        mcp {
            tools {
                allow "get_weather" "search_docs"
                deny "execute_sql"
            }
        }
    }
}
```

A route with an `mcp` block has its request bodies inspected. Without one, MCP
traffic is forwarded as ordinary HTTP.

### Why policy is resolved from the body

MCP's Streamable HTTP transport mirrors parts of the request into headers, so
that intermediaries can route without parsing JSON:

| Header | Mirrors |
|--------|---------|
| `MCP-Protocol-Version` | the protocol revision |
| `Mcp-Method` | `method` |
| `Mcp-Name` | `params.name` or `params.uri` |
| `Mcp-Param-{Name}` | an individual tool argument |

Reading those headers is cheaper than parsing a body, and it is tempting to
build an allowlist on them. Doing so builds an allowlist that allows
everything:

```http
POST /mcp HTTP/1.1
Mcp-Name: read_file                    ← what a header-based allowlist checks

{"method":"tools/call","params":{"name":"delete_everything"}}
                                ↑ what the server actually executes
```

**Zentinel resolves policy from the body.** Headers are read only to confirm
they agree with it, and a request whose header and body disagree is refused:

```
mcp-name header says "read_file" but the request body says "delete_everything";
policy is resolved against the body, and a request that disagrees with itself
is refused
```

This is treated as hostile rather than as a client bug. From the proxy the two
are indistinguishable — a broken client and an attacker send byte-identical
requests — and only one of them is dangerous. A broken client gets an error
message; the alternative is losing the allowlist.

### Protocol version

Revisions before `2026-07-28` did not require mirrored headers to match the
body. A request claiming one of those is refused by default, because its
headers carry no guarantee:

```
protocol version "2025-06-18" predates 2026-07-28, which is the first revision
requiring mirrored headers to match the body; header values from older
revisions cannot be trusted for policy
```

Without this check, header/body validation is optional at the caller's
discretion: claim an old revision and skip it. If you need to accept older
clients, `require-validated-version #false` disables the check — and means
mirrored headers on this route may be unvalidated, which matters if anything
downstream makes decisions from them.

### Settings

```kdl
mcp {
    require-validated-version #true       // default
    validate-param-headers #true          // default
    on-uninspectable-body "deny"          // default

    methods {
        allow "tools/call" "tools/list"
        deny "resources/read"
    }

    tools {
        allow "get_weather" "search_docs"
        deny "execute_sql"
    }
}
```

| Setting | Default | Meaning |
|---------|---------|---------|
| `require-validated-version` | `#true` | Refuse revisions older than `2026-07-28` |
| `validate-param-headers` | `#true` | Check `Mcp-Param-*` against tool arguments |
| `on-uninspectable-body` | `"deny"` | What to do with a body that cannot be read |
| `methods` | *(unset)* | `allow` / `deny` lists for JSON-RPC methods |
| `tools` | *(unset)* | `allow` / `deny` lists for tools and resources |

`methods` and `tools` each take `allow` and `deny`. An absent `allow` list means
no allowlist — everything is permitted except what `deny` names. `deny` is
applied after `allow`, so a name in both is refused.

Writing `allow` with no entries is rejected at parse time rather than read as an
empty allowlist, because "allow nothing listed" and "no restriction" are
opposite meanings for the same line.

### `Mcp-Param-*` headers

A tool schema can mirror individual arguments into headers using an
`x-mcp-header` annotation, and the specification's own example routes by
region:

```http
Mcp-Param-Region: us-west1

{"params":{"name":"execute_sql",
 "arguments":{"region":"us-west1","query":"SELECT 1"}}}
```

These get the same treatment as `Mcp-Name`: a header that disagrees with the
argument it mirrors is refused.

> **One limitation worth knowing.** The header's name comes from the
> `x-mcp-header` label in the tool's schema, and that label is not required to
> equal the property name — `x-mcp-header: "Region"` on a property called
> `region` is the specification's example, but `"Reg"` would be equally valid.
> Zentinel has never seen that schema, so it checks headers whose suffix matches
> an argument name and leaves the rest alone. Denying an unmatched header would
> refuse legitimate traffic over a naming convention the proxy cannot see.
>
> **If you route or rate-limit on `Mcp-Param-*` headers, keep the label equal to
> the property name**, or the proxy cannot confirm the two still agree.
>
> To rate limit by *tool* rather than by argument, prefer the
> [`mcp-tool` rate-limit key](@/configuration/filters.md#rate-limiting-mcp-calls-per-tool),
> which reads the tool from the body and so cannot be misdirected by a header at
> all.

### Bodies that cannot be inspected

A body is uninspectable if it exceeds 1 MiB, is not valid JSON, or is a
JSON-RPC batch array (which Zentinel does not decompose).

`on-uninspectable-body` defaults to `"deny"`, because a body that cannot be read
cannot be checked against an allowlist — failing open would make an oversized or
malformed body a way around policy. Set it to `"allow"` where the `mcp` block is
for observability and enforcement lives elsewhere.

### What this does not do

This is about whether a request is coherent and permitted. It does not inspect
tool *arguments* for prompt injection, secrets, or PII — that is
[agent](../agents/) work, and stays there. The division: Zentinel decides
whether a call may be made, agents decide whether its contents are safe.

## A2A

```kdl
routes {
    route "a2a" {
        matches {
            path-prefix "/a2a"
        }
        upstream "agent"

        a2a {
            methods {
                allow "GetTask" "ListTasks"
                deny "CancelTask"
            }
        }
    }
}
```

A2A defines no mirrored headers — the method exists only in the body. There is
nothing to desynchronise and correspondingly nothing to spoof, so policy reads
the body directly and there is no equivalent of the MCP header checks.

### Settings

| Setting | Default | Meaning |
|---------|---------|---------|
| `unknown-methods` | `"allow"` | What to do with methods Zentinel does not recognise |
| `deny-uninspectable-body` | `#true` | Refuse bodies that cannot be read |
| `methods` | *(unset)* | `allow` / `deny` lists for methods |

`unknown-methods` defaults to `"allow"` deliberately. A2A is young, and a proxy
that refuses every method added after it was built becomes an obstacle to
upgrading the agents behind it. Set `"deny"` where you would rather fail than
forward something the proxy cannot classify.

### Recognised methods

As of A2A v1.0:

`SendMessage` · `SendStreamingMessage` · `GetTask` · `ListTasks` · `CancelTask` ·
`SubscribeToTask` · `CreateTaskPushNotificationConfig` ·
`GetTaskPushNotificationConfig` · `ListTaskPushNotificationConfigs` ·
`DeleteTaskPushNotificationConfig` · `GetExtendedAgentCard`

A common shape is a read-only route — task state may be queried, but nothing may
ask the agent to begin work:

```kdl
a2a {
    methods {
        deny "SendMessage" "SendStreamingMessage"
    }
}
```

### Agent cards

An agent publishes its capability manifest at `/.well-known/agent-card.json`,
listing skills, endpoints and accepted authentication. That is a discovery
document: exposing it decides who can enumerate what an agent can do. If that
matters for your deployment, route it explicitly rather than letting it fall
through a catch-all.

## Observability

Allowed requests record the method and tool resolved **from the body**, so
metrics and audit logs describe what the upstream actually executed rather than
what a header claimed. Denials record the reason, which is written to be read by
an operator rather than parsed:

```
"execute_sql" is not permitted for tools/call on this route
```

## Checking your configuration

`zentinel lint` reports keys inside an `mcp` or `a2a` block that no parser
reads, so a misspelling in a security policy is not silently discarded. A
misspelled setting is refused outright at load time:

```
Unknown setting 'allowed_tools' in mcp block. Valid settings:
require-validated-version, validate-param-headers, on-uninspectable-body,
methods, tools
```

See [Limits](../limits/#checking-bounds-with-zentinel-lint) for what else the
linter checks.

+++
title = "Protocol v1 (Removed)"
weight = 20
sort_by = "weight"
+++

{{ callout(type="warning", title="V1 Protocol Removed") }}
Agent Protocol v1 was **removed** in Zentinel release 26.02_18 (February 2026). All agents must use [Protocol v2](../v2/). The documentation below is preserved for historical reference only.
{{ end }}

## Documentation (Historical)

| Page | Description |
|------|-------------|
| [Protocol Specification](protocol/) | Wire protocol and message formats |
| [Events & Hooks](events/) | Request lifecycle events agents can handle |
| [Building Agents](building/) | How to create your own agent |
| [Transport Protocols](transports/) | Unix sockets and gRPC connectivity |

## Migrating to v2

All agents must use [Protocol v2](../v2/). See the [v2 documentation](../v2/) for the current protocol specification, API reference, and transport options.

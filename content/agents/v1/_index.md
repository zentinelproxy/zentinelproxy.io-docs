+++
title = "Protocol v1 (Legacy)"
weight = 20
sort_by = "weight"
+++

Agent Protocol v1 is the legacy protocol for agent communication. It remains fully supported for backwards compatibility with existing agents.

## Documentation

| Page | Description |
|------|-------------|
| [Protocol Specification](protocol/) | Wire protocol and message formats |
| [Events & Hooks](events/) | Request lifecycle events agents can handle |
| [Building Agents](building/) | How to create your own agent |
| [Transport Protocols](transports/) | Unix sockets and gRPC connectivity |
| [Agent Registry](registry/) | Official and community agents |

## When to Use v1

Use Protocol v1 if you:
- Have existing agents built on v1
- Need simple request-response patterns
- Don't require connection pooling or cancellation

## Migrating to v2

For new deployments, consider [Protocol v2](../v2/) which offers:
- Connection pooling with load balancing
- Request cancellation
- Reverse connections (NAT traversal)
- Enhanced observability with Prometheus metrics

See the [Migration Guide](/operations/upgrade-guide/) for details on upgrading.

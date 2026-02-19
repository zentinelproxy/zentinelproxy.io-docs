+++
title = "Examples"
weight = 5
sort_by = "weight"
template = "section.html"
+++

Complete, production-ready configuration examples for common Zentinel use cases. Each example includes the full configuration file, setup instructions, and testing commands.

## Quick Reference

| Example | Use Case | Key Features |
|---------|----------|--------------|
| [Simple Proxy](simple-proxy/) | Basic reverse proxy | Single upstream, health checks |
| [API Gateway](api-gateway/) | API management | Versioning, auth, rate limiting |
| [Load Balancer](load-balancer/) | Traffic distribution | Multiple backends, algorithms |
| [Static Site](static-site/) | File serving | Caching, compression, SPA |
| [Microservices](microservices/) | Service mesh | Multi-service routing |
| [Security](security/) | WAF + Auth | Agents, protection layers |
| [Observability](observability/) | Monitoring stack | Prometheus, Grafana, tracing |
| [WebSocket](websocket/) | Real-time apps | WS proxying, inspection |
| [AI Gateway](ai-gateway/) | LLM API proxy | Prompt security, PII filtering |
| [LLM Gateway](llm-gateway/) | LLM cost control | Token budgets, cost attribution |

## Getting Started

Each example follows this structure:

1. **Overview** - What the example demonstrates
2. **Configuration** - Complete `zentinel.kdl` file
3. **Setup** - How to run the example
4. **Testing** - Commands to verify it works
5. **Customization** - Common modifications

## Running Examples

All examples assume Zentinel is installed:

```bash
# Install Zentinel
cargo install zentinel-proxy

# Run with a configuration
zentinel -c zentinel.kdl
```

For examples using agents, install the required agents first:

```bash
# Example: Install WAF and auth agents
cargo install zentinel-agent-waf zentinel-agent-auth
```

## Example Files

All configuration files in these examples are available in the [examples directory](https://github.com/zentinelproxy/zentinel/tree/main/examples) of the main repository:

```bash
git clone https://github.com/zentinelproxy/zentinel
cd zentinel/examples
```

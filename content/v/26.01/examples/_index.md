+++
title = "Examples"
weight = 11
sort_by = "weight"
template = "section.html"
+++

Complete, production-ready configuration examples for common Sentinel use cases. Each example includes the full configuration file, setup instructions, and testing commands.

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
2. **Configuration** - Complete `sentinel.kdl` file
3. **Setup** - How to run the example
4. **Testing** - Commands to verify it works
5. **Customization** - Common modifications

## Running Examples

All examples assume Sentinel is installed:

```bash
# Install Sentinel
cargo install sentinel-proxy

# Run with a configuration
sentinel -c sentinel.kdl
```

For examples using agents, install the required agents first:

```bash
# Example: Install WAF and auth agents
cargo install sentinel-agent-waf sentinel-agent-auth
```

## Example Files

All configuration files in these examples are available in the [sentinel-examples](https://github.com/raskell-io/sentinel-examples) repository:

```bash
git clone https://github.com/raskell-io/sentinel-examples
cd sentinel-examples
```

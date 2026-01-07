+++
title = "Core Concepts"
weight = 2
sort_by = "weight"
template = "section.html"
+++

Understanding Sentinel's architecture and design principles.

## Overview

Sentinel is a high-performance reverse proxy built on [Cloudflare's Pingora](https://github.com/cloudflare/pingora) framework. It provides a flexible agent-based architecture for implementing security controls, traffic management, and custom request processing.

## Key Concepts

| Concept | Description |
|---------|-------------|
| **Proxy** | The core Sentinel process that handles incoming requests |
| **Listener** | A network endpoint (IP:port) that accepts connections |
| **Route** | Rules that match requests and direct them to upstreams |
| **Upstream** | A group of backend servers that handle requests |
| **Agent** | An external process that inspects/modifies requests |

## Architecture Principles

1. **Performance First** - Built on Pingora for minimal latency overhead
2. **Agent Isolation** - Security logic runs in separate processes
3. **Fail-Safe Defaults** - Configurable fail-open behavior for resilience
4. **Observable** - Built-in metrics, logging, and tracing

## In This Section

| Page | Description |
|------|-------------|
| [Architecture](architecture/) | System design and component interaction |
| [Components](components/) | Detailed breakdown of each component |
| [Pingora Foundation](pingora/) | Understanding the Pingora framework |
| [Request Flow](request-flow/) | How requests traverse the proxy |
| [Routing](routing/) | Request matching and forwarding rules |
| [Comparison](comparison/) | How Sentinel compares to Envoy, HAProxy, and Nginx |

## Recommended Reading Order

1. Start with [Architecture](architecture/) for the big picture
2. Read [Components](components/) to understand each part
3. Review [Request Flow](request-flow/) to see how they work together
4. Dive into [Routing](routing/) for traffic management details
5. See [Comparison](comparison/) to understand trade-offs with alternatives


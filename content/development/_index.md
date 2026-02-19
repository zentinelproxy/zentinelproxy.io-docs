+++
title = "Development"
weight = 10
sort_by = "weight"
template = "section.html"
+++

Guide for contributors and developers working on Zentinel and its ecosystem.

## Quick Start

```bash
# Clone and build
git clone https://github.com/zentinelproxy/zentinel.git
cd zentinel
cargo build --release

# Run tests
cargo test

# Check formatting and lints
cargo fmt --check
cargo clippy
```

## Section Overview

| Guide | Description |
|-------|-------------|
| [Building from Source](building/) | Compile Zentinel and agents from source |
| [Development Setup](setup/) | IDE configuration, recommended tools |
| [Code Style](code-style/) | Formatting, naming conventions, best practices |
| [Testing](testing/) | Testing strategy and philosophy |
| [Unit Tests](unit-tests/) | Writing and running unit tests |
| [Integration Tests](integration-tests/) | End-to-end testing with real connections |
| [Load Testing](load-testing/) | Performance and stress testing |
| [Contributing](contributing/) | How to contribute to the project |
| [Pull Request Process](pr-process/) | Submitting and reviewing PRs |
| [Release Process](releases/) | Versioning and release workflow |

## Repository Structure

```
zentinel/
├── src/
│   ├── main.rs              # Entry point
│   ├── config/              # KDL configuration parsing
│   ├── server/              # HTTP server, listeners
│   ├── routing/             # Route matching, upstream selection
│   ├── proxy/               # Request/response proxying
│   ├── agents/              # Agent client, protocol handling
│   ├── health/              # Health checks
│   └── observability/       # Metrics, logging, tracing
├── tests/
│   ├── unit/                # Unit tests
│   └── integration/         # Integration tests
├── benches/                 # Benchmarks
└── examples/                # Example configurations
```

## Agent Repositories

Each agent is maintained in its own repository:

| Agent | Repository |
|-------|------------|
| WAF | [zentinel-agent-waf](https://github.com/zentinelproxy/zentinel-agent-waf) |
| ModSecurity | [zentinel-agent-modsec](https://github.com/zentinelproxy/zentinel-agent-modsec) |
| Auth | [zentinel-agent-auth](https://github.com/zentinelproxy/zentinel-agent-auth) |
| Rate Limit | [zentinel-agent-ratelimit](https://github.com/zentinelproxy/zentinel-agent-ratelimit) |
| JavaScript | [zentinel-agent-js](https://github.com/zentinelproxy/zentinel-agent-js) |
| AI Gateway | [zentinel-agent-ai-gateway](https://github.com/zentinelproxy/zentinel-agent-ai-gateway) |
| WebSocket Inspector | [zentinel-agent-websocket-inspector](https://github.com/zentinelproxy/zentinel-agent-websocket-inspector) |

## Agent Protocol

All agents use the shared protocol library:

```toml
[dependencies]
zentinel-agent-protocol = "0.1"
```

See [Agent Development](/agents/custom/) for creating custom agents.

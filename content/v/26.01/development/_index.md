+++
title = "Development"
weight = 12
sort_by = "weight"
template = "section.html"
+++

Guide for contributors and developers working on Sentinel and its ecosystem.

## Quick Start

```bash
# Clone and build
git clone https://github.com/raskell-io/sentinel.git
cd sentinel
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
| [Building from Source](building/) | Compile Sentinel and agents from source |
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
sentinel/
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
| WAF | [sentinel-agent-waf](https://github.com/raskell-io/sentinel-agent-waf) |
| ModSecurity | [sentinel-agent-modsec](https://github.com/raskell-io/sentinel-agent-modsec) |
| Auth | [sentinel-agent-auth](https://github.com/raskell-io/sentinel-agent-auth) |
| Rate Limit | [sentinel-agent-ratelimit](https://github.com/raskell-io/sentinel-agent-ratelimit) |
| JavaScript | [sentinel-agent-js](https://github.com/raskell-io/sentinel-agent-js) |
| AI Gateway | [sentinel-agent-ai-gateway](https://github.com/raskell-io/sentinel-agent-ai-gateway) |
| WebSocket Inspector | [sentinel-agent-websocket-inspector](https://github.com/raskell-io/sentinel-agent-websocket-inspector) |

## Agent Protocol

All agents use the shared protocol library:

```toml
[dependencies]
sentinel-agent-protocol = "0.1"
```

See [Agent Development](/agents/custom/) for creating custom agents.

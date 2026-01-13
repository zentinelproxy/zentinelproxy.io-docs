+++
title = "Building Agents"
weight = 3
+++

This guide covers two approaches to building Sentinel agents:

1. **SDK (Recommended)** - High-level, ergonomic API with less boilerplate
2. **Low-level Protocol** - Direct protocol access for maximum control

## Using the SDK (Recommended)

The [Sentinel Agent SDK](https://github.com/raskell-io/sentinel-agent-sdk) provides a high-level API that handles protocol details, connection management, CLI parsing, and logging automatically.

### Add Dependency

```toml
[dependencies]
sentinel-agent-sdk = { git = "https://github.com/raskell-io/sentinel-agent-sdk" }
```

### Implement Your Agent

```rust
use sentinel_agent_sdk::prelude::*;

struct MyAgent;

#[async_trait]
impl Agent for MyAgent {
    async fn on_request(&self, request: &Request) -> Decision {
        // Block admin paths without token
        if request.path_starts_with("/admin") && request.header("x-admin-token").is_none() {
            return Decision::deny().with_body("Admin access required");
        }

        // Add headers to allowed requests
        Decision::allow()
            .add_request_header("X-Processed-By", "my-agent")
            .add_request_header("X-Client-IP", request.client_ip())
    }

    async fn on_response(&self, _request: &Request, response: &Response) -> Decision {
        // Add security headers to HTML responses
        if response.is_html() {
            Decision::allow()
                .add_response_header("X-Frame-Options", "DENY")
        } else {
            Decision::allow()
        }
    }
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    AgentRunner::new(MyAgent)
        .with_name("my-agent")
        .with_socket("/tmp/my-agent.sock")
        .run()
        .await
}
```

### SDK Features

| Type | Methods |
|------|---------|
| `Request` | `method()`, `path()`, `query("key")`, `header("name")`, `client_ip()`, `body_json::<T>()` |
| `Response` | `status_code()`, `is_success()`, `is_html()`, `header("name")`, `body_json::<T>()` |
| `Decision` | `allow()`, `block(status)`, `deny()`, `redirect(url)`, `add_request_header()`, `with_tag()` |
| `AgentRunner` | `with_name()`, `with_socket()`, `with_json_logs()`, `run()` |

### Handling Configuration

Receive configuration from the proxy's KDL config block:

```rust
#[async_trait]
impl Agent for MyAgent {
    async fn on_configure(&self, config: serde_json::Value) -> Result<(), String> {
        let my_config: MyConfig = serde_json::from_value(config)
            .map_err(|e| format!("Invalid config: {}", e))?;
        // Store config...
        Ok(())
    }
}
```

---

## Using cargo-generate (Low-level)

For more control, use the low-level protocol directly. The fastest way to start is using `cargo-generate`:

```bash
# Install cargo-generate
cargo install cargo-generate

# Generate from template
cargo generate --git https://github.com/raskell-io/sentinel --path agent-template

# Follow prompts for project name and description
```

## Manual Setup

### 1. Create Project

```bash
cargo new my-agent
cd my-agent
```

### 2. Add Dependencies

```toml
# Cargo.toml
[package]
name = "my-agent"
version = "0.1.0"
edition = "2021"

[dependencies]
# Sentinel agent protocol
sentinel-agent-protocol = "0.1"

# Async runtime
tokio = { version = "1", features = ["full"] }
async-trait = "0.1"

# CLI and configuration
clap = { version = "4", features = ["derive", "env"] }
anyhow = "1"

# Logging
tracing = "0.1"
tracing-subscriber = { version = "0.3", features = ["json", "env-filter"] }

# Serialization (for custom config)
serde = { version = "1", features = ["derive"] }
serde_json = "1"
```

### 3. Implement AgentHandler

The core of every agent is the `AgentHandler` trait:

```rust
use async_trait::async_trait;
use sentinel_agent_protocol::{
    AgentHandler, AgentResponse, AuditMetadata, HeaderOp,
    ConfigureEvent, RequestHeadersEvent, RequestBodyChunkEvent,
    ResponseHeadersEvent, ResponseBodyChunkEvent,
    RequestCompleteEvent,
};

pub struct MyAgent {
    // Your agent's state
}

#[async_trait]
impl AgentHandler for MyAgent {
    /// Called once when agent connects (optional)
    async fn on_configure(&self, event: ConfigureEvent) -> AgentResponse {
        // Handle configuration from KDL config block
        AgentResponse::default_allow()
    }

    /// Called when request headers are received
    async fn on_request_headers(&self, event: RequestHeadersEvent) -> AgentResponse {
        // Your logic here
        AgentResponse::default_allow()
    }

    /// Called for each request body chunk (optional)
    async fn on_request_body_chunk(&self, event: RequestBodyChunkEvent) -> AgentResponse {
        AgentResponse::default_allow()
    }

    /// Called when response headers are received (optional)
    async fn on_response_headers(&self, event: ResponseHeadersEvent) -> AgentResponse {
        AgentResponse::default_allow()
    }

    /// Called for each response body chunk (optional)
    async fn on_response_body_chunk(&self, event: ResponseBodyChunkEvent) -> AgentResponse {
        AgentResponse::default_allow()
    }

    /// Called after request completes (optional, for logging)
    async fn on_request_complete(&self, event: RequestCompleteEvent) -> AgentResponse {
        AgentResponse::default_allow()
    }
}
```

### 4. Create Main Entry Point

```rust
use std::path::PathBuf;
use anyhow::{Context, Result};
use clap::Parser;
use tracing::info;
use sentinel_agent_protocol::{AgentServer, GrpcAgentServer};

mod handler;
use handler::MyAgent;

#[derive(Parser)]
#[command(author, version, about)]
struct Args {
    /// Unix socket path
    #[arg(short, long, conflicts_with = "grpc")]
    socket: Option<PathBuf>,

    /// gRPC address (e.g., "0.0.0.0:50051")
    #[arg(short, long, conflicts_with = "socket")]
    grpc: Option<String>,

    /// Log level
    #[arg(short, long, default_value = "info")]
    log_level: String,
}

#[tokio::main]
async fn main() -> Result<()> {
    let args = Args::parse();

    // Initialize logging
    tracing_subscriber::fmt()
        .with_env_filter(&args.log_level)
        .json()
        .init();

    let agent = Box::new(MyAgent::new());

    match (&args.socket, &args.grpc) {
        (Some(socket), None) => {
            info!("Starting agent on Unix socket: {:?}", socket);
            let server = AgentServer::new("my-agent", socket, agent);
            server.run().await.context("Server failed")?;
        }
        (None, Some(addr)) => {
            info!("Starting agent on gRPC: {}", addr);
            let server = GrpcAgentServer::new("my-agent", agent);
            server.run(addr.parse()?).await.context("gRPC server failed")?;
        }
        _ => {
            // Default to Unix socket
            let socket = PathBuf::from("/tmp/my-agent.sock");
            info!("Starting agent on default socket: {:?}", socket);
            let server = AgentServer::new("my-agent", socket, agent);
            server.run().await.context("Server failed")?;
        }
    }

    Ok(())
}
```

## Echo Agent Deep Dive

The Echo Agent is a complete reference implementation. Let's examine its key components.

### Agent Structure

```rust
pub struct EchoAgent {
    /// Header prefix for echo headers
    prefix: String,
    /// Verbose mode flag
    verbose: bool,
    /// Request counter for tracking
    request_count: std::sync::atomic::AtomicU64,
}

impl EchoAgent {
    pub fn new(prefix: String, verbose: bool) -> Self {
        Self {
            prefix,
            verbose,
            request_count: std::sync::atomic::AtomicU64::new(0),
        }
    }
}
```

### Handling Request Headers

```rust
#[async_trait]
impl AgentHandler for EchoAgent {
    async fn on_request_headers(&self, event: RequestHeadersEvent) -> AgentResponse {
        // Increment request counter
        let request_num = self.request_count
            .fetch_add(1, std::sync::atomic::Ordering::Relaxed) + 1;

        // Log the event
        tracing::debug!(
            correlation_id = %event.metadata.correlation_id,
            method = %event.method,
            uri = %event.uri,
            "Processing request"
        );

        // Build response with header mutations
        let mut response = AgentResponse::default_allow();

        // Add echo headers
        response = response
            .add_request_header(HeaderOp::Set {
                name: format!("{}Agent", self.prefix),
                value: "echo-agent/1.0".to_string(),
            })
            .add_request_header(HeaderOp::Set {
                name: format!("{}Correlation-Id", self.prefix),
                value: event.metadata.correlation_id.clone(),
            })
            .add_request_header(HeaderOp::Set {
                name: format!("{}Method", self.prefix),
                value: event.method.clone(),
            })
            .add_request_header(HeaderOp::Set {
                name: format!("{}Path", self.prefix),
                value: event.uri.clone(),
            });

        // Add audit metadata
        let mut audit = AuditMetadata::default();
        audit.tags = vec!["echo".to_string()];
        audit.custom.insert(
            "request_num".to_string(),
            serde_json::Value::Number(request_num.into()),
        );

        response.with_audit(audit)
    }
}
```

### Blocking Requests

To block a request, return a block decision:

```rust
async fn on_request_headers(&self, event: RequestHeadersEvent) -> AgentResponse {
    // Check for blocked paths
    if event.uri.starts_with("/admin") {
        return AgentResponse::block(403, Some("Forbidden".to_string()))
            .with_audit(AuditMetadata {
                tags: vec!["blocked".to_string()],
                reason_codes: vec!["ADMIN_PATH".to_string()],
                ..Default::default()
            });
    }

    // Check for blocked IPs
    if self.blocked_ips.contains(&event.metadata.client_ip) {
        return AgentResponse::block(403, Some("IP Blocked".to_string()));
    }

    AgentResponse::default_allow()
}
```

### Redirecting Requests

```rust
async fn on_request_headers(&self, event: RequestHeadersEvent) -> AgentResponse {
    // Redirect unauthenticated users
    if !event.headers.contains_key("authorization") {
        return AgentResponse::redirect(
            "https://login.example.com/auth".to_string(),
            302,
        );
    }

    AgentResponse::default_allow()
}
```

### Handling Configuration

Implement `on_configure()` to receive configuration from the proxy's KDL config:

```rust
use std::sync::RwLock;
use serde::{Deserialize, Serialize};

// Define your config struct with kebab-case for KDL compatibility
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
#[serde(rename_all = "kebab-case")]
pub struct MyAgentConfig {
    #[serde(default)]
    pub enabled: bool,
    pub threshold: Option<u32>,
    #[serde(default)]
    pub allowed_paths: Vec<String>,
}

pub struct MyAgent {
    config: RwLock<MyAgentConfig>,
}

impl MyAgent {
    pub fn new() -> Self {
        Self {
            config: RwLock::new(MyAgentConfig::default()),
        }
    }
}

#[async_trait]
impl AgentHandler for MyAgent {
    async fn on_configure(&self, event: ConfigureEvent) -> AgentResponse {
        // Parse the JSON config into your struct
        match serde_json::from_value::<MyAgentConfig>(event.config) {
            Ok(new_config) => {
                // Update the agent's configuration
                if let Ok(mut config) = self.config.write() {
                    *config = new_config;
                    tracing::info!("Agent configured successfully");
                }
                AgentResponse::default_allow()
            }
            Err(e) => {
                tracing::error!("Invalid configuration: {}", e);
                // Reject invalid config - proxy won't route to this agent
                AgentResponse::block(500, Some(format!("Invalid config: {}", e)))
            }
        }
    }

    async fn on_request_headers(&self, event: RequestHeadersEvent) -> AgentResponse {
        // Read the current config
        let config = self.config.read().unwrap();

        if !config.enabled {
            return AgentResponse::default_allow();
        }

        // Use config values in your logic
        if config.allowed_paths.iter().any(|p| event.uri.starts_with(p)) {
            return AgentResponse::default_allow();
        }

        // ... rest of your logic
        AgentResponse::default_allow()
    }
}
```

The corresponding KDL configuration:

```kdl
agent "my-agent" type="custom" {
    unix-socket "/tmp/my-agent.sock"
    events "request_headers"
    config {
        enabled #true
        threshold 100
        allowed-paths "/health" "/metrics" "/api/public"
    }
}
```

**Key points:**

- Use `#[serde(rename_all = "kebab-case")]` to match KDL naming conventions
- Use `#[serde(default)]` for optional fields with defaults
- Wrap mutable config in `RwLock` for thread-safe updates
- Return a block decision to reject invalid configurations
- CLI args can serve as fallback when no config block is present

## Running the Agent

### Unix Socket Mode

```bash
# Build
cargo build --release

# Run
./target/release/my-agent --socket /tmp/my-agent.sock
```

### gRPC Mode

```bash
./target/release/my-agent --grpc 0.0.0.0:50051
```

### Docker Deployment

```dockerfile
FROM rust:1.75-slim AS builder
WORKDIR /app
COPY . .
RUN cargo build --release

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y ca-certificates && rm -rf /var/lib/apt/lists/*
COPY --from=builder /app/target/release/my-agent /usr/local/bin/
USER nobody
ENTRYPOINT ["my-agent"]
CMD ["--grpc", "0.0.0.0:50051"]
```

### Systemd Service

```ini
# /etc/systemd/system/my-agent.service
[Unit]
Description=My Sentinel Agent
After=network.target

[Service]
Type=simple
User=sentinel
ExecStart=/usr/local/bin/my-agent --socket /var/run/sentinel/my-agent.sock
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

## Proxy Configuration

Configure Sentinel to use your agent:

```kdl
agents {
    agent "my-agent" type="custom" {
        unix-socket "/var/run/sentinel/my-agent.sock"
        // Or for gRPC:
        // grpc "http://localhost:50051"

        events "request_headers"
        timeout-ms 100
        failure-mode "open"
    }
}

routes {
    route "api" {
        matches { path-prefix "/api/" }
        upstream "backend"
        agents "my-agent"
    }
}
```

## Testing Your Agent

### Unit Tests

```rust
#[cfg(test)]
mod tests {
    use super::*;
    use sentinel_agent_protocol::Decision;

    #[tokio::test]
    async fn test_allows_normal_requests() {
        let agent = MyAgent::new();
        let event = RequestHeadersEvent {
            metadata: RequestMetadata {
                correlation_id: "test-123".to_string(),
                client_ip: "127.0.0.1".to_string(),
                ..Default::default()
            },
            method: "GET".to_string(),
            uri: "/api/users".to_string(),
            headers: HashMap::new(),
        };

        let response = agent.on_request_headers(event).await;
        assert_eq!(response.decision, Decision::Allow);
    }

    #[tokio::test]
    async fn test_blocks_admin_path() {
        let agent = MyAgent::new();
        let event = RequestHeadersEvent {
            method: "GET".to_string(),
            uri: "/admin/secret".to_string(),
            ..Default::default()
        };

        let response = agent.on_request_headers(event).await;
        match response.decision {
            Decision::Block { status, .. } => assert_eq!(status, 403),
            _ => panic!("Expected block decision"),
        }
    }
}
```

### Integration Testing

Test with the actual protocol using grpcurl:

```bash
# Start your agent
./my-agent --grpc 127.0.0.1:50051 &

# Test with grpcurl
grpcurl -plaintext \
  -import-path ./proto -proto agent.proto \
  -d '{
    "version": 1,
    "event_type": "EVENT_TYPE_REQUEST_HEADERS",
    "request_headers": {
      "metadata": {"correlation_id": "test-123", "client_ip": "127.0.0.1"},
      "method": "GET",
      "uri": "/api/test"
    }
  }' \
  127.0.0.1:50051 sentinel.agent.v1.AgentProcessor/ProcessEvent
```

## Best Practices

### Performance

1. **Keep handlers fast** - Agents add latency to every request
2. **Use async I/O** - Never block the event loop
3. **Pre-compile patterns** - Compile regexes at startup
4. **Limit body inspection** - Only inspect when necessary

### Reliability

1. **Handle errors gracefully** - Return allow/block, don't panic
2. **Configure timeouts** - The proxy will timeout slow agents
3. **Use structured logging** - Include correlation IDs
4. **Export metrics** - Prometheus metrics for observability

### Security

1. **Validate all input** - Don't trust data from the proxy
2. **Minimize dependencies** - Fewer deps = smaller attack surface
3. **Keep secrets secure** - Use environment variables
4. **Audit regularly** - Run `cargo audit` in CI

## Building Agents in Other Languages

With gRPC support, you can build agents in any language. See the [Protocol Specification](protocol/) for the protobuf definitions.

### Python Example

```python
import grpc
from concurrent import futures
import agent_pb2
import agent_pb2_grpc

class MyAgent(agent_pb2_grpc.AgentProcessorServicer):
    def ProcessEvent(self, request, context):
        if request.event_type == agent_pb2.EVENT_TYPE_REQUEST_HEADERS:
            headers = request.request_headers
            # Your logic here
            return agent_pb2.AgentResponse(
                version=1,
                allow=agent_pb2.AllowDecision()
            )
        return agent_pb2.AgentResponse(version=1, allow=agent_pb2.AllowDecision())

server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
agent_pb2_grpc.add_AgentProcessorServicer_to_server(MyAgent(), server)
server.add_insecure_port('[::]:50051')
server.start()
server.wait_for_termination()
```

### Go Example

```go
package main

import (
    "context"
    "net"
    pb "github.com/your-org/sentinel-proto"
    "google.golang.org/grpc"
)

type myAgent struct {
    pb.UnimplementedAgentProcessorServer
}

func (a *myAgent) ProcessEvent(ctx context.Context, req *pb.AgentRequest) (*pb.AgentResponse, error) {
    return &pb.AgentResponse{
        Version: 1,
        Decision: &pb.AgentResponse_Allow{
            Allow: &pb.AllowDecision{},
        },
    }, nil
}

func main() {
    lis, _ := net.Listen("tcp", ":50051")
    s := grpc.NewServer()
    pb.RegisterAgentProcessorServer(s, &myAgent{})
    s.Serve(lis)
}
```

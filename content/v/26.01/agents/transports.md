+++
title = "Transport Protocols"
weight = 4
+++

Sentinel agents communicate with the proxy over two transport mechanisms: Unix domain sockets (UDS) and gRPC. Both transports use the same logical protocol—only the wire encoding differs.

## Transport Comparison

| Feature | Unix Socket | gRPC |
|---------|-------------|------|
| **Encoding** | Length-prefixed JSON | Protocol Buffers |
| **Location** | Local only | Local or remote |
| **Latency** | ~50-100µs | ~100-500µs |
| **Throughput** | High | Very high |
| **Streaming** | Manual chunking | Native support |
| **Tooling** | Any JSON library | Protobuf + gRPC toolchain |
| **Language Support** | Universal | Most languages |

## Unix Domain Sockets

Unix sockets provide the lowest-latency option for agents running on the same host as Sentinel.

### Wire Format

Messages are length-prefixed JSON:

```
┌──────────────────┬─────────────────────────────────────┐
│ Length (4 bytes) │ JSON Message (variable length)       │
│ Big-endian u32   │ UTF-8 encoded                        │
└──────────────────┴─────────────────────────────────────┘
```

**Example:**

```
00 00 00 1A  {"event_type":"request_headers"...}
└─────────┘  └──────────────────────────────────┘
  26 bytes          JSON payload
```

### Configuration

```kdl
agent "my-agent" type="custom" {
    unix-socket "/var/run/sentinel/my-agent.sock"
    events "request_headers"
    timeout-ms 100
}
```

### Message Flow

```
Sentinel Proxy                              Agent Process
      │                                           │
      │ ──── [4 bytes: length] ────────────────▶ │
      │ ──── [N bytes: JSON request] ──────────▶ │
      │                                           │
      │                                    (process)
      │                                           │
      │ ◀──── [4 bytes: length] ─────────────── │
      │ ◀──── [N bytes: JSON response] ──────── │
      │                                           │
```

### Rust Implementation

**Server Side (Agent):**

```rust
use tokio::net::UnixListener;
use tokio::io::{AsyncReadExt, AsyncWriteExt};

async fn run_server(socket_path: &str) -> Result<(), Box<dyn std::error::Error>> {
    // Remove existing socket
    let _ = std::fs::remove_file(socket_path);

    let listener = UnixListener::bind(socket_path)?;

    loop {
        let (mut stream, _) = listener.accept().await?;

        tokio::spawn(async move {
            loop {
                // Read length prefix (4 bytes, big-endian)
                let mut len_bytes = [0u8; 4];
                if stream.read_exact(&mut len_bytes).await.is_err() {
                    break; // Client disconnected
                }
                let msg_len = u32::from_be_bytes(len_bytes) as usize;

                // Read JSON message
                let mut buffer = vec![0u8; msg_len];
                stream.read_exact(&mut buffer).await?;

                let request: AgentRequest = serde_json::from_slice(&buffer)?;

                // Process and respond
                let response = process_request(request);
                let response_bytes = serde_json::to_vec(&response)?;

                // Write length prefix
                let len = (response_bytes.len() as u32).to_be_bytes();
                stream.write_all(&len).await?;

                // Write response
                stream.write_all(&response_bytes).await?;
                stream.flush().await?;
            }
            Ok::<_, Box<dyn std::error::Error>>(())
        });
    }
}
```

**Client Side (Proxy):**

```rust
use tokio::net::UnixStream;

async fn call_agent(
    socket_path: &str,
    request: &AgentRequest,
) -> Result<AgentResponse, Box<dyn std::error::Error>> {
    let mut stream = UnixStream::connect(socket_path).await?;

    // Send request
    let request_bytes = serde_json::to_vec(request)?;
    let len = (request_bytes.len() as u32).to_be_bytes();
    stream.write_all(&len).await?;
    stream.write_all(&request_bytes).await?;
    stream.flush().await?;

    // Read response
    let mut len_bytes = [0u8; 4];
    stream.read_exact(&mut len_bytes).await?;
    let msg_len = u32::from_be_bytes(len_bytes) as usize;

    let mut buffer = vec![0u8; msg_len];
    stream.read_exact(&mut buffer).await?;

    let response: AgentResponse = serde_json::from_slice(&buffer)?;
    Ok(response)
}
```

### JSON Message Format

**Request:**

```json
{
  "version": 1,
  "event_type": "request_headers",
  "payload": {
    "metadata": {
      "correlation_id": "abc-123",
      "client_ip": "192.168.1.100",
      "client_port": 54321,
      "protocol": "HTTP/1.1",
      "timestamp": "2025-12-29T08:00:00Z"
    },
    "method": "POST",
    "uri": "/api/users",
    "headers": {
      "content-type": ["application/json"],
      "authorization": ["Bearer token123"]
    }
  }
}
```

**Response:**

```json
{
  "version": 1,
  "decision": {"allow": {}},
  "request_headers": [
    {"set": {"name": "X-User-Id", "value": "user-123"}}
  ],
  "audit": {
    "tags": ["auth", "success"]
  }
}
```

### Socket Path Conventions

| Pattern | Use Case |
|---------|----------|
| `/var/run/sentinel/<agent>.sock` | Production (systemd) |
| `/tmp/<agent>.sock` | Development/testing |
| `~/.sentinel/<agent>.sock` | User-space development |

### Message Size Limits

The protocol enforces a maximum message size of **16 MB** (16,777,216 bytes). Messages exceeding this limit are rejected:

```rust
const MAX_MESSAGE_SIZE: usize = 16 * 1024 * 1024;
```

---

## gRPC Transport

gRPC provides higher throughput and native streaming support, ideal for remote agents or high-volume scenarios.

### Configuration

```kdl
agent "waf-agent" type="waf" {
    grpc "http://localhost:50051"
    events "request_headers" "request_body"
    timeout-ms 200
}

// Remote agent (Kubernetes sidecar, etc.)
agent "ml-scorer" type="custom" {
    grpc "http://ml-service.default.svc.cluster.local:50051"
    timeout-ms 500
}
```

### Service Definition

Agents implement the `AgentProcessor` service:

```protobuf
service AgentProcessor {
    // Process a single event
    rpc ProcessEvent(AgentRequest) returns (AgentResponse);

    // Stream body chunks for inspection
    rpc ProcessEventStream(stream AgentRequest) returns (AgentResponse);
}
```

### Rust Implementation (Server)

Using the `sentinel-agent-protocol` crate:

```rust
use sentinel_agent_protocol::{GrpcAgentServer, AgentHandler, AgentResponse};

struct MyAgent;

#[async_trait::async_trait]
impl AgentHandler for MyAgent {
    async fn on_request_headers(&self, event: RequestHeadersEvent) -> AgentResponse {
        // Your logic here
        AgentResponse::default_allow()
    }
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let agent = Box::new(MyAgent);
    let server = GrpcAgentServer::new("my-agent", agent);

    server.run("0.0.0.0:50051".parse()?).await?;
    Ok(())
}
```

### Go Implementation (Server)

```go
package main

import (
    "context"
    "net"

    pb "github.com/raskell-io/sentinel-proto/go"
    "google.golang.org/grpc"
)

type myAgent struct {
    pb.UnimplementedAgentProcessorServer
}

func (a *myAgent) ProcessEvent(
    ctx context.Context,
    req *pb.AgentRequest,
) (*pb.AgentResponse, error) {
    // Handle different event types
    switch e := req.Event.(type) {
    case *pb.AgentRequest_RequestHeaders:
        return a.handleRequestHeaders(e.RequestHeaders)
    case *pb.AgentRequest_RequestBodyChunk:
        return a.handleRequestBody(e.RequestBodyChunk)
    }

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

### Python Implementation (Server)

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

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    agent_pb2_grpc.add_AgentProcessorServicer_to_server(MyAgent(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    server.wait_for_termination()

if __name__ == '__main__':
    serve()
```

### Testing with grpcurl

```bash
# List available services
grpcurl -plaintext localhost:50051 list

# Test request headers event
grpcurl -plaintext -d '{
  "version": 1,
  "event_type": "EVENT_TYPE_REQUEST_HEADERS",
  "request_headers": {
    "metadata": {
      "correlation_id": "test-123",
      "client_ip": "127.0.0.1"
    },
    "method": "GET",
    "uri": "/api/test"
  }
}' localhost:50051 sentinel.agent.v1.AgentProcessor/ProcessEvent
```

### Streaming for Body Inspection

For large request/response bodies, use the streaming RPC:

```rust
// Client-side (proxy sending body chunks)
let mut stream = client.process_event_stream().await?;

// Send headers first
stream.send(AgentRequest {
    event_type: EventType::RequestHeaders,
    request_headers: Some(headers_event),
    ..Default::default()
}).await?;

// Stream body chunks
for chunk in body_chunks {
    stream.send(AgentRequest {
        event_type: EventType::RequestBodyChunk,
        request_body_chunk: Some(RequestBodyChunkEvent {
            correlation_id: correlation_id.clone(),
            data: chunk.data,
            is_last: chunk.is_last,
            total_size: chunk.total_size,
        }),
        ..Default::default()
    }).await?;
}

// Get final response
let response = stream.finish().await?;
```

---

## Choosing a Transport

### Use Unix Sockets When:

- Agent runs on the same host as Sentinel
- Latency is critical (< 100µs per call)
- Simplicity is preferred (no protobuf toolchain)
- Deploying as systemd services

### Use gRPC When:

- Agent runs on a different host
- Building agents in languages with strong gRPC support
- Need streaming for large body inspection
- Deploying in Kubernetes (service mesh integration)
- Higher throughput requirements

---

## Connection Management

### Unix Socket Considerations

```kdl
agent "local-auth" type="auth" {
    unix-socket "/var/run/sentinel/auth.sock"

    // Connection pool settings
    pool {
        min-connections 2
        max-connections 10
        idle-timeout-ms 30000
    }
}
```

### gRPC Considerations

```kdl
agent "remote-waf" type="waf" {
    grpc "http://waf-service:50051"

    // HTTP/2 connection settings
    http2 {
        keep-alive-interval-ms 10000
        keep-alive-timeout-ms 5000
        max-concurrent-streams 100
    }
}
```

---

## Security

### Unix Socket Security

Unix sockets rely on filesystem permissions:

```bash
# Restrict socket access
chmod 0600 /var/run/sentinel/auth.sock
chown sentinel:sentinel /var/run/sentinel/auth.sock
```

### gRPC Security

For production gRPC agents, use TLS:

```kdl
agent "secure-agent" type="custom" {
    grpc "https://agent.internal:50051"

    tls {
        ca-cert "/etc/sentinel/ca.crt"
        client-cert "/etc/sentinel/client.crt"
        client-key "/etc/sentinel/client.key"
    }
}
```

---

## Failure Handling

Both transports support the same failure policies:

```kdl
agent "auth" type="auth" {
    unix-socket "/var/run/sentinel/auth.sock"
    timeout-ms 100

    // What to do when agent fails
    failure-mode "closed"  // Block requests (secure default)
    // failure-mode "open"  // Allow requests (availability)

    // Circuit breaker
    circuit-breaker {
        failure-threshold 5      // Open after 5 failures
        success-threshold 3      // Close after 3 successes
        timeout-seconds 30       // Half-open after 30s
    }
}
```

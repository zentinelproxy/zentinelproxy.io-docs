+++
title = "Integration Tests"
weight = 7
+++

End-to-end testing with real network connections.

## Integration Test Setup

### Test Server Utilities

Create reusable test infrastructure:

```rust
// tests/common/mod.rs

use std::net::SocketAddr;
use tokio::net::TcpListener;

pub struct TestBackend {
    pub addr: SocketAddr,
    handle: tokio::task::JoinHandle<()>,
}

impl TestBackend {
    /// Start an echo server that returns request info
    pub async fn echo() -> Self {
        let listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
        let addr = listener.local_addr().unwrap();

        let handle = tokio::spawn(async move {
            loop {
                let (stream, _) = listener.accept().await.unwrap();
                tokio::spawn(handle_echo(stream));
            }
        });

        Self { addr, handle }
    }

    /// Start a server that returns fixed response
    pub async fn fixed(status: u16, body: &'static str) -> Self {
        // Implementation
    }

    /// Start a server that delays response
    pub async fn slow(delay: Duration) -> Self {
        // Implementation
    }
}

impl Drop for TestBackend {
    fn drop(&mut self) {
        self.handle.abort();
    }
}
```

### Test Proxy Setup

```rust
pub struct TestProxy {
    pub addr: SocketAddr,
    handle: tokio::task::JoinHandle<()>,
    config_path: PathBuf,
}

impl TestProxy {
    pub async fn start(config: &str) -> Self {
        // Write config to temp file
        let dir = tempfile::tempdir().unwrap();
        let config_path = dir.path().join("sentinel.kdl");
        std::fs::write(&config_path, config).unwrap();

        // Start sentinel
        let listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
        let addr = listener.local_addr().unwrap();

        let handle = tokio::spawn(async move {
            sentinel::run(config_path).await
        });

        // Wait for server to be ready
        Self::wait_ready(addr).await;

        Self { addr, handle, config_path }
    }

    async fn wait_ready(addr: SocketAddr) {
        for _ in 0..50 {
            if TcpStream::connect(addr).await.is_ok() {
                return;
            }
            tokio::time::sleep(Duration::from_millis(100)).await;
        }
        panic!("Proxy failed to start");
    }

    pub fn url(&self, path: &str) -> String {
        format!("http://{}{}", self.addr, path)
    }
}
```

## Writing Integration Tests

### Basic Proxy Test

```rust
// tests/proxy_test.rs

mod common;
use common::{TestBackend, TestProxy};

#[tokio::test]
async fn test_proxy_forwards_request() {
    // Start backend
    let backend = TestBackend::echo().await;

    // Start proxy with config
    let config = format!(r#"
        listeners {{
            listener "http" {{
                address "127.0.0.1:0"
            }}
        }}
        routes {{
            route "api" {{
                matches {{ path-prefix "/" }}
                upstream "backend"
            }}
        }}
        upstreams {{
            upstream "backend" {{
                targets {{
                    target {{ address "{}" }}
                }}
            }}
        }}
    "#, backend.addr);

    let proxy = TestProxy::start(&config).await;

    // Make request through proxy
    let response = reqwest::get(proxy.url("/api/test"))
        .await
        .unwrap();

    assert_eq!(response.status(), 200);
}
```

### Testing Headers

```rust
#[tokio::test]
async fn test_proxy_adds_headers() {
    let backend = TestBackend::echo().await;

    let config = format!(r#"
        routes {{
            route "api" {{
                matches {{ path-prefix "/" }}
                upstream "backend"
                policies {{
                    request-headers {{
                        set {{ "X-Proxy" "sentinel" }}
                    }}
                }}
            }}
        }}
        // ... upstreams
    "#, backend.addr);

    let proxy = TestProxy::start(&config).await;

    let response = reqwest::get(proxy.url("/test")).await.unwrap();
    let body: serde_json::Value = response.json().await.unwrap();

    // Echo server returns headers in response
    assert_eq!(body["headers"]["x-proxy"], "sentinel");
}
```

### Testing Error Handling

```rust
#[tokio::test]
async fn test_upstream_unavailable() {
    // No backend - proxy should return 502
    let config = r#"
        routes {
            route "api" {
                matches { path-prefix "/" }
                upstream "backend"
            }
        }
        upstreams {
            upstream "backend" {
                targets {
                    target { address "127.0.0.1:59999" }
                }
            }
        }
    "#;

    let proxy = TestProxy::start(config).await;

    let response = reqwest::get(proxy.url("/test")).await.unwrap();

    assert_eq!(response.status(), 502);
}
```

## Testing Agents

### Agent Test Infrastructure

```rust
use sentinel_agent_protocol::{AgentClient, AgentServer};

pub struct TestAgent {
    pub socket_path: PathBuf,
    handle: JoinHandle<()>,
}

impl TestAgent {
    pub async fn start<H: AgentHandler + Send + Sync + 'static>(
        handler: H,
    ) -> Self {
        let dir = tempfile::tempdir().unwrap();
        let socket_path = dir.path().join("agent.sock");

        let server = AgentServer::bind(&socket_path).await.unwrap();
        let handle = tokio::spawn(async move {
            server.serve(handler).await
        });

        Self { socket_path, handle }
    }
}
```

### Testing WAF Agent

```rust
#[tokio::test]
async fn test_waf_blocks_sql_injection() {
    // Start WAF agent
    let waf = TestAgent::start(WafAgent::new(WafConfig {
        sqli_detection: true,
        block_mode: true,
        ..Default::default()
    })).await;

    // Start backend
    let backend = TestBackend::echo().await;

    // Start proxy with WAF
    let config = format!(r#"
        agents {{
            agent "waf" {{
                transport "unix_socket" {{
                    path "{}"
                }}
                events ["request_headers"]
            }}
        }}
        routes {{
            route "api" {{
                matches {{ path-prefix "/" }}
                upstream "backend"
                agents ["waf"]
            }}
        }}
        upstreams {{
            upstream "backend" {{
                targets {{
                    target {{ address "{}" }}
                }}
            }}
        }}
    "#, waf.socket_path.display(), backend.addr);

    let proxy = TestProxy::start(&config).await;

    // Test SQL injection is blocked
    let response = reqwest::get(
        proxy.url("/api/users?id=1' OR '1'='1")
    ).await.unwrap();

    assert_eq!(response.status(), 403);
}
```

### Testing Agent Communication

```rust
#[tokio::test]
async fn test_agent_protocol_roundtrip() {
    let socket_path = tempfile::tempdir()
        .unwrap()
        .path()
        .join("test.sock");

    // Start server
    let server = AgentServer::bind(&socket_path).await.unwrap();
    let handle = tokio::spawn(async move {
        server.serve(EchoAgent).await
    });

    // Connect client
    let client = AgentClient::connect(&socket_path).await.unwrap();

    // Send request
    let event = RequestHeadersEvent {
        correlation_id: "test-123".to_string(),
        method: "GET".to_string(),
        uri: "/api/test".to_string(),
        headers: vec![],
    };

    let decision = client.send_request_headers(event).await.unwrap();

    assert!(matches!(decision, RequestDecision::Allow));

    handle.abort();
}
```

## Testing WebSocket

```rust
#[tokio::test]
async fn test_websocket_proxy() {
    let backend = TestBackend::websocket_echo().await;

    let config = format!(r#"
        routes {{
            route "ws" {{
                matches {{ path "/ws" }}
                upstream "backend"
                websocket {{
                    enabled true
                }}
            }}
        }}
        // ... upstreams
    "#, backend.addr);

    let proxy = TestProxy::start(&config).await;

    // Connect WebSocket
    let (mut ws, _) = tokio_tungstenite::connect_async(
        format!("ws://{}/ws", proxy.addr)
    ).await.unwrap();

    // Send message
    ws.send(Message::Text("hello".to_string())).await.unwrap();

    // Receive echo
    let msg = ws.next().await.unwrap().unwrap();
    assert_eq!(msg.to_text().unwrap(), "hello");
}
```

## Testing TLS

```rust
#[tokio::test]
async fn test_https_proxy() {
    let certs = TestCerts::generate();
    let backend = TestBackend::echo().await;

    let config = format!(r#"
        listeners {{
            listener "https" {{
                address "127.0.0.1:0"
                protocol "https"
                tls {{
                    cert-file "{}"
                    key-file "{}"
                }}
            }}
        }}
        // ... routes and upstreams
    "#, certs.cert_path.display(), certs.key_path.display());

    let proxy = TestProxy::start(&config).await;

    // Create client with custom CA
    let client = reqwest::Client::builder()
        .add_root_certificate(certs.ca_cert())
        .build()
        .unwrap();

    let response = client
        .get(format!("https://localhost:{}/test", proxy.port()))
        .send()
        .await
        .unwrap();

    assert_eq!(response.status(), 200);
}
```

## Testing Health Checks

```rust
#[tokio::test]
async fn test_health_check_removes_unhealthy_target() {
    // Start two backends
    let healthy = TestBackend::echo().await;
    let unhealthy = TestBackend::fixed(500, "error").await;

    let config = format!(r#"
        upstreams {{
            upstream "backend" {{
                targets {{
                    target {{ address "{}" }}
                    target {{ address "{}" }}
                }}
                health-check {{
                    type "http" {{ path "/health" }}
                    interval-secs 1
                    unhealthy-threshold 2
                }}
            }}
        }}
    "#, healthy.addr, unhealthy.addr);

    let proxy = TestProxy::start(&config).await;

    // Wait for health checks
    tokio::time::sleep(Duration::from_secs(3)).await;

    // All requests should go to healthy backend
    for _ in 0..10 {
        let response = reqwest::get(proxy.url("/test")).await.unwrap();
        assert_eq!(response.status(), 200);
    }
}
```

## Testing Rate Limiting

```rust
#[tokio::test]
async fn test_rate_limiting() {
    let ratelimit = TestAgent::start(RateLimitAgent::new(
        RateLimitConfig {
            requests_per_minute: 5,
            ..Default::default()
        }
    )).await;

    let backend = TestBackend::echo().await;
    let proxy = TestProxy::start(&config).await;

    // First 5 requests succeed
    for _ in 0..5 {
        let response = reqwest::get(proxy.url("/test")).await.unwrap();
        assert_eq!(response.status(), 200);
    }

    // 6th request is rate limited
    let response = reqwest::get(proxy.url("/test")).await.unwrap();
    assert_eq!(response.status(), 429);
}
```

## Parallel Test Execution

### Isolating Tests

```rust
// Use random ports to avoid conflicts
async fn get_free_port() -> u16 {
    TcpListener::bind("127.0.0.1:0")
        .await
        .unwrap()
        .local_addr()
        .unwrap()
        .port()
}

// Use unique socket paths
fn unique_socket_path() -> PathBuf {
    let id = uuid::Uuid::new_v4();
    std::env::temp_dir().join(format!("sentinel-test-{}.sock", id))
}
```

### Serial Tests

For tests that can't run in parallel:

```rust
use serial_test::serial;

#[tokio::test]
#[serial]
async fn test_that_modifies_global_state() {
    // This test runs alone
}
```

## Test Timeouts

```rust
#[tokio::test]
async fn test_with_timeout() {
    let result = tokio::time::timeout(
        Duration::from_secs(10),
        async {
            // Test code
        }
    ).await;

    result.expect("Test timed out");
}
```

## Debugging Integration Tests

### Enable Logging

```rust
#[tokio::test]
async fn test_with_logging() {
    // Initialize logging for test
    let _ = tracing_subscriber::fmt()
        .with_env_filter("sentinel=debug")
        .try_init();

    // Test code
}
```

### Run Single Test

```bash
# Run with output
cargo test test_proxy_forwards_request -- --nocapture

# With debug logging
RUST_LOG=debug cargo test test_proxy_forwards_request -- --nocapture
```

## Next Steps

- [Load Testing](../load-testing/) - Performance testing
- [Unit Tests](../unit-tests/) - Unit testing guide
- [Testing Overview](../testing/) - General strategy

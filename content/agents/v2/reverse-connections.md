+++
title = "Reverse Connections"
weight = 5
+++

This document provides detailed coverage of the reverse connection feature in Agent Protocol v2, which allows agents to connect to the proxy instead of the proxy connecting to agents.

## Overview

Traditional agent deployment requires the proxy to initiate connections to agents:

```
┌─────────┐                    ┌─────────┐
│  Proxy  │ ──── Connect ────► │  Agent  │
└─────────┘                    └─────────┘
```

This model has limitations:
- Agents behind NAT cannot be reached
- Firewall rules must allow inbound connections to agents
- Static agent discovery required
- Scaling requires configuration changes

**Reverse connections** flip this model:

```
┌─────────┐                    ┌─────────┐
│  Proxy  │ ◄──── Connect ──── │  Agent  │
│         │                    │  (NAT)  │
│ Listener│                    │         │
└─────────┘                    └─────────┘
```

Benefits:
- **NAT Traversal**: Agents behind NAT/firewalls can connect out
- **Dynamic Scaling**: Agents register on startup, no config changes
- **Zero-Config Discovery**: Agents announce their capabilities
- **Load-Based Pooling**: Agents can open multiple connections

---

## Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│                         Proxy                                │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │             ReverseConnectionListener                │   │
│  │                                                      │   │
│  │  ┌─────────────┐  ┌─────────────┐                   │   │
│  │  │ UDS Socket  │  │ TCP Socket  │                   │   │
│  │  │ (local)     │  │ (remote)    │                   │   │
│  │  └──────┬──────┘  └──────┬──────┘                   │   │
│  │         │                │                          │   │
│  │         └────────────────┘                          │   │
│  │                  │                                   │   │
│  │                  ▼                                   │   │
│  │         ┌───────────────┐                           │   │
│  │         │ Registration  │                           │   │
│  │         │  Validator    │                           │   │
│  │         └───────┬───────┘                           │   │
│  │                 │                                    │   │
│  └─────────────────┼────────────────────────────────────┘   │
│                    │                                        │
│                    ▼                                        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                   AgentPool                          │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐          │   │
│  │  │  waf-1   │  │  waf-2   │  │  auth-1  │          │   │
│  │  │(reverse) │  │(reverse) │  │(reverse) │          │   │
│  │  └──────────┘  └──────────┘  └──────────┘          │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Registration Flow

```
Agent                                                     Proxy
  │                                                         │
  │ 1. TCP/UDS Connect                                      │
  │ ───────────────────────────────────────────────────────►│
  │                                                         │
  │ 2. RegistrationRequest                                  │
  │    {                                                    │
  │      protocol_version: 2,                               │
  │      agent_id: "waf-worker-3",                          │
  │      capabilities: {                                    │
  │        handles_request_headers: true,                   │
  │        handles_request_body: true,                      │
  │        supports_cancellation: true,                     │
  │        max_concurrent_requests: 100                     │
  │      },                                                 │
  │      auth_token: "secret-token",                        │
  │      metadata: { "version": "1.2.0" }                   │
  │    }                                                    │
  │ ───────────────────────────────────────────────────────►│
  │                                                         │
  │                                          3. Validate    │
  │                                             - Auth      │
  │                                             - Allowlist │
  │                                                         │
  │ 4. RegistrationResponse                                 │
  │    {                                                    │
  │      accepted: true,                                    │
  │      assigned_id: "waf-worker-3-conn-7",                │
  │      config: { "rules_version": "3.4.0" }               │
  │    }                                                    │
  │ ◄───────────────────────────────────────────────────────│
  │                                                         │
  │ 5. Normal v2 protocol                                   │
  │ ◄──────────────────────────────────────────────────────►│
  │                                                         │
```

---

## Listener Configuration

### Basic Setup

```rust
use zentinel_agent_protocol::v2::{
    ReverseConnectionListener,
    ReverseConnectionConfig,
};
use std::time::Duration;

let config = ReverseConnectionConfig {
    handshake_timeout: Duration::from_secs(10),
    max_connections_per_agent: 4,
    require_auth: false,
    allowed_agents: None,
};

// UDS listener for local agents
let listener = ReverseConnectionListener::bind_uds(
    "/var/run/zentinel/agents.sock",
    config.clone(),
).await?;

// TCP listener for remote agents
let listener = ReverseConnectionListener::bind_tcp(
    "0.0.0.0:9090",
    config,
).await?;
```

### Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `handshake_timeout` | 10s | Time allowed for registration handshake |
| `max_connections_per_agent` | 4 | Max connections from same agent_id |
| `require_auth` | false | Require auth_token in registration |
| `allowed_agents` | None | Allowlist of agent IDs (supports wildcards) |

### Security Configuration

```rust
let config = ReverseConnectionConfig {
    // Require authentication
    require_auth: true,

    // Only allow specific agents
    allowed_agents: Some(vec![
        "waf-*".to_string(),           // Wildcard: any waf-prefixed agent
        "auth-primary".to_string(),    // Exact match
        "auth-secondary".to_string(),
    ]),

    // Shorter timeout for faster failure detection
    handshake_timeout: Duration::from_secs(5),

    ..Default::default()
};
```

---

## Accepting Connections

### Simple Accept Loop

```rust
let pool = AgentPool::new();
let listener = ReverseConnectionListener::bind_uds(
    "/var/run/zentinel/agents.sock",
    ReverseConnectionConfig::default(),
).await?;

// Accept loop
loop {
    match listener.accept().await {
        Ok((client, registration)) => {
            tracing::info!(
                agent_id = %registration.agent_id,
                capabilities = ?registration.capabilities,
                "Agent connected"
            );

            // Add to pool
            if let Err(e) = pool.add_reverse_connection(
                &registration.agent_id,
                client,
                registration.capabilities,
            ).await {
                tracing::error!("Failed to add agent: {}", e);
            }
        }
        Err(e) => {
            tracing::error!("Accept error: {}", e);
        }
    }
}
```

### Production Accept Loop

```rust
use tokio::select;
use tokio::sync::broadcast;

async fn run_accept_loop(
    listener: ReverseConnectionListener,
    pool: AgentPool,
    mut shutdown: broadcast::Receiver<()>,
) {
    loop {
        select! {
            result = listener.accept() => {
                match result {
                    Ok((client, registration)) => {
                        handle_new_connection(&pool, client, registration).await;
                    }
                    Err(e) => {
                        tracing::error!("Accept error: {}", e);
                        tokio::time::sleep(Duration::from_millis(100)).await;
                    }
                }
            }
            _ = shutdown.recv() => {
                tracing::info!("Shutting down accept loop");
                break;
            }
        }
    }
}
```

---

## Agent-Side Implementation

### Connecting to Proxy

```rust
use tokio::net::UnixStream;
use zentinel_agent_protocol::v2::reverse::{
    RegistrationRequest,
    RegistrationResponse,
    write_registration_request,
    read_registration_response,
};

async fn connect_to_proxy(
    socket_path: &str,
    agent_id: &str,
    auth_token: Option<String>,
) -> Result<UnixStream, Box<dyn std::error::Error>> {
    // Connect to proxy listener
    let mut stream = UnixStream::connect(socket_path).await?;

    // Build registration request
    let request = RegistrationRequest {
        protocol_version: 2,
        agent_id: agent_id.to_string(),
        capabilities: UdsCapabilities {
            handles_request_headers: true,
            handles_request_body: true,
            handles_response_headers: true,
            handles_response_body: false,
            supports_streaming: true,
            supports_cancellation: true,
            max_concurrent_requests: Some(100),
        },
        auth_token,
        metadata: Some(serde_json::json!({
            "version": env!("CARGO_PKG_VERSION"),
        })),
    };

    // Send registration
    write_registration_request(&mut stream, &request).await?;

    // Read response
    let response = read_registration_response(&mut stream).await?;

    if !response.accepted {
        return Err(format!(
            "Registration rejected: {}",
            response.error.unwrap_or_default()
        ).into());
    }

    tracing::info!(
        assigned_id = ?response.assigned_id,
        "Registered with proxy"
    );

    Ok(stream)
}
```

### Connection Pool on Agent Side

For high availability, agents should maintain multiple connections:

```rust
struct AgentConnectionManager {
    socket_path: String,
    agent_id: String,
    auth_token: Option<String>,
    target_connections: usize,
}

impl AgentConnectionManager {
    pub async fn run(&self) {
        loop {
            // Maintain target number of connections
            while active_connections() < self.target_connections {
                match self.establish_connection().await {
                    Ok(stream) => {
                        tokio::spawn(async move {
                            handle_connection(stream).await;
                        });
                    }
                    Err(e) => {
                        tracing::error!("Connection failed: {}", e);
                        tokio::time::sleep(Duration::from_secs(5)).await;
                    }
                }
            }
            tokio::time::sleep(Duration::from_secs(1)).await;
        }
    }
}
```

---

## Error Handling

### Registration Errors

| Error | Cause | Resolution |
|-------|-------|------------|
| Version mismatch | Protocol version != 2 | Update agent to v2 |
| Auth failed | Invalid or missing token | Check auth configuration |
| Not allowed | Agent ID not in allowlist | Add to allowed_agents |
| Connection limit | Too many connections | Wait or reduce connections |
| Timeout | Handshake took too long | Check network/agent health |

### Handling Disconnects

```rust
// Agent side: reconnect loop with exponential backoff
let mut backoff = Duration::from_secs(1);

loop {
    match connect_and_handle().await {
        Ok(()) => {
            tracing::info!("Connection closed normally");
            backoff = Duration::from_secs(1); // Reset on success
        }
        Err(e) => {
            tracing::error!("Connection error: {}", e);
        }
    }

    tokio::time::sleep(backoff).await;
    backoff = std::cmp::min(backoff * 2, Duration::from_secs(60));
}
```

---

## Best Practices

### 1. Use Multiple Connections Per Agent

```rust
// Agent side: maintain 4 connections for load distribution
let manager = AgentConnectionManager::new(
    "/var/run/zentinel/agents.sock",
    "waf-worker-1",
    Some("auth-token".to_string()),
    4,  // target connections
);
```

### 2. Include Useful Metadata

```rust
let request = RegistrationRequest {
    // ...
    metadata: Some(serde_json::json!({
        "version": env!("CARGO_PKG_VERSION"),
        "hostname": hostname::get()?.to_string_lossy(),
        "pid": std::process::id(),
        "started_at": chrono::Utc::now().to_rfc3339(),
        "features": ["waf", "rate-limiting"],
    })),
};
```

### 3. Handle Configuration Pushes

```rust
if let Some(config) = response.config {
    // Hot-reload configuration
    if let Some(rules_version) = config.get("rules_version") {
        reload_rules(rules_version.as_str().unwrap())?;
    }
}
```

### 4. Implement Health Monitoring

```rust
// Agent side: track connection health
let mut consecutive_errors = 0;

loop {
    match handle_next_request(&mut stream).await {
        Ok(()) => {
            consecutive_errors = 0;
        }
        Err(e) => {
            consecutive_errors += 1;
            if consecutive_errors > 5 {
                tracing::warn!("Too many errors, reconnecting");
                break;
            }
        }
    }
}
```

---

## KDL Configuration

Configure reverse connection listener in your Zentinel config:

```kdl
reverse-listener {
    path "/var/run/zentinel/agents.sock"
    max-connections-per-agent 4
    handshake-timeout "10s"

    // Optional: TCP listener for remote agents
    // tcp-address "0.0.0.0:9090"

    // Security settings
    require-auth true
    allowed-agents "waf-*" "auth-agent"
}
```

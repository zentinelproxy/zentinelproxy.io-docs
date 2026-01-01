+++
title = "WebSocket"
weight = 8
+++

WebSocket proxying with frame inspection, security controls, and real-time monitoring.

## Use Case

- Proxy WebSocket connections to backend services
- Inspect and filter WebSocket frames
- Rate limit connections and messages
- Detect attacks in WebSocket traffic

## Configuration

Create `sentinel.kdl`:

```kdl
// WebSocket Configuration
// Real-time WebSocket proxying with security

server {
    worker-threads 0
    graceful-shutdown-timeout-secs 60
}

listeners {
    listener "https" {
        address "0.0.0.0:8443"
        protocol "https"
        tls {
            cert-file "/etc/sentinel/certs/ws.crt"
            key-file "/etc/sentinel/certs/ws.key"
        }
    }
    listener "http" {
        address "0.0.0.0:8080"
        protocol "http"
    }
}

routes {
    // Health check
    route "health" {
        priority 1000
        matches { path "/health" }
        service-type "builtin"
        builtin-handler "health"
    }

    // WebSocket endpoint
    route "websocket" {
        priority 200
        matches {
            path "/ws"
        }
        upstream "ws-backend"
        agents ["ws-inspector"]
        websocket {
            enabled true
            ping-interval-secs 30
            ping-timeout-secs 10
            max-message-size "1MB"
        }
    }

    // Socket.io endpoint
    route "socketio" {
        priority 200
        matches {
            path-prefix "/socket.io/"
        }
        upstream "ws-backend"
        agents ["ws-inspector"]
        websocket {
            enabled true
        }
    }

    // REST API (same backend)
    route "api" {
        priority 100
        matches {
            path-prefix "/api/"
        }
        upstream "ws-backend"
        agents ["auth"]
    }
}

upstreams {
    upstream "ws-backend" {
        targets {
            target { address "127.0.0.1:3000" }
        }
        health-check {
            type "http" { path "/health" }
            interval-secs 10
        }
    }
}

agents {
    agent "ws-inspector" {
        transport "unix_socket" {
            path "/var/run/sentinel/ws-inspector.sock"
        }
        events ["websocket_frame"]
        timeout-ms 50
        failure-mode "open"
    }

    agent "auth" {
        transport "unix_socket" {
            path "/var/run/sentinel/auth.sock"
        }
        events ["request_headers"]
        timeout-ms 50
        failure-mode "closed"
    }
}

observability {
    metrics {
        enabled true
        address "0.0.0.0:9090"
    }
    logging {
        level "info"
        format "json"
    }
}
```

## Agent Setup

### Install WebSocket Inspector

```bash
cargo install sentinel-agent-websocket-inspector
```

### Start WebSocket Inspector

```bash
sentinel-agent-websocket-inspector \
    --socket /var/run/sentinel/ws-inspector.sock \
    --xss-detection true \
    --sqli-detection true \
    --max-message-size 1048576 \
    --rate-limit-messages 100 \
    --block-mode true &
```

### Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `--xss-detection` | `true` | Detect XSS in text frames |
| `--sqli-detection` | `true` | Detect SQL injection |
| `--command-injection` | `true` | Detect command injection |
| `--max-message-size` | `1048576` | Max message size (bytes) |
| `--rate-limit-messages` | `0` | Messages per second (0=unlimited) |
| `--block-mode` | `true` | Block or detect-only |
| `--json-schema` | - | Validate JSON against schema |

## Testing

### Basic WebSocket Connection

```bash
# Using websocat
websocat ws://localhost:8080/ws

# Or with wscat
wscat -c ws://localhost:8080/ws
```

### Test with JavaScript

```javascript
const ws = new WebSocket('wss://localhost:8443/ws');

ws.onopen = () => {
    console.log('Connected');
    ws.send(JSON.stringify({ type: 'ping' }));
};

ws.onmessage = (event) => {
    console.log('Received:', event.data);
};

ws.onerror = (error) => {
    console.error('Error:', error);
};
```

### Test XSS Detection

```bash
echo '{"message": "<script>alert(1)</script>"}' | websocat ws://localhost:8080/ws
```

Expected: Connection closed with code 1008 (Policy Violation)

### Test Rate Limiting

```javascript
// Send 200 messages rapidly
for (let i = 0; i < 200; i++) {
    ws.send(JSON.stringify({ i }));
}
// Expect connection closed after rate limit exceeded
```

## Authentication

### Token in Query String

```kdl
routes {
    route "websocket" {
        matches {
            path "/ws"
            query-param name="token"
        }
        agents ["auth" "ws-inspector"]
        upstream "ws-backend"
    }
}
```

Client connection:

```javascript
const ws = new WebSocket('wss://localhost:8443/ws?token=eyJ...');
```

### Token in Subprotocol

```javascript
const ws = new WebSocket('wss://localhost:8443/ws', ['access_token', 'eyJ...']);
```

### Cookie-Based Auth

```kdl
routes {
    route "websocket" {
        matches {
            path "/ws"
            header name="Cookie"
        }
        agents ["auth" "ws-inspector"]
        upstream "ws-backend"
    }
}
```

## Socket.io Support

Sentinel supports Socket.io's WebSocket transport:

```javascript
import { io } from 'socket.io-client';

const socket = io('https://localhost:8443', {
    path: '/socket.io/',
    transports: ['websocket'],
    auth: {
        token: 'your-jwt-token'
    }
});

socket.on('connect', () => {
    console.log('Connected');
});
```

## JSON Schema Validation

Validate WebSocket messages against a JSON Schema:

```bash
sentinel-agent-websocket-inspector \
    --socket /var/run/sentinel/ws-inspector.sock \
    --json-schema /etc/sentinel/ws-schema.json &
```

Create `/etc/sentinel/ws-schema.json`:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["type"],
  "properties": {
    "type": {
      "type": "string",
      "enum": ["message", "ping", "subscribe", "unsubscribe"]
    },
    "channel": {
      "type": "string",
      "pattern": "^[a-zA-Z0-9_-]+$"
    },
    "data": {
      "type": "object"
    }
  }
}
```

## Connection Limits

```kdl
routes {
    route "websocket" {
        upstream "ws-backend"
        websocket {
            enabled true
            max-connections 1000
            max-connections-per-ip 10
            idle-timeout-secs 300
        }
    }
}
```

## Metrics

Key WebSocket metrics:

```promql
# Active connections
sentinel_websocket_connections_active

# Messages per second
rate(sentinel_websocket_messages_total[5m])

# Connection duration
histogram_quantile(0.95, sentinel_websocket_connection_duration_seconds_bucket)

# Blocked frames
rate(sentinel_agent_ws_blocked_total[5m])
```

## Multi-Room Chat Example

Complete configuration for a chat application:

```kdl
routes {
    // WebSocket for real-time messages
    route "chat-ws" {
        priority 200
        matches {
            path "/chat"
        }
        upstream "chat-service"
        agents ["auth" "ws-inspector"]
        websocket {
            enabled true
            ping-interval-secs 30
            max-message-size "64KB"
        }
    }

    // REST API for history, rooms, etc.
    route "chat-api" {
        priority 100
        matches {
            path-prefix "/api/chat/"
        }
        upstream "chat-service"
        agents ["auth" "ratelimit"]
    }
}

agents {
    agent "ws-inspector" {
        transport "unix_socket" {
            path "/var/run/sentinel/ws-inspector.sock"
        }
        events ["websocket_frame"]
        timeout-ms 20
        failure-mode "open"
    }
}
```

## Next Steps

- [Security](../security/) - Add WAF protection
- [Observability](../observability/) - Monitor connections
- [Microservices](../microservices/) - Multi-service WebSocket

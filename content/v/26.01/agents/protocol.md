+++
title = "Protocol Specification"
weight = 5
+++

This document defines the Sentinel Agent Protocol v1—the wire format for communication between Sentinel and external agents.

## Overview

The protocol supports two encodings:

| Transport | Encoding | Schema |
|-----------|----------|--------|
| Unix Socket | JSON | Informal (see below) |
| gRPC | Protocol Buffers | `sentinel.agent.v1` |

Both encodings represent the same logical protocol. Agents can implement either or both.

---

## Protocol Buffers Definition

```protobuf
// Sentinel Agent Protocol - gRPC Definition
// Package: sentinel.agent.v1

syntax = "proto3";
package sentinel.agent.v1;

// ============================================================================
// Event Types
// ============================================================================

enum EventType {
  EVENT_TYPE_UNSPECIFIED = 0;
  EVENT_TYPE_CONFIGURE = 1;           // Agent configuration
  EVENT_TYPE_REQUEST_HEADERS = 2;
  EVENT_TYPE_REQUEST_BODY_CHUNK = 3;
  EVENT_TYPE_RESPONSE_HEADERS = 4;
  EVENT_TYPE_RESPONSE_BODY_CHUNK = 5;
  EVENT_TYPE_REQUEST_COMPLETE = 6;
}

// ============================================================================
// Request Metadata
// ============================================================================

message RequestMetadata {
  string correlation_id = 1;      // Unique ID for request correlation
  string request_id = 2;          // Internal request ID
  string client_ip = 3;           // Client IP address
  uint32 client_port = 4;         // Client port
  optional string server_name = 5;    // SNI or Host header
  string protocol = 6;            // "HTTP/1.1", "HTTP/2", etc.
  optional string tls_version = 7;    // "TLSv1.3", etc.
  optional string tls_cipher = 8;     // Cipher suite
  optional string route_id = 9;       // Matched route ID
  optional string upstream_id = 10;   // Target upstream
  string timestamp = 11;          // RFC3339 timestamp
}

// ============================================================================
// Event Messages
// ============================================================================

// Sent once when agent connects, before any request events
message ConfigureEvent {
  string agent_id = 1;            // Agent identifier from config
  string config_json = 2;         // Configuration as JSON string
}

// Header values (supports multiple values per header name)
message HeaderValues {
  repeated string values = 1;
}

// Sent when HTTP request headers are received
message RequestHeadersEvent {
  RequestMetadata metadata = 1;
  string method = 2;              // GET, POST, etc.
  string uri = 3;                 // /path?query
  map<string, HeaderValues> headers = 4;
}

// Sent for each request body chunk
message RequestBodyChunkEvent {
  string correlation_id = 1;
  bytes data = 2;                 // Raw bytes
  bool is_last = 3;               // True if final chunk
  optional uint64 total_size = 4; // Total body size if known
}

// Sent when upstream response headers are received
message ResponseHeadersEvent {
  string correlation_id = 1;
  uint32 status = 2;              // HTTP status code
  map<string, HeaderValues> headers = 3;
}

// Sent for each response body chunk
message ResponseBodyChunkEvent {
  string correlation_id = 1;
  bytes data = 2;                 // Raw bytes
  bool is_last = 3;
  optional uint64 total_size = 4;
}

// Sent after response completes (for logging)
message RequestCompleteEvent {
  string correlation_id = 1;
  uint32 status = 2;              // Final HTTP status
  uint64 duration_ms = 3;         // Total request duration
  uint64 request_body_size = 4;   // Bytes received
  uint64 response_body_size = 5;  // Bytes sent
  uint32 upstream_attempts = 6;   // Retry count
  optional string error = 7;      // Error message if failed
}

// ============================================================================
// Header Operations
// ============================================================================

message HeaderOp {
  oneof operation {
    SetHeader set = 1;
    AddHeader add = 2;
    RemoveHeader remove = 3;
  }
}

message SetHeader {
  string name = 1;
  string value = 2;
}

message AddHeader {
  string name = 1;
  string value = 2;
}

message RemoveHeader {
  string name = 1;
}

// ============================================================================
// Audit Metadata
// ============================================================================

message AuditMetadata {
  repeated string tags = 1;           // Searchable tags
  repeated string rule_ids = 2;       // Matched rule IDs
  optional float confidence = 3;      // Confidence score (0.0-1.0)
  repeated string reason_codes = 4;   // Machine-readable codes
  map<string, string> custom = 5;     // Arbitrary key-value data
}

// ============================================================================
// Decision Types
// ============================================================================

message AllowDecision {
  // Empty - request proceeds
}

message BlockDecision {
  uint32 status = 1;              // HTTP status code (e.g., 403)
  optional string body = 2;       // Response body
  map<string, string> headers = 3; // Response headers
}

message RedirectDecision {
  string url = 1;                 // Target URL
  uint32 status = 2;              // 301, 302, 307, or 308
}

message ChallengeDecision {
  string challenge_type = 1;      // "captcha", "javascript", etc.
  map<string, string> params = 2; // Challenge parameters
}

// ============================================================================
// Request/Response Wrappers
// ============================================================================

message AgentRequest {
  uint32 version = 1;             // Protocol version (1)
  EventType event_type = 2;

  oneof event {
    ConfigureEvent configure = 9;
    RequestHeadersEvent request_headers = 10;
    RequestBodyChunkEvent request_body_chunk = 11;
    ResponseHeadersEvent response_headers = 12;
    ResponseBodyChunkEvent response_body_chunk = 13;
    RequestCompleteEvent request_complete = 14;
  }
}

message AgentResponse {
  uint32 version = 1;             // Protocol version (1)

  oneof decision {
    AllowDecision allow = 2;
    BlockDecision block = 3;
    RedirectDecision redirect = 4;
    ChallengeDecision challenge = 5;
  }

  repeated HeaderOp request_headers = 10;   // Request header mutations
  repeated HeaderOp response_headers = 11;  // Response header mutations
  map<string, string> routing_metadata = 12; // Routing hints
  optional AuditMetadata audit = 13;        // Logging metadata
}

// ============================================================================
// Service Definition
// ============================================================================

service AgentProcessor {
  // Process a single event
  rpc ProcessEvent(AgentRequest) returns (AgentResponse);

  // Bidirectional streaming for body inspection
  rpc ProcessEventStream(stream AgentRequest) returns (AgentResponse);
}
```

---

## JSON Schema (Unix Socket)

For Unix socket transport, messages use JSON with the following schema:

### AgentRequest

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["version", "event_type", "payload"],
  "properties": {
    "version": {
      "type": "integer",
      "const": 1
    },
    "event_type": {
      "type": "string",
      "enum": [
        "configure",
        "request_headers",
        "request_body_chunk",
        "response_headers",
        "response_body_chunk",
        "request_complete"
      ]
    },
    "payload": {
      "type": "object",
      "description": "Event-specific payload"
    }
  }
}
```

### Event Payloads

**ConfigureEvent:**

```json
{
  "agent_id": "waf-agent",
  "config": {
    "paranoia-level": 2,
    "sqli": true,
    "xss": true,
    "exclude-paths": ["/health", "/metrics"]
  }
}
```

**RequestHeadersEvent:**

```json
{
  "metadata": {
    "correlation_id": "string",
    "request_id": "string",
    "client_ip": "string",
    "client_port": 12345,
    "server_name": "string|null",
    "protocol": "HTTP/1.1|HTTP/2",
    "tls_version": "string|null",
    "tls_cipher": "string|null",
    "route_id": "string|null",
    "upstream_id": "string|null",
    "timestamp": "2025-12-29T08:00:00Z"
  },
  "method": "GET|POST|...",
  "uri": "/path?query",
  "headers": {
    "header-name": ["value1", "value2"]
  }
}
```

**RequestBodyChunkEvent:**

```json
{
  "correlation_id": "string",
  "data": "base64-encoded-data",
  "is_last": true,
  "total_size": 1234
}
```

**ResponseHeadersEvent:**

```json
{
  "correlation_id": "string",
  "status": 200,
  "headers": {
    "content-type": ["application/json"]
  }
}
```

**ResponseBodyChunkEvent:**

```json
{
  "correlation_id": "string",
  "data": "base64-encoded-data",
  "is_last": true,
  "total_size": 5678
}
```

**RequestCompleteEvent:**

```json
{
  "correlation_id": "string",
  "status": 200,
  "duration_ms": 150,
  "request_body_size": 1024,
  "response_body_size": 2048,
  "upstream_attempts": 1,
  "error": null
}
```

### AgentResponse

```json
{
  "version": 1,
  "decision": {
    "allow": {}
  },
  "request_headers": [
    {"set": {"name": "X-Header", "value": "value"}},
    {"add": {"name": "X-Tag", "value": "processed"}},
    {"remove": {"name": "X-Internal"}}
  ],
  "response_headers": [],
  "routing_metadata": {},
  "audit": {
    "tags": ["auth", "success"],
    "rule_ids": [],
    "confidence": 0.95,
    "reason_codes": ["AUTH_SUCCESS"],
    "custom": {
      "user_id": "user-123"
    }
  }
}
```

### Decision Types (JSON)

**Allow:**
```json
{"decision": {"allow": {}}}
```

**Block:**
```json
{
  "decision": {
    "block": {
      "status": 403,
      "body": "Access Denied",
      "headers": {"X-Block-Reason": "rate-limit"}
    }
  }
}
```

**Redirect:**
```json
{
  "decision": {
    "redirect": {
      "url": "https://login.example.com/auth",
      "status": 302
    }
  }
}
```

**Challenge:**
```json
{
  "decision": {
    "challenge": {
      "challenge_type": "captcha",
      "params": {
        "site_key": "abc123",
        "action": "login"
      }
    }
  }
}
```

---

## Protocol Version

Current version: **1**

The `version` field in requests and responses allows for future protocol evolution:

```json
{"version": 1, ...}
```

Agents should reject requests with unsupported versions.

---

## Header Operations

Three operations are supported for header mutation:

| Operation | Description | Example |
|-----------|-------------|---------|
| `set` | Set value (replaces existing) | `{"set": {"name": "X-User", "value": "alice"}}` |
| `add` | Add value (appends) | `{"add": {"name": "X-Tag", "value": "processed"}}` |
| `remove` | Remove header entirely | `{"remove": {"name": "X-Internal"}}` |

### Mutation Ordering

1. All `remove` operations execute first
2. Then all `set` operations
3. Finally all `add` operations

This ensures predictable behavior regardless of the order in the array.

---

## Error Handling

### Protocol Errors

| Error | Response |
|-------|----------|
| Malformed JSON | Connection closed |
| Unknown event_type | 400 Bad Request (gRPC: INVALID_ARGUMENT) |
| Missing required field | 400 Bad Request (gRPC: INVALID_ARGUMENT) |
| Message too large | Connection closed |
| Version mismatch | 400 Bad Request (gRPC: INVALID_ARGUMENT) |

### Timeout Behavior

When an agent times out, Sentinel applies the configured `failure-mode`:

- `failure-mode "open"` → Allow request
- `failure-mode "closed"` → Block request (503)

---

## Correlation ID

The `correlation_id` field links all events for a single HTTP request:

```
request_headers  ─┐
request_body[0]  ─┤
request_body[1]  ─┼── Same correlation_id
response_headers ─┤
request_complete ─┘
```

Use this ID for:
- Log correlation across events
- Stateful body inspection (accumulating chunks)
- Request tracing

---

## Body Inspection

Body chunks are sent incrementally with `is_last` indicating the final chunk:

```
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│  chunk 1     │ → │  chunk 2     │ → │  chunk 3     │
│  is_last: F  │   │  is_last: F  │   │  is_last: T  │
└──────────────┘   └──────────────┘   └──────────────┘
```

For streaming inspection, use `ProcessEventStream`:

1. Headers event sent first
2. Body chunks streamed
3. Single response returned after all chunks processed

---

## Limits

| Limit | Value | Notes |
|-------|-------|-------|
| Max message size | 16 MB | Per individual message |
| Max header name | 8 KB | |
| Max header value | 64 KB | Per value |
| Max headers per request | 100 | |
| Max body chunk size | 1 MB | Recommended |

---

## Versioning Strategy

Future protocol changes will follow semantic versioning:

- **Patch** (1.0.x): Bug fixes, no schema changes
- **Minor** (1.x.0): Additive changes (new optional fields)
- **Major** (x.0.0): Breaking changes (new required fields, removed fields)

Agents should:
1. Accept unknown fields gracefully
2. Reject requests with major version mismatch
3. Handle missing optional fields with defaults

---

## Generating Code

### Rust (tonic)

```bash
# Build script (build.rs)
tonic_build::compile_protos("proto/agent.proto")?;
```

### Go

```bash
protoc --go_out=. --go-grpc_out=. agent.proto
```

### Python

```bash
python -m grpc_tools.protoc \
  -I. \
  --python_out=. \
  --grpc_python_out=. \
  agent.proto
```

### TypeScript (Node.js)

```bash
npm install @grpc/grpc-js @grpc/proto-loader
```

```typescript
import * as grpc from '@grpc/grpc-js';
import * as protoLoader from '@grpc/proto-loader';

const packageDefinition = protoLoader.loadSync('agent.proto');
const proto = grpc.loadPackageDefinition(packageDefinition);
```

---

## Reference

- **Proto file:** [`crates/agent-protocol/proto/agent.proto`](https://github.com/raskell-io/sentinel/tree/main/crates/agent-protocol/proto/agent.proto)
- **Rust SDK:** [`sentinel-agent-protocol`](https://crates.io/crates/sentinel-agent-protocol)
- **Example agents:** [`agents/`](https://github.com/raskell-io/sentinel/tree/main/agents)

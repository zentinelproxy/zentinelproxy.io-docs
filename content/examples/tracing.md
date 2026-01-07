+++
title = "Distributed Tracing"
weight = 8
+++

Complete distributed tracing setup with Jaeger or Grafana Tempo for end-to-end request visibility.

## Use Case

- Trace requests through Sentinel to upstream services
- Debug latency issues across service boundaries
- Correlate logs with traces for faster troubleshooting
- Monitor agent processing time in traces

## Prerequisites

Build Sentinel with the OpenTelemetry feature:

```bash
cargo build --release --features opentelemetry
```

Or if using Docker, ensure your image is built with the feature enabled.

## Quick Start with Jaeger

### 1. Start Jaeger

```bash
docker run -d --name jaeger \
  -p 4317:4317 \
  -p 16686:16686 \
  jaegertracing/all-in-one:latest
```

### 2. Configure Sentinel

Create `sentinel.kdl`:

```kdl
// Distributed Tracing Configuration
// Traces all requests to Jaeger

system {
    worker-threads 0
    trace-id-format "tinyflake"
}

listeners {
    listener "http" {
        address "0.0.0.0:8080"
        protocol "http"
    }
}

routes {
    route "api" {
        priority 100
        matches {
            path-prefix "/api/"
        }
        upstream "api-backend"
    }

    route "health" {
        priority 1000
        matches { path "/health" }
        service-type "builtin"
        builtin-handler "health"
    }
}

upstreams {
    upstream "api-backend" {
        targets {
            target { address "127.0.0.1:3000" }
        }
    }
}

observability {
    tracing {
        backend "otlp" {
            endpoint "http://localhost:4317"
        }
        sampling-rate 1.0    // 100% for testing
        service-name "sentinel"
    }

    logging {
        level "info"
        format "json"
        access-log {
            enabled #true
            include-trace-id #true
        }
    }

    metrics {
        enabled #true
        address "0.0.0.0:9090"
    }
}
```

### 3. Start Sentinel

```bash
./target/release/sentinel --config sentinel.kdl
```

### 4. Generate Traffic

```bash
# Make some requests
curl http://localhost:8080/api/users
curl http://localhost:8080/api/products
curl -X POST http://localhost:8080/api/orders -d '{"item": "widget"}'
```

### 5. View Traces

Open Jaeger UI: http://localhost:16686

1. Select "sentinel" from the Service dropdown
2. Click "Find Traces"
3. Click on a trace to see the full request timeline

## Production Setup with Grafana Tempo

For production, use Grafana Tempo with Grafana for visualization:

### docker-compose.yml

```yaml
version: '3.8'

services:
  sentinel:
    image: ghcr.io/raskell-io/sentinel:latest-otel
    ports:
      - "8080:8080"
      - "9090:9090"
    volumes:
      - ./sentinel.kdl:/etc/sentinel/sentinel.kdl
    command: ["--config", "/etc/sentinel/sentinel.kdl"]
    depends_on:
      - tempo

  tempo:
    image: grafana/tempo:2.3.0
    command: ["-config.file=/etc/tempo.yaml"]
    volumes:
      - ./tempo.yaml:/etc/tempo.yaml
      - tempo-data:/var/tempo
    ports:
      - "4317:4317"   # OTLP gRPC
      - "3200:3200"   # Tempo API

  grafana:
    image: grafana/grafana:10.2.0
    ports:
      - "3000:3000"
    volumes:
      - ./grafana-datasources.yaml:/etc/grafana/provisioning/datasources/datasources.yaml
    environment:
      - GF_AUTH_ANONYMOUS_ENABLED=true
      - GF_AUTH_ANONYMOUS_ORG_ROLE=Admin
    depends_on:
      - tempo

  # Example backend service (traces its own spans)
  api-backend:
    image: your-api:latest
    ports:
      - "3001:3000"
    environment:
      - OTEL_EXPORTER_OTLP_ENDPOINT=http://tempo:4317
      - OTEL_SERVICE_NAME=api-backend

volumes:
  tempo-data:
```

### tempo.yaml

```yaml
server:
  http_listen_port: 3200

distributor:
  receivers:
    otlp:
      protocols:
        grpc:
          endpoint: 0.0.0.0:4317

ingester:
  trace_idle_period: 10s
  max_block_bytes: 1_000_000
  max_block_duration: 5m

compactor:
  compaction:
    block_retention: 48h

storage:
  trace:
    backend: local
    local:
      path: /var/tempo/traces
    wal:
      path: /var/tempo/wal
```

### grafana-datasources.yaml

```yaml
apiVersion: 1

datasources:
  - name: Tempo
    type: tempo
    access: proxy
    url: http://tempo:3200
    isDefault: true
```

### sentinel.kdl (for Tempo)

```kdl
system {
    worker-threads 0
    trace-id-format "tinyflake"
}

listeners {
    listener "http" {
        address "0.0.0.0:8080"
        protocol "http"
    }
}

routes {
    route "api" {
        priority 100
        matches {
            path-prefix "/api/"
        }
        upstream "api-backend"
        agents ["auth" "ratelimit"]
    }

    route "health" {
        priority 1000
        matches { path "/health" }
        service-type "builtin"
        builtin-handler "health"
    }
}

upstreams {
    upstream "api-backend" {
        targets {
            target { address "api-backend:3000" }
        }
        health-check {
            type "http" { path "/health" }
            interval-secs 10
        }
    }
}

agents {
    agent "auth" {
        transport "unix_socket" {
            path "/var/run/sentinel/auth.sock"
        }
        events ["request_headers"]
        timeout-ms 50
    }

    agent "ratelimit" {
        transport "unix_socket" {
            path "/var/run/sentinel/ratelimit.sock"
        }
        events ["request_headers"]
        timeout-ms 20
    }
}

observability {
    tracing {
        backend "otlp" {
            endpoint "http://tempo:4317"
        }
        sampling-rate 0.1    // 10% in production
        service-name "sentinel"
    }

    logging {
        level "info"
        format "json"
        access-log {
            enabled #true
            include-trace-id #true
        }
    }

    metrics {
        enabled #true
        address "0.0.0.0:9090"
    }
}
```

## Tracing with Agents

Agents receive the `traceparent` header in request metadata, enabling them to create child spans:

### Agent Trace Context

When an agent receives a request event, the metadata includes:

```json
{
  "metadata": {
    "correlation_id": "2Kj8mNpQ3xR",
    "traceparent": "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01",
    "client_ip": "192.168.1.100",
    "route_id": "api",
    ...
  }
}
```

### Creating Agent Child Spans (Rust Example)

```rust
use opentelemetry::{global, trace::{TraceContextExt, Tracer}};
use opentelemetry::propagation::TextMapPropagator;

fn process_request(metadata: &RequestMetadata) -> AgentResponse {
    // Extract trace context from traceparent
    let mut headers = HashMap::new();
    if let Some(tp) = &metadata.traceparent {
        headers.insert("traceparent".to_string(), tp.clone());
    }

    // Create child span
    let propagator = opentelemetry_sdk::propagation::TraceContextPropagator::new();
    let parent_cx = propagator.extract(&headers);

    let tracer = global::tracer("my-agent");
    let span = tracer
        .span_builder("agent.process")
        .with_parent_context(parent_cx)
        .start(&tracer);

    // Do processing...

    span.end();
    AgentResponse::default_allow()
}
```

## Sampling Strategies

### Development

Trace everything for debugging:

```kdl
tracing {
    backend "otlp" { endpoint "http://jaeger:4317" }
    sampling-rate 1.0
    service-name "sentinel-dev"
}
```

### Production

Balance visibility with overhead:

```kdl
tracing {
    backend "otlp" { endpoint "http://tempo:4317" }
    sampling-rate 0.05   // 5% of requests
    service-name "sentinel-prod"
}
```

### Error-Focused

For high-volume services, consider tail-based sampling in your collector to capture all errors while sampling normal requests.

## Correlating Logs and Traces

### Access Log with Trace ID

```kdl
observability {
    logging {
        access-log {
            enabled #true
            format "json"
            include-trace-id #true
        }
    }
}
```

### Log Output

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "trace_id": "0af7651916cd43dd8448eb211c80319c",
  "method": "POST",
  "path": "/api/orders",
  "status": 201,
  "duration_ms": 145
}
```

### Grafana Log-to-Trace Link

In Grafana, configure Loki to link to Tempo traces:

```yaml
datasources:
  - name: Loki
    type: loki
    url: http://loki:3100
    jsonData:
      derivedFields:
        - datasourceUid: tempo
          matcherRegex: '"trace_id":"([a-f0-9]+)"'
          name: TraceID
          url: '$${__value.raw}'
```

## Metrics

Monitor tracing health:

```promql
# Spans exported per second
rate(otel_exporter_spans_exported_total[5m])

# Export errors
rate(otel_exporter_spans_failed_total[5m])
```

## Next Steps

- [Prometheus Example](../prometheus/) - Metrics setup
- [Grafana Example](../grafana/) - Dashboard creation
- [Observability Config](../../configuration/observability/) - Full configuration reference

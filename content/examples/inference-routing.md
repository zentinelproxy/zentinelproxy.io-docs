+++
title = "Inference Routing"
weight = 18
updated = 2026-10-18
+++

Configure Zentinel for LLM/AI inference endpoints with token-based rate limiting, model routing, cost tracking, and intelligent load balancing. This example demonstrates how to build a production-ready AI gateway.

## Use Case

- Route requests to multiple LLM providers (OpenAI, Anthropic, local models)
- Token-based rate limiting (tokens per minute instead of requests)
- Cost attribution and budget tracking
- Model-based routing to appropriate backends
- Automatic fallback on provider failures
- GPU-aware load balancing for self-hosted models

## Architecture

```
                    ┌─────────────────┐
                    │    Clients      │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │    Zentinel     │
                    │  AI Gateway     │
                    │                 │
                    │ - Token counting│
                    │ - Rate limiting │
                    │ - Cost tracking │
                    └────────┬────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
         ▼                   ▼                   ▼
    ┌─────────┐        ┌─────────┐        ┌─────────┐
    │ OpenAI  │        │Anthropic│        │Local LLM│
    │   API   │        │   API   │        │ (vLLM)  │
    └─────────┘        └─────────┘        └─────────┘
```

## Configuration

Create `zentinel.kdl`:

```kdl
// Inference Routing Configuration
// AI Gateway with token-based rate limiting

system {
    worker-threads 4
    max-connections 5000
    graceful-shutdown-timeout-secs 30
}

listeners {
    listener "http" {
        address "0.0.0.0:8080"
        protocol "http"
        request-timeout-secs 300  // Long timeout for inference
    }
}

// =============================================================================
// Upstreams for different inference providers
// =============================================================================
upstreams {
    // OpenAI-compatible endpoint
    upstream "openai" {
        target "api.openai.com:443" weight=1

        load-balancing "round_robin"

        tls {
            sni "api.openai.com"
        }

        health-check {
            type "tcp"
            interval-secs 30
            timeout-secs 5
            healthy-threshold 1
            unhealthy-threshold 3
        }

        timeouts {
            connect-secs 10
            request-secs 300
            read-secs 300
        }
    }

    // Anthropic endpoint
    upstream "anthropic" {
        target "api.anthropic.com:443" weight=1

        load-balancing "round_robin"

        tls {
            sni "api.anthropic.com"
        }

        timeouts {
            connect-secs 10
            request-secs 300
            read-secs 300
        }
    }

    // Self-hosted vLLM or similar
    upstream "local-llm" {
        target "10.0.1.10:8000" weight=3
        target "10.0.1.11:8000" weight=3
        target "10.0.1.12:8000" weight=2

        // Use least-tokens-queued for optimal GPU utilization
        load-balancing "least_tokens_queued"

        health-check {
            type "http" {
                path "/health"
                expected-status 200
            }
            interval-secs 10
            timeout-secs 5
            healthy-threshold 2
            unhealthy-threshold 3
        }

        connection-pool {
            max-connections 50
            max-idle 10
            idle-timeout-secs 60
        }

        circuit-breaker {
            failure-threshold 5
            success-threshold 2
            timeout-seconds 60
            half-open-max-requests 3
        }
    }

    // Fallback provider (cheaper, lower quality)
    upstream "fallback-llm" {
        target "inference-fallback.internal:8080" weight=1

        load-balancing "round_robin"
    }
}

// =============================================================================
// Routes with inference configuration
// =============================================================================
routes {
    // OpenAI API proxy with token rate limiting
    route "openai-chat" {
        priority "high"

        matches {
            path-prefix "/v1/chat/completions"
            method "POST"
        }

        upstream "openai"
        service-type "inference"

        inference {
            // Provider determines token extraction strategy
            provider "openai"

            // Token-based rate limiting (per-minute)
            rate-limit {
                tokens-per-minute 100000
                burst-tokens 20000
            }

            // Token budget for cumulative tracking
            budget {
                limit 10000000  // 10M tokens per period
                period "monthly"
            }

            // Cost attribution for billing (prices per million tokens)
            cost-attribution {
                enabled #true
                currency "USD"
                pricing {
                    model "gpt-4" {
                        input-cost-per-million 30.0
                        output-cost-per-million 60.0
                    }
                    model "gpt-4-turbo" {
                        input-cost-per-million 10.0
                        output-cost-per-million 30.0
                    }
                    model "gpt-3.5-turbo" {
                        input-cost-per-million 0.5
                        output-cost-per-million 1.5
                    }
                }
            }

            // Inference-aware routing
            routing {
                strategy "least-tokens-queued"
            }
        }

        policies {
            timeout-secs 300
            max-body-size "1MB"
            failure-mode "closed"
        }
    }

    // Anthropic API proxy
    route "anthropic-messages" {
        priority "high"

        matches {
            path-prefix "/v1/messages"
            method "POST"
        }

        upstream "anthropic"
        service-type "inference"

        inference {
            provider "anthropic"

            rate-limit {
                tokens-per-minute 50000
                burst-tokens 10000
            }

            // Model routing: model name pattern -> upstream
            model-routing {
                model "claude-3-opus*" upstream="anthropic"
                model "claude-3-sonnet*" upstream="anthropic"
                // Unknown models go to the local cluster
                default-upstream "local-llm"
            }
        }

        policies {
            timeout-secs 300
            max-body-size "1MB"
            failure-mode "closed"
        }
    }

    // Local LLM with model-based routing
    route "local-inference" {
        priority "normal"

        matches {
            path-prefix "/inference"
            method "POST"
        }

        upstream "local-llm"
        service-type "inference"

        inference {
            provider "generic"

            // Header that carries the model name
            model-header "X-Model-Name"

            rate-limit {
                tokens-per-minute 500000
                burst-tokens 100000
                // Token estimation when the provider doesn't report tokens
                estimation-method "chars"  // chars, words, or tiktoken
            }

            routing {
                strategy "least-latency"
            }

            // Model routing for multi-model deployments
            model-routing {
                model "llama-70b*" upstream="local-llm"
                model "llama-7b*" upstream="local-llm"
                model "mistral*" upstream="local-llm"
            }
        }

        // Automatic fallback on errors
        fallback {
            triggers {
                on-health-failure #true
                on-budget-exhausted #true
                on-latency-threshold-ms 5000
                on-error-codes 502 503 504 429
            }

            fallback-upstream "fallback-llm" {
                // Model mapping for the fallback provider
                model-mapping {
                    "llama-70b" "llama-7b"  // Fall back to smaller model
                }
            }
        }

        policies {
            timeout-secs 120
            max-body-size "10MB"
            failure-mode "open"
        }

        retry-policy {
            max-attempts 2
        }
    }

    // Health check
    route "health" {
        priority "critical"

        matches {
            path "/health"
        }

        builtin-handler "health"
    }
}

// =============================================================================
// Observability for inference metrics
// =============================================================================
observability {
    metrics {
        enabled #true
        address "0.0.0.0:9090"
        path "/metrics"
        // Inference-specific metrics:
        // - zentinel_inference_tokens_total (by model, type)
        // - zentinel_inference_latency_seconds
        // - zentinel_inference_queue_depth
        // - zentinel_inference_cost_dollars
        // - zentinel_inference_budget_remaining
    }

    logging {
        level "info"
        format "json"

        access-log {
            enabled #true
            file "/var/log/zentinel/inference-access.log"
            include-trace-id #true
            // Token counts included in access logs
        }
    }
}

limits {
    max-header-size-bytes 8192
    max-header-count 100
    max-body-size-bytes 10485760  // 10MB for large prompts
}
```

## Key Features

### Token-Based Rate Limiting

Instead of request-based limits, inference routes can use token-based limits:

```fragment,kdl
// inside a route's inference { } block
rate-limit {
    tokens-per-minute 100000  // Total tokens (input + output)
    burst-tokens 20000        // Allow burst above limit
}
```

### Budget Tracking

Track cumulative token usage per organization or user:

```fragment,kdl
// inside a route's inference { } block
budget {
    limit 10000000       // 10M tokens
    period "monthly"     // hourly, daily, monthly, or seconds
    alert-thresholds 0.8 0.9 0.95
}
```

### Cost Attribution

Track costs per model for billing:

```fragment,kdl
// inside a route's inference { } block
cost-attribution {
    enabled #true
    pricing {
        model "gpt-4" {
            input-cost-per-million 30.0
            output-cost-per-million 60.0
        }
    }
}
```

### Model Routing

Route requests to different backends based on model name:

```fragment,kdl
// inside a route's inference { } block
model-routing {
    model "gpt-4*" upstream="openai"
    model "claude*" upstream="anthropic" provider="anthropic"
    default-upstream "local-llm"
}
```

## Setup

### 1. Start Zentinel

```bash
zentinel -c zentinel.kdl
```

### 2. Set Up API Keys

Create an environment file with provider API keys:

```bash
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
```

### 3. Configure Header Injection (Optional)

Use an agent to inject provider API keys:

```kdl
agents {
    agent "api-key-inject" {
        type "header-inject"
        unix-socket path="/var/run/zentinel/api-key.sock"
        events "request_headers"
    }
}
```

## Testing

### OpenAI Proxy

```bash
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "X-API-Key: user-key-123" \
  -H "X-Org-Id: org-456" \
  -d '{
    "model": "gpt-4",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

### Check Token Usage

```bash
curl http://localhost:9090/metrics | grep inference_tokens
```

Output:
```
zentinel_inference_tokens_total{model="gpt-4",type="input"} 15
zentinel_inference_tokens_total{model="gpt-4",type="output"} 42
```

### Check Budget

```bash
curl http://localhost:9090/metrics | grep budget
```

Output:
```
zentinel_inference_budget_remaining{org="org-456"} 9999943
```

### Local Inference

```bash
curl -X POST http://localhost:8080/inference \
  -H "Content-Type: application/json" \
  -H "X-Model-Name: llama-7b" \
  -d '{
    "prompt": "Explain quantum computing in simple terms."
  }'
```

## Customizations

### Streaming and Priority

Streaming-specific token counting and per-request priority queuing are not
configurable in the `inference` block. Route priority (`priority "high"`)
only affects route matching order.

### GPU-Aware Load Balancing

```kdl
upstream "gpu-cluster" {
    target "gpu-1:8000" weight=8   // 8x A100
    target "gpu-2:8000" weight=4   // 4x A100
    target "gpu-3:8000" weight=2   // 2x A100

    load-balancing "least_tokens_queued"

    health-check {
        type "http" {
            path "/health"
        }
    }
}
```

## Next Steps

- [Distributed Rate Limiting](../distributed-rate-limit/) - Advanced rate limiting
- [API Gateway](../api-gateway/) - Complete API management
- [Tracing](../tracing/) - Distributed tracing for debugging

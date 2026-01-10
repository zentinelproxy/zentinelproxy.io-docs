+++
title = "Inference Routing"
weight = 18
+++

Configure Sentinel for LLM/AI inference endpoints with token-based rate limiting, model routing, cost tracking, and intelligent load balancing. This example demonstrates how to build a production-ready AI gateway.

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
                    │    Sentinel     │
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

Create `sentinel.kdl`:

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

        load-balancing "round-robin"

        tls {
            sni "api.openai.com"
            verify #true
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

        load-balancing "round-robin"

        tls {
            sni "api.anthropic.com"
            verify #true
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
        load-balancing "least-tokens-queued"

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
    }

    // Fallback provider (cheaper, lower quality)
    upstream "fallback-llm" {
        target "inference-fallback.internal:8080" weight=1

        load-balancing "round-robin"
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
                key "header:X-API-Key"  // Rate limit per API key
            }

            // Token budget for cumulative tracking
            budget {
                limit 10000000  // 10M tokens per period
                period "monthly"
                key "header:X-Org-Id"  // Budget per organization
            }

            // Cost attribution for billing
            cost-attribution {
                enabled #true
                models {
                    model "gpt-4" {
                        input-cost-per-1k 0.03
                        output-cost-per-1k 0.06
                    }
                    model "gpt-4-turbo" {
                        input-cost-per-1k 0.01
                        output-cost-per-1k 0.03
                    }
                    model "gpt-3.5-turbo" {
                        input-cost-per-1k 0.0005
                        output-cost-per-1k 0.0015
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
            buffer-requests #true  // Required for token counting
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
                key "header:X-API-Key"
            }

            // Model routing with fallback
            model-routing {
                mappings {
                    mapping "claude-3-opus*" {
                        upstream "anthropic"
                    }
                    mapping "claude-3-sonnet*" {
                        upstream "anthropic"
                    }
                    // Fallback unknown models to local
                    mapping "*" {
                        upstream "local-llm"
                    }
                }
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

            // Token estimation when provider doesn't report tokens
            token-estimation "chars"  // chars, words, or tiktoken

            rate-limit {
                tokens-per-minute 500000
                burst-tokens 100000
                key "client-ip"
            }

            routing {
                strategy "least-latency"
            }

            // Model routing for multi-model deployments
            model-routing {
                model-header "X-Model-Name"
                mappings {
                    mapping "llama-70b*" {
                        upstream "local-llm"
                        weight 1
                    }
                    mapping "llama-7b*" {
                        upstream "local-llm"
                        weight 3  // Prefer smaller model
                    }
                    mapping "mistral*" {
                        upstream "local-llm"
                    }
                }
            }
        }

        // Automatic fallback on errors
        fallback {
            upstream "fallback-llm"

            triggers {
                on-health-failure #true
                on-budget-exhausted #true
                on-latency-threshold-ms 5000
                on-error-codes 502 503 504 429
            }

            // Model mapping for cross-provider fallback
            model-mapping {
                "llama-70b" "llama-7b"  // Fall back to smaller model
                "claude-3-opus" "gpt-4"
            }
        }

        policies {
            timeout-secs 120
            max-body-size "10MB"
            failure-mode "open"
        }

        circuit-breaker {
            failure-threshold 5
            success-threshold 2
            timeout-seconds 60
            half-open-max-requests 3
        }

        retry-policy {
            max-attempts 2
            timeout-ms 10000
            backoff-base-ms 500
            retryable-status-codes 502 503 504
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
        // - sentinel_inference_tokens_total (by model, type)
        // - sentinel_inference_latency_seconds
        // - sentinel_inference_queue_depth
        // - sentinel_inference_cost_dollars
        // - sentinel_inference_budget_remaining
    }

    logging {
        level "info"
        format "json"

        access-log {
            enabled #true
            file "/var/log/sentinel/inference-access.log"
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

```kdl
rate-limit {
    tokens-per-minute 100000  // Total tokens (input + output)
    burst-tokens 20000        // Allow burst above limit
    key "header:X-API-Key"    // Rate limit per API key
}
```

### Budget Tracking

Track cumulative token usage per organization or user:

```kdl
budget {
    limit 10000000       // 10M tokens
    period "monthly"     // Reset period
    key "header:X-Org-Id"
}
```

### Cost Attribution

Track costs per model for billing:

```kdl
cost-attribution {
    enabled #true
    models {
        model "gpt-4" {
            input-cost-per-1k 0.03
            output-cost-per-1k 0.06
        }
    }
}
```

### Model Routing

Route requests to different backends based on model name:

```kdl
model-routing {
    mappings {
        mapping "gpt-4*" { upstream "openai" }
        mapping "claude*" { upstream "anthropic" }
        mapping "*" { upstream "local-llm" }
    }
}
```

## Setup

### 1. Start Sentinel

```bash
sentinel -c sentinel.kdl
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
        unix-socket path="/var/run/sentinel/api-key.sock"
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
sentinel_inference_tokens_total{model="gpt-4",type="input"} 15
sentinel_inference_tokens_total{model="gpt-4",type="output"} 42
```

### Check Budget

```bash
curl http://localhost:9090/metrics | grep budget
```

Output:
```
sentinel_inference_budget_remaining{org="org-456"} 9999943
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

### Streaming Support

```kdl
route "streaming-inference" {
    inference {
        streaming {
            enabled #true
            // Count tokens from streamed chunks
            token-counting "stream"
        }
    }
}
```

### Priority Queuing

```kdl
route "premium-inference" {
    inference {
        priority "high"  // Process before normal priority
        queue-timeout-ms 30000
    }
}
```

### GPU-Aware Load Balancing

```kdl
upstream "gpu-cluster" {
    target "gpu-1:8000" weight=8   // 8x A100
    target "gpu-2:8000" weight=4   // 4x A100
    target "gpu-3:8000" weight=2   // 2x A100

    load-balancing "least-tokens-queued"

    health-check {
        type "http" {
            path "/health"
            // Check GPU memory availability
        }
    }
}
```

## Next Steps

- [Distributed Rate Limiting](../distributed-rate-limit/) - Advanced rate limiting
- [API Gateway](../api-gateway/) - Complete API management
- [Tracing](../tracing/) - Distributed tracing for debugging

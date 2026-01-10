+++
title = "Inference"
weight = 11
+++

The `inference` block provides first-class support for LLM/AI inference traffic patterns, including token-based rate limiting, provider-specific adapters, and model-aware load balancing.

## Overview

Inference routing addresses the unique challenges of AI/LLM traffic:

- **Token-based rate limiting**: Limit by tokens per minute rather than requests per second
- **Provider adapters**: Extract token counts from OpenAI, Anthropic, and generic APIs
- **Intelligent load balancing**: Route based on estimated queue time (tokens queued / throughput)
- **Model-based routing**: Route to different upstreams based on model name with glob patterns
- **Fallback routing**: Automatic failover with cross-provider model mapping
- **Token budgets**: Track cumulative usage with alerts and enforcement
- **Cost attribution**: Per-model pricing and spending metrics
- **Semantic guardrails**: Prompt injection detection and PII scanning via external agents

## Basic Configuration

```kdl
routes {
    route "openai-proxy" {
        matches {
            path-prefix "/v1/"
        }
        service-type "inference"
        upstream "llm-pool"

        inference {
            provider "openai"

            rate-limit {
                tokens-per-minute 100000
                requests-per-minute 500
                burst-tokens 20000
            }
        }
    }
}
```

## Service Type

Set `service-type` to `"inference"` to enable inference-specific handling:

```kdl
route "llm-api" {
    service-type "inference"
}
```

This enables:
- Token counting on requests/responses
- Token-based rate limiting
- JSON error responses (like `api` service type)
- Integration with inference-aware load balancing

## Provider Configuration

### Provider Selection

```kdl
inference {
    provider "openai"    // or "anthropic" or "generic"
}
```

| Provider | Token Header | Body Format |
|----------|--------------|-------------|
| `openai` | `x-ratelimit-used-tokens` | `usage.total_tokens` |
| `anthropic` | `anthropic-ratelimit-tokens-*` | `usage.input_tokens + output_tokens` |
| `generic` | `x-tokens-used` | OpenAI or Anthropic format |

### OpenAI Provider

```kdl
inference {
    provider "openai"
}
```

Token extraction:
1. **Headers** (preferred): `x-ratelimit-used-tokens`, or calculated from `x-ratelimit-limit-tokens` - `x-ratelimit-remaining-tokens`
2. **Body** (fallback): `usage.total_tokens` from response JSON

### Anthropic Provider

```kdl
inference {
    provider "anthropic"
}
```

Token extraction:
1. **Headers** (preferred): Calculated from `anthropic-ratelimit-tokens-limit` - `anthropic-ratelimit-tokens-remaining`
2. **Body** (fallback): `usage.input_tokens + usage.output_tokens` from response JSON

### Generic Provider

```kdl
inference {
    provider "generic"
}
```

For custom or self-hosted LLM APIs. Tries multiple extraction methods:
- Headers: `x-tokens-used`, `x-token-count`, `x-total-tokens`
- Body: OpenAI format, then Anthropic format

### Model Header

Override the header used to extract model name:

```kdl
inference {
    provider "openai"
    model-header "x-model"
}
```

## Token Rate Limiting

Token-based rate limiting is essential for LLM APIs where request cost varies dramatically based on token count.

### Basic Rate Limiting

```kdl
inference {
    rate-limit {
        tokens-per-minute 100000
        burst-tokens 20000
    }
}
```

| Option | Required | Description |
|--------|----------|-------------|
| `tokens-per-minute` | Yes | Maximum tokens per minute per client |
| `burst-tokens` | Yes | Maximum burst capacity |
| `requests-per-minute` | No | Secondary request limit |
| `estimation-method` | No | How to estimate request tokens |

### Dual Limiting

Combine token and request limits for comprehensive protection:

```kdl
inference {
    rate-limit {
        tokens-per-minute 100000
        requests-per-minute 500
        burst-tokens 20000
    }
}
```

Both limits must pass for a request to proceed. This prevents:
- High-volume, low-token attacks
- Low-volume, high-token attacks

### Token Estimation Methods

Configure how request tokens are estimated before the response is available:

```kdl
inference {
    rate-limit {
        tokens-per-minute 100000
        burst-tokens 10000
        estimation-method "tiktoken"
    }
}
```

| Method | Description | Accuracy |
|--------|-------------|----------|
| `chars` | Characters / 4 (default) | ~75% |
| `words` | Words * 1.3 | ~80% |
| `tiktoken` | Model-specific BPE tokenizer | ~99% |

After the response, actual token counts are used to refund or charge the difference.

### Tiktoken Tokenizer

When `estimation-method` is set to `tiktoken`, Sentinel uses OpenAI's tiktoken tokenizer for accurate token counting. This requires the `tiktoken` feature to be enabled at build time.

**Model-specific encodings:**

| Encoding | Models |
|----------|--------|
| `o200k_base` | GPT-4o, GPT-4o-mini |
| `cl100k_base` | GPT-4, GPT-4-turbo, GPT-3.5-turbo, Claude (approximation) |
| `p50k_base` | Codex, text-davinci-003 |

**Features:**

- **Cached tokenizers**: BPE instances are cached and reused across requests
- **Model detection**: Automatically selects the correct encoding based on model name
- **Chat-aware parsing**: Extracts message content from chat completion requests
- **Multi-modal support**: Estimates tokens for image attachments (~170 tokens per image)
- **Tool call handling**: Counts tokens in function names and arguments

**Request parsing:**

For chat completion requests, tiktoken parses the JSON to extract just the text content:

```json
{
  "model": "gpt-4",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello!"}
  ]
}
```

Token count includes:
- Message content (tokenized with model-specific encoding)
- Role names (~1 token each)
- Per-message overhead (~4 tokens for formatting)
- Conversation overhead (~3 tokens)

**Fallback behavior:**

If the `tiktoken` feature is not enabled at compile time, the tokenizer falls back to character-based estimation (characters / 4).

```bash
# Build with tiktoken support
cargo build --features tiktoken
```

### Streaming Token Counting

For streaming responses (SSE), Sentinel automatically counts tokens as they stream through:

**How it works:**

1. **Detection**: SSE responses are detected via `Content-Type: text/event-stream`
2. **Parsing**: Each SSE chunk is parsed to extract content deltas
3. **Accumulation**: Content is accumulated across all chunks
4. **Counting**: Final token count is calculated when the stream completes

**Supported formats:**

| Provider | SSE Format | Usage in Stream |
|----------|-----------|-----------------|
| OpenAI | `{"choices":[{"delta":{"content":"..."}}]}` | Final chunk includes `usage` |
| Anthropic | `{"type":"content_block_delta","delta":{"text":"..."}}` | `message_delta` includes `usage` |

**Token count sources (priority order):**

1. **API-provided**: If the LLM includes usage in the SSE stream (preferred)
2. **Tiktoken**: Count accumulated content using model-specific tokenizer
3. **Fallback**: Character-based estimation if tiktoken unavailable

**Example SSE flow:**

```
data: {"choices":[{"delta":{"content":"Hello"}}]}
data: {"choices":[{"delta":{"content":" world"}}]}
data: {"choices":[{"delta":{},"finish_reason":"stop"}],"usage":{"prompt_tokens":10,"completion_tokens":2}}
data: [DONE]
```

Sentinel accumulates "Hello world" and either uses the API-provided token count (2 completion tokens) or counts via tiktoken.

### Rate Limit Response

When rate limited, clients receive a `429 Too Many Requests` with headers:

```
HTTP/1.1 429 Too Many Requests
Retry-After: 1234
X-RateLimit-Limit-Tokens: 100000
X-RateLimit-Remaining-Tokens: 0
X-RateLimit-Reset: 1704067200
```

## Token Budget Management

While rate limiting controls tokens *per minute*, budget management tracks **cumulative token usage** over longer periods (hourly, daily, monthly). This enables:

- **Quota enforcement** for API consumers
- **Usage alerts** at configurable thresholds
- **Spending controls** for cost management

### Basic Budget Configuration

```kdl
inference {
    provider "openai"

    budget {
        period "daily"
        limit 1000000
        enforce true
    }
}
```

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `period` | No | `daily` | Reset period: `hourly`, `daily`, `monthly`, or custom seconds |
| `limit` | Yes | — | Maximum tokens allowed in the period |
| `enforce` | No | `true` | Block requests when budget exhausted |
| `alert-thresholds` | No | `0.80 0.90 0.95` | Percentages that trigger alerts |
| `rollover` | No | `false` | Carry unused tokens to next period |
| `burst-allowance` | No | — | Allow percentage above limit (soft limit) |

### Budget Periods

```kdl
// Hourly budget
budget {
    period "hourly"
    limit 100000
}

// Daily budget (default)
budget {
    period "daily"
    limit 1000000
}

// Monthly budget
budget {
    period "monthly"
    limit 50000000
}

// Custom period (seconds)
budget {
    period 3600  // 1 hour in seconds
    limit 100000
}
```

### Alert Thresholds

Configure usage alerts at specific percentages:

```kdl
budget {
    period "daily"
    limit 1000000
    alert-thresholds 0.50 0.80 0.90 0.95
}
```

Alerts are logged when usage crosses each threshold:

```
2026-01-10T14:30:00Z WARN Token budget alert threshold crossed
    route_id="openai-proxy" tenant="client-123"
    threshold_pct=80 tokens_used=800000 tokens_limit=1000000
```

### Soft Limits with Burst Allowance

Allow temporary burst usage above the limit:

```kdl
budget {
    period "daily"
    limit 1000000
    burst-allowance 0.10  // Allow 10% burst (up to 1.1M tokens)
    enforce true
}
```

When within burst allowance:
- Request proceeds with a warning logged
- `X-Budget-Remaining` header shows negative value
- Next request may be blocked if over burst limit

### Rollover

Carry unused tokens to the next period:

```kdl
budget {
    period "daily"
    limit 1000000
    rollover true
}
```

If a client uses 300,000 tokens on day 1, they have 1,700,000 tokens available on day 2 (capped at 2× limit).

### Budget Response Headers

Successful responses include budget headers when budget tracking is enabled:

```
HTTP/1.1 200 OK
X-Budget-Remaining: 500000
X-Budget-Period-Reset: 2026-01-11T00:00:00Z
```

| Header | Description |
|--------|-------------|
| `X-Budget-Remaining` | Tokens remaining in current period |
| `X-Budget-Period-Reset` | ISO 8601 timestamp when period resets |

### Budget Exhausted Response

When budget is exhausted and enforcement is enabled:

```
HTTP/1.1 429 Too Many Requests
Retry-After: 3600
Content-Type: application/json

{"error": "Token budget exhausted"}
```

## Cost Attribution

Track the monetary cost of inference requests with per-model pricing.

### Basic Cost Configuration

```kdl
inference {
    provider "openai"

    cost-attribution {
        pricing {
            model "gpt-4*" {
                input-cost-per-million 30.0
                output-cost-per-million 60.0
            }
            model "gpt-3.5*" {
                input-cost-per-million 0.50
                output-cost-per-million 1.50
            }
        }
        default-input-cost 1.0
        default-output-cost 2.0
    }
}
```

### Model Pattern Matching

Model patterns support wildcards:

| Pattern | Matches |
|---------|---------|
| `gpt-4*` | `gpt-4`, `gpt-4-turbo`, `gpt-4o`, `gpt-4o-mini` |
| `*claude*` | `claude-3-opus`, `claude-3-sonnet`, `claude-instant` |
| `llama-3` | Exact match only |

### Multiple Pricing Rules

```kdl
cost-attribution {
    pricing {
        // OpenAI models
        model "gpt-4o" {
            input-cost-per-million 5.0
            output-cost-per-million 15.0
        }
        model "gpt-4-turbo*" {
            input-cost-per-million 10.0
            output-cost-per-million 30.0
        }
        model "gpt-4*" {
            input-cost-per-million 30.0
            output-cost-per-million 60.0
        }
        model "gpt-3.5*" {
            input-cost-per-million 0.50
            output-cost-per-million 1.50
        }

        // Anthropic models
        model "claude-3-opus*" {
            input-cost-per-million 15.0
            output-cost-per-million 75.0
        }
        model "claude-3-sonnet*" {
            input-cost-per-million 3.0
            output-cost-per-million 15.0
        }
        model "claude-3-haiku*" {
            input-cost-per-million 0.25
            output-cost-per-million 1.25
        }
    }

    // Fallback for unknown models
    default-input-cost 1.0
    default-output-cost 2.0
    currency "USD"
}
```

### Currency Override

Set currency per model or globally:

```kdl
cost-attribution {
    currency "USD"  // Global default

    pricing {
        model "gpt-4*" {
            input-cost-per-million 30.0
            output-cost-per-million 60.0
            currency "EUR"  // Override for this model
        }
    }
}
```

### Cost Metrics

Cost attribution exposes Prometheus metrics:

```prometheus
# Total cost by model and route
sentinel_inference_cost_total{namespace="",service="",route="openai",model="gpt-4-turbo",currency="USD"} 12.45

# Token counts by model
sentinel_inference_input_tokens_total{route="openai",model="gpt-4-turbo"} 415000
sentinel_inference_output_tokens_total{route="openai",model="gpt-4-turbo"} 125000

# Cost per request histogram
sentinel_inference_cost_per_request_bucket{route="openai",model="gpt-4-turbo",le="0.01"} 45
sentinel_inference_cost_per_request_bucket{route="openai",model="gpt-4-turbo",le="0.1"} 892
```

## Inference Routing

### Routing Strategies

```kdl
inference {
    routing {
        strategy "least_tokens_queued"
    }
}
```

| Strategy | Description |
|----------|-------------|
| `round_robin` | Simple rotation (default) |
| `least_tokens_queued` | Route to least loaded target by tokens |

### Least Tokens Queued

For inference workloads, `least_tokens_queued` provides the best load distribution:

```kdl
inference {
    routing {
        strategy "least_tokens_queued"
    }
}
```

Selection algorithm:
```
queue_time = queued_tokens / tokens_per_second
select target with min(queue_time)
```

This accounts for:
- Current queue depth (tokens waiting)
- Historical throughput (tokens per second EWMA)

## Model-Based Routing

Route inference requests to different upstreams based on the model name in the request. This enables:

- **Multi-provider gateways**: Route GPT models to OpenAI, Claude models to Anthropic
- **Specialized hardware**: Route large models to high-memory GPUs
- **Cost optimization**: Route cheaper models to lower-cost infrastructure

### Basic Model Routing

```kdl
inference {
    provider "openai"

    model-routing {
        default-upstream "openai-primary"

        model "gpt-4" upstream="openai-premium"
        model "gpt-4*" upstream="openai-primary" provider="openai"
        model "claude-*" upstream="anthropic-backend" provider="anthropic"
        model "llama-*" upstream="local-gpu" provider="generic"
    }
}
```

| Option | Required | Description |
|--------|----------|-------------|
| `default-upstream` | No | Fallback upstream when no pattern matches |
| `model` | Yes | Model pattern with upstream mapping |
| `upstream` | Yes | Target upstream for matching models |
| `provider` | No | Override inference provider for this upstream |

### Pattern Matching

Model patterns support glob-style wildcards:

| Pattern | Matches |
|---------|---------|
| `gpt-4` | Exact match only |
| `gpt-4*` | `gpt-4`, `gpt-4-turbo`, `gpt-4o`, `gpt-4o-mini` |
| `claude-*` | `claude-3-opus`, `claude-3-sonnet`, `claude-3-haiku` |
| `*-turbo` | `gpt-4-turbo`, `gpt-3.5-turbo` |
| `claude-*-sonnet` | `claude-3-sonnet`, `claude-3.5-sonnet` |

**First match wins**: Order patterns from most specific to least specific.

### Model Header Extraction

Sentinel extracts the model name from request headers:

1. `x-model` (preferred)
2. `x-model-id` (fallback)

If no header is found, the `default-upstream` is used.

### Cross-Provider Routing

Route requests to different providers with automatic provider switching:

```kdl
routes {
    route "unified-llm-api" {
        matches {
            path-prefix "/v1/chat/completions"
        }
        service-type "inference"
        upstream "openai-primary"

        inference {
            provider "openai"  // Default provider

            model-routing {
                default-upstream "openai-primary"

                // OpenAI models stay with OpenAI
                model "gpt-4*" upstream="openai-primary" provider="openai"
                model "gpt-3.5*" upstream="openai-secondary" provider="openai"

                // Claude models route to Anthropic
                model "claude-*" upstream="anthropic-backend" provider="anthropic"

                // Local models use generic provider
                model "llama-*" upstream="local-gpu" provider="generic"
                model "mistral-*" upstream="local-gpu" provider="generic"
            }
        }
    }
}

upstreams {
    upstream "openai-primary" {
        targets { target { address "api.openai.com:443" } }
        tls { enabled true }
    }
    upstream "openai-secondary" {
        targets { target { address "api.openai.com:443" } }
        tls { enabled true }
    }
    upstream "anthropic-backend" {
        targets { target { address "api.anthropic.com:443" } }
        tls { enabled true }
    }
    upstream "local-gpu" {
        targets {
            target { address "gpu-1.internal:8080" }
            target { address "gpu-2.internal:8080" }
        }
        load-balancing "least_tokens_queued"
    }
}
```

When a request with `x-model: claude-3-opus` arrives:
1. Model routing matches `claude-*` pattern
2. Request routes to `anthropic-backend` upstream
3. Provider switches to `anthropic` for correct token extraction

### Model Routing Metrics

```prometheus
# Requests routed by model
sentinel_model_routing_total{route="unified-api",model="gpt-4-turbo",upstream="openai-primary"} 1523

# Requests using default upstream (no pattern matched)
sentinel_model_routing_default_total{route="unified-api"} 42

# Requests with no model header
sentinel_model_routing_no_header_total{route="unified-api"} 15

# Provider overrides applied
sentinel_model_routing_provider_override_total{route="unified-api",upstream="anthropic-backend",provider="anthropic"} 892
```

## Fallback Routing

Automatically fail over to alternative upstreams when the primary is unavailable, exhausted, or returns errors.

### Basic Fallback Configuration

```kdl
routes {
    route "inference-api" {
        matches {
            path-prefix "/v1/chat/completions"
        }
        upstream "openai-primary"

        inference {
            provider "openai"
        }

        fallback {
            max-attempts 2

            triggers {
                on-health-failure true
                on-budget-exhausted true
                on-connection-error true
                on-error-codes 429 500 502 503 504
            }

            fallback-upstream "anthropic-fallback" {
                provider "anthropic"
                skip-if-unhealthy true

                model-mapping {
                    "gpt-4" "claude-3-opus"
                    "gpt-4o" "claude-3-5-sonnet"
                    "gpt-3.5-turbo" "claude-3-haiku"
                }
            }

            fallback-upstream "local-gpu" {
                provider "generic"
                skip-if-unhealthy true

                model-mapping {
                    "gpt-4*" "llama-3-70b"
                    "gpt-3.5*" "llama-3-8b"
                }
            }
        }
    }
}
```

### Fallback Triggers

Configure when fallback is triggered:

| Trigger | Default | Description |
|---------|---------|-------------|
| `on-health-failure` | `true` | Primary upstream health check failed |
| `on-budget-exhausted` | `false` | Token budget for primary is exhausted |
| `on-latency-threshold-ms` | — | Response time exceeds threshold |
| `on-error-codes` | — | Specific HTTP status codes (e.g., 429, 503) |
| `on-connection-error` | `true` | Connection to primary failed |

```kdl
fallback {
    triggers {
        on-health-failure true
        on-budget-exhausted true
        on-latency-threshold-ms 5000
        on-error-codes 429 500 502 503 504
        on-connection-error true
    }
}
```

### Fallback Upstreams

Define ordered fallback targets:

```kdl
fallback {
    max-attempts 3  // Try up to 3 upstreams total

    fallback-upstream "backup-1" {
        provider "openai"
        skip-if-unhealthy true
    }

    fallback-upstream "backup-2" {
        provider "anthropic"
        skip-if-unhealthy true
    }
}
```

| Option | Default | Description |
|--------|---------|-------------|
| `provider` | `generic` | Inference provider for this upstream |
| `skip-if-unhealthy` | `false` | Skip if health check reports unhealthy |
| `model-mapping` | — | Map models to equivalents on this provider |

### Model Mapping

When falling back to a different provider, map model names:

```kdl
fallback-upstream "anthropic-fallback" {
    provider "anthropic"

    model-mapping {
        // Exact mappings
        "gpt-4" "claude-3-opus"
        "gpt-4-turbo" "claude-3-5-sonnet"
        "gpt-3.5-turbo" "claude-3-haiku"

        // Glob pattern mappings
        "gpt-4o*" "claude-3-5-sonnet"
        "gpt-4*" "claude-3-opus"
    }
}
```

Model mapping supports the same glob patterns as model-based routing.

### Fallback Response Headers

When fallback occurs, response headers indicate the routing decision:

```
HTTP/1.1 200 OK
X-Fallback-Used: true
X-Fallback-Upstream: anthropic-fallback
X-Fallback-Reason: health_check_failed
X-Original-Upstream: openai-primary
```

### Fallback Metrics

```prometheus
# Fallback attempts by reason
sentinel_fallback_attempts_total{route="inference-api",from_upstream="openai-primary",to_upstream="anthropic-fallback",reason="health_check_failed"} 45

# Successful responses after fallback
sentinel_fallback_success_total{route="inference-api",upstream="anthropic-fallback"} 42

# All fallback upstreams exhausted
sentinel_fallback_exhausted_total{route="inference-api"} 3

# Model mapping applied during fallback
sentinel_fallback_model_mapping_total{route="inference-api",original_model="gpt-4",mapped_model="claude-3-opus"} 38
```

### Complete Fallback Example

```kdl
routes {
    route "resilient-llm-api" {
        priority 100
        matches {
            path-prefix "/v1/"
        }
        service-type "inference"
        upstream "openai-primary"

        inference {
            provider "openai"

            rate-limit {
                tokens-per-minute 100000
                burst-tokens 20000
                estimation-method "tiktoken"
            }

            budget {
                period "daily"
                limit 1000000
                enforce true
            }
        }

        fallback {
            max-attempts 3

            triggers {
                on-health-failure true
                on-budget-exhausted true
                on-error-codes 429 503
                on-connection-error true
            }

            // First fallback: Different OpenAI endpoint
            fallback-upstream "openai-secondary" {
                provider "openai"
                skip-if-unhealthy true
            }

            // Second fallback: Anthropic
            fallback-upstream "anthropic-backend" {
                provider "anthropic"
                skip-if-unhealthy true

                model-mapping {
                    "gpt-4" "claude-3-opus"
                    "gpt-4o" "claude-3-5-sonnet"
                    "gpt-4o-mini" "claude-3-haiku"
                    "gpt-3.5-turbo" "claude-3-haiku"
                }
            }

            // Third fallback: Local models
            fallback-upstream "local-gpu" {
                provider "generic"
                skip-if-unhealthy true

                model-mapping {
                    "gpt-4*" "llama-3-70b"
                    "gpt-3.5*" "llama-3-8b"
                    "claude-*" "llama-3-70b"
                }
            }
        }

        policies {
            timeout-secs 120
        }
    }
}

upstreams {
    upstream "openai-primary" {
        targets { target { address "api.openai.com:443" } }
        tls { enabled true }
        health-check {
            type "http" { path "/v1/models" expected-status 200 }
            interval-secs 30
        }
    }

    upstream "openai-secondary" {
        targets { target { address "api.openai.com:443" } }
        tls { enabled true }
        health-check {
            type "http" { path "/v1/models" expected-status 200 }
            interval-secs 30
        }
    }

    upstream "anthropic-backend" {
        targets { target { address "api.anthropic.com:443" } }
        tls { enabled true }
        health-check {
            type "http" { path "/v1/models" expected-status 200 }
            interval-secs 30
        }
    }

    upstream "local-gpu" {
        targets {
            target { address "gpu-1.internal:8080" }
            target { address "gpu-2.internal:8080" }
        }
        load-balancing "least_tokens_queued"
        health-check {
            type "inference" {
                endpoint "/v1/models"
                expected-models "llama-3-70b" "llama-3-8b"
            }
            interval-secs 30
        }
    }
}
```

## Semantic Guardrails

Semantic guardrails provide content inspection for inference routes via external agents. This enables:

- **Prompt injection detection**: Block or flag requests containing injection attacks
- **PII detection**: Detect sensitive data (SSN, credit cards, emails) in responses
- **Configurable actions**: Block, log, or warn based on detection results
- **Failure modes**: Define behavior when guardrail agents are unavailable

### Basic Guardrails Configuration

```kdl
routes {
    route "inference-api" {
        matches {
            path-prefix "/v1/chat/completions"
        }
        service-type "inference"
        upstream "openai-primary"

        inference {
            provider "openai"

            guardrails {
                prompt-injection {
                    enabled true
                    agent "prompt-guard"
                    action "block"
                    block-status 400
                    block-message "Request blocked: potential prompt injection detected"
                    timeout-ms 500
                    failure-mode "open"
                }

                pii-detection {
                    enabled true
                    agent "pii-scanner"
                    action "log"
                    categories "ssn" "credit-card" "email" "phone"
                    timeout-ms 1000
                    failure-mode "open"
                }
            }
        }
    }
}
```

### Prompt Injection Detection

Detects attempts to manipulate LLM behavior through malicious prompts in the request phase.

```kdl
guardrails {
    prompt-injection {
        enabled true
        agent "prompt-guard"
        action "block"
        block-status 400
        block-message "Request blocked: potential prompt injection detected"
        timeout-ms 500
        failure-mode "open"
    }
}
```

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `enabled` | No | `false` | Enable prompt injection detection |
| `agent` | Yes | — | Name of the guardrail agent to use |
| `action` | No | `block` | Action on detection: `block`, `log`, or `warn` |
| `block-status` | No | `400` | HTTP status code when blocking |
| `block-message` | No | — | Custom message in block response |
| `timeout-ms` | No | `500` | Agent call timeout in milliseconds |
| `failure-mode` | No | `open` | Behavior on agent failure: `open` or `closed` |

#### Actions

| Action | Behavior |
|--------|----------|
| `block` | Return error response, do not forward to upstream |
| `log` | Log detection, allow request to proceed |
| `warn` | Allow request, add `X-Guardrail-Warning` header to response |

#### Failure Modes

| Mode | Behavior |
|------|----------|
| `open` | Allow request if agent times out or fails (fail-open) |
| `closed` | Block request if agent times out or fails (fail-closed) |

### PII Detection

Detects personally identifiable information in LLM responses during the logging phase.

```kdl
guardrails {
    pii-detection {
        enabled true
        agent "pii-scanner"
        action "log"
        categories "ssn" "credit-card" "email" "phone" "address"
        timeout-ms 1000
        failure-mode "open"
    }
}
```

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `enabled` | No | `false` | Enable PII detection |
| `agent` | Yes | — | Name of the guardrail agent to use |
| `action` | No | `log` | Action on detection: `log`, `redact`, or `block` |
| `categories` | No | — | PII categories to detect |
| `timeout-ms` | No | `1000` | Agent call timeout in milliseconds |
| `failure-mode` | No | `open` | Behavior on agent failure |

#### PII Categories

Common PII categories supported by guardrail agents:

| Category | Examples |
|----------|----------|
| `ssn` | Social Security Numbers |
| `credit-card` | Credit/debit card numbers |
| `email` | Email addresses |
| `phone` | Phone numbers |
| `address` | Physical addresses |
| `name` | Personal names |
| `dob` | Dates of birth |
| `passport` | Passport numbers |
| `driver-license` | Driver's license numbers |

#### PII Actions

| Action | Behavior |
|--------|----------|
| `log` | Log detection with categories, response unchanged |
| `redact` | Replace detected PII with redacted placeholders |
| `block` | Block response (non-streaming only) |

> **Note:** PII detection runs in the logging phase after the response has been sent. For streaming responses, the `redact` and `block` actions are not supported; use `log` to record detections.

### Agent Configuration

Guardrail agents must be defined in the agents section:

```kdl
agents {
    agent "prompt-guard" {
        address "127.0.0.1:9001"
        timeout-ms 500
        failure-mode "open"
    }

    agent "pii-scanner" {
        address "127.0.0.1:9002"
        timeout-ms 1000
        failure-mode "open"
    }
}
```

Agents receive `GuardrailInspect` events with:
- `inspection_type`: `PromptInjection` or `PiiDetection`
- `content`: Text content to inspect
- `model`: Model name (for prompt injection)
- `categories`: Requested PII categories (for PII detection)
- `correlation_id`: Request trace ID

Agents respond with:
- `detected`: Boolean indicating if issues were found
- `confidence`: Detection confidence score (0.0-1.0)
- `detections`: List of detected issues with category and description
- `redacted_content`: Optional redacted version of content

### Response Headers

When guardrails detect issues in warn mode:

```
HTTP/1.1 200 OK
X-Guardrail-Warning: prompt-injection-detected
```

### Guardrail Metrics

```prometheus
# Requests blocked by prompt injection detection
sentinel_blocked_requests_total{reason="prompt_injection"} 42

# PII detections by route and category
sentinel_pii_detected_total{route="inference-api",category="ssn"} 15
sentinel_pii_detected_total{route="inference-api",category="email"} 128
sentinel_pii_detected_total{route="inference-api",category="credit-card"} 7
```

### Complete Guardrails Example

```kdl
routes {
    route "secure-inference-api" {
        priority 100
        matches {
            path-prefix "/v1/chat/completions"
        }
        service-type "inference"
        upstream "openai-primary"

        inference {
            provider "openai"

            rate-limit {
                tokens-per-minute 100000
                burst-tokens 20000
            }

            guardrails {
                // Block prompt injection attempts
                prompt-injection {
                    enabled true
                    agent "prompt-guard"
                    action "block"
                    block-status 400
                    block-message "Request blocked: potential prompt injection detected"
                    timeout-ms 500
                    failure-mode "open"  // Allow if agent unavailable
                }

                // Log PII in responses for compliance
                pii-detection {
                    enabled true
                    agent "pii-scanner"
                    action "log"
                    categories "ssn" "credit-card" "email" "phone"
                    timeout-ms 1000
                    failure-mode "open"
                }
            }
        }

        policies {
            timeout-secs 120
        }
    }
}

agents {
    agent "prompt-guard" {
        address "127.0.0.1:9001"
        timeout-ms 500
        failure-mode "open"
    }

    agent "pii-scanner" {
        address "127.0.0.1:9002"
        timeout-ms 1000
        failure-mode "open"
    }
}

upstreams {
    upstream "openai-primary" {
        targets { target { address "api.openai.com:443" } }
        tls { enabled true }
    }
}
```

### Best Practices

1. **Choose appropriate actions**: Use `block` for high-security environments; use `log` or `warn` for monitoring before enforcement
2. **Set reasonable timeouts**: Guardrail checks add latency; keep timeouts under 1 second for interactive APIs
3. **Use fail-open for availability**: Default to `failure-mode "open"` unless security requirements mandate fail-closed
4. **Monitor agent health**: Track agent latency and timeout metrics to ensure guardrails remain effective
5. **Start with logging**: Enable guardrails in `log` mode first to understand detection patterns before blocking
6. **Configure PII categories**: Only enable categories relevant to your use case to reduce false positives

## Load Balancing for Inference

The `least_tokens_queued` load balancing algorithm can also be set at the upstream level:

```kdl
upstreams {
    upstream "llm-pool" {
        targets {
            target { address "gpu-server-1:8080" }
            target { address "gpu-server-2:8080" }
            target { address "gpu-server-3:8080" }
        }
        load-balancing "least_tokens_queued"
    }
}
```

This is recommended for inference upstreams where request processing time correlates strongly with token count.

## Complete Examples

### OpenAI Proxy with Budget and Cost Tracking

```kdl
routes {
    route "openai" {
        priority 100
        matches {
            path-prefix "/openai/"
        }
        service-type "inference"
        upstream "openai-pool"
        strip-prefix "/openai"

        inference {
            provider "openai"

            rate-limit {
                tokens-per-minute 100000
                requests-per-minute 1000
                burst-tokens 20000
                estimation-method "tiktoken"
            }

            budget {
                period "daily"
                limit 1000000
                alert-thresholds 0.80 0.90 0.95
                enforce true
            }

            cost-attribution {
                pricing {
                    model "gpt-4o" {
                        input-cost-per-million 5.0
                        output-cost-per-million 15.0
                    }
                    model "gpt-4-turbo*" {
                        input-cost-per-million 10.0
                        output-cost-per-million 30.0
                    }
                    model "gpt-4*" {
                        input-cost-per-million 30.0
                        output-cost-per-million 60.0
                    }
                    model "gpt-3.5*" {
                        input-cost-per-million 0.50
                        output-cost-per-million 1.50
                    }
                }
                default-input-cost 1.0
                default-output-cost 2.0
            }

            routing {
                strategy "least_tokens_queued"
            }
        }

        policies {
            timeout-secs 120
            request-headers {
                set {
                    "Authorization" "Bearer ${OPENAI_API_KEY}"
                }
            }
        }
    }
}

upstreams {
    upstream "openai-pool" {
        targets {
            target { address "api.openai.com:443" }
        }
        tls {
            enabled true
        }
    }
}
```

### Multi-Provider Gateway

```kdl
routes {
    // OpenAI endpoint
    route "openai" {
        priority 100
        matches {
            path-prefix "/v1/openai/"
        }
        service-type "inference"
        upstream "openai"
        strip-prefix "/v1/openai"

        inference {
            provider "openai"
            rate-limit {
                tokens-per-minute 50000
                burst-tokens 10000
            }
        }
    }

    // Anthropic endpoint
    route "anthropic" {
        priority 100
        matches {
            path-prefix "/v1/anthropic/"
        }
        service-type "inference"
        upstream "anthropic"
        strip-prefix "/v1/anthropic"

        inference {
            provider "anthropic"
            rate-limit {
                tokens-per-minute 100000
                burst-tokens 20000
            }
        }
    }

    // Self-hosted models
    route "local-llm" {
        priority 100
        matches {
            path-prefix "/v1/local/"
        }
        service-type "inference"
        upstream "local-gpu-cluster"
        strip-prefix "/v1/local"

        inference {
            provider "generic"
            rate-limit {
                tokens-per-minute 500000
                requests-per-minute 100
                burst-tokens 50000
            }
            routing {
                strategy "least_tokens_queued"
            }
        }
    }
}

upstreams {
    upstream "openai" {
        targets {
            target { address "api.openai.com:443" }
        }
        tls { enabled true }
    }

    upstream "anthropic" {
        targets {
            target { address "api.anthropic.com:443" }
        }
        tls { enabled true }
    }

    upstream "local-gpu-cluster" {
        targets {
            target { address "gpu-1.internal:8080" }
            target { address "gpu-2.internal:8080" }
            target { address "gpu-3.internal:8080" }
        }
        load-balancing "least_tokens_queued"
        health-check {
            type "http" {
                path "/v1/models"
                expected-status 200
            }
            interval-secs 30
        }
    }
}
```

### Per-Tier Rate Limits

```kdl
routes {
    // Premium tier - higher limits
    route "premium-api" {
        priority 200
        matches {
            path-prefix "/v1/"
            header name="X-Tier" value="premium"
        }
        service-type "inference"
        upstream "llm-pool"

        inference {
            provider "openai"
            rate-limit {
                tokens-per-minute 500000
                requests-per-minute 5000
                burst-tokens 100000
            }
        }
    }

    // Free tier - lower limits
    route "free-api" {
        priority 100
        matches {
            path-prefix "/v1/"
        }
        service-type "inference"
        upstream "llm-pool"

        inference {
            provider "openai"
            rate-limit {
                tokens-per-minute 10000
                requests-per-minute 100
                burst-tokens 2000
            }
        }
    }
}
```

## Metrics

Inference routes expose additional Prometheus metrics:

```prometheus
# Token rate limiter stats
sentinel_inference_tokens_allowed_total{route="openai"}
sentinel_inference_tokens_rejected_total{route="openai"}
sentinel_inference_tokens_queued{upstream="llm-pool",target="gpu-1:8080"}

# Token throughput
sentinel_inference_tokens_per_second{upstream="llm-pool",target="gpu-1:8080"}

# Queue depth
sentinel_inference_queue_depth_tokens{upstream="llm-pool",target="gpu-1:8080"}
sentinel_inference_queue_depth_requests{upstream="llm-pool",target="gpu-1:8080"}
```

### Budget Metrics

When budget tracking is enabled:

```prometheus
# Budget limit per tenant (gauge)
sentinel_inference_budget_limit{namespace="",service="",route="openai",tenant="client-123"} 1000000

# Total tokens consumed against budget (counter)
sentinel_inference_budget_used_total{namespace="",service="",route="openai",tenant="client-123"} 450000

# Tokens remaining in budget (gauge, can be negative)
sentinel_inference_budget_remaining{namespace="",service="",route="openai",tenant="client-123"} 550000

# Requests blocked due to exhausted budget (counter)
sentinel_inference_budget_exhausted_total{namespace="",service="",route="openai",tenant="client-123"} 12

# Budget alert thresholds crossed (counter)
sentinel_inference_budget_alerts_total{namespace="",service="",route="openai",tenant="client-123",threshold="80"} 1
sentinel_inference_budget_alerts_total{namespace="",service="",route="openai",tenant="client-123",threshold="90"} 1
```

### Cost Metrics

When cost attribution is enabled:

```prometheus
# Total cost by model and route (counter)
sentinel_inference_cost_total{namespace="",service="",route="openai",model="gpt-4-turbo",currency="USD"} 12.45

# Input tokens by model (counter)
sentinel_inference_input_tokens_total{namespace="",service="",route="openai",model="gpt-4-turbo"} 415000

# Output tokens by model (counter)
sentinel_inference_output_tokens_total{namespace="",service="",route="openai",model="gpt-4-turbo"} 125000

# Cost per request histogram (histogram)
sentinel_inference_cost_per_request_bucket{namespace="",service="",route="openai",model="gpt-4-turbo",le="0.001"} 15
sentinel_inference_cost_per_request_bucket{namespace="",service="",route="openai",model="gpt-4-turbo",le="0.01"} 245
sentinel_inference_cost_per_request_bucket{namespace="",service="",route="openai",model="gpt-4-turbo",le="0.1"} 892
sentinel_inference_cost_per_request_bucket{namespace="",service="",route="openai",model="gpt-4-turbo",le="1.0"} 1050
sentinel_inference_cost_per_request_bucket{namespace="",service="",route="openai",model="gpt-4-turbo",le="+Inf"} 1052
```

## Best Practices

### Token Limits

1. **Start conservative**: Begin with lower limits and increase based on observed usage
2. **Use dual limiting**: Combine token and request limits for comprehensive protection
3. **Monitor refunds**: High refund rates indicate over-estimation; consider adjusting
4. **Use tiktoken when possible**: Build with `--features tiktoken` for ~99% accuracy; falls back to character-based estimation otherwise

### Load Balancing

1. **Use `least_tokens_queued`** for inference upstreams with varying request sizes
2. **Enable inference health checks** to verify model availability
3. **Set appropriate timeouts**: LLM requests can take 30-120 seconds

### Health Checks

Use the `inference` health check type for LLM backends:

```kdl
upstream "llm-pool" {
    targets {
        target { address "gpu-1:8080" }
        target { address "gpu-2:8080" }
    }
    load-balancing "least_tokens_queued"
    health-check {
        type "inference" {
            endpoint "/v1/models"
            expected-models "gpt-4" "llama-3"
        }
        interval-secs 30
        timeout-secs 10
    }
}
```

The inference health check:
- Probes the models endpoint (default: `/v1/models`)
- Expects HTTP 200 response
- Optionally verifies expected models are available
- Marks target unhealthy if models are missing

### Provider Selection

1. **Match provider to backend**: Use `openai` for OpenAI API, `anthropic` for Claude API
2. **Use `generic`** for self-hosted or uncommon APIs
3. **Prefer header extraction**: It's more efficient than body parsing

### Budget Management

1. **Choose appropriate periods**: Use `daily` for most use cases, `monthly` for enterprise quotas
2. **Set alert thresholds**: Configure alerts at 80%, 90%, 95% to notify before exhaustion
3. **Consider burst allowance**: Allow 10-20% burst for traffic spikes
4. **Enable rollover carefully**: Rollover can lead to large accumulated quotas
5. **Combine with rate limiting**: Budget controls total usage; rate limiting controls burst speed

### Cost Attribution

1. **Keep pricing rules updated**: Model pricing changes frequently
2. **Use specific patterns first**: Order rules from specific to general (e.g., `gpt-4-turbo` before `gpt-4*`)
3. **Set reasonable defaults**: Fallback pricing should be conservative (higher than expected)
4. **Monitor cost metrics**: Track `sentinel_inference_cost_total` for spending trends

### Model-Based Routing

1. **Order patterns carefully**: Most specific patterns first, then glob patterns (e.g., `gpt-4` before `gpt-4*`)
2. **Set a default upstream**: Always configure `default-upstream` to handle unknown models
3. **Use model headers**: Have clients send `x-model` header to enable routing before body parsing
4. **Match provider to upstream**: Use `provider` override when routing to different API providers
5. **Monitor routing metrics**: Track `sentinel_model_routing_total` to understand traffic distribution

### Fallback Routing

1. **Enable health checks**: Set `skip-if-unhealthy true` to avoid routing to known-bad upstreams
2. **Configure realistic triggers**: Start with `on-health-failure` and `on-connection-error`; add `on-error-codes` based on observed failures
3. **Plan model mappings**: Map to equivalent capability models (e.g., GPT-4 → Claude Opus, not Claude Haiku)
4. **Limit max attempts**: Set `max-attempts` to 2-3 to avoid excessive latency on failures
5. **Test fallback paths**: Regularly verify fallback upstreams work with mapped models
6. **Monitor exhaustion**: Alert on `sentinel_fallback_exhausted_total` to detect infrastructure issues

## Default Values

| Setting | Default |
|---------|---------|
| `provider` | `generic` |
| `estimation-method` | `chars` |
| `routing.strategy` | `round_robin` |
| `budget.period` | `daily` |
| `budget.enforce` | `true` |
| `budget.alert-thresholds` | `0.80, 0.90, 0.95` |
| `budget.rollover` | `false` |
| `cost-attribution.currency` | `USD` |
| `fallback.max-attempts` | `3` |
| `fallback.triggers.on-health-failure` | `true` |
| `fallback.triggers.on-budget-exhausted` | `false` |
| `fallback.triggers.on-connection-error` | `true` |
| `fallback-upstream.skip-if-unhealthy` | `false` |
| `fallback-upstream.provider` | `generic` |
| `guardrails.prompt-injection.enabled` | `false` |
| `guardrails.prompt-injection.action` | `block` |
| `guardrails.prompt-injection.block-status` | `400` |
| `guardrails.prompt-injection.timeout-ms` | `500` |
| `guardrails.prompt-injection.failure-mode` | `open` |
| `guardrails.pii-detection.enabled` | `false` |
| `guardrails.pii-detection.action` | `log` |
| `guardrails.pii-detection.timeout-ms` | `1000` |
| `guardrails.pii-detection.failure-mode` | `open` |

## Next Steps

- [Upstreams](../upstreams/) - Backend pool configuration including `least_tokens_queued`
- [Limits](../limits/) - General request limits and rate limiting
- [Routes](../routes/) - Route configuration basics

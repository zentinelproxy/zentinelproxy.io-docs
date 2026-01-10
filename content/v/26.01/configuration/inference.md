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
        estimation-method "chars"
    }
}
```

| Method | Description | Accuracy |
|--------|-------------|----------|
| `chars` | Characters / 4 (default) | ~75% |
| `words` | Words * 1.3 | ~80% |
| `tiktoken` | Actual tokenizer (future) | ~99% |

After the response, actual token counts are used to refund or charge the difference.

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
                estimation-method "chars"
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

## Next Steps

- [Upstreams](../upstreams/) - Backend pool configuration including `least_tokens_queued`
- [Limits](../limits/) - General request limits and rate limiting
- [Routes](../routes/) - Route configuration basics

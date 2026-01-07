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

### OpenAI Proxy

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

## Best Practices

### Token Limits

1. **Start conservative**: Begin with lower limits and increase based on observed usage
2. **Use dual limiting**: Combine token and request limits for comprehensive protection
3. **Monitor refunds**: High refund rates indicate over-estimation; consider adjusting

### Load Balancing

1. **Use `least_tokens_queued`** for inference upstreams with varying request sizes
2. **Enable health checks** on `/v1/models` or similar endpoints
3. **Set appropriate timeouts**: LLM requests can take 30-120 seconds

### Provider Selection

1. **Match provider to backend**: Use `openai` for OpenAI API, `anthropic` for Claude API
2. **Use `generic`** for self-hosted or uncommon APIs
3. **Prefer header extraction**: It's more efficient than body parsing

## Default Values

| Setting | Default |
|---------|---------|
| `provider` | `generic` |
| `estimation-method` | `chars` |
| `routing.strategy` | `round_robin` |

## Next Steps

- [Upstreams](../upstreams/) - Backend pool configuration including `least_tokens_queued`
- [Limits](../limits/) - General request limits and rate limiting
- [Routes](../routes/) - Route configuration basics

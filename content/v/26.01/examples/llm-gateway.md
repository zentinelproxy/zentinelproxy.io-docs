+++
title = "LLM Gateway"
weight = 60
+++

This example demonstrates configuring Sentinel as an LLM API gateway with token-based rate limiting, budget management, and cost attribution.

## Use Case

You want to:
- Proxy requests to multiple LLM providers (OpenAI, Anthropic)
- Rate limit by tokens per minute (not just requests)
- Track cumulative token usage per client with daily budgets
- Monitor costs per model and client
- Load balance across multiple inference backends

## Configuration

```kdl
// sentinel.kdl

version "1.0"

server {
    workers 4
    log-level "info"
}

listeners {
    listener "llm-gateway" {
        bind-address "0.0.0.0:8080"
    }

    listener "llm-gateway-tls" {
        bind-address "0.0.0.0:8443"
        tls {
            certificate "/etc/sentinel/certs/llm-gateway.crt"
            private-key "/etc/sentinel/certs/llm-gateway.key"
        }
    }
}

routes {
    // OpenAI API proxy with full budget and cost tracking
    route "openai-api" {
        priority 100
        matches {
            path-prefix "/v1/openai/"
        }
        service-type "inference"
        upstream "openai"
        strip-prefix "/v1/openai"

        inference {
            provider "openai"

            // Rate limiting: tokens per minute
            rate-limit {
                tokens-per-minute 100000
                requests-per-minute 1000
                burst-tokens 20000
                estimation-method "tiktoken"  // Accurate model-specific tokenization
            }

            // Budget: cumulative daily limit per client
            budget {
                period "daily"
                limit 1000000
                alert-thresholds 0.50 0.80 0.90 0.95
                enforce true
                burst-allowance 0.10
            }

            // Cost tracking with model-specific pricing
            cost-attribution {
                pricing {
                    model "gpt-4o" {
                        input-cost-per-million 5.0
                        output-cost-per-million 15.0
                    }
                    model "gpt-4o-mini" {
                        input-cost-per-million 0.15
                        output-cost-per-million 0.60
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
                currency "USD"
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

    // Anthropic API proxy
    route "anthropic-api" {
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
                tokens-per-minute 200000
                requests-per-minute 500
                burst-tokens 40000
            }

            budget {
                period "daily"
                limit 2000000
                alert-thresholds 0.80 0.90 0.95
                enforce true
            }

            cost-attribution {
                pricing {
                    model "claude-opus-4*" {
                        input-cost-per-million 15.0
                        output-cost-per-million 75.0
                    }
                    model "claude-sonnet-4*" {
                        input-cost-per-million 3.0
                        output-cost-per-million 15.0
                    }
                    model "claude-3-opus*" {
                        input-cost-per-million 15.0
                        output-cost-per-million 75.0
                    }
                    model "claude-3-5-sonnet*" {
                        input-cost-per-million 3.0
                        output-cost-per-million 15.0
                    }
                    model "claude-3-haiku*" {
                        input-cost-per-million 0.25
                        output-cost-per-million 1.25
                    }
                }
                default-input-cost 3.0
                default-output-cost 15.0
            }
        }

        policies {
            timeout-secs 120
            request-headers {
                set {
                    "x-api-key" "${ANTHROPIC_API_KEY}"
                    "anthropic-version" "2023-06-01"
                }
            }
        }
    }

    // Self-hosted models with higher limits
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
                burst-tokens 100000
            }

            budget {
                period "monthly"
                limit 100000000
                alert-thresholds 0.80 0.95
                enforce false  // Log only, don't block
            }

            routing {
                strategy "least_tokens_queued"
            }
        }

        policies {
            timeout-secs 300
        }
    }
}

upstreams {
    upstream "openai" {
        targets {
            target { address "api.openai.com:443" }
        }
        tls { enabled true }
        connect-timeout-ms 5000
    }

    upstream "anthropic" {
        targets {
            target { address "api.anthropic.com:443" }
        }
        tls { enabled true }
        connect-timeout-ms 5000
    }

    upstream "local-gpu-cluster" {
        targets {
            target { address "gpu-server-1.internal:8080" weight 100 }
            target { address "gpu-server-2.internal:8080" weight 100 }
            target { address "gpu-server-3.internal:8080" weight 50 }
        }
        load-balancing "least_tokens_queued"
        health-check {
            type "http" {
                path "/v1/models"
                expected-status 200
            }
            interval-secs 30
            timeout-secs 10
        }
    }
}

observability {
    metrics {
        enabled true
        bind-address "0.0.0.0:9090"
        path "/metrics"
    }
}
```

## Response Headers

When budget tracking is enabled, responses include informative headers:

```http
HTTP/1.1 200 OK
X-Correlation-Id: abc123
X-Budget-Remaining: 750000
X-Budget-Period-Reset: 2026-01-11T00:00:00Z
```

When budget is exhausted:

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 3600
Content-Type: application/json

{"error": "Token budget exhausted"}
```

## Prometheus Metrics

Query these metrics to monitor usage and costs:

```promql
# Total tokens used per client today
sum(sentinel_inference_budget_used_total{route="openai-api"}) by (tenant)

# Remaining budget percentage
sentinel_inference_budget_remaining / sentinel_inference_budget_limit * 100

# Total cost by model (last 24h)
increase(sentinel_inference_cost_total[24h])

# Average cost per request by model
rate(sentinel_inference_cost_total[1h]) / rate(sentinel_http_requests_total[1h])

# Budget exhaustion events
increase(sentinel_inference_budget_exhausted_total[24h])

# Alert threshold crossings
increase(sentinel_inference_budget_alerts_total[24h])
```

## Grafana Dashboard Queries

### Cost Overview Panel

```promql
# Total spend by provider (last 30 days)
sum(increase(sentinel_inference_cost_total[30d])) by (route)
```

### Budget Utilization Panel

```promql
# Current budget utilization percentage
(sentinel_inference_budget_limit - sentinel_inference_budget_remaining)
  / sentinel_inference_budget_limit * 100
```

### Top Spenders Panel

```promql
# Top 10 clients by spend
topk(10, sum(increase(sentinel_inference_cost_total[24h])) by (tenant))
```

## Usage Examples

### OpenAI Chat Completion

```bash
curl -X POST https://llm-gateway.example.com/v1/openai/chat/completions \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-client-key" \
  -d '{
    "model": "gpt-4o",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

### Anthropic Message

```bash
curl -X POST https://llm-gateway.example.com/v1/anthropic/messages \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-client-key" \
  -d '{
    "model": "claude-sonnet-4-20250514",
    "max_tokens": 1024,
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

## Alerting Rules

Example Prometheus alerting rules:

```yaml
groups:
  - name: llm-gateway
    rules:
      - alert: BudgetNearlyExhausted
        expr: |
          sentinel_inference_budget_remaining
            / sentinel_inference_budget_limit < 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Token budget nearly exhausted"
          description: "Client {{ $labels.tenant }} has less than 10% budget remaining"

      - alert: HighInferenceCost
        expr: |
          increase(sentinel_inference_cost_total[1h]) > 100
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High inference cost detected"
          description: "Route {{ $labels.route }} spent over $100 in the last hour"

      - alert: BudgetExhaustionSpike
        expr: |
          increase(sentinel_inference_budget_exhausted_total[5m]) > 10
        labels:
          severity: critical
        annotations:
          summary: "Multiple clients hitting budget limits"
          description: "{{ $value }} budget exhaustion events in the last 5 minutes"
```

## Next Steps

- [Inference Configuration](../configuration/inference/) — Full reference for inference options
- [Rate Limiting](../configuration/limits/) — Additional rate limiting options
- [Prometheus Integration](./prometheus/) — Complete metrics setup

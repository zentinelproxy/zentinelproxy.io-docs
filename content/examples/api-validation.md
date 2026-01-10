+++
title = "API Schema Validation"
weight = 3
+++

Validate API requests and responses against JSON schemas or OpenAPI specifications at the proxy layer. This example demonstrates contract validation, ensuring all API traffic conforms to your API specifications.

## Use Case

- Validate request payloads before reaching backend services
- Enforce API contracts at the edge
- Provide clear validation errors to clients
- Support both OpenAPI specs and inline JSON schemas
- Catch malformed requests early
- Validate response shapes in development

## Architecture

```
                    ┌─────────────────────┐
                    │     Sentinel        │
                    │  Schema Validator   │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │  Request Validated  │
                    │  Against Schema     │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   Backend Service   │
                    │      :3001          │
                    └─────────────────────┘
```

## Configuration

### OpenAPI/Swagger File Reference

Create `sentinel.kdl` with schema file reference:

```kdl
// API Validation with OpenAPI Specification

system {
    worker-threads 0
}

listeners {
    listener "http" {
        address "0.0.0.0:8080"
        protocol "http"
    }
}

upstreams {
    upstream "api-backend" {
        target "127.0.0.1:3001" weight=1
        load-balancing "round-robin"
    }
}

routes {
    // API v1 with OpenAPI validation
    route "api-v1" {
        priority 100
        matches {
            path-prefix "/api/v1"
        }
        upstream "api-backend"
        service-type "api"

        // Reference OpenAPI 3.0 specification
        api-schema {
            schema-file "/etc/sentinel/schemas/api-v1.yaml"
            validate-requests #true
            validate-responses #false
            strict-mode #true
        }

        // Buffer requests for validation
        policies {
            buffer-requests #true
            max-body-size "10MB"
        }
    }
}
```

### Inline OpenAPI Specification

Embed an OpenAPI spec directly in the configuration (useful for small APIs or testing):

```kdl
system {
    worker-threads 0
}

listeners {
    listener "http" {
        address "0.0.0.0:8080"
        protocol "http"
    }
}

routes {
    // API v1 with inline OpenAPI spec
    route "api-v1" {
        priority 100
        matches {
            path-prefix "/api/v1"
        }
        upstream "api-backend"

        policies {
            buffer-requests #true
            max-body-size "1MB"
        }
    }
}

upstreams {
    upstream "backend" {
        target "127.0.0.1:3000"
    }
}

```

**Note**: `schema-file` and `schema-content` are mutually exclusive. Use one or the other.

### Inline JSON Schema

For simpler APIs, define schemas inline using KDL syntax:

```kdl
routes {
    // User registration with inline schema
    route "register" {
        priority 200
        matches {
            path "/api/register"
            method "POST"
        }
        upstream "api-backend"
        service-type "api"

        api-schema {
            validate-requests #true
            strict-mode #true

            request-schema {
                type "object"
                properties {
                    email {
                        type "string"
                        format "email"
                        description "Valid email address"
                    }
                    password {
                        type "string"
                        minLength 8
                        maxLength 128
                        pattern "^(?=.*[a-z])(?=.*[A-Z])(?=.*\\d).*$"
                        description "Strong password with upper, lower, and digit"
                    }
                    username {
                        type "string"
                        minLength 3
                        maxLength 32
                        pattern "^[a-zA-Z0-9_-]+$"
                    }
                    age {
                        type "integer"
                        minimum 13
                        maximum 120
                    }
                    terms_accepted {
                        type "boolean"
                    }
                }
                required "email" "password" "username" "terms_accepted"
            }
        }

        policies {
            buffer-requests #true
        }
    }
}
```

### Request and Response Validation

Validate both directions for development/testing:

```kdl
routes {
    // User profile with bidirectional validation
    route "profile" {
        priority 100
        matches {
            path-prefix "/api/profile"
            method "GET" "PUT" "PATCH"
        }
        upstream "api-backend"
        service-type "api"

        api-schema {
            validate-requests #true
            validate-responses #true  // Enable in dev/staging
            strict-mode #true

            request-schema {
                type "object"
                properties {
                    display_name {
                        type "string"
                        minLength 1
                        maxLength 100
                    }
                    bio {
                        type "string"
                        maxLength 500
                    }
                    avatar_url {
                        type "string"
                        format "uri"
                    }
                }
                minProperties 1
            }

            response-schema {
                type "object"
                properties {
                    id {
                        type "string"
                        format "uuid"
                    }
                    email {
                        type "string"
                        format "email"
                    }
                    username { type "string" }
                    display_name { type "string" }
                    bio { type "string" }
                    avatar_url {
                        type "string"
                        format "uri"
                    }
                    created_at {
                        type "string"
                        format "date-time"
                    }
                    updated_at {
                        type "string"
                        format "date-time"
                    }
                }
                required "id" "email" "username" "created_at"
            }
        }

        policies {
            buffer-requests #true
            buffer-responses #true  // Required for response validation
        }
    }
}
```

### Complex Nested Schemas

Handle nested objects and arrays:

```kdl
routes {
    // Order creation with complex validation
    route "create-order" {
        priority 100
        matches {
            path "/api/orders"
            method "POST"
        }
        upstream "api-backend"
        service-type "api"

        api-schema {
            validate-requests #true
            strict-mode #true

            request-schema {
                type "object"
                properties {
                    customer {
                        type "object"
                        properties {
                            name {
                                type "string"
                                minLength 1
                                maxLength 100
                            }
                            email {
                                type "string"
                                format "email"
                            }
                            phone {
                                type "string"
                                pattern "^\\+?[1-9]\\d{1,14}$"
                            }
                        }
                        required "name" "email"
                    }
                    items {
                        type "array"
                        minItems 1
                        maxItems 100
                        items {
                            type "object"
                            properties {
                                product_id {
                                    type "string"
                                    pattern "^[A-Z0-9-]+$"
                                }
                                quantity {
                                    type "integer"
                                    minimum 1
                                    maximum 1000
                                }
                                price {
                                    type "number"
                                    minimum 0
                                    maximum 1000000
                                }
                            }
                            required "product_id" "quantity" "price"
                        }
                    }
                    shipping_address {
                        type "object"
                        properties {
                            street { type "string" }
                            city { type "string" }
                            state {
                                type "string"
                                minLength 2
                                maxLength 2
                            }
                            zip {
                                type "string"
                                pattern "^\\d{5}(-\\d{4})?$"
                            }
                            country {
                                type "string"
                                enum "US" "CA" "MX"
                            }
                        }
                        required "street" "city" "state" "zip" "country"
                    }
                    payment_method {
                        type "string"
                        enum "card" "paypal" "bank_transfer"
                    }
                }
                required "customer" "items" "shipping_address" "payment_method"
            }
        }

        policies {
            buffer-requests #true
            max-body-size "1MB"
        }

        error-pages {
            default-format "json"
            pages {
                "400" {
                    format "json"
                    message "Invalid order data"
                }
            }
        }
    }
}
```

## OpenAPI Specification Example

Create `/etc/sentinel/schemas/api-v1.yaml`:

```yaml
openapi: 3.0.0
info:
  title: User API
  version: 1.0.0
  description: User management API

paths:
  /api/v1/users:
    post:
      summary: Create a new user
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - email
                - password
                - username
              properties:
                email:
                  type: string
                  format: email
                  example: user@example.com
                password:
                  type: string
                  minLength: 8
                  maxLength: 128
                  pattern: '^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).*$'
                  example: SecurePass123
                username:
                  type: string
                  minLength: 3
                  maxLength: 32
                  pattern: '^[a-zA-Z0-9_-]+$'
                  example: john_doe
                age:
                  type: integer
                  minimum: 13
                  maximum: 120
                  example: 25
      responses:
        '201':
          description: User created successfully
          content:
            application/json:
              schema:
                type: object
                required:
                  - id
                  - email
                  - username
                  - created_at
                properties:
                  id:
                    type: string
                    format: uuid
                    example: 123e4567-e89b-12d3-a456-426614174000
                  email:
                    type: string
                    format: email
                  username:
                    type: string
                  created_at:
                    type: string
                    format: date-time
                    example: '2025-01-01T12:00:00Z'
        '400':
          description: Validation error
```

## Testing

### Valid Request

```bash
curl -X POST http://localhost:8080/api/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123",
    "username": "john_doe",
    "age": 25,
    "terms_accepted": true
  }'
```

**Response:** `201 Created`

### Invalid Request - Missing Field

```bash
curl -X POST http://localhost:8080/api/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123"
  }'
```

**Response:** `400 Bad Request`
```json
{
  "error": "Validation failed",
  "status": 400,
  "request_id": "req-abc123",
  "validation_errors": [
    {
      "field": "$.username",
      "message": "Missing required property",
      "value": #null
    },
    {
      "field": "$.terms_accepted",
      "message": "Missing required property",
      "value": #null
    }
  ]
}
```

### Invalid Request - Wrong Format

```bash
curl -X POST http://localhost:8080/api/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "not-an-email",
    "password": "short",
    "username": "a",
    "age": 10,
    "terms_accepted": true
  }'
```

**Response:** `400 Bad Request`
```json
{
  "error": "Validation failed",
  "status": 400,
  "request_id": "req-xyz789",
  "validation_errors": [
    {
      "field": "$.email",
      "message": "'not-an-email' is not a valid email",
      "value": "not-an-email"
    },
    {
      "field": "$.password",
      "message": "String is too short (expected minimum 8 characters)",
      "value": "short"
    },
    {
      "field": "$.username",
      "message": "String is too short (expected minimum 3 characters)",
      "value": "a"
    },
    {
      "field": "$.age",
      "message": "Value is below minimum (expected minimum 13)",
      "value": 10
    }
  ]
}
```

## Production Considerations

### Performance

- Schemas are compiled once at startup
- Validation adds ~1ms latency per request
- Use `buffer-requests #true` for validation
- Consider validating only critical endpoints

### Response Validation

Response validation requires buffering:

```kdl
policies {
    buffer-responses #true
    max-body-size "10MB"
}
```

**Only enable in development/staging** - adds latency and memory usage.

### Strict Mode

```kdl
api-schema {
    strict-mode #true  // Reject extra fields
}
```

Catches clients sending unexpected fields, preventing:
- API misuse
- Version conflicts
- Security issues

### Error Handling

Configure custom error pages:

```kdl
error-pages {
    default-format "json"
    pages {
        "400" {
            format "json"
            message "Request validation failed. Check your payload."
            headers {
                "X-Validation-Failed" "true"
            }
        }
    }
}
```

### Schema Versioning

Organize schemas by API version:

```
/etc/sentinel/schemas/
├── api-v1.yaml
├── api-v2.yaml
└── api-v3.yaml
```

Reference the correct version per route:

```kdl
route "api-v2" {
    matches {
        path-prefix "/api/v2"
    }
    api-schema {
        schema-file "/etc/sentinel/schemas/api-v2.yaml"
    }
}
```

## Benefits

1. **Early Validation**: Catch errors before backend processing
2. **Clear Errors**: Structured validation messages for clients
3. **Contract Enforcement**: Ensure API compliance at the edge
4. **Documentation**: OpenAPI specs serve as living documentation
5. **Security**: Prevent malformed or malicious payloads
6. **Development**: Response validation catches backend bugs

## Next Steps

- [Routes Configuration](../configuration/routes/) - Full route configuration reference
- [Upstreams](../configuration/upstreams/) - Backend service setup
- [Error Pages](../configuration/routes/#error-pages) - Custom error handling

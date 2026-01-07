+++
title = "Docker Compose"
weight = 4
+++

Docker Compose provides a straightforward way to deploy Sentinel with agents as containers. This guide covers local development and small production setups.

## Overview

```
┌──────────────────────────────────────────────────────────────┐
│                    docker-compose.yml                        │
│  ┌─────────────────────────────────────────────────────────┐│
│  │                    Network: sentinel                    ││
│  │                                                         ││
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐             ││
│  │  │ sentinel │  │   auth   │  │   waf    │             ││
│  │  │  :8080   │  │  :50051  │  │  :50052  │             ││
│  │  │  :9090   │  │          │  │          │             ││
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘             ││
│  │       │             │             │                    ││
│  │       └─────────────┴─────────────┘                    ││
│  │                  gRPC / UDS                            ││
│  └─────────────────────────────────────────────────────────┘│
│                                                              │
│  ┌──────────────────────────────────────────────────────────┐│
│  │  Volume: sockets (for Unix sockets)                     ││
│  │  Volume: config (configuration files)                   ││
│  └──────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────┘
```

## Quick Start

```yaml
# docker-compose.yml
version: "3.8"

services:
  sentinel:
    image: ghcr.io/raskell-io/sentinel:latest
    ports:
      - "8080:8080"   # HTTP
      - "9090:9090"   # Admin
    volumes:
      - ./config:/etc/sentinel:ro
      - sockets:/var/run/sentinel
    depends_on:
      - auth-agent
      - echo-agent
    networks:
      - sentinel

  auth-agent:
    image: ghcr.io/raskell-io/sentinel-auth:latest
    command: ["--socket", "/var/run/sentinel/auth.sock"]
    volumes:
      - sockets:/var/run/sentinel
    networks:
      - sentinel

  echo-agent:
    image: ghcr.io/raskell-io/sentinel-echo:latest
    command: ["--socket", "/var/run/sentinel/echo.sock"]
    volumes:
      - sockets:/var/run/sentinel
    networks:
      - sentinel

volumes:
  sockets:

networks:
  sentinel:
```

```bash
# Start everything
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f sentinel

# Stop
docker-compose down
```

## Unix Sockets vs gRPC

### Unix Sockets (Shared Volume)

Best for lowest latency when all containers run on the same host:

```yaml
services:
  sentinel:
    volumes:
      - sockets:/var/run/sentinel

  auth-agent:
    volumes:
      - sockets:/var/run/sentinel
    command: ["--socket", "/var/run/sentinel/auth.sock"]

volumes:
  sockets:
```

Configuration:
```kdl
agent "auth" type="auth" {
    unix-socket "/var/run/sentinel/auth.sock"
}
```

### gRPC (Network)

Best for scaling agents independently or running on different hosts:

```yaml
services:
  sentinel:
    depends_on:
      - waf-agent

  waf-agent:
    image: ghcr.io/raskell-io/sentinel-waf:latest
    command: ["--grpc", "0.0.0.0:50051"]
    networks:
      - sentinel
```

Configuration:
```kdl
agent "waf" type="waf" {
    grpc "http://waf-agent:50051"
}
```

## Complete Example

### Project Structure

```
sentinel-deploy/
├── docker-compose.yml
├── config/
│   └── sentinel.kdl
├── agents/
│   └── auth/
│       └── config.toml
└── certs/
    ├── cert.pem
    └── key.pem
```

### docker-compose.yml

```yaml
version: "3.8"

services:
  # ─────────────────────────────────────────────────────────
  # Sentinel Proxy
  # ─────────────────────────────────────────────────────────
  sentinel:
    image: ghcr.io/raskell-io/sentinel:latest
    container_name: sentinel
    ports:
      - "80:8080"
      - "443:8443"
      - "9090:9090"
    volumes:
      - ./config:/etc/sentinel:ro
      - ./certs:/etc/sentinel/tls:ro
      - sockets:/var/run/sentinel
    environment:
      - RUST_LOG=info
    depends_on:
      auth-agent:
        condition: service_healthy
      waf-agent:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9090/health"]
      interval: 10s
      timeout: 5s
      retries: 3
    restart: unless-stopped
    networks:
      - sentinel
      - backend

  # ─────────────────────────────────────────────────────────
  # Auth Agent (Unix Socket)
  # ─────────────────────────────────────────────────────────
  auth-agent:
    image: ghcr.io/raskell-io/sentinel-auth:latest
    container_name: sentinel-auth
    command:
      - "--socket"
      - "/var/run/sentinel/auth.sock"
      - "--config"
      - "/etc/auth/config.toml"
    volumes:
      - sockets:/var/run/sentinel
      - ./agents/auth:/etc/auth:ro
    environment:
      - RUST_LOG=info
      - AUTH_SECRET=${AUTH_SECRET}
    healthcheck:
      test: ["CMD", "test", "-S", "/var/run/sentinel/auth.sock"]
      interval: 5s
      timeout: 3s
      retries: 3
    restart: unless-stopped
    networks:
      - sentinel

  # ─────────────────────────────────────────────────────────
  # WAF Agent (gRPC)
  # ─────────────────────────────────────────────────────────
  waf-agent:
    image: ghcr.io/raskell-io/sentinel-waf:latest
    container_name: sentinel-waf
    command:
      - "--grpc"
      - "0.0.0.0:50051"
      - "--rules"
      - "/etc/waf/crs-rules"
    volumes:
      - ./agents/waf/rules:/etc/waf/crs-rules:ro
    environment:
      - RUST_LOG=info
    healthcheck:
      test: ["CMD", "grpc-health-probe", "-addr=:50051"]
      interval: 10s
      timeout: 5s
      retries: 3
    restart: unless-stopped
    networks:
      - sentinel

  # ─────────────────────────────────────────────────────────
  # Echo Agent (for debugging)
  # ─────────────────────────────────────────────────────────
  echo-agent:
    image: ghcr.io/raskell-io/sentinel-echo:latest
    container_name: sentinel-echo
    command: ["--grpc", "0.0.0.0:50052", "--verbose"]
    environment:
      - RUST_LOG=debug
    healthcheck:
      test: ["CMD", "grpc-health-probe", "-addr=:50052"]
      interval: 10s
      timeout: 5s
      retries: 3
    restart: unless-stopped
    profiles:
      - debug
    networks:
      - sentinel

  # ─────────────────────────────────────────────────────────
  # Example Backend
  # ─────────────────────────────────────────────────────────
  backend:
    image: nginx:alpine
    container_name: backend
    volumes:
      - ./backend/html:/usr/share/nginx/html:ro
    networks:
      - backend

volumes:
  sockets:
    driver: local

networks:
  sentinel:
    driver: bridge
  backend:
    driver: bridge
    internal: true
```

### config/sentinel.kdl

```kdl
server {
    listen "0.0.0.0:8080"
    listen "0.0.0.0:8443" {
        tls {
            cert "/etc/sentinel/tls/cert.pem"
            key "/etc/sentinel/tls/key.pem"
        }
    }
}

admin {
    listen "0.0.0.0:9090"
}

agents {
    agent "auth" type="auth" {
        unix-socket "/var/run/sentinel/auth.sock"
        events "request_headers"
        timeout-ms 50
        failure-mode "closed"
    }

    agent "waf" type="waf" {
        grpc "http://waf-agent:50051"
        events "request_headers" "request_body"
        timeout-ms 100
        failure-mode "open"
        max-request-body-bytes 1048576
    }

    agent "echo" type="custom" {
        grpc "http://echo-agent:50052"
        events "request_headers"
        timeout-ms 50
        failure-mode "open"
    }
}

upstreams {
    upstream "backend" {
        target "backend:80"
    }
}

routes {
    route "api" {
        matches { path-prefix "/api/" }
        upstream "backend"
        agents "auth" "waf"
    }

    route "default" {
        matches { path-prefix "/" }
        upstream "backend"
        agents "echo"
    }
}
```

## Development Setup

### Hot Reload with Local Build

```yaml
# docker-compose.dev.yml
version: "3.8"

services:
  sentinel:
    build:
      context: ../sentinel
      dockerfile: Dockerfile
    volumes:
      - ./config:/etc/sentinel:ro
      - sockets:/var/run/sentinel
    environment:
      - RUST_LOG=debug
    ports:
      - "8080:8080"
      - "9090:9090"

  auth-agent:
    build:
      context: ../sentinel
      dockerfile: agents/auth/Dockerfile
    volumes:
      - sockets:/var/run/sentinel
    command: ["--socket", "/var/run/sentinel/auth.sock"]

volumes:
  sockets:
```

```bash
# Build and run in development
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

### Debug Profile

```bash
# Start with echo agent for debugging
docker-compose --profile debug up -d

# Test with echo headers
curl -v http://localhost:8080/test
```

## Scaling

### Scale Agents

```bash
# Scale WAF agent replicas
docker-compose up -d --scale waf-agent=3
```

With load balancing in config:

```kdl
agent "waf" type="waf" {
    // Docker DNS handles round-robin
    grpc "http://waf-agent:50051"
}
```

### Multiple Sentinel Instances

```yaml
services:
  sentinel-1:
    image: ghcr.io/raskell-io/sentinel:latest
    ports:
      - "8081:8080"

  sentinel-2:
    image: ghcr.io/raskell-io/sentinel:latest
    ports:
      - "8082:8080"

  # HAProxy or Traefik in front
  lb:
    image: haproxy:latest
    ports:
      - "80:80"
    depends_on:
      - sentinel-1
      - sentinel-2
```

## Resource Limits

```yaml
services:
  sentinel:
    deploy:
      resources:
        limits:
          cpus: "2"
          memory: 1G
        reservations:
          cpus: "0.5"
          memory: 256M

  auth-agent:
    deploy:
      resources:
        limits:
          cpus: "0.5"
          memory: 128M
```

## Logging

### Centralized Logging

```yaml
services:
  sentinel:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
        labels: "service"
    labels:
      service: "sentinel-proxy"

  # Or with Loki
  sentinel:
    logging:
      driver: loki
      options:
        loki-url: "http://loki:3100/loki/api/v1/push"
        loki-batch-size: "400"
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f sentinel

# With timestamps
docker-compose logs -f -t sentinel

# Last 100 lines
docker-compose logs --tail=100 sentinel
```

## Health Checks

### Service Dependencies

```yaml
services:
  sentinel:
    depends_on:
      auth-agent:
        condition: service_healthy
      waf-agent:
        condition: service_started

  auth-agent:
    healthcheck:
      test: ["CMD", "test", "-S", "/var/run/sentinel/auth.sock"]
      interval: 5s
      timeout: 3s
      retries: 3
      start_period: 10s
```

### External Health Check

```bash
# Check Sentinel health
curl http://localhost:9090/health

# Check agent connectivity
curl http://localhost:9090/agents/health
```

## Production Considerations

### Security

```yaml
services:
  sentinel:
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
```

### Secrets Management

```yaml
services:
  auth-agent:
    secrets:
      - auth_secret
    environment:
      - AUTH_SECRET_FILE=/run/secrets/auth_secret

secrets:
  auth_secret:
    file: ./secrets/auth.key
    # Or from external source
    # external: true
```

### TLS Configuration

```yaml
services:
  sentinel:
    volumes:
      - ./certs:/etc/sentinel/tls:ro
    environment:
      - SENTINEL_TLS_CERT=/etc/sentinel/tls/cert.pem
      - SENTINEL_TLS_KEY=/etc/sentinel/tls/key.pem
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker-compose logs auth-agent

# Run interactively
docker-compose run --rm auth-agent sh

# Check if socket exists
docker-compose exec sentinel ls -la /var/run/sentinel/
```

### Agent Connection Failed

```bash
# Check network connectivity
docker-compose exec sentinel ping waf-agent

# Test gRPC connection
docker-compose exec sentinel grpcurl -plaintext waf-agent:50051 list

# Check socket permissions
docker-compose exec sentinel ls -la /var/run/sentinel/
```

### Socket Permission Issues

```yaml
# Ensure same user in all containers
services:
  sentinel:
    user: "1000:1000"

  auth-agent:
    user: "1000:1000"
```

### Memory Issues

```bash
# Check memory usage
docker stats

# Increase limits if needed
docker-compose up -d --force-recreate
```

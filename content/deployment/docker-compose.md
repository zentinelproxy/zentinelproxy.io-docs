+++
title = "Docker Compose"
weight = 4
+++

Docker Compose provides a straightforward way to deploy Zentinel with agents as containers. This guide covers local development and small production setups.

## Overview

```
┌──────────────────────────────────────────────────────────────┐
│                    docker-compose.yml                        │
│  ┌─────────────────────────────────────────────────────────┐│
│  │                    Network: zentinel                    ││
│  │                                                         ││
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐             ││
│  │  │ zentinel │  │   auth   │  │   echo   │             ││
│  │  │  :8080   │  │  agent   │  │  agent   │             ││
│  │  │  :9090   │  │          │  │          │             ││
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘             ││
│  │       │             │             │                    ││
│  │       └─────────────┴─────────────┘                    ││
│  │                 Unix Sockets                           ││
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
  zentinel:
    image: ghcr.io/zentinelproxy/zentinel:latest
    ports:
      - "8080:8080"   # HTTP
      - "9090:9090"   # Admin
    volumes:
      - ./config:/etc/zentinel:ro
      - sockets:/var/run/zentinel
    depends_on:
      - auth-agent
      - echo-agent
    networks:
      - zentinel

  auth-agent:
    image: ghcr.io/zentinelproxy/zentinel-auth:latest
    platform: linux/amd64  # Currently AMD64 only
    environment:
      - SOCKET_PATH=/var/run/zentinel/auth.sock
    volumes:
      - sockets:/var/run/zentinel
    networks:
      - zentinel

  echo-agent:
    image: ghcr.io/zentinelproxy/zentinel-echo:latest
    environment:
      - SOCKET_PATH=/var/run/zentinel/echo.sock
    volumes:
      - sockets:/var/run/zentinel
    networks:
      - zentinel

volumes:
  sockets:

networks:
  zentinel:
```

```bash
# Start everything
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f zentinel

# Stop
docker-compose down
```

## Unix Sockets vs gRPC

### Unix Sockets (Shared Volume)

Best for lowest latency when all containers run on the same host:

```yaml
services:
  zentinel:
    volumes:
      - sockets:/var/run/zentinel

  auth-agent:
    volumes:
      - sockets:/var/run/zentinel
    environment:
      - SOCKET_PATH=/var/run/zentinel/auth.sock

volumes:
  sockets:
```

Configuration:
```kdl
agent "auth" type="auth" {
    unix-socket "/var/run/zentinel/auth.sock"
}
```

### gRPC (Network)

Best for scaling agents independently or running on different hosts:

> **Note:** The WAF agent (`zentinel-waf`) is not yet available. This example shows the planned configuration pattern for future gRPC-based agents.

```yaml
services:
  zentinel:
    depends_on:
      - custom-agent

  custom-agent:
    image: your-custom-agent:latest
    environment:
      - GRPC_ADDRESS=0.0.0.0:50051
    networks:
      - zentinel
```

Configuration:
```kdl
agent "custom" type="custom" {
    grpc "http://custom-agent:50051"
}
```

## Complete Example

### Project Structure

```
zentinel-deploy/
├── docker-compose.yml
├── config/
│   └── zentinel.kdl
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
  # Zentinel Proxy
  # ─────────────────────────────────────────────────────────
  zentinel:
    image: ghcr.io/zentinelproxy/zentinel:latest
    container_name: zentinel
    ports:
      - "80:8080"
      - "443:8443"
      - "9090:9090"
    volumes:
      - ./config:/etc/zentinel:ro
      - ./certs:/etc/zentinel/tls:ro
      - sockets:/var/run/zentinel
    environment:
      - RUST_LOG=info
    depends_on:
      - auth-agent
    restart: unless-stopped
    networks:
      - zentinel
      - backend

  # ─────────────────────────────────────────────────────────
  # Auth Agent (Unix Socket)
  # ─────────────────────────────────────────────────────────
  auth-agent:
    image: ghcr.io/zentinelproxy/zentinel-auth:latest
    platform: linux/amd64  # Currently AMD64 only
    container_name: zentinel-auth
    volumes:
      - sockets:/var/run/zentinel
      - ./agents/auth:/etc/auth:ro
    environment:
      - RUST_LOG=info
      - SOCKET_PATH=/var/run/zentinel/auth.sock
      - AUTH_SECRET=${AUTH_SECRET}
    restart: unless-stopped
    networks:
      - zentinel

  # ─────────────────────────────────────────────────────────
  # Echo Agent (for debugging)
  # ─────────────────────────────────────────────────────────
  echo-agent:
    image: ghcr.io/zentinelproxy/zentinel-echo:latest
    container_name: zentinel-echo
    volumes:
      - sockets:/var/run/zentinel
    environment:
      - RUST_LOG=debug
      - SOCKET_PATH=/var/run/zentinel/echo.sock
    restart: unless-stopped
    profiles:
      - debug
    networks:
      - zentinel

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
  zentinel:
    driver: bridge
  backend:
    driver: bridge
    internal: true
```

### config/zentinel.kdl

```kdl
system {
    listen "0.0.0.0:8080"
    listen "0.0.0.0:8443" {
        tls {
            cert "/etc/zentinel/tls/cert.pem"
            key "/etc/zentinel/tls/key.pem"
        }
    }
}

admin {
    listen "0.0.0.0:9090"
}

agents {
    agent "auth" type="auth" {
        unix-socket "/var/run/zentinel/auth.sock"
        events "request_headers"
        timeout-ms 50
        failure-mode "closed"
    }

    agent "echo" type="custom" {
        unix-socket "/var/run/zentinel/echo.sock"
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
        agents "auth"
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
  zentinel:
    build:
      context: ../zentinel
      dockerfile: Dockerfile
    volumes:
      - ./config:/etc/zentinel:ro
      - sockets:/var/run/zentinel
    environment:
      - RUST_LOG=debug
    ports:
      - "8080:8080"
      - "9090:9090"

  auth-agent:
    build:
      context: ../zentinel-agent-auth
      dockerfile: Dockerfile
    volumes:
      - sockets:/var/run/zentinel
    environment:
      - SOCKET_PATH=/var/run/zentinel/auth.sock

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

For gRPC-based agents, you can scale replicas:

```bash
# Scale agent replicas (for gRPC-based agents)
docker-compose up -d --scale custom-agent=3
```

With load balancing in config:

```kdl
agent "custom" type="custom" {
    // Docker DNS handles round-robin
    grpc "http://custom-agent:50051"
}
```

> **Note:** Unix socket-based agents cannot be scaled via `--scale` as they bind to a specific socket path.

### Multiple Zentinel Instances

```yaml
services:
  zentinel-1:
    image: ghcr.io/zentinelproxy/zentinel:latest
    ports:
      - "8081:8080"

  zentinel-2:
    image: ghcr.io/zentinelproxy/zentinel:latest
    ports:
      - "8082:8080"

  # HAProxy or Traefik in front
  lb:
    image: haproxy:latest
    ports:
      - "80:80"
    depends_on:
      - zentinel-1
      - zentinel-2
```

## Resource Limits

```yaml
services:
  zentinel:
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
  zentinel:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
        labels: "service"
    labels:
      service: "zentinel-proxy"

  # Or with Loki
  zentinel:
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
docker-compose logs -f zentinel

# With timestamps
docker-compose logs -f -t zentinel

# Last 100 lines
docker-compose logs --tail=100 zentinel
```

## Health Checks

### Service Dependencies

The default agent images use distroless containers without shell access, so traditional health checks (`test -S`, `curl`) are not available. Use one of these approaches:

**Option 1: Simple depends_on (recommended for most cases)**
```yaml
services:
  zentinel:
    depends_on:
      - auth-agent
      - echo-agent
```

**Option 2: Use the debug image (Alpine-based, has shell)**
```yaml
services:
  auth-agent:
    image: ghcr.io/zentinelproxy/zentinel-auth:latest-debug
    healthcheck:
      test: ["CMD", "test", "-S", "/var/run/zentinel/auth.sock"]
      interval: 5s
      timeout: 3s
      retries: 3
      start_period: 10s
```

### External Health Check

```bash
# Check Zentinel health
curl http://localhost:9090/health

# Check if socket exists (from host)
docker-compose exec zentinel ls -la /var/run/zentinel/
```

## Production Considerations

### Security

```yaml
services:
  zentinel:
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
  zentinel:
    volumes:
      - ./certs:/etc/zentinel/tls:ro
    environment:
      - ZENTINEL_TLS_CERT=/etc/zentinel/tls/cert.pem
      - ZENTINEL_TLS_KEY=/etc/zentinel/tls/key.pem
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker-compose logs auth-agent

# Check if socket exists
docker-compose exec zentinel ls -la /var/run/zentinel/
```

> **Note:** The default agent images are distroless and don't have a shell. You cannot use `docker-compose run --rm agent sh`. Use the debug images if you need shell access.

### Agent Connection Failed

```bash
# Check socket exists
docker-compose exec zentinel ls -la /var/run/zentinel/

# Check agent logs for connection errors
docker-compose logs auth-agent
docker-compose logs echo-agent
```

### Socket Permission Issues

```yaml
# Ensure same user in all containers
services:
  zentinel:
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

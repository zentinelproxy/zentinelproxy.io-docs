+++
title = "Docker Deployment"
weight = 4
updated = 2026-02-19
+++

Running Zentinel and agents in Docker containers.

## Quick Start

### Run Zentinel

```bash
# Run with default configuration
docker run -d \
    --name zentinel \
    -p 8080:8080 \
    -p 9090:9090 \
    -v $(pwd)/zentinel.kdl:/etc/zentinel/zentinel.kdl:ro \
    ghcr.io/zentinelproxy/zentinel:latest

# Check status
docker logs zentinel
curl http://localhost:9090/health
```

### Run with Agents

```bash
# Create shared socket directory
mkdir -p /tmp/zentinel-sockets

# Run WAF agent
docker run -d \
    --name waf-agent \
    -v /tmp/zentinel-sockets:/var/run/zentinel \
    ghcr.io/zentinelproxy/zentinel-agent-waf:latest \
    --socket /var/run/zentinel/waf.sock

# Run Zentinel
docker run -d \
    --name zentinel \
    -p 8080:8080 \
    -v $(pwd)/zentinel.kdl:/etc/zentinel/zentinel.kdl:ro \
    -v /tmp/zentinel-sockets:/var/run/zentinel \
    ghcr.io/zentinelproxy/zentinel:latest
```

## Container Configuration

### Environment Variables

```bash
docker run -d \
    --name zentinel \
    -e RUST_LOG=zentinel=info \
    -e ZENTINEL_WORKERS=4 \
    -e BACKEND_ADDR=api.example.com:443 \
    -p 8080:8080 \
    -v $(pwd)/zentinel.kdl:/etc/zentinel/zentinel.kdl:ro \
    ghcr.io/zentinelproxy/zentinel:latest
```

> **Note:** If your backend serves HTTPS (port 443), your `zentinel.kdl` must include a `tls` block in the upstream configuration. Without it, Zentinel connects with plaintext HTTP, causing 502 errors or redirect loops. See [Upstream TLS](/configuration/upstreams/#upstream-tls) for details.

### Volume Mounts

| Mount | Purpose |
|-------|---------|
| `/etc/zentinel/zentinel.kdl` | Main configuration |
| `/etc/zentinel/certs/` | TLS certificates |
| `/var/run/zentinel/` | Unix sockets for agents |
| `/var/log/zentinel/` | Log files (optional) |

```bash
docker run -d \
    --name zentinel \
    -v $(pwd)/config:/etc/zentinel:ro \
    -v $(pwd)/certs:/etc/zentinel/certs:ro \
    -v zentinel-sockets:/var/run/zentinel \
    -v zentinel-logs:/var/log/zentinel \
    ghcr.io/zentinelproxy/zentinel:latest
```

### Port Mapping

```bash
docker run -d \
    --name zentinel \
    -p 80:8080 \      # HTTP
    -p 443:8443 \     # HTTPS
    -p 9090:9090 \    # Metrics
    ghcr.io/zentinelproxy/zentinel:latest
```

## Networking

### Bridge Network (Default)

```bash
# Create network
docker network create zentinel-net

# Run containers on network
docker run -d --name backend --network zentinel-net nginx

docker run -d \
    --name zentinel \
    --network zentinel-net \
    -p 8080:8080 \
    ghcr.io/zentinelproxy/zentinel:latest
```

### Host Network

For lowest latency (Linux only):

```bash
docker run -d \
    --name zentinel \
    --network host \
    ghcr.io/zentinelproxy/zentinel:latest
```

### Connecting to Host Services

```bash
# Linux
docker run -d \
    --name zentinel \
    --add-host=host.docker.internal:host-gateway \
    ghcr.io/zentinelproxy/zentinel:latest

# In zentinel.kdl
upstreams {
    upstream "backend" {
        targets {
            target { address "host.docker.internal:3000" }
        }
    }
}
```

## Running Agents

### WAF Agent

```bash
docker run -d \
    --name waf-agent \
    -v zentinel-sockets:/var/run/zentinel \
    ghcr.io/zentinelproxy/zentinel-agent-waf:latest \
    --socket /var/run/zentinel/waf.sock \
    --paranoia-level 1 \
    --block-mode true
```

### Auth Agent

```bash
docker run -d \
    --name auth-agent \
    -v zentinel-sockets:/var/run/zentinel \
    -e JWT_SECRET="${JWT_SECRET}" \
    ghcr.io/zentinelproxy/zentinel-agent-auth:latest \
    --socket /var/run/zentinel/auth.sock \
    --jwt-issuer api.example.com
```

### Rate Limit Agent

```bash
docker run -d \
    --name ratelimit-agent \
    -v zentinel-sockets:/var/run/zentinel \
    ghcr.io/zentinelproxy/zentinel-agent-ratelimit:latest \
    --socket /var/run/zentinel/ratelimit.sock \
    --requests-per-minute 100
```

### JavaScript Agent

```bash
docker run -d \
    --name js-agent \
    -v zentinel-sockets:/var/run/zentinel \
    -v $(pwd)/scripts:/scripts:ro \
    ghcr.io/zentinelproxy/zentinel-agent-js:latest \
    --socket /var/run/zentinel/js.sock \
    --script /scripts/policy.js
```

## Resource Limits

### Memory and CPU

```bash
docker run -d \
    --name zentinel \
    --memory=512m \
    --memory-reservation=256m \
    --cpus=2 \
    ghcr.io/zentinelproxy/zentinel:latest
```

### File Descriptors

```bash
docker run -d \
    --name zentinel \
    --ulimit nofile=65536:65536 \
    ghcr.io/zentinelproxy/zentinel:latest
```

## Health Checks

### Built-in Health Check

```bash
docker run -d \
    --name zentinel \
    --health-cmd="curl -f http://localhost:9090/health || exit 1" \
    --health-interval=30s \
    --health-timeout=3s \
    --health-retries=3 \
    --health-start-period=5s \
    ghcr.io/zentinelproxy/zentinel:latest
```

### Check Health Status

```bash
# View health status
docker inspect --format='{{.State.Health.Status}}' zentinel

# View health logs
docker inspect --format='{{json .State.Health}}' zentinel | jq
```

## Logging

### Log Drivers

```bash
# JSON file (default)
docker run -d \
    --log-driver json-file \
    --log-opt max-size=100m \
    --log-opt max-file=3 \
    --name zentinel \
    ghcr.io/zentinelproxy/zentinel:latest

# Syslog
docker run -d \
    --log-driver syslog \
    --log-opt syslog-address=udp://loghost:514 \
    --name zentinel \
    ghcr.io/zentinelproxy/zentinel:latest

# Fluentd
docker run -d \
    --log-driver fluentd \
    --log-opt fluentd-address=localhost:24224 \
    --log-opt tag=zentinel \
    --name zentinel \
    ghcr.io/zentinelproxy/zentinel:latest
```

### View Logs

```bash
# Follow logs
docker logs -f zentinel

# Last 100 lines
docker logs --tail 100 zentinel

# With timestamps
docker logs -t zentinel
```

## Security

### Read-Only Root Filesystem

```bash
docker run -d \
    --name zentinel \
    --read-only \
    --tmpfs /tmp \
    -v zentinel-sockets:/var/run/zentinel \
    ghcr.io/zentinelproxy/zentinel:latest
```

### Security Options

```bash
docker run -d \
    --name zentinel \
    --security-opt no-new-privileges:true \
    --cap-drop ALL \
    --cap-add NET_BIND_SERVICE \
    ghcr.io/zentinelproxy/zentinel:latest
```

### User Namespace

```bash
docker run -d \
    --name zentinel \
    --userns=host \
    --user 1000:1000 \
    ghcr.io/zentinelproxy/zentinel:latest
```

## Restart Policies

```bash
# Always restart
docker run -d \
    --name zentinel \
    --restart always \
    ghcr.io/zentinelproxy/zentinel:latest

# Restart on failure (max 3 times)
docker run -d \
    --name zentinel \
    --restart on-failure:3 \
    ghcr.io/zentinelproxy/zentinel:latest

# Unless stopped manually
docker run -d \
    --name zentinel \
    --restart unless-stopped \
    ghcr.io/zentinelproxy/zentinel:latest
```

## Configuration Reload

### Using Docker Exec

```bash
# Reload configuration
docker exec zentinel kill -HUP 1

# Or via admin API
docker exec zentinel curl -X POST http://localhost:9090/admin/reload
```

### Updating Configuration

```bash
# Update config file
docker cp zentinel.kdl zentinel:/etc/zentinel/zentinel.kdl

# Reload
docker exec zentinel kill -HUP 1
```

## Debugging

### Interactive Shell

```bash
# Start shell in running container
docker exec -it zentinel /bin/sh

# Start new container with shell
docker run -it --rm \
    -v $(pwd)/zentinel.kdl:/etc/zentinel/zentinel.kdl:ro \
    ghcr.io/zentinelproxy/zentinel:latest \
    /bin/sh
```

### Inspect Container

```bash
# View configuration
docker inspect zentinel

# View mounts
docker inspect --format='{{json .Mounts}}' zentinel | jq

# View network settings
docker inspect --format='{{json .NetworkSettings}}' zentinel | jq
```

### Debug Mode

```bash
docker run -d \
    --name zentinel \
    -e RUST_LOG=zentinel=debug,tower=debug \
    -e RUST_BACKTRACE=1 \
    ghcr.io/zentinelproxy/zentinel:latest
```

## Production Checklist

### Container Configuration

- [ ] Resource limits set (memory, CPU)
- [ ] File descriptor limits increased
- [ ] Health check configured
- [ ] Restart policy set
- [ ] Logging configured
- [ ] Read-only root filesystem (if possible)

### Security

- [ ] Running as non-root user
- [ ] Capabilities dropped
- [ ] No new privileges
- [ ] Secrets not in environment variables (use Docker secrets)

### Networking

- [ ] Appropriate network mode selected
- [ ] Only required ports exposed
- [ ] TLS certificates mounted

### Monitoring

- [ ] Metrics port exposed
- [ ] Log aggregation configured
- [ ] Health checks monitored

## Next Steps

- [Docker Compose](../docker-compose/) - Multi-container orchestration
- [Monitoring](../monitoring/) - Observability setup
- [Rolling Updates](../rolling-updates/) - Zero-downtime deployments

+++
title = "Docker Deployment"
weight = 4
+++

Running Sentinel and agents in Docker containers.

## Quick Start

### Run Sentinel

```bash
# Run with default configuration
docker run -d \
    --name sentinel \
    -p 8080:8080 \
    -p 9090:9090 \
    -v $(pwd)/sentinel.kdl:/etc/sentinel/sentinel.kdl:ro \
    ghcr.io/raskell-io/sentinel:latest

# Check status
docker logs sentinel
curl http://localhost:9090/health
```

### Run with Agents

```bash
# Create shared socket directory
mkdir -p /tmp/sentinel-sockets

# Run WAF agent
docker run -d \
    --name waf-agent \
    -v /tmp/sentinel-sockets:/var/run/sentinel \
    ghcr.io/raskell-io/sentinel-agent-waf:latest \
    --socket /var/run/sentinel/waf.sock

# Run Sentinel
docker run -d \
    --name sentinel \
    -p 8080:8080 \
    -v $(pwd)/sentinel.kdl:/etc/sentinel/sentinel.kdl:ro \
    -v /tmp/sentinel-sockets:/var/run/sentinel \
    ghcr.io/raskell-io/sentinel:latest
```

## Container Configuration

### Environment Variables

```bash
docker run -d \
    --name sentinel \
    -e RUST_LOG=sentinel=info \
    -e SENTINEL_WORKERS=4 \
    -e BACKEND_ADDR=api.example.com:443 \
    -p 8080:8080 \
    -v $(pwd)/sentinel.kdl:/etc/sentinel/sentinel.kdl:ro \
    ghcr.io/raskell-io/sentinel:latest
```

### Volume Mounts

| Mount | Purpose |
|-------|---------|
| `/etc/sentinel/sentinel.kdl` | Main configuration |
| `/etc/sentinel/certs/` | TLS certificates |
| `/var/run/sentinel/` | Unix sockets for agents |
| `/var/log/sentinel/` | Log files (optional) |

```bash
docker run -d \
    --name sentinel \
    -v $(pwd)/config:/etc/sentinel:ro \
    -v $(pwd)/certs:/etc/sentinel/certs:ro \
    -v sentinel-sockets:/var/run/sentinel \
    -v sentinel-logs:/var/log/sentinel \
    ghcr.io/raskell-io/sentinel:latest
```

### Port Mapping

```bash
docker run -d \
    --name sentinel \
    -p 80:8080 \      # HTTP
    -p 443:8443 \     # HTTPS
    -p 9090:9090 \    # Metrics
    ghcr.io/raskell-io/sentinel:latest
```

## Networking

### Bridge Network (Default)

```bash
# Create network
docker network create sentinel-net

# Run containers on network
docker run -d --name backend --network sentinel-net nginx

docker run -d \
    --name sentinel \
    --network sentinel-net \
    -p 8080:8080 \
    ghcr.io/raskell-io/sentinel:latest
```

### Host Network

For lowest latency (Linux only):

```bash
docker run -d \
    --name sentinel \
    --network host \
    ghcr.io/raskell-io/sentinel:latest
```

### Connecting to Host Services

```bash
# Linux
docker run -d \
    --name sentinel \
    --add-host=host.docker.internal:host-gateway \
    ghcr.io/raskell-io/sentinel:latest

# In sentinel.kdl
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
    -v sentinel-sockets:/var/run/sentinel \
    ghcr.io/raskell-io/sentinel-agent-waf:latest \
    --socket /var/run/sentinel/waf.sock \
    --paranoia-level 1 \
    --block-mode true
```

### Auth Agent

```bash
docker run -d \
    --name auth-agent \
    -v sentinel-sockets:/var/run/sentinel \
    -e JWT_SECRET="${JWT_SECRET}" \
    ghcr.io/raskell-io/sentinel-agent-auth:latest \
    --socket /var/run/sentinel/auth.sock \
    --jwt-issuer api.example.com
```

### Rate Limit Agent

```bash
docker run -d \
    --name ratelimit-agent \
    -v sentinel-sockets:/var/run/sentinel \
    ghcr.io/raskell-io/sentinel-agent-ratelimit:latest \
    --socket /var/run/sentinel/ratelimit.sock \
    --requests-per-minute 100
```

### JavaScript Agent

```bash
docker run -d \
    --name js-agent \
    -v sentinel-sockets:/var/run/sentinel \
    -v $(pwd)/scripts:/scripts:ro \
    ghcr.io/raskell-io/sentinel-agent-js:latest \
    --socket /var/run/sentinel/js.sock \
    --script /scripts/policy.js
```

## Resource Limits

### Memory and CPU

```bash
docker run -d \
    --name sentinel \
    --memory=512m \
    --memory-reservation=256m \
    --cpus=2 \
    ghcr.io/raskell-io/sentinel:latest
```

### File Descriptors

```bash
docker run -d \
    --name sentinel \
    --ulimit nofile=65536:65536 \
    ghcr.io/raskell-io/sentinel:latest
```

## Health Checks

### Built-in Health Check

```bash
docker run -d \
    --name sentinel \
    --health-cmd="curl -f http://localhost:9090/health || exit 1" \
    --health-interval=30s \
    --health-timeout=3s \
    --health-retries=3 \
    --health-start-period=5s \
    ghcr.io/raskell-io/sentinel:latest
```

### Check Health Status

```bash
# View health status
docker inspect --format='{{.State.Health.Status}}' sentinel

# View health logs
docker inspect --format='{{json .State.Health}}' sentinel | jq
```

## Logging

### Log Drivers

```bash
# JSON file (default)
docker run -d \
    --log-driver json-file \
    --log-opt max-size=100m \
    --log-opt max-file=3 \
    --name sentinel \
    ghcr.io/raskell-io/sentinel:latest

# Syslog
docker run -d \
    --log-driver syslog \
    --log-opt syslog-address=udp://loghost:514 \
    --name sentinel \
    ghcr.io/raskell-io/sentinel:latest

# Fluentd
docker run -d \
    --log-driver fluentd \
    --log-opt fluentd-address=localhost:24224 \
    --log-opt tag=sentinel \
    --name sentinel \
    ghcr.io/raskell-io/sentinel:latest
```

### View Logs

```bash
# Follow logs
docker logs -f sentinel

# Last 100 lines
docker logs --tail 100 sentinel

# With timestamps
docker logs -t sentinel
```

## Security

### Read-Only Root Filesystem

```bash
docker run -d \
    --name sentinel \
    --read-only \
    --tmpfs /tmp \
    -v sentinel-sockets:/var/run/sentinel \
    ghcr.io/raskell-io/sentinel:latest
```

### Security Options

```bash
docker run -d \
    --name sentinel \
    --security-opt no-new-privileges:true \
    --cap-drop ALL \
    --cap-add NET_BIND_SERVICE \
    ghcr.io/raskell-io/sentinel:latest
```

### User Namespace

```bash
docker run -d \
    --name sentinel \
    --userns=host \
    --user 1000:1000 \
    ghcr.io/raskell-io/sentinel:latest
```

## Restart Policies

```bash
# Always restart
docker run -d \
    --name sentinel \
    --restart always \
    ghcr.io/raskell-io/sentinel:latest

# Restart on failure (max 3 times)
docker run -d \
    --name sentinel \
    --restart on-failure:3 \
    ghcr.io/raskell-io/sentinel:latest

# Unless stopped manually
docker run -d \
    --name sentinel \
    --restart unless-stopped \
    ghcr.io/raskell-io/sentinel:latest
```

## Configuration Reload

### Using Docker Exec

```bash
# Reload configuration
docker exec sentinel kill -HUP 1

# Or via admin API
docker exec sentinel curl -X POST http://localhost:9090/admin/reload
```

### Updating Configuration

```bash
# Update config file
docker cp sentinel.kdl sentinel:/etc/sentinel/sentinel.kdl

# Reload
docker exec sentinel kill -HUP 1
```

## Debugging

### Interactive Shell

```bash
# Start shell in running container
docker exec -it sentinel /bin/sh

# Start new container with shell
docker run -it --rm \
    -v $(pwd)/sentinel.kdl:/etc/sentinel/sentinel.kdl:ro \
    ghcr.io/raskell-io/sentinel:latest \
    /bin/sh
```

### Inspect Container

```bash
# View configuration
docker inspect sentinel

# View mounts
docker inspect --format='{{json .Mounts}}' sentinel | jq

# View network settings
docker inspect --format='{{json .NetworkSettings}}' sentinel | jq
```

### Debug Mode

```bash
docker run -d \
    --name sentinel \
    -e RUST_LOG=sentinel=debug,tower=debug \
    -e RUST_BACKTRACE=1 \
    ghcr.io/raskell-io/sentinel:latest
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

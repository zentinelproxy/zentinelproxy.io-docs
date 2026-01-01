+++
title = "Building Images"
weight = 2
+++

Build optimized Docker images for Sentinel and agents.

## Official Images

Pre-built images are available:

```bash
# Sentinel proxy
docker pull ghcr.io/raskell-io/sentinel:latest
docker pull ghcr.io/raskell-io/sentinel:1.0.0

# Agents
docker pull ghcr.io/raskell-io/sentinel-agent-waf:latest
docker pull ghcr.io/raskell-io/sentinel-agent-auth:latest
docker pull ghcr.io/raskell-io/sentinel-agent-ratelimit:latest
docker pull ghcr.io/raskell-io/sentinel-agent-js:latest
```

## Building Sentinel

### Basic Dockerfile

```dockerfile
# Dockerfile
FROM rust:1.75-bookworm as builder

WORKDIR /app
COPY . .

RUN cargo build --release

FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y \
    ca-certificates \
    libssl3 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/target/release/sentinel /usr/local/bin/

EXPOSE 8080 8443 9090

ENTRYPOINT ["sentinel"]
CMD ["-c", "/etc/sentinel/sentinel.kdl"]
```

Build:

```bash
docker build -t sentinel:latest .
```

### Optimized Multi-Stage Build

```dockerfile
# Dockerfile.optimized
FROM rust:1.75-bookworm as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    pkg-config \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN useradd --create-home --uid 1000 sentinel

WORKDIR /app

# Cache dependencies
COPY Cargo.toml Cargo.lock ./
RUN mkdir src && echo "fn main() {}" > src/main.rs
RUN cargo build --release && rm -rf src target/release/deps/sentinel*

# Build actual application
COPY src ./src
RUN cargo build --release

# Runtime stage
FROM debian:bookworm-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    ca-certificates \
    libssl3 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 sentinel

# Copy binary
COPY --from=builder /app/target/release/sentinel /usr/local/bin/

# Create config directory
RUN mkdir -p /etc/sentinel && chown sentinel:sentinel /etc/sentinel

USER sentinel

EXPOSE 8080 8443 9090

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s \
    CMD curl -f http://localhost:9090/health || exit 1

ENTRYPOINT ["sentinel"]
CMD ["-c", "/etc/sentinel/sentinel.kdl"]
```

### Alpine-Based (Smaller)

```dockerfile
# Dockerfile.alpine
FROM rust:1.75-alpine as builder

RUN apk add --no-cache musl-dev openssl-dev pkgconfig

WORKDIR /app
COPY . .

RUN cargo build --release --target x86_64-unknown-linux-musl

FROM alpine:3.19

RUN apk add --no-cache ca-certificates libssl3 curl

COPY --from=builder /app/target/x86_64-unknown-linux-musl/release/sentinel \
    /usr/local/bin/

RUN adduser -D -u 1000 sentinel
USER sentinel

EXPOSE 8080 8443 9090

ENTRYPOINT ["sentinel"]
CMD ["-c", "/etc/sentinel/sentinel.kdl"]
```

### Distroless (Minimal Attack Surface)

```dockerfile
# Dockerfile.distroless
FROM rust:1.75-bookworm as builder

WORKDIR /app
COPY . .

RUN cargo build --release

FROM gcr.io/distroless/cc-debian12

COPY --from=builder /app/target/release/sentinel /sentinel

EXPOSE 8080 8443 9090

ENTRYPOINT ["/sentinel"]
CMD ["-c", "/etc/sentinel/sentinel.kdl"]
```

## Building Agents

### WAF Agent

```dockerfile
# Dockerfile.waf
FROM rust:1.75-bookworm as builder

WORKDIR /app
COPY . .

RUN cargo build --release

FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 agent

COPY --from=builder /app/target/release/sentinel-agent-waf /usr/local/bin/

USER agent

ENTRYPOINT ["sentinel-agent-waf"]
CMD ["--socket", "/var/run/sentinel/waf.sock"]
```

### ModSecurity Agent

```dockerfile
# Dockerfile.modsec
FROM rust:1.75-bookworm as builder

# Install libmodsecurity
RUN apt-get update && apt-get install -y \
    libmodsecurity-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

RUN cargo build --release

FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y \
    ca-certificates \
    libmodsecurity3 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 agent

COPY --from=builder /app/target/release/sentinel-agent-modsec /usr/local/bin/

# Copy OWASP CRS rules
COPY --from=owasp/modsecurity-crs:3.3.5 /opt/owasp-crs /opt/owasp-crs

USER agent

ENTRYPOINT ["sentinel-agent-modsec"]
```

### JavaScript Agent

```dockerfile
# Dockerfile.js
FROM rust:1.75-bookworm as builder

WORKDIR /app
COPY . .

RUN cargo build --release

FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 agent

COPY --from=builder /app/target/release/sentinel-agent-js /usr/local/bin/

USER agent

ENTRYPOINT ["sentinel-agent-js"]
```

## Multi-Architecture Builds

### Using Docker Buildx

```bash
# Create builder
docker buildx create --name multiarch --use

# Build for multiple architectures
docker buildx build \
    --platform linux/amd64,linux/arm64 \
    -t ghcr.io/raskell-io/sentinel:latest \
    --push \
    .
```

### Dockerfile for Multi-Arch

```dockerfile
# Dockerfile.multiarch
FROM --platform=$BUILDPLATFORM rust:1.75-bookworm as builder

ARG TARGETPLATFORM
ARG BUILDPLATFORM

# Install cross-compilation tools
RUN case "$TARGETPLATFORM" in \
    "linux/arm64") \
        apt-get update && apt-get install -y gcc-aarch64-linux-gnu \
        && rustup target add aarch64-unknown-linux-gnu \
        ;; \
    esac

WORKDIR /app
COPY . .

RUN case "$TARGETPLATFORM" in \
    "linux/amd64") cargo build --release ;; \
    "linux/arm64") \
        CARGO_TARGET_AARCH64_UNKNOWN_LINUX_GNU_LINKER=aarch64-linux-gnu-gcc \
        cargo build --release --target aarch64-unknown-linux-gnu \
        && mv target/aarch64-unknown-linux-gnu/release/sentinel target/release/ \
        ;; \
    esac

FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y \
    ca-certificates libssl3 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/target/release/sentinel /usr/local/bin/

ENTRYPOINT ["sentinel"]
```

## CI/CD Integration

### GitHub Actions

```yaml
# .github/workflows/docker.yml
name: Build Docker Image

on:
  push:
    tags: ['v*']
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to GHCR
        if: github.event_name != 'pull_request'
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=sha

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          platforms: linux/amd64,linux/arm64
          push: ${{ github.event_name != 'pull_request' }}
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

## Image Size Optimization

### Comparison

| Base Image | Size | Security |
|------------|------|----------|
| debian:bookworm | ~150MB | Good |
| debian:bookworm-slim | ~80MB | Good |
| alpine:3.19 | ~50MB | Good |
| distroless | ~30MB | Excellent |

### Reducing Size

```dockerfile
# Use multi-stage builds
FROM rust:1.75 as builder
# ... build steps ...

# Minimize runtime image
FROM debian:bookworm-slim

# Only install required packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Use COPY instead of ADD
COPY --from=builder /app/target/release/sentinel /usr/local/bin/

# Strip binary (if not using LTO)
RUN strip /usr/local/bin/sentinel
```

### Using cargo-strip

```dockerfile
FROM rust:1.75 as builder

RUN cargo install cargo-strip

WORKDIR /app
COPY . .

RUN cargo build --release \
    && cargo strip --target release
```

## Security Best Practices

### Non-Root User

```dockerfile
# Create user at build time
RUN useradd --create-home --uid 1000 sentinel

# Copy files with correct ownership
COPY --from=builder --chown=sentinel:sentinel \
    /app/target/release/sentinel /usr/local/bin/

# Switch to non-root user
USER sentinel
```

### Read-Only Filesystem

```dockerfile
# In docker-compose.yml or K8s
security_context:
  read_only_root_filesystem: true

# Mount writable directories
volumes:
  - /var/run/sentinel  # For Unix sockets
  - /tmp               # For temp files
```

### Scanning Images

```bash
# Scan for vulnerabilities
docker scout cves sentinel:latest

# Or use Trivy
trivy image sentinel:latest
```

## Registry Setup

### GitHub Container Registry

```bash
# Login
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# Push
docker push ghcr.io/raskell-io/sentinel:latest
```

### Private Registry

```bash
# Tag for private registry
docker tag sentinel:latest registry.example.com/sentinel:latest

# Push
docker push registry.example.com/sentinel:latest
```

## Next Steps

- [Docker Deployment](../docker/) - Run Sentinel in Docker
- [Docker Compose](../docker-compose/) - Multi-container setup
- [Kubernetes](../kubernetes/) - Production deployment

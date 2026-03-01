+++
title = "Installation"
weight = 1
updated = 2026-02-19
+++

Zentinel can be installed via the install script, from pre-built binaries, built from source, or run as an OCI container.

## Install Script (Recommended)

The easiest way to install Zentinel is using the install script, which automatically detects your OS and architecture:

```bash
curl -fsSL https://get.zentinelproxy.io | sh
```

The script downloads the appropriate binary and installs it to `~/.local/bin`. You may need to add this to your PATH:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Add this line to your shell profile (`~/.bashrc`, `~/.zshrc`, etc.) to make it permanent.

### Verify Installation

```bash
zentinel --version
```

## Install with Bundled Agents

For production deployments, you'll likely want the proxy plus agents (WAF, rate limiting, denylist). The bundle command installs everything together:

```bash
# First install Zentinel
curl -fsSL https://get.zentinelproxy.io | sh

# Then install bundled agents
sudo zentinel bundle install
```

This downloads and installs:
- **WAF agent** - ModSecurity-based web application firewall
- **Ratelimit agent** - Token bucket rate limiting
- **Denylist agent** - IP and path blocking

Check installation status:

```bash
zentinel bundle status
```

For detailed bundle documentation, see [Deploying with Agents](/docs/deployment/zentinel-stack/).

## Pre-built Binaries

Alternatively, download binaries manually from [GitHub Releases](https://github.com/zentinelproxy/zentinel/releases).

**Supported platforms:**
- Linux x86_64 (amd64)
- Linux ARM64 (aarch64)
- macOS Apple Silicon (arm64)
- macOS Intel (amd64)

Download the archive for your platform from the [latest release](https://github.com/zentinelproxy/zentinel/releases), extract, and install:

```bash
# Example for Linux amd64 — replace version and platform as needed
curl -LO https://github.com/zentinelproxy/zentinel/releases/download/26.02_4/zentinel-26.02_4-linux-amd64.tar.gz
tar xzf zentinel-26.02_4-linux-amd64.tar.gz
sudo mv zentinel /usr/local/bin/
```

## Build from Source

Building from source requires Rust 1.85 or later.

### Prerequisites

```bash
# Install Rust via rustup
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Ensure you have Rust 1.85+
rustup update stable
```

### Clone and Build

```bash
git clone https://github.com/zentinelproxy/zentinel.git
cd zentinel
cargo build --release
```

The binary will be at `target/release/zentinel`.

### Install System-wide

```bash
sudo cp target/release/zentinel /usr/local/bin/
```

## OCI Container

Zentinel provides official OCI container images.

### Pull the Image

```bash
# Using Docker
docker pull ghcr.io/zentinelproxy/zentinel:latest

# Using Podman
podman pull ghcr.io/zentinelproxy/zentinel:latest
```

### Run the Container

```bash
# Using Docker
docker run -d \
  --name zentinel \
  -p 8080:8080 \
  -p 9090:9090 \
  -v $(pwd)/zentinel.kdl:/etc/zentinel/zentinel.kdl:ro \
  ghcr.io/zentinelproxy/zentinel:latest

# Using Podman
podman run -d \
  --name zentinel \
  -p 8080:8080 \
  -p 9090:9090 \
  -v $(pwd)/zentinel.kdl:/etc/zentinel/zentinel.kdl:ro \
  ghcr.io/zentinelproxy/zentinel:latest
```

### Compose File

Works with both Docker Compose and Podman Compose:

```yaml
version: '3.8'

services:
  zentinel:
    image: ghcr.io/zentinelproxy/zentinel:latest
    ports:
      - "8080:8080"   # HTTP proxy
      - "9090:9090"   # Metrics
    volumes:
      - ./zentinel.kdl:/etc/zentinel/zentinel.kdl:ro
      - ./certs:/etc/zentinel/certs:ro
    restart: unless-stopped
```

Run with:

```bash
# Docker Compose
docker compose up -d

# Podman Compose
podman-compose up -d
```

## Configuration File Location

By default, Zentinel looks for configuration in these locations:

1. Path specified with `-c` or `--config` flag
2. `./zentinel.kdl` (current directory)
3. `/etc/zentinel/zentinel.kdl`

### Create a Basic Config

```bash
mkdir -p /etc/zentinel
cat > /etc/zentinel/zentinel.kdl << 'EOF'
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
    route "default" {
        matches {
            path-prefix "/"
        }
        upstream "backend"
    }
}

upstreams {
    upstream "backend" {
        targets {
            target {
                address "127.0.0.1:3000"
            }
        }
    }
}
EOF
```

## Running Zentinel

### Basic Usage

```bash
# Run with default config location
zentinel

# Run with specific config file
zentinel -c /path/to/zentinel.kdl

# Validate config without running
zentinel -c zentinel.kdl --test

# Run with verbose logging
zentinel -c zentinel.kdl --log-level debug
```

### Command Line Options

| Option | Description |
|--------|-------------|
| `-c, --config <FILE>` | Path to configuration file |
| `-t, --test` | Test configuration and exit |
| `--log-level <LEVEL>` | Log level (trace, debug, info, warn, error) |
| `--version` | Print version information |
| `--help` | Print help |

## Systemd Service

For production deployments on Linux, create a systemd service:

```bash
sudo cat > /etc/systemd/system/zentinel.service << 'EOF'
[Unit]
Description=Zentinel Reverse Proxy
After=network.target

[Service]
Type=simple
User=zentinel
Group=zentinel
ExecStart=/usr/local/bin/zentinel -c /etc/zentinel/zentinel.kdl
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=5
LimitNOFILE=65535

[Install]
WantedBy=multi-user.target
EOF

# Create zentinel user
sudo useradd -r -s /sbin/nologin zentinel

# Set permissions
sudo chown -R zentinel:zentinel /etc/zentinel

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable zentinel
sudo systemctl start zentinel
```

### Managing the Service

```bash
# Check status
sudo systemctl status zentinel

# View logs
sudo journalctl -u zentinel -f

# Reload configuration (graceful)
sudo systemctl reload zentinel

# Restart
sudo systemctl restart zentinel
```

## Verifying the Installation

After starting Zentinel, verify it's running:

```bash
# Check if listening
curl -I http://localhost:8080/

# Check metrics endpoint
curl http://localhost:9090/metrics
```

> **Production deployments:** Before deploying to production, verify binary authenticity using cosign signatures and SLSA provenance. See [Supply Chain Security](/docs/operations/supply-chain/).

## Next Steps

- [Quick Start](../quick-start/) - Get up and running in 5 minutes
- [Basic Configuration](../basic-configuration/) - Learn the configuration format
- [First Route](../first-route/) - Create your first routing rule

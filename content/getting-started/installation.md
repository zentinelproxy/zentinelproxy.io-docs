+++
title = "Installation"
weight = 1
+++

Sentinel can be installed via the install script, from pre-built binaries, built from source, or run as an OCI container.

## Install Script (Recommended)

The easiest way to install Sentinel is using the install script, which automatically detects your OS and architecture:

```bash
curl -fsSL https://getsentinel.raskell.io | sh
```

The script downloads the appropriate binary and installs it to `~/.local/bin`. You may need to add this to your PATH:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Add this line to your shell profile (`~/.bashrc`, `~/.zshrc`, etc.) to make it permanent.

### Verify Installation

```bash
sentinel --version
```

## Pre-built Binaries

Alternatively, download binaries manually from [GitHub Releases](https://github.com/raskell-io/sentinel/releases).

### Linux (amd64)

```bash
curl -LO https://github.com/raskell-io/sentinel/releases/latest/download/sentinel-linux-amd64.tar.gz
tar xzf sentinel-linux-amd64.tar.gz
sudo mv sentinel /usr/local/bin/
```

### macOS (Apple Silicon)

```bash
curl -LO https://github.com/raskell-io/sentinel/releases/latest/download/sentinel-darwin-arm64.tar.gz
tar xzf sentinel-darwin-arm64.tar.gz
sudo mv sentinel /usr/local/bin/
```

### macOS (Intel)

```bash
curl -LO https://github.com/raskell-io/sentinel/releases/latest/download/sentinel-darwin-amd64.tar.gz
tar xzf sentinel-darwin-amd64.tar.gz
sudo mv sentinel /usr/local/bin/
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
git clone https://github.com/raskell-io/sentinel.git
cd sentinel
cargo build --release
```

The binary will be at `target/release/sentinel`.

### Install System-wide

```bash
sudo cp target/release/sentinel /usr/local/bin/
```

## OCI Container

Sentinel provides official OCI container images.

### Pull the Image

```bash
# Using Docker
docker pull ghcr.io/raskell-io/sentinel:latest

# Using Podman
podman pull ghcr.io/raskell-io/sentinel:latest
```

### Run the Container

```bash
# Using Docker
docker run -d \
  --name sentinel \
  -p 8080:8080 \
  -p 9090:9090 \
  -v $(pwd)/sentinel.kdl:/etc/sentinel/sentinel.kdl:ro \
  ghcr.io/raskell-io/sentinel:latest

# Using Podman
podman run -d \
  --name sentinel \
  -p 8080:8080 \
  -p 9090:9090 \
  -v $(pwd)/sentinel.kdl:/etc/sentinel/sentinel.kdl:ro \
  ghcr.io/raskell-io/sentinel:latest
```

### Compose File

Works with both Docker Compose and Podman Compose:

```yaml
version: '3.8'

services:
  sentinel:
    image: ghcr.io/raskell-io/sentinel:latest
    ports:
      - "8080:8080"   # HTTP proxy
      - "9090:9090"   # Metrics
    volumes:
      - ./sentinel.kdl:/etc/sentinel/sentinel.kdl:ro
      - ./certs:/etc/sentinel/certs:ro
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

By default, Sentinel looks for configuration in these locations:

1. Path specified with `-c` or `--config` flag
2. `./sentinel.kdl` (current directory)
3. `/etc/sentinel/sentinel.kdl`

### Create a Basic Config

```bash
mkdir -p /etc/sentinel
cat > /etc/sentinel/sentinel.kdl << 'EOF'
server {
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

## Running Sentinel

### Basic Usage

```bash
# Run with default config location
sentinel

# Run with specific config file
sentinel -c /path/to/sentinel.kdl

# Validate config without running
sentinel -c sentinel.kdl --test

# Run with verbose logging
sentinel -c sentinel.kdl --log-level debug
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
sudo cat > /etc/systemd/system/sentinel.service << 'EOF'
[Unit]
Description=Sentinel Reverse Proxy
After=network.target

[Service]
Type=simple
User=sentinel
Group=sentinel
ExecStart=/usr/local/bin/sentinel -c /etc/sentinel/sentinel.kdl
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=5
LimitNOFILE=65535

[Install]
WantedBy=multi-user.target
EOF

# Create sentinel user
sudo useradd -r -s /sbin/nologin sentinel

# Set permissions
sudo chown -R sentinel:sentinel /etc/sentinel

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable sentinel
sudo systemctl start sentinel
```

### Managing the Service

```bash
# Check status
sudo systemctl status sentinel

# View logs
sudo journalctl -u sentinel -f

# Reload configuration (graceful)
sudo systemctl reload sentinel

# Restart
sudo systemctl restart sentinel
```

## Verifying the Installation

After starting Sentinel, verify it's running:

```bash
# Check if listening
curl -I http://localhost:8080/

# Check metrics endpoint
curl http://localhost:9090/metrics
```

## Next Steps

- [Quick Start](../quick-start/) - Get up and running in 5 minutes
- [Basic Configuration](../basic-configuration/) - Learn the configuration format
- [First Route](../first-route/) - Create your first routing rule

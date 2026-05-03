+++
title = "Installation"
weight = 1
updated = 2026-05-03
+++

Zentinel can be installed via the install script, from pre-built binaries, built from source, or run as an OCI container.

## Install Script (Recommended)

The install script detects your OS and architecture and installs the binary. On Linux hosts running systemd it also drops a managed-service layout: unit file, sysusers snippet, and a starter config at `/etc/zentinel/zentinel.kdl`.

```bash
# Binary + service files (service is installed but NOT started)
curl -fsSL https://get.zentinelproxy.io | sh

# Install and start the service in one shot
curl -fsSL https://get.zentinelproxy.io | sh -s -- --enable-service

# Binary only, even on systemd hosts
curl -fsSL https://get.zentinelproxy.io | sh -s -- --skip-service
```

When run as root or via sudo on a systemd host, the script creates:

| Path | Purpose |
|------|---------|
| `/usr/local/bin/zentinel` | Binary |
| `/etc/systemd/system/zentinel.service` | Unit file with `CAP_NET_BIND_SERVICE` and sandboxing |
| `/usr/lib/sysusers.d/zentinel.conf` | System user declaration (applied via `systemd-sysusers`) |
| `/etc/zentinel/zentinel.kdl` | Starter config (preserved across re-installs) |

When run as a regular user, when systemd is unavailable, or with `--skip-service`, only the binary is installed. The fallback location is `~/.local/bin`. Add it to your `PATH` if needed:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Add this line to your shell profile (`~/.bashrc`, `~/.zshrc`, etc.) to make it permanent.

### Verify Installation

```bash
zentinel --version
```

### Service flow

On systemd hosts the script does not enable or start the service by default. After the install completes:

```bash
sudoedit /etc/zentinel/zentinel.kdl   # edit listeners and routes
zentinel test --config /etc/zentinel/zentinel.kdl
sudo systemctl enable --now zentinel
journalctl -u zentinel -f
```

To bind ports below 1024 (such as 80 and 443), edit the listener address in the config. The shipped unit grants `AmbientCapabilities=CAP_NET_BIND_SERVICE`, so this works without running the proxy as root.

For details on the unit, file layout, capabilities, and uninstall, see [systemd Deployment](/docs/deployment/systemd/).

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

The install script provisions the unit, sysusers, and starter config automatically. The block below is the equivalent manual setup, useful when installing from source or behind air-gapped networks.

```bash
# Create zentinel user
sudo useradd --system --shell /usr/sbin/nologin --home-dir /var/lib/zentinel zentinel

# Drop the unit file
sudo cat > /etc/systemd/system/zentinel.service << 'EOF'
[Unit]
Description=Zentinel Security-First Reverse Proxy
Documentation=https://docs.zentinelproxy.io
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=zentinel
Group=zentinel
ExecStart=/usr/local/bin/zentinel --config /etc/zentinel/zentinel.kdl
ExecReload=/bin/kill -HUP $MAINPID
Restart=on-failure
RestartSec=5
LimitNOFILE=65535
AmbientCapabilities=CAP_NET_BIND_SERVICE
CapabilityBoundingSet=CAP_NET_BIND_SERVICE
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
StateDirectory=zentinel
LogsDirectory=zentinel
RuntimeDirectory=zentinel
ConfigurationDirectory=zentinel

[Install]
WantedBy=multi-user.target
EOF

# Permissions
sudo chown -R zentinel:zentinel /etc/zentinel

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable --now zentinel
```

The shipped unit also includes a stricter sandboxing block (`Protect{Kernel,Tunables,Modules}=true`, `RestrictAddressFamilies=`, `SystemCallFilter=@system-service`, etc.). See [systemd Deployment](/docs/deployment/systemd/) for the complete reference.

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

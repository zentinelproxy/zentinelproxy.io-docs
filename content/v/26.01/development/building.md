+++
title = "Building from Source"
weight = 1
+++

Compile Sentinel and agents from source code.

## Prerequisites

### Rust Toolchain

Install Rust via rustup:

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source ~/.cargo/env

# Verify installation
rustc --version  # 1.75.0 or later
cargo --version
```

### System Dependencies

**macOS:**

```bash
brew install openssl pkg-config
```

**Ubuntu/Debian:**

```bash
sudo apt update
sudo apt install build-essential pkg-config libssl-dev
```

**RHEL/Fedora:**

```bash
sudo dnf install gcc openssl-devel pkg-config
```

### Optional Dependencies

For the ModSecurity agent:

```bash
# macOS
brew install libmodsecurity

# Ubuntu/Debian
sudo apt install libmodsecurity-dev
```

## Building Sentinel

### Clone the Repository

```bash
git clone https://github.com/raskell-io/sentinel.git
cd sentinel
```

### Debug Build

```bash
cargo build
```

Binary location: `target/debug/sentinel`

### Release Build

```bash
cargo build --release
```

Binary location: `target/release/sentinel`

### Build with Features

```bash
# All features
cargo build --release --all-features

# Specific features
cargo build --release --features "metrics,tracing"
```

### Available Features

| Feature | Description | Default |
|---------|-------------|---------|
| `metrics` | Prometheus metrics endpoint | Yes |
| `tracing` | OpenTelemetry tracing | Yes |
| `tls` | TLS/HTTPS support | Yes |
| `http2` | HTTP/2 support | Yes |
| `websocket` | WebSocket proxying | Yes |

## Building Agents

### WAF Agent

```bash
git clone https://github.com/raskell-io/sentinel-agent-waf.git
cd sentinel-agent-waf
cargo build --release
```

### ModSecurity Agent

Requires libmodsecurity:

```bash
git clone https://github.com/raskell-io/sentinel-agent-modsec.git
cd sentinel-agent-modsec

# Set library paths if needed (macOS)
export CPLUS_INCLUDE_PATH=/opt/homebrew/include
export LIBRARY_PATH=/opt/homebrew/lib

cargo build --release
```

### JavaScript Agent

```bash
git clone https://github.com/raskell-io/sentinel-agent-js.git
cd sentinel-agent-js
cargo build --release
```

### AI Gateway Agent

```bash
git clone https://github.com/raskell-io/sentinel-agent-ai-gateway.git
cd sentinel-agent-ai-gateway
cargo build --release
```

### WebSocket Inspector

```bash
git clone https://github.com/raskell-io/sentinel-agent-websocket-inspector.git
cd sentinel-agent-websocket-inspector
cargo build --release
```

## Cross-Compilation

### Linux from macOS

```bash
# Add target
rustup target add x86_64-unknown-linux-gnu

# Install cross-compiler
brew install filosottile/musl-cross/musl-cross

# Build
cargo build --release --target x86_64-unknown-linux-gnu
```

### Using Cross

For easier cross-compilation:

```bash
cargo install cross

# Build for Linux
cross build --release --target x86_64-unknown-linux-gnu

# Build for ARM64
cross build --release --target aarch64-unknown-linux-gnu
```

### Static Linking (musl)

```bash
rustup target add x86_64-unknown-linux-musl
cargo build --release --target x86_64-unknown-linux-musl
```

## Build Profiles

### Cargo.toml Settings

```toml
[profile.release]
lto = true           # Link-time optimization
codegen-units = 1    # Better optimization
panic = "abort"      # Smaller binary
strip = true         # Strip symbols

[profile.release-debug]
inherits = "release"
debug = true         # Include debug symbols
strip = false
```

Build with custom profile:

```bash
cargo build --profile release-debug
```

## Verification

### Check Binary

```bash
# Version
./target/release/sentinel --version

# Help
./target/release/sentinel --help

# Validate config
./target/release/sentinel validate -c sentinel.kdl
```

### Run Tests

```bash
cargo test
cargo test --release
```

### Check for Issues

```bash
# Formatting
cargo fmt --check

# Lints
cargo clippy -- -D warnings

# Security audit
cargo audit
```

## Troubleshooting

### OpenSSL Not Found

```bash
# macOS
export OPENSSL_DIR=$(brew --prefix openssl)

# Linux
export OPENSSL_DIR=/usr

cargo build --release
```

### libmodsecurity Not Found

```bash
# Check installation
pkg-config --libs modsecurity

# Set paths manually
export CPLUS_INCLUDE_PATH=/opt/homebrew/include
export LIBRARY_PATH=/opt/homebrew/lib
```

### Out of Memory

For large builds:

```bash
# Reduce parallelism
cargo build --release -j 2
```

### Slow Builds

Use sccache for faster rebuilds:

```bash
cargo install sccache
export RUSTC_WRAPPER=sccache
cargo build --release
```

## Next Steps

- [Development Setup](../setup/) - Configure your IDE
- [Testing](../testing/) - Run the test suite
- [Contributing](../contributing/) - Submit your first PR

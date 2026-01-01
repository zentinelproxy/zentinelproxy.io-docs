+++
title = "Development Setup"
weight = 2
+++

Configure your development environment for working on Sentinel.

## IDE Configuration

### VS Code

Install recommended extensions:

```bash
# Rust Analyzer - essential
code --install-extension rust-lang.rust-analyzer

# Additional tools
code --install-extension tamasfe.even-better-toml  # TOML syntax
code --install-extension serayuzgur.crates         # Crate version hints
code --install-extension vadimcn.vscode-lldb       # Debugging
```

Create `.vscode/settings.json`:

```json
{
    "rust-analyzer.cargo.features": "all",
    "rust-analyzer.check.command": "clippy",
    "rust-analyzer.procMacro.enable": true,
    "editor.formatOnSave": true,
    "[rust]": {
        "editor.defaultFormatter": "rust-lang.rust-analyzer"
    }
}
```

Create `.vscode/launch.json` for debugging:

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Debug Sentinel",
            "type": "lldb",
            "request": "launch",
            "program": "${workspaceFolder}/target/debug/sentinel",
            "args": ["-c", "examples/simple.kdl"],
            "cwd": "${workspaceFolder}"
        },
        {
            "name": "Debug Tests",
            "type": "lldb",
            "request": "launch",
            "cargo": {
                "args": ["test", "--no-run"]
            },
            "cwd": "${workspaceFolder}"
        }
    ]
}
```

### JetBrains (RustRover/CLion)

1. Install the Rust plugin
2. Open the project directory
3. Configure:
   - **Settings > Languages & Frameworks > Rust**
   - Enable "Run clippy on build"
   - Enable "Format on save"

### Neovim

With `lazy.nvim`:

```lua
{
    "mrcjkb/rustaceanvim",
    version = "^4",
    lazy = false,
    config = function()
        vim.g.rustaceanvim = {
            tools = {
                hover_actions = { auto_focus = true },
            },
            server = {
                settings = {
                    ["rust-analyzer"] = {
                        cargo = { features = "all" },
                        check = { command = "clippy" },
                    },
                },
            },
        }
    end,
}
```

## Essential Tools

### Required

```bash
# Formatting
rustup component add rustfmt

# Linting
rustup component add clippy

# Documentation
cargo install cargo-doc
```

### Recommended

```bash
# Watch for changes and rebuild
cargo install cargo-watch

# Security audit
cargo install cargo-audit

# Unused dependencies
cargo install cargo-udeps

# Better test output
cargo install cargo-nextest

# Fast linker (macOS/Linux)
brew install mold  # or via package manager
```

### cargo-watch Usage

```bash
# Watch and run tests
cargo watch -x test

# Watch and run specific test
cargo watch -x "test test_name"

# Watch and run with clippy
cargo watch -x clippy

# Watch multiple commands
cargo watch -x check -x test -x clippy
```

## Environment Variables

Create a `.env` file for development:

```bash
# Logging
RUST_LOG=sentinel=debug,tower=info

# Backtrace for panics
RUST_BACKTRACE=1

# Colored output
CARGO_TERM_COLOR=always
```

Load with:

```bash
source .env
cargo run
```

Or use `direnv`:

```bash
# Install direnv
brew install direnv  # macOS
sudo apt install direnv  # Ubuntu

# Create .envrc
echo 'export RUST_LOG=sentinel=debug' > .envrc
echo 'export RUST_BACKTRACE=1' >> .envrc

# Allow the directory
direnv allow
```

## Git Configuration

### Pre-commit Hooks

Create `.git/hooks/pre-commit`:

```bash
#!/bin/sh
set -e

echo "Running cargo fmt..."
cargo fmt --check

echo "Running cargo clippy..."
cargo clippy -- -D warnings

echo "Running tests..."
cargo test --quiet

echo "All checks passed!"
```

Make it executable:

```bash
chmod +x .git/hooks/pre-commit
```

### Git Attributes

Create `.gitattributes`:

```
*.rs text eol=lf
*.toml text eol=lf
*.kdl text eol=lf
Cargo.lock text eol=lf
```

## Fast Linking

### mold (Linux/macOS)

```bash
# Install
brew install mold  # macOS
sudo apt install mold  # Ubuntu

# Configure in .cargo/config.toml
[target.x86_64-unknown-linux-gnu]
linker = "clang"
rustflags = ["-C", "link-arg=-fuse-ld=mold"]
```

### lld (Cross-platform)

```bash
# Install
brew install llvm  # macOS
sudo apt install lld  # Ubuntu

# Configure in .cargo/config.toml
[target.x86_64-unknown-linux-gnu]
linker = "clang"
rustflags = ["-C", "link-arg=-fuse-ld=lld"]
```

## Workspace Layout

For agent development, consider this layout:

```
sentinel-workspace/
├── sentinel/                    # Main proxy
├── sentinel-agent-protocol/     # Shared protocol
├── sentinel-agent-waf/          # WAF agent
├── sentinel-agent-auth/         # Auth agent
└── Cargo.toml                   # Workspace manifest
```

Workspace `Cargo.toml`:

```toml
[workspace]
members = [
    "sentinel",
    "sentinel-agent-protocol",
    "sentinel-agent-waf",
    "sentinel-agent-auth",
]
resolver = "2"

[workspace.dependencies]
tokio = { version = "1", features = ["full"] }
serde = { version = "1", features = ["derive"] }
tracing = "0.1"
```

## Development Server

Run Sentinel with live reload:

```bash
# Terminal 1: Watch and rebuild
cargo watch -x build

# Terminal 2: Run (restart manually on rebuild)
./target/debug/sentinel -c examples/dev.kdl
```

Or use `systemfd` for socket handoff:

```bash
cargo install systemfd

# Keeps socket open across restarts
systemfd --no-pid -s http::8080 -- cargo watch -x run
```

## Testing Setup

### Test Database

Some integration tests need a test backend:

```bash
# Simple echo server
python3 -m http.server 3000
```

Or use the provided test server:

```bash
cargo run --example test_server
```

### Test Certificates

Generate self-signed certs for TLS testing:

```bash
# Create certs directory
mkdir -p certs

# Generate CA
openssl genrsa -out certs/ca.key 2048
openssl req -x509 -new -nodes -key certs/ca.key \
    -sha256 -days 365 -out certs/ca.crt \
    -subj "/CN=Test CA"

# Generate server cert
openssl genrsa -out certs/server.key 2048
openssl req -new -key certs/server.key \
    -out certs/server.csr \
    -subj "/CN=localhost"
openssl x509 -req -in certs/server.csr \
    -CA certs/ca.crt -CAkey certs/ca.key \
    -CAcreateserial -out certs/server.crt \
    -days 365 -sha256
```

## Next Steps

- [Code Style](../code-style/) - Formatting and conventions
- [Testing](../testing/) - Run the test suite
- [Contributing](../contributing/) - Submit your first PR

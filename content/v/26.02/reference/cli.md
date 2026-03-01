+++
title = "CLI Reference"
weight = 1
updated = 2026-02-19
+++

Complete command-line interface reference for Zentinel.

## Synopsis

```
zentinel [OPTIONS] [COMMAND]
```

## Global Options

| Option | Short | Environment | Description |
|--------|-------|-------------|-------------|
| `--config <FILE>` | `-c` | `ZENTINEL_CONFIG` | Configuration file path |
| `--test` | `-t` | | Test configuration and exit |
| `--verbose` | | | Enable debug logging |
| `--daemon` | `-d` | | Run as background daemon |
| `--upgrade` | `-u` | | Upgrade from running instance |
| `--version` | `-V` | | Print version information |
| `--help` | `-h` | | Print help information |

## Commands

### run (default)

Run the proxy server. This is the default command when none is specified.

```bash
# These are equivalent
zentinel --config zentinel.kdl
zentinel run --config zentinel.kdl
```

**Options:**
- `-c, --config <FILE>` - Configuration file path

### test

Validate configuration file and exit without starting the server.

```bash
zentinel test --config zentinel.kdl
zentinel -t -c zentinel.kdl
```

**Options:**
- `-c, --config <FILE>` - Configuration file to test

**Exit codes:**
- `0` - Configuration is valid
- `1` - Configuration error

**Output:**
```
INFO Testing configuration file: zentinel.kdl
INFO Configuration test successful:
INFO   - 2 listener(s)
INFO   - 5 route(s)
INFO   - 3 upstream(s)
zentinel: configuration file zentinel.kdl test is successful
```

## Examples

### Basic Usage

```bash
# Start with configuration file
zentinel --config /etc/zentinel/zentinel.kdl

# Start with environment variable
export ZENTINEL_CONFIG=/etc/zentinel/zentinel.kdl
zentinel

# Use embedded default configuration
zentinel
```

### Configuration Testing

```bash
# Test configuration syntax and semantics
zentinel --test --config zentinel.kdl

# Test with verbose output
zentinel --test --verbose --config zentinel.kdl
```

### Daemon Mode

```bash
# Run as daemon (background process)
zentinel --daemon --config zentinel.kdl

# Upgrade running instance (zero-downtime restart)
zentinel --upgrade --config zentinel.kdl
```

### Debug Mode

```bash
# Enable debug logging
zentinel --verbose --config zentinel.kdl

# Or via environment variable
RUST_LOG=debug zentinel --config zentinel.kdl
```

## Version Information

```bash
zentinel --version
```

Output:
```
zentinel 0.1.0 (release 2025.01, commit abc1234)
```

Version string includes:
- Semantic version (Cargo.toml)
- CalVer release tag
- Git commit hash

## Configuration Resolution

Zentinel resolves configuration in this order (first found wins):

1. `--config` / `-c` command-line argument
2. `ZENTINEL_CONFIG` environment variable
3. Embedded default configuration

## Process Management

### Signals

| Signal | Behavior |
|--------|----------|
| `SIGTERM` | Graceful shutdown (drain connections) |
| `SIGINT` | Graceful shutdown (Ctrl+C) |
| `SIGHUP` | Reload configuration |

### Graceful Shutdown

On SIGTERM/SIGINT:

1. Stop accepting new connections
2. Drain in-flight requests (configurable timeout)
3. Close remaining connections
4. Exit with code 0

```bash
# Graceful shutdown
kill -TERM $(cat /var/run/zentinel.pid)

# Force shutdown (after graceful timeout)
kill -9 $(cat /var/run/zentinel.pid)
```

### Configuration Reload

```bash
# Reload configuration without restart
kill -HUP $(cat /var/run/zentinel.pid)
```

Reload behavior:
1. Parse new configuration
2. Validate syntax and semantics
3. If valid: atomically swap configuration
4. If invalid: keep old configuration, log error

### Zero-Downtime Upgrade

```bash
# Start new instance that takes over from old
zentinel --upgrade --config zentinel.kdl
```

Upgrade sequence:
1. New process starts
2. New process signals old process
3. Old process transfers listening sockets
4. Old process drains connections
5. Old process exits

## Exit Codes

| Code | Description |
|------|-------------|
| `0` | Success / clean shutdown |
| `1` | Configuration error |
| `2` | Runtime error |

## See Also

- [Environment Variables](../env-vars/) - Environment variable reference
- [Configuration](../../configuration/) - Configuration file format

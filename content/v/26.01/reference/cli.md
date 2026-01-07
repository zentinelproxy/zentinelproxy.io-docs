+++
title = "CLI Reference"
weight = 1
+++

Complete command-line interface reference for Sentinel.

## Synopsis

```
sentinel [OPTIONS] [COMMAND]
```

## Global Options

| Option | Short | Environment | Description |
|--------|-------|-------------|-------------|
| `--config <FILE>` | `-c` | `SENTINEL_CONFIG` | Configuration file path |
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
sentinel --config sentinel.kdl
sentinel run --config sentinel.kdl
```

**Options:**
- `-c, --config <FILE>` - Configuration file path

### test

Validate configuration file and exit without starting the server.

```bash
sentinel test --config sentinel.kdl
sentinel -t -c sentinel.kdl
```

**Options:**
- `-c, --config <FILE>` - Configuration file to test

**Exit codes:**
- `0` - Configuration is valid
- `1` - Configuration error

**Output:**
```
INFO Testing configuration file: sentinel.kdl
INFO Configuration test successful:
INFO   - 2 listener(s)
INFO   - 5 route(s)
INFO   - 3 upstream(s)
sentinel: configuration file sentinel.kdl test is successful
```

## Examples

### Basic Usage

```bash
# Start with configuration file
sentinel --config /etc/sentinel/sentinel.kdl

# Start with environment variable
export SENTINEL_CONFIG=/etc/sentinel/sentinel.kdl
sentinel

# Use embedded default configuration
sentinel
```

### Configuration Testing

```bash
# Test configuration syntax and semantics
sentinel --test --config sentinel.kdl

# Test with verbose output
sentinel --test --verbose --config sentinel.kdl
```

### Daemon Mode

```bash
# Run as daemon (background process)
sentinel --daemon --config sentinel.kdl

# Upgrade running instance (zero-downtime restart)
sentinel --upgrade --config sentinel.kdl
```

### Debug Mode

```bash
# Enable debug logging
sentinel --verbose --config sentinel.kdl

# Or via environment variable
RUST_LOG=debug sentinel --config sentinel.kdl
```

## Version Information

```bash
sentinel --version
```

Output:
```
sentinel 0.1.0 (release 2025.01, commit abc1234)
```

Version string includes:
- Semantic version (Cargo.toml)
- CalVer release tag
- Git commit hash

## Configuration Resolution

Sentinel resolves configuration in this order (first found wins):

1. `--config` / `-c` command-line argument
2. `SENTINEL_CONFIG` environment variable
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
kill -TERM $(cat /var/run/sentinel.pid)

# Force shutdown (after graceful timeout)
kill -9 $(cat /var/run/sentinel.pid)
```

### Configuration Reload

```bash
# Reload configuration without restart
kill -HUP $(cat /var/run/sentinel.pid)
```

Reload behavior:
1. Parse new configuration
2. Validate syntax and semantics
3. If valid: atomically swap configuration
4. If invalid: keep old configuration, log error

### Zero-Downtime Upgrade

```bash
# Start new instance that takes over from old
sentinel --upgrade --config sentinel.kdl
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

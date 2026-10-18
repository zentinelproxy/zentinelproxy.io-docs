+++
title = "CLI Reference"
weight = 1
updated = 2026-10-18
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

### validate

Validate the configuration, then run checks that need the outside world:
upstream connectivity, TLS certificates and agent connectivity. Each check can
be skipped.

```bash
zentinel validate --config zentinel.kdl

# Configuration only, no network, agent or certificate checks (CI)
zentinel validate --config zentinel.kdl --skip-network --skip-agents --skip-certs
```

**Options:**
- `-c, --config <FILE>` - Configuration file to validate (embedded default if omitted)
- `--skip-network` - Skip upstream connectivity checks
- `--skip-agents` - Skip agent connectivity checks
- `--skip-certs` - Skip TLS certificate validation

**Exit codes:**
- `0` - Configuration valid and every check that ran passed (warnings are printed but do not fail)
- `1` - Configuration error, or at least one check failed

**Output:**
```
✓ Configuration schema valid
Checking upstream connectivity...
Validating TLS certificates...
Checking agent connectivity...
✓ All validation checks passed
```

### lint

Validate the configuration and report best-practice warnings. When the
configuration comes from a file, `lint` also reports **unknown keys**: settings
that parse but are read by nothing (misspelled keys, keys in the wrong block,
two settings run together on one line).

```bash
zentinel lint --config zentinel.kdl
```

**Options:**
- `-c, --config <FILE>` - Configuration file to lint (embedded default if omitted)

**Exit codes:**
- `0` - Configuration is valid, **including when warnings are reported**; lint
  warnings are recommendations. To fail a CI job on them, check the output
  for `⚠` lines.
- `1` - Configuration error

**Output:**
```
✓ No best practice issues found
```

or

```
⚠  Configuration has 1 best practice warnings:

  ⚠  <warning message>
```

### bundle

Install and manage the bundled agents (WAF, rate limiting, and others) that are
versioned together with Zentinel. See [Bundle](../../deployment/bundle/) for
the workflow.

```
zentinel bundle <COMMAND>
```

| Command | Description |
|---------|-------------|
| `install [AGENT]` | Install all bundled agents, or only `AGENT` |
| `status` | Show status of installed agents |
| `list` | List the agents available in the bundle |
| `uninstall [AGENT]` | Uninstall all bundled agents, or only `AGENT` |
| `update` | Check for updates to bundled agents |

**`bundle install` options:**
- `-n, --dry-run` - Preview what would be installed without making changes
- `-f, --force` - Reinstall even if already installed
- `--systemd` - Also install systemd service files
- `--prefix <PREFIX>` - Custom installation prefix (`<PREFIX>/bin`, `<PREFIX>/etc/zentinel/agents`, `<PREFIX>/lib/systemd/system`)
- `--skip-verify` - Skip checksum verification

Without `--prefix`, agents install system-wide (`/usr/local/bin`,
`/etc/zentinel/agents`, `/etc/systemd/system`) when running as root or when all
of those directories are writable, and otherwise per user (`~/.local/bin`,
`~/.config/zentinel/agents`, `~/.config/systemd/user`).

**`bundle status` / `bundle list` options:**
- `-v, --verbose` - Show detailed output

**`bundle uninstall` options:**
- `-n, --dry-run` - Preview what would be uninstalled

**`bundle update` options:**
- `--apply` - Perform the update (without it, `update` only reports available updates)

```bash
zentinel bundle list
zentinel bundle install --dry-run
sudo zentinel bundle install --systemd
zentinel bundle install waf
zentinel bundle status --verbose
zentinel bundle update --apply
zentinel bundle uninstall waf
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

Output (26.10_3 release binary):
```
zentinel 0.6.45 (release 26.10_3, commit 07c2f6d)
```

Version string includes:
- Semantic version of the crate
- CalVer release tag
- Git commit hash (short)

Up to and including 26.10_3, the semantic version printed by release binaries
is one patch below the crate published for that release (26.10_3 is `0.6.46`
on crates.io). Releases after 26.10_3 print the published version; see
[Versioning](../../appendix/versioning/#version-mapping).

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

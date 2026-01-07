+++
title = "Code Style"
weight = 3
+++

Formatting conventions and best practices for Sentinel codebase.

## Formatting

### rustfmt

All code must be formatted with `rustfmt`:

```bash
# Format all code
cargo fmt

# Check formatting without changing
cargo fmt --check
```

### Configuration

The project uses default rustfmt settings. If customization is needed, create `rustfmt.toml`:

```toml
edition = "2021"
max_width = 100
tab_spaces = 4
use_small_heuristics = "Default"
```

## Linting

### Clippy

All code must pass clippy with no warnings:

```bash
# Run clippy
cargo clippy

# Treat warnings as errors (CI mode)
cargo clippy -- -D warnings

# With all features
cargo clippy --all-features -- -D warnings
```

### Allowed Lints

Suppress specific lints only with justification:

```rust
// Reason: XYZ requires this pattern
#[allow(clippy::too_many_arguments)]
fn complex_function(...) { }
```

### Denied Lints

These are always errors:

```rust
#![deny(unsafe_code)]           // No unsafe without review
#![deny(missing_docs)]          // Public items need docs
#![deny(unused_must_use)]       // Must handle Results
```

## Naming Conventions

### General Rules

| Item | Convention | Example |
|------|------------|---------|
| Types | PascalCase | `RouteConfig`, `HttpRequest` |
| Functions | snake_case | `handle_request`, `parse_config` |
| Variables | snake_case | `request_count`, `upstream_url` |
| Constants | SCREAMING_SNAKE_CASE | `MAX_CONNECTIONS`, `DEFAULT_TIMEOUT` |
| Modules | snake_case | `health_check`, `route_matching` |
| Traits | PascalCase | `Handler`, `Configurable` |
| Lifetimes | short lowercase | `'a`, `'req`, `'cfg` |

### Prefixes/Suffixes

| Pattern | Usage | Example |
|---------|-------|---------|
| `is_*`, `has_*` | Boolean functions | `is_healthy()`, `has_body()` |
| `*_mut` | Mutable variants | `get_config_mut()` |
| `try_*` | Fallible operations | `try_parse()` |
| `into_*` | Consuming conversions | `into_response()` |
| `as_*` | Borrowed conversions | `as_bytes()` |
| `*Builder` | Builder types | `RequestBuilder` |
| `*Config` | Configuration structs | `ServerConfig` |
| `*Error` | Error types | `ConfigError` |

### Module Organization

```rust
// Good: logical grouping
mod config;
mod server;
mod routing;
mod proxy;

// In each module:
mod.rs or module_name.rs
├── types.rs      // Public types
├── error.rs      // Module-specific errors
├── impl.rs       // Implementations
└── tests.rs      // Unit tests
```

## Documentation

### Public Items

All public items require documentation:

```rust
/// A route configuration entry.
///
/// Routes define how incoming requests are matched and
/// forwarded to upstream services.
///
/// # Examples
///
/// ```
/// let route = Route::new("/api")
///     .upstream("backend")
///     .timeout(Duration::from_secs(30));
/// ```
pub struct Route {
    /// The path pattern to match.
    pub path: PathPattern,

    /// Target upstream name.
    pub upstream: String,
}
```

### Functions

```rust
/// Parses a KDL configuration file.
///
/// # Arguments
///
/// * `path` - Path to the configuration file
///
/// # Returns
///
/// The parsed configuration or an error if parsing fails.
///
/// # Errors
///
/// Returns `ConfigError::IoError` if the file cannot be read.
/// Returns `ConfigError::ParseError` if the KDL is invalid.
pub fn parse_config(path: &Path) -> Result<Config, ConfigError> {
    // ...
}
```

### Internal Code

Internal code should be self-documenting with clear names. Add comments for non-obvious logic:

```rust
fn calculate_retry_delay(&self, attempt: u32) -> Duration {
    // Exponential backoff with jitter to prevent thundering herd
    let base = self.base_delay.as_millis() as u64;
    let max = self.max_delay.as_millis() as u64;

    let exponential = base.saturating_mul(2u64.saturating_pow(attempt));
    let capped = exponential.min(max);

    // Add 0-25% jitter
    let jitter = rand::random::<u64>() % (capped / 4 + 1);
    Duration::from_millis(capped + jitter)
}
```

## Error Handling

### Error Types

Use `thiserror` for library errors:

```rust
use thiserror::Error;

#[derive(Error, Debug)]
pub enum ConfigError {
    #[error("failed to read config file: {0}")]
    IoError(#[from] std::io::Error),

    #[error("invalid KDL syntax at line {line}: {message}")]
    ParseError { line: usize, message: String },

    #[error("unknown upstream: {0}")]
    UnknownUpstream(String),
}
```

### Error Propagation

Use `?` operator and `anyhow` for applications:

```rust
// Library code: explicit error types
pub fn parse(input: &str) -> Result<Config, ConfigError> {
    let kdl = input.parse().map_err(|e| ConfigError::ParseError {
        line: e.line(),
        message: e.to_string(),
    })?;
    // ...
}

// Application code: anyhow for convenience
fn main() -> anyhow::Result<()> {
    let config = parse_config(&args.config)?;
    // ...
    Ok(())
}
```

### Avoid Panics

Never panic in library code:

```rust
// Bad: panics on invalid input
fn get_route(&self, index: usize) -> &Route {
    &self.routes[index]  // Panics if out of bounds
}

// Good: returns Option
fn get_route(&self, index: usize) -> Option<&Route> {
    self.routes.get(index)
}

// Good: returns Result with context
fn get_route(&self, index: usize) -> Result<&Route, RouteError> {
    self.routes.get(index)
        .ok_or_else(|| RouteError::NotFound(index))
}
```

## Async Code

### Async Functions

```rust
// Prefer async fn over manual Future impl
pub async fn handle_request(&self, req: Request) -> Response {
    // ...
}

// Use async blocks for closures
let handler = |req| async move {
    process(req).await
};
```

### Cancellation Safety

Document cancellation behavior:

```rust
/// Processes a request through the agent pipeline.
///
/// # Cancellation Safety
///
/// This function is cancellation-safe. If cancelled, no partial
/// state will be left. In-flight requests to agents will be
/// abandoned but the connection remains valid.
pub async fn process(&self, req: Request) -> Result<Response> {
    // ...
}
```

### Avoid Blocking

Never block in async code:

```rust
// Bad: blocks the runtime
async fn read_file(path: &Path) -> Vec<u8> {
    std::fs::read(path).unwrap()  // Blocking!
}

// Good: use async filesystem
async fn read_file(path: &Path) -> io::Result<Vec<u8>> {
    tokio::fs::read(path).await
}

// Good: spawn blocking for CPU-heavy work
async fn hash_password(password: &str) -> String {
    let password = password.to_string();
    tokio::task::spawn_blocking(move || {
        bcrypt::hash(&password, 12)
    }).await.unwrap()
}
```

## Testing

### Test Organization

```rust
// Unit tests in the same file
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_valid_config() {
        // ...
    }
}

// Integration tests in tests/ directory
// tests/integration_test.rs
```

### Test Naming

```rust
#[test]
fn test_route_matches_exact_path() { }

#[test]
fn test_route_rejects_invalid_method() { }

#[test]
fn test_upstream_health_check_timeout() { }
```

### Async Tests

```rust
#[tokio::test]
async fn test_agent_communication() {
    let server = TestServer::start().await;
    let response = server.request("/health").await;
    assert_eq!(response.status(), 200);
}
```

## Performance

### Avoid Allocations in Hot Paths

```rust
// Bad: allocates on every call
fn format_header(name: &str, value: &str) -> String {
    format!("{}: {}", name, value)
}

// Good: write to existing buffer
fn write_header(buf: &mut Vec<u8>, name: &str, value: &str) {
    buf.extend_from_slice(name.as_bytes());
    buf.extend_from_slice(b": ");
    buf.extend_from_slice(value.as_bytes());
}
```

### Use Appropriate Collections

```rust
// Small fixed set: array
const METHODS: [&str; 4] = ["GET", "POST", "PUT", "DELETE"];

// Fast lookup: HashMap with ahash
use ahash::AHashMap;
let routes: AHashMap<String, Route> = AHashMap::new();

// Ordered iteration: BTreeMap
use std::collections::BTreeMap;
let sorted: BTreeMap<String, Route> = BTreeMap::new();
```

## Next Steps

- [Testing](../testing/) - Testing strategy
- [Contributing](../contributing/) - Submit changes
- [PR Process](../pr-process/) - Code review

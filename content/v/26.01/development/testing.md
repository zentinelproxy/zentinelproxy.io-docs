+++
title = "Testing"
weight = 5
+++

Testing strategy and philosophy for Sentinel development.

## Testing Philosophy

### Test Pyramid

```
        /\
       /  \        E2E Tests (few)
      /----\       Integration Tests (some)
     /------\      Unit Tests (many)
    /--------\
```

- **Unit tests**: Fast, isolated, test individual functions
- **Integration tests**: Test component interactions
- **E2E tests**: Full system tests with real connections

### What to Test

| Component | Test Type | Focus |
|-----------|-----------|-------|
| Config parsing | Unit | Valid/invalid inputs |
| Route matching | Unit | Path patterns, priorities |
| Health checks | Integration | HTTP/TCP checks |
| Agent protocol | Integration | Message encoding/decoding |
| Full proxy | E2E | Request/response flow |

## Running Tests

### All Tests

```bash
# Run all tests
cargo test

# With output
cargo test -- --nocapture

# Release mode (faster, but slower to compile)
cargo test --release
```

### Specific Tests

```bash
# Single test
cargo test test_route_matching

# Tests matching pattern
cargo test route

# Tests in module
cargo test config::tests

# Single package in workspace
cargo test -p sentinel-agent-waf
```

### Test Options

```bash
# Show test output even for passing tests
cargo test -- --show-output

# Run ignored tests
cargo test -- --ignored

# Run tests in parallel (default)
cargo test -- --test-threads=4

# Run tests sequentially
cargo test -- --test-threads=1
```

## Using cargo-nextest

Faster test runner with better output:

```bash
# Install
cargo install cargo-nextest

# Run tests
cargo nextest run

# With retries for flaky tests
cargo nextest run --retries 2

# Filter by test name
cargo nextest run -E 'test(route)'
```

## Test Organization

### Unit Tests

In the same file as the code:

```rust
// src/routing/matcher.rs

pub fn matches_path(pattern: &str, path: &str) -> bool {
    // implementation
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_exact_match() {
        assert!(matches_path("/api/users", "/api/users"));
    }

    #[test]
    fn test_no_match() {
        assert!(!matches_path("/api/users", "/api/posts"));
    }

    #[test]
    fn test_prefix_match() {
        assert!(matches_path("/api/*", "/api/users"));
    }
}
```

### Integration Tests

In `tests/` directory:

```rust
// tests/proxy_test.rs

use sentinel::test_utils::TestServer;

#[tokio::test]
async fn test_proxy_forwards_request() {
    // Setup
    let backend = TestServer::echo().await;
    let proxy = TestServer::proxy(&backend).await;

    // Execute
    let response = proxy.get("/api/test").await;

    // Verify
    assert_eq!(response.status(), 200);
    assert!(response.headers().contains_key("x-proxy"));
}
```

### Test Utilities

Create shared test helpers:

```rust
// src/test_utils.rs (or tests/common/mod.rs)

pub struct TestServer {
    addr: SocketAddr,
    handle: JoinHandle<()>,
}

impl TestServer {
    pub async fn echo() -> Self {
        // Start an echo server
    }

    pub async fn proxy(backend: &TestServer) -> Self {
        // Start proxy pointing to backend
    }

    pub async fn get(&self, path: &str) -> Response {
        reqwest::get(format!("http://{}{}", self.addr, path))
            .await
            .unwrap()
    }
}

impl Drop for TestServer {
    fn drop(&mut self) {
        self.handle.abort();
    }
}
```

## Async Testing

### tokio::test

```rust
#[tokio::test]
async fn test_async_operation() {
    let result = async_function().await;
    assert!(result.is_ok());
}

// With custom runtime
#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
async fn test_concurrent() {
    // ...
}
```

### Timeouts

```rust
use tokio::time::{timeout, Duration};

#[tokio::test]
async fn test_with_timeout() {
    let result = timeout(
        Duration::from_secs(5),
        slow_operation()
    ).await;

    assert!(result.is_ok(), "Operation timed out");
}
```

### Testing Cancellation

```rust
#[tokio::test]
async fn test_cancellation_safety() {
    let (tx, rx) = oneshot::channel();

    let handle = tokio::spawn(async move {
        cancellable_operation().await
    });

    // Cancel after short delay
    tokio::time::sleep(Duration::from_millis(10)).await;
    handle.abort();

    // Verify no resource leaks or panics
}
```

## Mocking

### Trait-Based Mocking

```rust
// Define trait
#[async_trait]
pub trait HealthChecker {
    async fn check(&self, target: &str) -> bool;
}

// Production implementation
pub struct HttpHealthChecker;

#[async_trait]
impl HealthChecker for HttpHealthChecker {
    async fn check(&self, target: &str) -> bool {
        // Real HTTP check
    }
}

// Test mock
pub struct MockHealthChecker {
    pub healthy: bool,
}

#[async_trait]
impl HealthChecker for MockHealthChecker {
    async fn check(&self, _target: &str) -> bool {
        self.healthy
    }
}

#[test]
fn test_with_mock() {
    let checker = MockHealthChecker { healthy: true };
    let upstream = Upstream::new(checker);
    assert!(upstream.is_available());
}
```

### mockall Crate

```rust
use mockall::{automock, predicate::*};

#[automock]
trait Database {
    fn get(&self, key: &str) -> Option<String>;
}

#[test]
fn test_with_mockall() {
    let mut mock = MockDatabase::new();
    mock.expect_get()
        .with(eq("key"))
        .times(1)
        .returning(|_| Some("value".to_string()));

    assert_eq!(mock.get("key"), Some("value".to_string()));
}
```

## Fixtures and Test Data

### Test Fixtures

```rust
// tests/fixtures/mod.rs

pub fn sample_config() -> &'static str {
    include_str!("fixtures/sample.kdl")
}

pub fn invalid_config() -> &'static str {
    include_str!("fixtures/invalid.kdl")
}
```

### Temporary Files

```rust
use tempfile::{tempdir, NamedTempFile};

#[test]
fn test_config_file() {
    let dir = tempdir().unwrap();
    let config_path = dir.path().join("sentinel.kdl");

    std::fs::write(&config_path, "server { }").unwrap();

    let config = parse_config(&config_path).unwrap();
    assert!(config.server.is_some());
}
```

### Property-Based Testing

```rust
use proptest::prelude::*;

proptest! {
    #[test]
    fn test_path_parsing_never_panics(s in ".*") {
        // Should never panic, even on random input
        let _ = parse_path(&s);
    }

    #[test]
    fn test_roundtrip(path in "/[a-z/]+") {
        let parsed = parse_path(&path).unwrap();
        assert_eq!(parsed.to_string(), path);
    }
}
```

## Coverage

### Using cargo-tarpaulin

```bash
# Install
cargo install cargo-tarpaulin

# Generate report
cargo tarpaulin --out Html

# Exclude test code
cargo tarpaulin --out Html --ignore-tests

# Only specific packages
cargo tarpaulin -p sentinel-core --out Html
```

### Using cargo-llvm-cov

```bash
# Install
cargo install cargo-llvm-cov

# Generate report
cargo llvm-cov --html

# Open report
open target/llvm-cov/html/index.html
```

## CI Testing

### GitHub Actions

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@stable

      - name: Run tests
        run: cargo test --all-features

      - name: Run clippy
        run: cargo clippy -- -D warnings

      - name: Check formatting
        run: cargo fmt --check
```

## Next Steps

- [Unit Tests](../unit-tests/) - Detailed unit testing guide
- [Integration Tests](../integration-tests/) - E2E testing
- [Load Testing](../load-testing/) - Performance testing

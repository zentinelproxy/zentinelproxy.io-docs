+++
title = "Unit Tests"
weight = 6
+++

Writing effective unit tests for Sentinel components.

## Unit Test Basics

### Test Structure

Follow the Arrange-Act-Assert pattern:

```rust
#[test]
fn test_route_matches_path() {
    // Arrange
    let route = Route::new("/api/users");

    // Act
    let matches = route.matches("/api/users");

    // Assert
    assert!(matches);
}
```

### Test Naming

Use descriptive names that explain what is being tested:

```rust
// Good: describes the scenario and expected outcome
#[test]
fn test_route_with_wildcard_matches_any_suffix() { }

#[test]
fn test_upstream_returns_error_when_all_targets_unhealthy() { }

#[test]
fn test_config_parser_rejects_duplicate_route_names() { }

// Bad: vague names
#[test]
fn test_route() { }

#[test]
fn test_error() { }
```

## Testing Patterns

### Testing Success Cases

```rust
#[test]
fn test_parse_valid_config() {
    let input = r#"
        server {
            worker-threads 4
        }
        listeners {
            listener "http" {
                address "0.0.0.0:8080"
            }
        }
    "#;

    let config = parse_config(input).unwrap();

    assert_eq!(config.server.worker_threads, 4);
    assert_eq!(config.listeners.len(), 1);
}
```

### Testing Error Cases

```rust
#[test]
fn test_parse_rejects_invalid_port() {
    let input = r#"
        listeners {
            listener "http" {
                address "0.0.0.0:99999"
            }
        }
    "#;

    let result = parse_config(input);

    assert!(result.is_err());
    let error = result.unwrap_err();
    assert!(error.to_string().contains("port"));
}
```

### Testing with Expected Errors

```rust
use std::assert_matches::assert_matches;

#[test]
fn test_specific_error_type() {
    let result = parse_config("invalid");

    assert_matches!(
        result,
        Err(ConfigError::ParseError { line: 1, .. })
    );
}
```

### Testing Edge Cases

```rust
#[test]
fn test_empty_input() {
    let result = parse_config("");
    assert!(result.is_err());
}

#[test]
fn test_whitespace_only() {
    let result = parse_config("   \n\t  ");
    assert!(result.is_err());
}

#[test]
fn test_maximum_routes() {
    let config = generate_config_with_routes(1000);
    let result = parse_config(&config);
    assert!(result.is_ok());
}

#[test]
fn test_unicode_in_path() {
    let route = Route::new("/api/用户");
    assert!(route.matches("/api/用户"));
}
```

## Testing Private Functions

### Using `#[cfg(test)]`

```rust
// src/lib.rs
fn internal_helper(x: i32) -> i32 {
    x * 2
}

pub fn public_function(x: i32) -> i32 {
    internal_helper(x) + 1
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_internal_helper() {
        // Can access private functions in tests
        assert_eq!(internal_helper(5), 10);
    }
}
```

### Testing via Public Interface

Prefer testing through public APIs when possible:

```rust
#[test]
fn test_public_function_uses_helper_correctly() {
    // Tests internal_helper indirectly
    assert_eq!(public_function(5), 11);  // 5*2 + 1
}
```

## Testing Complex Types

### Custom Assertions

```rust
fn assert_route_matches(route: &Route, path: &str) {
    assert!(
        route.matches(path),
        "Expected route {:?} to match path {:?}",
        route.pattern(),
        path
    );
}

fn assert_route_rejects(route: &Route, path: &str) {
    assert!(
        !route.matches(path),
        "Expected route {:?} NOT to match path {:?}",
        route.pattern(),
        path
    );
}

#[test]
fn test_route_patterns() {
    let route = Route::new("/api/*");

    assert_route_matches(&route, "/api/users");
    assert_route_matches(&route, "/api/users/123");
    assert_route_rejects(&route, "/other/path");
}
```

### Testing Collections

```rust
#[test]
fn test_route_priority_ordering() {
    let routes = vec![
        Route::new("/api/users").priority(100),
        Route::new("/api/*").priority(50),
        Route::new("/*").priority(10),
    ];

    let sorted = sort_by_priority(routes);

    assert_eq!(sorted[0].pattern(), "/api/users");
    assert_eq!(sorted[1].pattern(), "/api/*");
    assert_eq!(sorted[2].pattern(), "/*");
}
```

### Testing Structs with Many Fields

```rust
#[test]
fn test_config_defaults() {
    let config = Config::default();

    // Test important defaults explicitly
    assert_eq!(config.server.worker_threads, 0);  // auto
    assert_eq!(config.server.graceful_shutdown, Duration::from_secs(30));
    assert!(config.listeners.is_empty());

    // Use snapshot testing for full comparison
    insta::assert_debug_snapshot!(config);
}
```

## Parameterized Tests

### Using Arrays

```rust
#[test]
fn test_path_matching_cases() {
    let cases = [
        ("/api/users", "/api/users", true),
        ("/api/*", "/api/users", true),
        ("/api/*", "/other", false),
        ("/*", "/anything", true),
        ("/api/users", "/api/users/123", false),
    ];

    for (pattern, path, expected) in cases {
        let route = Route::new(pattern);
        assert_eq!(
            route.matches(path),
            expected,
            "Pattern {:?} with path {:?}",
            pattern,
            path
        );
    }
}
```

### Using test-case Crate

```rust
use test_case::test_case;

#[test_case("/api/users", "/api/users" => true ; "exact match")]
#[test_case("/api/*", "/api/users" => true ; "wildcard match")]
#[test_case("/api/*", "/other" => #false ; "wildcard no match")]
#[test_case("/*", "/anything" => true ; "root wildcard")]
fn test_route_matching(pattern: &str, path: &str) -> bool {
    Route::new(pattern).matches(path)
}
```

## Testing with rstest

```rust
use rstest::rstest;

#[rstest]
#[case("/api/users", "/api/users", true)]
#[case("/api/*", "/api/users", true)]
#[case("/api/*", "/other", false)]
fn test_route_matching(
    #[case] pattern: &str,
    #[case] path: &str,
    #[case] expected: bool,
) {
    let route = Route::new(pattern);
    assert_eq!(route.matches(path), expected);
}
```

### Fixtures with rstest

```rust
use rstest::*;

#[fixture]
fn sample_config() -> Config {
    Config::builder()
        .worker_threads(4)
        .timeout(Duration::from_secs(30))
        .build()
}

#[rstest]
fn test_config_worker_threads(sample_config: Config) {
    assert_eq!(sample_config.server.worker_threads, 4);
}

#[rstest]
fn test_config_timeout(sample_config: Config) {
    assert_eq!(sample_config.server.timeout, Duration::from_secs(30));
}
```

## Snapshot Testing

### Using insta

```rust
use insta::{assert_snapshot, assert_debug_snapshot};

#[test]
fn test_config_serialization() {
    let config = Config::default();
    let json = serde_json::to_string_pretty(&config).unwrap();

    assert_snapshot!(json);
}

#[test]
fn test_error_message_format() {
    let error = ConfigError::InvalidPort { port: 99999 };

    assert_snapshot!(error.to_string());
}

#[test]
fn test_route_debug_output() {
    let route = Route::new("/api/*").priority(100);

    assert_debug_snapshot!(route);
}
```

Updating snapshots:

```bash
# Review and accept changes
cargo insta test
cargo insta review

# Accept all changes
cargo insta test --accept
```

## Testing Panics

### Expected Panics

```rust
#[test]
#[should_panic(expected = "index out of bounds")]
fn test_panics_on_invalid_index() {
    let routes = vec![Route::new("/api")];
    let _ = routes[5];  // Panics
}
```

### Catching Panics

```rust
use std::panic;

#[test]
fn test_recovers_from_panic() {
    let result = panic::catch_unwind(|| {
        panic!("test panic");
    });

    assert!(result.is_err());
}
```

## Test Helpers

### Builder Pattern for Test Data

```rust
struct TestRequestBuilder {
    method: String,
    path: String,
    headers: Vec<(String, String)>,
}

impl TestRequestBuilder {
    fn new() -> Self {
        Self {
            method: "GET".to_string(),
            path: "/".to_string(),
            headers: vec![],
        }
    }

    fn method(mut self, method: &str) -> Self {
        self.method = method.to_string();
        self
    }

    fn path(mut self, path: &str) -> Self {
        self.path = path.to_string();
        self
    }

    fn header(mut self, name: &str, value: &str) -> Self {
        self.headers.push((name.to_string(), value.to_string()));
        self
    }

    fn build(self) -> Request {
        // Build actual request
    }
}

#[test]
fn test_with_builder() {
    let request = TestRequestBuilder::new()
        .method("POST")
        .path("/api/users")
        .header("Content-Type", "application/json")
        .build();

    // Test with request
}
```

## Best Practices

### Keep Tests Independent

```rust
// Bad: tests depend on shared state
static mut COUNTER: i32 = 0;

#[test]
fn test_increment() {
    unsafe { COUNTER += 1; }
    // Depends on test execution order
}

// Good: each test has its own state
#[test]
fn test_increment() {
    let mut counter = Counter::new();
    counter.increment();
    assert_eq!(counter.value(), 1);
}
```

### Test One Thing Per Test

```rust
// Bad: testing multiple things
#[test]
fn test_route() {
    let route = Route::new("/api/*");
    assert!(route.matches("/api/users"));
    assert!(!route.matches("/other"));
    assert_eq!(route.priority(), 0);
}

// Good: separate tests
#[test]
fn test_route_matches_valid_path() {
    let route = Route::new("/api/*");
    assert!(route.matches("/api/users"));
}

#[test]
fn test_route_rejects_invalid_path() {
    let route = Route::new("/api/*");
    assert!(!route.matches("/other"));
}

#[test]
fn test_route_default_priority() {
    let route = Route::new("/api/*");
    assert_eq!(route.priority(), 0);
}
```

### Use Clear Assertions

```rust
// Bad: unclear what's being tested
#[test]
fn test_something() {
    let result = process("input");
    assert!(result.is_some());
}

// Good: clear assertion message
#[test]
fn test_process_returns_value_for_valid_input() {
    let result = process("valid_input");
    assert!(
        result.is_some(),
        "Expected process to return Some for valid input"
    );
}
```

## Next Steps

- [Integration Tests](../integration-tests/) - Testing with real connections
- [Load Testing](../load-testing/) - Performance testing
- [Testing Overview](../testing/) - General testing strategy

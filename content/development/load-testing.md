+++
title = "Load Testing"
weight = 8
+++

Performance and stress testing for Sentinel.

## Load Testing Tools

### wrk

High-performance HTTP benchmarking tool:

```bash
# Install
brew install wrk  # macOS
sudo apt install wrk  # Ubuntu

# Basic usage
wrk -t12 -c400 -d30s http://localhost:8080/api/test

# Options:
#   -t12    12 threads
#   -c400   400 connections
#   -d30s   30 second duration
```

### hey

Simple HTTP load generator:

```bash
# Install
go install github.com/rakyll/hey@latest

# Basic usage
hey -n 10000 -c 100 http://localhost:8080/api/test

# Options:
#   -n 10000   10,000 requests total
#   -c 100     100 concurrent workers
```

### k6

Modern load testing with JavaScript:

```bash
# Install
brew install k6  # macOS
sudo apt install k6  # Ubuntu
```

## Basic Load Tests

### Throughput Test

Measure maximum requests per second:

```bash
# Start Sentinel
./sentinel -c sentinel.kdl &

# Run throughput test
wrk -t4 -c100 -d60s http://localhost:8080/health
```

Expected output:

```
Running 1m test @ http://localhost:8080/health
  4 threads and 100 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.23ms    0.45ms  15.32ms   92.45%
    Req/Sec    20.12k     1.23k   24.56k    85.12%
  4821456 requests in 1.00m, 512.34MB read
Requests/sec:  80357.60
Transfer/sec:      8.54MB
```

### Latency Test

Measure response time distribution:

```bash
hey -n 100000 -c 50 http://localhost:8080/api/users

# Output includes:
# - Response time histogram
# - Latency percentiles (p50, p90, p99)
# - Error rates
```

### Connection Test

Test connection handling:

```bash
# Many short-lived connections
wrk -t4 -c1000 -d30s --timeout 10s http://localhost:8080/health

# Keep-alive connections
wrk -t4 -c100 -d30s -H "Connection: keep-alive" http://localhost:8080/health
```

## k6 Test Scripts

### Basic Script

```javascript
// load_test.js
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
    stages: [
        { duration: '30s', target: 100 },  // Ramp up
        { duration: '1m', target: 100 },   // Steady state
        { duration: '30s', target: 0 },    // Ramp down
    ],
    thresholds: {
        http_req_duration: ['p(95)<200'],  // 95% under 200ms
        http_req_failed: ['rate<0.01'],    // Error rate under 1%
    },
};

export default function() {
    const response = http.get('http://localhost:8080/api/users');

    check(response, {
        'status is 200': (r) => r.status === 200,
        'response time < 200ms': (r) => r.timings.duration < 200,
    });

    sleep(0.1);  // Think time
}
```

Run:

```bash
k6 run load_test.js
```

### Stress Test Script

```javascript
// stress_test.js
import http from 'k6/http';
import { check } from 'k6';

export const options = {
    stages: [
        { duration: '2m', target: 100 },
        { duration: '5m', target: 100 },
        { duration: '2m', target: 200 },
        { duration: '5m', target: 200 },
        { duration: '2m', target: 300 },
        { duration: '5m', target: 300 },
        { duration: '10m', target: 0 },
    ],
};

export default function() {
    const response = http.get('http://localhost:8080/api/users');

    check(response, {
        'status is 200': (r) => r.status === 200,
    });
}
```

### Spike Test Script

```javascript
// spike_test.js
import http from 'k6/http';

export const options = {
    stages: [
        { duration: '10s', target: 100 },
        { duration: '1m', target: 100 },
        { duration: '10s', target: 1400 },  // Spike
        { duration: '3m', target: 1400 },
        { duration: '10s', target: 100 },
        { duration: '3m', target: 100 },
        { duration: '10s', target: 0 },
    ],
};

export default function() {
    http.get('http://localhost:8080/api/users');
}
```

## Testing Agents

### Agent Latency Impact

```javascript
// agent_overhead.js
import http from 'k6/http';
import { Trend } from 'k6/metrics';

const withAgent = new Trend('with_agent');
const withoutAgent = new Trend('without_agent');

export default function() {
    // Endpoint with WAF agent
    let r1 = http.get('http://localhost:8080/api/users');
    withAgent.add(r1.timings.duration);

    // Endpoint without agent
    let r2 = http.get('http://localhost:8080/health');
    withoutAgent.add(r2.timings.duration);
}
```

### Agent Under Load

Test agent behavior under pressure:

```bash
# Start agent with limited resources
sentinel-agent-waf --socket /tmp/waf.sock &

# Generate high load
wrk -t8 -c500 -d5m http://localhost:8080/api/test
```

Monitor agent metrics:

```bash
curl http://localhost:9091/metrics | grep agent
```

## Metrics Collection

### Prometheus Metrics During Load Test

```bash
# Start Prometheus
docker run -p 9090:9090 -v ./prometheus.yml:/etc/prometheus/prometheus.yml prom/prometheus

# During load test, query:
# - Request rate: rate(sentinel_requests_total[1m])
# - Latency p99: histogram_quantile(0.99, rate(sentinel_request_duration_seconds_bucket[1m]))
# - Error rate: rate(sentinel_requests_total{status=~"5.."}[1m])
```

### Recording Results

```bash
# Save wrk output
wrk -t4 -c100 -d60s http://localhost:8080/api/test 2>&1 | tee results.txt

# k6 with JSON output
k6 run --out json=results.json load_test.js

# k6 with InfluxDB
k6 run --out influxdb=http://localhost:8086/k6 load_test.js
```

## Benchmark Tests

### Cargo Benchmarks

Using criterion for micro-benchmarks:

```rust
// benches/routing.rs
use criterion::{criterion_group, criterion_main, Criterion};
use sentinel::routing::Router;

fn bench_route_matching(c: &mut Criterion) {
    let router = Router::from_config(test_config());

    c.bench_function("exact_path_match", |b| {
        b.iter(|| router.match_route("/api/users"))
    });

    c.bench_function("wildcard_match", |b| {
        b.iter(|| router.match_route("/api/users/123/posts/456"))
    });
}

criterion_group!(benches, bench_route_matching);
criterion_main!(benches);
```

Run benchmarks:

```bash
cargo bench

# Save baseline
cargo bench -- --save-baseline main

# Compare to baseline
cargo bench -- --baseline main
```

## Performance Profiling

### CPU Profiling with perf

```bash
# Linux
perf record -g ./target/release/sentinel -c sentinel.kdl &
# Run load test
perf report
```

### CPU Profiling with Instruments (macOS)

```bash
# Profile with Instruments
xcrun xctrace record --template 'Time Profiler' --launch ./target/release/sentinel -- -c sentinel.kdl
```

### Memory Profiling

```bash
# Using heaptrack
heaptrack ./target/release/sentinel -c sentinel.kdl &
# Run load test
heaptrack_gui heaptrack.sentinel.*.gz

# Using valgrind
valgrind --tool=massif ./target/release/sentinel -c sentinel.kdl
```

### Flamegraphs

```bash
# Install flamegraph
cargo install flamegraph

# Generate flamegraph
cargo flamegraph --bin sentinel -- -c sentinel.kdl &
# Run load test
# Stop sentinel

# View flamegraph.svg in browser
```

## Performance Checklist

### Before Release

1. **Baseline Performance**
   - [ ] Measure current RPS with `wrk`
   - [ ] Record p50, p95, p99 latencies
   - [ ] Document memory usage under load

2. **Regression Testing**
   - [ ] Compare against previous release
   - [ ] Check for latency increases
   - [ ] Verify no memory leaks

3. **Stress Testing**
   - [ ] Run 1-hour stress test
   - [ ] Monitor for degradation over time
   - [ ] Check connection handling under load

### Performance Targets

| Metric | Target | Minimum |
|--------|--------|---------|
| RPS (simple proxy) | 100,000 | 50,000 |
| p50 latency | < 1ms | < 5ms |
| p99 latency | < 10ms | < 50ms |
| Memory per connection | < 10KB | < 50KB |

## Troubleshooting Performance

### High Latency

```bash
# Check for blocking operations
RUST_LOG=trace cargo run -- -c sentinel.kdl 2>&1 | grep -i block

# Profile to find hot spots
cargo flamegraph
```

### Connection Issues

```bash
# Check file descriptor limits
ulimit -n
ulimit -n 65536

# Check connection states
ss -tan | awk '{print $1}' | sort | uniq -c
```

### Memory Growth

```bash
# Monitor memory over time
while true; do
    ps -o rss= -p $(pgrep sentinel)
    sleep 1
done | tee memory.log
```

## CI Performance Tests

### GitHub Actions

```yaml
name: Performance

on:
  push:
    branches: [main]

jobs:
  benchmark:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@stable

      - name: Run benchmarks
        run: cargo bench -- --save-baseline new

      - name: Compare benchmarks
        run: cargo bench -- --baseline main --load-baseline new
```

## Next Steps

- [Testing Overview](../testing/) - General testing strategy
- [Integration Tests](../integration-tests/) - E2E testing
- [Release Process](../releases/) - Performance requirements for releases

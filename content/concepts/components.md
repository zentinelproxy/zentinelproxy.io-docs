+++
title = "Component Design"
weight = 2
+++

Sentinel is organized as a Cargo workspace with four core crates. This page explains each component's responsibilities and how they interact.

## Crate Structure

```
sentinel/
├── crates/
│   ├── proxy/           # Main proxy binary and library
│   ├── config/          # Configuration parsing and validation
│   ├── agent-protocol/  # Agent communication protocol
│   └── common/          # Shared types and utilities
└── agents/
    └── echo/            # Reference agent implementation
```

## Proxy Crate

**Package**: `sentinel-proxy`
**Binary**: `sentinel`

The main proxy implementation that ties everything together.

### Key Modules

| Module | Purpose |
|--------|---------|
| `main.rs` | CLI entry point, signal handling |
| `proxy/` | Core proxy logic, Pingora integration |
| `routing.rs` | Route matching and compilation |
| `upstream/` | Upstream pool management, load balancing |
| `agents/` | Agent manager and coordination |
| `static_files/` | Static file serving |
| `health.rs` | Active and passive health checking |
| `reload/` | Configuration hot reload |
| `logging.rs` | Access, error, and audit logging |

### Proxy Module

The `SentinelProxy` struct implements Pingora's `ProxyHttp` trait:

```rust
impl ProxyHttp for SentinelProxy {
    // Select upstream target for request
    async fn upstream_peer(&self, session: &mut Session, ctx: &mut Context)
        -> Result<Box<HttpPeer>>;

    // Process request before forwarding
    async fn request_filter(&self, session: &mut Session, ctx: &mut Context)
        -> Result<bool>;

    // Process response before returning to client
    async fn response_filter(&self, session: &mut Session, ctx: &mut Context)
        -> Result<()>;

    // Log after request completes
    async fn logging(&self, session: &mut Session, ctx: &mut Context);
}
```

### Routing Module

Routes are compiled at startup for efficient matching:

```rust
pub struct RouteMatcher {
    routes: Vec<CompiledRoute>,  // Sorted by priority
    cache: LruCache<String, RouteId>,  // Path cache
}

pub struct CompiledRoute {
    id: RouteId,
    priority: Priority,
    matchers: Vec<CompiledMatcher>,
    specificity: u32,  // For tie-breaking
}

pub enum CompiledMatcher {
    Path(String),
    PathPrefix(String),
    PathRegex(Regex),
    Host(String),
    Method(Vec<Method>),
    Header { name: String, value: Option<String> },
    QueryParam { key: String, value: Option<String> },
}
```

### Upstream Module

Manages backend server pools with multiple load balancing strategies:

```rust
pub struct UpstreamPool {
    id: UpstreamId,
    targets: Vec<Target>,
    load_balancer: Box<dyn LoadBalancer>,
    health_checker: HealthChecker,
    circuit_breaker: CircuitBreaker,
    connection_pool: ConnectionPool,
}

pub trait LoadBalancer: Send + Sync {
    fn select(&self, targets: &[Target], ctx: &RequestContext) -> Option<&Target>;
}
```

**Load Balancing Algorithms**:

| Algorithm | Description | Use Case |
|-----------|-------------|----------|
| `round_robin` | Sequential rotation | General purpose |
| `least_connections` | Fewest active connections | Variable latency backends |
| `ip_hash` | Hash client IP | Session affinity |
| `consistent_hash` | Consistent hashing | Cache distribution |
| `p2c` | Power of Two Choices | Low latency selection |
| `adaptive` | Adjusts based on response times | Mixed workloads |

### Agent Module

Coordinates external agent communication:

```rust
pub struct AgentManager {
    agents: HashMap<AgentId, Agent>,
    pools: HashMap<AgentId, AgentConnectionPool>,
    circuit_breakers: HashMap<AgentId, CircuitBreaker>,
    metrics: AgentMetrics,
}

pub struct Agent {
    id: AgentId,
    transport: AgentTransport,
    timeout: Duration,
    failure_mode: FailureMode,
    events: Vec<EventType>,
}
```

## Config Crate

**Package**: `sentinel-config`

Handles configuration parsing, validation, and hot reload.

### Supported Formats

- **KDL** (primary) - Human-friendly document language
- **TOML** - Standard configuration format
- **YAML** - For Kubernetes integration
- **JSON** - For programmatic generation

### Configuration Structure

```rust
pub struct Config {
    pub server: ServerConfig,
    pub listeners: Vec<ListenerConfig>,
    pub routes: Vec<RouteConfig>,
    pub upstreams: HashMap<String, UpstreamConfig>,
    pub filters: HashMap<String, FilterConfig>,
    pub agents: Vec<AgentConfig>,
    pub waf: Option<WafConfig>,
    pub limits: Limits,
    pub observability: ObservabilityConfig,
}
```

### Key Types

```rust
pub struct RouteConfig {
    pub id: String,
    pub priority: Priority,
    pub matches: Vec<MatchCondition>,
    pub upstream: Option<String>,
    pub service_type: ServiceType,
    pub filters: Vec<String>,
    pub policies: RoutePolicies,
}

pub struct UpstreamConfig {
    pub targets: Vec<TargetConfig>,
    pub load_balancing: LoadBalancingAlgorithm,
    pub health_check: Option<HealthCheckConfig>,
    pub timeouts: TimeoutConfig,
    pub circuit_breaker: Option<CircuitBreakerConfig>,
}

pub struct AgentConfig {
    pub id: String,
    pub agent_type: AgentType,
    pub transport: AgentTransport,
    pub events: Vec<EventType>,
    pub timeout_ms: u64,
    pub failure_mode: FailureMode,
}
```

### Validation

Configuration is validated at multiple levels:

1. **Schema validation** - Structure and types
2. **Semantic validation** - Cross-references (route → upstream)
3. **Custom validators** - Business rules

```rust
pub trait ConfigValidator {
    fn validate(&self, config: &Config) -> Result<(), Vec<ValidationError>>;
}
```

### Hot Reload

Configuration changes are applied atomically:

```rust
pub struct ConfigManager {
    config: ArcSwap<Config>,
    watcher: FileWatcher,
    validators: Vec<Box<dyn ConfigValidator>>,
    subscribers: Vec<Sender<ReloadEvent>>,
}

pub enum ReloadEvent {
    Applied(Arc<Config>),
    Failed(ValidationError),
}
```

## Agent Protocol Crate

**Package**: `sentinel-agent-protocol`

Defines the contract between Sentinel and external agents.

### Transport Options

| Transport | Format | Use Case |
|-----------|--------|----------|
| Unix Socket | JSON | Default, same-host agents |
| gRPC | Protobuf | Cross-host, high-performance |

### Protocol Types

```rust
pub enum EventType {
    RequestHeaders,
    RequestBodyChunk,
    ResponseHeaders,
    ResponseBodyChunk,
    RequestComplete,
}

pub struct AgentRequest {
    pub event_type: EventType,
    pub correlation_id: String,
    pub request_id: String,
    pub metadata: RequestMetadata,
    pub headers: Vec<Header>,
    pub body_chunk: Option<Vec<u8>>,
}

pub struct AgentResponse {
    pub decision: Decision,
    pub header_mutations: HeaderMutations,
    pub metadata: HashMap<String, String>,
    pub audit: AuditInfo,
}

pub enum Decision {
    Allow,
    Block { status: u16, body: Option<String> },
    Redirect { url: String, status: u16 },
    Challenge { challenge_type: String, data: String },
}
```

### Header Mutations

Agents can modify request and response headers:

```rust
pub struct HeaderMutations {
    pub request: HeaderOps,
    pub response: HeaderOps,
}

pub struct HeaderOps {
    pub set: HashMap<String, String>,    // Replace or create
    pub add: HashMap<String, String>,    // Append
    pub remove: Vec<String>,             // Delete
}
```

### Client and Server

```rust
// Proxy side - calls agents
pub struct AgentClient {
    transport: Transport,
    timeout: Duration,
}

impl AgentClient {
    pub async fn call(&self, request: AgentRequest) -> Result<AgentResponse>;
}

// Agent side - receives calls
pub struct AgentServer {
    transport: Transport,
    handler: Box<dyn AgentHandler>,
}

pub trait AgentHandler: Send + Sync {
    async fn handle(&self, request: AgentRequest) -> AgentResponse;
}
```

## Common Crate

**Package**: `sentinel-common`

Shared types and utilities used across all crates.

### Type-Safe IDs

```rust
// Strongly typed identifiers prevent mix-ups
pub struct CorrelationId(String);
pub struct RequestId(String);
pub struct RouteId(String);
pub struct UpstreamId(String);
pub struct AgentId(String);
```

### Error Types

```rust
pub enum SentinelError {
    Config(ConfigError),
    Routing(RoutingError),
    Upstream(UpstreamError),
    Agent(AgentError),
    Validation(ValidationError),
    Io(std::io::Error),
}

pub type SentinelResult<T> = Result<T, SentinelError>;
```

### Circuit Breaker

```rust
pub struct CircuitBreaker {
    state: AtomicState,
    failure_threshold: u32,
    success_threshold: u32,
    timeout: Duration,
    failure_count: AtomicU32,
    success_count: AtomicU32,
    last_failure: AtomicInstant,
}

pub enum CircuitState {
    Closed,   // Normal operation
    Open,     // Failing, fast-reject
    HalfOpen, // Testing recovery
}
```

### Limits

```rust
pub struct Limits {
    pub max_header_count: usize,
    pub max_header_size_bytes: usize,
    pub max_body_size_bytes: usize,
    pub max_connections_per_client: usize,
    pub max_total_connections: usize,
    pub max_in_flight_requests: usize,
}
```

### Observability

```rust
pub struct RequestMetrics {
    pub route_id: RouteId,
    pub method: Method,
    pub status_code: u16,
    pub latency: Duration,
    pub upstream_latency: Option<Duration>,
    pub bytes_in: u64,
    pub bytes_out: u64,
}
```

## Component Interactions

```
┌─────────────────────────────────────────────────────────────────┐
│                         sentinel-proxy                           │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────────────────┐│
│  │ Routing │  │Upstream │  │ Agents  │  │    Static Files     ││
│  └────┬────┘  └────┬────┘  └────┬────┘  └─────────────────────┘│
│       │            │            │                               │
└───────┼────────────┼────────────┼───────────────────────────────┘
        │            │            │
        │            │            │
┌───────▼────────────▼────────────▼───────────────────────────────┐
│                       sentinel-config                            │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │   Parsing   │  │  Validation  │  │     Hot Reload         │ │
│  └─────────────┘  └──────────────┘  └────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
        │
        │
┌───────▼─────────────────────────────────────────────────────────┐
│                    sentinel-agent-protocol                       │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │   Client    │  │    Types     │  │      Server            │ │
│  └─────────────┘  └──────────────┘  └────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
        │
        │
┌───────▼─────────────────────────────────────────────────────────┐
│                       sentinel-common                            │
│  ┌─────────┐  ┌──────────┐  ┌─────────┐  ┌──────────────────┐  │
│  │  Types  │  │  Errors  │  │ Circuit │  │  Observability   │  │
│  │  (IDs)  │  │          │  │ Breaker │  │                  │  │
│  └─────────┘  └──────────┘  └─────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Next Steps

- [Architecture Overview](../architecture/) - High-level design
- [Request Flow](../request-flow/) - Detailed request lifecycle
- [Routing System](../routing/) - How routes are matched

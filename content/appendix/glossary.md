+++
title = "Glossary"
weight = 3
+++

Definitions of key terms used throughout Sentinel documentation.

## A

### Agent
An external process that handles request processing tasks like authentication, rate limiting, or WAF inspection. Agents communicate with Sentinel via Unix sockets or gRPC.

### ALPN (Application-Layer Protocol Negotiation)
A TLS extension that allows the application layer to negotiate which protocol should be performed over a secure connection, enabling HTTP/2 or HTTP/3 negotiation.

## B

### Backend
See [Upstream](#upstream).

### Backoff
A strategy for retrying failed requests with increasing delays between attempts. Sentinel supports exponential backoff with configurable base and maximum delays.

## C

### Circuit Breaker
A fault tolerance pattern that prevents cascading failures by temporarily stopping requests to an unhealthy upstream. States include closed (normal), open (blocking), and half-open (testing).

### Connection Pool
A cache of reusable connections to upstream servers, reducing the overhead of establishing new connections for each request.

### Correlation ID
A unique identifier assigned to each request for tracing through logs and distributed systems. Sentinel uses the `X-Correlation-Id` header.

## D

### Downstream
The client side of the proxy - the entity making requests to Sentinel. Opposite of [upstream](#upstream).

## F

### Failover
The process of automatically switching to a backup upstream server when the primary server fails.

### Filter
A processing component that modifies requests or responses as they pass through Sentinel. Filters can add headers, transform bodies, or enforce policies.

## G

### Graceful Shutdown
A shutdown process that allows in-flight requests to complete before the server stops, preventing dropped connections.

### gRPC
A high-performance RPC framework using HTTP/2 and Protocol Buffers. Sentinel can proxy gRPC traffic and use gRPC for agent communication.

## H

### Health Check
A periodic probe to determine if an upstream server is healthy and able to receive traffic. Supports HTTP, TCP, and gRPC protocols.

### Hot Reload
The ability to reload configuration without restarting the server or dropping connections. Triggered by `SIGHUP` signal.

## K

### KDL (KDL Document Language)
The configuration file format used by Sentinel. A human-friendly, document-oriented configuration language.

### Keepalive
A mechanism to maintain persistent connections between client and server, reducing connection establishment overhead.

## L

### Listener
A network endpoint where Sentinel accepts incoming connections. Defined by address, port, and protocol (HTTP, HTTPS, H2, H3).

### Load Balancing
The distribution of incoming requests across multiple upstream servers. Algorithms include round robin, least connections, IP hash, and weighted random.

## M

### Middleware
See [Filter](#filter).

### mTLS (Mutual TLS)
TLS authentication where both client and server present certificates to verify each other's identity.

## O

### OCSP Stapling
A method for checking certificate revocation status where the server periodically obtains a signed OCSP response and includes it in the TLS handshake.

## P

### Pingora
The Rust-based proxy framework developed by Cloudflare that powers Sentinel's core networking capabilities.

### Policy
Configuration that defines how requests are processed for a specific route, including timeouts, rate limits, header modifications, and retry behavior.

### Proxy
A server that acts as an intermediary between clients and backend servers. Sentinel is a reverse proxy.

## Q

### QUIC
A UDP-based transport protocol that provides the foundation for HTTP/3, offering reduced latency and improved connection migration.

## R

### Rate Limiting
Controlling the number of requests a client can make within a time period. Configurable per client IP, route, or globally.

### Retry Policy
Configuration defining how Sentinel handles failed upstream requests, including maximum attempts, retryable status codes, and backoff strategy.

### Reverse Proxy
A proxy server that sits in front of backend servers and forwards client requests to them. Sentinel is a reverse proxy.

### Route
A rule that matches incoming requests based on criteria (path, host, headers) and directs them to an upstream or handler.

### Round Robin
A load balancing algorithm that distributes requests sequentially across upstream servers in rotation.

## S

### Session Resumption
A TLS optimization that allows clients to resume previous sessions without a full handshake, reducing latency.

### SNI (Server Name Indication)
A TLS extension that allows a client to indicate which hostname it's connecting to, enabling multiple TLS certificates on a single IP address.

### Static Files
Files served directly from disk without backend processing. Sentinel can serve static content with caching and compression.

## T

### Target
An individual server within an upstream group, identified by address and optional weight.

### TLS (Transport Layer Security)
A cryptographic protocol for secure communication. Sentinel supports TLS 1.2 and 1.3 for both client connections and upstream connections.

### Tinyflake
A compact, time-ordered unique ID format used by Sentinel for correlation IDs. More compact than UUIDs.

## U

### Upstream
A backend server or group of servers that Sentinel forwards requests to. Also called "backend" in other proxy software.

## W

### WAF (Web Application Firewall)
A security layer that filters and monitors HTTP traffic to protect against common web exploits like SQL injection and XSS.

### Weight
A value assigned to upstream targets that influences load balancing distribution. Higher weights receive proportionally more traffic.

### Worker Thread
An OS thread dedicated to processing requests. Sentinel uses multiple worker threads for parallel request handling.

## Numbers

### 0-RTT (Zero Round Trip Time)
A TLS 1.3 feature allowing data to be sent on the first flight of the handshake, reducing latency for repeat connections.


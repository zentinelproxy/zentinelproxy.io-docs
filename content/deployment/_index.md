+++
title = "Deployment"
weight = 8
sort_by = "weight"
template = "section.html"
+++

Sentinel is designed for flexible deployment across environments—from single-binary development setups to distributed Kubernetes clusters.

## Deployment Philosophy

Sentinel follows a **separation of concerns** model:

| Component | Responsibility |
|-----------|----------------|
| **Sentinel proxy** | Route traffic, call agents, circuit breaking |
| **Agents** | Security logic, custom processing |
| **Process supervisor** | Lifecycle management (systemd, Docker, K8s) |

Sentinel intentionally does **not** manage agent lifecycles. Process supervision is a solved problem—systemd, Docker, and Kubernetes do it better than we could. This keeps the proxy lean and focused.

## Deployment Tiers

```
┌─────────────────────────────────────────────────────────────────┐
│                     DEPLOYMENT OPTIONS                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Development:        sentinel-stack                             │
│                      └── Single command, spawns everything      │
│                                                                 │
│  Production (VMs):   systemd with socket activation             │
│                      └── Independent services, proper isolation │
│                                                                 │
│  Cloud-native:       Kubernetes / Docker Compose                │
│                      └── Containers, sidecars, service mesh     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Comparison

| Deployment | Best For | Agents | Complexity |
|------------|----------|--------|------------|
| [sentinel-stack](architecture/) | Development, simple setups | Child processes | Minimal |
| [systemd](systemd/) | Production VMs, bare metal | Socket-activated services | Low |
| [Docker Compose](docker-compose/) | Local development, small prod | Sidecar containers | Medium |
| [Kubernetes](kubernetes/) | Cloud-native, scale-out | Pods, service mesh | Higher |

## Agent Connectivity

Regardless of deployment model, agents connect via:

- **Unix sockets** — Local agents, lowest latency (~50-100µs)
- **gRPC** — Remote agents, scalable, polyglot (~100-500µs)

See [Agent Transports](/agents/transports/) for protocol details.

## Documentation

| Page | Description |
|------|-------------|
| [Architecture](architecture/) | Deployment philosophy and agent lifecycle |
| [sentinel-stack](sentinel-stack/) | All-in-one launcher for development |
| [systemd](systemd/) | Production deployment with systemd |
| [Docker Compose](docker-compose/) | Container-based local/small deployments |
| [Kubernetes](kubernetes/) | Cloud-native deployment patterns |
| [Service Mesh](service-mesh/) | Istio, Linkerd, and Consul Connect integration |
| [Monitoring](monitoring/) | Observability and health checks |

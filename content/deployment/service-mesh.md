+++
title = "Service Mesh Integration"
weight = 7
+++

Sentinel integrates with service mesh environments through dynamic service discovery and mTLS support. While not a service mesh itself, Sentinel can serve as an ingress gateway or edge proxy in mesh deployments.

## Integration Patterns

```
┌─────────────────────────────────────────────────────────────────────┐
│                    SERVICE MESH INTEGRATION                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Pattern 1: Ingress Gateway                                          │
│  ┌──────────┐      ┌──────────┐      ┌──────────┐                   │
│  │ Internet │─────▶│ Sentinel │─────▶│ Mesh     │                   │
│  │          │      │ (edge)   │      │ Services │                   │
│  └──────────┘      └──────────┘      └──────────┘                   │
│                          │                                           │
│                    Service Discovery                                 │
│                    (DNS/Consul/K8s)                                  │
│                                                                      │
│  Pattern 2: Sidecar-Adjacent                                         │
│  ┌──────────┐      ┌──────────────────────────┐                     │
│  │ Internet │─────▶│ Pod                       │                     │
│  │          │      │ ┌────────┐  ┌──────────┐ │                     │
│  └──────────┘      │ │Sentinel│─▶│ Sidecar  │ │                     │
│                    │ │        │  │(Envoy/   │ │                     │
│                    │ └────────┘  │ Linkerd) │ │                     │
│                    └─────────────┴──────────┴─┘                     │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Service Discovery Methods

Sentinel supports multiple discovery backends that integrate with service mesh control planes:

| Method | Mesh Compatibility | Use Case |
|--------|-------------------|----------|
| DNS | All (Istio, Linkerd, Consul) | Simple, universal |
| Consul | Consul Connect | Native Consul integration |
| Kubernetes | Istio, Linkerd | K8s-native endpoint discovery |

### DNS Discovery

Works with any service mesh that provides DNS-based service discovery (all major meshes do).

```kdl
upstream "api-service" {
    discovery "dns" {
        hostname "api.default.svc.cluster.local"
        port 8080
        refresh-interval 30
    }
}
```

**Mesh DNS patterns:**

| Mesh | DNS Format |
|------|------------|
| Kubernetes | `<service>.<namespace>.svc.cluster.local` |
| Consul | `<service>.service.consul` |
| Istio | Standard K8s DNS (with VirtualService routing) |
| Linkerd | Standard K8s DNS |

### Consul Discovery

Native integration with Consul's service catalog and health checking.

```kdl
upstream "backend" {
    discovery "consul" {
        address "http://consul.service.consul:8500"
        service "backend-api"
        datacenter "dc1"
        only-passing true
        tag "production"
        refresh-interval 10
    }
}
```

| Option | Default | Description |
|--------|---------|-------------|
| `address` | Required | Consul HTTP API address |
| `service` | Required | Service name in catalog |
| `datacenter` | None | Target datacenter |
| `only-passing` | `true` | Only healthy instances |
| `tag` | None | Filter by service tag |
| `refresh-interval` | `10` | Seconds between refreshes |

#### Consul Connect Integration

When using Consul Connect (service mesh), Sentinel can discover services but connects directly (not through Connect proxies). For full Connect mTLS:

```kdl
upstream "secure-backend" {
    discovery "consul" {
        address "http://consul:8500"
        service "backend"
        only-passing true
    }
    tls {
        // Use Consul-provisioned certificates
        client-cert "/etc/consul/certs/client.crt"
        client-key "/etc/consul/certs/client.key"
        ca-cert "/etc/consul/certs/ca.crt"
    }
}
```

### Kubernetes Endpoint Discovery

Direct integration with Kubernetes Endpoints API for real-time pod discovery.

```kdl
upstream "k8s-backend" {
    discovery "kubernetes" {
        namespace "production"
        service "api-server"
        port-name "http"
        refresh-interval 10
    }
}
```

#### Authentication Methods

**In-cluster (recommended for K8s deployments):**

```kdl
upstream "backend" {
    discovery "kubernetes" {
        namespace "default"
        service "my-service"
        // Uses service account token automatically
    }
}
```

**Kubeconfig file (for external access):**

```kdl
upstream "backend" {
    discovery "kubernetes" {
        namespace "production"
        service "api"
        kubeconfig "~/.kube/config"
    }
}
```

| Auth Method | Source | Use Case |
|-------------|--------|----------|
| Service Account | In-cluster token | Pods running in K8s |
| Kubeconfig | File on disk | External access, dev |
| Token | Bearer token in kubeconfig | CI/CD pipelines |
| Client Cert | mTLS in kubeconfig | High security |
| Exec | External command (e.g., `aws eks`) | Cloud provider auth |

## Istio Integration

Sentinel works alongside Istio as an ingress gateway or within the mesh.

### As Istio Ingress Gateway

Deploy Sentinel outside the mesh to handle external traffic:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sentinel-gateway
  namespace: istio-system
spec:
  template:
    metadata:
      annotations:
        sidecar.istio.io/inject: "false"  # No Istio sidecar
    spec:
      containers:
      - name: sentinel
        image: ghcr.io/raskell-io/sentinel:latest
```

Configure Sentinel to discover Istio services:

```kdl
upstream "frontend" {
    discovery "kubernetes" {
        namespace "default"
        service "frontend"
        port-name "http"
    }
    // Connect directly to pods, bypassing Istio sidecar
}
```

### Within Istio Mesh

Deploy Sentinel with Istio sidecar injection:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sentinel
spec:
  template:
    metadata:
      annotations:
        sidecar.istio.io/inject: "true"
    spec:
      containers:
      - name: sentinel
        # Traffic flows through Envoy sidecar
```

In this mode, Sentinel routes to `localhost` and Istio handles service discovery:

```kdl
upstream "backend" {
    targets {
        target { address "127.0.0.1:15001" }  // Istio outbound
    }
    // Istio sidecar handles discovery and mTLS
}
```

## Linkerd Integration

Linkerd uses a transparent proxy model. Sentinel works naturally within Linkerd-meshed namespaces.

### Meshed Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sentinel
  annotations:
    linkerd.io/inject: enabled
spec:
  template:
    spec:
      containers:
      - name: sentinel
```

Sentinel discovers services normally; Linkerd handles mTLS:

```kdl
upstream "api" {
    discovery "kubernetes" {
        namespace "default"
        service "api"
        port-name "http"
    }
    // Linkerd proxy handles connection security
}
```

### Unmeshed (Ingress) Deployment

For ingress, deploy without Linkerd injection:

```yaml
metadata:
  annotations:
    linkerd.io/inject: disabled
```

Use Kubernetes discovery to find meshed services:

```kdl
upstream "meshed-service" {
    discovery "kubernetes" {
        namespace "production"
        service "api"
    }
    // Direct connection to pod IPs
}
```

## mTLS Configuration

For direct mTLS (without mesh sidecar), configure upstream TLS:

```kdl
upstream "secure-backend" {
    discovery "kubernetes" {
        namespace "production"
        service "secure-api"
    }
    tls {
        sni "secure-api.production.svc.cluster.local"
        client-cert "/etc/sentinel/certs/client.crt"
        client-key "/etc/sentinel/certs/client.key"
        ca-cert "/etc/sentinel/certs/ca.crt"
    }
}
```

### Certificate Sources

| Source | Configuration |
|--------|--------------|
| Kubernetes Secret | Mount as volume |
| Consul PKI | Use Consul CA endpoints |
| cert-manager | Automatic certificate provisioning |
| Vault | Dynamic secrets |

Example with cert-manager:

```yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: sentinel-client-cert
spec:
  secretName: sentinel-client-tls
  issuerRef:
    name: mesh-ca
    kind: ClusterIssuer
  dnsNames:
  - sentinel.default.svc.cluster.local
---
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      volumes:
      - name: client-certs
        secret:
          secretName: sentinel-client-tls
      containers:
      - name: sentinel
        volumeMounts:
        - name: client-certs
          mountPath: /etc/sentinel/certs
```

## Health Checks

Configure health checks that work with mesh health reporting:

```kdl
upstream "backend" {
    discovery "kubernetes" {
        namespace "default"
        service "api"
    }
    health-check {
        type "http" {
            path "/health"
            expected-status 200
        }
        interval-secs 10
        unhealthy-threshold 3
    }
}
```

Sentinel health checks run independently of mesh health checks, providing defense in depth.

## Load Balancing

Sentinel performs client-side load balancing across discovered endpoints:

```kdl
upstream "api" {
    discovery "kubernetes" {
        namespace "default"
        service "api"
    }
    load-balancing "least_connections"
}
```

| Algorithm | Mesh Compatibility |
|-----------|-------------------|
| `round_robin` | All |
| `least_connections` | All |
| `consistent_hash` | All (good for caching) |
| `random` | All |
| `power_of_two_choices` | All |

**Note:** When running inside a mesh with sidecar, the sidecar may also perform load balancing. Consider using `round_robin` in Sentinel to avoid double load balancing.

## Observability

Sentinel exposes metrics compatible with mesh observability:

```kdl
observability {
    metrics {
        enabled true
        endpoint "/metrics"
    }
}
```

### Key Metrics for Mesh Deployments

| Metric | Description |
|--------|-------------|
| `sentinel_upstream_healthy_backends` | Healthy endpoints per upstream |
| `sentinel_upstream_attempts_total` | Connection attempts |
| `sentinel_upstream_failures_total` | Failed connections by reason |
| `sentinel_requests_total` | Request count by route/status |

Integrate with mesh observability:
- **Prometheus**: Scrape `/metrics` endpoint
- **Jaeger/Tempo**: Configure OpenTelemetry export
- **Grafana**: Use provided dashboard template

## Limitations

Current service mesh integration limitations:

| Feature | Status | Notes |
|---------|--------|-------|
| xDS API (Envoy config) | Not supported | No Istio control plane integration |
| Automatic mTLS rotation | Manual | Use cert-manager or Vault |
| Traffic policies from mesh | Not supported | Configure in Sentinel directly |
| SPIFFE identity | Not supported | Use standard X.509 certs |
| Canary/subset routing | Manual | Configure via route weights |

### Workarounds

**For automatic mTLS rotation:**
- Use cert-manager with short-lived certificates
- Mount certificates from Kubernetes secrets
- Use SIGHUP to reload certificates

**For traffic policies:**
- Configure timeouts, retries, and circuit breakers in Sentinel
- Use Sentinel's rate limiting instead of mesh rate limiting

## Complete Example

Full Kubernetes deployment with Consul discovery:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: sentinel-config
data:
  sentinel.kdl: |
    listener "http" {
        address "0.0.0.0:8080"
    }

    upstream "api" {
        discovery "consul" {
            address "http://consul.consul:8500"
            service "api"
            only-passing true
            refresh-interval 10
        }
        health-check {
            type "http" { path "/health" }
            interval-secs 10
        }
        load-balancing "least_connections"
    }

    routes {
        route "api" {
            matches { path-prefix "/api/" }
            upstream "api"
        }
    }
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sentinel
spec:
  replicas: 2
  selector:
    matchLabels:
      app: sentinel
  template:
    metadata:
      labels:
        app: sentinel
    spec:
      containers:
      - name: sentinel
        image: ghcr.io/raskell-io/sentinel:latest
        ports:
        - containerPort: 8080
        volumeMounts:
        - name: config
          mountPath: /etc/sentinel
        readinessProbe:
          httpGet:
            path: /_/health
            port: 8080
      volumes:
      - name: config
        configMap:
          name: sentinel-config
---
apiVersion: v1
kind: Service
metadata:
  name: sentinel
spec:
  ports:
  - port: 80
    targetPort: 8080
  selector:
    app: sentinel
```

## Next Steps

- [Kubernetes Deployment](../kubernetes/) - Detailed K8s deployment guide
- [Monitoring](../monitoring/) - Observability setup
- [Upstreams Configuration](/configuration/upstreams/) - Discovery options

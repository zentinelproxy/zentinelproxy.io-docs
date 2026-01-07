+++
title = "Kubernetes"
weight = 5
+++

Kubernetes provides the most flexible deployment model for Sentinel, supporting multiple patterns from simple sidecar deployments to sophisticated service mesh integrations.

## Deployment Patterns

| Pattern | Description | Best For |
|---------|-------------|----------|
| **Sidecar** | Agents in same pod as Sentinel | Simple setups, low latency |
| **Service** | Agents as separate deployments | Shared agents, independent scaling |
| **DaemonSet** | Sentinel on every node | Edge/gateway deployments |

## Pattern 1: Sidecar Deployment

Agents run as sidecar containers in the same pod as Sentinel.

```yaml
# sentinel-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sentinel
  labels:
    app: sentinel
spec:
  replicas: 3
  selector:
    matchLabels:
      app: sentinel
  template:
    metadata:
      labels:
        app: sentinel
    spec:
      containers:
        # ─────────────────────────────────────────────────
        # Sentinel Proxy
        # ─────────────────────────────────────────────────
        - name: sentinel
          image: ghcr.io/raskell-io/sentinel:latest
          ports:
            - name: http
              containerPort: 8080
            - name: admin
              containerPort: 9090
          volumeMounts:
            - name: config
              mountPath: /etc/sentinel
              readOnly: true
            - name: sockets
              mountPath: /var/run/sentinel
          resources:
            requests:
              cpu: "100m"
              memory: "128Mi"
            limits:
              cpu: "1000m"
              memory: "512Mi"
          livenessProbe:
            httpGet:
              path: /health
              port: admin
            initialDelaySeconds: 5
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /ready
              port: admin
            initialDelaySeconds: 5
            periodSeconds: 5

        # ─────────────────────────────────────────────────
        # Auth Agent (sidecar)
        # ─────────────────────────────────────────────────
        - name: auth-agent
          image: ghcr.io/raskell-io/sentinel-auth:latest
          args:
            - "--socket"
            - "/var/run/sentinel/auth.sock"
          volumeMounts:
            - name: sockets
              mountPath: /var/run/sentinel
            - name: auth-secrets
              mountPath: /etc/auth/secrets
              readOnly: true
          env:
            - name: AUTH_SECRET
              valueFrom:
                secretKeyRef:
                  name: sentinel-secrets
                  key: auth-secret
          resources:
            requests:
              cpu: "50m"
              memory: "64Mi"
            limits:
              cpu: "200m"
              memory: "128Mi"

        # ─────────────────────────────────────────────────
        # WAF Agent (sidecar, gRPC)
        # ─────────────────────────────────────────────────
        - name: waf-agent
          image: ghcr.io/raskell-io/sentinel-waf:latest
          args:
            - "--grpc"
            - "127.0.0.1:50051"
          resources:
            requests:
              cpu: "100m"
              memory: "256Mi"
            limits:
              cpu: "500m"
              memory: "512Mi"
          livenessProbe:
            grpc:
              port: 50051
            initialDelaySeconds: 5
            periodSeconds: 10

      volumes:
        - name: config
          configMap:
            name: sentinel-config
        - name: sockets
          emptyDir: {}
        - name: auth-secrets
          secret:
            secretName: sentinel-secrets
---
apiVersion: v1
kind: Service
metadata:
  name: sentinel
spec:
  selector:
    app: sentinel
  ports:
    - name: http
      port: 80
      targetPort: 8080
    - name: admin
      port: 9090
      targetPort: 9090
  type: LoadBalancer
```

### ConfigMap

```yaml
# sentinel-configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: sentinel-config
data:
  sentinel.kdl: |
    server {
        listen "0.0.0.0:8080"
    }

    admin {
        listen "0.0.0.0:9090"
    }

    agents {
        agent "auth" type="auth" {
            unix-socket "/var/run/sentinel/auth.sock"
            events "request_headers"
            timeout-ms 50
            failure-mode "closed"
        }

        agent "waf" type="waf" {
            grpc "http://127.0.0.1:50051"
            events "request_headers" "request_body"
            timeout-ms 100
            failure-mode "open"
        }
    }

    upstreams {
        upstream "api" {
            target "api-service.default.svc.cluster.local:80"
        }
    }

    routes {
        route "api" {
            matches { path-prefix "/api/" }
            upstream "api"
            agents "auth" "waf"
        }
    }
```

### Secrets

```yaml
# sentinel-secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: sentinel-secrets
type: Opaque
data:
  auth-secret: <base64-encoded-secret>
```

## Pattern 2: Separate Service

Agents run as independent deployments, accessed via Kubernetes services.

```yaml
# waf-agent-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: waf-agent
  labels:
    app: waf-agent
spec:
  replicas: 3
  selector:
    matchLabels:
      app: waf-agent
  template:
    metadata:
      labels:
        app: waf-agent
    spec:
      containers:
        - name: waf-agent
          image: ghcr.io/raskell-io/sentinel-waf:latest
          args:
            - "--grpc"
            - "0.0.0.0:50051"
          ports:
            - name: grpc
              containerPort: 50051
          resources:
            requests:
              cpu: "200m"
              memory: "256Mi"
            limits:
              cpu: "1000m"
              memory: "1Gi"
          livenessProbe:
            grpc:
              port: 50051
            initialDelaySeconds: 10
            periodSeconds: 10
          readinessProbe:
            grpc:
              port: 50051
            initialDelaySeconds: 5
            periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: waf-agent
spec:
  selector:
    app: waf-agent
  ports:
    - name: grpc
      port: 50051
      targetPort: 50051
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: waf-agent-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: waf-agent
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```

Update Sentinel config to use the service:

```kdl
agent "waf" type="waf" {
    grpc "http://waf-agent.default.svc.cluster.local:50051"
    events "request_headers" "request_body"
    timeout-ms 200
    failure-mode "open"
}
```

## Pattern 3: DaemonSet (Edge Gateway)

Run Sentinel on every node for edge/gateway scenarios.

```yaml
# sentinel-daemonset.yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: sentinel-edge
  labels:
    app: sentinel-edge
spec:
  selector:
    matchLabels:
      app: sentinel-edge
  template:
    metadata:
      labels:
        app: sentinel-edge
    spec:
      hostNetwork: true
      dnsPolicy: ClusterFirstWithHostNet
      containers:
        - name: sentinel
          image: ghcr.io/raskell-io/sentinel:latest
          ports:
            - name: http
              containerPort: 80
              hostPort: 80
            - name: https
              containerPort: 443
              hostPort: 443
          volumeMounts:
            - name: config
              mountPath: /etc/sentinel
          securityContext:
            capabilities:
              add:
                - NET_BIND_SERVICE
      volumes:
        - name: config
          configMap:
            name: sentinel-edge-config
      tolerations:
        - key: node-role.kubernetes.io/master
          effect: NoSchedule
```

## Helm Chart

### Installation

```bash
# Clone the repository
git clone https://github.com/raskell-io/sentinel.git
cd sentinel

# Install with default values
helm install sentinel ./deploy/helm/sentinel

# Install with custom values
helm install sentinel ./deploy/helm/sentinel -f values.yaml

# Or install directly from GitHub (OCI registry coming soon)
helm install sentinel oci://ghcr.io/raskell-io/charts/sentinel --version 0.1.3
```

### values.yaml

```yaml
# values.yaml
replicaCount: 3

image:
  repository: ghcr.io/raskell-io/sentinel
  tag: latest
  pullPolicy: IfNotPresent

service:
  type: LoadBalancer
  httpPort: 80
  httpsPort: 443
  adminPort: 9090

config:
  sentinel.kdl: |
    server {
        listen "0.0.0.0:8080"
    }
    # ... rest of config

agents:
  auth:
    enabled: true
    image: ghcr.io/raskell-io/sentinel-auth:latest
    type: sidecar
    transport: socket
    resources:
      requests:
        cpu: "50m"
        memory: "64Mi"

  waf:
    enabled: true
    image: ghcr.io/raskell-io/sentinel-waf:latest
    type: service
    replicas: 3
    transport: grpc
    resources:
      requests:
        cpu: "200m"
        memory: "256Mi"
    autoscaling:
      enabled: true
      minReplicas: 2
      maxReplicas: 10
      targetCPUUtilization: 70

ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
  hosts:
    - host: api.example.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: api-tls
      hosts:
        - api.example.com

resources:
  requests:
    cpu: "100m"
    memory: "128Mi"
  limits:
    cpu: "1000m"
    memory: "512Mi"

nodeSelector: {}
tolerations: []
affinity: {}

podDisruptionBudget:
  enabled: true
  minAvailable: 2

serviceMonitor:
  enabled: true
  interval: 15s
```

## Service Mesh Integration

### Istio

```yaml
# sentinel-virtualservice.yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: sentinel
spec:
  hosts:
    - sentinel
  http:
    - route:
        - destination:
            host: sentinel
            port:
              number: 8080
      timeout: 30s
      retries:
        attempts: 3
        perTryTimeout: 10s
---
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: sentinel
spec:
  host: sentinel
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        h2UpgradePolicy: UPGRADE
    loadBalancer:
      simple: LEAST_CONN
```

### Linkerd

```yaml
# Add annotation to deployment
metadata:
  annotations:
    linkerd.io/inject: enabled
```

## Observability

### Prometheus ServiceMonitor

```yaml
# sentinel-servicemonitor.yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: sentinel
  labels:
    app: sentinel
spec:
  selector:
    matchLabels:
      app: sentinel
  endpoints:
    - port: admin
      path: /metrics
      interval: 15s
```

### Grafana Dashboard

```yaml
# sentinel-dashboard-configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: sentinel-dashboard
  labels:
    grafana_dashboard: "1"
data:
  sentinel.json: |
    {
      "title": "Sentinel Proxy",
      "panels": [
        {
          "title": "Request Rate",
          "targets": [
            {
              "expr": "rate(sentinel_requests_total[5m])"
            }
          ]
        }
      ]
    }
```

### Logging with Fluentd

```yaml
# fluentd-configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluentd-config
data:
  fluent.conf: |
    <source>
      @type tail
      path /var/log/containers/sentinel*.log
      pos_file /var/log/sentinel.pos
      tag sentinel.*
      <parse>
        @type json
      </parse>
    </source>

    <match sentinel.**>
      @type elasticsearch
      host elasticsearch
      port 9200
      index_name sentinel
    </match>
```

## Network Policies

```yaml
# sentinel-networkpolicy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: sentinel
spec:
  podSelector:
    matchLabels:
      app: sentinel
  policyTypes:
    - Ingress
    - Egress
  ingress:
    # Allow from ingress controller
    - from:
        - namespaceSelector:
            matchLabels:
              name: ingress-nginx
      ports:
        - protocol: TCP
          port: 8080
    # Allow admin from monitoring namespace
    - from:
        - namespaceSelector:
            matchLabels:
              name: monitoring
      ports:
        - protocol: TCP
          port: 9090
  egress:
    # Allow to upstream services
    - to:
        - namespaceSelector:
            matchLabels:
              name: backend
      ports:
        - protocol: TCP
          port: 80
    # Allow to agent services
    - to:
        - podSelector:
            matchLabels:
              app: waf-agent
      ports:
        - protocol: TCP
          port: 50051
    # Allow DNS
    - to:
        - namespaceSelector: {}
          podSelector:
            matchLabels:
              k8s-app: kube-dns
      ports:
        - protocol: UDP
          port: 53
```

## Rolling Updates

```yaml
# Update strategy in deployment
spec:
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
```

```bash
# Trigger rolling update
kubectl set image deployment/sentinel sentinel=ghcr.io/raskell-io/sentinel:v1.2.0

# Watch rollout
kubectl rollout status deployment/sentinel

# Rollback if needed
kubectl rollout undo deployment/sentinel
```

## Troubleshooting

### Pod Not Starting

```bash
# Check pod status
kubectl get pods -l app=sentinel

# Describe pod
kubectl describe pod sentinel-xxx

# Check logs
kubectl logs sentinel-xxx -c sentinel
kubectl logs sentinel-xxx -c auth-agent

# Check events
kubectl get events --sort-by='.lastTimestamp'
```

### Agent Connection Issues

```bash
# Check service discovery
kubectl exec sentinel-xxx -c sentinel -- nslookup waf-agent

# Test gRPC connection
kubectl exec sentinel-xxx -c sentinel -- grpcurl -plaintext waf-agent:50051 list

# Check socket exists (sidecar)
kubectl exec sentinel-xxx -c sentinel -- ls -la /var/run/sentinel/
```

### Resource Issues

```bash
# Check resource usage
kubectl top pods -l app=sentinel

# Check resource limits
kubectl describe pod sentinel-xxx | grep -A5 Resources

# Check OOMKilled
kubectl get events | grep OOM
```

### Config Issues

```bash
# Validate config
kubectl exec sentinel-xxx -c sentinel -- sentinel --config /etc/sentinel/sentinel.kdl --dry-run

# Check configmap
kubectl get configmap sentinel-config -o yaml
```

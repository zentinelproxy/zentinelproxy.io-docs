+++
title = "Kubernetes"
weight = 5
+++

Kubernetes provides the most flexible deployment model for Zentinel, supporting multiple patterns from simple sidecar deployments to sophisticated service mesh integrations.

## Deployment Patterns

| Pattern | Description | Best For |
|---------|-------------|----------|
| **Sidecar** | Agents in same pod as Zentinel | Simple setups, low latency |
| **Service** | Agents as separate deployments | Shared agents, independent scaling |
| **DaemonSet** | Zentinel on every node | Edge/gateway deployments |

## Pattern 1: Sidecar Deployment

Agents run as sidecar containers in the same pod as Zentinel.

```yaml
# zentinel-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: zentinel
  labels:
    app: zentinel
spec:
  replicas: 3
  selector:
    matchLabels:
      app: zentinel
  template:
    metadata:
      labels:
        app: zentinel
    spec:
      containers:
        # ─────────────────────────────────────────────────
        # Zentinel Proxy
        # ─────────────────────────────────────────────────
        - name: zentinel
          image: ghcr.io/zentinelproxy/zentinel:latest
          ports:
            - name: http
              containerPort: 8080
            - name: admin
              containerPort: 9090
          volumeMounts:
            - name: config
              mountPath: /etc/zentinel
              readOnly: true
            - name: sockets
              mountPath: /var/run/zentinel
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
          image: ghcr.io/zentinelproxy/zentinel-auth:latest
          args:
            - "--socket"
            - "/var/run/zentinel/auth.sock"
          volumeMounts:
            - name: sockets
              mountPath: /var/run/zentinel
            - name: auth-secrets
              mountPath: /etc/auth/secrets
              readOnly: true
          env:
            - name: AUTH_SECRET
              valueFrom:
                secretKeyRef:
                  name: zentinel-secrets
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
          image: ghcr.io/zentinelproxy/zentinel-waf:latest
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
            name: zentinel-config
        - name: sockets
          emptyDir: {}
        - name: auth-secrets
          secret:
            secretName: zentinel-secrets
---
apiVersion: v1
kind: Service
metadata:
  name: zentinel
spec:
  selector:
    app: zentinel
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
# zentinel-configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: zentinel-config
data:
  zentinel.kdl: |
    server {
        listen "0.0.0.0:8080"
    }

    admin {
        listen "0.0.0.0:9090"
    }

    agents {
        agent "auth" type="auth" {
            unix-socket "/var/run/zentinel/auth.sock"
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
# zentinel-secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: zentinel-secrets
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
          image: ghcr.io/zentinelproxy/zentinel-waf:latest
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

Update Zentinel config to use the service:

```kdl
agent "waf" type="waf" {
    grpc "http://waf-agent.default.svc.cluster.local:50051"
    events "request_headers" "request_body"
    timeout-ms 200
    failure-mode "open"
}
```

## Pattern 3: DaemonSet (Edge Gateway)

Run Zentinel on every node for edge/gateway scenarios.

```yaml
# zentinel-daemonset.yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: zentinel-edge
  labels:
    app: zentinel-edge
spec:
  selector:
    matchLabels:
      app: zentinel-edge
  template:
    metadata:
      labels:
        app: zentinel-edge
    spec:
      hostNetwork: true
      dnsPolicy: ClusterFirstWithHostNet
      containers:
        - name: zentinel
          image: ghcr.io/zentinelproxy/zentinel:latest
          ports:
            - name: http
              containerPort: 80
              hostPort: 80
            - name: https
              containerPort: 443
              hostPort: 443
          volumeMounts:
            - name: config
              mountPath: /etc/zentinel
          securityContext:
            capabilities:
              add:
                - NET_BIND_SERVICE
      volumes:
        - name: config
          configMap:
            name: zentinel-edge-config
      tolerations:
        - key: node-role.kubernetes.io/master
          effect: NoSchedule
```

## Helm Chart

### Installation

```bash
# Clone the repository
git clone https://github.com/zentinelproxy/zentinel.git
cd zentinel

# Install with default values
helm install zentinel ./deploy/helm/zentinel

# Install with custom values
helm install zentinel ./deploy/helm/zentinel -f values.yaml

# Or install directly from GitHub (OCI registry coming soon)
helm install zentinel oci://ghcr.io/zentinelproxy/charts/zentinel --version 0.1.3
```

### values.yaml

```yaml
# values.yaml
replicaCount: 3

image:
  repository: ghcr.io/zentinelproxy/zentinel
  tag: latest
  pullPolicy: IfNotPresent

service:
  type: LoadBalancer
  httpPort: 80
  httpsPort: 443
  adminPort: 9090

config:
  zentinel.kdl: |
    server {
        listen "0.0.0.0:8080"
    }
    # ... rest of config

agents:
  auth:
    enabled: true
    image: ghcr.io/zentinelproxy/zentinel-auth:latest
    type: sidecar
    transport: socket
    resources:
      requests:
        cpu: "50m"
        memory: "64Mi"

  waf:
    enabled: true
    image: ghcr.io/zentinelproxy/zentinel-waf:latest
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
# zentinel-virtualservice.yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: zentinel
spec:
  hosts:
    - zentinel
  http:
    - route:
        - destination:
            host: zentinel
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
  name: zentinel
spec:
  host: zentinel
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
# zentinel-servicemonitor.yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: zentinel
  labels:
    app: zentinel
spec:
  selector:
    matchLabels:
      app: zentinel
  endpoints:
    - port: admin
      path: /metrics
      interval: 15s
```

### Grafana Dashboard

```yaml
# zentinel-dashboard-configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: zentinel-dashboard
  labels:
    grafana_dashboard: "1"
data:
  zentinel.json: |
    {
      "title": "Zentinel Proxy",
      "panels": [
        {
          "title": "Request Rate",
          "targets": [
            {
              "expr": "rate(zentinel_requests_total[5m])"
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
      path /var/log/containers/zentinel*.log
      pos_file /var/log/zentinel.pos
      tag zentinel.*
      <parse>
        @type json
      </parse>
    </source>

    <match zentinel.**>
      @type elasticsearch
      host elasticsearch
      port 9200
      index_name zentinel
    </match>
```

## Network Policies

```yaml
# zentinel-networkpolicy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: zentinel
spec:
  podSelector:
    matchLabels:
      app: zentinel
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
kubectl set image deployment/zentinel zentinel=ghcr.io/zentinelproxy/zentinel:v1.2.0

# Watch rollout
kubectl rollout status deployment/zentinel

# Rollback if needed
kubectl rollout undo deployment/zentinel
```

## Troubleshooting

### Pod Not Starting

```bash
# Check pod status
kubectl get pods -l app=zentinel

# Describe pod
kubectl describe pod zentinel-xxx

# Check logs
kubectl logs zentinel-xxx -c zentinel
kubectl logs zentinel-xxx -c auth-agent

# Check events
kubectl get events --sort-by='.lastTimestamp'
```

### Agent Connection Issues

```bash
# Check service discovery
kubectl exec zentinel-xxx -c zentinel -- nslookup waf-agent

# Test gRPC connection
kubectl exec zentinel-xxx -c zentinel -- grpcurl -plaintext waf-agent:50051 list

# Check socket exists (sidecar)
kubectl exec zentinel-xxx -c zentinel -- ls -la /var/run/zentinel/
```

### Resource Issues

```bash
# Check resource usage
kubectl top pods -l app=zentinel

# Check resource limits
kubectl describe pod zentinel-xxx | grep -A5 Resources

# Check OOMKilled
kubectl get events | grep OOM
```

### Config Issues

```bash
# Validate config
kubectl exec zentinel-xxx -c zentinel -- zentinel --config /etc/zentinel/zentinel.kdl --dry-run

# Check configmap
kubectl get configmap zentinel-config -o yaml
```

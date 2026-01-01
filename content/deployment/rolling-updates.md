+++
title = "Rolling Updates"
weight = 7
+++

Zero-downtime deployment strategies for Sentinel.

## Update Strategies

### Overview

| Strategy | Downtime | Rollback | Resource Usage |
|----------|----------|----------|----------------|
| Rolling Update | None | Fast | +50-100% |
| Blue-Green | None | Instant | +100% |
| Canary | None | Fast | +10-25% |
| In-Place | Brief | Manual | None |

## Rolling Updates

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sentinel
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1        # Add 1 new pod before removing old
      maxUnavailable: 0  # Never reduce below desired replicas
  template:
    spec:
      containers:
        - name: sentinel
          image: ghcr.io/raskell-io/sentinel:1.2.0
          readinessProbe:
            httpGet:
              path: /health
              port: 9090
            initialDelaySeconds: 5
            periodSeconds: 5
          livenessProbe:
            httpGet:
              path: /health
              port: 9090
            initialDelaySeconds: 10
            periodSeconds: 10
```

Update:

```bash
# Update image
kubectl set image deployment/sentinel \
    sentinel=ghcr.io/raskell-io/sentinel:1.3.0

# Watch rollout
kubectl rollout status deployment/sentinel

# Rollback if needed
kubectl rollout undo deployment/sentinel
```

### Docker Swarm

```yaml
# docker-compose.yml
version: '3.8'

services:
  sentinel:
    image: ghcr.io/raskell-io/sentinel:1.2.0
    deploy:
      replicas: 3
      update_config:
        parallelism: 1
        delay: 10s
        failure_action: rollback
        order: start-first
      rollback_config:
        parallelism: 1
        delay: 10s
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9090/health"]
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 10s
```

Update:

```bash
# Update service
docker service update \
    --image ghcr.io/raskell-io/sentinel:1.3.0 \
    sentinel

# Watch update
docker service ps sentinel

# Rollback
docker service rollback sentinel
```

### systemd

```bash
#!/bin/bash
# rolling-update.sh

set -e

NEW_VERSION=$1
OLD_BINARY="/usr/local/bin/sentinel"
NEW_BINARY="/usr/local/bin/sentinel.new"

# Download new version
curl -Lo "$NEW_BINARY" \
    "https://github.com/raskell-io/sentinel/releases/download/v${NEW_VERSION}/sentinel"
chmod +x "$NEW_BINARY"

# Validate new binary
$NEW_BINARY validate -c /etc/sentinel/sentinel.kdl

# Swap binaries
mv "$OLD_BINARY" "${OLD_BINARY}.old"
mv "$NEW_BINARY" "$OLD_BINARY"

# Graceful restart
systemctl reload sentinel

# Wait for health
for i in {1..30}; do
    if curl -sf http://localhost:9090/health; then
        echo "Update successful"
        rm -f "${OLD_BINARY}.old"
        exit 0
    fi
    sleep 1
done

# Rollback on failure
echo "Update failed, rolling back"
mv "${OLD_BINARY}.old" "$OLD_BINARY"
systemctl reload sentinel
exit 1
```

## Blue-Green Deployment

### Architecture

```
                    ┌─────────────────┐
                    │  Load Balancer  │
                    └────────┬────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
      ┌───────▼───────┐           ┌─────────▼───────┐
      │  Blue (v1.2)  │           │  Green (v1.3)   │
      │   [ACTIVE]    │           │   [STANDBY]     │
      └───────────────┘           └─────────────────┘
```

### Kubernetes Implementation

```yaml
# blue-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sentinel-blue
  labels:
    app: sentinel
    version: blue
spec:
  replicas: 3
  selector:
    matchLabels:
      app: sentinel
      version: blue
  template:
    metadata:
      labels:
        app: sentinel
        version: blue
    spec:
      containers:
        - name: sentinel
          image: ghcr.io/raskell-io/sentinel:1.2.0
---
# green-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sentinel-green
  labels:
    app: sentinel
    version: green
spec:
  replicas: 3
  selector:
    matchLabels:
      app: sentinel
      version: green
  template:
    metadata:
      labels:
        app: sentinel
        version: green
    spec:
      containers:
        - name: sentinel
          image: ghcr.io/raskell-io/sentinel:1.3.0
---
# service.yaml
apiVersion: v1
kind: Service
metadata:
  name: sentinel
spec:
  selector:
    app: sentinel
    version: blue  # Switch to 'green' for cutover
  ports:
    - port: 8080
      targetPort: 8080
```

Switch traffic:

```bash
# Deploy green
kubectl apply -f green-deployment.yaml

# Wait for ready
kubectl rollout status deployment/sentinel-green

# Switch traffic
kubectl patch service sentinel -p '{"spec":{"selector":{"version":"green"}}}'

# Verify
kubectl get endpoints sentinel

# Remove blue after verification
kubectl delete deployment sentinel-blue
```

### Docker Compose

```yaml
# docker-compose.blue-green.yml
version: '3.8'

services:
  sentinel-blue:
    image: ghcr.io/raskell-io/sentinel:1.2.0
    networks:
      - sentinel-net

  sentinel-green:
    image: ghcr.io/raskell-io/sentinel:1.3.0
    networks:
      - sentinel-net
    profiles:
      - green  # Only start with --profile green

  nginx:
    image: nginx:alpine
    ports:
      - "8080:8080"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    networks:
      - sentinel-net
```

## Canary Deployment

### Kubernetes with Ingress

```yaml
# canary-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sentinel-canary
spec:
  replicas: 1  # Small number for canary
  template:
    metadata:
      labels:
        app: sentinel
        track: canary
    spec:
      containers:
        - name: sentinel
          image: ghcr.io/raskell-io/sentinel:1.3.0
---
# Split traffic with Ingress annotations (NGINX)
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: sentinel-canary
  annotations:
    nginx.ingress.kubernetes.io/canary: "true"
    nginx.ingress.kubernetes.io/canary-weight: "10"  # 10% to canary
spec:
  rules:
    - http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: sentinel-canary
                port:
                  number: 8080
```

Progressive rollout:

```bash
# Start with 10%
kubectl annotate ingress sentinel-canary \
    nginx.ingress.kubernetes.io/canary-weight="10" --overwrite

# Monitor metrics, increase to 25%
kubectl annotate ingress sentinel-canary \
    nginx.ingress.kubernetes.io/canary-weight="25" --overwrite

# Continue to 50%, then 100%
kubectl annotate ingress sentinel-canary \
    nginx.ingress.kubernetes.io/canary-weight="100" --overwrite

# Promote canary to stable
kubectl set image deployment/sentinel-stable \
    sentinel=ghcr.io/raskell-io/sentinel:1.3.0

# Remove canary
kubectl delete deployment sentinel-canary
kubectl delete ingress sentinel-canary
```

### Istio Traffic Splitting

```yaml
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
            subset: stable
          weight: 90
        - destination:
            host: sentinel
            subset: canary
          weight: 10
---
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: sentinel
spec:
  host: sentinel
  subsets:
    - name: stable
      labels:
        version: stable
    - name: canary
      labels:
        version: canary
```

## Graceful Shutdown

### Configuration

```kdl
server {
    graceful-shutdown-timeout-secs 30
}
```

### Behavior

1. Stop accepting new connections
2. Complete in-flight requests (up to timeout)
3. Close idle connections
4. Exit

### Kubernetes Pod Lifecycle

```yaml
spec:
  terminationGracePeriodSeconds: 60
  containers:
    - name: sentinel
      lifecycle:
        preStop:
          exec:
            command:
              - /bin/sh
              - -c
              - "sleep 5"  # Allow time for endpoint removal
```

## Health Check Integration

### Readiness vs Liveness

| Probe | Purpose | Failure Action |
|-------|---------|----------------|
| Liveness | Is the process healthy? | Restart container |
| Readiness | Can it serve traffic? | Remove from service |

### During Updates

```yaml
readinessProbe:
  httpGet:
    path: /health
    port: 9090
  initialDelaySeconds: 5
  periodSeconds: 5
  successThreshold: 1
  failureThreshold: 2

livenessProbe:
  httpGet:
    path: /health
    port: 9090
  initialDelaySeconds: 15
  periodSeconds: 10
  successThreshold: 1
  failureThreshold: 3
```

## Rollback Procedures

### Kubernetes

```bash
# View rollout history
kubectl rollout history deployment/sentinel

# Rollback to previous
kubectl rollout undo deployment/sentinel

# Rollback to specific revision
kubectl rollout undo deployment/sentinel --to-revision=2
```

### Docker Swarm

```bash
docker service rollback sentinel
```

### Manual Binary Rollback

```bash
# Keep old binary
mv /usr/local/bin/sentinel /usr/local/bin/sentinel.new
mv /usr/local/bin/sentinel.old /usr/local/bin/sentinel

# Restart
systemctl restart sentinel
```

## Automated Rollback

### Based on Metrics

```yaml
# Kubernetes with Argo Rollouts
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: sentinel
spec:
  strategy:
    canary:
      steps:
        - setWeight: 10
        - pause: {duration: 5m}
        - setWeight: 25
        - pause: {duration: 5m}
        - setWeight: 50
        - pause: {duration: 5m}
      analysis:
        templates:
          - templateName: success-rate
        startingStep: 1
---
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: success-rate
spec:
  metrics:
    - name: success-rate
      interval: 1m
      successCondition: result[0] >= 0.95
      provider:
        prometheus:
          address: http://prometheus:9090
          query: |
            sum(rate(sentinel_requests_total{status!~"5.."}[5m]))
            / sum(rate(sentinel_requests_total[5m]))
```

## Pre-Update Checklist

- [ ] New version tested in staging
- [ ] Configuration validated
- [ ] Health checks pass
- [ ] Metrics baseline captured
- [ ] Rollback plan documented
- [ ] Team notified

## Post-Update Verification

```bash
# Check health
curl http://localhost:9090/health

# Verify metrics
curl http://localhost:9090/metrics | grep sentinel_requests

# Check logs for errors
kubectl logs -l app=sentinel --tail=100 | grep -i error

# Verify routing
curl -v http://localhost:8080/api/test
```

## Next Steps

- [Monitoring](../monitoring/) - Observability setup
- [Kubernetes](../kubernetes/) - Cloud-native deployment
- [Configuration Management](../config-management/) - Config updates

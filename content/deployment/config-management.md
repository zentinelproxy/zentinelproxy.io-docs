+++
title = "Configuration Management"
weight = 1
+++

Managing Sentinel configurations across environments.

## Configuration Files

### File Structure

```
/etc/sentinel/
├── sentinel.kdl           # Main configuration
├── certs/
│   ├── server.crt         # TLS certificate
│   ├── server.key         # TLS private key
│   └── ca.crt             # CA certificate (optional)
├── agents/
│   ├── waf.conf           # Agent-specific config
│   └── auth.conf
└── includes/
    ├── routes.kdl         # Modular route definitions
    └── upstreams.kdl      # Upstream definitions
```

### Including Files

Split large configurations into modules:

```kdl
// sentinel.kdl
include "includes/routes.kdl"
include "includes/upstreams.kdl"

server {
    worker-threads 0
}

listeners {
    listener "https" {
        address "0.0.0.0:8443"
        protocol "https"
        tls {
            cert-file "/etc/sentinel/certs/server.crt"
            key-file "/etc/sentinel/certs/server.key"
        }
    }
}
```

## Environment-Specific Configuration

### Directory Layout

```
configs/
├── base/
│   ├── sentinel.kdl       # Shared configuration
│   ├── routes.kdl
│   └── upstreams.kdl
├── development/
│   ├── sentinel.kdl       # Dev overrides
│   └── upstreams.kdl      # Local backends
├── staging/
│   ├── sentinel.kdl
│   └── upstreams.kdl
└── production/
    ├── sentinel.kdl
    └── upstreams.kdl
```

### Environment Variables

Use environment variables for dynamic values:

```kdl
server {
    worker-threads env("SENTINEL_WORKERS", "0")
}

listeners {
    listener "https" {
        address env("SENTINEL_LISTEN_ADDR", "0.0.0.0:8443")
    }
}

upstreams {
    upstream "backend" {
        targets {
            target { address env("BACKEND_ADDR", "127.0.0.1:3000") }
        }
    }
}
```

### Validation

Validate configuration before deployment:

```bash
# Validate syntax
sentinel validate -c /etc/sentinel/sentinel.kdl

# Check with environment variables
BACKEND_ADDR=api.example.com:443 sentinel validate -c sentinel.kdl

# Dry run (parse and show resolved config)
sentinel config show -c sentinel.kdl
```

## Secrets Management

### File-Based Secrets

```kdl
listeners {
    listener "https" {
        tls {
            cert-file "/run/secrets/tls.crt"
            key-file "/run/secrets/tls.key"
        }
    }
}

agents {
    agent "auth" {
        config {
            jwt-secret file("/run/secrets/jwt-secret")
        }
    }
}
```

### Environment Variables

```kdl
agents {
    agent "auth" {
        config {
            jwt-secret env("JWT_SECRET")
            api-key env("API_KEY")
        }
    }
}
```

### HashiCorp Vault

For production secrets management:

```bash
# Fetch secrets at startup
export JWT_SECRET=$(vault kv get -field=jwt-secret secret/sentinel)
export TLS_CERT=$(vault kv get -field=cert secret/sentinel/tls)

# Or use Vault Agent for automatic injection
vault agent -config=vault-agent.hcl
```

### Kubernetes Secrets

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: sentinel-tls
type: kubernetes.io/tls
data:
  tls.crt: <base64-encoded-cert>
  tls.key: <base64-encoded-key>
---
apiVersion: v1
kind: Pod
spec:
  containers:
    - name: sentinel
      volumeMounts:
        - name: tls
          mountPath: /etc/sentinel/certs
          readOnly: true
  volumes:
    - name: tls
      secret:
        secretName: sentinel-tls
```

## Configuration Templating

### Using envsubst

```bash
# Template file
cat > sentinel.kdl.template << 'EOF'
server {
    worker-threads ${WORKERS}
}
upstreams {
    upstream "backend" {
        targets {
            target { address "${BACKEND_HOST}:${BACKEND_PORT}" }
        }
    }
}
EOF

# Generate config
export WORKERS=4 BACKEND_HOST=api.example.com BACKEND_PORT=443
envsubst < sentinel.kdl.template > sentinel.kdl
```

### Using Jinja2 (Ansible)

```yaml
# templates/sentinel.kdl.j2
server {
    worker-threads {{ sentinel_workers | default(0) }}
}

listeners {
    listener "https" {
        address "0.0.0.0:{{ sentinel_https_port }}"
        tls {
            cert-file "{{ sentinel_cert_path }}"
            key-file "{{ sentinel_key_path }}"
        }
    }
}

upstreams {
{% for upstream in sentinel_upstreams %}
    upstream "{{ upstream.name }}" {
        targets {
{% for target in upstream.targets %}
            target { address "{{ target }}" }
{% endfor %}
        }
    }
{% endfor %}
}
```

### Using Helm (Kubernetes)

```yaml
# templates/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: sentinel-config
data:
  sentinel.kdl: |
    server {
        worker-threads {{ .Values.workers }}
    }
    listeners {
        listener "https" {
            address "0.0.0.0:{{ .Values.port }}"
        }
    }
    upstreams {
        {{- range .Values.upstreams }}
        upstream "{{ .name }}" {
            targets {
                {{- range .targets }}
                target { address "{{ . }}" }
                {{- end }}
            }
        }
        {{- end }}
    }
```

## GitOps Workflow

### Repository Structure

```
infrastructure/
├── sentinel/
│   ├── base/
│   │   ├── kustomization.yaml
│   │   ├── deployment.yaml
│   │   └── config/
│   │       └── sentinel.kdl
│   └── overlays/
│       ├── staging/
│       │   ├── kustomization.yaml
│       │   └── patches/
│       └── production/
│           ├── kustomization.yaml
│           └── patches/
└── .github/
    └── workflows/
        └── deploy.yaml
```

### Kustomize Overlay

```yaml
# overlays/production/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - ../../base

namespace: sentinel-prod

patches:
  - path: patches/replicas.yaml
  - path: patches/resources.yaml

configMapGenerator:
  - name: sentinel-config
    behavior: replace
    files:
      - config/sentinel.kdl
```

### ArgoCD Application

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: sentinel
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/org/infrastructure
    targetRevision: main
    path: sentinel/overlays/production
  destination:
    server: https://kubernetes.default.svc
    namespace: sentinel
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

## Configuration Reload

### Hot Reload

Sentinel supports configuration reload without restart:

```bash
# Send SIGHUP to reload configuration
kill -HUP $(pidof sentinel)

# Or use the admin API
curl -X POST http://localhost:9090/admin/reload
```

### What Can Be Reloaded

| Setting | Hot Reload | Requires Restart |
|---------|------------|------------------|
| Routes | Yes | - |
| Upstreams | Yes | - |
| Agent config | Yes | - |
| TLS certificates | Yes | - |
| Listeners (new) | - | Yes |
| Worker threads | - | Yes |

### Reload Workflow

```bash
# 1. Validate new config
sentinel validate -c /etc/sentinel/sentinel.kdl.new

# 2. Replace config
mv /etc/sentinel/sentinel.kdl.new /etc/sentinel/sentinel.kdl

# 3. Reload
kill -HUP $(pidof sentinel)

# 4. Verify
curl -s http://localhost:9090/health
```

## Backup and Restore

### Backup Script

```bash
#!/bin/bash
# backup-sentinel.sh

BACKUP_DIR="/var/backups/sentinel"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

# Backup configuration
tar -czf "$BACKUP_DIR/sentinel-config-$TIMESTAMP.tar.gz" \
    /etc/sentinel/

# Backup certificates (encrypted)
tar -czf - /etc/sentinel/certs/ | \
    gpg --symmetric --cipher-algo AES256 \
    > "$BACKUP_DIR/sentinel-certs-$TIMESTAMP.tar.gz.gpg"

# Keep last 30 days
find "$BACKUP_DIR" -mtime +30 -delete
```

### Restore Script

```bash
#!/bin/bash
# restore-sentinel.sh

BACKUP_FILE=$1

# Stop sentinel
systemctl stop sentinel

# Restore config
tar -xzf "$BACKUP_FILE" -C /

# Validate
sentinel validate -c /etc/sentinel/sentinel.kdl

# Restart
systemctl start sentinel
```

## Configuration Drift Detection

### Using AIDE

```bash
# Initialize baseline
aide --init

# Check for changes
aide --check
```

### Using Git

```bash
# Track config in Git
cd /etc/sentinel
git init
git add sentinel.kdl
git commit -m "Initial config"

# Detect drift
git diff
git status
```

### Automated Drift Check

```yaml
# .github/workflows/drift-check.yaml
name: Config Drift Check

on:
  schedule:
    - cron: '0 */6 * * *'

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - name: Fetch running config
        run: |
          ssh sentinel-prod "cat /etc/sentinel/sentinel.kdl" > running.kdl

      - name: Compare with source
        run: |
          diff -u production/sentinel.kdl running.kdl || \
            echo "::warning::Configuration drift detected"
```

## Next Steps

- [Building Images](../docker-build/) - Create Docker images
- [Docker Deployment](../docker/) - Container deployment
- [Kubernetes](../kubernetes/) - Cloud-native deployment

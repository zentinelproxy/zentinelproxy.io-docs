+++
title = "Configuration Management"
weight = 1
+++

Managing Zentinel configurations across environments.

## Configuration Files

### File Structure

```
/etc/zentinel/
├── zentinel.kdl           # Main configuration
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
// zentinel.kdl
include "includes/routes.kdl"
include "includes/upstreams.kdl"

system {
    worker-threads 0
}

listeners {
    listener "https" {
        address "0.0.0.0:8443"
        protocol "https"
        tls {
            cert-file "/etc/zentinel/certs/server.crt"
            key-file "/etc/zentinel/certs/server.key"
        }
    }
}
```

## Environment-Specific Configuration

### Directory Layout

```
configs/
├── base/
│   ├── zentinel.kdl       # Shared configuration
│   ├── routes.kdl
│   └── upstreams.kdl
├── development/
│   ├── zentinel.kdl       # Dev overrides
│   └── upstreams.kdl      # Local backends
├── staging/
│   ├── zentinel.kdl
│   └── upstreams.kdl
└── production/
    ├── zentinel.kdl
    └── upstreams.kdl
```

### Environment Variables

Use environment variables for dynamic values:

```kdl
system {
    worker-threads "0"
}

listeners {
    listener "https" {
        address "0.0.0.0:8443"
    }
}

upstreams {
    upstream "backend" {
        targets {
            target { address "127.0.0.1:3000" }
        }
    }
}

routes {
    route "default" {
        matches { path-prefix "/" }
        upstream "backend"
    }
}

```

### Validation

Validate configuration before deployment:

```bash
# Validate syntax
zentinel validate -c /etc/zentinel/zentinel.kdl

# Check with environment variables
BACKEND_ADDR=api.example.com:443 zentinel validate -c zentinel.kdl

# Dry run (parse and show resolved config)
zentinel config show -c zentinel.kdl
```

## Secrets Management

### File-Based Secrets

```kdl
system {
    worker-threads 0
}

listeners {
    listener "https" {
        tls {
            cert-file "/run/secrets/tls.crt"
            key-file "/run/secrets/tls.key"
        }
    }
}

agents {
    agent "auth" type="custom" {
        unix-socket "/tmp/auth.sock"
        config {
            jwt-secret "/path/to/secret"
        }
    }
}

routes {
    route "default" {
        matches { path-prefix "/" }
        upstream "backend"
    }
}

upstreams {
    upstream "backend" {
        targets {
            target { address "127.0.0.1:3000" }
        }
    }
}

```

### Environment Variables

```kdl
system {
    worker-threads 0
}

listeners {
    listener "http" {
        address "0.0.0.0:8080"
        protocol "http"
    }
}

agents {
    agent "auth" type="custom" {
        unix-socket "/tmp/auth.sock"
        config {
            jwt-secret "placeholder"
            api-key "placeholder"
        }
    }
}

routes {
    route "default" {
        matches { path-prefix "/" }
        upstream "backend"
    }
}

upstreams {
    upstream "backend" {
        targets {
            target { address "127.0.0.1:3000" }
        }
    }
}

```

### HashiCorp Vault

For production secrets management:

```bash
# Fetch secrets at startup
export JWT_SECRET=$(vault kv get -field=jwt-secret secret/zentinel)
export TLS_CERT=$(vault kv get -field=cert secret/zentinel/tls)

# Or use Vault Agent for automatic injection
vault agent -config=vault-agent.hcl
```

### Kubernetes Secrets

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: zentinel-tls
type: kubernetes.io/tls
data:
  tls.crt: <base64-encoded-cert>
  tls.key: <base64-encoded-key>
---
apiVersion: v1
kind: Pod
spec:
  containers:
    - name: zentinel
      volumeMounts:
        - name: tls
          mountPath: /etc/zentinel/certs
          readOnly: true
  volumes:
    - name: tls
      secret:
        secretName: zentinel-tls
```

## Configuration Templating

### Using envsubst

```bash
# Template file
cat > zentinel.kdl.template << 'EOF'
system {
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
envsubst < zentinel.kdl.template > zentinel.kdl
```

### Using Jinja2 (Ansible)

```yaml
# templates/zentinel.kdl.j2
system {
    worker-threads {{ zentinel_workers | default(0) }}
}

listeners {
    listener "https" {
        address "0.0.0.0:{{ zentinel_https_port }}"
        tls {
            cert-file "{{ zentinel_cert_path }}"
            key-file "{{ zentinel_key_path }}"
        }
    }
}

upstreams {
{% for upstream in zentinel_upstreams %}
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
  name: zentinel-config
data:
  zentinel.kdl: |
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
├── zentinel/
│   ├── base/
│   │   ├── kustomization.yaml
│   │   ├── deployment.yaml
│   │   └── config/
│   │       └── zentinel.kdl
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

namespace: zentinel-prod

patches:
  - path: patches/replicas.yaml
  - path: patches/resources.yaml

configMapGenerator:
  - name: zentinel-config
    behavior: replace
    files:
      - config/zentinel.kdl
```

### ArgoCD Application

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: zentinel
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/org/infrastructure
    targetRevision: main
    path: zentinel/overlays/production
  destination:
    server: https://kubernetes.default.svc
    namespace: zentinel
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

## Configuration Reload

### Hot Reload

Zentinel supports configuration reload without restart:

```bash
# Send SIGHUP to reload configuration
kill -HUP $(pidof zentinel)

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
zentinel validate -c /etc/zentinel/zentinel.kdl.new

# 2. Replace config
mv /etc/zentinel/zentinel.kdl.new /etc/zentinel/zentinel.kdl

# 3. Reload
kill -HUP $(pidof zentinel)

# 4. Verify
curl -s http://localhost:9090/health
```

## Backup and Restore

### Backup Script

```bash
#!/bin/bash
# backup-zentinel.sh

BACKUP_DIR="/var/backups/zentinel"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

# Backup configuration
tar -czf "$BACKUP_DIR/zentinel-config-$TIMESTAMP.tar.gz" \
    /etc/zentinel/

# Backup certificates (encrypted)
tar -czf - /etc/zentinel/certs/ | \
    gpg --symmetric --cipher-algo AES256 \
    > "$BACKUP_DIR/zentinel-certs-$TIMESTAMP.tar.gz.gpg"

# Keep last 30 days
find "$BACKUP_DIR" -mtime +30 -delete
```

### Restore Script

```bash
#!/bin/bash
# restore-zentinel.sh

BACKUP_FILE=$1

# Stop zentinel
systemctl stop zentinel

# Restore config
tar -xzf "$BACKUP_FILE" -C /

# Validate
zentinel validate -c /etc/zentinel/zentinel.kdl

# Restart
systemctl start zentinel
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
cd /etc/zentinel
git init
git add zentinel.kdl
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
          ssh zentinel-prod "cat /etc/zentinel/zentinel.kdl" > running.kdl

      - name: Compare with source
        run: |
          diff -u production/zentinel.kdl running.kdl || \
            echo "::warning::Configuration drift detected"
```

## Next Steps

- [Building Images](../docker-build/) - Create Docker images
- [Docker Deployment](../docker/) - Container deployment
- [Kubernetes](../kubernetes/) - Cloud-native deployment

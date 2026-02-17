+++
title = "Upgrade Guide"
weight = 7
+++

Procedures for upgrading and migrating Zentinel deployments.

## Version Management

### Version Numbering

Zentinel follows semantic versioning: `MAJOR.MINOR.PATCH`

| Version Change | Meaning | Upgrade Approach |
|----------------|---------|------------------|
| Patch (x.y.Z) | Bug fixes, no breaking changes | Rolling upgrade, minimal risk |
| Minor (x.Y.z) | New features, backward compatible | Rolling upgrade, test new features |
| Major (X.y.z) | Breaking changes possible | Staged rollout, careful testing |

### Compatibility Matrix

| Component | Compatible Versions | Notes |
|-----------|---------------------|-------|
| Config format | Same major version | Config migration may be needed |
| Agent protocol | Same major version | Agents must be upgraded together |
| Metrics format | All versions | Metric names stable |

### Version Checking

```bash
# Check current version
zentinel --version

# Check version in running instance
curl -s localhost:9090/admin/version

# Compare with latest release
curl -s https://api.github.com/repos/zentinelproxy/zentinel/releases/latest | \
    jq -r '.tag_name'
```

## Pre-Upgrade Checklist

### Before Any Upgrade

- [ ] Read release notes for all versions between current and target
- [ ] Identify breaking changes
- [ ] Backup current binary, configuration, and certificates
- [ ] Test new version in staging environment
- [ ] Verify configuration compatibility
- [ ] Test rollback procedure
- [ ] Ensure on-call coverage during upgrade

### Backup Procedure

```bash
#!/bin/bash
BACKUP_DIR="/var/backups/zentinel/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Backup binary
cp /usr/local/bin/zentinel "$BACKUP_DIR/"

# Backup configuration
cp -r /etc/zentinel "$BACKUP_DIR/config"

# Save current version
zentinel --version > "$BACKUP_DIR/version.txt"

# Save metrics snapshot
curl -s localhost:9090/metrics > "$BACKUP_DIR/metrics.txt"

echo "Backup complete: $BACKUP_DIR"
```

## Upgrade Procedures

### Patch Upgrade (x.y.Z)

**Risk Level**: Low
**Downtime**: Zero (with rolling upgrade)

```bash
#!/bin/bash
NEW_VERSION="$1"

# Download new version
curl -L -o /tmp/zentinel-new \
    "https://github.com/zentinelproxy/zentinel/releases/download/v${NEW_VERSION}/zentinel-linux-amd64"
chmod +x /tmp/zentinel-new

# Verify download and validate config
/tmp/zentinel-new --version
/tmp/zentinel-new --validate --config /etc/zentinel/config.kdl

# Create backup
./backup-zentinel.sh

# Replace binary
mv /tmp/zentinel-new /usr/local/bin/zentinel

# Graceful restart
systemctl restart zentinel

# Verify
sleep 5
curl -sf localhost:8080/health && echo "Upgrade successful!"
```

### Minor Upgrade (x.Y.z)

**Risk Level**: Medium
**Downtime**: Zero (with rolling upgrade)

```bash
#!/bin/bash
NEW_VERSION="$1"

# Pre-flight checks
AVAILABLE_SPACE=$(df -P /usr/local/bin | tail -1 | awk '{print $4}')
if [ "$AVAILABLE_SPACE" -lt 100000 ]; then
    echo "ERROR: Insufficient disk space"
    exit 1
fi

# Download and verify checksum
curl -L -o /tmp/zentinel-new \
    "https://github.com/zentinelproxy/zentinel/releases/download/v${NEW_VERSION}/zentinel-linux-amd64"
curl -L -o /tmp/zentinel-new.sha256 \
    "https://github.com/zentinelproxy/zentinel/releases/download/v${NEW_VERSION}/zentinel-linux-amd64.sha256"

cd /tmp && sha256sum -c zentinel-new.sha256
chmod +x /tmp/zentinel-new

# Test new binary
/tmp/zentinel-new --version
/tmp/zentinel-new --validate --config /etc/zentinel/config.kdl

# Create backup
./backup-zentinel.sh

# Graceful shutdown and replace
kill -TERM $(cat /var/run/zentinel.pid)
sleep 5
mv /tmp/zentinel-new /usr/local/bin/zentinel
systemctl start zentinel

# Verify
sleep 5
curl -sf localhost:8080/health || { ./rollback-zentinel.sh; exit 1; }
echo "Upgrade successful!"
```

### Major Upgrade (X.y.z)

**Risk Level**: High
**Approach**: Blue-Green or Canary

#### Blue-Green Upgrade

```
Phase 1: Deploy new version alongside old
┌─────────────────────────────────────────────────┐
│              Load Balancer                       │
│        ┌────────────┴────────────┐              │
│        ▼ (100%)                  ▼ (0%)          │
│  ┌───────────┐            ┌───────────┐         │
│  │Blue (v1.x)│            │Green(v2.x)│         │
│  │  Active   │            │  Standby  │         │
│  └───────────┘            └───────────┘         │
└─────────────────────────────────────────────────┘

Phase 2: Shift traffic to new version
┌─────────────────────────────────────────────────┐
│              Load Balancer                       │
│        ┌────────────┴────────────┐              │
│        ▼ (0%)                    ▼ (100%)        │
│  ┌───────────┐            ┌───────────┐         │
│  │Blue (v1.x)│            │Green(v2.x)│         │
│  │  Standby  │            │  Active   │         │
│  └───────────┘            └───────────┘         │
└─────────────────────────────────────────────────┘
```

**Steps**:
1. Deploy new version to green environment
2. Test with synthetic traffic
3. Shift 10% traffic to green, monitor for 5 minutes
4. If error rate acceptable, shift 50%, monitor 10 minutes
5. Complete shift to 100%
6. Retain blue for rollback

#### Canary Upgrade

**Steps**:
1. Deploy to single canary instance
2. Enable canary routing at 5%
3. Monitor for 30 minutes
4. Gradual rollout: 10% → 25% → 50% → 75% → 100%
5. Validate at each stage before proceeding

## Rollback Procedures

### Quick Rollback

```bash
#!/bin/bash
BACKUP_DIR=$(ls -td /var/backups/zentinel/*/ | head -1)

if [ -z "$BACKUP_DIR" ]; then
    echo "ERROR: No backup found!"
    exit 1
fi

echo "Rolling back from $BACKUP_DIR"

# Stop current version
systemctl stop zentinel

# Restore binary
cp "$BACKUP_DIR/zentinel" /usr/local/bin/zentinel
chmod +x /usr/local/bin/zentinel

# Restore configuration
cp -r "$BACKUP_DIR/config/"* /etc/zentinel/

# Start
systemctl start zentinel

# Verify
sleep 5
curl -sf localhost:8080/health && echo "Rollback successful!"
```

### Blue-Green Rollback

```bash
# Shift all traffic back to blue
curl -X POST "$LB_API/backends/blue/weight" -d '{"weight": 100}'
curl -X POST "$LB_API/backends/green/weight" -d '{"weight": 0}'
```

## Configuration Migration

### Common Migration Patterns

**Deprecated Directive Replacement**:
```kdl
// Old (v1.x)
upstream "backend" {
    timeout-secs 30  // DEPRECATED
}

// New (v2.x)
upstream "backend" {
    timeouts {
        connect-secs 5
        request-secs 30
    }
}
```

**Restructured Configuration**:
```kdl
// Old (v1.x) - flat structure
route "api" {
    path-prefix "/api/"
    upstream "backend"
    timeout-secs 30
}

// New (v2.x) - nested structure
routes {
    route "api" {
        matches {
            path-prefix "/api/"
        }
        upstream "backend"
        policies {
            timeouts {
                request-secs 30
            }
        }
    }
}
```

### Migration Tool

```bash
# Check for configuration issues
zentinel config check /etc/zentinel/config.kdl

# Migrate configuration to new format
zentinel config migrate /etc/zentinel/config.kdl -o config.kdl.new

# Show migration diff
diff /etc/zentinel/config.kdl config.kdl.new

# Validate migrated configuration
zentinel --validate --config config.kdl.new
```

## Post-Upgrade Validation

### Immediate Validation (First 5 Minutes)

```bash
#!/bin/bash
ERRORS=0

# Process running
echo -n "Process running: "
pgrep -f zentinel > /dev/null && echo "OK" || { echo "FAIL"; ((ERRORS++)); }

# Health endpoint
echo -n "Health endpoint: "
curl -sf localhost:8080/health > /dev/null && echo "OK" || { echo "FAIL"; ((ERRORS++)); }

# Metrics endpoint
echo -n "Metrics endpoint: "
curl -sf localhost:9090/metrics > /dev/null && echo "OK" || { echo "FAIL"; ((ERRORS++)); }

# Version correct
echo -n "Version: "
zentinel --version

# Configuration loaded
echo -n "Config loaded: "
ROUTES=$(curl -s localhost:9090/admin/routes | jq length)
[ "$ROUTES" -gt 0 ] && echo "OK ($ROUTES routes)" || { echo "FAIL"; ((ERRORS++)); }

if [ $ERRORS -eq 0 ]; then
    echo "Validation PASSED"
else
    echo "Validation FAILED ($ERRORS errors)"
    exit 1
fi
```

### Extended Validation (First Hour)

```bash
#!/bin/bash
DURATION=3600
INTERVAL=60

echo "Monitoring for $((DURATION/60)) minutes..."

START=$(date +%s)
while [ $(($(date +%s) - START)) -lt $DURATION ]; do
    ERROR_RATE=$(curl -s localhost:9090/metrics | \
        grep 'requests_total.*status="5' | \
        awk '{sum+=$2} END {print sum}')

    P99_LATENCY=$(curl -s localhost:9090/metrics | \
        grep 'request_duration.*quantile="0.99"' | \
        awk '{print $2}')

    echo "$(date): errors=$ERROR_RATE p99=${P99_LATENCY}s"

    sleep $INTERVAL
done
```

## Quick Reference

### Upgrade Commands

```bash
# Validate config before upgrade
zentinel --validate --config /etc/zentinel/config.kdl

# Create backup
./backup-zentinel.sh

# Perform upgrade
./patch-upgrade.sh 2.1.5      # Patch
./minor-upgrade.sh 2.2.0      # Minor
./blue-green-upgrade.sh 3.0.0 # Major

# Rollback if needed
./rollback-zentinel.sh
```

### Health Check Endpoints

| Endpoint | Purpose | Expected |
|----------|---------|----------|
| `/health` | Liveness | 200 OK |
| `/ready` | Readiness | 200 OK |
| `/admin/version` | Version | JSON |
| `/metrics` | Prometheus | Text |

### Upgrade Timing

| Type | Downtime | Window |
|------|----------|--------|
| Patch | Zero | Anytime |
| Minor | Zero | Business hours |
| Major | Minutes | Maintenance window |

## See Also

- [Migration Guide](../migration/) - Migrating from other proxies
- [Troubleshooting](../troubleshooting/) - Diagnosing upgrade issues
- [Configuration Reference](../../reference/config-schema/) - Config options
- [Changelog](../../appendix/changelog/) - Version history

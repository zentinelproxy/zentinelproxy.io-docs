+++
title = "Release Process"
weight = 10
+++

Versioning, release workflow, and publishing.

## Versioning

### Semantic Versioning

Sentinel follows [Semantic Versioning](https://semver.org/):

```
MAJOR.MINOR.PATCH

1.0.0  - Initial stable release
1.1.0  - New features, backwards compatible
1.1.1  - Bug fixes only
2.0.0  - Breaking changes
```

### Version Bumps

| Change Type | Version Bump | Example |
|-------------|--------------|---------|
| Breaking API change | Major | 1.0.0 → 2.0.0 |
| New feature | Minor | 1.0.0 → 1.1.0 |
| Bug fix | Patch | 1.0.0 → 1.0.1 |
| Security fix | Patch | 1.0.0 → 1.0.1 |
| Documentation | None | - |

### Pre-release Versions

```
1.0.0-alpha.1  - Early testing
1.0.0-beta.1   - Feature complete, needs testing
1.0.0-rc.1     - Release candidate
1.0.0          - Stable release
```

## Release Workflow

### 1. Prepare Release

```bash
# Create release branch
git checkout main
git pull upstream main
git checkout -b release/v1.2.0

# Update version in Cargo.toml
sed -i 's/version = "1.1.0"/version = "1.2.0"/' Cargo.toml

# Update CHANGELOG.md
# Move [Unreleased] items to [1.2.0]
```

### 2. Update Changelog

```markdown
# Changelog

## [Unreleased]

## [1.2.0] - 2024-01-15

### Added
- Circuit breaker for upstream connections (#123)
- WebSocket frame inspection (#124)

### Fixed
- Memory leak in long-running connections (#125)
- Race condition in health checks (#126)

### Changed
- Default timeout increased to 30s (#127)

### Deprecated
- Old config format (will be removed in 2.0.0)

### Security
- Fixed XSS vulnerability in error pages (#128)
```

### 3. Create Release PR

```bash
git add Cargo.toml Cargo.lock CHANGELOG.md
git commit -m "chore: prepare release v1.2.0"
git push origin release/v1.2.0

gh pr create --title "Release v1.2.0" \
    --body "## Release v1.2.0

See CHANGELOG.md for details.

## Checklist
- [ ] Version bumped in Cargo.toml
- [ ] CHANGELOG.md updated
- [ ] All tests pass
- [ ] Documentation updated
"
```

### 4. Merge and Tag

After PR approval:

```bash
# Merge release PR
gh pr merge --squash

# Create tag
git checkout main
git pull upstream main
git tag -a v1.2.0 -m "Release v1.2.0"
git push upstream v1.2.0
```

### 5. Create GitHub Release

```bash
gh release create v1.2.0 \
    --title "Sentinel v1.2.0" \
    --notes-file release-notes.md
```

Or via GitHub UI:
1. Go to Releases
2. Click "Draft a new release"
3. Select tag `v1.2.0`
4. Copy changelog section to description
5. Attach binaries (built by CI)
6. Publish

## Automated Releases

### GitHub Actions Workflow

```yaml
# .github/workflows/release.yml
name: Release

on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    strategy:
      matrix:
        include:
          - target: x86_64-unknown-linux-gnu
            os: ubuntu-latest
          - target: x86_64-apple-darwin
            os: macos-latest
          - target: aarch64-apple-darwin
            os: macos-latest

    runs-on: ${{ matrix.os }}

    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@stable
        with:
          targets: ${{ matrix.target }}

      - name: Build
        run: cargo build --release --target ${{ matrix.target }}

      - name: Package
        run: |
          mkdir -p dist
          cp target/${{ matrix.target }}/release/sentinel dist/
          tar -czvf sentinel-${{ matrix.target }}.tar.gz -C dist .

      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: sentinel-${{ matrix.target }}
          path: sentinel-${{ matrix.target }}.tar.gz

  release:
    needs: build
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Download artifacts
        uses: actions/download-artifact@v4
        with:
          path: artifacts

      - name: Create release
        uses: softprops/action-gh-release@v1
        with:
          files: artifacts/**/*.tar.gz
          generate_release_notes: true
```

## Publishing to crates.io

### First-Time Setup

```bash
# Login to crates.io
cargo login

# Verify package
cargo publish --dry-run
```

### Publishing

```bash
# Publish to crates.io
cargo publish

# For workspace packages, publish in order:
cargo publish -p sentinel-agent-protocol
cargo publish -p sentinel-core
cargo publish -p sentinel
```

### Yanking

If a release has critical issues:

```bash
# Yank version (can still be used as dependency)
cargo yank --version 1.2.0

# Unyank if needed
cargo yank --version 1.2.0 --undo
```

## Docker Images

### Building Images

```dockerfile
# Dockerfile
FROM rust:1.75 as builder
WORKDIR /app
COPY . .
RUN cargo build --release

FROM debian:bookworm-slim
COPY --from=builder /app/target/release/sentinel /usr/local/bin/
ENTRYPOINT ["sentinel"]
```

### Publishing to GHCR

```yaml
# In release workflow
- name: Build and push Docker image
  uses: docker/build-push-action@v5
  with:
    push: true
    tags: |
      ghcr.io/raskell-io/sentinel:${{ github.ref_name }}
      ghcr.io/raskell-io/sentinel:latest
```

## Agent Releases

### Coordinated Releases

When Sentinel protocol changes:

1. Release `sentinel-agent-protocol` first
2. Update agents to use new protocol
3. Release agents
4. Release Sentinel

### Agent Version Matrix

| Sentinel | Protocol | WAF | Auth | JS |
|----------|----------|-----|------|----|
| 1.2.0 | 0.2.0 | 0.3.0 | 0.2.0 | 0.2.0 |
| 1.1.0 | 0.1.0 | 0.2.0 | 0.1.0 | 0.1.0 |

## Hotfix Releases

For critical bugs in production:

```bash
# Create hotfix branch from release tag
git checkout -b hotfix/v1.2.1 v1.2.0

# Apply minimal fix
git cherry-pick <fix-commit>

# Bump patch version
sed -i 's/version = "1.2.0"/version = "1.2.1"/' Cargo.toml

# Update changelog
# Add to ## [1.2.1] section

# Tag and release
git tag -a v1.2.1 -m "Hotfix v1.2.1"
git push upstream v1.2.1

# Merge fix to main
git checkout main
git merge hotfix/v1.2.1
```

## Release Checklist

### Pre-Release

- [ ] All tests pass on main
- [ ] Changelog is complete
- [ ] Documentation is updated
- [ ] Breaking changes are documented
- [ ] Performance benchmarks run
- [ ] Security audit complete

### Release

- [ ] Version bumped
- [ ] Release PR merged
- [ ] Tag created and pushed
- [ ] GitHub release created
- [ ] Binaries attached
- [ ] Docker images published
- [ ] Published to crates.io

### Post-Release

- [ ] Announcement posted (blog, Discord)
- [ ] Documentation site updated
- [ ] Homebrew formula updated
- [ ] Monitor for issues

## Long-Term Support

### LTS Versions

Major versions may receive LTS support:

| Version | Status | Support Until |
|---------|--------|---------------|
| 2.x | Current | - |
| 1.x | LTS | 2025-12-31 |
| 0.x | EOL | - |

### Backporting Fixes

For LTS versions:

```bash
# Cherry-pick security fix to LTS branch
git checkout v1.x
git cherry-pick <security-fix-commit>
git push upstream v1.x

# Create patch release
git tag -a v1.5.1 -m "Security fix"
git push upstream v1.5.1
```

## Next Steps

- [Contributing](../contributing/) - How to contribute
- [PR Process](../pr-process/) - Submitting changes
- [Testing](../testing/) - Testing requirements

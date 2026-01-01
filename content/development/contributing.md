+++
title = "Contributing"
weight = 4
+++

Guide to contributing to Sentinel and its ecosystem.

## Ways to Contribute

### Code Contributions

- Bug fixes
- New features
- Performance improvements
- Documentation updates
- Test coverage

### Non-Code Contributions

- Bug reports with reproduction steps
- Feature requests with use cases
- Documentation improvements
- Answering questions in discussions
- Code reviews

## Getting Started

### 1. Find an Issue

Browse [GitHub Issues](https://github.com/raskell-io/sentinel/issues):

- `good first issue` - Suitable for newcomers
- `help wanted` - Community contributions welcome
- `bug` - Confirmed bugs
- `enhancement` - New features

### 2. Fork and Clone

```bash
# Fork on GitHub, then clone
git clone https://github.com/YOUR_USERNAME/sentinel.git
cd sentinel

# Add upstream remote
git remote add upstream https://github.com/raskell-io/sentinel.git
```

### 3. Create a Branch

```bash
# Sync with upstream
git fetch upstream
git checkout main
git merge upstream/main

# Create feature branch
git checkout -b feature/your-feature-name
```

### 4. Make Changes

Follow the [Code Style](../code-style/) guide and ensure:

```bash
# Format code
cargo fmt

# Check lints
cargo clippy -- -D warnings

# Run tests
cargo test
```

### 5. Commit Changes

Write clear commit messages:

```
feat: add circuit breaker for upstream connections

- Implement failure counting with sliding window
- Add configurable threshold and timeout
- Include metrics for circuit state changes

Closes #123
```

Commit message format:

| Prefix | Usage |
|--------|-------|
| `feat:` | New feature |
| `fix:` | Bug fix |
| `docs:` | Documentation only |
| `refactor:` | Code change without feature/fix |
| `test:` | Adding/updating tests |
| `perf:` | Performance improvement |
| `chore:` | Maintenance tasks |

### 6. Push and Create PR

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub.

## Development Workflow

### Branching Strategy

```
main                 # Stable, release-ready
├── feature/xyz      # New features
├── fix/issue-123    # Bug fixes
└── docs/update-xyz  # Documentation
```

### Branch Naming

| Pattern | Example |
|---------|---------|
| `feature/description` | `feature/circuit-breaker` |
| `fix/issue-number` | `fix/issue-123` |
| `docs/description` | `docs/agent-api` |
| `refactor/description` | `refactor/config-parsing` |

### Keep Branches Updated

```bash
# Rebase on main before PR
git fetch upstream
git rebase upstream/main

# Resolve conflicts if any
git add .
git rebase --continue

# Force push to update PR
git push --force-with-lease
```

## Code Review Process

### What Reviewers Look For

1. **Correctness** - Does it work as intended?
2. **Tests** - Is it properly tested?
3. **Style** - Does it follow conventions?
4. **Performance** - Any performance concerns?
5. **Security** - Any security implications?
6. **Documentation** - Is it documented?

### Responding to Reviews

- Address all comments
- Push fixes as new commits (easier to review)
- Request re-review when ready
- Squash commits before merge

### Review Etiquette

- Be respectful and constructive
- Explain the "why" behind suggestions
- Distinguish between blocking issues and suggestions
- Acknowledge good solutions

## Testing Requirements

### All PRs Must Include

1. **Unit tests** for new functionality
2. **Integration tests** for user-facing features
3. **Documentation** for public APIs

### Test Coverage

```bash
# Generate coverage report
cargo install cargo-tarpaulin
cargo tarpaulin --out Html

# Open report
open tarpaulin-report.html
```

Aim for >80% coverage on new code.

## Documentation

### When to Document

- New public APIs
- Configuration options
- CLI arguments
- Behavior changes

### Documentation Locations

| Type | Location |
|------|----------|
| API docs | Rust doc comments |
| User guide | `docs/` or website |
| README | Repository root |
| Changelog | `CHANGELOG.md` |

### Update the Changelog

Add entries under `[Unreleased]`:

```markdown
## [Unreleased]

### Added
- Circuit breaker for upstream connections (#123)

### Fixed
- Memory leak in WebSocket handler (#124)

### Changed
- Default timeout increased to 30s (#125)
```

## Agent Contributions

### Creating a New Agent

1. Use the protocol library:

```toml
[dependencies]
sentinel-agent-protocol = "0.1"
```

2. Implement the handler trait:

```rust
use sentinel_agent_protocol::{AgentHandler, RequestHeadersEvent};

pub struct MyAgent { }

#[async_trait]
impl AgentHandler for MyAgent {
    async fn on_request_headers(
        &self,
        event: RequestHeadersEvent,
    ) -> RequestDecision {
        // Your logic here
        RequestDecision::Allow
    }
}
```

3. See [Custom Agents](/agents/custom/) for full guide.

### Agent Repository Setup

New agent repositories should include:

```
sentinel-agent-xyz/
├── Cargo.toml
├── README.md
├── LICENSE
├── .github/
│   └── workflows/
│       └── ci.yml
├── src/
│   ├── lib.rs
│   └── main.rs
└── tests/
    └── integration.rs
```

## Security Issues

### Reporting Security Vulnerabilities

**Do not open public issues for security vulnerabilities.**

Instead:

1. Email security@raskell.io
2. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

We will respond within 48 hours.

### Security Fix Process

1. Report received and acknowledged
2. Issue confirmed and severity assessed
3. Fix developed in private branch
4. Security advisory prepared
5. Coordinated disclosure with fix release

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (Apache 2.0 or MIT, at your option).

## Getting Help

- **Discussions**: [GitHub Discussions](https://github.com/raskell-io/sentinel/discussions)
- **Chat**: Discord (link in README)
- **Issues**: [GitHub Issues](https://github.com/raskell-io/sentinel/issues)

## Next Steps

- [Pull Request Process](../pr-process/) - PR guidelines
- [Testing](../testing/) - Testing strategy
- [Code Style](../code-style/) - Formatting conventions

+++
title = "Pull Request Process"
weight = 9
+++

Guidelines for submitting and reviewing pull requests.

## Before Submitting

### Pre-PR Checklist

- [ ] Code compiles without warnings: `cargo build`
- [ ] All tests pass: `cargo test`
- [ ] Code is formatted: `cargo fmt`
- [ ] Lints pass: `cargo clippy -- -D warnings`
- [ ] Documentation updated if needed
- [ ] Changelog updated for user-facing changes
- [ ] Commit messages follow conventions

### Branch Preparation

```bash
# Sync with upstream
git fetch upstream
git rebase upstream/main

# Squash WIP commits
git rebase -i upstream/main
# Mark commits as 'squash' or 'fixup'

# Force push to update branch
git push --force-with-lease
```

## Creating a Pull Request

### PR Title Format

```
<type>: <description>

Examples:
feat: add circuit breaker for upstream connections
fix: resolve memory leak in WebSocket handler
docs: update agent development guide
refactor: simplify config parsing logic
perf: optimize route matching algorithm
test: add integration tests for health checks
chore: update dependencies
```

### PR Description Template

```markdown
## Summary

Brief description of what this PR does.

## Changes

- Added X functionality
- Fixed Y bug
- Updated Z documentation

## Testing

Describe how you tested these changes:
- Unit tests added/updated
- Manual testing performed
- Integration tests run

## Related Issues

Closes #123
Related to #456

## Checklist

- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] Changelog entry added
- [ ] Breaking changes documented
```

## PR Size Guidelines

### Ideal PR Size

| Type | Lines Changed | Files |
|------|--------------|-------|
| Bug fix | < 100 | 1-3 |
| Feature | < 500 | 3-10 |
| Refactor | < 300 | 5-15 |

### Large PRs

If your PR is large:

1. Consider splitting into smaller PRs
2. Add detailed description explaining the scope
3. Use a feature branch with incremental commits
4. Request multiple reviewers

### Stacked PRs

For large features:

```
main
└── feature/base-infrastructure (PR #1)
    └── feature/core-logic (PR #2)
        └── feature/api-integration (PR #3)
```

## Review Process

### Getting Reviews

1. **Request Reviewers**: Add relevant team members
2. **Add Labels**: `needs-review`, feature area labels
3. **Link Issues**: Reference related issues
4. **CI Must Pass**: All checks must be green

### Review Timeline

| Priority | Target Response |
|----------|-----------------|
| Critical (security) | Same day |
| High (blocking) | 1 day |
| Normal | 2-3 days |
| Low (docs, chores) | 1 week |

### Review States

| State | Meaning |
|-------|---------|
| Approved | Ready to merge |
| Changes Requested | Must address feedback |
| Commented | Non-blocking feedback |

## Responding to Reviews

### Addressing Feedback

```bash
# Make requested changes
git add .
git commit -m "fix: address review feedback"

# Push updates
git push

# Re-request review
```

### Discussing Feedback

- Respond to all comments
- Explain your reasoning if you disagree
- Mark conversations as resolved when addressed
- Use "Resolve conversation" button

### Common Review Patterns

**Nit** - Minor suggestion, non-blocking:
```
nit: Consider renaming this variable for clarity
```

**Question** - Seeking clarification:
```
Q: Why did you choose this approach over X?
```

**Suggestion** - Proposed change:
```
suggestion: This could be simplified:
\`\`\`rust
let result = items.iter().filter(|x| x.is_valid()).count();
\`\`\`
```

## Merge Requirements

### Required Checks

- CI passes (tests, lint, format)
- At least one approval
- No unresolved conversations
- Branch is up to date with main

### Merge Strategy

Use **Squash and Merge** for most PRs:

```
feat: add circuit breaker (#123)

- Implement failure counting
- Add configurable threshold
- Include metrics

Co-authored-by: Reviewer <reviewer@example.com>
```

Use **Rebase and Merge** for:
- Multiple logical commits that should be preserved
- Large features with meaningful history

### After Merge

1. Delete the feature branch
2. Verify deployment (if applicable)
3. Close related issues
4. Update documentation if needed

## Special Cases

### Draft PRs

Use draft PRs for:
- Work in progress needing early feedback
- Experiments
- RFC-style discussions

```bash
# Create PR as draft via CLI
gh pr create --draft
```

### Breaking Changes

For breaking changes:

1. Add `breaking` label
2. Document migration path in PR description
3. Update CHANGELOG with `### BREAKING`
4. Consider deprecation period

```markdown
## BREAKING CHANGES

This PR changes the configuration format for upstreams.

### Migration

Before:
\`\`\`kdl
upstream "backend" {
    address "127.0.0.1:3000"
}
\`\`\`

After:
\`\`\`kdl
upstream "backend" {
    targets {
        target { address "127.0.0.1:3000" }
    }
}
\`\`\`
```

### Security Fixes

For security-related changes:

1. Do NOT include exploit details in public PR
2. Coordinate with maintainers privately
3. Prepare security advisory
4. Merge and release together

### Reverts

If a change needs to be reverted:

```bash
git revert <commit-hash>
git push origin revert-branch

# Create PR with explanation
gh pr create --title "revert: <original title>" \
    --body "Reverts #123 due to <reason>"
```

## PR Hygiene

### Keep PRs Current

```bash
# Update branch regularly
git fetch upstream
git rebase upstream/main
git push --force-with-lease
```

### Close Stale PRs

PRs inactive for 30+ days may be closed. To reopen:
1. Rebase on current main
2. Address any outdated feedback
3. Re-request review

### PR Labels

| Label | Meaning |
|-------|---------|
| `needs-review` | Ready for review |
| `wip` | Work in progress |
| `breaking` | Contains breaking changes |
| `security` | Security-related |
| `docs` | Documentation only |
| `good-first-issue` | Good for newcomers |

## GitHub CLI Commands

```bash
# Create PR
gh pr create

# Check PR status
gh pr status

# View PR
gh pr view 123

# Checkout PR locally
gh pr checkout 123

# Merge PR
gh pr merge 123 --squash

# Request review
gh pr edit 123 --add-reviewer username
```

## Next Steps

- [Contributing](../contributing/) - Contribution guidelines
- [Code Style](../code-style/) - Formatting conventions
- [Release Process](../releases/) - How releases work

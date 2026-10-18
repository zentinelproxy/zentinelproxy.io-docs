# zentinelproxy.io-docs

Documentation site for [Zentinel](https://github.com/zentinelproxy/zentinel).

**Live:** https://docs.zentinelproxy.io

## Quick Start

```bash
# Install tools
mise install

# Start dev server
mise run serve
```

Visit http://127.0.0.1:1111

## Tasks

| Task | Description |
|------|-------------|
| `mise run serve` | Dev server with live reload |
| `mise run build` | Build for production |
| `mise run check` | Check for broken links |
| `mise run check-kdl` | Validate KDL snippets (needs `zentinel`, or `ZENTINEL_BIN`) |
| `mise run clean` | Clean build artifacts |

## Structure

```
zentinelproxy.io-docs/
├── config.toml           # Zola configuration
├── content/
│   ├── _index.md         # Introduction
│   ├── getting-started/  # Installation, quick start
│   ├── concepts/         # Architecture, design
│   ├── configuration/    # Config reference
│   ├── agents/           # Agent system docs
│   ├── operations/       # Production guides
│   ├── deployment/       # Deployment options
│   ├── examples/         # Example configs
│   ├── development/      # Contributing guides
│   ├── reference/        # API, CLI, metrics
│   └── appendix/         # Changelog, FAQ, license
├── syntaxes/             # Custom syntax highlighting
└── themes/tanuki/        # Documentation theme
```

## Writing Docs

Create `content/section/page.md`:

```markdown
+++
title = "Page Title"
weight = 1
+++

Content in Markdown...
```

Code blocks with syntax highlighting:

````markdown
```kdl
routes {
    route "api" {
        matches { path-prefix "/api/" }
        upstream "backend"
    }
}
```
````

### KDL snippets are validated

CI runs every ` ```kdl ` block through a pinned Zentinel release
(`zentinel validate --skip-network --skip-agents --skip-certs` and
`zentinel lint`) and fails on errors and on "is being ignored" lint warnings
(unknown or misplaced keys). The checker adds the boilerplate a snippet leaves
out — `system`, a listener, stubs for upstreams/filters/agents it references
when the snippet has no such block, and the plural wrapper around a bare
`route "x" { }` — but never rewrites what the snippet says.

A piece that cannot stand alone (the inside of a block shown out of context,
an intentionally wrong "before" example, `...` elisions) is fenced as
` ```fragment,kdl `. It renders and highlights exactly like ` ```kdl `
(Zola uses the last fence token as the language) and is skipped by the check.

```bash
# Run locally against a Zentinel binary (release archive or cargo build)
ZENTINEL_BIN=/path/to/zentinel mise run check-kdl
python3 scripts/check_kdl.py --zentinel /path/to/zentinel content/examples/websocket.md
```

## Tech Stack

- [Zola](https://www.getzola.org/) — Static site generator
- [mise](https://mise.jdx.dev/) — Task runner
- [Tanuki](https://github.com/raskell-io/tanuki) — Documentation theme

## Related

- [zentinel](https://github.com/zentinelproxy/zentinel) — Main repository
- [zentinelproxy.io](https://github.com/zentinelproxy/zentinelproxy.io) — Marketing site
- [Discussions](https://github.com/zentinelproxy/zentinel/discussions) — Questions and ideas

## License

Apache 2.0


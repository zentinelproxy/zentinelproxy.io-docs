# zentinelproxy.io-docs

Documentation site for [Zentinel](https://github.com/zentinelproxy/zentinel).

**Live:** https://zentinelproxy.io/docs

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
server {
    listener "0.0.0.0:8080"
}
```
````

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


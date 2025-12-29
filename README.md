# Sentinel Documentation

Documentation for [Sentinel](https://github.com/raskell-io/sentinel), a security-first reverse proxy built on Pingora.

**Live Site:** https://sentinel.raskell.io

Built with [Zola](https://www.getzola.org/) and the [Tanuki](https://github.com/raskell-io/tanuki) theme.

## Structure

```
sentinel.raskell.io-docs/
├── content/              # Documentation pages
│   ├── _index.md         # Introduction
│   ├── getting-started/  # Getting started guide
│   ├── concepts/         # Core concepts
│   ├── configuration/    # Configuration reference
│   └── ...
├── themes/tanuki/        # Tanuki theme (submodule)
├── config.toml           # Zola configuration
└── mise.toml             # Task runner configuration
```

## Getting Started

### Prerequisites

- [mise](https://mise.jdx.dev/) - Task runner (installs Zola automatically)

### Install Dependencies

```bash
mise install
```

### Development

Serve with live reload:

```bash
mise run serve
# Visit http://127.0.0.1:1111
```

### Build

```bash
mise run build
```

Output in `public/`.

## Available Tasks

| Task | Description |
|------|-------------|
| `mise run build` | Build documentation |
| `mise run serve` | Serve with live reload |
| `mise run check` | Check for broken links |
| `mise run clean` | Clean build artifacts |

## Writing Documentation

### Creating Pages

1. Create a `.md` file in the appropriate `content/` subdirectory
2. Add front matter:
   ```toml
   +++
   title = "Page Title"
   weight = 1
   +++
   ```
3. Write content in Markdown

### Code Blocks

Use language-specific fences:

````markdown
```kdl
route "api" {
    pattern "/api/*"
    service_type "api"
}
```
````

## License

[MIT](LICENSE) or [Apache-2.0](LICENSE-APACHE)

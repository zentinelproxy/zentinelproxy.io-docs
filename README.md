# Sentinel Documentation

This repository contains the versioned documentation for [Sentinel](https://github.com/raskell-io/sentinel), a security-first reverse proxy built on Pingora.

**Documentation Site:** https://sentinel.raskell.io

## Structure

```
sentinel.raskell.io-docs/
├── versions/           # Versioned documentation
│   └── 25.12/          # Version 25.12 documentation
│       ├── book.toml   # mdBook configuration
│       ├── src/        # Markdown source files
│       └── theme/      # Custom theme files
├── versions.json       # Version configuration
├── mise.toml           # Build tool configuration
└── .mise/tasks/        # Build tasks
```

## Getting Started

### Prerequisites

- [mise](https://mise.jdx.dev/) - Runtime version manager and task runner
- [mdBook](https://rust-lang.github.io/mdBook/) - Installed automatically via mise

### Install Dependencies

```bash
mise install
```

### Development

Serve documentation with live reload:

```bash
# Serve default version
mise run serve

# Serve specific version
VERSION=25.12 mise run serve
```

### Build

Build all documentation versions:

```bash
mise run build
```

Output will be in the `build/` directory.

### Creating a New Version

When releasing a new version of Sentinel, create a corresponding docs version:

```bash
# Create new version from current default
mise run new-version 26.01

# Or specify source version
mise run new-version 26.01 --from 25.12
```

This will:
1. Copy the source version's documentation
2. Update version references
3. Update `versions.json` to mark the new version as latest

### Deploy

Deploy to GitHub Pages:

```bash
mise run deploy
```

## Available Tasks

| Task | Description |
|------|-------------|
| `mise run build` | Build all documentation versions |
| `mise run serve` | Serve with live reload |
| `mise run deploy` | Deploy to GitHub Pages |
| `mise run new-version` | Create a new version |
| `mise run clean` | Clean build artifacts |

## Versioning Scheme

Documentation versions follow Sentinel's CalVer scheme: `YY.MM` (e.g., `25.12` for December 2025).

Each version contains:
- Complete documentation snapshot at release time
- Version-specific configuration and code examples
- Version picker for navigating between versions

## Writing Documentation

### Creating New Pages

1. Create a new Markdown file in the appropriate directory under `versions/<version>/src/`
2. Add an entry to `SUMMARY.md` to include it in the table of contents
3. Write your content using standard Markdown

### Style Guide

- Use clear, concise language
- Include code examples where appropriate
- Use proper heading hierarchy (# for title, ## for main sections, etc.)
- Add cross-references to related topics using relative links
- Include practical examples for complex concepts

### Code Blocks

Use language-specific code blocks for syntax highlighting:

````markdown
```rust
fn main() {
    println!("Hello, Sentinel!");
}
```
````

For configuration examples, use `kdl`:

````markdown
```kdl
route "api" {
    pattern "/api/*"
    service_type "api"
}
```
````

## CI/CD

Documentation is automatically deployed to GitHub Pages on push to `main` branch via GitHub Actions.

## Contributing

1. Make changes to the appropriate version in `versions/<version>/src/`
2. Test locally with `mise run serve`
3. Submit a pull request

## Resources

- [mdBook Documentation](https://rust-lang.github.io/mdBook/)
- [Markdown Guide](https://www.markdownguide.org/)
- [KDL Documentation](https://kdl.dev/)
- [Mise Documentation](https://mise.jdx.dev/)

## License

This documentation is licensed under [MIT](LICENSE) or [Apache-2.0](LICENSE-APACHE).

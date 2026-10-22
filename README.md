<p align="center">
  <a href="https://zentinelproxy.io">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/zentinelproxy/design/main/marks/lockup/zentinel-lockup-dark.svg">
      <img alt="Zentinel" src="https://raw.githubusercontent.com/zentinelproxy/design/main/marks/lockup/zentinel-lockup-light.svg" height="52">
    </picture>
  </a>
</p>

<h3 align="center">Zentinel documentation</h3>

<p align="center">The source of docs.zentinelproxy.io: installation, configuration reference, agents, operations and versioned snapshots for each release series.</p>

<p align="center">
  <a href="https://github.com/zentinelproxy/zentinelproxy.io-docs/actions/workflows/build.yml"><img alt="CI" src="https://github.com/zentinelproxy/zentinelproxy.io-docs/actions/workflows/build.yml/badge.svg"></a>
  <img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-9b4d8a?style=flat&labelColor=1f161e">
</p>

<p align="center">
  <a href="https://docs.zentinelproxy.io">docs.zentinelproxy.io</a> &middot;
  <a href="https://zentinelproxy.io">Website</a> &middot;
  <a href="https://github.com/zentinelproxy">All repositories</a>
</p>

A [Zola](https://www.getzola.org/) site on the
[Tanuki](https://github.com/raskell-io/tanuki) theme (a git submodule). It is
served at the root of docs.zentinelproxy.io, so pages live at
`/getting-started/...`, not `/docs/...`. Every ` ```kdl ` snippet is checked in
CI against a pinned Zentinel release, so a configuration copied from the docs
loads.

## Quick start

```bash
git clone --recurse-submodules https://github.com/zentinelproxy/zentinelproxy.io-docs
cd zentinelproxy.io-docs
mise install        # zola 0.19.2, pinned in mise.toml
mise run serve      # http://127.0.0.1:1111
```

In an existing clone without the theme: `git submodule update --init`.

## Writing docs

Create `content/<section>/<page>.md`:

```markdown
+++
title = "Page Title"
weight = 1
+++

Content in Markdown...
```

| Section | Contents |
|---|---|
| `getting-started/` | installation, quick start, first route and agent, playground |
| `concepts/` | architecture, request flow, routing, Pingora |
| `configuration/` | the KDL reference, one page per block |
| `agents/` | the agent system and agent protocol v2 (`v1/` is kept for history) |
| `control-plane/` | the fleet control plane |
| `deployment/`, `operations/` | running Zentinel in production, migration guides |
| `examples/` | complete configurations |
| `reference/` | CLI, config schema, metrics, error codes, known limitations |
| `development/` | building and contributing to Zentinel |
| `appendix/` | changelog, FAQ, glossary, versioning |
| `v/<YY.MM>/` | snapshots of earlier release series |

Link between pages with Zola's `@/section/page.md` syntax or absolute paths
without a `/docs/` prefix; `scripts/check_links.py` fails the build on a
`/docs/` link or a broken internal path.

**Version snapshots.** Each `content/v/<YY.MM>/` tree is the documentation as
it stood for that release series, listed in `[extra.versions]` in
`config.toml`. Every `_index.md` in a snapshot needs `in_search_index = false`
(the setting is per section, not inherited): Cloudflare Pages caps a file at
25 MiB and the search index grows with every snapshot that is indexed.

### KDL snippets are validated

CI runs every ` ```kdl ` block through the Zentinel release pinned in
`.github/workflows/build.yml` (`zentinel validate --skip-network
--skip-agents --skip-certs` and `zentinel lint`) and fails on errors and on
"is being ignored" lint warnings (unknown or misplaced keys). The checker adds
the boilerplate a snippet leaves out (`system`, a listener, stubs for the
upstreams, filters and agents it references when the snippet has no such
block, and the plural wrapper around a bare `route "x" { }`) but never
rewrites what the snippet says.

A piece that cannot stand alone (the inside of a block shown out of context,
an intentionally wrong "before" example, `...` elisions) is fenced as
` ```fragment,kdl `. It renders like ` ```kdl ` (Zola uses the last fence
token as the language) and is skipped by the check.

```bash
# Against a Zentinel binary (release archive or cargo build)
ZENTINEL_BIN=/path/to/zentinel mise run check-kdl
python3 scripts/check_kdl.py --zentinel /path/to/zentinel content/examples/websocket.md
```

When documenting a newer release, bump `ZENTINEL_RELEASE` **and**
`ZENTINEL_SHA256` in `build.yml` together.

## Development

| Task | What it does |
|---|---|
| `mise run serve` | dev server with live reload on port 1111 |
| `mise run build` | `zola build` into `public/` |
| `mise run check` | `zola check` plus `scripts/check_links.py content` |
| `mise run check-links` | internal links only (`zola check` misses absolute paths) |
| `mise run check-kdl` | validate KDL snippets (needs `zentinel` on `PATH` or `ZENTINEL_BIN`) |
| `mise run update-theme` | move the Tanuki submodule to its latest commit |
| `mise run clean` | remove `public/` |

**Zola version.** `mise.toml` pins zola 0.19.2, but `config.toml` uses zola
0.22's highlighting block (`[markdown.highlighting]` with `style = "class"` and
`extra_grammars`), which 0.19 ignores, so code blocks build without
highlighting. The same mismatch on the website is tracked in
[zentinelproxy.io#51](https://github.com/zentinelproxy/zentinelproxy.io/issues/51);
until it is resolved, build with the mise-pinned version.

**Design tokens are vendored, not edited.** These files are copied from
[zentinelproxy/design](https://github.com/zentinelproxy/design) by its
`deno task sync` and must not be edited by hand here:
`static/css/zentinel-tokens.css`, `static/css/zentinel-fonts.css`,
`static/css/zentinel-bridge.css`, `static/css/zentinel-frame.css` and
`static/fonts/`. Change `tokens.json` in the design repository, rebuild, sync,
and commit the copies. Docs-only styling goes in `static/css/zentinel-docs.css`
and `static/css/site.css`; the theme itself is a submodule and is not edited
here either.

**Playground payload.** `static/wasm/` holds the playground module for
`content/getting-started/playground.md`, built from the zentinel release in
`static/wasm/PAYLOAD_VERSION`. The weekly `payload-staleness.yml` workflow
builds a newer one when zentinel releases and opens a pull request, or a
tracking issue when it cannot.

## Deploy

Cloudflare Pages builds and serves docs.zentinelproxy.io from this repository:
every merge to `main` deploys, and pull requests get a preview deployment. The
Zola version and build command are set in the Cloudflare dashboard. The
`build.yml` workflow is the CI gate (link check, build, KDL validation on every
pull request); on `main` it also publishes a GitHub Pages copy, which is not
what serves docs.zentinelproxy.io.

## Related

- [zentinel](https://github.com/zentinelproxy/zentinel): the proxy the docs describe
- [zentinelproxy.io](https://github.com/zentinelproxy/zentinelproxy.io): the website
- [registry.zentinelproxy.io](https://github.com/zentinelproxy/registry.zentinelproxy.io): per-agent reference pages
- [design](https://github.com/zentinelproxy/design): the design tokens this site vendors
- [Discussions](https://github.com/zentinelproxy/zentinel/discussions): questions and ideas

## License

MIT, see [`LICENSE`](LICENSE).

The typefaces in `static/fonts/`
(Unbounded, Atkinson Hyperlegible Next and Mono) are under the SIL Open Font
License 1.1.

---

<p align="center">
  <sub>Part of <a href="https://zentinelproxy.io">Zentinel</a>, the security-first reverse proxy. The shisa guards the gate.</sub>
</p>

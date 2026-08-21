#!/usr/bin/env python3
"""Check internal links in the Zola content tree.

`zola check` only validates Zola's own `@/page.md` link syntax, so the
absolute-path links this site mostly uses (`/configuration/routes/`) are
never verified and rot silently. This walks every markdown link and
resolves it against the routes Zola will actually serve.

Zola routing: content/foo/bar.md    -> /foo/bar/
              content/foo/_index.md -> /foo/

Usage: python3 scripts/check_links.py [content] [--include-versioned]
Exits non-zero if any internal link is broken.
"""
import os
import re
import sys
from collections import defaultdict

ROOT = sys.argv[1] if len(sys.argv) > 1 else "content"
SKIP_VERSIONED = "--include-versioned" not in sys.argv

LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")


def build_routes(root):
    """Map every URL path Zola will serve -> source file."""
    routes = {}
    for dirpath, _dirs, files in os.walk(root):
        for fn in files:
            if not fn.endswith(".md"):
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, root)
            if fn == "_index.md":
                url = "/" + os.path.dirname(rel).replace(os.sep, "/")
            else:
                url = "/" + rel[:-3].replace(os.sep, "/")
            url = url.rstrip("/")
            if url == "":
                url = "/"
            routes[url] = full
    return routes


def normalize(target, src_url):
    """Resolve a markdown link target to a normalized URL path, or None if external."""
    t = target.strip()
    if t.startswith("<") and t.endswith(">"):
        t = t[1:-1]
    # strip title:  (/foo "Title")
    t = re.split(r"\s+", t, maxsplit=1)[0]
    if not t:
        return None
    low = t.lower()
    if low.startswith(("http://", "https://", "mailto:", "tel:", "#", "data:")):
        return None
    t = t.split("#")[0].split("?")[0]
    if not t:
        return None
    if t.startswith("@/"):
        # Zola internal link: @/path/to/page.md, relative to content root
        url = "/" + t[2:]
    elif t.startswith("/"):
        url = t
    else:
        base = src_url if src_url.endswith("/") else src_url + "/"
        url = os.path.normpath(os.path.join(base, t))
    url = "/" + url.strip("/")
    if url.endswith(".md"):
        url = url[:-3]
    return url.rstrip("/") or "/"


def main():
    routes = build_routes(ROOT)
    broken = defaultdict(list)
    total = 0
    for url, path in sorted(routes.items()):
        if SKIP_VERSIONED and (path.startswith(os.path.join(ROOT, "v" + os.sep))
                               or "/v/" in path.replace(os.sep, "/")):
            continue
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        # strip fenced code blocks so example configs don't produce false hits
        text = re.sub(r"```.*?```", "", text, flags=re.S)
        for label, target in LINK_RE.findall(text):
            resolved = normalize(target, url)
            if resolved is None:
                continue
            total += 1
            # static assets live outside content/
            if re.search(r"\.(png|jpg|jpeg|svg|gif|pdf|zip|txt|css|js|toml|kdl)$", resolved):
                continue
            if resolved not in routes:
                broken[path].append((label, target, resolved))
    print(f"checked {total} internal links across {len(routes)} pages "
          f"({'excluding' if SKIP_VERSIONED else 'including'} content/v/)")
    count = 0
    for path in sorted(broken):
        print(f"\n{path}")
        for label, target, resolved in broken[path]:
            count += 1
            print(f"   [{label}]({target})   -> {resolved}  MISSING")
    print(f"\n{count} broken internal links in {len(broken)} files")
    return 1 if count else 0


if __name__ == "__main__":
    sys.exit(main())

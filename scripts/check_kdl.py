#!/usr/bin/env python3
"""Validate every KDL configuration snippet in the docs against a real Zentinel.

Convention for fenced code blocks
---------------------------------

    ```kdl            a configuration. It must load, pass schema validation and
                      produce no "is being ignored" lint warning (unknown keys,
                      keys in the wrong block, settings run together on a line).

    ```fragment,kdl   a piece that cannot stand alone: the contents of a block
                      shown out of context, an intentionally wrong "before"
                      example, `...` elisions. Skipped. Zola takes the *last*
                      fence token as the language, so this still highlights and
                      renders exactly like ```kdl (``kdl,fragment`` would not).

A ```kdl snippet does not have to repeat the boilerplate every config needs.
Before validating, the checker adds only what is missing, never rewriting what
the snippet says:

  * a snippet made only of `route "x" {..}` nodes (or only `upstream`,
    `listener`, `agent`, `filter` nodes) is wrapped in the plural
    block (`routes { .. }`);
  * `system { }` and a single HTTP `listeners` entry are added when absent;
  * when the snippet has no `upstreams` block, the upstreams its routes
    reference are added as one-target stubs; likewise filters (as agent
    filters) when it has no `filters` block, and agents when it has no
    `agents` block. A snippet that defines one of these blocks must define
    everything it uses from it;
  * absolute `unix-socket` and static-files `root` paths are relocated into a
    scratch directory that exists, since the loader checks them on disk.

Each assembled config is run through

    zentinel validate --skip-network --skip-agents --skip-certs -c FILE
    zentinel lint -c FILE

and fails if either exits non-zero or lint/the loader reports a setting as
ignored, or if the snippet contains one of the TRAPS below (mistakes the
loader accepts silently). Snapshots under content/v/ are frozen and not checked.

Usage:
    python3 scripts/check_kdl.py [--zentinel PATH] [--content DIR]
                                    [--show-config] [FILE.md ...]
"""
import argparse
import concurrent.futures
import os
import re
import shutil
import subprocess
import sys
import tempfile

FENCE_RE = re.compile(r"^([ \t]*)(```+|~~~+)[ \t]*([^\n`]*)$", re.M)
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

PLURALS = {
    "route": "routes",
    "upstream": "upstreams",
    "listener": "listeners",
    "agent": "agents",
    "filter": "filters",
}

SYSTEM_STUB = "system {\n    worker-threads 0\n}\n"
LISTENER_STUB = (
    "listeners {\n"
    '    listener "docs-snippet-http" {\n'
    '        address "127.0.0.1:18080"\n'
    '        protocol "http"\n'
    "    }\n"
    "}\n"
)


# --------------------------------------------------------------------------
# Extraction
# --------------------------------------------------------------------------

def extract_blocks(path):
    """Yield (line, info_tokens, body) for every fenced block in a markdown file."""
    text = open(path, encoding="utf-8").read()
    pos = 0
    while True:
        m = FENCE_RE.search(text, pos)
        if not m:
            return
        indent, fence, info = m.group(1), m.group(2), m.group(3).strip()
        start = m.end() + 1
        close = re.compile(r"^[ \t]*" + re.escape(fence[0]) + "{" + str(len(fence)) + r",}[ \t]*$", re.M)
        cm = close.search(text, start)
        if not cm:
            return
        body = text[start:cm.start()]
        if indent:
            body = "\n".join(l[len(indent):] if l.startswith(indent) else l
                             for l in body.split("\n"))
        line = text.count("\n", 0, m.start()) + 1
        tokens = [t.strip().lower() for t in info.split(",") if t.strip()]
        yield line, tokens, body
        pos = cm.end()


# --------------------------------------------------------------------------
# A minimal KDL scanner: enough to find top-level node names
# --------------------------------------------------------------------------

def top_level_nodes(src):
    """Return the names of nodes at brace depth 0, ignoring strings/comments."""
    names = []
    depth = 0
    i = 0
    n = len(src)
    at_stmt_start = True
    while i < n:
        c = src[i]
        if src.startswith("//", i):
            j = src.find("\n", i)
            i = n if j < 0 else j
            continue
        if src.startswith("/*", i):
            j = src.find("*/", i + 2)
            i = n if j < 0 else j + 2
            continue
        if src.startswith("/-", i):
            i += 2
            continue
        if c == "r" and re.match(r'r#*"', src[i:]):
            hashes = re.match(r"r(#*)\"", src[i:]).group(1)
            end = src.find('"' + hashes, i + 2 + len(hashes))
            i = n if end < 0 else end + 1 + len(hashes)
            at_stmt_start = False
            continue
        if c == '"':
            i += 1
            while i < n and src[i] != '"':
                i += 2 if src[i] == "\\" else 1
            i += 1
            at_stmt_start = False
            continue
        if c == "{":
            depth += 1
            at_stmt_start = True
            i += 1
            continue
        if c == "}":
            depth -= 1
            at_stmt_start = True
            i += 1
            continue
        if c in "\n;":
            at_stmt_start = True
            i += 1
            continue
        if c.isspace() or c == "\\":
            i += 1
            continue
        if at_stmt_start:
            m = re.match(r"[^\s{}();=\"\\/]+", src[i:])
            if m:
                if depth == 0:
                    names.append(m.group(0))
                i += len(m.group(0))
                at_stmt_start = False
                continue
        at_stmt_start = False
        i += 1
    return names


def strip_comments(src):
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    return re.sub(r"(?m)//.*$", "", src)


def assemble(snippet):
    """Add the boilerplate a snippet leaves out. Returns the config text."""
    cfg = snippet.rstrip() + "\n"
    names = top_level_nodes(cfg)
    kinds = set(names)
    if len(kinds) == 1 and next(iter(kinds)) in PLURALS:
        cfg = "%s {\n%s}\n" % (PLURALS[next(iter(kinds))], cfg)
        names = top_level_nodes(cfg)
        kinds = set(names)

    code = strip_comments(cfg)

    # Upstreams referenced by routes, when the snippet has no upstreams block
    # (same rule as filters below: a snippet that defines upstreams must
    # define all it uses).
    defined_up = set(re.findall(r'(?m)^\s*upstream\s+"([^"]+)"\s*\{', code))
    referenced_up = set(re.findall(r'(?m)^\s*(?:upstream|fallback-upstream)\s+"([^"]+)"\s*(?:$|;|//)', code))
    referenced_up |= set(re.findall(r'(?m)^\s*(?:shadow|mirror)\s+"([^"]+)"', code))
    missing_up = sorted(referenced_up - defined_up)
    if missing_up and "upstreams" not in kinds:
        cfg += "upstreams {\n%s}\n" % "".join(
            '    upstream "%s" {\n        target "127.0.0.1:19000"\n    }\n' % u for u in missing_up)

    # Filters referenced by routes, when the snippet has no filters block at
    # all (a route shown on its own). A snippet that does define filters must
    # define every one it uses.
    if "filters" not in kinds:
        referenced_f = []
        for args in re.findall(r'(?m)^\s*filters((?:\s+"[^"]+")+)', code):
            referenced_f += re.findall(r'"([^"]+)"', args)
        referenced_f = sorted(set(referenced_f))
        if referenced_f:
            cfg += "filters {\n%s}\n" % "".join(
                '    filter "%s" {\n        type "agent"\n        agent "%s"\n    }\n' % (f, f)
                for f in referenced_f)
            code = strip_comments(cfg)

    # Agents referenced by filters but not defined.
    defined_ag = set(re.findall(r'(?m)^\s*agent\s+"([^"]+)"[^\n{]*\{', code))
    referenced_ag = set(re.findall(r'(?m)^\s*agent\s+"([^"]+)"\s*(?:$|;|//|\})', code))
    missing_ag = sorted(referenced_ag - defined_ag)
    if missing_ag and "agents" not in kinds:
        cfg += "agents {\n%s}\n" % "".join(
            '    agent "%s" type="custom" {\n        unix-socket "/tmp/zentinel-docs-%s.sock"\n    }\n'
            % (a, re.sub(r"[^A-Za-z0-9_-]", "_", a)) for a in missing_ag)

    prefix = ""
    if "system" not in kinds and "server" not in kinds:
        prefix += SYSTEM_STUB
    if "listeners" not in kinds:
        prefix += LISTENER_STUB
    return prefix + cfg


# Mistakes the loader accepts without a word, so neither validate nor lint can
# report them. Checked against the snippet text.
TRAPS = [
    # (also: multi-argument `method`, a `filters { }` block inside a route and
    # unknown load-balancing names, checked in traps() below)
    (re.compile(r"(?m)^\s*websocket\s*\{"),
     "`websocket` on a route is a boolean (`websocket #true`); written as a block "
     "it parses as false and WebSocket stays disabled (zentinel#369)"),
]


# Names parse_load_balancing (crates/config/src/kdl/upstreams.rs) accepts;
# anything else silently becomes round robin.
LOAD_BALANCING = {
    "round_robin", "roundrobin", "least_connections", "leastconnections",
    "weighted", "weighted_round_robin", "weighted-round-robin", "ip_hash",
    "iphash", "random", "consistent_hash", "consistenthash",
    "power_of_two_choices", "p2c", "adaptive", "least_tokens_queued",
    "leasttokensqueued", "least_tokens", "maglev", "locality_aware",
    "localityaware", "locality", "peak_ewma", "peakewma", "ewma",
    "deterministic_subset", "subset", "subsetting",
    "weighted_least_connections", "weighted_least_conn", "wlc", "sticky",
    "sticky_session", "stickysession",
}
LB_RE = re.compile(r'(?m)^\s*load-balancing\s+"([^"]+)"')


METHOD_RE = re.compile(r'(?m)^\s*method((?:\s+"[^"]*")+)')


def block_inside(code, child, parent):
    """True if a `child {` block opens anywhere inside a `parent ... {` block."""
    stack = []
    for raw in code.splitlines():
        line = re.sub(r'"(?:\\.|[^"\\])*"', '""', raw)
        for tok in re.finditer(r"[{}]", line):
            if tok.group() == "{":
                head = line[:tok.start()].split(";")[-1].split("}")[-1].strip()
                name = head.split()[0] if head.split() else ""
                if name == child and parent in stack:
                    return True
                stack.append(name)
            elif stack:
                stack.pop()
    return False


def traps(snippet):
    code = strip_comments(snippet)
    found = [msg for rx, msg in TRAPS if rx.search(code)]
    for args in METHOD_RE.findall(code):
        if len(re.findall(r'"[^"]*"', args)) > 1:
            found.append("method %s: the parser reads only the first method "
                         "(kdl/routes.rs), so the others never match" % args.strip())
    if block_inside(code, "filters", "route"):
        found.append("a filters { } block inside a route is ignored: routes reference "
                     "filters by name (filters \"a\" \"b\"), defined in the top-level filters block")
    for name in LB_RE.findall(code):
        if name.lower() not in LOAD_BALANCING:
            found.append("load-balancing \"%s\" is not a known algorithm and silently "
                         "falls back to round robin (use underscores, e.g. least_connections)" % name)
    return found


# --------------------------------------------------------------------------
# Running zentinel
# --------------------------------------------------------------------------

# Paths the loader checks on disk. They describe the reader's machine, not the
# configuration, so they are relocated under the scratch directory (and
# created there) rather than failing every snippet on a CI runner.
RELOCATE_RE = re.compile(r'(?m)^(\s*)(unix-socket|root)(\s+(?:path=)?)"(/[^"]+)"')


def relocate_paths(config_text, scratch):
    def sub(m):
        indent, key, ws, path = m.groups()
        new = os.path.join(scratch, "fs", path.lstrip("/"))
        os.makedirs(os.path.dirname(new) if key == "unix-socket" else new, exist_ok=True)
        return '%s%s%s"%s"' % (indent, key, ws, new)
    return RELOCATE_RE.sub(sub, config_text)


def run(zentinel, config_text):
    with tempfile.TemporaryDirectory(prefix="zentinel-docs-") as d:
        config_text = relocate_paths(config_text, d)
        path = os.path.join(d, "snippet.kdl")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(config_text)
        problems = []
        env = dict(os.environ, NO_COLOR="1", RUST_LOG="warn")
        cmds = [
            [zentinel, "validate", "--skip-network", "--skip-agents", "--skip-certs", "-c", path],
            [zentinel, "lint", "-c", path],
        ]
        for cmd in cmds:
            try:
                p = subprocess.run(cmd, capture_output=True, text=True, timeout=30,
                                   env=env, cwd=d)
            except subprocess.TimeoutExpired:
                problems.append("%s: timed out" % cmd[1])
                continue
            out = ANSI_RE.sub("", p.stdout + "\n" + p.stderr)
            if p.returncode != 0:
                problems.append("%s exited %d: %s" % (cmd[1], p.returncode, error_summary(out)))
                break
            for line in out.splitlines():
                l = line.strip()
                if "ignored" in l and ("⚠" in l or " WARN " in " %s " % l or l.startswith("WARN")):
                    msg = re.sub(r"^.*?(⚠\s*|WARN\s*)", "", l)
                    if msg not in problems:
                        problems.append(msg)
        return problems


def error_summary(out):
    lines = [l.strip() for l in out.splitlines() if l.strip()]
    for i, l in enumerate(lines):
        if l.startswith("Caused by:") and i + 1 < len(lines):
            return " | ".join(lines[i + 1:i + 3])
    for l in lines:
        if l.startswith("Error:") or "✗" in l:
            return l
    return lines[-1] if lines else "no output"


# --------------------------------------------------------------------------

def collect(content, files):
    if files:
        paths = files
    else:
        paths = []
        for root, dirs, fns in os.walk(content):
            rel = os.path.relpath(root, content)
            if rel == "v" or rel.startswith("v" + os.sep):
                dirs[:] = []
                continue
            dirs.sort()
            for fn in sorted(fns):
                if fn.endswith(".md"):
                    paths.append(os.path.join(root, fn))
    jobs, skipped = [], 0
    for path in paths:
        for line, tokens, body in extract_blocks(path):
            if "kdl" not in tokens:
                continue
            if "fragment" in tokens:
                skipped += 1
                continue
            jobs.append((path, line, body))
    return jobs, skipped


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--zentinel", default=os.environ.get("ZENTINEL_BIN", "zentinel"))
    ap.add_argument("--content", default="content")
    ap.add_argument("--show-config", action="store_true",
                    help="print the assembled config for each failure")
    ap.add_argument("-j", "--jobs", type=int, default=os.cpu_count() or 4)
    ap.add_argument("files", nargs="*")
    args = ap.parse_args()

    zentinel = os.path.abspath(shutil.which(args.zentinel) or args.zentinel)
    if not os.access(zentinel, os.X_OK):
        sys.exit("zentinel binary not found: %s (use --zentinel or ZENTINEL_BIN)" % args.zentinel)
    version = subprocess.run([zentinel, "--version"], capture_output=True, text=True).stdout.strip()

    jobs, skipped = collect(args.content, args.files)
    failures = []

    def check(job):
        path, line, body = job
        cfg = assemble(body)
        return path, line, cfg, traps(body) + run(zentinel, cfg)

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as ex:
        for path, line, cfg, problems in ex.map(check, jobs):
            if problems:
                failures.append((path, line, cfg, problems))

    for path, line, cfg, problems in failures:
        print("%s:%d" % (path, line))
        for p in problems:
            print("    %s" % p)
        if args.show_config:
            print("    --- assembled config ---")
            print("\n".join("    | " + l for l in cfg.splitlines()))
    print("\n%s" % version)
    print("%d kdl snippets checked, %d failed, %d fragments skipped"
          % (len(jobs), len(failures), skipped))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

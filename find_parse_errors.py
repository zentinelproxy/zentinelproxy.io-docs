#!/usr/bin/env python3
"""Find KDL blocks with parse errors (non-versioned only)."""
import re, os, subprocess, tempfile

ZENTINEL = '/Users/zara/Development/github.com/zentinelproxy/zentinel/target/release/zentinel'
CONTENT = 'content'

for root, dirs, files in os.walk(CONTENT):
    rel = os.path.relpath(root, CONTENT)
    if any(rel.startswith(d) for d in ['agents/v1', 'v/']):
        continue
    for fn in sorted(files):
        if not fn.endswith('.md'):
            continue
        path = os.path.join(root, fn)
        with open(path) as f:
            content = f.read()
        for m in re.finditer(r'```kdl\s*\n(.*?)```', content, re.DOTALL):
            block = m.group(1).rstrip()
            line = content[:m.start()].count('\n') + 2
            opens = block.count('{')
            closes = block.count('}')
            if opens != closes:
                rp = os.path.relpath(path, CONTENT)
                print(f'BRACE MISMATCH ({opens} open, {closes} close) {rp}:{line}')
                first = block[:120].replace('\n', '\\n')
                print(f'  {first}')
                print()

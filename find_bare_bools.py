#!/usr/bin/env python3
"""Find bare true/false (not #true/#false) inside KDL code blocks."""
import re, os

CONTENT = 'content'
SKIP_DIRS = {'agents/v1', 'v/'}

count = 0
for root, dirs, files in os.walk(CONTENT):
    rel = os.path.relpath(root, CONTENT)
    if any(rel.startswith(d) for d in SKIP_DIRS):
        continue
    for fn in sorted(files):
        if not fn.endswith('.md'):
            continue
        path = os.path.join(root, fn)
        with open(path) as f:
            content = f.read()
        for m in re.finditer(r'```kdl\s*\n(.*?)```', content, re.DOTALL):
            block = m.group(1)
            block_start = content[:m.start()].count('\n') + 2
            for i, line in enumerate(block.split('\n')):
                stripped = line.strip()
                # Skip comment lines
                if stripped.startswith('//'):
                    continue
                # Find bare true/false (not preceded by #)
                if re.search(r'(?<!#)\b(true|false)\b', stripped):
                    # Skip if it's inside a string
                    if re.search(r'"[^"]*\b(true|false)\b[^"]*"', stripped):
                        continue
                    rp = os.path.relpath(path, CONTENT)
                    actual_line = block_start + i
                    print(f'{rp}:{actual_line}: {stripped}')
                    count += 1

print(f'\nTotal: {count} bare booleans found')

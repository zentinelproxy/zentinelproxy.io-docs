#!/usr/bin/env python3
"""Show main content failures only (not versioned)."""
import re, os, subprocess, tempfile
import validate_blocks as vb

failures = []
for root, dirs, files in os.walk(vb.CONTENT_DIR):
    rel = os.path.relpath(root, vb.CONTENT_DIR)
    if any(rel.startswith(d) for d in vb.SKIP_DIRS) or rel.startswith('v/'):
        continue
    for fn in sorted(files):
        if not fn.endswith('.md'):
            continue
        filepath = os.path.join(root, fn)
        blocks = vb.extract_kdl_blocks(filepath)
        for block in blocks:
            processed = vb.preprocess_config(block['code'])
            if processed is None:
                continue
            ok, err = vb.validate_config(processed)
            if not ok:
                rp = os.path.relpath(filepath, vb.CONTENT_DIR)
                failures.append({'file': rp, 'line': block['line'], 'error': err})

# Group by error type
error_groups = {}
for f in failures:
    key = re.sub(r'"[^"]*"', '"..."', f['error'])
    key = re.sub(r'\d+', 'N', key)
    error_groups.setdefault(key, []).append(f)

print(f"Main content: {len(failures)} failures\n")
for key, group in sorted(error_groups.items(), key=lambda x: -len(x[1])):
    print(f"  [{len(group)}] {key}")
    for f in group[:2]:
        print(f"       {f['file']}:{f['line']}")

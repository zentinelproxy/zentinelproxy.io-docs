#!/usr/bin/env python3
"""Count validation failures by versioned vs non-versioned."""
import re, os, subprocess, tempfile
import validate_blocks as vb

main_fail = 0
versioned_fail = 0
main_pass = 0
versioned_pass = 0

for root, dirs, files in os.walk(vb.CONTENT_DIR):
    rel = os.path.relpath(root, vb.CONTENT_DIR)
    if any(rel.startswith(d) for d in vb.SKIP_DIRS):
        continue
    is_versioned = rel.startswith('v/')
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
            if ok:
                if is_versioned: versioned_pass += 1
                else: main_pass += 1
            else:
                if is_versioned: versioned_fail += 1
                else: main_fail += 1

print(f"Main content:     {main_pass} pass, {main_fail} fail = {100*main_pass/(main_pass+main_fail):.0f}%")
print(f"Versioned (v/):   {versioned_pass} pass, {versioned_fail} fail = {100*versioned_pass/(versioned_pass+versioned_fail):.0f}%")

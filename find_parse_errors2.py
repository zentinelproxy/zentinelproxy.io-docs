#!/usr/bin/env python3
"""Find blocks that cause KDL parse errors specifically (after preprocessing)."""
import re, os, subprocess, tempfile

ZENTINEL = '/Users/zara/Development/github.com/zentinelproxy/zentinel/target/release/zentinel'
CONTENT = 'content'
SKIP_DIRS = {'agents/v1'}

def preprocess(config):
    """Minimal preprocess to match code.js."""
    result = config
    result = re.sub(r'\bcert-path\b', 'cert-file', result)
    result = re.sub(r'\bkey-path\b', 'key-file', result)
    result = re.sub(r'(?<![-\w])socket\s+"(/[^"]*)"', r'unix-socket "\1"', result)
    # Flatten target { address "addr" }
    def flatten(m):
        addr = m.group(1)
        rest = m.group(2)
        w = re.search(r'weight\s+(\d+)', rest)
        return f'target "{addr}" weight={w.group(1)}' if w else f'target "{addr}"'
    result = re.sub(r'target\s*\{[^}]*?address\s+"([^"]+)"([^}]*)\}', flatten, result)
    return result

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
            block = m.group(1).rstrip()
            line_no = content[:m.start()].count('\n') + 2
            processed = preprocess(block)

            # Write a complete config to test just parsing
            full = f'''system {{
    worker-threads 0
}}

listeners {{
    listener "http" {{
        address "0.0.0.0:8080"
        protocol "http"
    }}
}}

routes {{
    route "default" {{
        matches {{ path-prefix "/" }}
        upstream "backend"
    }}
}}

upstreams {{
    upstream "backend" {{
        target "127.0.0.1:3000"
    }}
}}

// --- test block below ---
{processed}
'''
            with tempfile.NamedTemporaryFile(mode='w', suffix='.kdl', delete=False) as f:
                f.write(full)
                f.flush()
                try:
                    r = subprocess.run([ZENTINEL, 'test', '-c', f.name],
                                       capture_output=True, text=True, timeout=5)
                    err = (r.stderr or r.stdout).strip()
                    if 'parse error' in err.lower() or 'kdl parse' in err.lower():
                        rp = os.path.relpath(path, CONTENT)
                        print(f'\n--- {rp}:{line_no} ---')
                        print(processed[:200])
                        count += 1
                except:
                    pass
                finally:
                    os.unlink(f.name)

print(f'\nTotal KDL parse errors: {count}')

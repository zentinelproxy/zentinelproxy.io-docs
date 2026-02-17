#!/usr/bin/env python3
"""
Complete all KDL config snippets into full valid configurations.
Intelligently detects what's present and adds only what's needed.
"""

import re
from pathlib import Path
import subprocess
import tempfile
import os

DOCS_DIR = Path("/Users/zara/Development/github.com/zentinelproxy/zentinelproxy.io-docs/content")
ZENTINEL_BIN = "/Users/zara/.cargo/bin/zentinel"

def test_config(config_text):
    """Test if a config is valid."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.kdl', delete=False) as f:
        f.write(config_text)
        temp_file = f.name
    try:
        result = subprocess.run(
            [ZENTINEL_BIN, '--conf', temp_file, '--test'],
            capture_output=True,
            timeout=3
        )
        return result.returncode == 0
    except:
        return False
    finally:
        os.unlink(temp_file)

def has_block(config, block_name):
    """Check if config has a top-level block."""
    pattern = rf'^\s*{block_name}\s*\{{'
    return bool(re.search(pattern, config, re.MULTILINE))

def get_first_word(config):
    """Get the first keyword in the config."""
    match = re.search(r'^\s*(\w+)', config.strip(), re.MULTILINE)
    return match.group(1) if match else None

def is_syntax_example(config):
    """Check if this is a pure KDL syntax example (not a real config)."""
    first_word = get_first_word(config)
    # Common syntax example keywords
    syntax_keywords = ['name', 'port', 'weight', 'enabled', 'disabled',
                       'optional-field', 'key', 'value', 'my-field']
    return first_word in syntax_keywords

def complete_config(config):
    """Complete a partial config by adding missing required blocks."""
    # Skip if already valid
    if test_config(config):
        return config

    # Skip syntax examples - wrap them in a comment block
    if is_syntax_example(config):
        return f"""// KDL Syntax Example (not a complete config)
system {{
    worker-threads 0
}}

listeners {{
    listener "http" {{
        address "0.0.0.0:8080"
        protocol "http"
    }}
}}

routes {{
    route "example" {{
        matches {{ path-prefix "/" }}
        upstream "backend"
    }}
}}

upstreams {{
    upstream "backend" {{
        targets {{
            target {{ address "127.0.0.1:3000" }}
        }}
    }}
}}

// The syntax being demonstrated:
// {config}
"""

    parts = []

    # Add system if missing
    if not has_block(config, 'system'):
        parts.append("""system {
    worker-threads 0
}""")

    # Add listeners if missing
    if not has_block(config, 'listeners'):
        parts.append("""listeners {
    listener "http" {
        address "0.0.0.0:8080"
        protocol "http"
    }
}""")

    # Add original config
    parts.append(config.strip())

    # Determine if we need routes/upstreams
    needs_routes = not has_block(config, 'routes')
    needs_upstreams = not has_block(config, 'upstreams')

    # If config has agents, listeners, or other blocks but no routes, add them
    if needs_routes:
        parts.append("""routes {
    route "default" {
        matches { path-prefix "/" }
        upstream "backend"
    }
}""")
        needs_upstreams = True

    if needs_upstreams:
        parts.append("""upstreams {
    upstream "backend" {
        targets {
            target { address "127.0.0.1:3000" }
        }
    }
}""")

    completed = "\n\n".join(parts)

    # Test if completion worked
    if test_config(completed):
        return completed

    # If still invalid, return original (we'll report it)
    return config

def process_file(file_path):
    """Process a markdown file and complete partial configs."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content
    fixes = []

    def fix_kdl_block(match):
        prefix = match.group(1)
        kdl_content = match.group(2)
        suffix = match.group(3)

        # Skip if already valid
        if test_config(kdl_content):
            return match.group(0)

        # Try to complete it
        completed = complete_config(kdl_content)

        # Check if we made progress
        if completed != kdl_content:
            if test_config(completed):
                fixes.append("completed")
                return prefix + completed + '\n' + suffix
            else:
                fixes.append("attempted")

        # Return original if we couldn't fix it
        return match.group(0)

    content = re.sub(r'(```kdl\n)(.*?)(```)', fix_kdl_block, content, flags=re.DOTALL)

    if content != original:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True, fixes

    return False, []

def main():
    print("=" * 80)
    print("Complete All KDL Configs")
    print("=" * 80)
    print()

    # Process all markdown files (exclude versioned for now)
    md_files = sorted(DOCS_DIR.rglob("*.md"))
    md_files = [f for f in md_files if '/v/' not in str(f)]

    modified_count = 0
    total_fixed = 0
    total_attempted = 0

    for md_file in md_files:
        rel_path = md_file.relative_to(DOCS_DIR)
        was_modified, fixes = process_file(md_file)

        if was_modified:
            completed = fixes.count("completed")
            attempted = fixes.count("attempted")

            if completed > 0:
                print(f"✓ {rel_path} ({completed} fixed)")
                modified_count += 1
                total_fixed += completed
            if attempted > 0:
                print(f"⚠ {rel_path} ({attempted} attempted but still invalid)")
                total_attempted += attempted

    print()
    print("=" * 80)
    print(f"Modified {modified_count} files")
    print(f"✓ Fixed: {total_fixed} configs")
    if total_attempted > 0:
        print(f"⚠ Attempted but still invalid: {total_attempted} configs")

if __name__ == "__main__":
    main()

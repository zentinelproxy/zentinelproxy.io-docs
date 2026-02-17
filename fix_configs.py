#!/usr/bin/env python3
"""
Fix invalid KDL configs in Zentinel documentation:
1. Replace deprecated 'server' with 'system'
2. Wrap partial snippets in minimal valid configs
"""

import re
from pathlib import Path

DOCS_DIR = Path("/Users/zara/Development/github.com/zentinelproxy/zentinelproxy.io-docs/content")

# Minimal wrapper for incomplete snippets
MINIMAL_WRAPPER_TEMPLATE = """// Documentation example - wrapped in minimal config for validation
system {{
    worker-threads 0
}}

listeners {{
    listener "http" {{
        address "0.0.0.0:8080"
        protocol "http"
    }}
}}

{content}

{extra_sections}"""

def has_block(config, block_name):
    """Check if config has a top-level block."""
    pattern = rf'^\s*{block_name}\s*{{'
    return bool(re.search(pattern, config, re.MULTILINE))

def is_complete_config(config):
    """Check if config has required top-level blocks."""
    has_system = has_block(config, 'system') or has_block(config, 'server')
    has_listeners = has_block(config, 'listeners')
    return has_system and has_listeners

def fix_deprecated_server_keyword(config):
    """Replace 'server {' with 'system {'."""
    return re.sub(r'\bserver\s*{', 'system {', config)

def should_skip_wrapping(config):
    """Determine if a snippet should not be auto-wrapped."""
    # Skip if it's just showing route priority (intentional partial example)
    if re.search(r'route\s+"[^"]+"\s*\{\s*priority\s+\d+\s*\}\s*$', config.strip(), re.MULTILINE):
        return True

    # Skip standalone waf config blocks (documentation-only)
    if config.strip().startswith('waf {') and not has_block(config, 'agents'):
        return True

    # Skip standalone agent definitions (not in agents block)
    if re.match(r'^\s*agent\s+"[^"]+"\s+type=', config.strip()) and not has_block(config, 'agents'):
        return True

    # Skip very short blocks that are clearly just showing syntax
    if len(config.strip().split('\n')) <= 5 and (
        config.strip().startswith('listeners {') or
        config.strip().startswith('limits {')
    ):
        return True

    return False

def wrap_incomplete_snippet(config):
    """Wrap an incomplete snippet in a minimal valid config."""
    if should_skip_wrapping(config):
        return config

    extra_sections = []

    # If config has routes, ensure it has upstreams
    if has_block(config, 'routes') and not has_block(config, 'upstreams'):
        extra_sections.append("""upstreams {
    upstream "backend" {
        targets {
            target { address "127.0.0.1:3000" }
        }
    }
}""")

    # If config doesn't have routes, add a default one
    if not has_block(config, 'routes'):
        if not has_block(config, 'upstreams'):
            extra_sections.append("""upstreams {
    upstream "backend" {
        targets {
            target { address "127.0.0.1:3000" }
        }
    }
}""")
        extra_sections.append("""routes {
    route "default" {
        matches { path-prefix "/" }
        upstream "backend"
    }
}""")

    return MINIMAL_WRAPPER_TEMPLATE.format(
        content=config,
        extra_sections="\n\n".join(extra_sections)
    ).strip()

def process_file(file_path):
    """Process a markdown file and fix KDL configs."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content
    changes = []

    # Find and fix all ```kdl ... ``` blocks
    def replace_kdl_block(match):
        prefix = match.group(1)
        kdl_content = match.group(2)
        suffix = match.group(3)

        original_kdl = kdl_content
        modified = False

        # Fix 1: Replace deprecated 'server' keyword
        kdl_content = fix_deprecated_server_keyword(kdl_content)
        if kdl_content != original_kdl:
            modified = True
            changes.append("server->system")

        # Fix 2: Wrap incomplete snippets
        if not is_complete_config(kdl_content):
            wrapped = wrap_incomplete_snippet(kdl_content)
            if wrapped != kdl_content:
                kdl_content = wrapped
                modified = True
                changes.append("wrapped snippet")

        return prefix + kdl_content + '\n' + suffix

    content = re.sub(r'(```kdl\n)(.*?)(```)', replace_kdl_block, content, flags=re.DOTALL)

    # Only write if changed
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True, changes
    return False, []

def main():
    print("=" * 80)
    print("KDL Config Fixer")
    print("=" * 80)
    print()

    # Process all markdown files (exclude versioned for now)
    md_files = sorted(DOCS_DIR.rglob("*.md"))
    md_files = [f for f in md_files if '/v/' not in str(f)]

    modified_count = 0
    total_changes = {
        "server->system": 0,
        "wrapped snippet": 0
    }

    for md_file in md_files:
        rel_path = md_file.relative_to(DOCS_DIR)
        was_modified, changes = process_file(md_file)

        if was_modified:
            print(f"✓ {rel_path}")
            for change in changes:
                print(f"  - {change}")
                if change in total_changes:
                    total_changes[change] += 1
            modified_count += 1

    print()
    print("=" * 80)
    print(f"Modified {modified_count} files")
    print(f"  - {total_changes['server->system']} server->system replacements")
    print(f"  - {total_changes['wrapped snippet']} snippets wrapped")

if __name__ == "__main__":
    main()

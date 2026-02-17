#!/usr/bin/env python3
"""
Fix invalid KDL snippets by wrapping them in minimal valid configurations.
"""

import re
from pathlib import Path

DOCS_DIR = Path("/Users/zara/Development/github.com/zentinelproxy/zentinelproxy.io-docs/content")

# Minimal boilerplate for wrapping snippets
MINIMAL_WRAPPER = """system {{
    worker-threads 0
}}

listeners {{
    listener "http" {{
        address "0.0.0.0:8080"
        protocol "http"
    }}
}}

{content}

{extra_blocks}"""

def has_top_level_block(config, block_name):
    """Check if config has a top-level block (e.g., 'routes', 'agents')."""
    pattern = rf'^\s*{block_name}\s*{{'
    return re.search(pattern, config, re.MULTILINE) is not None

def is_complete_config(config):
    """Check if a KDL config is complete (has required top-level blocks)."""
    # A complete config should have at least system/server and listeners
    has_system = has_top_level_block(config, 'system') or has_top_level_block(config, 'server')
    has_listeners = has_top_level_block(config, 'listeners')
    return has_system and has_listeners

def is_standalone_block(config):
    """Check if this is a standalone block like 'waf { ... }' or 'agent \"name\" { ... }'."""
    # Match patterns like:
    # - waf { ... }
    # - agent "..." { ... }
    # - route "..." { ... }
    patterns = [
        r'^\s*waf\s*\{',
        r'^\s*agent\s+["\']',
        r'^\s*route\s+["\'].*\{\s*priority',  # Just a route with priority
    ]
    for pattern in patterns:
        if re.search(pattern, config, re.MULTILINE):
            # Make sure it's not part of a larger config
            if not has_top_level_block(config, 'routes') or config.strip().startswith('waf'):
                return True
    return False

def wrap_snippet(config):
    """Wrap a partial snippet in a minimal valid configuration."""
    # Detect what kind of snippet this is
    has_routes = has_top_level_block(config, 'routes')
    has_upstreams = has_top_level_block(config, 'upstreams')
    has_agents = has_top_level_block(config, 'agents')

    extra_blocks = []

    # If it's a standalone agent block, wrap in agents { }
    if is_standalone_block(config):
        if config.strip().startswith('agent'):
            config = f"agents {{\n    {config}\n}}"
            has_agents = True
        elif config.strip().startswith('waf'):
            # waf blocks are special, they need to be in agents as an agent definition
            # Actually, looking at the errors, these seem to be configuration-only blocks
            # Let's skip these for now - they might be intentional snippets
            return None

    # If config has routes but no upstreams, add a dummy upstream
    if has_routes and not has_upstreams:
        extra_blocks.append("""upstreams {
    upstream "backend" {
        targets {
            target { address "127.0.0.1:3000" }
        }
    }
}""")

    # If config doesn't have routes, add a minimal one
    if not has_routes:
        extra_blocks.append("""routes {
    route "default" {
        matches { path-prefix "/" }
        upstream "backend"
    }
}""")
        # Also need upstream
        if not has_upstreams:
            extra_blocks.append("""upstreams {
    upstream "backend" {
        targets {
            target { address "127.0.0.1:3000" }
        }
    }
}""")

    wrapped = MINIMAL_WRAPPER.format(
        content=config,
        extra_blocks="\n\n".join(extra_blocks)
    )

    return wrapped

def process_file(file_path):
    """Process a markdown file and wrap partial KDL snippets."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find all ```kdl ... ``` blocks
    pattern = r'(```kdl\n)(.*?)(```)'

    def replace_kdl_block(match):
        prefix = match.group(1)
        kdl_content = match.group(2)
        suffix = match.group(3)

        # Skip if already complete
        if is_complete_config(kdl_content):
            return match.group(0)

        # Skip waf standalone blocks (they're documentation-only)
        if is_standalone_block(kdl_content) and kdl_content.strip().startswith('waf'):
            return match.group(0)

        # Skip route priority examples (incomplete by design)
        if re.search(r'route\s+"[^"]+"\s*\{\s*priority\s+\d+\s*\}', kdl_content):
            return match.group(0)

        # Try to wrap the snippet
        wrapped = wrap_snippet(kdl_content)
        if wrapped is None:
            return match.group(0)

        return prefix + wrapped + '\n' + suffix

    modified_content = re.sub(pattern, replace_kdl_block, content, flags=re.DOTALL)

    # Only write if changed
    if modified_content != content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(modified_content)
        return True
    return False

def main():
    print("=" * 80)
    print("KDL Snippet Fixer")
    print("=" * 80)
    print()

    # Get all markdown files (excluding versioned)
    md_files = sorted(DOCS_DIR.rglob("*.md"))
    md_files = [f for f in md_files if '/v/' not in str(f)]

    modified_count = 0

    for md_file in md_files:
        rel_path = md_file.relative_to(DOCS_DIR)
        if process_file(md_file):
            print(f"✓ Modified: {rel_path}")
            modified_count += 1

    print()
    print(f"Modified {modified_count} files")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Convert newer agent syntax to older syntax for validation.
"""

import re
from pathlib import Path
import subprocess
import tempfile
import os

DOCS_DIR = Path("/Users/zara/Development/github.com/raskell-io/sentinel.raskell.io-docs/content")
SENTINEL_BIN = "/Users/zara/.cargo/bin/sentinel"

def test_config(config_text):
    """Test if a config is valid."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.kdl', delete=False) as f:
        f.write(config_text)
        temp_file = f.name
    try:
        result = subprocess.run(
            [SENTINEL_BIN, '--conf', temp_file, '--test'],
            capture_output=True,
            timeout=3
        )
        return result.returncode == 0
    except:
        return False
    finally:
        os.unlink(temp_file)

def convert_agent_syntax(config):
    """Convert new agent syntax to old syntax."""

    # Pattern 1: Convert transport "unix_socket" { path "..." } to unix-socket "..."
    def replace_unix_socket(match):
        # Extract the path from inside the transport block
        transport_block = match.group(0)
        path_match = re.search(r'path\s+"([^"]+)"', transport_block)
        if path_match:
            path = path_match.group(1)
            # Return old syntax with proper indentation
            indent = match.group(1) if match.group(1) else '    '
            return f'{indent}unix-socket "{path}"'
        return match.group(0)

    config = re.sub(
        r'(\s*)transport\s+"unix_socket"\s*\{\s*path\s+"[^"]+"\s*\}',
        replace_unix_socket,
        config
    )

    # Pattern 2: Convert transport "grpc" { url "..." } to grpc "..."
    def replace_grpc(match):
        transport_block = match.group(0)
        url_match = re.search(r'url\s+"([^"]+)"', transport_block)
        if url_match:
            url = url_match.group(1)
            indent = match.group(1) if match.group(1) else '    '
            return f'{indent}grpc "{url}"'
        return match.group(0)

    config = re.sub(
        r'(\s*)transport\s+"grpc"\s*\{\s*url\s+"[^"]+"\s*\}',
        replace_grpc,
        config
    )

    # Pattern 3: Convert events ["event1", "event2"] to events "event1" "event2"
    def replace_events_array(match):
        indent = match.group(1)
        events_content = match.group(2)
        # Extract all quoted strings
        events = re.findall(r'"([^"]+)"', events_content)
        if events:
            events_str = ' '.join(f'"{e}"' for e in events)
            return f'{indent}events {events_str}'
        return match.group(0)

    config = re.sub(
        r'(\s*)events\s+\[([^\]]+)\]',
        replace_events_array,
        config
    )

    # Pattern 4: Add type="custom" to agent definitions if missing
    def add_agent_type(match):
        agent_line = match.group(0)
        if 'type=' not in agent_line:
            # Insert type="custom" after the agent name
            agent_line = re.sub(
                r'(agent\s+"[^"]+")(\s*\{)',
                r'\1 type="custom"\2',
                agent_line
            )
        return agent_line

    config = re.sub(
        r'agent\s+"[^"]+"\s*\{',
        add_agent_type,
        config
    )

    # Pattern 5: Remove raw string prefix from schema-content if present
    config = re.sub(r'schema-content\s+r#"', 'schema-content "', config)
    config = re.sub(r'"#\s*\n\s*\}', '"\n    }', config)

    return config

def process_file(file_path):
    """Process a markdown file and convert agent syntax."""
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

        # Apply conversion
        converted = convert_agent_syntax(kdl_content)

        # Test if conversion worked
        if converted != kdl_content:
            if test_config(converted):
                fixes.append("converted")
                return prefix + converted + '\n' + suffix
            else:
                # Try one more time with additional fixes
                # Sometimes we need to remove service-type for certain routes
                if 'service-type "builtin"' in converted:
                    converted2 = re.sub(r'\s*service-type\s+"builtin"', '', converted)
                    if test_config(converted2):
                        fixes.append("converted+fixed")
                        return prefix + converted2 + '\n' + suffix

        # Return original if we couldn't fix it
        return match.group(0)

    content = re.sub(r'(```kdl\n)(.*?)(```)', fix_kdl_block, content, flags=re.DOTALL)

    if content != original:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True, len(fixes)

    return False, 0

def main():
    print("=" * 80)
    print("Agent Syntax Converter (New → Old)")
    print("=" * 80)
    print()

    # Process all markdown files
    md_files = sorted(DOCS_DIR.rglob("*.md"))
    md_files = [f for f in md_files if '/v/' not in str(f)]

    modified_count = 0
    total_fixed = 0

    for md_file in md_files:
        rel_path = md_file.relative_to(DOCS_DIR)
        was_modified, fix_count = process_file(md_file)

        if was_modified and fix_count > 0:
            print(f"✓ {rel_path} ({fix_count} blocks converted)")
            modified_count += 1
            total_fixed += fix_count

    print()
    print(f"Modified {modified_count} files, converted {total_fixed} configs")

if __name__ == "__main__":
    main()

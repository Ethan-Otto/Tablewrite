#!/usr/bin/env python3
"""
Read FoundryVTT spells compendium from LevelDB and extract spell UUIDs and metadata.

This script directly parses the LevelDB .ldb file to extract JSON spell data.
"""

import json
import re
import sys
from pathlib import Path


def extract_spells_from_ldb(ldb_file: Path) -> list[dict]:
    """
    Parse LevelDB .ldb file and extract spell JSON objects.

    LevelDB stores records with keys like "!items!{id}" followed by JSON data.
    We scan for these patterns and extract complete JSON objects.
    """
    with open(ldb_file, 'rb') as f:
        data = f.read()

    results = []

    # Work with binary data to find JSON patterns
    marker = b'!items!'
    pos = 0

    while True:
        # Find next item marker
        pos = data.find(marker, pos)
        if pos == -1:
            break

        # Skip past the marker and ID
        pos += len(marker)

        # Find the opening brace of JSON (skip the ID bytes)
        json_start = data.find(b'{', pos)
        if json_start == -1 or json_start - pos > 100:  # ID should be short
            continue

        # Extract a large chunk that should contain the full JSON
        chunk = data[json_start:json_start + 50000]

        # Find balanced JSON in binary
        brace_count = 0
        json_end = -1
        in_string = False
        escape_next = False
        i = 0

        while i < len(chunk):
            byte = chunk[i:i+1]

            # Only process printable ASCII and common JSON characters
            if byte == b'\\' and not escape_next:
                escape_next = True
                i += 1
                continue

            if escape_next:
                escape_next = False
                i += 1
                continue

            if byte == b'"' and not escape_next:
                in_string = not in_string
            elif not in_string:
                if byte == b'{':
                    brace_count += 1
                elif byte == b'}':
                    brace_count -= 1
                    if brace_count == 0:
                        json_end = i + 1
                        break

            i += 1

        if json_end > 0:
            json_bytes = chunk[:json_end]
            try:
                # Decode JSON bytes, ignoring binary noise
                json_str = json_bytes.decode('utf-8', errors='ignore')

                # Remove any remaining control characters (except \t, \n, \r)
                json_str = ''.join(char if ord(char) >= 32 or char in '\t\n\r' else ' ' for char in json_str)

                obj = json.loads(json_str)

                # Filter for spells only
                if isinstance(obj, dict) and obj.get('type') == 'spell' and 'name' in obj:
                    results.append(obj)
            except (json.JSONDecodeError, UnicodeDecodeError):
                # Skip malformed JSON
                pass

        pos = json_start + 1

    return results


def main():
    # Path to the spells compendium
    compendium_dir = Path(__file__).parent.parent / "data" / "foundry_examples" / "compendium" / "spells"
    ldb_file = compendium_dir / "000005.ldb"

    if not ldb_file.exists():
        print(f"Error: LDB file not found at {ldb_file}", file=sys.stderr)
        sys.exit(1)

    print(f"Reading spells from {ldb_file}...\n")
    spells = extract_spells_from_ldb(ldb_file)

    print(f"Found {len(spells)} spell entries\n")

    if not spells:
        print("⚠ No spells found. The LDB file may be empty or corrupted.")
        return

    # Print spells sorted by name
    spells_sorted = sorted(spells, key=lambda s: s.get('name', ''))

    print(f"{'Name':<35} {'Level':<8} {'School':<15} {'ID'}")
    print("-" * 90)

    for spell in spells_sorted:
        spell_id = spell.get('_id', 'UNKNOWN')
        name = spell.get('name', 'UNKNOWN')
        level = spell.get('system', {}).get('level', '?')
        school = spell.get('system', {}).get('school', '?')

        print(f"{name:<35} {str(level):<8} {school:<15} {spell_id}")

    # Save to JSON file
    output_file = compendium_dir.parent / "spells_extracted.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(spells_sorted, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Saved {len(spells)} spells to {output_file}")

    # Show example UUID format
    example_spell = spells_sorted[0]
    spell_id = example_spell.get('_id')
    uuid = f"Compendium.dnd5e.spells.Item.{spell_id}"

    print(f"\nExample spell: {example_spell.get('name')}")
    print(f"UUID format: {uuid}")
    print(f"\nAll spells follow the pattern: Compendium.dnd5e.spells.Item.{{spell_id}}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Fetch items from FoundryVTT compendiums.

Supports fetching any item subtype (spell, weapon, equipment, etc.)
and automatically deduplicates by source priority.
"""

import sys
import json
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from foundry.items import fetch_items_by_type, deduplicate_items, get_source_stats

# Load environment
load_dotenv(Path(__file__).parent.parent / '.env')


def main():
    parser = argparse.ArgumentParser(description='Fetch items from FoundryVTT compendiums')
    parser.add_argument(
        'subtype',
        help='Item subtype to fetch (e.g., spell, weapon, equipment, consumable, container, loot)'
    )
    parser.add_argument(
        '--output',
        '-o',
        help='Output JSON file path (default: data/foundry_examples/<subtype>s.json)'
    )
    parser.add_argument(
        '--deduplicate',
        '-d',
        action='store_true',
        default=True,
        help='Deduplicate items by name (default: True)'
    )
    parser.add_argument(
        '--no-deduplicate',
        dest='deduplicate',
        action='store_false',
        help='Keep all duplicates from different sources'
    )
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Show detailed logging'
    )

    args = parser.parse_args()

    # Set up logging
    import logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(message)s'
    )

    # Determine output file
    if args.output:
        output_file = Path(args.output)
    else:
        output_dir = Path(__file__).parent.parent / 'data' / 'foundry_examples'
        output_dir.mkdir(parents=True, exist_ok=True)

        # Pluralize subtype for filename
        plural = f"{args.subtype}s" if not args.subtype.endswith('s') else args.subtype
        output_file = output_dir / f"{plural}.json"

    print(f"Fetching all '{args.subtype}' items from FoundryVTT...\n")

    # Fetch items
    items = fetch_items_by_type(args.subtype)

    print(f"\n{'='*60}")
    print(f"Total items fetched: {len(items)}")
    print(f"{'='*60}\n")

    # Show source stats before deduplication
    print("Sources before deduplication:")
    for source, count in sorted(get_source_stats(items).items()):
        print(f"  {source}: {count}")

    # Deduplicate if requested
    if args.deduplicate:
        print("\nDeduplicating by name...\n")
        items = deduplicate_items(items, verbose=args.verbose)

        print(f"\n{'='*60}")
        print(f"Unique items after deduplication: {len(items)}")
        print(f"{'='*60}\n")

        print("Sources after deduplication:")
        for source, count in sorted(get_source_stats(items).items()):
            print(f"  {source}: {count}")

    # Save to file
    with open(output_file, 'w') as f:
        json.dump(items, f, indent=2)

    print(f"\n✓ Saved {len(items)} items to {output_file}")

    # Show first 20
    print(f"\n{'Name':<40} {'Source':<25} {'UUID'}")
    print("-" * 120)
    for item in items[:20]:
        uuid = item.get('uuid', 'UNKNOWN')
        source = uuid.split('.')[1] if '.' in uuid else 'unknown'
        print(f"{item.get('name', 'UNKNOWN'):<40} {source:<25} {uuid}")

    if len(items) > 20:
        print(f"... and {len(items) - 20} more")


if __name__ == "__main__":
    main()

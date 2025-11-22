#!/usr/bin/env python3
"""
Fetch all spells from FoundryVTT via the REST API.

Uses alphabet-based querying to work around the 200-result search limit.
Deduplicates by UUID and saves to JSON file.
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv
import requests
import json
from string import ascii_lowercase

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

def fetch_all_spells(output_file: str = None) -> list[dict]:
    """
    Fetch all spells from FoundryVTT using alphabet strategy.

    For letters that hit the 200-result limit, uses two-letter combinations.

    Returns:
        List of spell dicts with name, uuid, and other metadata
    """
    relay_url = os.getenv("FOUNDRY_RELAY_URL")
    api_key = os.getenv("FOUNDRY_API_KEY")
    client_id = os.getenv("FOUNDRY_CLIENT_ID")

    if not all([relay_url, api_key, client_id]):
        raise ValueError("Missing required environment variables (FOUNDRY_RELAY_URL, FOUNDRY_API_KEY, FOUNDRY_CLIENT_ID)")

    print("Fetching all spells using alphabet strategy...\n")

    all_spells = {}  # Use dict to deduplicate by UUID
    letters_at_limit = []  # Track letters that hit 200

    def search_query(query: str) -> list:
        """Helper to search with a query string."""
        url = f"{relay_url}/search"
        headers = {"x-api-key": api_key}
        params = {
            "clientId": client_id,
            "filter": "documentType:Item,subType:spell",
            "query": query
        }

        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data.get('results', data) if isinstance(data, dict) else data

    # Query with each letter
    for letter in ascii_lowercase:
        try:
            results = search_query(letter)

            # Deduplicate by UUID
            for spell in results:
                uuid = spell.get('uuid')
                if uuid:
                    all_spells[uuid] = spell

            print(f"Letter '{letter}': {len(results)} results (total unique: {len(all_spells)})")

            # If we hit the limit, we need to drill down with two-letter combos
            if len(results) == 200:
                letters_at_limit.append(letter)

        except Exception as e:
            print(f"Error fetching '{letter}': {e}")

    # For letters that hit 200, query with two-letter combinations
    if letters_at_limit:
        print(f"\n⚠ Letters at 200 limit: {', '.join(letters_at_limit)}")
        print("Querying with two-letter combinations...\n")

        for letter in letters_at_limit:
            for second in ascii_lowercase:
                query = f"{letter}{second}"
                try:
                    results = search_query(query)

                    for spell in results:
                        uuid = spell.get('uuid')
                        if uuid:
                            all_spells[uuid] = spell

                    if results:
                        print(f"  '{query}': {len(results)} results (total unique: {len(all_spells)})")

                    # If even two-letter combo hits 200, warn
                    if len(results) == 200:
                        print(f"    ⚠ WARNING: '{query}' hit 200 limit - may need 3-letter combos!")

                except Exception as e:
                    print(f"  Error fetching '{query}': {e}")

    # Also try empty query for spells that don't match letters
    try:
        results = search_query("")
        for spell in results:
            uuid = spell.get('uuid')
            if uuid:
                all_spells[uuid] = spell
        print(f"\nEmpty query: {len(results)} results (total unique: {len(all_spells)})")
    except Exception as e:
        print(f"Error with empty query: {e}")

    spells_list = list(all_spells.values())
    spells_sorted = sorted(spells_list, key=lambda s: s.get('name', ''))

    print(f"\n{'='*60}")
    print(f"Total unique spells found: {len(spells_sorted)}")
    print(f"{'='*60}\n")

    # Save to file if specified
    if output_file:
        with open(output_file, 'w') as f:
            json.dump(spells_sorted, f, indent=2)
        print(f"✓ Saved {len(spells_sorted)} spells to {output_file}")

    return spells_sorted


def main():
    # Default output location
    output_file = Path(__file__).parent.parent / 'data' / 'foundry_examples' / 'all_spells.json'

    spells = fetch_all_spells(str(output_file))

    # Show first 20
    print(f"\n{'Name':<40} {'UUID'}")
    print("-" * 120)
    for spell in spells[:20]:
        print(f"{spell.get('name', 'UNKNOWN'):<40} {spell.get('uuid', 'UNKNOWN')}")

    print(f"\nUUID format: Compendium.dnd5e.spells.{{id}}")


if __name__ == "__main__":
    main()

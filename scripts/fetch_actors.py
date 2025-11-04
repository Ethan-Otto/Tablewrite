#!/usr/bin/env python3
"""
Fetch all actors from FoundryVTT compendiums.

Extracts actor name, type, and UUID for all available actors.
Useful for building a local database of creatures and NPCs.
"""

import sys
import json
import logging
import os
from pathlib import Path
from string import ascii_lowercase
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import requests

# Load environment
load_dotenv(Path(__file__).parent.parent / '.env')

logger = logging.getLogger(__name__)


def fetch_all_actors(
    relay_url: str = None,
    api_key: str = None,
    client_id: str = None,
    use_two_letter_fallback: bool = True
) -> list:
    """
    Fetch all actors from FoundryVTT using alphabet strategy.

    Args:
        relay_url: Relay server URL (default: from env)
        api_key: API key (default: from env)
        client_id: Client ID (default: from env)
        use_two_letter_fallback: Use two-letter combos for queries hitting 200 limit

    Returns:
        List of actor dicts with keys: name, type, uuid

    Raises:
        ValueError: If credentials are missing
        RuntimeError: If API call fails
    """
    # Get credentials from environment if not provided
    relay_url = relay_url or os.getenv("FOUNDRY_RELAY_URL")
    api_key = api_key or os.getenv("FOUNDRY_LOCAL_API_KEY")
    client_id = client_id or os.getenv("FOUNDRY_LOCAL_CLIENT_ID")

    if not all([relay_url, api_key, client_id]):
        raise ValueError(
            "Missing required credentials. Set FOUNDRY_RELAY_URL, "
            "FOUNDRY_LOCAL_API_KEY, and FOUNDRY_LOCAL_CLIENT_ID in .env"
        )

    endpoint = f"{relay_url}/search"

    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json"
    }

    all_actors = {}  # Use dict to deduplicate by UUID
    letters_at_limit = []

    def search_query(query: str) -> list:
        """Execute search query and return results."""
        params = {
            "clientId": client_id,
            "filter": "Actor",
            "query": query
        }

        logger.debug(f"Querying actors: '{query}'")

        try:
            response = requests.get(endpoint, params=params, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()

            # Handle both list and dict response formats
            results = data.get("results", []) if isinstance(data, dict) else data

            logger.debug(f"  Found {len(results)} actors")
            return results

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to search for actors with query '{query}': {e}")
            raise RuntimeError(f"Failed to search for actors: {e}") from e

    # Query with each letter of alphabet
    logger.info("Fetching actors (a-z)...")
    for letter in ascii_lowercase:
        results = search_query(letter)

        # Track if we hit the 200 limit
        if len(results) == 200:
            logger.warning(f"  Letter '{letter}' returned max results (200), may be incomplete")
            letters_at_limit.append(letter)

        # Add to results (deduplicating by UUID)
        for actor in results:
            uuid = actor.get("uuid")
            if uuid and uuid not in all_actors:
                all_actors[uuid] = {
                    "name": actor.get("name"),
                    "type": actor.get("subType"),  # Actor type: npc, character, vehicle
                    "uuid": uuid
                }

    # Empty query to catch actors not starting with letters
    logger.info("Fetching actors (non-alphabetic)...")
    results = search_query("")
    for actor in results:
        uuid = actor.get("uuid")
        if uuid and uuid not in all_actors:
            all_actors[uuid] = {
                "name": actor.get("name"),
                "type": actor.get("subType"),  # Actor type: npc, character, vehicle
                "uuid": uuid
            }

    # Two-letter fallback for queries that hit 200 limit
    if letters_at_limit and use_two_letter_fallback:
        logger.info(f"Using two-letter fallback for: {', '.join(letters_at_limit)}")
        for first in letters_at_limit:
            for second in ascii_lowercase:
                query = f"{first}{second}"
                results = search_query(query)

                # Add new results
                for actor in results:
                    uuid = actor.get("uuid")
                    if uuid and uuid not in all_actors:
                        all_actors[uuid] = {
                            "name": actor.get("name"),
                            "type": actor.get("subType"),  # Actor type: npc, character, vehicle
                            "uuid": uuid
                        }

    return list(all_actors.values())


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Fetch all actors from FoundryVTT compendiums')
    parser.add_argument(
        '--output',
        '-o',
        help='Output JSON file path (default: data/foundry_examples/actors.json)'
    )
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Show detailed logging'
    )

    args = parser.parse_args()

    # Set up logging
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
        output_file = output_dir / "actors.json"

    print("Fetching all actors from FoundryVTT...\n")

    # Fetch actors
    actors = fetch_all_actors()

    print(f"\n{'='*60}")
    print(f"Total actors fetched: {len(actors)}")

    # Show type breakdown
    type_counts = {}
    for actor in actors:
        actor_type = actor.get('type', 'unknown')
        type_counts[actor_type] = type_counts.get(actor_type, 0) + 1

    print(f"\nActor types:")
    for actor_type, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"  {actor_type}: {count}")

    # Save to JSON
    with open(output_file, 'w') as f:
        json.dump(actors, f, indent=2)

    print(f"\n✓ Saved {len(actors)} actors to {output_file}")


if __name__ == '__main__':
    main()

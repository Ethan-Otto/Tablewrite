#!/usr/bin/env python
"""Delete all actors with duplicate names, keeping only one of each."""
import asyncio
import sys
import os
from collections import defaultdict

# Add the parent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.websocket.push import list_actors, delete_actor


async def main():
    print("Fetching all world actors from Foundry...")

    result = await list_actors(timeout=10.0)

    if not result.success:
        print(f"Failed to list actors: {result.error}")
        return

    actors = result.actors or []
    print(f"Found {len(actors)} world actors")

    # Group actors by name
    by_name = defaultdict(list)
    for actor in actors:
        by_name[actor.name].append(actor)

    # Find duplicates
    duplicates_to_delete = []
    for name, actor_list in by_name.items():
        if len(actor_list) > 1:
            print(f"\nDuplicate: '{name}' ({len(actor_list)} copies)")
            # Keep the first one, delete the rest
            for actor in actor_list[1:]:
                duplicates_to_delete.append(actor)
                print(f"  - Will delete: {actor.uuid}")

    if not duplicates_to_delete:
        print("\nNo duplicates found!")
        return

    print(f"\n{'='*50}")
    print(f"Will delete {len(duplicates_to_delete)} duplicate actors")
    print(f"{'='*50}\n")

    # Delete duplicates
    deleted = 0
    failed = 0
    for actor in duplicates_to_delete:
        result = await delete_actor(actor.uuid, timeout=10.0)
        if result.success:
            print(f"Deleted: {result.name} ({result.uuid})")
            deleted += 1
        else:
            print(f"Failed to delete {actor.name}: {result.error}")
            failed += 1

    print(f"\n{'='*50}")
    print(f"Summary: {deleted} deleted, {failed} failed")
    print(f"{'='*50}")


if __name__ == "__main__":
    asyncio.run(main())

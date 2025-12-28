#!/usr/bin/env python3
"""Delete all actors in the FoundryVTT world."""

import sys
import os
import argparse
from pathlib import Path

# Add src to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from dotenv import load_dotenv
from foundry.client import FoundryClient

# Load environment variables
load_dotenv(PROJECT_ROOT / ".env")


def main():
    """Delete all actors in the world."""
    parser = argparse.ArgumentParser(description="Delete all actors from FoundryVTT world")
    parser.add_argument("--yes", "-y", action="store_true", help="Skip confirmation prompt")
    args = parser.parse_args()

    client = FoundryClient()

    print("Fetching all actors...")
    all_actors = client.actors.get_all_actors()

    if not all_actors:
        print("No actors found in the world.")
        return

    # Filter to only world actors (not compendium actors)
    world_actors = [
        actor for actor in all_actors
        if actor.get("uuid", actor.get("_id", "")).startswith("Actor.")
    ]

    print(f"Found {len(all_actors)} total actors ({len(world_actors)} in world, {len(all_actors) - len(world_actors)} in compendiums)")

    if not world_actors:
        print("No world actors to delete.")
        return

    print(f"\nWorld actors to delete:")
    for actor in world_actors:
        name = actor.get("name", "Unknown")
        actor_type = actor.get("type", "Unknown")
        uuid = actor.get("uuid", actor.get("_id"))
        print(f"  - {name} ({actor_type}) [{uuid}]")

    # Ask for confirmation unless --yes flag provided
    if not args.yes:
        try:
            response = input(f"\nAre you sure you want to delete all {len(world_actors)} world actors? (yes/no): ")
            if response.lower() != "yes":
                print("Deletion cancelled.")
                return
        except EOFError:
            print("\nNo input available. Use --yes flag to skip confirmation.")
            return

    print("\nDeleting actors...")
    deleted_count = 0
    failed_count = 0

    for actor in world_actors:
        name = actor.get("name", "Unknown")
        uuid = actor.get("uuid", actor.get("_id"))

        try:
            client.actors.delete_actor(uuid)
            deleted_count += 1
            print(f"  ✓ Deleted: {name}")
        except Exception as e:
            failed_count += 1
            print(f"  ✗ Failed to delete {name}: {e}")

    print(f"\nDeletion complete!")
    print(f"  Deleted: {deleted_count}")
    print(f"  Failed: {failed_count}")


if __name__ == "__main__":
    main()

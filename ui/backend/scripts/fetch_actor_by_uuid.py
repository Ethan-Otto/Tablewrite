#!/usr/bin/env python
"""Fetch an actor from Foundry by UUID via WebSocket."""
import asyncio
import sys
import os

# Add the parent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.websocket.push import fetch_actor


async def main():
    uuid = sys.argv[1] if len(sys.argv) > 1 else "Actor.vKEhnoBxM7unbhAL"
    print(f"Fetching actor: {uuid}")

    result = await fetch_actor(uuid, timeout=10.0)

    if result.success:
        entity = result.entity
        print(f"\n=== Actor Found ===")
        print(f"Name: {entity.get('name')}")
        print(f"Type: {entity.get('type')}")
        if 'system' in entity:
            system = entity['system']
            if 'details' in system:
                cr = system['details'].get('cr')
                if cr is not None:
                    print(f"CR: {cr}")
    else:
        print(f"\nFetch failed: {result.error}")


if __name__ == "__main__":
    asyncio.run(main())

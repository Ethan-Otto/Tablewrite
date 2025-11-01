# Item Fetching & Management

Utilities for fetching and managing FoundryVTT compendium items.

## Quick Start

### Fetch Spells
```bash
uv run python scripts/fetch_items.py spell
```

### Fetch Weapons
```bash
uv run python scripts/fetch_items.py weapon
```

### Fetch Equipment (Armor, Wondrous Items, etc.)
```bash
uv run python scripts/fetch_items.py equipment
```

### Fetch All Physical Items
```bash
# Physical item types: equipment, weapon, consumable, container, loot
for type in equipment weapon consumable container loot; do
    uv run python scripts/fetch_items.py $type
done
```

## Item SubTypes

| SubType | Description | Example Items |
|---------|-------------|---------------|
| `spell` | Spells | Fireball, Cure Wounds, Shield |
| `weapon` | Weapons (mundane & magical) | Longsword, Dagger +1, Flame Tongue |
| `equipment` | Armor, wondrous items, accessories | Plate Armor, Ring of Protection, Cloak of Invisibility |
| `consumable` | Potions, scrolls, ammunition | Potion of Healing, Scroll of Fireball |
| `container` | Bags, chests, backpacks | Bag of Holding, Chest |
| `loot` | Treasure, gems, art objects | Gold Pieces, Ruby, Painting |
| `feat` | Feats and features | Alert, Action Surge |
| `background` | Background features | Acolyte, Criminal |
| `race` | Racial traits | Darkvision, Trance |
| `subclass` | Subclass features | Arcane Tradition, Fighting Style |

## Options

```bash
# Custom output location
uv run python scripts/fetch_items.py spell --output my_spells.json

# Keep all duplicates (don't deduplicate)
uv run python scripts/fetch_items.py spell --no-deduplicate

# Verbose logging
uv run python scripts/fetch_items.py spell --verbose
```

## Output Files

By default, items are saved to:
```
data/foundry_examples/spells.json        # Deduplicated spells
data/foundry_examples/weapons.json       # Deduplicated weapons
data/foundry_examples/equipment.json     # Deduplicated equipment
```

## Deduplication

Items are automatically deduplicated by name with source priority:

1. **Player's Handbook** (highest priority)
2. **D&D 5e 2024 rules**
3. **D&D 5e SRD**
4. **Other sources** (homebrew, modules)

If a spell appears in both Player's Handbook and SRD, only the Player's Handbook version is kept.

## Programmatic Usage

```python
from foundry.items import fetch_items_by_type, deduplicate_items

# Fetch all spells
spells = fetch_items_by_type('spell')

# Deduplicate
unique_spells = deduplicate_items(spells)

# Access spell data
for spell in unique_spells:
    print(f"{spell['name']}: {spell['uuid']}")
```

## Module Structure

```
src/foundry/items/
├── __init__.py          # Public API exports
├── manager.py           # ItemManager (CRUD operations via API)
├── fetch.py             # Fetch items from compendiums
└── deduplicate.py       # Deduplication logic
```

## How It Works

### Bypassing the 200-Result Limit

FoundryVTT's search API has a hardcoded 200-result limit. We bypass this by:

1. Querying with each letter (a-z)
2. For letters that hit 200 results, querying with two-letter combinations (aa, ab, ac, etc.)
3. Deduplicating by UUID across all results
4. Also querying with empty string to catch non-letter items

This ensures we get ALL items even for large compendiums.

### Example: Fetching Spells

```
Query 'a': 200 results (hit limit → drill down)
  Query 'aa': 6 results
  Query 'ab': 7 results
  Query 'ac': 17 results
  ...
Query 'b': 100 results (under limit → done)
Query 'c': 195 results (under limit → done)
...

Total: 1,049 unique spells found
After deduplication: 410 unique spell names
```

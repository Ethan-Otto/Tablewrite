# FoundryVTT Compendium Integration

**Date**: 2025-10-31
**Status**: Design Phase - Architecture Extension

## Problem Statement

When creating actors, we need to decide:
1. **Create custom items** (attacks, traits, spells) from scratch?
2. **Reference existing items** from FoundryVTT compendiums (SRD)?
3. **Hybrid approach** (reference when possible, create when necessary)?

## FoundryVTT Compendium Patterns

### Pattern 1: Spell References (Pit Fiend Example)

From `data/foundry_examples/pit_fiend.json`:

```json
{
  "name": "Hellfire Spellcasting",
  "type": "feat",
  "system": {
    "activities": {
      "fN8SjzxRhERq8DlF": {
        "type": "cast",
        "spell": {
          "uuid": "Compendium.dnd5e.spells24.Item.phbsplFireball00",  // ← Reference!
          "level": 5,
          "ability": "cha"
        }
      }
    }
  }
}
```

**Key observation**: The feat references the spell by UUID, and FoundryVTT automatically caches it.

**Items array also includes cached spell**:
```json
{
  "name": "Fireball",
  "type": "spell",
  "flags": {
    "dnd5e": {
      "cachedFor": ".Item.mmHellfireSpellc.Activity.fN8SjzxRhERq8DlF"  // ← Cache marker
    }
  },
  "_stats": {
    "compendiumSource": "Compendium.dnd5e.spells24.Item.phbsplFireball00"  // ← Source
  }
}
```

### Pattern 2: Custom Attacks (Always Created)

From pit_fiend.json:

```json
{
  "name": "Bite",
  "type": "weapon",
  "system": {
    "type": {"value": "natural", "baseItem": ""},  // ← No baseItem reference
    "damage": {
      "base": {
        "number": 3,
        "denomination": 6,
        "types": ["piercing"]
      }
    }
  },
  "_stats": {
    "compendiumSource": "Compendium.dnd-monster-manual.features.Item.mmBite0000000000"  // ← From monster compendium
  }
}
```

**Key observation**: Natural weapons are custom items (not standard weapons), but may come from a monster features compendium.

### Pattern 3: Standard Weapons (Referenced Then Customized)

From `mage_actor.json`:

```json
{
  "name": "Dagger",
  "type": "weapon",
  "system": {
    "type": {
      "value": "simpleM",
      "baseItem": "dagger"  // ← References base item
    },
    "damage": {
      "base": {
        "number": 1,
        "denomination": 4,
        "types": ["piercing"]
      }
    }
  }
}
```

**Key observation**: Standard weapons reference `baseItem` but are still created as custom items (to allow creature-specific modifiers).

---

## Compendium Strategy

### What to Reference vs. Create

| Type | Strategy | Rationale |
|------|----------|-----------|
| **Spells** | **Reference by UUID** | Standard spells (Fireball, Hold Monster) exist in SRD compendium |
| **Standard Weapons** | **Create with baseItem reference** | Need creature-specific attack bonuses, but metadata comes from SRD |
| **Natural Weapons** | **Create custom** | Unique to creature (Bite, Claw, Breath Weapon) |
| **Traits/Features** | **Create custom** (check compendium first) | Some common features (Magic Resistance) might exist in monster features compendium |
| **Magic Items** | **Reference by UUID** (future) | Standard magic items exist in SRD |

### Compendium Lookup Flow

```
ParsedActorData → Conversion Layer
                      ↓
        ┌─────────────┴──────────────┐
        ↓                            ↓
    Spell?                       Attack/Trait?
        ↓                            ↓
    Search Compendium           Check if standard
        ↓                            ↓
    Found? → Use UUID           Standard → baseItem ref
        ↓                            ↓
    Not Found → Error           Custom → Create
```

---

## Implementation Design

### Component: CompendiumLookup (NEW)

**File**: `src/foundry/compendium_lookup.py`

**Purpose**: Search FoundryVTT compendiums for reusable items

```python
from typing import Optional, Dict, Any
from foundry.client import FoundryClient

class CompendiumLookup:
    """Lookup items in FoundryVTT compendiums."""

    def __init__(self, client: FoundryClient):
        self.client = client
        self._spell_cache: Dict[str, str] = {}  # name → UUID
        self._item_cache: Dict[str, str] = {}   # name → UUID

    def find_spell_uuid(self, spell_name: str) -> Optional[str]:
        """
        Find spell UUID in SRD compendium.

        Args:
            spell_name: Spell name (e.g., "Fireball")

        Returns:
            UUID like "Compendium.dnd5e.spells24.Item.phbsplFireball00"
            or None if not found
        """
        # Check cache first
        if spell_name in self._spell_cache:
            return self._spell_cache[spell_name]

        # Search compendium via REST API
        try:
            results = self.client.search_compendium(
                query=spell_name,
                filter="Spell"
            )

            for result in results:
                if result["name"].lower() == spell_name.lower():
                    uuid = result["uuid"]
                    self._spell_cache[spell_name] = uuid
                    return uuid

        except Exception as e:
            logger.warning(f"Failed to lookup spell '{spell_name}': {e}")

        return None

    def find_item_uuid(self, item_name: str) -> Optional[str]:
        """Find magic item UUID in SRD compendium."""
        # Similar to find_spell_uuid but searches Item compendiums
        pass

    def get_weapon_base_item(self, weapon_name: str) -> Optional[str]:
        """
        Get base item type for standard weapons.

        Args:
            weapon_name: "Dagger", "Longsword", etc.

        Returns:
            Base item identifier: "dagger", "longsword"
            or None if not a standard weapon
        """
        standard_weapons = {
            "dagger": "dagger",
            "shortsword": "shortsword",
            "longsword": "longsword",
            "greatsword": "greatsword",
            "shortbow": "shortbow",
            "longbow": "longbow",
            # ... etc
        }

        return standard_weapons.get(weapon_name.lower())
```

### Updated: convert_to_foundry.py

```python
from .compendium_lookup import CompendiumLookup
from ..actors.parsed_models import ParsedActorData, Attack, Trait

def create_spell_activity(
    spell_name: str,
    spell_level: int,
    compendium: CompendiumLookup
) -> Dict[str, Any]:
    """
    Create spell cast activity with compendium reference.

    Args:
        spell_name: "Fireball", "Hold Monster", etc.
        spell_level: Spell level to cast at
        compendium: Compendium lookup service

    Returns:
        Activity dict with spell reference
    """
    spell_uuid = compendium.find_spell_uuid(spell_name)

    if not spell_uuid:
        raise ValueError(f"Spell '{spell_name}' not found in compendium")

    return {
        "_id": _generate_id(f"cast_{spell_name}"),
        "type": "cast",
        "activation": {"type": "action", "value": None, "override": False},
        "spell": {
            "uuid": spell_uuid,
            "level": spell_level,
            "spellbook": True
        },
        # ... rest of activity structure
    }

def create_weapon_item(
    attack: Attack,
    compendium: CompendiumLookup
) -> FoundryItem:
    """
    Create weapon item with optional base item reference.

    Args:
        attack: Parsed attack data
        compendium: Compendium lookup service

    Returns:
        Weapon item (custom or with baseItem reference)
    """
    # Check if standard weapon
    base_item = compendium.get_weapon_base_item(attack.name)

    return FoundryItem(
        _id=_generate_id(attack.name),
        name=attack.name,
        type="weapon",
        system={
            "type": {
                "value": "natural" if not base_item else "simpleM",
                "baseItem": base_item or ""
            },
            "damage": {
                "base": {
                    "number": attack.damage[0].number,
                    "denomination": attack.damage[0].denomination,
                    "types": [attack.damage[0].type]
                }
            },
            "activities": {
                _generate_id("attack"): _create_attack_activity(attack)
            }
        }
    )

def parsed_to_foundry(
    data: ParsedActorData,
    compendium: CompendiumLookup
) -> FoundryActor:
    """
    Convert ParsedActorData to FoundryVTT actor with compendium lookups.

    Args:
        data: Parsed actor data
        compendium: Compendium lookup service

    Returns:
        Complete FoundryVTT actor
    """
    items = []

    # Attacks
    for attack in data.attacks:
        items.append(create_weapon_item(attack, compendium))

    # Traits
    for trait in data.traits:
        items.append(create_feat_item(trait, compendium))

    # Spells (if spellcaster)
    if data.spells:
        for spell in data.spells:
            # Create spellcasting feature with spell references
            items.append(create_spellcasting_feature(spell, compendium))

    return FoundryActor(
        name=data.name,
        system=_build_system_data(data),
        items=items
    )
```

---

## Search API Integration

### REST API: /search Endpoint

From `foundryvtt-rest-api-relay` documentation:

**Request**:
```http
GET /search?clientId={id}&filter=Spell&query=Fireball
```

**Response**:
```json
[
  {
    "uuid": "Compendium.dnd5e.spells24.Item.phbsplFireball00",
    "name": "Fireball",
    "type": "spell",
    "img": "icons/magic/fire/...",
    "_id": "phbsplFireball00"
  }
]
```

**Filter Options**:
- `filter=Spell` - Search spells
- `filter=Item` - Search items
- `filter=Actor` - Search actors
- `filter=documentType:Spell,package:dnd5e.spells24` - Advanced filtering

### Caching Strategy

**Problem**: Searching compendium on every conversion is slow

**Solution**: Build local cache on first run

```python
class CompendiumCache:
    """Persistent cache of compendium lookups."""

    def __init__(self, cache_file: str = ".cache/compendium.json"):
        self.cache_file = cache_file
        self.spells: Dict[str, str] = {}
        self.items: Dict[str, str] = {}
        self._load()

    def _load(self):
        """Load cache from disk."""
        if os.path.exists(self.cache_file):
            with open(self.cache_file) as f:
                data = json.load(f)
                self.spells = data.get("spells", {})
                self.items = data.get("items", {})

    def save(self):
        """Save cache to disk."""
        os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
        with open(self.cache_file, "w") as f:
            json.dump({
                "spells": self.spells,
                "items": self.items
            }, f, indent=2)

    def get_spell(self, name: str) -> Optional[str]:
        """Get cached spell UUID."""
        return self.spells.get(name.lower())

    def cache_spell(self, name: str, uuid: str):
        """Cache spell UUID."""
        self.spells[name.lower()] = uuid
        self.save()
```

---

## Error Handling

### Spell Not Found

**Scenario**: Stat block references "Homebrew Spell" not in SRD

**Options**:
1. **Fail fast** (v1): Raise error, require manual intervention
2. **Create placeholder** (v2): Create custom spell item with description
3. **Skip** (v2): Log warning, exclude from actor

**Recommendation**: Fail fast for v1 (ensures data quality)

### Compendium Unavailable

**Scenario**: FoundryVTT server offline or compendium not installed

**Options**:
1. **Offline mode**: Create all items custom (no references)
2. **Fail**: Require compendium access for conversion
3. **Partial**: Use cache if available, create custom for misses

**Recommendation**: Fail for v1, add offline mode in v2

---

## Testing Strategy

### Unit Tests

```python
def test_find_spell_uuid():
    """Test spell lookup in compendium."""
    mock_client = MockFoundryClient()
    lookup = CompendiumLookup(mock_client)

    # Mock search result
    mock_client.set_search_result("Fireball", {
        "uuid": "Compendium.dnd5e.spells24.Item.phbsplFireball00",
        "name": "Fireball"
    })

    uuid = lookup.find_spell_uuid("Fireball")
    assert uuid == "Compendium.dnd5e.spells24.Item.phbsplFireball00"

def test_spell_not_found():
    """Test handling of spell not in compendium."""
    lookup = CompendiumLookup(MockFoundryClient())

    uuid = lookup.find_spell_uuid("Homebrew Spell")
    assert uuid is None
```

### Integration Tests

```python
@pytest.mark.integration
def test_real_compendium_lookup():
    """Test lookup against real FoundryVTT instance."""
    client = FoundryClient(target="local")
    lookup = CompendiumLookup(client)

    # Test SRD spells
    assert lookup.find_spell_uuid("Fireball") is not None
    assert lookup.find_spell_uuid("Hold Monster") is not None
    assert lookup.find_spell_uuid("Wall of Fire") is not None
```

---

## Updated Architecture

### Revised Conversion Flow

```
ParsedActorData → CompendiumLookup → Conversion Layer
                      ↓                      ↓
                  Cache/API            FoundryActor
                      ↓                      ↓
              UUID References           Items with
              + Base Items              - Spell UUIDs
                                        - baseItem refs
                                        - Custom data
```

### Updated File Structure

```
src/foundry/
├── client.py                 # FoundryClient (existing)
├── actors.py                 # ActorManager (existing)
├── foundry_models.py         # Type-safe structures (NEW)
├── compendium_lookup.py      # Compendium search/cache (NEW)
├── convert_to_foundry.py     # Conversion with lookups (NEW)
└── __init__.py

.cache/
└── compendium.json           # Persistent lookup cache (NEW)
```

---

## Open Questions

1. **Compendium availability**: Require SRD installed, or support custom compendiums?
2. **Homebrew spells**: How to handle spells not in SRD? Create custom or error?
3. **Monster features**: Build cache of common monster traits (Magic Resistance, etc.)?
4. **Cache invalidation**: How often to refresh compendium cache (FoundryVTT updates)?
5. **Multiple servers**: Support different compendium sets for local vs. Forge?

---

## Next Steps

1. Implement `CompendiumLookup` class with caching
2. Update `convert_to_foundry.py` to use lookups
3. Test spell references with real FoundryVTT instance
4. Build cache of SRD spells on first run
5. Document compendium requirements in README

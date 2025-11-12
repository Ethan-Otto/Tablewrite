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

### Component: Use Existing ItemManager (Updated)

**File**: `src/foundry/items/manager.py` (**EXISTING**)
**File**: `src/foundry/items/fetch.py` (**EXISTING**)

**Purpose**: Already implemented! Search FoundryVTT compendiums for reusable items

**Existing API**:

```python
from foundry.items.fetch import fetch_all_spells
from foundry.items.manager import ItemManager

# Bulk fetch all spells (a-z queries, handles 200-result limit)
all_spells = fetch_all_spells(
    relay_url="...",
    api_key="...",
    client_id="..."
)

# Search by name (via ItemManager)
item_manager = ItemManager(relay_url, foundry_url, api_key, client_id)
spell = item_manager.get_item_by_name("Fireball")
# Returns: {'uuid': 'Compendium.dnd5e.spells24.Item.phbsplFireball00', 'name': 'Fireball', ...}
```

### Component: SpellCache (NEW - Wrapper)

**File**: `src/actors/spell_cache.py` (new)

**Purpose**: Lightweight wrapper around existing infrastructure for actor parsing

```python
from typing import Optional, Dict
from foundry.items.fetch import fetch_all_spells
import logging

logger = logging.getLogger(__name__)


class SpellCache:
    """Cache of spell name → UUID mappings for actor conversion."""

    def __init__(self, relay_url: str, api_key: str, client_id: str):
        self.relay_url = relay_url
        self.api_key = api_key
        self.client_id = client_id
        self._cache: Dict[str, str] = {}  # Lowercase name → UUID
        self._loaded = False

    def load(self):
        """Load all spells from FoundryVTT (run once per session)."""
        if self._loaded:
            return

        logger.info("Loading spell cache from FoundryVTT...")
        spells = fetch_all_spells(
            relay_url=self.relay_url,
            api_key=self.api_key,
            client_id=self.client_id
        )

        for spell in spells:
            name_lower = spell['name'].lower()
            self._cache[name_lower] = spell['uuid']

        self._loaded = True
        logger.info(f"Loaded {len(self._cache)} spells into cache")

    def find_spell_uuid(self, spell_name: str) -> Optional[str]:
        """
        Find spell UUID by name.

        Args:
            spell_name: Spell name (case-insensitive)

        Returns:
            UUID or None if not found
        """
        if not self._loaded:
            self.load()

        return self._cache.get(spell_name.lower())

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
from actors.spell_cache import SpellCache
from actors.parsed_models import ParsedActorData, Attack, Trait, Spell

def create_spell_activity(
    spell: Spell,
    spell_cache: SpellCache
) -> Dict[str, Any]:
    """
    Create spell cast activity with compendium reference.

    Args:
        spell: Parsed spell with name, level, and UUID
        spell_cache: Spell cache service

    Returns:
        Activity dict with spell reference
    """
    # UUID should already be populated during parsing
    if not spell.uuid:
        raise ValueError(f"Spell '{spell.name}' has no UUID (not found in compendium)")

    return {
        "_id": _generate_id(f"cast_{spell.name}"),
        "type": "cast",
        "activation": {"type": "action", "value": None, "override": False},
        "spell": {
            "uuid": spell.uuid,  # Use pre-resolved UUID
            "level": spell.level,
            "spellbook": True
        },
        # ... rest of activity structure
    }

def create_weapon_item(
    attack: Attack,
    spell_cache: SpellCache
) -> FoundryItem:
    """
    Create weapon item with optional base item reference.

    Args:
        attack: Parsed attack data
        spell_cache: Spell cache service (for baseItem lookup)

    Returns:
        Weapon item (custom or with baseItem reference)
    """
    # Check if standard weapon
    base_item = spell_cache.get_weapon_base_item(attack.name)

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
    spell_cache: SpellCache
) -> FoundryActor:
    """
    Convert ParsedActorData to FoundryVTT actor.

    Args:
        data: Parsed actor data (spells already have UUIDs populated)
        spell_cache: Spell cache service

    Returns:
        Complete FoundryVTT actor
    """
    items = []

    # Attacks
    for attack in data.attacks:
        items.append(create_weapon_item(attack, spell_cache))

    # Traits
    for trait in data.traits:
        items.append(create_feat_item(trait))

    # Spells (if spellcaster) - UUIDs already resolved during parsing
    if data.spells:
        for spell in data.spells:
            # Create spellcasting feature with spell references
            items.append(create_spellcasting_feature(spell, spell_cache))

    return FoundryActor(
        name=data.name,
        system=_build_system_data(data),
        items=items
    )
```

---

## Integration into ParsedActorData

### Updated Spell Model (in parsed_models.py)

```python
class Spell(BaseModel):
    """Parsed spell reference."""
    name: str
    level: int
    uuid: Optional[str] = None  # Resolved during parsing from compendium

    # Additional metadata if needed
    school: Optional[str] = None
    casting_time: Optional[str] = None
```

### Updated ParsedActorData (add spells field)

```python
class ParsedActorData(BaseModel):
    """Fully parsed stat block ready for FoundryVTT conversion."""

    # ... existing fields ...

    # Spellcasting
    spells: List[Spell] = []  # Each spell has UUID pre-resolved
    spellcasting_ability: Optional[Literal["int", "wis", "cha"]] = None
```

### Spell Resolution During Parsing (parse_detailed.py)

**Key insight**: Resolve spell UUIDs **during parsing**, not during conversion

```python
def parse_actor_details(
    stat_block: StatBlock,
    api: GeminiAPI,
    spell_cache: SpellCache  # Pass spell cache to parser
) -> ParsedActorData:
    """Parse detailed actor data from stat block using Gemini."""

    # Python-extracted data
    abilities = stat_block.abilities or {}

    # Gemini-parsed data
    parsed_json = _parse_with_gemini(stat_block, api)

    # RESOLVE SPELL UUIDs HERE
    spells_with_uuids = []
    for spell_data in parsed_json.get("spells", []):
        spell_name = spell_data["name"]
        spell_level = spell_data["level"]

        # Lookup UUID in compendium
        uuid = spell_cache.find_spell_uuid(spell_name)

        if not uuid:
            logger.warning(f"Spell '{spell_name}' not found in compendium - skipping")
            continue  # Or raise error in strict mode

        spells_with_uuids.append(Spell(
            name=spell_name,
            level=spell_level,
            uuid=uuid  # ← UUID resolved at parse time!
        ))

    return ParsedActorData(
        source_statblock=stat_block,
        name=stat_block.name,
        armor_class=stat_block.armor_class,
        hit_points=stat_block.hit_points,
        challenge_rating=stat_block.challenge_rating,
        abilities=abilities,
        attacks=parsed_json["attacks"],
        traits=parsed_json["traits"],
        spells=spells_with_uuids,  # ← Spells with UUIDs
        # ... etc
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
├── convert_to_foundry.py     # Conversion (NEW)
├── items/
│   ├── fetch.py              # fetch_all_spells() (EXISTING)
│   ├── manager.py            # ItemManager (EXISTING)
│   └── __init__.py
└── __init__.py

src/actors/
├── models.py                 # StatBlock (existing)
├── parsed_models.py          # ParsedActorData, Spell, Attack, etc. (NEW)
├── parse_detailed.py         # Detailed parsing (NEW)
├── spell_cache.py            # SpellCache wrapper (NEW)
└── __init__.py
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

# Implementation Plan: Actor Parsing Data Structures

**Created**: 2025-10-31 15:42:00 UTC
**Status**: Ready for Implementation
**References**:
- `docs/actor_parsing_architecture.md`
- `docs/foundry_actor_structure.md`
- `docs/compendium_integration.md`

---

## File Organization

### Proposed Structure
```
src/actors/                     # Extraction and basic parsing
├── models.py                   # StatBlock, NPC (EXISTING - minor updates)
├── extract_stat_blocks.py      # Extract from XML (EXISTING)
├── parse_stat_blocks.py        # Basic Gemini parsing (EXISTING)
└── __init__.py

src/foundry/actors/             # FoundryVTT-specific models and conversion (NEW DIRECTORY)
├── models.py                   # ParsedActorData, Attack, Trait, Spell, etc. (NEW)
├── spell_cache.py              # SpellCache wrapper around items.fetch (NEW)
├── converter.py                # ParsedActorData → FoundryVTT JSON (NEW)
└── __init__.py

src/foundry/
├── client.py                   # FoundryClient (EXISTING)
├── actors.py                   # ActorManager - update to use new converter (EXISTING)
├── items/                      # Item fetching (EXISTING)
│   ├── fetch.py
│   ├── manager.py
│   └── __init__.py
└── __init__.py
```

**Rationale**:
- `src/actors/models.py`: Source of truth for stat block extraction (domain: D&D rules)
- `src/foundry/actors/models.py`: FoundryVTT-specific structured data (domain: FoundryVTT API)
- Clear separation: extraction (actors) vs. export (foundry)

---

## Task Breakdown

### Task 1: Update StatBlock Model
**File**: `src/actors/models.py`
**Estimated Time**: 15 minutes
**Dependencies**: None

**Changes**:
1. Add `reactions` field to StatBlock:
   ```python
   reactions: Optional[str] = None  # REACTIONS section (if present)
   ```

**Verification**:
- [ ] Existing tests pass: `pytest tests/actors/test_models.py`
- [ ] Can create StatBlock with reactions field
- [ ] Reactions field is optional (defaults to None)

**Code**:
```python
# In src/actors/models.py, add after line 28:
reactions: Optional[str] = None  # REACTIONS section (if present)
```

---

### Task 2: Create ParsedActorData Models
**File**: `src/foundry/actors/models.py` (NEW)
**Estimated Time**: 2 hours
**Dependencies**: Task 1 (StatBlock updates)

**Models to Create**:

#### 2.1: DamageFormula
```python
"""Foundry-specific actor models for detailed parsing."""

from typing import List, Optional, Literal, Dict
from pydantic import BaseModel, Field


class DamageFormula(BaseModel):
    """Dice damage formula (FoundryVTT format)."""
    number: int  # Dice count (e.g., 3 for 3d6)
    denomination: int  # Dice size (e.g., 6 for d6)
    bonus: str = ""  # Flat modifier (e.g., "+2")
    type: str  # Damage type: "piercing", "slashing", "fire", etc.

    class Config:
        frozen = True  # Immutable
```

#### 2.2: Attack
```python
class Attack(BaseModel):
    """Parsed attack (weapon or spell attack)."""
    name: str
    attack_type: Literal["melee", "ranged", "melee_ranged"]
    attack_bonus: int  # To-hit bonus
    reach: Optional[int] = None  # Melee reach in feet (5, 10, 15, etc.)
    range_short: Optional[int] = None  # Ranged short range
    range_long: Optional[int] = None  # Ranged long range
    damage: List[DamageFormula]  # Primary + additional damage
    additional_effects: Optional[str] = None  # e.g., "target is grappled (escape DC 16)"
```

#### 2.3: SavingThrow
```python
class SavingThrow(BaseModel):
    """Saving throw triggered by ability."""
    ability: Literal["str", "dex", "con", "int", "wis", "cha"]
    dc: Optional[int] = None  # Explicit DC if specified
    dc_ability: Optional[str] = None  # Ability for DC calculation (e.g., "cha")
    on_failure: str  # Effect description on failure
    on_success: Optional[str] = None  # Effect on success (if specified)
```

#### 2.4: Trait
```python
class Trait(BaseModel):
    """Parsed trait/feature."""
    name: str
    description: str
    activation: Literal["action", "bonus", "reaction", "passive"] = "passive"
    uses: Optional[int] = None  # Limited uses per day/rest
    recharge: Optional[str] = None  # e.g., "5-6" for recharge on 5 or 6
    saving_throw: Optional[SavingThrow] = None
```

#### 2.5: Spell
```python
class Spell(BaseModel):
    """Parsed spell reference with compendium UUID."""
    name: str
    level: int  # 0-9
    uuid: Optional[str] = None  # Compendium UUID (resolved during parsing)
    school: Optional[str] = None  # "evo", "abj", etc.
    casting_time: Optional[str] = None
```

#### 2.6: SkillProficiency
```python
class SkillProficiency(BaseModel):
    """Skill proficiency entry."""
    skill: str  # "Stealth", "Perception", etc.
    bonus: int  # Total bonus (ability mod + proficiency)
    proficiency_level: Literal[0, 1, 2] = 1  # 0=none, 1=proficient, 2=expertise
```

#### 2.7: DamageModification
```python
class DamageModification(BaseModel):
    """Damage resistance/immunity/vulnerability."""
    types: List[str]  # ["fire", "poison"]
    condition: Optional[str] = None  # "from nonmagical attacks"
```

#### 2.8: ParsedActorData (Main Model)
```python
class ParsedActorData(BaseModel):
    """Fully parsed stat block ready for FoundryVTT conversion."""

    # Reference to source (for debugging)
    source_statblock_name: str  # Just the name, not full object

    # Core stats (copied from StatBlock)
    name: str
    armor_class: int
    hit_points: int
    hit_dice: Optional[str] = None  # e.g., "27d10 + 189"
    challenge_rating: float

    # Creature type
    size: Optional[str] = None  # "Small", "Medium", "Large", etc.
    creature_type: Optional[str] = None  # "humanoid", "fiend", etc.
    creature_subtype: Optional[str] = None  # "goblinoid", "devil", etc.
    alignment: Optional[str] = None

    # Abilities
    abilities: Dict[str, int]  # STR, DEX, CON, INT, WIS, CHA (required)
    saving_throw_proficiencies: List[str] = []  # ["dex", "wis"]

    # Skills
    skill_proficiencies: List[SkillProficiency] = []

    # Defenses
    damage_resistances: Optional[DamageModification] = None
    damage_immunities: Optional[DamageModification] = None
    damage_vulnerabilities: Optional[DamageModification] = None
    condition_immunities: List[str] = []  # ["poisoned", "charmed"]

    # Movement
    speed_walk: int = 30  # Default 30 ft
    speed_fly: Optional[int] = None
    speed_swim: Optional[int] = None
    speed_burrow: Optional[int] = None
    speed_climb: Optional[int] = None
    speed_hover: bool = False

    # Senses
    darkvision: Optional[int] = None  # Distance in feet
    blindsight: Optional[int] = None
    tremorsense: Optional[int] = None
    truesight: Optional[int] = None
    passive_perception: Optional[int] = None

    # Languages
    languages: List[str] = []  # ["Common", "Goblin"]
    telepathy: Optional[int] = None  # Range in feet

    # Abilities
    traits: List[Trait] = []
    attacks: List[Attack] = []
    reactions: List[Trait] = []  # Reactions use Trait model with activation="reaction"

    # Multiattack
    multiattack_description: Optional[str] = None  # Text description

    # Spellcasting
    spells: List[Spell] = []  # Each spell has UUID pre-resolved
    spellcasting_ability: Optional[Literal["int", "wis", "cha"]] = None
    spell_save_dc: Optional[int] = None
    spell_attack_bonus: Optional[int] = None
```

**Verification**:
- [ ] All models import successfully
- [ ] Can create instances with test data
- [ ] Pydantic validation works (invalid data raises error)
- [ ] Test with Goblin example from fixtures

**Test File**: `tests/foundry/actors/test_models.py`

```python
"""Tests for foundry.actors.models."""

import pytest
from foundry.actors.models import (
    DamageFormula, Attack, Trait, Spell, SkillProficiency,
    DamageModification, ParsedActorData
)


class TestDamageFormula:
    """Tests for DamageFormula model."""

    def test_basic_creation(self):
        """Should create damage formula with required fields."""
        formula = DamageFormula(
            number=1,
            denomination=6,
            bonus="+2",
            type="piercing"
        )

        assert formula.number == 1
        assert formula.denomination == 6
        assert formula.bonus == "+2"
        assert formula.type == "piercing"

    def test_immutable(self):
        """Should be immutable (frozen)."""
        formula = DamageFormula(number=1, denomination=6, type="slashing")

        with pytest.raises(Exception):  # Pydantic raises ValidationError
            formula.number = 2


class TestAttack:
    """Tests for Attack model."""

    def test_melee_attack(self):
        """Should create melee attack."""
        attack = Attack(
            name="Scimitar",
            attack_type="melee",
            attack_bonus=4,
            reach=5,
            damage=[
                DamageFormula(number=1, denomination=6, bonus="+2", type="slashing")
            ]
        )

        assert attack.name == "Scimitar"
        assert attack.attack_type == "melee"
        assert attack.reach == 5
        assert len(attack.damage) == 1

    def test_ranged_attack(self):
        """Should create ranged attack."""
        attack = Attack(
            name="Shortbow",
            attack_type="ranged",
            attack_bonus=4,
            range_short=80,
            range_long=320,
            damage=[
                DamageFormula(number=1, denomination=6, bonus="+2", type="piercing")
            ]
        )

        assert attack.range_short == 80
        assert attack.range_long == 320


class TestParsedActorData:
    """Tests for ParsedActorData model."""

    def test_minimal_goblin(self):
        """Should create minimal goblin data."""
        goblin = ParsedActorData(
            source_statblock_name="Goblin",
            name="Goblin",
            armor_class=15,
            hit_points=7,
            challenge_rating=0.25,
            abilities={
                "STR": 8,
                "DEX": 14,
                "CON": 10,
                "INT": 10,
                "WIS": 8,
                "CHA": 8
            }
        )

        assert goblin.name == "Goblin"
        assert goblin.armor_class == 15
        assert goblin.abilities["DEX"] == 14

    def test_with_attacks_and_traits(self):
        """Should create goblin with attacks and traits."""
        goblin = ParsedActorData(
            source_statblock_name="Goblin",
            name="Goblin",
            armor_class=15,
            hit_points=7,
            challenge_rating=0.25,
            abilities={"STR": 8, "DEX": 14, "CON": 10, "INT": 10, "WIS": 8, "CHA": 8},
            attacks=[
                Attack(
                    name="Scimitar",
                    attack_type="melee",
                    attack_bonus=4,
                    reach=5,
                    damage=[DamageFormula(number=1, denomination=6, bonus="+2", type="slashing")]
                )
            ],
            traits=[
                Trait(
                    name="Nimble Escape",
                    description="The goblin can take the Disengage or Hide action as a bonus action.",
                    activation="bonus"
                )
            ]
        )

        assert len(goblin.attacks) == 1
        assert len(goblin.traits) == 1
        assert goblin.traits[0].activation == "bonus"
```

---

### Task 3: Create SpellCache
**File**: `src/foundry/actors/spell_cache.py` (NEW)
**Estimated Time**: 1 hour
**Dependencies**: Task 2

**Implementation**:

```python
"""Spell cache for actor parsing - wraps foundry.items.fetch."""

from typing import Optional, Dict
from foundry.items.fetch import fetch_all_spells
import logging

logger = logging.getLogger(__name__)


STANDARD_WEAPONS = {
    # Simple Melee
    "club": "club",
    "dagger": "dagger",
    "greatclub": "greatclub",
    "handaxe": "handaxe",
    "javelin": "javelin",
    "light hammer": "lighthammer",
    "mace": "mace",
    "quarterstaff": "quarterstaff",
    "sickle": "sickle",
    "spear": "spear",

    # Simple Ranged
    "light crossbow": "lightcrossbow",
    "dart": "dart",
    "shortbow": "shortbow",
    "sling": "sling",

    # Martial Melee
    "battleaxe": "battleaxe",
    "flail": "flail",
    "glaive": "glaive",
    "greataxe": "greataxe",
    "greatsword": "greatsword",
    "halberd": "halberd",
    "lance": "lance",
    "longsword": "longsword",
    "maul": "maul",
    "morningstar": "morningstar",
    "pike": "pike",
    "rapier": "rapier",
    "scimitar": "scimitar",
    "shortsword": "shortsword",
    "trident": "trident",
    "war pick": "warpick",
    "warhammer": "warhammer",
    "whip": "whip",

    # Martial Ranged
    "blowgun": "blowgun",
    "hand crossbow": "handcrossbow",
    "heavy crossbow": "heavycrossbow",
    "longbow": "longbow",
    "net": "net"
}


class SpellCache:
    """Cache of spell name → UUID mappings for actor conversion."""

    def __init__(self, relay_url: str, api_key: str, client_id: str):
        """
        Initialize spell cache.

        Args:
            relay_url: Relay server URL
            api_key: API key for authentication
            client_id: Client ID for FoundryVTT instance
        """
        self.relay_url = relay_url
        self.api_key = api_key
        self.client_id = client_id
        self._cache: Dict[str, str] = {}  # Lowercase name → UUID
        self._loaded = False

    def load(self):
        """
        Load all spells from FoundryVTT compendiums.

        Fetches spells using alphabet queries (a-z) to bypass 200-result limit.
        Caches results in memory for fast lookups.

        Should be called once at start of actor processing session.
        """
        if self._loaded:
            logger.debug("Spell cache already loaded")
            return

        logger.info("Loading spell cache from FoundryVTT...")

        try:
            spells = fetch_all_spells(
                relay_url=self.relay_url,
                api_key=self.api_key,
                client_id=self.client_id,
                use_two_letter_fallback=True
            )

            for spell in spells:
                name_lower = spell['name'].lower()
                self._cache[name_lower] = spell['uuid']

            self._loaded = True
            logger.info(f"✓ Loaded {len(self._cache)} spells into cache")

        except Exception as e:
            logger.error(f"Failed to load spell cache: {e}")
            raise RuntimeError(f"Failed to load spell cache: {e}") from e

    def find_spell_uuid(self, spell_name: str) -> Optional[str]:
        """
        Find spell UUID by name (case-insensitive).

        Args:
            spell_name: Spell name (e.g., "Fireball", "hold monster")

        Returns:
            Compendium UUID or None if not found

        Raises:
            RuntimeError: If cache not loaded
        """
        if not self._loaded:
            raise RuntimeError("Spell cache not loaded - call load() first")

        uuid = self._cache.get(spell_name.lower())

        if uuid:
            logger.debug(f"Found spell '{spell_name}' → {uuid}")
        else:
            logger.debug(f"Spell '{spell_name}' not found in cache")

        return uuid

    def get_weapon_base_item(self, weapon_name: str) -> Optional[str]:
        """
        Get base item identifier for standard weapons.

        Args:
            weapon_name: Weapon name (e.g., "Dagger", "Longsword")

        Returns:
            Base item identifier (e.g., "dagger", "longsword")
            or None if not a standard weapon
        """
        return STANDARD_WEAPONS.get(weapon_name.lower())

    def __len__(self) -> int:
        """Return number of cached spells."""
        return len(self._cache)
```

**Verification**:
- [ ] Can create SpellCache instance
- [ ] load() fetches spells successfully
- [ ] find_spell_uuid() returns correct UUID for known spells
- [ ] find_spell_uuid() returns None for unknown spells
- [ ] get_weapon_base_item() returns correct identifiers

**Test File**: `tests/foundry/actors/test_spell_cache.py`

```python
"""Tests for foundry.actors.spell_cache."""

import pytest
from unittest.mock import patch, MagicMock
from foundry.actors.spell_cache import SpellCache, STANDARD_WEAPONS


class TestSpellCache:
    """Tests for SpellCache class."""

    @patch('foundry.actors.spell_cache.fetch_all_spells')
    def test_load(self, mock_fetch):
        """Should load spells and cache by lowercase name."""
        mock_fetch.return_value = [
            {'name': 'Fireball', 'uuid': 'Compendium.dnd5e.spells.abc'},
            {'name': 'Hold Monster', 'uuid': 'Compendium.dnd5e.spells.def'}
        ]

        cache = SpellCache('http://test', 'key', 'client')
        cache.load()

        assert len(cache) == 2
        assert cache.find_spell_uuid('Fireball') == 'Compendium.dnd5e.spells.abc'
        assert cache.find_spell_uuid('fireball') == 'Compendium.dnd5e.spells.abc'  # Case-insensitive

    @patch('foundry.actors.spell_cache.fetch_all_spells')
    def test_find_spell_not_found(self, mock_fetch):
        """Should return None for unknown spells."""
        mock_fetch.return_value = []

        cache = SpellCache('http://test', 'key', 'client')
        cache.load()

        assert cache.find_spell_uuid('Homebrew Spell') is None

    def test_get_weapon_base_item(self):
        """Should return base item for standard weapons."""
        cache = SpellCache('http://test', 'key', 'client')

        assert cache.get_weapon_base_item('Dagger') == 'dagger'
        assert cache.get_weapon_base_item('longsword') == 'longsword'  # Case-insensitive
        assert cache.get_weapon_base_item('Bite') is None  # Natural weapon


@pytest.mark.integration
class TestSpellCacheIntegration:
    """Integration tests with real FoundryVTT."""

    def test_load_real_spells(self, check_api_key):
        """Load real spells from FoundryVTT (requires running server)."""
        import os

        if not os.getenv('FOUNDRY_RELAY_URL'):
            pytest.skip("FOUNDRY_RELAY_URL not configured")

        cache = SpellCache(
            os.getenv('FOUNDRY_RELAY_URL'),
            os.getenv('FOUNDRY_API_KEY'),
            os.getenv('FOUNDRY_CLIENT_ID')
        )
        cache.load()

        assert len(cache) > 100  # Should have many spells
        assert cache.find_spell_uuid('Fireball') is not None
        assert cache.find_spell_uuid('Hold Monster') is not None
```

---

### Task 4: Create Converter Stub
**File**: `src/foundry/actors/converter.py` (NEW)
**Estimated Time**: 30 minutes
**Dependencies**: Tasks 2, 3

**Purpose**: Stub file for FoundryVTT conversion (detailed implementation in Phase 2)

```python
"""Convert ParsedActorData to FoundryVTT actor JSON."""

from typing import Dict, Any
from .models import ParsedActorData
from .spell_cache import SpellCache
import logging

logger = logging.getLogger(__name__)


def parsed_to_foundry(
    data: ParsedActorData,
    spell_cache: SpellCache
) -> Dict[str, Any]:
    """
    Convert ParsedActorData to FoundryVTT actor JSON.

    Args:
        data: Parsed actor data
        spell_cache: Spell cache (for weapon baseItem lookups)

    Returns:
        FoundryVTT actor JSON structure

    Note:
        Full implementation in Phase 2. This stub returns minimal structure.
    """
    logger.warning("Using stub converter - full implementation pending")

    return {
        "name": data.name,
        "type": "npc",
        "system": {
            "abilities": {
                ability.lower(): {"value": value}
                for ability, value in data.abilities.items()
            },
            "attributes": {
                "ac": {"value": data.armor_class},
                "hp": {"value": data.hit_points, "max": data.hit_points}
            },
            "details": {
                "cr": data.challenge_rating,
                "biography": {
                    "value": f"<p>From stat block: {data.source_statblock_name}</p>"
                }
            }
        },
        "items": []  # TODO: Phase 2 - convert attacks, traits, spells to items
    }
```

**Verification**:
- [ ] Can import converter
- [ ] parsed_to_foundry() returns valid structure
- [ ] Logs warning about stub implementation

---

### Task 5: Update __init__.py Files
**File**: `src/foundry/actors/__init__.py` (NEW)
**Estimated Time**: 10 minutes
**Dependencies**: Tasks 2, 3, 4

```python
"""FoundryVTT actor models and conversion."""

from .models import (
    DamageFormula,
    Attack,
    SavingThrow,
    Trait,
    Spell,
    SkillProficiency,
    DamageModification,
    ParsedActorData
)
from .spell_cache import SpellCache
from .converter import parsed_to_foundry

__all__ = [
    "DamageFormula",
    "Attack",
    "SavingThrow",
    "Trait",
    "Spell",
    "SkillProficiency",
    "DamageModification",
    "ParsedActorData",
    "SpellCache",
    "parsed_to_foundry"
]
```

**File**: `src/actors/__init__.py` (UPDATE)

Add import for updated StatBlock:
```python
from .models import StatBlock, NPC
from .extract_stat_blocks import extract_and_parse_stat_blocks
from .extract_npcs import identify_npcs_with_gemini
from .parse_stat_blocks import parse_stat_block_with_gemini

__all__ = [
    "StatBlock",
    "NPC",
    "extract_and_parse_stat_blocks",
    "identify_npcs_with_gemini",
    "parse_stat_block_with_gemini"
]
```

---

### Task 6: Create Test Fixtures
**Directory**: `tests/foundry/actors/fixtures/` (NEW)
**Estimated Time**: 30 minutes
**Dependencies**: Task 2

**Files to Create**:

1. `tests/foundry/actors/fixtures/parsed_goblin.json`:
```json
{
  "source_statblock_name": "Goblin",
  "name": "Goblin",
  "armor_class": 15,
  "hit_points": 7,
  "hit_dice": "2d6",
  "challenge_rating": 0.25,
  "size": "Small",
  "creature_type": "humanoid",
  "creature_subtype": "goblinoid",
  "alignment": "neutral evil",
  "abilities": {
    "STR": 8,
    "DEX": 14,
    "CON": 10,
    "INT": 10,
    "WIS": 8,
    "CHA": 8
  },
  "skill_proficiencies": [
    {
      "skill": "Stealth",
      "bonus": 6,
      "proficiency_level": 2
    }
  ],
  "speed_walk": 30,
  "darkvision": 60,
  "passive_perception": 9,
  "languages": ["Common", "Goblin"],
  "traits": [
    {
      "name": "Nimble Escape",
      "description": "The goblin can take the Disengage or Hide action as a bonus action on each of its turns.",
      "activation": "bonus"
    }
  ],
  "attacks": [
    {
      "name": "Scimitar",
      "attack_type": "melee",
      "attack_bonus": 4,
      "reach": 5,
      "damage": [
        {
          "number": 1,
          "denomination": 6,
          "bonus": "+2",
          "type": "slashing"
        }
      ]
    },
    {
      "name": "Shortbow",
      "attack_type": "ranged",
      "attack_bonus": 4,
      "range_short": 80,
      "range_long": 320,
      "damage": [
        {
          "number": 1,
          "denomination": 6,
          "bonus": "+2",
          "type": "piercing"
        }
      ]
    }
  ]
}
```

2. `tests/foundry/actors/__init__.py` (empty)
3. `tests/foundry/actors/fixtures/__init__.py` (empty)

---

### Task 7: Documentation Updates
**Files**: `docs/*.md`, `CLAUDE.md`
**Estimated Time**: 30 minutes
**Dependencies**: All previous tasks

**Updates**:

1. Update `CLAUDE.md` with new file structure:
```markdown
## Actor Processing Architecture

### File Structure
- `src/actors/models.py`: StatBlock extraction models
- `src/foundry/actors/models.py`: ParsedActorData for FoundryVTT conversion
- `src/foundry/actors/spell_cache.py`: Spell compendium cache
- `src/foundry/actors/converter.py`: FoundryVTT JSON conversion

### Data Flow
```
PDF → StatBlock → ParsedActorData → FoundryVTT JSON
```
```

2. Add to `docs/actor_parsing_architecture.md`:
```markdown
## Implementation Status

✅ **Phase 1 Complete** (Data Structures)
- StatBlock updated with reactions field
- ParsedActorData models created
- SpellCache implemented
- Test fixtures added

⏳ **Phase 2 Pending** (Detailed Parsing)
- Gemini prompt for parsing attacks/traits
- parse_detailed.py implementation
- Full converter implementation
```

---

## Testing Strategy

### Unit Tests (pytest -m "not integration")
- [ ] All model instantiation tests pass
- [ ] Validation tests (invalid data raises errors)
- [ ] SpellCache mocked tests pass
- [ ] Converter stub tests pass

### Integration Tests (pytest -m integration)
- [ ] SpellCache loads real spells from FoundryVTT
- [ ] Spell UUID lookup works for known spells

### Manual Verification
- [ ] Create ParsedActorData from Goblin fixture JSON
- [ ] Convert to FoundryVTT JSON (stub converter)
- [ ] Validate JSON structure matches expected format

---

## Success Criteria

### Phase 1 Complete When:
1. ✅ All files created and importable
2. ✅ All unit tests pass
3. ✅ Can create ParsedActorData instances programmatically
4. ✅ Can load test fixtures into models
5. ✅ SpellCache loads and caches spells
6. ✅ Stub converter produces valid (minimal) FoundryVTT JSON
7. ✅ Documentation updated

---

## Estimated Total Time

- Task 1: 15 min
- Task 2: 2 hours
- Task 3: 1 hour
- Task 4: 30 min
- Task 5: 10 min
- Task 6: 30 min
- Task 7: 30 min

**Total: ~5 hours**

---

## Next Steps (Phase 2)

After Phase 1 complete:
1. Design Gemini prompt for detailed parsing
2. Implement `parse_detailed.py`
3. Implement full converter with Items
4. Test with complex stat blocks (Pit Fiend)
5. Integration with actor processing pipeline

# Actor Parsing Enhancements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add parsing for multiattack, innate spellcasting, and limited-use traits to achieve feature parity with official FoundryVTT actor exports.

**Architecture:** Extend ParsedActorData model and converter to handle special trait types. Add text parsing utilities to extract structured data from free-form stat block text. Integrate SpellCache for proper spell UUID resolution.

**Tech Stack:** Pydantic models, Python regex, existing SpellCache infrastructure

**Current Status:** Basic actor upload/download works (26/26 tests passing). Pit Fiend test shows 58% item coverage (7/12 items). Missing: multiattack feats, innate spells, limited-use traits.

---

## Task 1: Add Multiattack Model and Parsing

**Goal:** Parse "Multiattack" action sections and create feat items for them.

**Files:**
- Modify: `src/foundry/actors/models.py` (add multiattack field)
- Modify: `src/foundry/actors/converter.py` (convert multiattack to feat)
- Create: `tests/foundry/actors/test_multiattack.py` (test multiattack parsing)

### Step 1: Write failing test for multiattack in ParsedActorData

**File:** `tests/foundry/actors/test_multiattack.py`

```python
"""Tests for multiattack parsing."""

import pytest
from foundry.actors.models import ParsedActorData, Multiattack


class TestMultiattackModel:
    """Tests for Multiattack model."""

    def test_basic_multiattack(self):
        """Should create basic multiattack."""
        multiattack = Multiattack(
            name="Multiattack",
            description="The pit fiend makes four attacks: one with its bite, one with its claw, one with its mace, and one with its tail.",
            num_attacks=4
        )

        assert multiattack.name == "Multiattack"
        assert multiattack.num_attacks == 4
        assert "four attacks" in multiattack.description

    def test_multiattack_with_options(self):
        """Should handle multiattack with options."""
        multiattack = Multiattack(
            name="Multiattack",
            description="The dragon can use its Frightful Presence. It then makes three attacks: one with its bite and two with its claws.",
            num_attacks=3
        )

        assert multiattack.num_attacks == 3

    def test_parsed_actor_with_multiattack(self):
        """Should include multiattack in ParsedActorData."""
        actor = ParsedActorData(
            source_statblock_name="Pit Fiend",
            name="Pit Fiend",
            armor_class=19,
            hit_points=300,
            challenge_rating=20,
            abilities={"STR": 26, "DEX": 14, "CON": 24, "INT": 22, "WIS": 18, "CHA": 24},
            multiattack=Multiattack(
                name="Multiattack",
                description="Makes four attacks.",
                num_attacks=4
            )
        )

        assert actor.multiattack is not None
        assert actor.multiattack.num_attacks == 4
```

### Step 2: Run test to verify it fails

```bash
uv run pytest tests/foundry/actors/test_multiattack.py -v
```

**Expected:** FAIL - `Multiattack` not defined, `multiattack` field doesn't exist

### Step 3: Add Multiattack model to models.py

**File:** `src/foundry/actors/models.py`

Add after `Trait` class definition:

```python
class Multiattack(BaseModel):
    """Multiattack action."""

    name: str = "Multiattack"
    description: str
    num_attacks: Optional[int] = None
    activation: Literal["action", "bonus", "reaction", "passive"] = "action"

    model_config = ConfigDict(frozen=True)
```

Then modify `ParsedActorData` class to add:

```python
class ParsedActorData(BaseModel):
    # ... existing fields ...

    multiattack: Optional[Multiattack] = None  # Add after traits field
```

### Step 4: Run test to verify it passes

```bash
uv run pytest tests/foundry/actors/test_multiattack.py::TestMultiattackModel -v
```

**Expected:** PASS (3 tests)

### Step 5: Write failing test for multiattack conversion

**File:** `tests/foundry/actors/test_multiattack.py`

Add to same file:

```python
from foundry.actors.converter import convert_to_foundry


class TestMultiattackConversion:
    """Tests for converting multiattack to FoundryVTT format."""

    def test_converts_multiattack_to_feat(self):
        """Should convert multiattack to feat item."""
        actor = ParsedActorData(
            source_statblock_name="Test",
            name="Test Creature",
            armor_class=15,
            hit_points=100,
            challenge_rating=5,
            abilities={"STR": 18, "DEX": 14, "CON": 16, "INT": 10, "WIS": 12, "CHA": 10},
            multiattack=Multiattack(
                name="Multiattack",
                description="The creature makes two attacks: one with its bite and one with its claws.",
                num_attacks=2
            )
        )

        result = convert_to_foundry(actor)

        # Should have multiattack feat in items
        feats = [item for item in result["items"] if item["type"] == "feat"]
        multiattack_feat = next((f for f in feats if f["name"] == "Multiattack"), None)

        assert multiattack_feat is not None
        assert multiattack_feat["system"]["activation"]["type"] == "action"
        assert "two attacks" in multiattack_feat["system"]["description"]["value"]
```

### Step 6: Run test to verify it fails

```bash
uv run pytest tests/foundry/actors/test_multiattack.py::TestMultiattackConversion::test_converts_multiattack_to_feat -v
```

**Expected:** FAIL - multiattack_feat is None

### Step 7: Add multiattack conversion to converter.py

**File:** `src/foundry/actors/converter.py`

In `convert_to_foundry()` function, add after the traits conversion loop (around line 155):

```python
    # Convert multiattack to feat item
    if parsed_actor.multiattack:
        item = {
            "name": parsed_actor.multiattack.name,
            "type": "feat",
            "img": "icons/magic/movement/trail-streak-zigzag-yellow.webp",
            "system": {
                "description": {"value": parsed_actor.multiattack.description},
                "activation": {"type": parsed_actor.multiattack.activation},
                "uses": {}
            }
        }
        items.append(item)
```

### Step 8: Run test to verify it passes

```bash
uv run pytest tests/foundry/actors/test_multiattack.py::TestMultiattackConversion -v
```

**Expected:** PASS

### Step 9: Run all actor tests

```bash
uv run pytest tests/foundry/actors/ -v
```

**Expected:** All tests pass (should be 29 now: 26 + 3 new)

### Step 10: Commit multiattack feature

```bash
git add src/foundry/actors/models.py src/foundry/actors/converter.py tests/foundry/actors/test_multiattack.py
git commit -m "feat: add multiattack parsing and conversion to feat items"
```

---

## Task 2: Add Innate Spellcasting Model

**Goal:** Model innate spellcasting data structure before parsing.

**Files:**
- Modify: `src/foundry/actors/models.py` (add InnateSpellcasting)
- Create: `tests/foundry/actors/test_innate_spellcasting.py`

### Step 1: Write failing test for InnateSpellcasting model

**File:** `tests/foundry/actors/test_innate_spellcasting.py`

```python
"""Tests for innate spellcasting."""

import pytest
from foundry.actors.models import ParsedActorData, InnateSpellcasting, InnateSpell


class TestInnateSpellcastingModel:
    """Tests for innate spellcasting models."""

    def test_innate_spell(self):
        """Should create innate spell."""
        spell = InnateSpell(
            name="Fireball",
            frequency="at will"
        )

        assert spell.name == "Fireball"
        assert spell.frequency == "at will"
        assert spell.uses is None

    def test_innate_spell_with_uses(self):
        """Should handle limited-use spells."""
        spell = InnateSpell(
            name="Hold Monster",
            frequency="3/day",
            uses=3
        )

        assert spell.frequency == "3/day"
        assert spell.uses == 3

    def test_innate_spellcasting(self):
        """Should group spells by frequency."""
        innate = InnateSpellcasting(
            ability="charisma",
            save_dc=21,
            spells=[
                InnateSpell(name="Detect Magic", frequency="at will"),
                InnateSpell(name="Fireball", frequency="at will"),
                InnateSpell(name="Hold Monster", frequency="3/day", uses=3),
                InnateSpell(name="Wall of Fire", frequency="3/day", uses=3),
            ]
        )

        assert innate.ability == "charisma"
        assert innate.save_dc == 21
        assert len(innate.spells) == 4

    def test_parsed_actor_with_innate_spellcasting(self):
        """Should include innate spellcasting in ParsedActorData."""
        actor = ParsedActorData(
            source_statblock_name="Pit Fiend",
            name="Pit Fiend",
            armor_class=19,
            hit_points=300,
            challenge_rating=20,
            abilities={"STR": 26, "DEX": 14, "CON": 24, "INT": 22, "WIS": 18, "CHA": 24},
            innate_spellcasting=InnateSpellcasting(
                ability="charisma",
                save_dc=21,
                spells=[
                    InnateSpell(name="Fireball", frequency="at will"),
                ]
            )
        )

        assert actor.innate_spellcasting is not None
        assert len(actor.innate_spellcasting.spells) == 1
```

### Step 2: Run test to verify it fails

```bash
uv run pytest tests/foundry/actors/test_innate_spellcasting.py -v
```

**Expected:** FAIL - models not defined

### Step 3: Add InnateSpellcasting models to models.py

**File:** `src/foundry/actors/models.py`

Add after `Spell` class:

```python
class InnateSpell(BaseModel):
    """An innate spell with usage frequency."""

    name: str
    frequency: str  # "at will", "3/day", "1/day", etc.
    uses: Optional[int] = None  # Max uses per day

    model_config = ConfigDict(frozen=True)


class InnateSpellcasting(BaseModel):
    """Innate spellcasting ability."""

    ability: str  # "charisma", "intelligence", etc.
    save_dc: Optional[int] = None
    attack_bonus: Optional[int] = None
    spells: List[InnateSpell] = Field(default_factory=list)

    model_config = ConfigDict(frozen=True)
```

Then add to `ParsedActorData`:

```python
class ParsedActorData(BaseModel):
    # ... existing fields ...

    innate_spellcasting: Optional[InnateSpellcasting] = None  # Add after spells field
```

### Step 4: Run test to verify it passes

```bash
uv run pytest tests/foundry/actors/test_innate_spellcasting.py::TestInnateSpellcastingModel -v
```

**Expected:** PASS (4 tests)

### Step 5: Commit innate spellcasting models

```bash
git add src/foundry/actors/models.py tests/foundry/actors/test_innate_spellcasting.py
git commit -m "feat: add innate spellcasting data models"
```

---

## Task 3: Convert Innate Spellcasting to FoundryVTT Format

**Goal:** Convert innate spellcasting to feat + spell items with proper UUIDs.

**Files:**
- Modify: `src/foundry/actors/converter.py` (add innate spellcasting conversion)
- Modify: `tests/foundry/actors/test_innate_spellcasting.py` (add conversion tests)

### Step 1: Write failing test for innate spellcasting conversion

**File:** `tests/foundry/actors/test_innate_spellcasting.py`

Add to existing file:

```python
from foundry.actors.converter import convert_to_foundry


class TestInnateSpellcastingConversion:
    """Tests for converting innate spellcasting to FoundryVTT format."""

    def test_converts_innate_spellcasting_to_feat(self):
        """Should create Innate Spellcasting feat."""
        actor = ParsedActorData(
            source_statblock_name="Pit Fiend",
            name="Pit Fiend",
            armor_class=19,
            hit_points=300,
            challenge_rating=20,
            abilities={"STR": 26, "DEX": 14, "CON": 24, "INT": 22, "WIS": 18, "CHA": 24},
            innate_spellcasting=InnateSpellcasting(
                ability="charisma",
                save_dc=21,
                spells=[
                    InnateSpell(name="Detect Magic", frequency="at will"),
                    InnateSpell(name="Fireball", frequency="at will"),
                ]
            )
        )

        result = convert_to_foundry(actor)

        # Should have Innate Spellcasting feat
        feats = [item for item in result["items"] if item["type"] == "feat"]
        innate_feat = next((f for f in feats if "Innate Spellcasting" in f["name"]), None)

        assert innate_feat is not None
        assert "charisma" in innate_feat["system"]["description"]["value"].lower()

    def test_converts_innate_spells_to_spell_items(self):
        """Should create spell items for innate spells."""
        actor = ParsedActorData(
            source_statblock_name="Pit Fiend",
            name="Pit Fiend",
            armor_class=19,
            hit_points=300,
            challenge_rating=20,
            abilities={"STR": 26, "DEX": 14, "CON": 24, "INT": 22, "WIS": 18, "CHA": 24},
            innate_spellcasting=InnateSpellcasting(
                ability="charisma",
                save_dc=21,
                spells=[
                    InnateSpell(name="Fireball", frequency="at will"),
                    InnateSpell(name="Hold Monster", frequency="3/day", uses=3),
                ]
            )
        )

        result = convert_to_foundry(actor)

        # Should have spell items
        spells = [item for item in result["items"] if item["type"] == "spell"]

        assert len(spells) >= 2

        fireball = next((s for s in spells if s["name"] == "Fireball"), None)
        hold_monster = next((s for s in spells if s["name"] == "Hold Monster"), None)

        assert fireball is not None
        assert hold_monster is not None

        # Limited-use spell should have uses
        assert hold_monster["system"]["uses"]["max"] == 3
```

### Step 2: Run test to verify it fails

```bash
uv run pytest tests/foundry/actors/test_innate_spellcasting.py::TestInnateSpellcastingConversion -v
```

**Expected:** FAIL - innate_feat is None, spells not created

### Step 3: Add innate spellcasting conversion to converter.py

**File:** `src/foundry/actors/converter.py`

Add after the spells conversion loop (around line 170):

```python
    # Convert innate spellcasting to feat + spell items
    if parsed_actor.innate_spellcasting:
        innate = parsed_actor.innate_spellcasting

        # Build description from spell list
        spell_lines = []
        # Group by frequency
        by_frequency = {}
        for spell in innate.spells:
            if spell.frequency not in by_frequency:
                by_frequency[spell.frequency] = []
            by_frequency[spell.frequency].append(spell.name)

        for freq, spell_names in sorted(by_frequency.items()):
            spell_list = ", ".join(spell_names)
            spell_lines.append(f"{freq}: {spell_list}")

        description = (
            f"The {parsed_actor.name.lower()}'s spellcasting ability is "
            f"{innate.ability.capitalize()} (spell save DC {innate.save_dc or 10}). "
            f"It can innately cast the following spells, requiring no material components:\n\n"
            + "\n".join(spell_lines)
        )

        # Create Innate Spellcasting feat
        item = {
            "name": "Innate Spellcasting",
            "type": "feat",
            "img": "icons/magic/air/wind-tornado-wall-blue.webp",
            "system": {
                "description": {"value": description},
                "activation": {"type": "passive"},
                "uses": {}
            }
        }
        items.append(item)

        # Create spell items for each innate spell
        for spell in innate.spells:
            spell_item = {
                "name": spell.name,
                "type": "spell",
                "img": "icons/magic/air/wind-tornado-wall-blue.webp",
                "system": {
                    "level": 0,  # Will be looked up if SpellCache available
                    "school": ""
                }
            }

            # Add uses if limited
            if spell.uses:
                spell_item["system"]["uses"] = {
                    "value": spell.uses,
                    "max": spell.uses,
                    "per": "day"
                }

            items.append(spell_item)
```

### Step 4: Run test to verify it passes

```bash
uv run pytest tests/foundry/actors/test_innate_spellcasting.py::TestInnateSpellcastingConversion -v
```

**Expected:** PASS (2 tests)

### Step 5: Run all actor tests

```bash
uv run pytest tests/foundry/actors/ -v
```

**Expected:** All tests pass (should be 35 now: 29 + 6 new)

### Step 6: Commit innate spellcasting conversion

```bash
git add src/foundry/actors/converter.py tests/foundry/actors/test_innate_spellcasting.py
git commit -m "feat: convert innate spellcasting to feat and spell items"
```

---

## Task 4: Integrate SpellCache for Spell UUIDs

**Goal:** Use existing SpellCache to look up proper spell UUIDs from FoundryVTT compendium.

**Files:**
- Modify: `src/foundry/actors/converter.py` (integrate SpellCache)
- Modify: `tests/foundry/actors/test_innate_spellcasting.py` (test UUID lookup)

### Step 1: Write failing test for spell UUID lookup

**File:** `tests/foundry/actors/test_innate_spellcasting.py`

Add to TestInnateSpellcastingConversion class:

```python
    @pytest.mark.integration
    @pytest.mark.requires_foundry
    def test_looks_up_spell_uuids_from_cache(self):
        """Should use SpellCache to get proper spell UUIDs."""
        from foundry.actors.spell_cache import SpellCache
        from foundry.client import FoundryClient
        from dotenv import load_dotenv
        import os

        load_dotenv()

        # Skip if FoundryVTT not available
        if not os.getenv("FOUNDRY_RELAY_URL"):
            pytest.skip("FoundryVTT not configured")

        client = FoundryClient(target="local")
        spell_cache = SpellCache(client)
        spell_cache.load()

        actor = ParsedActorData(
            source_statblock_name="Pit Fiend",
            name="Pit Fiend",
            armor_class=19,
            hit_points=300,
            challenge_rating=20,
            abilities={"STR": 26, "DEX": 14, "CON": 24, "INT": 22, "WIS": 18, "CHA": 24},
            innate_spellcasting=InnateSpellcasting(
                ability="charisma",
                save_dc=21,
                spells=[
                    InnateSpell(name="Fireball", frequency="at will"),
                ]
            )
        )

        # Convert with spell cache
        result = convert_to_foundry(actor, spell_cache=spell_cache)

        spells = [item for item in result["items"] if item["type"] == "spell"]
        fireball = next((s for s in spells if s["name"] == "Fireball"), None)

        assert fireball is not None
        # Should have UUID from compendium
        assert "uuid" in fireball
        assert fireball["uuid"].startswith("Compendium.")
        # Should have proper level (Fireball is 3rd level)
        assert fireball["system"]["level"] == 3
```

### Step 2: Run test to verify it fails

```bash
uv run pytest tests/foundry/actors/test_innate_spellcasting.py::TestInnateSpellcastingConversion::test_looks_up_spell_uuids_from_cache -v
```

**Expected:** FAIL - `convert_to_foundry() got an unexpected keyword argument 'spell_cache'`

### Step 3: Add spell_cache parameter to convert_to_foundry

**File:** `src/foundry/actors/converter.py`

Modify function signature (around line 10):

```python
def convert_to_foundry(
    parsed_actor: ParsedActorData,
    spell_cache: Optional['SpellCache'] = None
) -> Dict[str, Any]:
```

Add import at top:

```python
from typing import Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .spell_cache import SpellCache
```

Then modify the innate spellcasting spell creation (in the loop):

```python
        # Create spell items for each innate spell
        for spell in innate.spells:
            spell_item = {
                "name": spell.name,
                "type": "spell",
                "img": "icons/magic/air/wind-tornado-wall-blue.webp",
                "system": {
                    "level": 0,
                    "school": ""
                }
            }

            # Look up UUID and details from spell cache if available
            if spell_cache:
                spell_uuid = spell_cache.get_spell_uuid(spell.name)
                if spell_uuid:
                    spell_item["uuid"] = spell_uuid

                    # Get spell details
                    spell_data = spell_cache.get_spell_data(spell.name)
                    if spell_data:
                        spell_item["system"]["level"] = spell_data.get("system", {}).get("level", 0)
                        spell_item["system"]["school"] = spell_data.get("system", {}).get("school", "")

            # Add uses if limited
            if spell.uses:
                spell_item["system"]["uses"] = {
                    "value": spell.uses,
                    "max": spell.uses,
                    "per": "day"
                }

            items.append(spell_item)
```

Also update the regular spells loop to use spell_cache:

```python
    # Convert spells to spell items (using UUIDs)
    for spell in parsed_actor.spells:
        item = {
            "name": spell.name,
            "type": "spell",
            "img": "icons/magic/air/wind-tornado-wall-blue.webp",
            "system": {
                "level": spell.level,
                "school": spell.school or ""
            }
        }

        # Prefer spell cache for UUID lookup
        if spell_cache:
            spell_uuid = spell_cache.get_spell_uuid(spell.name)
            if spell_uuid:
                item["uuid"] = spell_uuid
        elif spell.uuid:
            item["uuid"] = spell.uuid

        items.append(item)
```

### Step 4: Run integration test to verify it passes

```bash
uv run pytest tests/foundry/actors/test_innate_spellcasting.py::TestInnateSpellcastingConversion::test_looks_up_spell_uuids_from_cache -v -m integration
```

**Expected:** PASS (if FoundryVTT is running)

### Step 5: Run all actor tests

```bash
uv run pytest tests/foundry/actors/ -v -m "not integration"
```

**Expected:** All unit tests pass

### Step 6: Commit SpellCache integration

```bash
git add src/foundry/actors/converter.py tests/foundry/actors/test_innate_spellcasting.py
git commit -m "feat: integrate SpellCache for spell UUID lookups"
```

---

## Task 5: Update Pit Fiend Test with New Features

**Goal:** Verify the Pit Fiend now has all expected items.

**Files:**
- Create: `tests/foundry/actors/test_pit_fiend_integration.py`

### Step 1: Write integration test for complete Pit Fiend

**File:** `tests/foundry/actors/test_pit_fiend_integration.py`

```python
"""Integration test for Pit Fiend with all features."""

import pytest
from dotenv import load_dotenv
from pathlib import Path

from foundry.actors.models import (
    ParsedActorData, Attack, Trait, DamageFormula,
    Multiattack, InnateSpellcasting, InnateSpell
)
from foundry.actors.converter import convert_to_foundry
from foundry.client import FoundryClient
from foundry.actors.spell_cache import SpellCache

load_dotenv()


@pytest.mark.integration
@pytest.mark.requires_foundry
class TestPitFiendIntegration:
    """Full integration test for Pit Fiend."""

    @pytest.fixture
    def spell_cache(self):
        """Load spell cache."""
        client = FoundryClient(target="local")
        cache = SpellCache(client)
        cache.load()
        return cache

    @pytest.fixture
    def pit_fiend_data(self):
        """Complete Pit Fiend data."""
        return ParsedActorData(
            source_statblock_name="Pit Fiend",
            name="Pit Fiend",
            size="large",
            creature_type="fiend",
            creature_subtype="devil",
            alignment="lawful evil",
            armor_class=19,
            hit_points=300,
            hit_dice="24d10+168",
            speed_walk=30,
            speed_fly=60,
            challenge_rating=20,
            abilities={
                "STR": 26,
                "DEX": 14,
                "CON": 24,
                "INT": 22,
                "WIS": 18,
                "CHA": 24
            },
            saving_throw_proficiencies=["dex", "con", "wis"],
            condition_immunities=["poisoned"],
            truesight=120,
            languages=["Infernal", "Telepathy 120 ft."],
            multiattack=Multiattack(
                name="Multiattack",
                description="The pit fiend makes four attacks: one with its bite, one with its claw, one with its mace, and one with its tail.",
                num_attacks=4
            ),
            traits=[
                Trait(
                    name="Fear Aura",
                    description="Any creature hostile to the pit fiend that starts its turn within 20 feet must make a DC 21 Wisdom saving throw.",
                    activation="passive"
                ),
                Trait(
                    name="Magic Resistance",
                    description="The pit fiend has advantage on saving throws against spells and other magical effects.",
                    activation="passive"
                ),
                Trait(
                    name="Magic Weapons",
                    description="The pit fiend's weapon attacks are magical.",
                    activation="passive"
                ),
            ],
            innate_spellcasting=InnateSpellcasting(
                ability="charisma",
                save_dc=21,
                spells=[
                    InnateSpell(name="Detect Magic", frequency="at will"),
                    InnateSpell(name="Fireball", frequency="at will"),
                    InnateSpell(name="Hold Monster", frequency="3/day", uses=3),
                    InnateSpell(name="Wall of Fire", frequency="3/day", uses=3),
                ]
            ),
            attacks=[
                Attack(
                    name="Bite",
                    attack_type="melee",
                    attack_bonus=14,
                    reach=5,
                    damage=[
                        DamageFormula(number=4, denomination=6, bonus="+8", type="piercing")
                    ]
                ),
                Attack(
                    name="Claw",
                    attack_type="melee",
                    attack_bonus=14,
                    reach=10,
                    damage=[
                        DamageFormula(number=2, denomination=8, bonus="+8", type="slashing")
                    ]
                ),
                Attack(
                    name="Mace",
                    attack_type="melee",
                    attack_bonus=14,
                    reach=10,
                    damage=[
                        DamageFormula(number=2, denomination=6, bonus="+8", type="bludgeoning"),
                        DamageFormula(number=6, denomination=6, bonus="", type="fire")
                    ]
                ),
                Attack(
                    name="Tail",
                    attack_type="melee",
                    attack_bonus=14,
                    reach=10,
                    damage=[
                        DamageFormula(number=3, denomination=10, bonus="+8", type="bludgeoning")
                    ]
                ),
            ]
        )

    def test_pit_fiend_has_all_items(self, pit_fiend_data, spell_cache):
        """Pit Fiend should have 12+ items like official FoundryVTT."""
        result = convert_to_foundry(pit_fiend_data, spell_cache=spell_cache)

        items = result["items"]

        # Count by type
        weapons = [i for i in items if i["type"] == "weapon"]
        feats = [i for i in items if i["type"] == "feat"]
        spells = [i for i in items if i["type"] == "spell"]

        # Should have 4 weapons
        assert len(weapons) == 4
        assert any(w["name"] == "Bite" for w in weapons)
        assert any(w["name"] == "Claw" for w in weapons)
        assert any(w["name"] == "Mace" for w in weapons)
        assert any(w["name"] == "Tail" for w in weapons)

        # Should have 5 feats (3 traits + multiattack + innate spellcasting)
        assert len(feats) >= 5
        assert any(f["name"] == "Multiattack" for f in feats)
        assert any(f["name"] == "Fear Aura" for f in feats)
        assert any(f["name"] == "Magic Resistance" for f in feats)
        assert any(f["name"] == "Magic Weapons" for f in feats)
        assert any("Innate Spellcasting" in f["name"] for f in feats)

        # Should have 4 spells
        assert len(spells) == 4
        assert any(s["name"] == "Fireball" for s in spells)
        assert any(s["name"] == "Hold Monster" for s in spells)
        assert any(s["name"] == "Wall of Fire" for s in spells)
        assert any(s["name"] == "Detect Magic" for s in spells)

        # Total should be 13 items (4 weapons + 5 feats + 4 spells)
        assert len(items) == 13

        # Verify spell UUIDs were looked up
        fireball = next(s for s in spells if s["name"] == "Fireball")
        assert "uuid" in fireball
        assert fireball["uuid"].startswith("Compendium.")

    def test_pit_fiend_round_trip(self, pit_fiend_data, spell_cache):
        """Full upload/download round-trip with all features."""
        client = FoundryClient(target="local")

        # Convert and upload
        foundry_json = convert_to_foundry(pit_fiend_data, spell_cache=spell_cache)
        actor_uuid = client.actors.create_actor(foundry_json)

        # Download and verify
        downloaded = client.actors.get_actor(actor_uuid)

        assert downloaded["name"] == "Pit Fiend"
        assert len(downloaded["items"]) == 13
```

### Step 2: Run test to verify current status

```bash
uv run pytest tests/foundry/actors/test_pit_fiend_integration.py -v -m integration
```

**Expected:** PASS (all 13 items present)

### Step 3: Commit Pit Fiend integration test

```bash
git add tests/foundry/actors/test_pit_fiend_integration.py
git commit -m "test: add comprehensive Pit Fiend integration test"
```

---

## Task 6: Documentation and Cleanup

**Goal:** Document the new features and update README.

**Files:**
- Create: `docs/actor-parsing-guide.md`
- Modify: `CLAUDE.md` (update with new features)

### Step 1: Create actor parsing documentation

**File:** `docs/actor-parsing-guide.md`

```markdown
# Actor Parsing Guide

## Overview

The actor parsing system converts D&D 5e stat blocks into FoundryVTT actor JSON format.

## Supported Features

### Basic Stats
- Abilities (STR, DEX, CON, INT, WIS, CHA)
- Armor Class, Hit Points, Challenge Rating
- Saving throw proficiencies
- Movement speeds (walk, fly, swim, burrow, climb)
- Senses (darkvision, blindsight, tremorsense, truesight)

### Combat Features
- **Attacks** → Weapon items
- **Multiattack** → Feat item
- **Traits** → Feat items

### Spellcasting
- **Regular Spellcasting** → Spell items with levels
- **Innate Spellcasting** → Feat + Spell items
  - Supports frequency: "at will", "3/day", "1/day"
  - Automatically looks up spell UUIDs from FoundryVTT compendium
  - Preserves spell levels and schools

## Usage Example

```python
from foundry.actors.models import (
    ParsedActorData, Attack, Trait, Multiattack,
    InnateSpellcasting, InnateSpell, DamageFormula
)
from foundry.actors.converter import convert_to_foundry
from foundry.actors.spell_cache import SpellCache
from foundry.client import FoundryClient

# Create parsed actor data
actor_data = ParsedActorData(
    source_statblock_name="Pit Fiend",
    name="Pit Fiend",
    armor_class=19,
    hit_points=300,
    challenge_rating=20,
    abilities={"STR": 26, "DEX": 14, "CON": 24, "INT": 22, "WIS": 18, "CHA": 24},
    multiattack=Multiattack(
        name="Multiattack",
        description="Makes four attacks.",
        num_attacks=4
    ),
    innate_spellcasting=InnateSpellcasting(
        ability="charisma",
        save_dc=21,
        spells=[
            InnateSpell(name="Fireball", frequency="at will"),
            InnateSpell(name="Hold Monster", frequency="3/day", uses=3),
        ]
    ),
    attacks=[
        Attack(
            name="Bite",
            attack_type="melee",
            attack_bonus=14,
            reach=5,
            damage=[DamageFormula(number=4, denomination=6, bonus="+8", type="piercing")]
        )
    ]
)

# Convert to FoundryVTT format (with spell cache for UUIDs)
client = FoundryClient(target="local")
spell_cache = SpellCache(client)
spell_cache.load()

foundry_json = convert_to_foundry(actor_data, spell_cache=spell_cache)

# Upload to FoundryVTT
actor_uuid = client.actors.create_actor(foundry_json)
```

## Item Mapping

| Stat Block Element | FoundryVTT Item Type | Notes |
|--------------------|---------------------|-------|
| Attack | `weapon` | Melee/ranged attacks |
| Trait | `feat` | Special abilities |
| Multiattack | `feat` | Action to make multiple attacks |
| Innate Spellcasting | `feat` + `spell` items | Feat describes ability, spells are items |
| Spell | `spell` | Regular prepared spells |

## SpellCache Integration

The SpellCache automatically looks up spell UUIDs from the FoundryVTT compendium:

```python
spell_cache = SpellCache(client)
spell_cache.load()  # Loads once per session

# Use in conversion
foundry_json = convert_to_foundry(actor_data, spell_cache=spell_cache)
```

Benefits:
- Proper spell UUIDs that link to compendium
- Correct spell levels and schools
- No manual UUID management needed

## Testing

```bash
# Run unit tests
uv run pytest tests/foundry/actors/ -v -m "not integration"

# Run integration tests (requires FoundryVTT)
uv run pytest tests/foundry/actors/ -v -m integration
```
```

### Step 2: Update CLAUDE.md with new features

**File:** `CLAUDE.md`

Find the "FoundryVTT Integration" section and add:

```markdown
**Actor Parsing Features:**
- Basic stats (abilities, AC, HP, CR, saves, movement, senses)
- Attacks → weapon items with damage formulas
- Traits → feat items
- Multiattack → feat item
- Innate spellcasting → feat + spell items with usage limits
- SpellCache integration for automatic spell UUID lookup
- Full round-trip: ParsedActorData → Upload → Download → Verify

See `docs/actor-parsing-guide.md` for detailed usage.
```

### Step 3: Commit documentation

```bash
git add docs/actor-parsing-guide.md CLAUDE.md
git commit -m "docs: add actor parsing guide and update CLAUDE.md"
```

---

## Verification Steps

After completing all tasks, verify the implementation:

### 1. Run all tests

```bash
uv run pytest tests/foundry/actors/ -v
```

**Expected:** All tests pass (should be ~36-40 tests)

### 2. Run Pit Fiend integration test

```bash
uv run pytest tests/foundry/actors/test_pit_fiend_integration.py -v -m integration
```

**Expected:** PASS - Pit Fiend has 13 items (up from 7)

### 3. Manual verification

Run the Pit Fiend comparison script again:

```bash
uv run python /tmp/test_pit_fiend.py
```

**Expected:**
- Items count: 13 (vs official 12)
- All core items present
- Spell UUIDs correctly resolved

### 4. Check code quality

```bash
uv run python -m compileall src/foundry/actors
```

**Expected:** No syntax errors

---

## Success Criteria

✅ All tests pass (unit + integration)
✅ Pit Fiend has 13 items (4 weapons + 5 feats + 4 spells)
✅ SpellCache integration working (UUIDs resolved)
✅ Documentation complete
✅ Frequent commits with clear messages

## Next Steps (Future Enhancements)

1. **Legendary Actions** - Parse and convert legendary actions
2. **Lair Actions** - Parse lair action sections
3. **Reactions** - Parse and convert reactions
4. **Source Book Tracking** - Add source.book and source.license fields
5. **Damage Resistances/Immunities** - Parse complex resistance text
6. **Skills** - Parse skill proficiencies and bonuses

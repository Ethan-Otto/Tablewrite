# Weapon Activities Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix non-functional weapons by implementing FoundryVTT v10+ activities structure with full Pit Fiend support (attack + save + ongoing damage).

**Architecture:** Extend Attack model with optional SavingThrow field. Add activity generation helpers in converter that create proper v10+ activity structures (attack/save/damage types). Remove deprecated v9 fields (attackBonus, damage.parts at weapon level).

**Tech Stack:** Python 3.11, Pydantic models (frozen=True), FoundryVTT REST API

**Current Status:** 39/39 tests passing but weapons are non-functional in FoundryVTT (empty activities). Design validated with empirical test showing FoundryVTT does NOT auto-generate activities.

---

## Task 1: Add SavingThrow Model

**Files:**
- Modify: `src/foundry/actors/models.py` (add after Spell class, around line 80)
- Create: `tests/foundry/actors/test_saving_throw.py`

### Step 1: Write failing test for SavingThrow model

**File:** `tests/foundry/actors/test_saving_throw.py`

```python
"""Tests for SavingThrow model."""

import pytest
from foundry.actors.models import SavingThrow, DamageFormula


class TestSavingThrowModel:
    """Tests for SavingThrow model."""

    def test_basic_saving_throw(self):
        """Should create basic saving throw."""
        save = SavingThrow(
            ability="con",
            dc=13,
            damage=[DamageFormula(2, 6, "", "poison")],
            on_save="half"
        )

        assert save.ability == "con"
        assert save.dc == 13
        assert len(save.damage) == 1
        assert save.on_save == "half"

    def test_ongoing_damage_saving_throw(self):
        """Should support ongoing damage effects."""
        save = SavingThrow(
            ability="con",
            dc=21,
            damage=[],  # No immediate damage
            ongoing_damage=[DamageFormula(6, 6, "", "poison")],
            duration_rounds=10,
            effect_description="Poisoned - can't regain HP"
        )

        assert save.ongoing_damage is not None
        assert len(save.ongoing_damage) == 1
        assert save.duration_rounds == 10

    def test_saving_throw_on_save_validation(self):
        """Should validate on_save literal values."""
        # Valid values should work
        save1 = SavingThrow(ability="dex", dc=15, on_save="half")
        save2 = SavingThrow(ability="dex", dc=15, on_save="none")
        save3 = SavingThrow(ability="dex", dc=15, on_save="full")

        assert save1.on_save == "half"
        assert save2.on_save == "none"
        assert save3.on_save == "full"

    def test_saving_throw_frozen(self):
        """Should be immutable."""
        save = SavingThrow(ability="wis", dc=14)

        with pytest.raises(Exception):  # Pydantic frozen error
            save.dc = 15
```

### Step 2: Run test to verify it fails

**Command:**
```bash
uv run pytest tests/foundry/actors/test_saving_throw.py -v
```

**Expected Output:**
```
FAILED - ImportError: cannot import name 'SavingThrow'
```

### Step 3: Add SavingThrow model to models.py

**File:** `src/foundry/actors/models.py`

Add after the `Spell` class (around line 80):

```python
class SavingThrow(BaseModel):
    """A saving throw associated with an attack."""

    ability: str  # "con", "dex", "wis", etc.
    dc: int       # Difficulty Class

    # Damage on failed save
    damage: List[DamageFormula] = Field(default_factory=list)
    on_save: Literal["half", "none", "full"] = "none"  # Damage on successful save

    # For ongoing effects (e.g., poison damage each turn)
    ongoing_damage: Optional[List[DamageFormula]] = None
    duration_rounds: Optional[int] = None

    effect_description: Optional[str] = None  # e.g., "poisoned condition"

    model_config = ConfigDict(frozen=True)
```

### Step 4: Run test to verify it passes

**Command:**
```bash
uv run pytest tests/foundry/actors/test_saving_throw.py -v
```

**Expected Output:**
```
4 passed
```

### Step 5: Commit SavingThrow model

```bash
git add src/foundry/actors/models.py tests/foundry/actors/test_saving_throw.py
git commit -m "feat: add SavingThrow model for attack saves"
```

---

## Task 2: Update Attack Model with saving_throw Field

**Files:**
- Modify: `src/foundry/actors/models.py:40-50` (Attack class)
- Modify: `tests/foundry/actors/test_saving_throw.py` (add integration test)

### Step 1: Write failing test for Attack with saving_throw

**File:** `tests/foundry/actors/test_saving_throw.py`

Add to existing file:

```python
from foundry.actors.models import Attack


class TestAttackWithSavingThrow:
    """Tests for Attack model with saving_throw field."""

    def test_attack_with_saving_throw(self):
        """Should include optional saving_throw field."""
        attack = Attack(
            name="Poison Bite",
            attack_type="melee",
            attack_bonus=4,
            reach=5,
            damage=[DamageFormula(1, 6, "+2", "piercing")],
            saving_throw=SavingThrow(
                ability="con",
                dc=13,
                damage=[DamageFormula(2, 6, "", "poison")],
                on_save="half"
            )
        )

        assert attack.saving_throw is not None
        assert attack.saving_throw.ability == "con"
        assert attack.saving_throw.dc == 13

    def test_attack_without_saving_throw(self):
        """Should work without saving_throw (defaults to None)."""
        attack = Attack(
            name="Longsword",
            attack_type="melee",
            attack_bonus=5,
            reach=5,
            damage=[DamageFormula(1, 8, "+3", "slashing")]
        )

        assert attack.saving_throw is None
```

### Step 2: Run test to verify it fails

**Command:**
```bash
uv run pytest tests/foundry/actors/test_saving_throw.py::TestAttackWithSavingThrow -v
```

**Expected Output:**
```
FAILED - TypeError: Attack.__init__() got an unexpected keyword argument 'saving_throw'
```

### Step 3: Add saving_throw field to Attack model

**File:** `src/foundry/actors/models.py`

Update the `Attack` class (around line 40-50):

```python
class Attack(BaseModel):
    """An attack action."""

    name: str
    attack_type: Literal["melee", "ranged"]
    attack_bonus: int
    damage: List[DamageFormula]
    reach: Optional[int] = None
    range_short: Optional[int] = None
    range_long: Optional[int] = None
    additional_effects: Optional[str] = None

    # NEW: Optional saving throw
    saving_throw: Optional[SavingThrow] = None

    model_config = ConfigDict(frozen=True)
```

### Step 4: Run test to verify it passes

**Command:**
```bash
uv run pytest tests/foundry/actors/test_saving_throw.py -v
```

**Expected Output:**
```
6 passed
```

### Step 5: Commit Attack model update

```bash
git add src/foundry/actors/models.py tests/foundry/actors/test_saving_throw.py
git commit -m "feat: add saving_throw field to Attack model"
```

---

## Task 3: Add Activity Generation Helpers

**Files:**
- Modify: `src/foundry/actors/converter.py` (add helpers before convert_to_foundry function, around line 10)

### Step 1: Write failing test for activity helpers

**File:** `tests/foundry/actors/test_converter.py`

Add to existing file:

```python
from foundry.actors.converter import (
    _generate_activity_id,
    _base_activity_structure,
    _create_attack_activity,
    _create_save_activity,
    _create_ongoing_damage_activity
)
from foundry.actors.models import SavingThrow


class TestActivityHelpers:
    """Tests for activity generation helper functions."""

    def test_generate_activity_id(self):
        """Should generate unique 16-character IDs."""
        id1 = _generate_activity_id()
        id2 = _generate_activity_id()

        assert len(id1) == 16
        assert len(id2) == 16
        assert id1 != id2  # Should be unique

    def test_base_activity_structure(self):
        """Should return dict with all required base fields."""
        base = _base_activity_structure()

        assert "activation" in base
        assert "consumption" in base
        assert "description" in base
        assert "duration" in base
        assert "effects" in base
        assert "range" in base
        assert "target" in base
        assert "uses" in base

    def test_create_attack_activity(self):
        """Should create attack-type activity."""
        attack = Attack(
            name="Longsword",
            attack_type="melee",
            attack_bonus=5,
            reach=5,
            damage=[DamageFormula(1, 8, "+3", "slashing")]
        )

        activity = _create_attack_activity(attack, "test123")

        assert activity["type"] == "attack"
        assert activity["_id"] == "test123"
        assert activity["attack"]["bonus"] == "5"
        assert activity["attack"]["flat"] == True
        assert activity["damage"]["includeBase"] == True

    def test_create_save_activity(self):
        """Should create save-type activity."""
        save = SavingThrow(
            ability="con",
            dc=13,
            damage=[DamageFormula(2, 6, "", "poison")],
            on_save="half"
        )

        activity = _create_save_activity(save, "save456")

        assert activity["type"] == "save"
        assert activity["_id"] == "save456"
        assert activity["save"]["ability"] == ["con"]
        assert activity["save"]["dc"]["formula"] == "13"
        assert activity["damage"]["onSave"] == "half"
        assert len(activity["damage"]["parts"]) == 1
        assert activity["damage"]["parts"][0] == ["2d6", "poison"]

    def test_create_ongoing_damage_activity(self):
        """Should create damage-type activity for ongoing effects."""
        save = SavingThrow(
            ability="con",
            dc=21,
            ongoing_damage=[DamageFormula(6, 6, "", "poison")]
        )

        activity = _create_ongoing_damage_activity(save, "dmg789")

        assert activity["type"] == "damage"
        assert activity["_id"] == "dmg789"
        assert activity["activation"]["type"] == "turnStart"
        assert len(activity["damage"]["parts"]) == 1
        assert activity["damage"]["parts"][0] == ["6d6", "poison"]
```

### Step 2: Run test to verify it fails

**Command:**
```bash
uv run pytest tests/foundry/actors/test_converter.py::TestActivityHelpers -v
```

**Expected Output:**
```
FAILED - ImportError: cannot import name '_generate_activity_id'
```

### Step 3: Add activity helper functions to converter.py

**File:** `src/foundry/actors/converter.py`

Add these functions BEFORE the `convert_to_foundry` function (around line 10):

```python
import secrets
from .models import Attack, SavingThrow


def _generate_activity_id() -> str:
    """Generate a unique 16-character ID for activities."""
    return secrets.token_urlsafe(12)[:16]


def _base_activity_structure() -> dict:
    """Common fields for all activities."""
    return {
        "activation": {
            "type": "action",
            "value": None,
            "override": False,
            "condition": ""
        },
        "consumption": {
            "scaling": {"allowed": False},
            "spellSlot": True,
            "targets": []
        },
        "description": {"chatFlavor": ""},
        "duration": {
            "units": "inst",
            "concentration": False,
            "override": False
        },
        "effects": [],
        "range": {"override": False, "units": "self"},
        "target": {
            "template": {"contiguous": False, "units": "ft", "type": ""},
            "affects": {"choice": False, "type": "creature", "count": "1", "special": ""},
            "override": False,
            "prompt": True
        },
        "uses": {"spent": 0, "recovery": [], "max": ""}
    }


def _create_attack_activity(attack: Attack, activity_id: str) -> dict:
    """Create an attack-type activity for a weapon."""
    base = _base_activity_structure()
    base.update({
        "type": "attack",
        "_id": activity_id,
        "sort": 0,
        "attack": {
            "bonus": str(attack.attack_bonus),
            "flat": True,
            "critical": {"threshold": None},
            "type": {"value": attack.attack_type, "classification": "weapon"},
            "ability": ""
        },
        "damage": {
            "includeBase": True,
            "parts": [],
            "critical": {"bonus": ""}
        },
        "name": ""
    })
    return base


def _create_save_activity(save: SavingThrow, activity_id: str) -> dict:
    """Create a save-type activity."""
    base = _base_activity_structure()
    base.update({
        "type": "save",
        "_id": activity_id,
        "sort": 0,
        "save": {
            "ability": [save.ability],
            "dc": {"calculation": "", "formula": str(save.dc)}
        },
        "damage": {
            "parts": [[f"{d.number}d{d.denomination}{d.bonus}", d.type]
                     for d in save.damage],
            "onSave": save.on_save
        },
        "name": ""
    })
    return base


def _create_ongoing_damage_activity(save: SavingThrow, activity_id: str) -> dict:
    """Create ongoing damage activity (e.g., poison each turn)."""
    base = _base_activity_structure()
    base["activation"]["type"] = "turnStart"
    base.update({
        "type": "damage",
        "_id": activity_id,
        "sort": 0,
        "damage": {
            "critical": {"allow": False},
            "parts": [[f"{d.number}d{d.denomination}{d.bonus}", d.type]
                     for d in save.ongoing_damage]
        },
        "name": f"Add'l {save.ongoing_damage[0].type.capitalize()} Damage" if save.ongoing_damage else ""
    })
    return base
```

### Step 4: Run test to verify it passes

**Command:**
```bash
uv run pytest tests/foundry/actors/test_converter.py::TestActivityHelpers -v
```

**Expected Output:**
```
5 passed
```

### Step 5: Commit activity helpers

```bash
git add src/foundry/actors/converter.py tests/foundry/actors/test_converter.py
git commit -m "feat: add activity generation helper functions"
```

---

## Task 4: Update Weapon Conversion to Use Activities

**Files:**
- Modify: `src/foundry/actors/converter.py:93-114` (replace old attack conversion)

### Step 1: Write failing test for weapon with activities

**File:** `tests/foundry/actors/test_converter.py`

Update existing `TestConverter` class:

```python
def test_converts_attack_with_activities(self):
    """Should create weapon with attack activity (v10+ structure)."""
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
        ]
    )

    result = convert_to_foundry(goblin)
    weapon = result["items"][0]

    # NEW v10+ structure checks
    assert "activities" in weapon["system"]
    assert len(weapon["system"]["activities"]) == 1

    # Verify attack activity
    activity = list(weapon["system"]["activities"].values())[0]
    assert activity["type"] == "attack"
    assert activity["attack"]["bonus"] == "4"
    assert activity["attack"]["flat"] == True

    # OLD v9 fields should be removed
    assert "attackBonus" not in weapon["system"]
    assert "parts" not in weapon["system"].get("damage", {})

    # NEW damage.base structure
    assert "base" in weapon["system"]["damage"]
    assert weapon["system"]["damage"]["base"]["number"] == 1
    assert weapon["system"]["damage"]["base"]["denomination"] == 6

def test_converts_attack_with_save(self):
    """Should create weapon with attack + save activities."""
    actor = ParsedActorData(
        source_statblock_name="Test",
        name="Test",
        armor_class=15,
        hit_points=50,
        challenge_rating=2,
        abilities={"STR": 14, "DEX": 12, "CON": 13, "INT": 10, "WIS": 11, "CHA": 8},
        attacks=[
            Attack(
                name="Poison Bite",
                attack_type="melee",
                attack_bonus=4,
                reach=5,
                damage=[DamageFormula(1, 6, "+2", "piercing")],
                saving_throw=SavingThrow(
                    ability="con",
                    dc=13,
                    damage=[DamageFormula(2, 6, "", "poison")],
                    on_save="half"
                )
            )
        ]
    )

    result = convert_to_foundry(actor)
    weapon = result["items"][0]

    # Should have 2 activities: attack + save
    assert len(weapon["system"]["activities"]) == 2

    activities = list(weapon["system"]["activities"].values())
    assert any(a["type"] == "attack" for a in activities)
    assert any(a["type"] == "save" for a in activities)

def test_converts_attack_with_ongoing_damage(self):
    """Should create weapon with attack + save + ongoing damage activities."""
    pit_fiend = ParsedActorData(
        source_statblock_name="Pit Fiend",
        name="Pit Fiend",
        armor_class=19,
        hit_points=300,
        challenge_rating=20,
        abilities={"STR": 26, "DEX": 14, "CON": 24, "INT": 22, "WIS": 18, "CHA": 24},
        attacks=[
            Attack(
                name="Bite",
                attack_type="melee",
                attack_bonus=14,
                reach=5,
                damage=[DamageFormula(4, 6, "+8", "piercing")],
                saving_throw=SavingThrow(
                    ability="con",
                    dc=21,
                    ongoing_damage=[DamageFormula(6, 6, "", "poison")],
                    duration_rounds=10
                )
            )
        ]
    )

    result = convert_to_foundry(pit_fiend)
    bite = result["items"][0]

    # Should have 3 activities: attack + save + ongoing damage
    assert len(bite["system"]["activities"]) == 3

    activities = list(bite["system"]["activities"].values())
    assert any(a["type"] == "attack" for a in activities)
    assert any(a["type"] == "save" for a in activities)
    assert any(a["type"] == "damage" for a in activities)

    # Verify ongoing damage has correct activation
    dmg_activity = [a for a in activities if a["type"] == "damage"][0]
    assert dmg_activity["activation"]["type"] == "turnStart"
```

### Step 2: Run test to verify it fails

**Command:**
```bash
uv run pytest tests/foundry/actors/test_converter.py::TestConverter::test_converts_attack_with_activities -v
```

**Expected Output:**
```
FAILED - AssertionError: assert 'activities' in {...}
```

### Step 3: Replace weapon conversion with activities

**File:** `src/foundry/actors/converter.py`

Replace the attack conversion section (lines 93-114) with:

```python
    # Convert attacks to weapon items (NEW v10+ structure with activities)
    for attack in parsed_actor.attacks:
        activities = {}

        # 1. Always create attack activity
        attack_id = _generate_activity_id()
        activities[attack_id] = _create_attack_activity(attack, attack_id)

        # 2. Add save activity if present
        if attack.saving_throw:
            save_id = _generate_activity_id()
            activities[save_id] = _create_save_activity(attack.saving_throw, save_id)

            # 3. Add ongoing damage activity if present
            if attack.saving_throw.ongoing_damage:
                dmg_id = _generate_activity_id()
                activities[dmg_id] = _create_ongoing_damage_activity(attack.saving_throw, dmg_id)

        # Build weapon item (v10+ structure)
        item = {
            "name": attack.name,
            "type": "weapon",
            "img": "icons/weapons/swords/scimitar-guard-purple.webp",
            "system": {
                "description": {"value": attack.additional_effects or ""},
                "activities": activities,
                "damage": {
                    "base": {
                        "number": attack.damage[0].number,
                        "denomination": attack.damage[0].denomination,
                        "bonus": attack.damage[0].bonus.replace("+", ""),
                        "types": [attack.damage[0].type],
                        "custom": {"enabled": False, "formula": ""},
                        "scaling": {"mode": "", "number": None, "formula": ""}
                    },
                    "versatile": {
                        "number": None,
                        "denomination": None,
                        "types": [],
                        "custom": {"enabled": False},
                        "scaling": {"number": 1}
                    }
                },
                "range": {
                    "value": attack.range_short,
                    "long": attack.range_long,
                    "reach": attack.reach,
                    "units": "ft"
                },
                "type": {"value": "natural", "baseItem": ""},
                "properties": [],
                "uses": {"spent": 0, "recovery": [], "max": ""}
            }
        }
        items.append(item)
```

### Step 4: Run test to verify it passes

**Command:**
```bash
uv run pytest tests/foundry/actors/test_converter.py::TestConverter -v
```

**Expected Output:**
```
7 passed  # (4 old tests + 3 new activity tests)
```

### Step 5: Commit weapon activities conversion

```bash
git add src/foundry/actors/converter.py tests/foundry/actors/test_converter.py
git commit -m "feat: implement v10+ activities structure for weapons"
```

---

## Task 5: Add Integration Tests for Functional Weapons

**Files:**
- Modify: `tests/foundry/actors/test_roundtrip_integration.py` (add new tests)

### Step 1: Write failing integration test

**File:** `tests/foundry/actors/test_roundtrip_integration.py`

Add to existing file:

```python
@pytest.mark.integration
@pytest.mark.requires_foundry
def test_weapon_activities_functional_in_foundry():
    """Weapons should have working attack buttons in FoundryVTT."""
    goblin = ParsedActorData(
        source_statblock_name="Goblin",
        name="Goblin Activities Test",
        armor_class=15,
        hit_points=7,
        challenge_rating=0.25,
        abilities={"STR": 8, "DEX": 14, "CON": 10, "INT": 10, "WIS": 8, "CHA": 8},
        attacks=[Attack(
            name="Scimitar",
            attack_type="melee",
            attack_bonus=4,
            reach=5,
            damage=[DamageFormula(1, 6, "+2", "slashing")]
        )]
    )

    client = FoundryClient(target="local")
    foundry_json = convert_to_foundry(goblin)
    actor_uuid = client.actors.create_actor(foundry_json)

    # Download and verify
    downloaded = client.actors.get_actor(actor_uuid)
    weapon = [i for i in downloaded["items"] if i["type"] == "weapon"][0]

    # CRITICAL: Verify activities are present and correct
    assert "activities" in weapon["system"]
    assert len(weapon["system"]["activities"]) > 0

    # Verify attack activity has required functional fields
    attack_activity = [a for a in weapon["system"]["activities"].values()
                       if a["type"] == "attack"][0]
    assert attack_activity["attack"]["bonus"] == "4"
    assert attack_activity["attack"]["flat"] == True
    assert "damage" in attack_activity


@pytest.mark.integration
@pytest.mark.requires_foundry
def test_pit_fiend_bite_full_complexity():
    """Pit Fiend bite should have attack + save + ongoing damage."""
    pit_fiend = ParsedActorData(
        source_statblock_name="Pit Fiend",
        name="Pit Fiend Full Complexity Test",
        armor_class=19,
        hit_points=300,
        challenge_rating=20,
        abilities={"STR": 26, "DEX": 14, "CON": 24, "INT": 22, "WIS": 18, "CHA": 24},
        attacks=[Attack(
            name="Bite",
            attack_type="melee",
            attack_bonus=14,
            reach=5,
            damage=[DamageFormula(4, 6, "+8", "piercing")],
            saving_throw=SavingThrow(
                ability="con",
                dc=21,
                ongoing_damage=[DamageFormula(6, 6, "", "poison")],
                duration_rounds=10
            )
        )]
    )

    client = FoundryClient(target="local")
    foundry_json = convert_to_foundry(pit_fiend)
    actor_uuid = client.actors.create_actor(foundry_json)

    downloaded = client.actors.get_actor(actor_uuid)
    bite = [i for i in downloaded["items"] if i["name"] == "Bite"][0]

    # Should have 3 activities
    assert len(bite["system"]["activities"]) == 3

    # Verify each activity type
    activities = bite["system"]["activities"].values()
    assert any(a["type"] == "attack" for a in activities)
    assert any(a["type"] == "save" for a in activities)
    assert any(a["type"] == "damage" for a in activities)

    # Verify save details
    save_activity = [a for a in activities if a["type"] == "save"][0]
    assert save_activity["save"]["ability"] == ["con"]
    assert save_activity["save"]["dc"]["formula"] == "21"

    # Verify ongoing damage details
    dmg_activity = [a for a in activities if a["type"] == "damage"][0]
    assert dmg_activity["activation"]["type"] == "turnStart"
    assert dmg_activity["damage"]["parts"][0][0] == "6d6"
```

### Step 2: Run test to verify current state

**Command:**
```bash
uv run pytest tests/foundry/actors/test_roundtrip_integration.py::test_weapon_activities_functional_in_foundry -v -m integration
```

**Expected Output:**
```
PASSED  # Should pass with our new converter
```

### Step 3: Run all integration tests

**Command:**
```bash
uv run pytest tests/foundry/actors/test_roundtrip_integration.py -v -m integration
```

**Expected Output:**
```
8 passed  # All integration tests including 2 new ones
```

### Step 4: Commit integration tests

```bash
git add tests/foundry/actors/test_roundtrip_integration.py
git commit -m "test: add integration tests for functional weapon activities"
```

---

## Task 6: Update Pit Fiend Integration Test

**Files:**
- Modify: `tests/foundry/actors/test_pit_fiend_integration.py` (update fixture with saving_throw)

### Step 1: Update Pit Fiend test fixture with saving throw

**File:** `tests/foundry/actors/test_pit_fiend_integration.py`

Update the `pit_fiend_data` fixture (around line 80-90):

```python
@pytest.fixture
def pit_fiend_data(self):
    """Complete Pit Fiend data with saving throws."""
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
        saving_throw_proficiencies=["dex", "wis"],
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
                ],
                # NEW: Add saving throw
                saving_throw=SavingThrow(
                    ability="con",
                    dc=21,
                    ongoing_damage=[DamageFormula(6, 6, "", "poison")],
                    duration_rounds=10,
                    effect_description="Poisoned - can't regain HP"
                )
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
```

Add import at top of file:
```python
from foundry.actors.models import SavingThrow
```

### Step 2: Add test to verify Bite has 3 activities

**File:** `tests/foundry/actors/test_pit_fiend_integration.py`

Update `test_pit_fiend_has_all_items` test:

```python
def test_pit_fiend_has_all_items(self, pit_fiend_data, spell_cache):
    """Pit Fiend should have 13 items like official FoundryVTT."""
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

    # NEW: Verify Bite has 3 activities (attack + save + ongoing damage)
    bite = [w for w in weapons if w["name"] == "Bite"][0]
    assert len(bite["system"]["activities"]) == 3
    bite_activities = bite["system"]["activities"].values()
    assert any(a["type"] == "attack" for a in bite_activities)
    assert any(a["type"] == "save" for a in bite_activities)
    assert any(a["type"] == "damage" for a in bite_activities)

    # Other weapons should have 1 activity (just attack)
    claw = [w for w in weapons if w["name"] == "Claw"][0]
    assert len(claw["system"]["activities"]) == 1

    # Should have 5 feats
    assert len(feats) >= 5
    assert any(f["name"] == "Multiattack" for f in feats)
    assert any(f["name"] == "Fear Aura" for f in feats)
    assert any(f["name"] == "Magic Resistance" for f in feats)
    assert any(f["name"] == "Magic Weapons" for f in feats)
    assert any("Innate Spellcasting" in f["name"] for f in feats)

    # Should have 4 spells
    assert len(spells) == 4

    # Total should be 13 items
    assert len(items) == 13
```

### Step 3: Run Pit Fiend integration tests

**Command:**
```bash
uv run pytest tests/foundry/actors/test_pit_fiend_integration.py -v -m integration
```

**Expected Output:**
```
2 passed
```

### Step 4: Commit Pit Fiend test updates

```bash
git add tests/foundry/actors/test_pit_fiend_integration.py
git commit -m "test: update Pit Fiend fixture with saving throw for Bite"
```

---

## Task 7: Run Full Test Suite and Verify

**Files:**
- None (verification only)

### Step 1: Run all unit tests

**Command:**
```bash
uv run pytest tests/foundry/actors/ -v -m "not integration"
```

**Expected Output:**
```
40+ passed  # Should be more than original 39 due to new tests
```

### Step 2: Run all integration tests

**Command:**
```bash
uv run pytest tests/foundry/actors/ -v -m integration
```

**Expected Output:**
```
9+ passed  # Original 7 + 2 new weapon activity tests
```

### Step 3: Run complete test suite

**Command:**
```bash
uv run pytest tests/foundry/actors/ -v
```

**Expected Output:**
```
49+ passed
```

### Step 4: Verify with timestamped upload

**Command:**
```bash
uv run python /tmp/upload_pit_fiend_timestamped.py
```

**Expected Output:**
```
SUCCESS!
Actor Name: Pit Fiend (Enhanced YYYYMMDD_HHMMSS)
Total Items: 13

Check FoundryVTT - weapons should now have clickable attack buttons!
```

### Step 5: Final commit - update documentation

**File:** `docs/actor-parsing-guide.md`

Add section under "Future Enhancements":

```markdown
## Recent Additions

### Weapon Activities (2025-01-02)

Weapons now use FoundryVTT v10+ activities structure:
- ✅ Attack activities for all weapons
- ✅ Save activities for weapons with saving throws
- ✅ Ongoing damage activities (e.g., poison each turn)

**Example:**
```python
Attack(
    name="Poison Bite",
    attack_bonus=4,
    damage=[DamageFormula(1, 6, "+2", "piercing")],
    saving_throw=SavingThrow(
        ability="con",
        dc=13,
        ongoing_damage=[DamageFormula(2, 6, "", "poison")]
    )
)
```

Creates 3 activities in FoundryVTT:
1. Attack: +4 to hit, 1d6+2 piercing
2. Save: DC 13 CON
3. Damage: 2d6 poison (start of each turn)
```

**Command:**
```bash
git add docs/actor-parsing-guide.md
git commit -m "docs: document weapon activities feature"
```

---

## Verification Steps

After completing all tasks, verify the implementation:

### 1. Test Results

Run final test suite:
```bash
uv run pytest tests/foundry/actors/ -v
```

**Expected:** 49+ tests passing (40+ unit, 9+ integration)

### 2. FoundryVTT Verification

Upload test actor and verify in FoundryVTT UI:
```bash
uv run python /tmp/upload_pit_fiend_timestamped.py
```

**Manual checks in FoundryVTT:**
- ✅ Weapons have attack buttons
- ✅ Can click to roll attack
- ✅ Can click to roll damage
- ✅ Bite weapon shows save DC in tooltip
- ✅ Character sheet displays all activities

### 3. Round-Trip Test

Verify FoundryVTT preserves activities:
```bash
uv run python /tmp/test_current_converter_roundtrip.py
```

**Expected:**
```
BEFORE upload:
  - activities: ['abc123']  # Has attack activity

AFTER download:
  - activities: ['abc123']  # Still has attack activity

Activities added by FoundryVTT: False  # (already present)
```

---

## Success Criteria

- ✅ All tests pass (49+ tests, 100% success rate)
- ✅ Weapons have functional attack activities
- ✅ Pit Fiend Bite has 3 activities (attack + save + ongoing damage)
- ✅ v9 deprecated fields removed (attackBonus, damage.parts)
- ✅ v10+ structure implemented (activities, damage.base)
- ✅ Integration tests verify weapons work in FoundryVTT
- ✅ Documentation updated

---

## Next Steps (Future Enhancements)

1. **Gemini Parsing** - Extend Gemini prompt to extract saving throws from stat block text
2. **Legendary Actions** - Parse and create activities for legendary actions
3. **Reactions** - Support reaction-type activation
4. **Versatile Weapons** - Create separate activity for two-handed damage
5. **Spell Attack Activities** - Apply same pattern to spell items

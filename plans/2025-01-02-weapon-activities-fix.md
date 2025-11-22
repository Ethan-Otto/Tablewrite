# Weapon Activities Fix - Design Document

**Date:** 2025-01-02
**Status:** Approved
**Priority:** Critical (weapons are non-functional)

## Problem Statement

### Current Issue

Weapons created by our converter are **non-functional in FoundryVTT**:
- ✗ No attack button appears on character sheets
- ✗ Cannot roll attack or damage
- ✗ Weapons display but have no clickable actions

### Root Cause

Our converter uses the deprecated FoundryVTT v9 structure:
```python
"system": {
    "attackBonus": "14",  # Deprecated - ignored by v10+
    "damage": {
        "parts": [["4d6+8", "piercing"]]  # Wrong format
    }
}
```

FoundryVTT v10+ requires the **activities** system:
```python
"system": {
    "activities": {
        "abc123": {  # Unique activity ID
            "type": "attack",
            "attack": {"bonus": "14", "flat": true},
            "damage": {"parts": [["4d6+8", "piercing"]]}
        }
    },
    "damage": {
        "base": {  # Base damage structure (correct)
            "number": 4,
            "denomination": 6,
            "bonus": "8",
            "types": ["piercing"]
        }
    }
}
```

### Empirical Verification

Tested with FoundryVTT (2025-01-02):
- Uploaded weapon with `activities: {}` (empty)
- Downloaded back: Still `activities: {}`
- **Conclusion:** FoundryVTT does NOT auto-generate activities - we must create them

See test: `/tmp/test_current_converter_roundtrip.py`

---

## Design Goals

1. **Complete parity with official FoundryVTT structure**
2. **Support full Pit Fiend complexity** (attack + saving throw + ongoing damage)
3. **v10+ only** - remove deprecated v9 fields
4. **Extensible** - future Gemini integration for parsing saves from text

---

## Architecture

### Data Model Extensions

#### New Model: SavingThrow

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

#### Updated Model: Attack

```python
class Attack(BaseModel):
    # ... existing fields ...

    # NEW: Optional saving throw
    saving_throw: Optional[SavingThrow] = None

    model_config = ConfigDict(frozen=True)
```

### Example Usage: Pit Fiend Bite

```python
Attack(
    name="Bite",
    attack_type="melee",
    attack_bonus=14,
    reach=5,
    damage=[DamageFormula(4, 6, "+8", "piercing")],
    saving_throw=SavingThrow(
        ability="con",
        dc=21,
        damage=[],  # No immediate damage
        on_save="none",
        ongoing_damage=[DamageFormula(6, 6, "", "poison")],  # 6d6 per turn
        duration_rounds=10,  # 1 minute
        effect_description="Poisoned - can't regain HP"
    )
)
```

This creates 3 activities in FoundryVTT:
1. **Attack activity** - Roll to hit + 4d6+8 piercing damage
2. **Save activity** - DC 21 CON save
3. **Damage activity** - 6d6 poison damage (activation: "turnStart")

---

## Converter Implementation

### Activity Generation Functions

```python
# Helper: Generate unique activity IDs
def _generate_activity_id() -> str:
    """Generate a unique 16-character ID for activities."""
    import secrets
    return secrets.token_urlsafe(12)[:16]

# Helper: Base activity structure (common fields)
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

# Activity creator: Attack
def _create_attack_activity(attack: Attack, activity_id: str) -> dict:
    """Create an attack-type activity for a weapon."""
    base = _base_activity_structure()
    base.update({
        "type": "attack",
        "_id": activity_id,
        "sort": 0,
        "attack": {
            "bonus": str(attack.attack_bonus),
            "flat": True,  # Use flat bonus, not ability-based
            "critical": {"threshold": None},
            "type": {"value": attack.attack_type, "classification": "weapon"},
            "ability": ""
        },
        "damage": {
            "includeBase": True,  # Use weapon.damage.base
            "parts": [],
            "critical": {"bonus": ""}
        },
        "name": ""
    })
    return base

# Activity creator: Save
def _create_save_activity(save: SavingThrow, activity_id: str) -> dict:
    """Create a save-type activity."""
    base = _base_activity_structure()
    base.update({
        "type": "save",
        "_id": activity_id,
        "sort": 0,
        "save": {
            "ability": [save.ability],  # List of abilities
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

# Activity creator: Ongoing Damage
def _create_ongoing_damage_activity(save: SavingThrow, activity_id: str) -> dict:
    """Create ongoing damage activity (e.g., poison each turn)."""
    base = _base_activity_structure()
    base["activation"]["type"] = "turnStart"  # Override activation timing
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

### Main Conversion Logic

```python
# In convert_to_foundry(), replace attack conversion section:
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

    # Build weapon item (NEW v10+ structure)
    item = {
        "name": attack.name,
        "type": "weapon",
        "img": "icons/weapons/swords/scimitar-guard-purple.webp",
        "system": {
            "description": {"value": attack.additional_effects or ""},
            "activities": activities,  # NEW: activities instead of flat attackBonus
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

### Fields Removed (v9 deprecated)

- ✗ `system.attackBonus` - replaced by `activities[].attack.bonus`
- ✗ `system.damage.parts` - replaced by `activities[].damage.parts`
- ✗ `system.actionType` - replaced by `activities[].attack.type.value`

---

## Testing Strategy

### Unit Tests

**File:** `tests/foundry/actors/test_converter.py`

```python
def test_creates_attack_activity():
    """Should create attack activity with proper structure."""
    actor = ParsedActorData(
        name="Test",
        attacks=[Attack(
            name="Longsword",
            attack_type="melee",
            attack_bonus=5,
            reach=5,
            damage=[DamageFormula(1, 8, "+3", "slashing")]
        )]
    )

    result = convert_to_foundry(actor)
    weapon = result["items"][0]

    # Verify activities exist
    assert "activities" in weapon["system"]
    assert len(weapon["system"]["activities"]) == 1

    # Verify attack activity structure
    activity = list(weapon["system"]["activities"].values())[0]
    assert activity["type"] == "attack"
    assert activity["attack"]["bonus"] == "5"
    assert activity["attack"]["flat"] == True
    assert activity["damage"]["includeBase"] == True

def test_creates_save_activity():
    """Should create save activity when saving throw present."""
    actor = ParsedActorData(
        name="Test",
        attacks=[Attack(
            name="Poison Bite",
            attack_type="melee",
            attack_bonus=4,
            damage=[DamageFormula(1, 6, "+2", "piercing")],
            saving_throw=SavingThrow(
                ability="con",
                dc=13,
                damage=[DamageFormula(2, 6, "", "poison")],
                on_save="half"
            )
        )]
    )

    result = convert_to_foundry(actor)
    weapon = result["items"][0]

    # Should have 2 activities: attack + save
    assert len(weapon["system"]["activities"]) == 2

    # Verify save activity
    save_activity = [a for a in weapon["system"]["activities"].values()
                     if a["type"] == "save"][0]
    assert save_activity["save"]["ability"] == ["con"]
    assert save_activity["save"]["dc"]["formula"] == "13"
    assert save_activity["damage"]["onSave"] == "half"
```

### Integration Tests

**File:** `tests/foundry/actors/test_roundtrip_integration.py`

```python
@pytest.mark.integration
@pytest.mark.requires_foundry
def test_weapon_activities_functional_in_foundry():
    """Weapons should have working attack buttons in FoundryVTT."""
    goblin = ParsedActorData(
        name="Goblin Activities Test",
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
        name="Pit Fiend Full Test",
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
```

---

## Migration Path

### Existing Actors

All previously created actors will need to be re-uploaded after this fix:
- Old actors have `activities: {}` (broken)
- New actors will have proper activities (functional)

### Backward Compatibility

**None.** This is a breaking change:
- ✗ v9 structure removed entirely
- ✓ v10+ structure only
- Assumes FoundryVTT v10+ and dnd5e system v4+

---

## Success Criteria

- ✅ All weapons have at least one attack activity
- ✅ Weapons with saves create save activities
- ✅ Weapons with ongoing effects create damage activities
- ✅ Integration tests verify weapons work in FoundryVTT
- ✅ Pit Fiend bite has 3 functional activities
- ✅ All 39+ tests passing (unit + integration)

---

## Future Enhancements

### Phase 2: Gemini Integration

Once converter is fixed, extend Gemini prompt to extract:
- Saving throw ability and DC from text
- Ongoing damage from effect descriptions
- Duration of effects

Example extraction:
```
Input: "DC 21 Constitution saving throw or become poisoned. While poisoned,
        target takes 6d6 poison damage at start of each turn for 1 minute."

Output: SavingThrow(
    ability="con",
    dc=21,
    ongoing_damage=[DamageFormula(6, 6, "", "poison")],
    duration_rounds=10
)
```

This keeps complexity in Gemini (where it belongs) instead of text parsing in converter.

---

## References

- Official FoundryVTT documentation: https://github.com/foundryvtt/dnd5e/wiki/Activities
- Empirical test script: `/tmp/test_current_converter_roundtrip.py`
- Official Pit Fiend JSON: `data/foundry_examples/pit_fiend.json`

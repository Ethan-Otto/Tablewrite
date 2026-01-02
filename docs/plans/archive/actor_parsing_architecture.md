# Actor Parsing Architecture Proposal

**Date**: 2025-10-31
**Status**: Design Phase
**References**: `docs/foundry_actor_structure.md`, `docs/actor_parsing_design.md`

## Overview

Three-stage pipeline for converting D&D 5e stat blocks into mechanically complete FoundryVTT actors.

```
Raw Text → StatBlock (basic) → ParsedActorData (detailed) → FoundryVTT JSON
```

## Data Models

### 1. StatBlock (Current - Minimal Changes)

**Location**: `src/actors/models.py`

**Purpose**: Store extracted stat block with basic validation

```python
class StatBlock(BaseModel):
    """D&D 5e stat block - basic extraction."""

    # Identity
    name: str
    raw_text: str  # Always preserve original

    # Core stats (REQUIRED for validation)
    armor_class: int
    hit_points: int
    challenge_rating: float

    # Optional basic fields
    size: Optional[str] = None
    type: Optional[str] = None
    alignment: Optional[str] = None
    abilities: Optional[Dict[str, int]] = None  # STR, DEX, CON, INT, WIS, CHA
    speed: Optional[str] = None
    senses: Optional[str] = None
    languages: Optional[str] = None

    # Raw unparsed sections (still text)
    traits: Optional[str] = None  # Everything between stats and ACTIONS
    actions: Optional[str] = None  # ACTIONS section
    reactions: Optional[str] = None  # REACTIONS section (if present)
```

**Changes from current**:
- Add `reactions` field
- Keep as simple as possible (extraction-focused)

---

### 2. ParsedActorData (NEW - Detailed Parsing)

**Location**: `src/actors/parsed_models.py` (new file)

**Purpose**: Fully structured data ready for FoundryVTT conversion

```python
from typing import List, Optional, Literal
from pydantic import BaseModel, Field
from .models import StatBlock

# ========== Parsed Components ==========

class DamageFormula(BaseModel):
    """Dice damage formula."""
    number: int  # Dice count
    denomination: int  # Dice size (d6, d8, etc.)
    bonus: str = ""  # Flat bonus
    type: str  # piercing, slashing, fire, etc.

class Attack(BaseModel):
    """Parsed attack (weapon or spell attack)."""
    name: str
    attack_type: Literal["melee", "ranged", "melee_ranged"]
    attack_bonus: int
    reach: Optional[int] = None  # Melee reach in feet
    range_short: Optional[int] = None  # Ranged short range
    range_long: Optional[int] = None  # Ranged long range
    damage: List[DamageFormula]  # Multiple damage types possible
    additional_effects: Optional[str] = None  # e.g., "target is grappled"

class SavingThrow(BaseModel):
    """Saving throw triggered by ability."""
    ability: Literal["str", "dex", "con", "int", "wis", "cha"]
    dc: Optional[int] = None  # If specified in stat block
    dc_ability: Optional[str] = None  # e.g., "cha" for "DC 8 + Cha mod + prof"
    on_failure: str  # Description of failure effect
    on_success: Optional[str] = None  # Description if specified

class Trait(BaseModel):
    """Parsed trait/feature."""
    name: str
    description: str
    activation: Optional[Literal["action", "bonus", "reaction", "passive"]] = "passive"
    uses: Optional[int] = None  # Limited uses per day/rest
    recharge: Optional[str] = None  # e.g., "5-6" for recharge on 5 or 6
    saving_throw: Optional[SavingThrow] = None

class SkillProficiency(BaseModel):
    """Skill proficiency entry."""
    skill: str  # "Stealth", "Perception", etc.
    bonus: int  # Total bonus (includes ability mod + proficiency)
    proficiency_level: Literal[0, 1, 2] = 1  # 0=none, 1=proficient, 2=expertise

class DamageModification(BaseModel):
    """Damage resistance/immunity/vulnerability."""
    types: List[str]  # ["fire", "poison"]
    condition: Optional[str] = None  # "from nonmagical attacks"

# ========== Main Parsed Data ==========

class ParsedActorData(BaseModel):
    """Fully parsed stat block ready for FoundryVTT conversion."""

    # Reference to source
    source_statblock: StatBlock

    # Core stats (copied from StatBlock for convenience)
    name: str
    armor_class: int
    hit_points: int
    hit_dice: Optional[str] = None  # e.g., "27d10 + 189"
    challenge_rating: float

    # Abilities
    abilities: Dict[str, int]  # STR, DEX, CON, INT, WIS, CHA
    saving_throw_proficiencies: List[str] = []  # ["dex", "wis"]

    # Skills
    skill_proficiencies: List[SkillProficiency] = []

    # Defenses
    damage_resistances: Optional[DamageModification] = None
    damage_immunities: Optional[DamageModification] = None
    damage_vulnerabilities: Optional[DamageModification] = None
    condition_immunities: List[str] = []  # ["poisoned", "charmed"]

    # Movement
    speed_walk: Optional[int] = 30
    speed_fly: Optional[int] = None
    speed_swim: Optional[int] = None
    speed_burrow: Optional[int] = None
    speed_climb: Optional[int] = None

    # Senses
    darkvision: Optional[int] = None
    blindsight: Optional[int] = None
    tremorsense: Optional[int] = None
    truesight: Optional[int] = None

    # Languages
    languages: List[str] = []

    # Abilities
    traits: List[Trait] = []
    attacks: List[Attack] = []
    reactions: List[Trait] = []  # Reactions are traits with activation="reaction"

    # Multiattack label (optional)
    multiattack_description: Optional[str] = None
```

---

### 3. FoundryVTT Output (Existing - Enhanced)

**Location**: `src/foundry/foundry_models.py` (new file)

**Purpose**: Type-safe FoundryVTT JSON structure

```python
from typing import List, Dict, Any, Literal, Optional
from pydantic import BaseModel

class FoundryAbility(BaseModel):
    """FoundryVTT ability score structure."""
    value: int
    proficient: Literal[0, 1] = 0  # Saving throw proficiency
    max: None = None
    bonuses: Dict[str, str] = {"check": "", "save": ""}
    check: Dict[str, Any] = {"roll": {"min": None, "max": None, "mode": 0}}
    save: Dict[str, Any] = {"roll": {"min": None, "max": None, "mode": 0}}

class FoundrySkill(BaseModel):
    """FoundryVTT skill structure."""
    value: Literal[0, 1, 2]  # 0=none, 1=proficient, 2=expertise
    ability: str
    bonuses: Dict[str, str] = {"check": "", "passive": ""}
    roll: Dict[str, Any] = {"min": None, "max": None, "mode": 0}

class FoundryDamageFormula(BaseModel):
    """FoundryVTT damage part structure."""
    number: int
    denomination: int
    bonus: str = ""
    types: List[str]
    custom: Dict[str, Any] = {"enabled": False, "formula": ""}
    scaling: Dict[str, int] = {"number": 1}

class FoundryActivity(BaseModel):
    """FoundryVTT activity (attack, save, damage, etc.)."""
    _id: str
    type: Literal["attack", "save", "damage", "utility", "cast"]
    activation: Dict[str, Any]
    consumption: Dict[str, Any]
    description: Dict[str, str]
    duration: Dict[str, Any]
    range: Dict[str, Any]
    target: Dict[str, Any]
    uses: Dict[str, Any]
    # Type-specific fields
    attack: Optional[Dict[str, Any]] = None  # For attack activities
    damage: Optional[Dict[str, Any]] = None  # For damage activities
    save: Optional[Dict[str, Any]] = None  # For save activities

class FoundryItem(BaseModel):
    """FoundryVTT item (weapon, feat, spell)."""
    _id: str
    name: str
    type: Literal["weapon", "feat", "spell"]
    img: str
    system: Dict[str, Any]
    effects: List[Dict[str, Any]] = []
    flags: Dict[str, Any] = {}
    folder: Optional[str] = None
    sort: int = 0

class FoundryActor(BaseModel):
    """Complete FoundryVTT actor structure."""
    name: str
    type: Literal["npc"] = "npc"
    img: str = ""
    system: Dict[str, Any]
    items: List[FoundryItem]
    effects: List[Dict[str, Any]] = []
    flags: Dict[str, Any] = {}
```

---

## Pipeline Components

### Component 1: Stat Block Extractor (Existing)

**File**: `src/actors/extract_stat_blocks.py` (current)
**File**: `src/actors/parse_stat_blocks.py` (current)

**Input**: XML from PDF extraction
**Output**: `StatBlock` objects

**Status**: Already implemented, minimal changes needed

---

### Component 2: Detailed Parser (NEW)

**File**: `src/actors/parse_detailed.py` (new)

**Purpose**: Convert `StatBlock` → `ParsedActorData` using Gemini

**Strategy**:
1. **Gemini prompt**: Parse actions, traits, reactions into structured JSON
2. **Python validation**: Pydantic models enforce structure
3. **Python extraction**: Basic stats (abilities, skills) from existing fields

**Example**:

```python
def parse_actor_details(stat_block: StatBlock, api: GeminiAPI) -> ParsedActorData:
    """Parse detailed actor data from stat block using Gemini."""

    # Python-extracted data (no AI needed)
    abilities = stat_block.abilities or {}

    # Gemini-parsed data (complex natural language)
    parsed_json = _parse_with_gemini(stat_block, api)

    return ParsedActorData(
        source_statblock=stat_block,
        name=stat_block.name,
        armor_class=stat_block.armor_class,
        hit_points=stat_block.hit_points,
        challenge_rating=stat_block.challenge_rating,
        abilities=abilities,
        attacks=parsed_json["attacks"],
        traits=parsed_json["traits"],
        # ... etc
    )
```

**Gemini Prompt Structure**:

```
Parse this D&D 5e stat block into structured JSON.

STAT BLOCK:
{stat_block.raw_text}

Extract the following:

1. ATTACKS (from ACTIONS section):
For each attack, extract:
- name: Attack name
- attack_type: "melee" | "ranged" | "melee_ranged"
- attack_bonus: Integer (e.g., +4)
- reach: Integer feet (for melee)
- range_short, range_long: Integers (for ranged, e.g., 80/320)
- damage: List of damage formulas
  - number: Dice count
  - denomination: Dice size
  - bonus: Flat modifier
  - type: Damage type

2. TRAITS (between stat line and ACTIONS):
For each trait, extract:
- name: Trait name
- description: Full text
- activation: "action" | "bonus" | "reaction" | "passive"
- saving_throw (if applicable):
  - ability: "str" | "dex" | "con" | "int" | "wis" | "cha"
  - on_failure: Effect description

Return JSON matching this schema: {ParsedActorData.schema_json()}
```

---

### Component 3: FoundryVTT Converter (NEW)

**File**: `src/foundry/convert_to_foundry.py` (new)

**Purpose**: Convert `ParsedActorData` → `FoundryActor` (pure transformation, no parsing)

**Strategy**:
- Builder pattern for items
- Template-based activity generation
- No AI - pure data mapping

**Example**:

```python
def create_weapon_item(attack: Attack, actor_name: str) -> FoundryItem:
    """Convert Attack to FoundryVTT weapon item."""

    return FoundryItem(
        _id=_generate_id(attack.name),
        name=attack.name,
        type="weapon",
        img=_get_weapon_icon(attack.attack_type),
        system={
            "type": {"value": "natural", "baseItem": ""},
            "damage": {
                "base": {
                    "number": attack.damage[0].number,
                    "denomination": attack.damage[0].denomination,
                    "bonus": attack.damage[0].bonus,
                    "types": [attack.damage[0].type],
                    "scaling": {"number": 1}
                }
            },
            "range": {
                "reach": attack.reach,
                "value": attack.range_short,
                "long": attack.range_long,
                "units": "ft"
            },
            "activities": {
                _generate_id("attack"): _create_attack_activity(attack)
            }
        }
    )

def parsed_to_foundry(data: ParsedActorData) -> FoundryActor:
    """Convert ParsedActorData to FoundryVTT actor."""

    items = []

    # Create weapon items for attacks
    for attack in data.attacks:
        items.append(create_weapon_item(attack, data.name))

    # Create feat items for traits
    for trait in data.traits:
        items.append(create_feat_item(trait))

    return FoundryActor(
        name=data.name,
        system=_build_system_data(data),
        items=items
    )
```

---

## File Structure

```
src/actors/
├── models.py                 # StatBlock (existing - minimal changes)
├── parsed_models.py          # ParsedActorData, Attack, Trait, etc. (NEW)
├── extract_stat_blocks.py    # Extract from XML (existing)
├── parse_stat_blocks.py      # Basic parsing with Gemini (existing)
├── parse_detailed.py         # Detailed parsing (NEW)
└── __init__.py

src/foundry/
├── client.py                 # FoundryClient (existing)
├── actors.py                 # ActorManager (existing - refactor)
├── foundry_models.py         # Type-safe FoundryVTT structures (NEW)
├── convert_to_foundry.py     # ParsedActorData → FoundryActor (NEW)
└── __init__.py

tests/actors/
├── fixtures/
│   ├── sample_stat_block.txt         # Goblin (existing)
│   ├── complex_stat_block.txt        # Pit Fiend (NEW)
│   ├── parsed_goblin.json            # Expected ParsedActorData (NEW)
│   └── foundry_goblin.json           # Expected FoundryActor (NEW)
├── test_parse_detailed.py            # Test Gemini parsing (NEW)
└── test_convert_to_foundry.py        # Test conversion (NEW)
```

---

## Error Handling

### Stage 1: StatBlock Extraction
**Errors**: Missing required fields (AC, HP, CR)
**Action**: Raise `ValidationError`, skip creature

### Stage 2: Detailed Parsing
**Errors**: Gemini returns malformed JSON, missing fields
**Action**: Raise `ParsingError` with context, fail fast (v1)

### Stage 3: FoundryVTT Conversion
**Errors**: Invalid enum values, missing required FoundryVTT fields
**Action**: Raise `ConversionError`, log detailed error

**Future**: Graceful degradation (create partial actor, log warnings)

---

## Testing Strategy

### Unit Tests
1. **test_parse_detailed.py**: Mock Gemini, test JSON → ParsedActorData
2. **test_convert_to_foundry.py**: Test ParsedActorData → FoundryActor (pure functions)

### Integration Tests
1. **test_full_pipeline.py**: StatBlock → ParsedActorData → FoundryActor (real Gemini)
2. **test_foundry_upload.py**: Upload actor, verify in FoundryVTT (requires running instance)

### Validation Tests
1. Load `data/foundry_examples/pit_fiend.json`
2. Convert to `ParsedActorData`
3. Convert back to FoundryActor
4. Assert deep equality (round-trip validation)

---

## Implementation Plan

### Phase 1: Models (Week 1)
1. Create `src/actors/parsed_models.py`
2. Create `src/foundry/foundry_models.py`
3. Write Pydantic schemas for all models
4. Create test fixtures

### Phase 2: Detailed Parser (Week 2)
1. Implement `parse_detailed.py`
2. Design Gemini prompt
3. Test with Goblin stat block
4. Validate against expected JSON

### Phase 3: FoundryVTT Converter (Week 2)
1. Implement `convert_to_foundry.py`
2. Create item builders (weapon, feat, spell)
3. Test round-trip conversion
4. Validate against real FoundryVTT actors

### Phase 4: Integration (Week 3)
1. Update `process_actors.py` to use new pipeline
2. Test with full module (Lost Mine of Phandelver)
3. Upload to FoundryVTT
4. Manual validation (click attacks, verify damage rolls)

---

## Open Questions

1. **Effect IDs**: How to handle status effect references? Generate UUIDs or use FoundryVTT compendium IDs?
2. **Icon paths**: Hardcode icon mappings or use default FoundryVTT icons?
3. **Multiattack parsing**: Store as text or attempt to parse attack combinations?
4. **Spellcasting**: Handle in v1 or defer to v2?
5. **Storage**: Cache `ParsedActorData` as JSON or regenerate on demand?

---

## Success Criteria

### Minimum Viable Product (v1)
- ✅ Parse basic attacks (melee, ranged)
- ✅ Parse simple traits (passive abilities)
- ✅ Create weapon items with attack activities
- ✅ Create feat items for traits
- ✅ Populate damage resistances/immunities
- ✅ Upload to FoundryVTT
- ✅ Verify clickable attacks work

### Stretch Goals (v2)
- Parse reactions with triggers
- Parse multiattack as structured rules
- Handle legendary actions
- Parse innate spellcasting
- Support lair actions
- Add status effect generation

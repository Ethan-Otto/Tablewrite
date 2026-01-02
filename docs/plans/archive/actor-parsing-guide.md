# Actor Parsing Guide

## Overview

The actor parsing system converts D&D 5e stat blocks into FoundryVTT actor JSON format. It transforms raw stat block text into structured data with proper FoundryVTT item types, compendium links, and usage tracking.

## Supported Features

### Basic Stats
- **Abilities**: STR, DEX, CON, INT, WIS, CHA
- **Armor Class**: Natural armor and calculations
- **Hit Points**: Current/max HP and hit dice
- **Challenge Rating**: CR value for XP calculation
- **Saving Throw Proficiencies**: Proficient saves
- **Movement Speeds**: walk, fly, swim, burrow, climb
- **Senses**: darkvision, blindsight, tremorsense, truesight
- **Languages**: Known languages and telepathy
- **Condition Immunities**: Poison, charm, etc.

### Combat Features
- **Attacks** → Weapon items
  - Melee and ranged attacks
  - Attack bonus, reach/range
  - Multiple damage formulas (e.g., 2d6+8 piercing + 3d6 fire)
  - Damage types (piercing, slashing, bludgeoning, fire, etc.)

- **Multiattack** → Feat item
  - Parses "Multiattack" action sections
  - Extracts number of attacks
  - Creates feat with action activation

- **Traits** → Feat items
  - Special abilities (Magic Resistance, Pack Tactics, etc.)
  - Passive or activated traits
  - Full text descriptions

### Spellcasting
- **Regular Spellcasting** → Spell items with levels
  - Prepared spell lists
  - Spell slots by level
  - Spellcasting ability and save DC

- **Innate Spellcasting** → Feat + Spell items
  - Supports frequency: "at will", "3/day", "1/day"
  - Automatically looks up spell UUIDs from FoundryVTT compendium
  - Preserves spell levels and schools
  - Tracks limited uses per day
  - Creates summary feat describing innate spellcasting ability

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
    size="large",
    creature_type="fiend",
    creature_subtype="devil",
    alignment="lawful evil",
    armor_class=19,
    hit_points=300,
    hit_dice="24d10+168",
    challenge_rating=20,
    abilities={"STR": 26, "DEX": 14, "CON": 24, "INT": 22, "WIS": 18, "CHA": 24},
    saving_throw_proficiencies=["dex", "con", "wis"],
    speed_walk=30,
    speed_fly=60,
    truesight=120,
    languages=["Infernal", "Telepathy 120 ft."],
    condition_immunities=["poisoned"],
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
            name="Mace",
            attack_type="melee",
            attack_bonus=14,
            reach=10,
            damage=[
                DamageFormula(number=2, denomination=6, bonus="+8", type="bludgeoning"),
                DamageFormula(number=6, denomination=6, bonus="", type="fire")
            ]
        ),
    ]
)

# Convert to FoundryVTT format (with spell cache for UUIDs)
client = FoundryClient(target="local")
spell_cache = SpellCache(client)
spell_cache.load()  # Loads once per session

foundry_json = convert_to_foundry(actor_data, spell_cache=spell_cache)

# Upload to FoundryVTT
actor_uuid = client.actors.create_actor(foundry_json)
```

## Item Mapping

| Stat Block Element | FoundryVTT Item Type | Notes |
|--------------------|---------------------|-------|
| Attack | `weapon` | Melee/ranged attacks with damage formulas |
| Trait | `feat` | Special abilities (passive or activated) |
| Multiattack | `feat` | Action to make multiple attacks |
| Innate Spellcasting | `feat` + `spell` items | Feat describes ability, spells are separate items |
| Spell | `spell` | Regular prepared spells with levels |

## SpellCache Integration

The SpellCache automatically looks up spell UUIDs from the FoundryVTT compendium, avoiding manual UUID management:

```python
from foundry.actors.spell_cache import SpellCache
from foundry.client import FoundryClient

# Initialize and load cache
client = FoundryClient(target="local")
spell_cache = SpellCache(client)
spell_cache.load()  # Loads once per session (~5 seconds)

# Use in conversion
foundry_json = convert_to_foundry(actor_data, spell_cache=spell_cache)
```

### Benefits

- **Proper Spell UUIDs**: Links directly to FoundryVTT compendium entries
- **Correct Spell Levels**: Automatically populates spell level from compendium
- **School Information**: Includes spell school (evocation, conjuration, etc.)
- **No Manual Management**: No need to look up or hardcode UUIDs
- **Efficient Caching**: Loads all spells once, reuses for entire session

### How It Works

1. On first load, fetches all spells from FoundryVTT compendiums via API
2. Builds in-memory cache mapping spell names to UUIDs
3. During conversion, looks up each spell by name
4. If found, includes UUID and full spell data in item
5. If not found, creates spell item without UUID (still functional)

### Example Output

Without SpellCache:
```json
{
  "name": "Fireball",
  "type": "spell",
  "system": {
    "level": 0,
    "school": ""
  }
}
```

With SpellCache:
```json
{
  "name": "Fireball",
  "type": "spell",
  "uuid": "Compendium.dnd5e.spells.Item.ztgcdrWPshKRpFd0",
  "system": {
    "level": 3,
    "school": "evo"
  }
}
```

## Testing

### Unit Tests (Fast, No API Calls)

```bash
# Run all unit tests
uv run pytest tests/foundry/actors/ -v -m "not integration"

# Test specific features
uv run pytest tests/foundry/actors/test_multiattack.py -v
uv run pytest tests/foundry/actors/test_innate_spellcasting.py -v
```

### Integration Tests (Requires FoundryVTT)

```bash
# Run integration tests (requires FoundryVTT running locally)
uv run pytest tests/foundry/actors/ -v -m integration

# Test SpellCache with real FoundryVTT connection
uv run pytest tests/foundry/actors/test_innate_spellcasting.py::TestInnateSpellcastingConversion::test_looks_up_spell_uuids_from_cache -v

# Full Pit Fiend round-trip test
uv run pytest tests/foundry/actors/test_pit_fiend_integration.py -v
```

## Data Models

### ParsedActorData (src/foundry/actors/models.py)

The main model representing a fully parsed stat block:

```python
class ParsedActorData(BaseModel):
    """Fully parsed stat block ready for FoundryVTT conversion."""

    # Identity
    source_statblock_name: str
    name: str
    size: Optional[str] = None  # "tiny", "small", "medium", "large", "huge", "gargantuan"
    creature_type: Optional[str] = None  # "humanoid", "fiend", "beast", etc.
    creature_subtype: Optional[str] = None  # "goblinoid", "devil", etc.
    alignment: Optional[str] = None

    # Core Stats
    armor_class: int
    hit_points: int
    hit_dice: Optional[str] = None
    challenge_rating: float

    # Abilities
    abilities: Dict[str, int]  # STR, DEX, CON, INT, WIS, CHA
    saving_throw_proficiencies: List[str] = []

    # Movement
    speed_walk: Optional[int] = None
    speed_fly: Optional[int] = None
    speed_swim: Optional[int] = None
    speed_burrow: Optional[int] = None
    speed_climb: Optional[int] = None

    # Senses
    darkvision: Optional[int] = None
    blindsight: Optional[int] = None
    tremorsense: Optional[int] = None
    truesight: Optional[int] = None

    # Other
    languages: List[str] = []
    condition_immunities: List[str] = []

    # Combat Features
    attacks: List[Attack] = []
    multiattack: Optional[Multiattack] = None
    traits: List[Trait] = []

    # Spellcasting
    spells: List[Spell] = []
    innate_spellcasting: Optional[InnateSpellcasting] = None
```

### Attack (src/foundry/actors/models.py)

```python
class Attack(BaseModel):
    """A weapon attack."""
    name: str
    attack_type: Literal["melee", "ranged"]
    attack_bonus: int
    reach: Optional[int] = None  # Melee reach in feet
    range_normal: Optional[int] = None  # Ranged normal range
    range_long: Optional[int] = None  # Ranged long range
    damage: List[DamageFormula] = []
```

### DamageFormula (src/foundry/actors/models.py)

```python
class DamageFormula(BaseModel):
    """A damage dice formula (e.g., 2d6+8 piercing)."""
    number: int  # Number of dice
    denomination: int  # Die size (d4, d6, d8, etc.)
    bonus: str = ""  # Bonus ("+8", "-2", or "")
    type: str  # Damage type (piercing, fire, etc.)
```

### Multiattack (src/foundry/actors/models.py)

```python
class Multiattack(BaseModel):
    """Multiattack action."""
    name: str = "Multiattack"
    description: str
    num_attacks: Optional[int] = None
    activation: Literal["action", "bonus", "reaction", "passive"] = "action"
```

### InnateSpellcasting (src/foundry/actors/models.py)

```python
class InnateSpell(BaseModel):
    """An innate spell with usage frequency."""
    name: str
    frequency: str  # "at will", "3/day", "1/day", etc.
    uses: Optional[int] = None  # Max uses per day

class InnateSpellcasting(BaseModel):
    """Innate spellcasting ability."""
    ability: str  # "charisma", "intelligence", etc.
    save_dc: Optional[int] = None
    attack_bonus: Optional[int] = None
    spells: List[InnateSpell] = []
```

## Common Patterns

### Creating a Basic Creature

```python
from foundry.actors.models import ParsedActorData, Attack, DamageFormula

goblin = ParsedActorData(
    source_statblock_name="Goblin",
    name="Goblin",
    size="small",
    creature_type="humanoid",
    creature_subtype="goblinoid",
    alignment="neutral evil",
    armor_class=15,
    hit_points=7,
    hit_dice="2d6",
    challenge_rating=0.25,
    abilities={"STR": 8, "DEX": 14, "CON": 10, "INT": 10, "WIS": 8, "CHA": 8},
    speed_walk=30,
    darkvision=60,
    languages=["Common", "Goblin"],
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
```

### Adding Multiattack

```python
from foundry.actors.models import Multiattack

dragon = ParsedActorData(
    # ... basic stats ...
    multiattack=Multiattack(
        name="Multiattack",
        description="The dragon can use its Frightful Presence. It then makes three attacks: one with its bite and two with its claws.",
        num_attacks=3
    ),
    attacks=[...]  # Define bite and claw attacks
)
```

### Adding Innate Spellcasting

```python
from foundry.actors.models import InnateSpellcasting, InnateSpell

drow = ParsedActorData(
    # ... basic stats ...
    innate_spellcasting=InnateSpellcasting(
        ability="charisma",
        save_dc=11,
        spells=[
            InnateSpell(name="Dancing Lights", frequency="at will"),
            InnateSpell(name="Darkness", frequency="1/day", uses=1),
            InnateSpell(name="Faerie Fire", frequency="1/day", uses=1),
        ]
    )
)
```

## Error Handling

The parsing system includes robust error handling:

- **Missing Spell UUIDs**: If SpellCache can't find a spell, still creates functional spell item without UUID
- **Invalid Damage Formulas**: Validates dice notation during model creation
- **Missing Required Fields**: Pydantic validates all required fields are present
- **Type Validation**: Ensures all fields match expected types (int, str, List, etc.)

## Performance

- **SpellCache Loading**: ~5 seconds to load all spells from FoundryVTT compendiums
- **Actor Conversion**: <100ms per actor (after SpellCache loaded)
- **Parallel Processing**: Can process multiple actors in parallel (SpellCache is thread-safe after loading)

## Future Enhancements

Planned features for future implementation:

1. **Legendary Actions** - Parse and convert legendary actions
2. **Lair Actions** - Parse lair action sections
3. **Reactions** - Parse and convert reactions (beyond basic reaction text)
4. **Source Book Tracking** - Add source.book and source.license fields
5. **Damage Resistances/Immunities** - Parse complex resistance/immunity/vulnerability text
6. **Skills** - Parse skill proficiencies and bonuses
7. **Condition Immunities** - More comprehensive condition parsing
8. **Equipment** - Parse carried equipment and magic items

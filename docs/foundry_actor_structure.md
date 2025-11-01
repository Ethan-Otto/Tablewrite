# FoundryVTT Actor Structure Analysis

**Date**: 2025-10-31
**Sources**: `data/foundry_examples/pit_fiend.json`, `mage_actor.json`

## Top-Level Structure

```json
{
  "name": "Pit Fiend",
  "type": "npc",
  "img": "systems/dnd5e/tokens/fiend/PitFiend.webp",
  "system": { ... },           // Core stats and attributes
  "items": [ ... ],            // Attacks, traits, spells as Item documents
  "effects": [],               // Active effects
  "prototypeToken": { ... },   // Token configuration
  "flags": { ... }             // System-specific metadata
}
```

## system.* Hierarchy (Core Stats)

### system.abilities
- **6 abilities**: str, dex, con, int, wis, cha
- **Each contains**:
  - `value`: Ability score (8-30)
  - `proficient`: 0 (none), 1 (proficient), 2 (expertise) for saving throws
  - `bonuses`: {check: "", save: ""}
  - `max`: null
  - `check`: {roll: {min, max, mode}}
  - `save`: {roll: {min, max, mode}}

### system.attributes
- **ac**: {flat: 21, calc: "natural"}
- **hp**: {value: 337, max: 337, temp: null, tempmax: null, formula: "27d10 + 189"}
- **init**: {ability: "", bonus: "@prof * 2", roll: {...}}
- **movement**: {burrow, climb, fly, swim, walk, units, hover}
- **senses**: {darkvision, blindsight, tremorsense, truesight, units, special}
- **spellcasting**: "cha" | "int" | "wis" (primary spellcasting ability)
- **concentration**: {ability, roll, bonuses, limit}
- **death**: {roll, success, failure, bonuses}
- **spell**: {level: 0} (spellcaster level)

### system.details
- **biography**: {value: "<h1>...</h1>", public: ""}
- **alignment**: "Lawful Evil"
- **type**: {value: "fiend", custom: "", subtype: "Devil", swarm: ""}
- **cr**: 20 (challenge rating as number)
- **habitat**: {value: [{type: "planar", subtype: "nine hells"}], custom: ""}
- **treasure**: {value: ["relics"]}

### system.traits
- **size**: "lg" | "med" | "sm" | "tiny" | "huge" | "grg"
- **di**: {value: ["fire", "poison"], bypasses: [], custom: ""} (damage immunities)
- **dr**: {value: ["cold"], bypasses: [], custom: ""} (damage resistances)
- **dv**: {value: [], bypasses: [], custom: ""} (damage vulnerabilities)
- **dm**: {amount: {}, bypasses: []} (damage modification)
- **ci**: {value: ["poisoned"], custom: ""} (condition immunities)
- **languages**: {value: ["infernal"], custom: "", communication: {telepathy: {value: 120, units: "ft"}}}

### system.skills
- **18 skills** (acr, ani, arc, ath, dec, his, ins, itm, inv, med, nat, prc, prf, per, rel, slt, ste, sur)
- **Each contains**:
  - `value`: 0 (none), 1 (proficient), 2 (expertise)
  - `ability`: "str" | "dex" | "con" | "int" | "wis" | "cha"
  - `bonuses`: {check: "", passive: ""}
  - `roll`: {min, max, mode}

### system.spells
- **spell1-9**: {value: 0, override: null} (spell slots per level)
- **pact**: {value: 0, override: null} (warlock pact slots)

### system.resources
- **legact**: {value: 0, max: 0} (legendary actions)
- **legres**: {value: 4, max: 4} (legendary resistance uses)
- **lair**: {value: false, initiative: null, inside: false}

## items[] Array (Attacks, Traits, Spells)

### Item Types

1. **weapon** (attacks)
2. **feat** (traits, features)
3. **spell** (spells)

### Common Item Fields
```json
{
  "_id": "mmBite0000000000",
  "name": "Bite",
  "type": "weapon" | "feat" | "spell",
  "img": "icons/path/to/image.webp",
  "folder": "folder_id",
  "system": { ... },      // Type-specific data
  "effects": [ ... ],     // Status effects applied
  "flags": {},
  "_stats": {},
  "ownership": {},
  "sort": 0
}
```

### Weapon Item Structure
```json
{
  "type": "weapon",
  "system": {
    "description": {
      "value": "<p>[[/attack extended]]. [[/damage average extended]].</p>",
      "chat": ""
    },
    "type": {
      "value": "natural" | "simpleM" | "martialR",
      "baseItem": "dagger" | ""
    },
    "damage": {
      "base": {
        "number": 3,           // Dice count
        "denomination": 6,     // Dice size (d6)
        "bonus": "",
        "types": ["piercing"],
        "scaling": {number: 1}
      },
      "versatile": { ... }
    },
    "range": {
      "value": 20,    // Short range
      "long": 60,     // Long range
      "reach": 10,    // Melee reach
      "units": "ft"
    },
    "properties": ["fin", "lgt", "thr"],  // Weapon properties
    "equipped": true,

    "activities": {
      "attack_activity_id": {
        "type": "attack",
        "activation": {type: "action", value: null},
        "attack": {
          "ability": "",
          "bonus": "",
          "critical": {threshold: null},
          "type": {value: "", classification: "weapon"}
        },
        "damage": {
          "critical": {bonus: ""},
          "includeBase": true,
          "parts": []  // Additional damage (e.g., poison)
        }
      },
      "save_activity_id": {
        "type": "save",
        "save": {
          "ability": ["con"],
          "dc": {calculation: "cha", formula: "8 + @mod + @prof"}
        },
        "effects": [{_id: "effect_id", onSave: false}]
      }
    }
  }
}
```

### Feat Item Structure (Traits)
```json
{
  "type": "feat",
  "system": {
    "type": {value: "monster", subtype: ""},
    "description": {
      "value": "<p>The pit fiend emanates an aura...</p>",
      "chat": ""
    },
    "identifier": "fear-aura",
    "properties": ["trait"],  // or []
    "requirements": "",

    "activities": {
      "save_activity_id": {
        "type": "save",
        "target": {
          "template": {type: "radius", size: "20", units: "ft"},
          "affects": {type: "enemy", count: "", special: "any enemy that starts its turn"}
        },
        "save": {
          "ability": ["wis"],
          "dc": {calculation: "cha", formula: "8 + @mod + @prof"}
        },
        "effects": [{_id: "frightened_effect", onSave: false}]
      }
    },

    "uses": {
      "spent": 0,
      "recovery": [],
      "max": ""
    }
  }
}
```

### Spell Item Structure
```json
{
  "type": "spell",
  "system": {
    "description": {value: "<p>A bright streak...</p>"},
    "level": 3,
    "school": "evo",
    "properties": ["vocal", "somatic", "material", "concentration"],
    "materials": {value: "a ball of bat guano", consumed: false, cost: 0},
    "preparation": {mode: "prepared", prepared: false},

    "activities": {
      "cast_activity_id": {
        "type": "save",
        "activation": {type: "action", value: null},
        "target": {
          "template": {type: "sphere", size: "20", units: "ft"},
          "affects": {type: "creature"}
        },
        "damage": {
          "onSave": "half",
          "parts": [{
            "number": 8,
            "denomination": 6,
            "bonus": "",
            "types": ["fire"],
            "scaling": {mode: "whole", number: 1}
          }]
        },
        "save": {
          "ability": ["dex"],
          "dc": {calculation: "spellcasting", formula: ""}
        }
      }
    }
  }
}
```

## Key Observations

### 1. Items vs. System Data
- **system.abilities/attributes/traits**: Core stats
- **items[]**: Actionable abilities (attacks, spells, features)

### 2. Activities Pattern
- **Items contain activities** (not direct actions)
- **Activity types**: attack, save, damage, utility, cast
- **Each activity**: Independent action with own activation, target, damage, effects

### 3. Damage Structure
- **Dice formula**: number × d{denomination} + bonus
- **Multiple parts**: Base damage + additional damage types
- **Scaling**: For spells and monster abilities

### 4. Saving Throws
- **DC calculation**: "spellcasting" | "cha" | "str" | etc.
- **Formula**: "8 + @mod + @prof" or custom
- **Linked to effects**: Status conditions applied on failure

### 5. Effects System
- **Separate documents**: Referenced by _id in activities
- **Status conditions**: frightened, poisoned, paralyzed, etc.
- **Duration**: rounds, turns, seconds, or until save

### 6. Proficiencies
- **Abilities**: 0 = not proficient, 1 = proficient (saving throws)
- **Skills**: 0 = not proficient, 1 = proficient, 2 = expertise
- **Value-based**: Not boolean flags

## Critical Insights

### What Makes an Actor "Mechanically Complete"?

1. **Base stats populated** (abilities, AC, HP, CR)
2. **Items for each action**:
   - Weapon items for attacks
   - Feat items for traits
   - Spell items for spells
3. **Activities within items**:
   - Attack activities with damage formulas
   - Save activities with DCs
   - Effects linked to conditions
4. **Proper damage formulas**: Dice notation, types, scaling
5. **Targeting data**: Range, reach, area of effect

### Current Implementation Gap

**We populate**: system.abilities, system.attributes (partial), system.details (partial)

**We're missing**:
- system.traits (resistances, immunities)
- system.skills (proficiencies)
- items[] array (ALL attacks, traits, spells)
- activities within items
- effects for status conditions

**Impact**: Actors display in FoundryVTT but have no clickable actions or automated mechanics.

# Actor Parsing Architecture Design

**Date**: 2025-10-31
**Status**: Design Phase - Brainstorming

## Problem Statement

Current actor implementation only creates basic FoundryVTT actors with:
- Basic stats (AC, HP, abilities, CR)
- Biography as raw HTML text

**Missing**: Mechanically functional actors with clickable attacks, traits, and spells as Items.

## Design Decisions (Agreed)

### 1. Architecture Pattern: **Composition over Inheritance**
- `StatBlock` remains simple (extraction from PDFs)
- `StatBlockDetailed` references `StatBlock` (not extends)
- FoundryVTT conversion as separate transformation layer

### 2. Parsing Strategy: **Hybrid Gemini + Python**
- **Gemini**: Parse complex structures (attacks, traits, spell descriptions)
- **Python**: Basic validation (stats, proficiencies, enums)
- **Rationale**: Gemini excels at natural language, Python ensures type safety

### 3. Error Handling: **Fail Fast (v1)**
- Throw exceptions on parsing failures
- No fallback to partial data (yet)
- **Future**: Graceful degradation (keep what works, log what failed)

### 4. Scope Limitations (v1)

**In Scope:**
- Basic attacks (melee, ranged)
- Simple traits (passive abilities)
- Multiattack labels (e.g., "makes two claw attacks")
- Damage resistances/immunities/vulnerabilities
- Condition immunities
- Skill proficiencies

**Out of Scope (v1):**
- Legendary actions
- Lair actions
- Mythic traits
- Complex spellcasting (innate vs prepared)
- Reactions (beyond basic parsing)

**Rationale**: Cover 80% of stat blocks with 20% of complexity

### 5. Data Flow: **One-Way Pipeline**

```
PDF → StatBlock (basic) → StatBlockDetailed (gemini parse) → FoundryVTT JSON
```

**No round-tripping**: FoundryVTT edits don't sync back to StatBlock
**Validation needed**: For testing conversions

## Next Steps

1. **Analyze FoundryVTT Structure**: Document fields and hierarchy from examples (pit_fiend.json, mage_actor.json)
2. **Propose Data Models**: Define `StatBlockDetailed`, `Attack`, `Trait`, etc.
3. **Design Conversion**: Map detailed models → FoundryVTT JSON structure
4. **Prototype**: Build POC with Goblin example
5. **Test**: Validate against real FoundryVTT actors

## Open Questions

- How to handle multiattack descriptions? (Store as text label or parse into structured rules?)
- Validation strategy: Pre-conversion or post-conversion checks?
- Storage format: JSON files or database?
- Caching: Store `StatBlockDetailed` or regenerate on demand?

## References

- Example actors: `data/foundry_examples/pit_fiend.json`, `mage_actor.json`
- Current implementation: `src/foundry/actors.py:85-161`
- Current models: `src/actors/models.py:7-65`

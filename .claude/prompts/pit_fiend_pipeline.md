# Pit Fiend Full Pipeline Test

This prompt guides Claude through processing the Pit Fiend statblock through the complete actor pipeline.

## Instructions

Follow these steps in order:

### 1. Parse the Pit Fiend Statblock

Read `/Users/ethanotto/Documents/Projects/dnd_module_gen/data/foundry_examples/pit_fiend.txt` and create a complete `ParsedActorData` object based on the statblock.

**Key Details to Extract:**
- **Basic Stats**: name, size, type, alignment, AC, HP, speed, abilities
- **Saving Throws**: DEX +8, CON +13, WIS +10
- **Immunities/Resistances**: Parse damage resistances, immunities, condition immunities
- **Senses**: Truesight 120 ft
- **Languages**: Infernal, Telepathy 120 ft
- **Challenge Rating**: 20

**Traits:**
- Fear Aura (save DC 21 WIS)
- Magic Resistance
- Magic Weapons

**Innate Spellcasting:**
- At will: detect magic, fireball
- 3/day each: hold monster, wall of fire
- Spell save DC: 21
- Ability: Charisma

**Multiattack:**
- Four attacks: bite, claw, mace, tail

**Attacks:**
1. **Bite** (+14, reach 5 ft): 4d6+8 piercing + **poison save** (DC 21 CON, 6d6 poison per turn, can't regain HP)
2. **Claw** (+14, reach 10 ft): 2d8+8 slashing
3. **Mace** (+14, reach 10 ft): 2d6+8 bludgeoning + 6d6 fire
4. **Tail** (+14, reach 10 ft): 3d10+8 bludgeoning

### 2. Create Processing Script

Create a script at `scripts/process_pit_fiend.py` that:
1. Defines the complete `ParsedActorData` object (with all attacks, traits, spells)
2. Converts to FoundryVTT format using `convert_to_foundry()`
3. Uploads to FoundryVTT using `FoundryClient`
4. Downloads the actor back
5. Saves to `output/pit_fiend_roundtrip.json` with pretty formatting

**CRITICAL**: The Bite attack must include an `AttackSave` with:
- `ability="con"`
- `dc=21`
- `ongoing_damage=[DamageFormula(number=6, denomination=6, bonus="", type="poison")]`
- `duration_rounds=None` (repeats until success)
- `effect_description="Poisoned - can't regain HP"`

### 3. Run the Script

Execute the script with:
```bash
uv run python scripts/process_pit_fiend.py
```

### 4. Verify Output

After running, verify:
- Actor was created successfully in FoundryVTT
- Downloaded JSON contains all 13 items (4 weapons + 5 feats + 4 spells)
- Bite weapon has 3 activities (attack + save + ongoing damage)
- Output file `output/pit_fiend_roundtrip.json` exists and is well-formatted

### 5. Report Results

Report:
- Actor UUID in FoundryVTT
- Total items count
- Activities count for each weapon
- Any differences between uploaded and downloaded data
- Location of saved JSON file

## Success Criteria

- [ ] ParsedActorData object created with all fields from statblock
- [ ] Script created and saved to `scripts/process_pit_fiend.py`
- [ ] Script runs without errors
- [ ] Actor uploaded to FoundryVTT successfully
- [ ] Downloaded JSON saved to `output/pit_fiend_roundtrip.json`
- [ ] Bite weapon has 3 activities with correct damage.parts object structure
- [ ] All 13 items present in downloaded actor

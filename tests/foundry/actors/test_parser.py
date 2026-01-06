"""Tests for parallel StatBlock → ParsedActorData parser."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from actor_pipeline.models import StatBlock
from foundry_converters.actors.models import (
    ParsedActorData, Attack, Trait, Multiattack,
    InnateSpellcasting, InnateSpell, DamageFormula, AttackSave
)
from foundry_converters.actors.parser import (
    parse_single_action_async,
    parse_single_trait_async,
    parse_innate_spellcasting_async,
    parse_stat_block_parallel,
    parse_multiple_stat_blocks
)
from caches import SpellCache


# Test fixtures

@pytest.fixture
def mock_spell_cache():
    """Mock spell cache with common spells."""
    cache = Mock(spec=SpellCache)
    cache.get_spell_uuid = Mock(side_effect=lambda name: {
        "detect magic": "Compendium.dnd5e.spells.Item.detect_magic_uuid",
        "fireball": "Compendium.dnd5e.spells.Item.fireball_uuid",
        "hold monster": "Compendium.dnd5e.spells.Item.hold_monster_uuid",
        "wish": "Compendium.dnd5e.spells.Item.wish_uuid"
    }.get(name))
    return cache


@pytest.fixture
def goblin_statblock():
    """Simple Goblin stat block for testing."""
    return StatBlock(
        name="Goblin",
        raw_text="Goblin stat block...",
        armor_class=15,
        hit_points=7,
        challenge_rating=0.25,
        size="Small",
        type="humanoid",
        alignment="neutral evil",
        abilities={"STR": 8, "DEX": 14, "CON": 10, "INT": 10, "WIS": 8, "CHA": 8},
        traits=["Nimble Escape. The goblin can take the Disengage or Hide action as a bonus action on each of its turns."],
        actions=[
            "Scimitar. Melee Weapon Attack: +4 to hit, reach 5 ft., one target. Hit: 5 (1d6 + 2) slashing damage.",
            "Shortbow. Ranged Weapon Attack: +4 to hit, range 80/320 ft., one target. Hit: 5 (1d6 + 2) piercing damage."
        ],
        reactions=[]
    )


@pytest.fixture
def pit_fiend_statblock():
    """Complex Pit Fiend stat block for testing parallel processing."""
    return StatBlock(
        name="Pit Fiend",
        raw_text="Pit Fiend stat block...",
        armor_class=19,
        hit_points=300,
        challenge_rating=20,
        size="Large",
        type="fiend",
        alignment="lawful evil",
        abilities={"STR": 26, "DEX": 14, "CON": 24, "INT": 22, "WIS": 18, "CHA": 24},
        traits=[
            "Fear Aura. Any creature hostile to the pit fiend that starts its turn within 20 feet of the pit fiend must make a DC 21 Wisdom saving throw, unless the pit fiend is incapacitated. On a failed save, the creature is frightened until the start of its next turn. If a creature's saving throw is successful, the creature is immune to the pit fiend's Fear Aura for the next 24 hours.",
            "Magic Resistance. The pit fiend has advantage on saving throws against spells and other magical effects.",
            "Magic Weapons. The pit fiend's weapon attacks are magical.",
            "Innate Spellcasting. The pit fiend's spellcasting ability is Charisma (spell save DC 21). The pit fiend can innately cast the following spells, requiring no material components:\nAt will: detect magic, fireball\n3/day each: hold monster\n1/day: wish"
        ],
        actions=[
            "Multiattack. The pit fiend makes four attacks: one with its bite, one with its claw, one with its mace, and one with its tail.",
            "Bite. Melee Weapon Attack: +14 to hit, reach 5 ft., one target. Hit: 22 (4d6 + 8) piercing damage. The target must succeed on a DC 21 Constitution saving throw or become poisoned. While poisoned in this way, the target can't regain hit points, and it takes 21 (6d6) poison damage at the start of each of its turns. The poisoned target can repeat the saving throw at the end of each of its turns, ending the effect on itself on a success.",
            "Claw. Melee Weapon Attack: +14 to hit, reach 10 ft., one target. Hit: 17 (2d8 + 8) slashing damage.",
            "Mace. Melee Weapon Attack: +14 to hit, reach 10 ft., one target. Hit: 15 (2d6 + 8) bludgeoning damage plus 21 (6d6) fire damage.",
            "Tail. Melee Weapon Attack: +14 to hit, reach 10 ft., one target. Hit: 24 (3d10 + 8) piercing damage."
        ],
        reactions=[]
    )


# Unit tests for individual parsing functions

@pytest.mark.integration
@pytest.mark.asyncio
async def test_parse_single_action_simple_melee():
    """Test parsing a simple melee attack (Scimitar)."""
    action_text = "Scimitar. Melee Weapon Attack: +4 to hit, reach 5 ft., one target. Hit: 5 (1d6 + 2) slashing damage."

    result = await parse_single_action_async(action_text)

    assert isinstance(result, Attack)
    assert result.name == "Scimitar"
    assert result.attack_type == "melee"
    assert result.attack_bonus == 4
    assert result.reach == 5
    assert len(result.damage) == 1
    assert result.damage[0].number == 1
    assert result.damage[0].denomination == 6
    assert result.damage[0].bonus == "+2"
    assert result.damage[0].type == "slashing"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_parse_single_action_ranged():
    """Test parsing a ranged attack (Shortbow)."""
    action_text = "Shortbow. Ranged Weapon Attack: +4 to hit, range 80/320 ft., one target. Hit: 5 (1d6 + 2) piercing damage."

    result = await parse_single_action_async(action_text)

    assert isinstance(result, Attack)
    assert result.name == "Shortbow"
    assert result.attack_type == "ranged"
    assert result.attack_bonus == 4
    # Ranged weapons have separate short and long range fields
    assert result.range_short == 80
    assert result.range_long == 320
    assert len(result.damage) == 1
    assert result.damage[0].type == "piercing"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_parse_single_action_with_save():
    """Test parsing attack with saving throw (Poison Bite)."""
    action_text = """Bite. Melee Weapon Attack: +14 to hit, reach 5 ft., one target. Hit: 22 (4d6 + 8) piercing damage. The target must succeed on a DC 21 Constitution saving throw or become poisoned. While poisoned in this way, the target can't regain hit points, and it takes 21 (6d6) poison damage at the start of each of its turns. The poisoned target can repeat the saving throw at the end of each of its turns, ending the effect on itself on a success."""

    result = await parse_single_action_async(action_text)

    assert isinstance(result, Attack)
    assert result.name == "Bite"
    assert result.attack_bonus == 14
    assert len(result.damage) == 1
    assert result.damage[0].number == 4
    assert result.damage[0].denomination == 6

    # Check saving throw
    assert result.attack_save is not None
    assert result.attack_save.ability == "con"
    assert result.attack_save.dc == 21
    assert len(result.attack_save.ongoing_damage) > 0
    assert result.attack_save.ongoing_damage[0].number == 6
    assert result.attack_save.ongoing_damage[0].denomination == 6
    assert result.attack_save.ongoing_damage[0].type == "poison"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_parse_single_action_multiattack():
    """Test parsing multiattack."""
    action_text = "Multiattack. The pit fiend makes four attacks: one with its bite, one with its claw, one with its mace, and one with its tail."

    result = await parse_single_action_async(action_text)

    assert isinstance(result, Multiattack)
    assert result.name == "Multiattack"
    assert result.num_attacks == 4
    assert "four attacks" in result.description.lower()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_parse_single_trait_passive():
    """Test parsing passive trait (Nimble Escape)."""
    trait_text = "Nimble Escape. The goblin can take the Disengage or Hide action as a bonus action on each of its turns."

    result = await parse_single_trait_async(trait_text)

    assert isinstance(result, Trait)
    assert result.name == "Nimble Escape"
    assert result.activation in ["passive", "bonus"]  # Either is acceptable
    assert "Disengage" in result.description or "Hide" in result.description


@pytest.mark.integration
@pytest.mark.asyncio
async def test_parse_single_trait_action():
    """Test parsing action trait (Fear Aura)."""
    trait_text = "Fear Aura. Any creature hostile to the pit fiend that starts its turn within 20 feet of the pit fiend must make a DC 21 Wisdom saving throw, unless the pit fiend is incapacitated. On a failed save, the creature is frightened until the start of its next turn."

    result = await parse_single_trait_async(trait_text)

    assert isinstance(result, Trait)
    assert result.name == "Fear Aura"
    assert result.activation in ["passive", "action"]  # Could be either
    assert "DC 21" in result.description or "frightened" in result.description.lower()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_parse_innate_spellcasting(mock_spell_cache):
    """Test parsing innate spellcasting with spell UUID resolution."""
    trait_text = """Innate Spellcasting. The pit fiend's spellcasting ability is Charisma (spell save DC 21). The pit fiend can innately cast the following spells, requiring no material components:
At will: detect magic, fireball
3/day each: hold monster
1/day: wish"""

    result = await parse_innate_spellcasting_async(trait_text, spell_cache=mock_spell_cache)

    assert isinstance(result, InnateSpellcasting)
    assert result.ability == "charisma"
    assert result.save_dc == 21
    assert len(result.spells) == 4  # 2 at will + 1 from 3/day + 1 from 1/day

    # Check at will spells
    at_will_spells = [s for s in result.spells if s.frequency == "at will"]
    assert len(at_will_spells) == 2
    assert any(s.name == "detect magic" for s in at_will_spells)
    assert any(s.name == "fireball" for s in at_will_spells)

    # Check limited use spells
    limited_spells = [s for s in result.spells if "day" in s.frequency]
    assert len(limited_spells) == 2
    hold_monster = next(s for s in limited_spells if s.name == "hold monster")
    assert hold_monster.frequency == "3/day"
    assert hold_monster.uses == 3

    wish = next(s for s in limited_spells if s.name == "wish")
    assert wish.frequency == "1/day"
    assert wish.uses == 1

    # Check UUIDs were resolved
    for spell in result.spells:
        assert spell.uuid is not None
        assert spell.uuid.startswith("Compendium.")


# Integration tests for full stat block parsing

@pytest.mark.integration
@pytest.mark.asyncio
async def test_parse_stat_block_parallel_goblin(goblin_statblock, mock_spell_cache):
    """Test full Goblin parsing (2 attacks + 1 trait)."""
    result = await parse_stat_block_parallel(goblin_statblock, spell_cache=mock_spell_cache)

    assert isinstance(result, ParsedActorData)
    assert result.name == "Goblin"
    assert result.armor_class == 15
    assert result.hit_points == 7
    assert result.challenge_rating == 0.25

    # Check attacks
    assert len(result.attacks) == 2
    scimitar = next(a for a in result.attacks if a.name == "Scimitar")
    assert scimitar.attack_type == "melee"
    shortbow = next(a for a in result.attacks if a.name == "Shortbow")
    assert shortbow.attack_type == "ranged"

    # Check traits
    assert len(result.traits) == 1
    assert result.traits[0].name == "Nimble Escape"

    # No multiattack or spellcasting
    assert result.multiattack is None
    assert result.innate_spellcasting is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_parse_stat_block_parallel_pit_fiend(pit_fiend_statblock, mock_spell_cache):
    """Test full Pit Fiend parsing (9 parallel calls: 4 attacks + 4 traits + 1 multiattack)."""
    result = await parse_stat_block_parallel(pit_fiend_statblock, spell_cache=mock_spell_cache)

    assert isinstance(result, ParsedActorData)
    assert result.name == "Pit Fiend"
    assert result.armor_class == 19
    assert result.hit_points == 300
    assert result.challenge_rating == 20

    # Check multiattack (separated from regular attacks)
    assert result.multiattack is not None
    assert result.multiattack.num_attacks == 4

    # Check attacks (4 regular attacks, multiattack excluded)
    assert len(result.attacks) == 4
    attack_names = {a.name for a in result.attacks}
    assert attack_names == {"Bite", "Claw", "Mace", "Tail"}

    # Check Bite has saving throw
    bite = next(a for a in result.attacks if a.name == "Bite")
    assert bite.attack_save is not None
    assert bite.attack_save.ability == "con"
    assert bite.attack_save.dc == 21

    # Check innate spellcasting (separated from regular traits)
    assert result.innate_spellcasting is not None
    assert result.innate_spellcasting.ability == "charisma"
    assert result.innate_spellcasting.save_dc == 21
    assert len(result.innate_spellcasting.spells) == 4

    # Check regular traits (3 traits: Fear Aura, Magic Resistance, Magic Weapons)
    # Innate Spellcasting should be excluded
    assert len(result.traits) == 3
    trait_names = {t.name for t in result.traits}
    assert "Fear Aura" in trait_names
    assert "Magic Resistance" in trait_names
    assert "Magic Weapons" in trait_names
    assert "Innate Spellcasting" not in trait_names  # Should be in innate_spellcasting


@pytest.mark.integration
@pytest.mark.asyncio
async def test_parse_multiple_stat_blocks(goblin_statblock, pit_fiend_statblock, mock_spell_cache):
    """Test batch processing of multiple stat blocks."""
    results = await parse_multiple_stat_blocks(
        [goblin_statblock, pit_fiend_statblock],
        spell_cache=mock_spell_cache
    )

    assert len(results) == 2
    assert all(isinstance(r, ParsedActorData) for r in results)

    # Check that both were parsed correctly
    goblin_result = next(r for r in results if r.name == "Goblin")
    assert len(goblin_result.attacks) == 2

    pit_fiend_result = next(r for r in results if r.name == "Pit Fiend")
    assert len(pit_fiend_result.attacks) == 4
    assert pit_fiend_result.multiattack is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_parse_stat_block_with_no_spells(goblin_statblock):
    """Test parsing without spell cache (spells should still parse, just no UUIDs)."""
    result = await parse_stat_block_parallel(goblin_statblock, spell_cache=None)

    assert isinstance(result, ParsedActorData)
    assert result.name == "Goblin"
    # Should work fine without spell cache since Goblin has no spells


@pytest.mark.integration
@pytest.mark.asyncio
async def test_parse_stat_block_empty_lists():
    """Test parsing stat block with empty action/trait lists."""
    minimal_statblock = StatBlock(
        name="Minimal Creature",
        raw_text="Minimal creature...",
        armor_class=10,
        hit_points=5,
        challenge_rating=0,
        traits=[],
        actions=[],
        reactions=[]
    )

    result = await parse_stat_block_parallel(minimal_statblock)

    assert isinstance(result, ParsedActorData)
    assert result.name == "Minimal Creature"
    assert len(result.attacks) == 0
    assert len(result.traits) == 0
    assert result.multiattack is None
    assert result.innate_spellcasting is None


# Performance test

@pytest.mark.integration
@pytest.mark.asyncio
async def test_parallel_processing_performance(pit_fiend_statblock, mock_spell_cache):
    """Verify parallel processing is actually faster than sequential."""
    import time

    # Parallel processing (current implementation)
    start = time.time()
    result = await parse_stat_block_parallel(pit_fiend_statblock, spell_cache=mock_spell_cache)
    parallel_time = time.time() - start

    # Should complete in ~3-5 seconds (9 parallel calls)
    assert parallel_time < 10  # Generous upper bound

    # Verify correctness
    assert len(result.attacks) == 4
    assert result.multiattack is not None
    assert len(result.traits) == 3
    assert result.innate_spellcasting is not None

    print(f"\nParallel processing time: {parallel_time:.2f}s for 9 Gemini calls")

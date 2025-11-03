"""Integration test for Pit Fiend with all features."""

import pytest
from dotenv import load_dotenv
from pathlib import Path

from foundry.actors.models import (
    ParsedActorData, Attack, Trait, DamageFormula,
    Multiattack, InnateSpellcasting, InnateSpell, AttackSave
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
        spell_cache = SpellCache()
        spell_cache.load()
        return spell_cache

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
                    ],
                    # NEW: Add saving throw for poison
                    attack_save=AttackSave(
                        ability="con",
                        dc=21,
                        ongoing_damage=[DamageFormula(number=6, denomination=6, bonus="", type="poison")],
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

        # Verify all weapons are present (not just count)
        uploaded_weapons = {i["name"] for i in foundry_json["items"] if i["type"] == "weapon"}
        downloaded_weapons = {i["name"] for i in downloaded["items"] if i["type"] == "weapon"}
        assert uploaded_weapons == downloaded_weapons, f"Weapons lost: {uploaded_weapons - downloaded_weapons}"

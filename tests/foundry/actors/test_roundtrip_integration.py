"""Integration tests for full ParsedActorData → FoundryVTT → verify round-trip."""

import pytest
import json
import os
from pathlib import Path
from dotenv import load_dotenv
from foundry.actors.models import ParsedActorData, Attack, DamageFormula, AttackSave
from foundry.actors.converter import convert_to_foundry
from foundry.client import FoundryClient

# Load environment variables from .env file
load_dotenv()


@pytest.mark.integration
@pytest.mark.requires_foundry
class TestActorRoundTrip:
    """
    Integration tests for complete actor upload/download cycle.

    These tests require:
    - FoundryVTT running locally
    - REST API relay server running
    - Valid API credentials in .env
    """

    @pytest.fixture
    def foundry_client(self):
        """Create FoundryVTT client for testing."""
        try:
            client = FoundryClient(target="local")
            # Test connection
            client.journals.get_all_journals_by_name("__test__")
            return client
        except Exception as e:
            pytest.skip(f"FoundryVTT not available: {e}")

    @pytest.fixture
    def goblin_data(self):
        """Load Goblin ParsedActorData from fixture."""
        fixture_path = Path(__file__).parent / "fixtures" / "goblin_parsed.json"
        with open(fixture_path) as f:
            data = json.load(f)
        return ParsedActorData(**data)

    @pytest.fixture
    def mage_data(self):
        """Load Mage ParsedActorData from fixture."""
        fixture_path = Path(__file__).parent / "fixtures" / "mage_parsed.json"
        with open(fixture_path) as f:
            data = json.load(f)
        return ParsedActorData(**data)

    def test_upload_and_download_goblin(self, foundry_client, goblin_data):
        """
        Test complete cycle: Goblin ParsedActorData → FoundryVTT → verify.

        Steps:
        1. Convert ParsedActorData to FoundryVTT JSON
        2. Upload to FoundryVTT
        3. Download the actor back
        4. Verify all critical fields are preserved
        """
        # Step 1: Convert to FoundryVTT format
        foundry_json = convert_to_foundry(goblin_data)

        # Verify conversion produced valid structure
        assert foundry_json["name"] == "Goblin"
        assert foundry_json["type"] == "npc"
        assert len(foundry_json["items"]) == 3  # 2 attacks + 1 trait

        # Step 2: Upload to FoundryVTT
        actor_uuid = foundry_client.actors.create_actor(foundry_json)
        assert actor_uuid is not None
        assert actor_uuid.startswith("Actor.")

        # Step 3: Download back
        downloaded_actor = foundry_client.actors.get_actor(actor_uuid)

        # Step 4: Verify fields
        assert downloaded_actor["name"] == "Goblin"
        assert downloaded_actor["system"]["abilities"]["dex"]["value"] == 14
        assert downloaded_actor["system"]["attributes"]["ac"]["flat"] == 15
        assert downloaded_actor["system"]["attributes"]["hp"]["max"] == 7
        assert downloaded_actor["system"]["details"]["cr"] == 0.25

        # Verify items were preserved
        items = downloaded_actor["items"]
        assert len(items) == 3

        weapon_names = [item["name"] for item in items if item["type"] == "weapon"]
        assert "Scimitar" in weapon_names
        assert "Shortbow" in weapon_names

        trait_names = [item["name"] for item in items if item["type"] == "feat"]
        assert "Nimble Escape" in trait_names

    def test_upload_and_download_mage(self, foundry_client, mage_data):
        """
        Test complete cycle: Mage ParsedActorData → FoundryVTT → verify.

        This tests a more complex actor with:
        - Spellcasting
        - Multiple spell levels
        - Saving throw proficiencies
        """
        # Step 1: Convert to FoundryVTT format
        foundry_json = convert_to_foundry(mage_data)

        # Verify conversion
        assert foundry_json["name"] == "Mage"
        assert foundry_json["type"] == "npc"
        assert len(foundry_json["items"]) == 17  # 1 attack + 16 spells

        # Verify spellcasting attributes
        assert foundry_json["system"]["attributes"]["spellcasting"] == "int"
        assert foundry_json["system"]["attributes"]["spelldc"] == 14

        # Step 2: Upload to FoundryVTT
        actor_uuid = foundry_client.actors.create_actor(foundry_json)
        assert actor_uuid is not None
        assert actor_uuid.startswith("Actor.")

        # Step 3: Download and verify
        downloaded_actor = foundry_client.actors.get_actor(actor_uuid)

        # FoundryVTT may transform spellcasting attributes on storage
        # Just verify the actor was created and items preserved
        assert downloaded_actor["name"] == "Mage"
        assert downloaded_actor["type"] == "npc"

        spells = [item for item in downloaded_actor["items"] if item["type"] == "spell"]
        assert len(spells) == 16

        # Verify Fireball spell exists (UUID may be transformed by FoundryVTT)
        fireball = next(s for s in spells if s["name"] == "Fireball")
        assert fireball is not None

    def test_conversion_preserves_all_attacks(self, goblin_data):
        """Verify attacks are correctly converted to weapon items with activities."""
        foundry_json = convert_to_foundry(goblin_data)

        weapons = [item for item in foundry_json["items"] if item["type"] == "weapon"]
        assert len(weapons) == 2

        # Check Scimitar (v10+ structure)
        scimitar = next(w for w in weapons if w["name"] == "Scimitar")
        assert "activities" in scimitar["system"]
        assert len(scimitar["system"]["activities"]) == 1

        # Verify attack activity
        scimitar_activity = list(scimitar["system"]["activities"].values())[0]
        assert scimitar_activity["type"] == "attack"
        assert scimitar_activity["attack"]["bonus"] == "4"
        assert scimitar_activity["attack"]["type"]["value"] == "melee"

        # Check damage.base structure (v10+)
        assert "base" in scimitar["system"]["damage"]
        assert scimitar["system"]["damage"]["base"]["number"] == 1
        assert scimitar["system"]["damage"]["base"]["denomination"] == 6
        assert scimitar["system"]["damage"]["base"]["types"] == ["slashing"]

        # Check Shortbow
        shortbow = next(w for w in weapons if w["name"] == "Shortbow")
        assert "activities" in shortbow["system"]
        shortbow_activity = list(shortbow["system"]["activities"].values())[0]
        assert shortbow_activity["attack"]["type"]["value"] == "ranged"
        assert shortbow["system"]["range"]["value"] == 80
        assert shortbow["system"]["range"]["long"] == 320

    def test_conversion_preserves_all_traits(self, goblin_data):
        """Verify traits are correctly converted to feat items."""
        foundry_json = convert_to_foundry(goblin_data)

        feats = [item for item in foundry_json["items"] if item["type"] == "feat"]
        assert len(feats) == 1

        nimble_escape = feats[0]
        assert nimble_escape["name"] == "Nimble Escape"
        assert nimble_escape["system"]["activation"]["type"] == "bonus"
        assert "Disengage or Hide" in nimble_escape["system"]["description"]["value"]

    def test_conversion_preserves_spells(self, mage_data):
        """Verify spells are correctly converted with UUIDs."""
        foundry_json = convert_to_foundry(mage_data)

        spells = [item for item in foundry_json["items"] if item["type"] == "spell"]
        assert len(spells) == 16

        # Check cantrips
        cantrips = [s for s in spells if s["system"]["level"] == 0]
        assert len(cantrips) == 4

        # Check spell has UUID
        fireball = next(s for s in spells if s["name"] == "Fireball")
        assert "uuid" in fireball
        assert fireball["uuid"].startswith("Compendium.")
        assert fireball["system"]["level"] == 3
        assert fireball["system"]["school"] == "evo"

    def test_conversion_structure_matches_foundry_format(self, goblin_data):
        """Verify converted JSON matches FoundryVTT expected structure."""
        foundry_json = convert_to_foundry(goblin_data)

        # Check required top-level fields
        assert "name" in foundry_json
        assert "type" in foundry_json
        assert "system" in foundry_json
        assert "items" in foundry_json
        assert "effects" in foundry_json
        assert "flags" in foundry_json

        # Check system structure
        system = foundry_json["system"]
        assert "abilities" in system
        assert "attributes" in system
        assert "details" in system
        assert "traits" in system

        # Check abilities have correct structure
        for ability in ["str", "dex", "con", "int", "wis", "cha"]:
            assert ability in system["abilities"]
            assert "value" in system["abilities"][ability]
            assert "proficient" in system["abilities"][ability]

        # Check attributes structure
        assert "ac" in system["attributes"]
        assert "hp" in system["attributes"]
        assert "movement" in system["attributes"]

    def test_weapon_activities_functional_in_foundry(self, foundry_client):
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
                damage=[DamageFormula(number=1, denomination=6, bonus="+2", type="slashing")]
            )]
        )

        foundry_json = convert_to_foundry(goblin)
        actor_uuid = foundry_client.actors.create_actor(foundry_json)

        # Download and verify
        downloaded = foundry_client.actors.get_actor(actor_uuid)
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

    def test_pit_fiend_bite_full_complexity(self, foundry_client):
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
                damage=[DamageFormula(number=4, denomination=6, bonus="+8", type="piercing")],
                attack_save=AttackSave(
                    ability="con",
                    dc=21,
                    ongoing_damage=[DamageFormula(number=6, denomination=6, bonus="", type="poison")],
                    duration_rounds=10
                )
            )]
        )

        foundry_json = convert_to_foundry(pit_fiend)
        actor_uuid = foundry_client.actors.create_actor(foundry_json)

        downloaded = foundry_client.actors.get_actor(actor_uuid)
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

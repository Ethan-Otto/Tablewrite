"""Tests for FoundryVTT Actor manager (via WebSocket backend)."""

import pytest
from unittest.mock import Mock, patch
from foundry.actors import ActorManager


@pytest.mark.unit
class TestActorManagerSearch:
    """Test actor search operations."""

    def test_search_all_compendiums_found(self):
        """Test searching for actor returns UUID when found."""
        manager = ActorManager(backend_url="http://localhost:8000")

        # Mock search response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "results": [
                {"uuid": "Actor.abc123", "name": "Goblin", "type": "npc"}
            ]
        }

        with patch('requests.get', return_value=mock_response):
            uuid = manager.search_all_compendiums("Goblin")

        assert uuid == "Actor.abc123"

    def test_search_all_compendiums_not_found(self):
        """Test searching for actor returns None when not found."""
        manager = ActorManager(backend_url="http://localhost:8000")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True, "results": []}

        with patch('requests.get', return_value=mock_response):
            uuid = manager.search_all_compendiums("Nonexistent")

        assert uuid is None

    def test_search_handles_network_error(self):
        """Test search handles network errors gracefully."""
        manager = ActorManager(backend_url="http://localhost:8000")

        with patch('requests.get', side_effect=Exception("Network error")):
            uuid = manager.search_all_compendiums("Goblin")

        assert uuid is None


@pytest.mark.unit
class TestActorManagerCreate:
    """Test actor creation operations."""

    def test_create_creature_actor_raises_not_implemented(self):
        """Test creating a creature actor raises NotImplementedError."""
        from actor_pipeline.models import StatBlock

        manager = ActorManager(backend_url="http://localhost:8000")

        stat_block = StatBlock(
            name="Goblin",
            raw_text="Goblin stat block...",
            armor_class=15,
            hit_points=7,
            challenge_rating=0.25,
            size="Small",
            type="humanoid",
            abilities={"STR": 8, "DEX": 14, "CON": 10, "INT": 10, "WIS": 8, "CHA": 8}
        )

        with pytest.raises(NotImplementedError, match="Raw actor creation via WebSocket backend not yet implemented"):
            manager.create_creature_actor(stat_block)

    @patch('requests.post')
    def test_create_npc_actor_minimal(self, mock_post):
        """Test creating NPC actor creates minimal actor with bio."""
        from actor_pipeline.models import NPC

        manager = ActorManager(backend_url="http://localhost:8000")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "uuid": "Actor.klarg123",
            "id": "klarg123",
            "name": "Klarg"
        }
        mock_post.return_value = mock_response

        npc = NPC(
            name="Klarg",
            creature_stat_block_name="Goblin Boss",
            description="Leader of the Cragmaw goblins",
            plot_relevance="Guards the stolen supplies",
            location="Cragmaw Hideout"
        )

        uuid = manager.create_npc_actor(npc, stat_block_uuid="Actor.boss123")

        assert uuid == "Actor.klarg123"
        mock_post.assert_called_once()

        # Verify actor data contains biography
        call_args = mock_post.call_args
        actor_data = call_args[1]["json"]["actor"]
        assert actor_data["name"] == "Klarg"
        assert actor_data["type"] == "npc"
        assert "Leader of the Cragmaw goblins" in actor_data["system"]["details"]["biography"]["value"]
        assert "@UUID[Actor.boss123]" in actor_data["system"]["details"]["biography"]["value"]

    @patch('requests.post')
    def test_create_actor_success(self, mock_post):
        """Test creating an actor with raw actor data."""
        manager = ActorManager(backend_url="http://localhost:8000")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "uuid": "Actor.abc123",
            "id": "abc123",
            "name": "Goblin"
        }
        mock_post.return_value = mock_response

        actor_data = {
            "name": "Goblin",
            "type": "npc",
            "system": {"attributes": {"ac": {"value": 15}}}
        }

        uuid = manager.create_actor(actor_data)

        assert uuid == "Actor.abc123"
        mock_post.assert_called_once()

    @patch('requests.post')
    def test_create_actor_with_spells_calls_give(self, mock_post, caplog):
        """Test creating an actor with spell UUIDs calls add_compendium_items."""
        import logging

        manager = ActorManager(backend_url="http://localhost:8000")

        # Mock both POST calls: create actor and give items
        create_response = Mock()
        create_response.status_code = 200
        create_response.json.return_value = {
            "success": True,
            "uuid": "Actor.mage123",
            "id": "mage123",
            "name": "Mage"
        }

        give_response = Mock()
        give_response.status_code = 200
        give_response.json.return_value = {
            "success": True,
            "actor_uuid": "Actor.mage123",
            "items_added": 2
        }

        # First call is create, second call is give
        mock_post.side_effect = [create_response, give_response]

        actor_data = {"name": "Mage", "type": "npc"}
        spell_uuids = [
            "Compendium.dnd5e.spells.Item.fireball",
            "Compendium.dnd5e.spells.Item.magicmissile"
        ]

        with caplog.at_level(logging.INFO):
            uuid = manager.create_actor(actor_data, spell_uuids=spell_uuids)

        assert uuid == "Actor.mage123"

        # Verify both calls were made: create actor and give items
        assert mock_post.call_count == 2

        # Verify the give items call
        give_call = mock_post.call_args_list[1]
        assert "Actor.mage123/items" in give_call[0][0]  # URL contains actor UUID

        # Verify info logged about adding spells
        assert "Added 2 spells to Mage" in caplog.text


@pytest.mark.unit
class TestActorManagerGet:
    """Test actor retrieval operations."""

    @patch('requests.get')
    def test_get_actor_success(self, mock_get):
        """Test getting an actor by UUID."""
        manager = ActorManager(backend_url="http://localhost:8000")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "entity": {
                "name": "Goblin",
                "type": "npc",
                "uuid": "Actor.abc123"
            }
        }
        mock_get.return_value = mock_response

        result = manager.get_actor("Actor.abc123")

        assert result["name"] == "Goblin"
        mock_get.assert_called_once()

    @patch('requests.get')
    def test_get_all_actors(self, mock_get):
        """Test getting all actors."""
        manager = ActorManager(backend_url="http://localhost:8000")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "actors": [
                {"name": "Goblin", "uuid": "Actor.abc123"},
                {"name": "Orc", "uuid": "Actor.xyz789"}
            ]
        }
        mock_get.return_value = mock_response

        result = manager.get_all_actors()

        assert len(result) == 2
        assert result[0]["name"] == "Goblin"


@pytest.mark.unit
class TestActorManagerDelete:
    """Test actor deletion operations."""

    @patch('requests.delete')
    def test_delete_actor_success(self, mock_delete):
        """Test deleting an actor."""
        manager = ActorManager(backend_url="http://localhost:8000")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_delete.return_value = mock_response

        result = manager.delete_actor("Actor.abc123")

        assert result["success"] is True
        mock_delete.assert_called_once()

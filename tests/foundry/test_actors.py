"""Tests for FoundryVTT Actor manager."""

import pytest
from unittest.mock import Mock, patch
from src.foundry.actors import ActorManager


@pytest.mark.unit
class TestActorManagerSearch:
    """Test actor search operations."""

    def test_search_all_compendiums_found(self):
        """Test searching for actor returns UUID when found."""
        manager = ActorManager(
            relay_url="http://test",
            foundry_url="http://test",
            api_key="test",
            client_id="test"
        )

        # Mock search response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"uuid": "Actor.abc123", "name": "Goblin", "type": "npc"}
        ]

        with patch('requests.get', return_value=mock_response):
            uuid = manager.search_all_compendiums("Goblin")

        assert uuid == "Actor.abc123"

    def test_search_all_compendiums_not_found(self):
        """Test searching for actor returns None when not found."""
        manager = ActorManager(
            relay_url="http://test",
            foundry_url="http://test",
            api_key="test",
            client_id="test"
        )

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []

        with patch('requests.get', return_value=mock_response):
            uuid = manager.search_all_compendiums("Nonexistent")

        assert uuid is None

    def test_search_handles_network_error(self):
        """Test search handles network errors gracefully."""
        manager = ActorManager(
            relay_url="http://test",
            foundry_url="http://test",
            api_key="test",
            client_id="test"
        )

        with patch('requests.get', side_effect=Exception("Network error")):
            uuid = manager.search_all_compendiums("Goblin")

        assert uuid is None


@pytest.mark.unit
class TestActorManagerCreate:
    """Test actor creation operations."""

    def test_create_creature_actor(self):
        """Test creating a creature actor from stat block."""
        from src.actors.models import StatBlock

        manager = ActorManager(
            relay_url="http://test",
            foundry_url="http://test",
            api_key="test",
            client_id="test"
        )

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

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "entity": {"_id": "abc123"},
            "uuid": "Actor.abc123"
        }

        with patch('requests.post', return_value=mock_response) as mock_post:
            uuid = manager.create_creature_actor(stat_block)

        assert uuid == "Actor.abc123"

        # Verify request payload
        call_args = mock_post.call_args
        payload = call_args[1]["json"]
        assert payload["entityType"] == "Actor"
        assert payload["data"]["name"] == "Goblin"
        assert payload["data"]["type"] == "npc"
        assert payload["data"]["system"]["attributes"]["ac"]["value"] == 15
        assert payload["data"]["system"]["attributes"]["hp"]["value"] == 7

    def test_create_npc_actor_with_stat_block_link(self):
        """Test creating NPC actor with link to creature stat block."""
        from src.actors.models import NPC

        manager = ActorManager(
            relay_url="http://test",
            foundry_url="http://test",
            api_key="test",
            client_id="test"
        )

        npc = NPC(
            name="Klarg",
            creature_stat_block_name="Goblin Boss",
            description="Leader of the Cragmaw goblins",
            plot_relevance="Guards the stolen supplies",
            location="Cragmaw Hideout"
        )

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "entity": {"_id": "xyz789"},
            "uuid": "Actor.xyz789"
        }

        with patch('requests.post', return_value=mock_response) as mock_post:
            uuid = manager.create_npc_actor(npc, stat_block_uuid="Actor.boss123")

        assert uuid == "Actor.xyz789"

        # Verify biography includes stat block link
        payload = mock_post.call_args[1]["json"]
        bio = payload["data"]["system"]["details"]["biography"]["value"]
        assert "Klarg" in bio
        assert "Leader of the Cragmaw goblins" in bio
        assert "@UUID[Actor.boss123]" in bio

    def test_create_npc_actor_without_stat_block(self):
        """Test creating NPC actor when stat block not found."""
        from src.actors.models import NPC

        manager = ActorManager(
            relay_url="http://test",
            foundry_url="http://test",
            api_key="test",
            client_id="test"
        )

        npc = NPC(
            name="Mysterious Stranger",
            creature_stat_block_name="Unknown",
            description="A hooded figure",
            plot_relevance="Provides quest information"
        )

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "entity": {"_id": "mystery123"},
            "uuid": "Actor.mystery123"
        }

        with patch('requests.post', return_value=mock_response) as mock_post:
            uuid = manager.create_npc_actor(npc, stat_block_uuid=None)

        assert uuid == "Actor.mystery123"

        # Verify no stat block link in biography
        payload = mock_post.call_args[1]["json"]
        bio = payload["data"]["system"]["details"]["biography"]["value"]
        assert "@UUID" not in bio

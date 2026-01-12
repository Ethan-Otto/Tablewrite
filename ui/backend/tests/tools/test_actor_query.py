"""Unit tests for ActorQueryTool."""
import pytest


class TestActorQueryToolSchema:
    """Test ActorQueryTool schema."""

    def test_tool_name(self):
        """Test tool has correct name."""
        from app.tools.actor_query import ActorQueryTool

        tool = ActorQueryTool()
        assert tool.name == "query_actor"

    def test_get_schema_returns_tool_schema(self):
        """Test get_schema returns valid ToolSchema."""
        from app.tools.actor_query import ActorQueryTool
        from app.tools.base import ToolSchema

        tool = ActorQueryTool()
        schema = tool.get_schema()

        assert isinstance(schema, ToolSchema)
        assert schema.name == "query_actor"
        assert "actor_uuid" in schema.parameters["properties"]
        assert "query" in schema.parameters["properties"]
        assert "query_type" in schema.parameters["properties"]

    def test_schema_query_type_enum(self):
        """Test query_type has correct enum values."""
        from app.tools.actor_query import ActorQueryTool

        tool = ActorQueryTool()
        schema = tool.get_schema()

        query_type = schema.parameters["properties"]["query_type"]
        assert query_type["enum"] == ["abilities", "combat", "general"]


class TestActorContentExtraction:
    """Test extracting structured content from actor data."""

    def test_extract_basic_info(self):
        """Test extracting basic actor info (name, CR, type, AC, HP)."""
        from app.tools.actor_query import ActorQueryTool

        tool = ActorQueryTool()

        actor = {
            "name": "Grolak the Quick",
            "system": {
                "details": {
                    "cr": 0.25,
                    "type": {"value": "humanoid", "subtype": "goblinoid"},
                    "alignment": "neutral evil"
                },
                "attributes": {
                    "ac": {"value": 15},
                    "hp": {"value": 7, "max": 7}
                }
            }
        }

        content = tool._extract_actor_content(actor)

        assert "Grolak the Quick" in content
        assert "CR: 0.25" in content
        assert "humanoid" in content
        assert "AC: 15" in content
        assert "HP: 7" in content

    def test_extract_abilities(self):
        """Test extracting ability scores."""
        from app.tools.actor_query import ActorQueryTool

        tool = ActorQueryTool()

        actor = {
            "name": "Test Actor",
            "system": {
                "abilities": {
                    "str": {"value": 8, "mod": -1},
                    "dex": {"value": 14, "mod": 2},
                    "con": {"value": 10, "mod": 0},
                    "int": {"value": 10, "mod": 0},
                    "wis": {"value": 8, "mod": -1},
                    "cha": {"value": 7, "mod": -2}
                },
                "details": {},
                "attributes": {}
            }
        }

        content = tool._extract_actor_content(actor)

        assert "STR: 8 (-1)" in content
        assert "DEX: 14 (+2)" in content
        assert "CHA: 7 (-2)" in content

    def test_extract_weapons(self):
        """Test extracting weapon items."""
        from app.tools.actor_query import ActorQueryTool

        tool = ActorQueryTool()

        actor = {
            "name": "Test Actor",
            "system": {"details": {}, "attributes": {}, "abilities": {}},
            "items": [
                {
                    "name": "Shortsword",
                    "type": "weapon",
                    "system": {
                        "attack": {"bonus": 4},
                        "damage": {"parts": [["1d6+2", "piercing"]]},
                        "range": {"value": 5, "units": "ft"},
                        "actionType": "mwak"
                    }
                }
            ]
        }

        content = tool._extract_actor_content(actor)

        assert "Shortsword" in content
        assert "+4 to hit" in content
        assert "1d6+2 piercing" in content

    def test_extract_special_abilities(self):
        """Test extracting feat/feature items."""
        from app.tools.actor_query import ActorQueryTool

        tool = ActorQueryTool()

        actor = {
            "name": "Test Actor",
            "system": {"details": {}, "attributes": {}, "abilities": {}},
            "items": [
                {
                    "name": "Nimble Escape",
                    "type": "feat",
                    "system": {
                        "activation": {"type": "bonus"},
                        "description": {"value": "Can take Disengage or Hide as bonus action"}
                    }
                }
            ]
        }

        content = tool._extract_actor_content(actor)

        assert "Nimble Escape" in content
        assert "Bonus Action" in content or "bonus" in content.lower()


class TestPromptBuilding:
    """Test prompt building for different query types."""

    def test_build_abilities_prompt(self):
        """Test building prompt for abilities query type."""
        from app.tools.actor_query import ActorQueryTool

        tool = ActorQueryTool()

        prompt = tool._build_prompt(
            query="What are this creature's stats?",
            query_type="abilities",
            content="[ACTOR: Goblin]\nSTR: 8 (-1) | DEX: 14 (+2)"
        )

        assert "What are this creature's stats?" in prompt
        assert "Goblin" in prompt
        assert "ability scores" in prompt.lower() or "abilities" in prompt.lower()

    def test_build_combat_prompt(self):
        """Test building prompt for combat query type."""
        from app.tools.actor_query import ActorQueryTool

        tool = ActorQueryTool()

        prompt = tool._build_prompt(
            query="What attacks can this monster make?",
            query_type="combat",
            content="[ACTOR: Goblin]\n[COMBAT]\n- Shortsword: +4 to hit"
        )

        assert "attacks" in prompt.lower() or "combat" in prompt.lower()
        assert "Shortsword" in prompt

    def test_build_general_prompt(self):
        """Test building prompt for general query type."""
        from app.tools.actor_query import ActorQueryTool

        tool = ActorQueryTool()

        prompt = tool._build_prompt(
            query="Tell me about this creature",
            query_type="general",
            content="[ACTOR: Goblin]\nCR: 0.25"
        )

        assert "Tell me about this creature" in prompt
        assert "Goblin" in prompt

"""Actor query tool for answering questions about actor abilities and stats."""
import logging
from typing import Optional

from .base import BaseTool, ToolSchema, ToolResponse

logger = logging.getLogger(__name__)


class ActorQueryTool(BaseTool):
    """Tool for querying actors to answer questions about abilities, attacks, and stats."""

    @property
    def name(self) -> str:
        return "query_actor"

    def get_schema(self) -> ToolSchema:
        """Return tool schema for Gemini function calling."""
        return ToolSchema(
            name="query_actor",
            description=(
                "Query a Foundry actor to answer questions about its abilities, attacks, "
                "spells, or stats. Use when user @mentions an actor and asks about what "
                "it can do, its combat abilities, or specific stats. The actor_uuid should "
                "come from the mentioned_entities context."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "actor_uuid": {
                        "type": "string",
                        "description": "The actor UUID from @mention (e.g., 'Actor.abc123')"
                    },
                    "query": {
                        "type": "string",
                        "description": "The user's question about the actor"
                    },
                    "query_type": {
                        "type": "string",
                        "enum": ["abilities", "combat", "general"],
                        "description": "Type of query: abilities for stats/skills, combat for attacks/spells, general for other info"
                    }
                },
                "required": ["actor_uuid", "query", "query_type"]
            }
        )

    async def execute(
        self,
        actor_uuid: str,
        query: str,
        query_type: str
    ) -> ToolResponse:
        """
        Execute actor query.

        Args:
            actor_uuid: Actor UUID from @mention
            query: User's question about the actor
            query_type: One of "abilities", "combat", "general"

        Returns:
            ToolResponse with answer about the actor
        """
        # Placeholder - will implement in next task
        return ToolResponse(
            type="error",
            message="Not implemented yet",
            data=None
        )

    def _extract_actor_content(self, actor: dict) -> str:
        """
        Extract structured content from actor data for Gemini.

        Args:
            actor: Full actor dict from Foundry

        Returns:
            Formatted string with actor information
        """
        sections = []

        # Basic info
        name = actor.get("name", "Unknown")
        system = actor.get("system", {})
        details = system.get("details", {})
        attributes = system.get("attributes", {})

        # CR and type
        cr = details.get("cr", "?")
        actor_type = details.get("type", {})
        type_value = actor_type.get("value", "unknown") if isinstance(actor_type, dict) else str(actor_type)
        subtype = actor_type.get("subtype", "") if isinstance(actor_type, dict) else ""
        type_str = f"{type_value} ({subtype})" if subtype else type_value

        # AC and HP
        ac = attributes.get("ac", {}).get("value", "?")
        hp_data = attributes.get("hp", {})
        hp = hp_data.get("value", hp_data.get("max", "?"))

        sections.append(f"[ACTOR: {name}]")
        sections.append(f"CR: {cr} | Type: {type_str} | AC: {ac} | HP: {hp}")

        # Abilities
        abilities = system.get("abilities", {})
        if abilities:
            ability_strs = []
            for stat in ["str", "dex", "con", "int", "wis", "cha"]:
                if stat in abilities:
                    val = abilities[stat].get("value", 10)
                    mod = abilities[stat].get("mod", 0)
                    sign = "+" if mod >= 0 else ""
                    ability_strs.append(f"{stat.upper()}: {val} ({sign}{mod})")
            if ability_strs:
                sections.append("\n[ABILITIES]")
                sections.append(" | ".join(ability_strs))

        # Items (weapons, feats, spells)
        items = actor.get("items", [])
        weapons = []
        feats = []
        spells = []

        for item in items:
            item_type = item.get("type", "")
            item_name = item.get("name", "Unknown")
            item_system = item.get("system", {})

            if item_type == "weapon":
                attack_bonus = item_system.get("attack", {}).get("bonus", 0)
                damage_parts = item_system.get("damage", {}).get("parts", [])
                damage_str = ", ".join(f"{d[0]} {d[1]}" for d in damage_parts) if damage_parts else "?"
                range_val = item_system.get("range", {}).get("value", "")
                range_units = item_system.get("range", {}).get("units", "")
                range_str = f"{range_val} {range_units}" if range_val else ""

                weapons.append(f"- {item_name}: +{attack_bonus} to hit, {damage_str}" + (f" ({range_str})" if range_str else ""))

            elif item_type == "feat":
                activation = item_system.get("activation", {}).get("type", "")
                activation_str = activation.replace("bonus", "Bonus Action").replace("action", "Action") if activation else ""
                feats.append(f"- {item_name}" + (f" ({activation_str})" if activation_str else ""))

            elif item_type == "spell":
                level = item_system.get("level", 0)
                school = item_system.get("school", "")
                spells.append(f"- {item_name} (Level {level}, {school})")

        if weapons:
            sections.append("\n[COMBAT]")
            sections.extend(weapons)

        if feats:
            sections.append("\n[SPECIAL ABILITIES]")
            sections.extend(feats)

        if spells:
            sections.append("\n[SPELLS]")
            sections.extend(spells)

        return "\n".join(sections)

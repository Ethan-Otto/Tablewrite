"""Actor query tool for answering questions about actor abilities and stats."""
import asyncio
import logging
import sys
from pathlib import Path

from .base import BaseTool, ToolSchema, ToolResponse
from app.websocket import fetch_actor

# Add project src to path for GeminiAPI
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from util.gemini import GeminiAPI  # noqa: E402

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
        try:
            # 1. Fetch the actor from Foundry
            result = await fetch_actor(actor_uuid)

            if not result.success:
                return ToolResponse(
                    type="error",
                    message=f"Failed to fetch actor: {result.error or 'Actor not found'}",
                    data=None
                )

            actor = result.entity

            # 2. Extract structured content
            content = self._extract_actor_content(actor)

            # 3. Build prompt and query Gemini
            prompt = self._build_prompt(query, query_type, content)
            answer = await self._query_gemini(prompt)

            # 4. Return formatted response
            return ToolResponse(
                type="text",
                message=answer,
                data={
                    "actor_name": actor.get("name"),
                    "actor_uuid": actor_uuid,
                    "query_type": query_type
                }
            )

        except Exception as e:
            logger.error(f"Actor query failed: {e}")
            return ToolResponse(
                type="error",
                message=f"Failed to query actor: {str(e)}",
                data=None
            )

    async def _query_gemini(self, prompt: str) -> str:
        """Send prompt to Gemini and get response."""
        def _generate():
            api = GeminiAPI(model_name="gemini-2.0-flash")
            return api.generate_content(prompt).text

        return await asyncio.to_thread(_generate)

    def _build_prompt(self, query: str, query_type: str, content: str) -> str:
        """
        Build a prompt for Gemini based on query type.

        Args:
            query: User's question
            query_type: One of "abilities", "combat", "general"
            content: Extracted actor content

        Returns:
            Formatted prompt string
        """
        base_instructions = """You are a D&D assistant answering questions about a specific actor/creature.
Answer based ONLY on the provided actor data. Be concise and helpful.

Actor Data:
"""

        if query_type == "abilities":
            task = """

Focus on the creature's ability scores, skills, saving throws, and any passive abilities.
Explain what these stats mean for the creature's capabilities.

Question: """

        elif query_type == "combat":
            task = """

Focus on the creature's attacks, weapons, spells, and combat-related abilities.
Explain damage, attack bonuses, and tactical capabilities.

Question: """

        else:  # general
            task = """

Provide a helpful overview based on the question.

Question: """

        return base_instructions + content + task + query + "\n\nAnswer:"

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

        # Movement
        movement = attributes.get("movement", {})
        movement_strs = []
        if movement.get("walk"):
            movement_strs.append(f"walk {movement['walk']} ft")
        if movement.get("fly"):
            movement_strs.append(f"fly {movement['fly']} ft")
        if movement.get("swim"):
            movement_strs.append(f"swim {movement['swim']} ft")
        if movement.get("climb"):
            movement_strs.append(f"climb {movement['climb']} ft")
        if movement.get("burrow"):
            movement_strs.append(f"burrow {movement['burrow']} ft")
        movement_str = ", ".join(movement_strs) if movement_strs else ""

        sections.append(f"[ACTOR: {name}]")
        sections.append(f"CR: {cr} | Type: {type_str} | AC: {ac} | HP: {hp}")
        if movement_str:
            sections.append(f"Movement: {movement_str}")

        # Senses
        senses = attributes.get("senses", {})
        sense_strs = []
        if senses.get("darkvision"):
            sense_strs.append(f"darkvision {senses['darkvision']} ft")
        if senses.get("blindsight"):
            sense_strs.append(f"blindsight {senses['blindsight']} ft")
        if senses.get("tremorsense"):
            sense_strs.append(f"tremorsense {senses['tremorsense']} ft")
        if senses.get("truesight"):
            sense_strs.append(f"truesight {senses['truesight']} ft")
        passive_perc = senses.get("passive", 0)
        if passive_perc:
            sense_strs.append(f"passive Perception {passive_perc}")
        if sense_strs:
            sections.append(f"Senses: {', '.join(sense_strs)}")

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

        # Saving Throws - check proficiency flag
        save_strs = []
        for stat in ["str", "dex", "con", "int", "wis", "cha"]:
            if stat in abilities:
                stat_data = abilities[stat]
                # Foundry uses 'proficient' flag for saving throw proficiency
                if stat_data.get("proficient"):
                    mod = stat_data.get("mod", 0)
                    if isinstance(mod, (int, float)):
                        sign = "+" if mod >= 0 else ""
                        save_strs.append(f"{stat.upper()}: {sign}{mod}")
        if save_strs:
            sections.append(f"Saving Throws: {', '.join(save_strs)}")

        # Skills
        skills = system.get("skills", {})
        skill_strs = []
        for skill_name, skill_data in skills.items():
            if isinstance(skill_data, dict):
                total = skill_data.get("total", 0)
                if total != 0:
                    sign = "+" if total >= 0 else ""
                    # Convert skill name to display format
                    display_name = skill_name.replace("_", " ").title()
                    skill_strs.append(f"{display_name}: {sign}{total}")
        if skill_strs:
            sections.append(f"Skills: {', '.join(skill_strs)}")

        # Damage Resistances, Immunities, Vulnerabilities
        traits = system.get("traits", {})
        if traits.get("dr", {}).get("value"):
            sections.append(f"Damage Resistances: {', '.join(traits['dr']['value'])}")
        if traits.get("di", {}).get("value"):
            sections.append(f"Damage Immunities: {', '.join(traits['di']['value'])}")
        if traits.get("dv", {}).get("value"):
            sections.append(f"Damage Vulnerabilities: {', '.join(traits['dv']['value'])}")
        if traits.get("ci", {}).get("value"):
            sections.append(f"Condition Immunities: {', '.join(traits['ci']['value'])}")
        if traits.get("languages", {}).get("value"):
            sections.append(f"Languages: {', '.join(traits['languages']['value'])}")

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

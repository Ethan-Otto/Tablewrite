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


def normalize_uuid(uuid_str: str) -> str:
    """
    Normalize a Foundry UUID to remove duplicate type prefixes.

    Foundry sometimes returns UUIDs like 'Actor.Actor.xxx' instead of 'Actor.xxx'.
    """
    prefixes = ['Actor', 'JournalEntry', 'Scene', 'Item', 'Compendium']

    for prefix in prefixes:
        doubled = f"{prefix}.{prefix}."
        single = f"{prefix}."
        if uuid_str.startswith(doubled):
            uuid_str = uuid_str.replace(doubled, single, 1)

    return uuid_str


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
            # 1. Normalize UUID to fix doubled prefixes (Actor.Actor.xxx -> Actor.xxx)
            actor_uuid = normalize_uuid(actor_uuid)
            logger.info(f"Querying actor with UUID: {actor_uuid}")

            # 2. Fetch the actor from Foundry
            result = await fetch_actor(actor_uuid)

            if not result.success:
                return ToolResponse(
                    type="error",
                    message=f"Failed to fetch actor: {result.error or 'Actor not found'}",
                    data=None
                )

            actor = result.entity

            # 3. Extract structured content
            content = self._extract_actor_content(actor)
            logger.info(f"[ACTOR_CONTENT]\n{content}")

            # 4. Build prompt and query Gemini
            prompt = self._build_prompt(query, query_type, content)
            answer = await self._query_gemini(prompt)

            # 5. Return formatted response
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

        # Calculate proficiency bonus early so we can show it in header
        prof_bonus = attributes.get("prof")
        if prof_bonus is None:
            # Calculate from CR: prof = 2 + (CR-1)//4 for CR >= 1
            try:
                cr_val = float(cr) if cr not in ["?", None, ""] else 0
                if cr_val < 1:
                    prof_bonus = 2
                else:
                    prof_bonus = 2 + int((cr_val - 1) // 4)
            except (ValueError, TypeError):
                prof_bonus = 2

        sections.append(f"[ACTOR: {name}]")
        sections.append(f"CR: {cr} | Type: {type_str} | AC: {ac} | HP: {hp} | Proficiency: +{prof_bonus}")
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

        # Abilities - calculate mod from value since it's not always stored
        abilities = system.get("abilities", {})
        ability_mods = {}  # Store calculated mods for weapon attack calculations
        if abilities:
            ability_strs = []
            for stat in ["str", "dex", "con", "int", "wis", "cha"]:
                if stat in abilities:
                    val = abilities[stat].get("value", 10)
                    # Calculate mod: (value - 10) // 2
                    mod = (val - 10) // 2
                    ability_mods[stat] = mod
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
                # Get weapon type for ranged/melee detection
                weapon_type = item_system.get("type", {})
                weapon_type_str = weapon_type.get("value", "") if isinstance(weapon_type, dict) else str(weapon_type)

                # Weapon properties for finesse detection
                properties = item_system.get("properties", {})
                is_finesse = properties.get("fin", False) if isinstance(properties, dict) else False

                # Use calculated ability mods
                str_mod = ability_mods.get("str", 0)
                dex_mod = ability_mods.get("dex", 0)

                # Determine which ability mod to use based on weapon type
                # Types ending in 'R' are ranged (simpleR, martialR)
                is_ranged = weapon_type_str.endswith("R") or "ranged" in weapon_type_str.lower()
                if is_ranged:
                    ability_mod = dex_mod
                elif is_finesse and dex_mod > str_mod:
                    ability_mod = dex_mod
                else:
                    ability_mod = str_mod

                # Get attack bonus from activities structure
                activities = item_system.get("activities", {})
                activity_bonus = 0
                for activity_id, activity in activities.items():
                    if activity.get("type") == "attack":
                        bonus_str = activity.get("attack", {}).get("bonus", "0")
                        try:
                            activity_bonus = int(bonus_str) if bonus_str else 0
                        except ValueError:
                            activity_bonus = 0
                        break

                # Check if proficient
                proficient = item_system.get("proficient")
                if proficient is None:
                    proficient = True  # Default true for NPCs
                prof_to_add = prof_bonus if proficient else 0

                # Calculate total attack bonus
                calculated_attack = ability_mod + prof_to_add + activity_bonus
                logger.info(f"[WEAPON] {item_name}: +{calculated_attack} = {ability_mod}(ability) + {prof_to_add}(prof) + {activity_bonus}(bonus)")

                # Extract damage formula
                damage_str = "?"
                # Try activities structure (newer DnD5e)
                activities = item_system.get("activities", {})
                for activity_id, activity in activities.items():
                    if activity.get("type") == "attack":
                        damage_data = activity.get("damage", {})
                        damage_parts = damage_data.get("parts", [])
                        if damage_parts:
                            damage_strs = []
                            for part in damage_parts:
                                formula = part[0] if isinstance(part, list) else part.get("formula", "")
                                dmg_type = part[1] if isinstance(part, list) and len(part) > 1 else part.get("type", "")
                                if formula:
                                    damage_strs.append(f"{formula} {dmg_type}".strip())
                            damage_str = ", ".join(damage_strs) if damage_strs else "?"
                        break
                # Fallback to old structure
                if damage_str == "?":
                    damage_parts = item_system.get("damage", {}).get("parts", [])
                    if damage_parts:
                        damage_str = ", ".join(f"{d[0]} {d[1]}" for d in damage_parts if isinstance(d, list))
                # Try base damage structure
                if damage_str == "?":
                    base_damage = item_system.get("damage", {}).get("base", {})
                    if base_damage:
                        num = base_damage.get("number", 1)
                        die = base_damage.get("denomination", "")
                        bonus = base_damage.get("bonus", "")
                        dmg_types = base_damage.get("types", [])
                        dmg_type = dmg_types[0] if dmg_types else ""
                        if die:
                            formula = f"{num}d{die}"
                            if bonus:
                                formula += f" + {bonus}"
                            damage_str = f"{formula} {dmg_type}".strip()

                # Range
                range_data = item_system.get("range", {})
                range_val = range_data.get("value", "") if isinstance(range_data, dict) else ""
                range_long = range_data.get("long", "") if isinstance(range_data, dict) else ""
                range_units = range_data.get("units", "ft") if isinstance(range_data, dict) else "ft"
                if range_val and range_long:
                    range_str = f"{range_val}/{range_long} {range_units}"
                elif range_val:
                    range_str = f"{range_val} {range_units}"
                else:
                    range_str = ""

                # Weapon type for context
                weapon_type = item_system.get("type", {})
                weapon_type_str = weapon_type.get("value", "") if isinstance(weapon_type, dict) else str(weapon_type)

                attack_sign = "+" if calculated_attack >= 0 else ""
                type_context = f" [{weapon_type_str}]" if weapon_type_str else ""
                range_context = f" (range {range_str})" if range_str else ""

                # Build attack bonus breakdown for clarity
                breakdown_parts = []
                if ability_mod != 0:
                    ability_name = "DEX" if is_ranged or (is_finesse and dex_mod > str_mod) else "STR"
                    breakdown_parts.append(f"{ability_name} {'+' if ability_mod >= 0 else ''}{ability_mod}")
                if prof_to_add != 0:
                    breakdown_parts.append(f"Prof +{prof_to_add}")
                if activity_bonus != 0:
                    breakdown_parts.append(f"Weapon bonus +{activity_bonus}")
                breakdown_str = f" ({' + '.join(breakdown_parts)})" if breakdown_parts else ""

                weapons.append(f"- {item_name}{type_context}: {attack_sign}{calculated_attack} to hit{breakdown_str}, {damage_str}{range_context}")

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

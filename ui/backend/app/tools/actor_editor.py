"""Actor editing tool - allows modifications to existing actors."""
import logging
from typing import Optional, Dict, Any, List
from .base import BaseTool, ToolSchema, ToolResponse
from app.websocket import update_actor, fetch_actor, list_actors, add_custom_items, update_actor_item

logger = logging.getLogger(__name__)


async def find_actor_by_name(actor_name: str) -> Optional[str]:
    """
    Search for an actor by name and return its UUID.

    Uses fuzzy matching - returns the first actor whose name contains
    the search term (case-insensitive).

    Returns:
        Actor UUID if found, None otherwise
    """
    result = await list_actors()
    if not result.success or not result.actors:
        return None

    # Try exact match first (case-insensitive)
    search_lower = actor_name.lower()
    for actor in result.actors:
        if actor.name and actor.name.lower() == search_lower:
            return actor.uuid

    # Try partial match (name contains search term)
    for actor in result.actors:
        if actor.name and search_lower in actor.name.lower():
            return actor.uuid

    return None


# Skill name to FoundryVTT abbreviation mapping
SKILL_ABBREVIATIONS = {
    "acrobatics": "acr",
    "animal handling": "ani",
    "animal_handling": "ani",
    "arcana": "arc",
    "athletics": "ath",
    "deception": "dec",
    "history": "his",
    "insight": "ins",
    "intimidation": "itm",
    "investigation": "inv",
    "medicine": "med",
    "nature": "nat",
    "perception": "prc",
    "performance": "prf",
    "persuasion": "per",
    "religion": "rel",
    "sleight of hand": "slt",
    "sleight_of_hand": "slt",
    "stealth": "ste",
    "survival": "sur",
}


class ActorEditorTool(BaseTool):
    """Tool for editing existing D&D actors in FoundryVTT."""

    @property
    def name(self) -> str:
        return "edit_actor"

    def get_schema(self) -> ToolSchema:
        """Return tool schema for Gemini function calling."""
        return ToolSchema(
            name="edit_actor",
            description=(
                "Edit an existing actor/creature in FoundryVTT. Use when user asks to "
                "modify, change, update, or adjust an actor's stats, abilities, HP, AC, "
                "skills, name, or other attributes. Can search by actor name or use UUID directly."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "actor_name": {
                        "type": "string",
                        "description": "The actor's name to search for (e.g., 'Grolak the Quick', 'Goblin')"
                    },
                    "actor_uuid": {
                        "type": "string",
                        "description": "The actor's UUID if known (e.g., 'Actor.abc123'). Optional if actor_name is provided."
                    },
                    "new_name": {
                        "type": "string",
                        "description": "New name for the actor (to rename it)"
                    },
                    "hp": {
                        "type": "integer",
                        "description": "New hit points value"
                    },
                    "max_hp": {
                        "type": "integer",
                        "description": "New maximum hit points"
                    },
                    "ac": {
                        "type": "integer",
                        "description": "New armor class value"
                    },
                    "str": {
                        "type": "integer",
                        "description": "New Strength score (1-30)"
                    },
                    "dex": {
                        "type": "integer",
                        "description": "New Dexterity score (1-30)"
                    },
                    "con": {
                        "type": "integer",
                        "description": "New Constitution score (1-30)"
                    },
                    "int": {
                        "type": "integer",
                        "description": "New Intelligence score (1-30)"
                    },
                    "wis": {
                        "type": "integer",
                        "description": "New Wisdom score (1-30)"
                    },
                    "cha": {
                        "type": "integer",
                        "description": "New Charisma score (1-30)"
                    },
                    "speed": {
                        "type": "integer",
                        "description": "New walking speed in feet"
                    },
                    "skill_proficiencies": {
                        "type": "array",
                        "description": "Skills to set as proficient (1x proficiency bonus)",
                        "items": {
                            "type": "string",
                            "enum": ["acrobatics", "animal handling", "arcana", "athletics", "deception",
                                     "history", "insight", "intimidation", "investigation", "medicine",
                                     "nature", "perception", "performance", "persuasion", "religion",
                                     "sleight of hand", "stealth", "survival"]
                        }
                    },
                    "skill_expertise": {
                        "type": "array",
                        "description": "Skills to set as expertise (2x proficiency bonus, double proficiency)",
                        "items": {
                            "type": "string",
                            "enum": ["acrobatics", "animal handling", "arcana", "athletics", "deception",
                                     "history", "insight", "intimidation", "investigation", "medicine",
                                     "nature", "perception", "performance", "persuasion", "religion",
                                     "sleight of hand", "stealth", "survival"]
                        }
                    },
                    "remove_skill_proficiencies": {
                        "type": "array",
                        "description": "Skills to remove proficiency from (set to not proficient)",
                        "items": {
                            "type": "string",
                            "enum": ["acrobatics", "animal handling", "arcana", "athletics", "deception",
                                     "history", "insight", "intimidation", "investigation", "medicine",
                                     "nature", "perception", "performance", "persuasion", "religion",
                                     "sleight of hand", "stealth", "survival"]
                        }
                    },
                    "new_attacks": {
                        "type": "array",
                        "description": "New weapon attacks to add to the actor",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string", "description": "Attack name (e.g., 'Bite', 'Claw')"},
                                "description": {"type": "string", "description": "Attack description"},
                                "damage_formula": {"type": "string", "description": "Damage dice (e.g., '2d6+3', '1d8')"},
                                "damage_type": {"type": "string", "description": "Damage type (e.g., 'slashing', 'piercing', 'fire')"},
                                "attack_bonus": {"type": "integer", "description": "Attack bonus modifier"},
                                "range": {"type": "integer", "description": "Attack range in feet (default 5)"},
                                "activation": {"type": "string", "description": "Action type: 'action', 'bonus', 'reaction'"}
                            },
                            "required": ["name", "damage_formula", "damage_type"]
                        }
                    },
                    "new_feats": {
                        "type": "array",
                        "description": "New feats or special abilities to add to the actor",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string", "description": "Feat/ability name"},
                                "description": {"type": "string", "description": "Feat description and effects"},
                                "activation": {"type": "string", "description": "Action type: 'action', 'bonus', 'reaction', 'passive'"},
                                "damage_formula": {"type": "string", "description": "Damage dice if applicable (e.g., '3d6')"},
                                "damage_type": {"type": "string", "description": "Damage type if applicable"},
                                "save_dc": {"type": "integer", "description": "Save DC if this requires a saving throw"},
                                "save_ability": {"type": "string", "description": "Save ability: 'str', 'dex', 'con', 'int', 'wis', 'cha'"},
                                "aoe_type": {"type": "string", "description": "AOE shape: 'cone', 'sphere', 'line', 'cube', 'cylinder' (for breath weapons, fireballs, etc.)"},
                                "aoe_size": {"type": "integer", "description": "AOE size in feet (e.g., 60 for a 60-foot cone)"},
                                "on_save": {"type": "string", "description": "Effect on successful save: 'half' for half damage, 'none' for no damage"}
                            },
                            "required": ["name", "description"]
                        }
                    },
                    "edit_items": {
                        "type": "array",
                        "description": "Edit existing items (weapons, feats, features) on the actor instead of creating new ones",
                        "items": {
                            "type": "object",
                            "properties": {
                                "item_name": {"type": "string", "description": "Current name of the item to edit (case-insensitive match)"},
                                "new_name": {"type": "string", "description": "New name for the item"},
                                "attack_bonus": {"type": "integer", "description": "New attack bonus modifier"},
                                "damage_formula": {"type": "string", "description": "New damage dice (e.g., '2d6+3')"},
                                "damage_type": {"type": "string", "description": "New damage type (e.g., 'slashing', 'piercing')"},
                                "damage_bonus": {"type": "string", "description": "Additional damage bonus"},
                                "description": {"type": "string", "description": "New item description"},
                                "range": {"type": "integer", "description": "New attack range in feet"},
                                "range_long": {"type": "integer", "description": "New long range in feet (for ranged weapons)"},
                                "weapon_type": {"type": "string", "description": "Weapon type: 'natural', 'simpleM', 'simpleR', 'martialM', 'martialR'"},
                                "properties": {
                                    "type": "object",
                                    "description": "Weapon property flags to set",
                                    "properties": {
                                        "ada": {"type": "boolean", "description": "Adamantine"},
                                        "amm": {"type": "boolean", "description": "Ammunition"},
                                        "fin": {"type": "boolean", "description": "Finesse"},
                                        "fir": {"type": "boolean", "description": "Firearm"},
                                        "foc": {"type": "boolean", "description": "Focus"},
                                        "hvy": {"type": "boolean", "description": "Heavy"},
                                        "lgt": {"type": "boolean", "description": "Light"},
                                        "lod": {"type": "boolean", "description": "Loading"},
                                        "mgc": {"type": "boolean", "description": "Magical"},
                                        "rch": {"type": "boolean", "description": "Reach"},
                                        "rel": {"type": "boolean", "description": "Reload"},
                                        "ret": {"type": "boolean", "description": "Returning"},
                                        "sil": {"type": "boolean", "description": "Silvered"},
                                        "spc": {"type": "boolean", "description": "Special"},
                                        "thr": {"type": "boolean", "description": "Thrown"},
                                        "two": {"type": "boolean", "description": "Two-Handed"},
                                        "ver": {"type": "boolean", "description": "Versatile"}
                                    }
                                }
                            },
                            "required": ["item_name"]
                        }
                    }
                },
                "required": []
            }
        )

    async def execute(
        self,
        actor_name: Optional[str] = None,
        actor_uuid: Optional[str] = None,
        new_name: Optional[str] = None,
        hp: Optional[int] = None,
        max_hp: Optional[int] = None,
        ac: Optional[int] = None,
        speed: Optional[int] = None,
        skill_proficiencies: Optional[List[str]] = None,
        skill_expertise: Optional[List[str]] = None,
        remove_skill_proficiencies: Optional[List[str]] = None,
        new_attacks: Optional[List[Dict[str, Any]]] = None,
        new_feats: Optional[List[Dict[str, Any]]] = None,
        edit_items: Optional[List[Dict[str, Any]]] = None,
        **kwargs  # Capture ability scores from Gemini (str, dex, con, int, wis, cha)
    ) -> ToolResponse:
        """Execute actor edit using WebSocket connection to Foundry."""
        try:
            # Resolve actor UUID - either use provided UUID or search by name
            resolved_uuid = actor_uuid
            searched_name = None

            if not resolved_uuid and actor_name:
                # Search for actor by name
                logger.info(f"Searching for actor by name: {actor_name}")
                resolved_uuid = await find_actor_by_name(actor_name)
                searched_name = actor_name

                if not resolved_uuid:
                    return ToolResponse(
                        type="error",
                        message=f"Could not find an actor named '{actor_name}'. Please check the name or provide the UUID.",
                        data=None
                    )
                logger.info(f"Found actor '{actor_name}' with UUID: {resolved_uuid}")

            if not resolved_uuid:
                return ToolResponse(
                    type="error",
                    message="Please provide either an actor name or UUID to edit.",
                    data=None
                )

            # Build updates dictionary based on provided parameters
            updates: Dict[str, Any] = {}

            if new_name is not None:
                updates["name"] = new_name

            # HP updates (DnD5e system structure)
            if hp is not None:
                updates["system.attributes.hp.value"] = hp
            if max_hp is not None:
                updates["system.attributes.hp.max"] = max_hp

            # AC update
            if ac is not None:
                updates["system.attributes.ac.flat"] = ac

            # Ability score updates (from kwargs since str/int are Python reserved words)
            ability_names = ["str", "dex", "con", "int", "wis", "cha"]
            for ability in ability_names:
                value = kwargs.get(ability)
                if value is not None:
                    updates[f"system.abilities.{ability}.value"] = value

            # Speed update
            if speed is not None:
                updates["system.attributes.movement.walk"] = speed

            # Skill proficiency updates
            # In DnD5e, skill.value is: 0 = not proficient, 1 = proficient, 2 = expertise
            skill_changes = []
            if skill_proficiencies:
                for skill_name in skill_proficiencies:
                    skill_key = SKILL_ABBREVIATIONS.get(skill_name.lower())
                    if skill_key:
                        updates[f"system.skills.{skill_key}.value"] = 1
                        skill_changes.append(f"**{skill_name}** (proficient)")
                    else:
                        logger.warning(f"Unknown skill: {skill_name}")

            if skill_expertise:
                for skill_name in skill_expertise:
                    skill_key = SKILL_ABBREVIATIONS.get(skill_name.lower())
                    if skill_key:
                        updates[f"system.skills.{skill_key}.value"] = 2
                        skill_changes.append(f"**{skill_name}** (expertise)")
                    else:
                        logger.warning(f"Unknown skill: {skill_name}")

            if remove_skill_proficiencies:
                for skill_name in remove_skill_proficiencies:
                    skill_key = SKILL_ABBREVIATIONS.get(skill_name.lower())
                    if skill_key:
                        updates[f"system.skills.{skill_key}.value"] = 0
                        skill_changes.append(f"**{skill_name}** (removed)")
                    else:
                        logger.warning(f"Unknown skill: {skill_name}")

            # Check if we have any modifications to make
            has_stat_updates = bool(updates)
            has_custom_items = bool(new_attacks) or bool(new_feats)
            has_item_edits = bool(edit_items)

            if not has_stat_updates and not has_custom_items and not has_item_edits:
                return ToolResponse(
                    type="error",
                    message="No updates provided. Specify at least one attribute to change or items to add.",
                    data=None
                )

            actor_display_name = None
            final_uuid = resolved_uuid

            # Apply stat updates if any
            if has_stat_updates:
                logger.info(f"Updating actor {resolved_uuid} with: {updates}")
                result = await update_actor(resolved_uuid, updates)

                if not result.success:
                    return ToolResponse(
                        type="error",
                        message=f"Failed to update actor: {result.error}",
                        data=None
                    )
                actor_display_name = result.name
                final_uuid = result.uuid

            # Add custom attacks and feats if any
            items_added = 0
            if has_custom_items:
                custom_items = []

                # Convert attacks to item format
                if new_attacks:
                    for attack in new_attacks:
                        custom_items.append({
                            "name": attack.get("name", "Attack"),
                            "type": "weapon",
                            "description": attack.get("description", ""),
                            "damage_formula": attack.get("damage_formula"),
                            "damage_type": attack.get("damage_type", "bludgeoning"),
                            "attack_bonus": attack.get("attack_bonus"),
                            "range": attack.get("range", 5),
                            "activation": attack.get("activation", "action")
                        })

                # Convert feats to item format
                if new_feats:
                    for feat in new_feats:
                        custom_items.append({
                            "name": feat.get("name", "Ability"),
                            "type": "feat",
                            "description": feat.get("description", ""),
                            "activation": feat.get("activation", "passive"),
                            "damage_formula": feat.get("damage_formula"),
                            "damage_type": feat.get("damage_type"),
                            "save_dc": feat.get("save_dc"),
                            "save_ability": feat.get("save_ability"),
                            # AOE fields for breath weapons, etc.
                            "aoe_type": feat.get("aoe_type"),
                            "aoe_size": feat.get("aoe_size"),
                            "on_save": feat.get("on_save")
                        })

                logger.info(f"Adding {len(custom_items)} custom items to actor {resolved_uuid}")
                items_result = await add_custom_items(resolved_uuid, custom_items)

                if not items_result.success:
                    # If stat updates succeeded but items failed, report partial success
                    if has_stat_updates:
                        return ToolResponse(
                            type="text",
                            message=f"Updated actor stats but failed to add items: {items_result.error}",
                            data=None
                        )
                    return ToolResponse(
                        type="error",
                        message=f"Failed to add items to actor: {items_result.error}",
                        data=None
                    )
                items_added = items_result.items_added or 0

            # Edit existing items if any
            items_edited = []
            if has_item_edits:
                for item_edit in edit_items:
                    item_name = item_edit.get("item_name")
                    if not item_name:
                        continue

                    # Build update dict for this item
                    item_updates = {}
                    for key in ["new_name", "attack_bonus", "damage_formula", "damage_type",
                                "damage_bonus", "description", "range", "range_long",
                                "weapon_type", "properties"]:
                        if key in item_edit and item_edit[key] is not None:
                            # Map new_name to name for the Foundry handler
                            update_key = "name" if key == "new_name" else key
                            item_updates[update_key] = item_edit[key]

                    if item_updates:
                        logger.info(f"Editing item '{item_name}' on actor {resolved_uuid}: {item_updates}")
                        edit_result = await update_actor_item(resolved_uuid, item_name, item_updates)

                        if edit_result.success:
                            items_edited.append(edit_result.item_name or item_name)
                        else:
                            logger.warning(f"Failed to edit item '{item_name}': {edit_result.error}")

            # If we only modified items (no stat updates), fetch actor name
            if not has_stat_updates and (has_custom_items or has_item_edits):
                fetch_result = await fetch_actor(resolved_uuid)
                if fetch_result.success and fetch_result.entity:
                    actor_display_name = fetch_result.entity.get("name", "the actor")
                else:
                    actor_display_name = "the actor"

            # Build summary of changes
            change_summary = []
            if new_name is not None:
                change_summary.append(f"name to **{new_name}**")
            if hp is not None:
                change_summary.append(f"HP to **{hp}**")
            if max_hp is not None:
                change_summary.append(f"max HP to **{max_hp}**")
            if ac is not None:
                change_summary.append(f"AC to **{ac}**")
            for ability in ability_names:
                value = kwargs.get(ability)
                if value is not None:
                    change_summary.append(f"{ability.upper()} to **{value}**")
            if speed is not None:
                change_summary.append(f"speed to **{speed} ft**")

            # Add skill changes to summary
            if skill_changes:
                change_summary.append(f"skills: {', '.join(skill_changes)}")

            # Add attack/feat summaries
            if new_attacks:
                attack_names = [a.get("name", "Attack") for a in new_attacks]
                change_summary.append(f"added attacks: **{', '.join(attack_names)}**")
            if new_feats:
                feat_names = [f.get("name", "Ability") for f in new_feats]
                change_summary.append(f"added abilities: **{', '.join(feat_names)}**")

            # Add edited items summary
            if items_edited:
                change_summary.append(f"edited items: **{', '.join(items_edited)}**")

            changes_text = ", ".join(change_summary)
            actor_display_name = actor_display_name or "the actor"

            # Create FoundryVTT content link format
            actor_link = f"@UUID[{final_uuid}]{{{actor_display_name}}}"

            message = (
                f"Updated **{actor_display_name}**: {changes_text}\n\n"
                f"**Link:** `{actor_link}`"
            )

            return ToolResponse(
                type="text",
                message=message,
                data={
                    "uuid": final_uuid,
                    "name": actor_display_name,
                    "updates": updates,
                    "items_added": items_added,
                    "items_edited": items_edited,
                    "link": actor_link
                }
            )

        except Exception as e:
            logger.error(f"Actor edit failed: {e}")
            return ToolResponse(
                type="error",
                message=f"Failed to edit actor: {str(e)}",
                data=None
            )

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

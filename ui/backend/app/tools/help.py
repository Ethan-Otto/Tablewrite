"""Help tool - lists all available tools."""
import logging
from .base import BaseTool, ToolSchema, ToolResponse

logger = logging.getLogger(__name__)


class HelpTool(BaseTool):
    """Tool for listing all available tools and their descriptions."""

    @property
    def name(self) -> str:
        return "help"

    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name="help",
            description="List all available tools and commands",
            parameters={
                "type": "object",
                "properties": {},
                "required": []
            }
        )

    async def execute(self) -> ToolResponse:
        """List all available tools with descriptions."""
        try:
            # Import here to avoid circular import
            from .registry import registry

            schemas = registry.get_schemas()

            lines = ["**Available Tools:**\n"]
            for schema in sorted(schemas, key=lambda s: s.name):
                # Truncate long descriptions to first sentence
                desc = schema.description
                if ". " in desc:
                    desc = desc.split(". ")[0] + "."
                lines.append(f"- **{schema.name}**: {desc}")

            return ToolResponse(
                type="text",
                message="\n".join(lines),
                data={
                    "tools": [{"name": s.name, "description": s.description} for s in schemas],
                    "count": len(schemas)
                }
            )

        except Exception as e:
            logger.error(f"Help failed: {e}")
            return ToolResponse(
                type="error",
                message=f"Failed to get help: {str(e)}",
                data=None
            )

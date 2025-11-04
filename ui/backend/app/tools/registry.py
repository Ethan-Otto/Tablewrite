"""Central registry for all tools."""
from typing import Dict, List
from .base import BaseTool, ToolSchema, ToolResponse


class ToolRegistry:
    """Central registry for all tools."""

    def __init__(self):
        """Initialize empty registry."""
        self.tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool):
        """
        Register a tool.

        Args:
            tool: Tool instance to register
        """
        self.tools[tool.name] = tool

    def get_schemas(self) -> List[ToolSchema]:
        """
        Get all tool schemas for Gemini.

        Returns:
            List of tool schemas
        """
        return [tool.get_schema() for tool in self.tools.values()]

    async def execute_tool(self, tool_name: str, **kwargs) -> ToolResponse:
        """
        Execute a tool by name.

        Args:
            tool_name: Name of tool to execute
            **kwargs: Tool parameters

        Returns:
            Tool response

        Raises:
            ValueError: If tool not found
        """
        if tool_name not in self.tools:
            raise ValueError(f"Unknown tool: {tool_name}")
        return await self.tools[tool_name].execute(**kwargs)


# Global registry instance
registry = ToolRegistry()

"""Slash command parser for Module Assistant."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel


class CommandType(str, Enum):
    """Available command types."""
    GENERATE_SCENE = "generate_scene"
    LIST_SCENES = "list_scenes"
    LIST_ACTORS = "list_actors"
    HELP = "help"
    CHAT = "chat"  # Regular message, not a command
    UNKNOWN = "unknown"


class ParsedCommand(BaseModel):
    """Parsed command result."""
    type: CommandType
    args: str
    is_command: bool
    original_message: str


class CommandParser:
    """Parser for slash commands."""

    COMMAND_MAP = {
        "/generate-scene": CommandType.GENERATE_SCENE,
        "/list-scenes": CommandType.LIST_SCENES,
        "/list-actors": CommandType.LIST_ACTORS,
        "/help": CommandType.HELP,
    }

    def parse(self, message: str) -> ParsedCommand:
        """
        Parse a message into a command.

        Args:
            message: User input message

        Returns:
            ParsedCommand with type and arguments
        """
        message = message.strip()

        # Check if it's a command (starts with /)
        if not message.startswith("/"):
            return ParsedCommand(
                type=CommandType.CHAT,
                args=message,
                is_command=False,
                original_message=message
            )

        # Split command and args
        parts = message.split(maxsplit=1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        # Look up command type
        cmd_type = self.COMMAND_MAP.get(command, CommandType.UNKNOWN)

        return ParsedCommand(
            type=cmd_type,
            args=args,
            is_command=True,
            original_message=message
        )

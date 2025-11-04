"""Tests for slash command parser."""

import pytest
from app.services.command_parser import (
    CommandParser,
    ParsedCommand,
    CommandType
)


def test_parse_generate_scene():
    """Test parsing /generate-scene command."""
    parser = CommandParser()
    cmd = parser.parse("/generate-scene dark cave entrance")

    assert cmd.type == CommandType.GENERATE_SCENE
    assert cmd.args == "dark cave entrance"
    assert cmd.is_command is True


def test_parse_list_scenes():
    """Test parsing /list-scenes command."""
    parser = CommandParser()
    cmd = parser.parse("/list-scenes Chapter 2")

    assert cmd.type == CommandType.LIST_SCENES
    assert cmd.args == "Chapter 2"


def test_parse_help():
    """Test parsing /help command."""
    parser = CommandParser()
    cmd = parser.parse("/help")

    assert cmd.type == CommandType.HELP
    assert cmd.args == ""


def test_parse_regular_message():
    """Test parsing non-command message."""
    parser = CommandParser()
    cmd = parser.parse("Hello, how are you?")

    assert cmd.type == CommandType.CHAT
    assert cmd.args == "Hello, how are you?"
    assert cmd.is_command is False


def test_parse_unknown_command():
    """Test parsing unknown slash command."""
    parser = CommandParser()
    cmd = parser.parse("/unknown-command test")

    assert cmd.type == CommandType.UNKNOWN
    assert cmd.is_command is True

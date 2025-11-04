"""Tests for API models."""

import pytest
from app.models.chat import ChatMessage, ChatRole, ChatRequest, ChatResponse
from app.models.scene import Scene


def test_chat_message_creation():
    """Test ChatMessage model creation."""
    msg = ChatMessage(role=ChatRole.USER, content="Hello")
    assert msg.role == ChatRole.USER
    assert msg.content == "Hello"
    assert msg.timestamp is not None


def test_chat_request_validation():
    """Test ChatRequest validates message."""
    req = ChatRequest(message="test message")
    assert req.message == "test message"
    assert req.context == {}


def test_chat_response_creation():
    """Test ChatResponse model."""
    resp = ChatResponse(
        message="Generated response",
        type="text"
    )
    assert resp.message == "Generated response"
    assert resp.type == "text"
    assert resp.data is None


def test_scene_model_import():
    """Test Scene model can be imported."""
    scene = Scene(
        section_path="Chapter 1 → Area 1",
        name="Test Cave",
        description="A dark cave entrance",
        location_type="underground"
    )
    assert scene.name == "Test Cave"
    assert scene.location_type == "underground"

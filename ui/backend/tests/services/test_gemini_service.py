"""Tests for Gemini service with function calling."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from app.services.gemini_service import GeminiService
from app.tools.base import ToolSchema


class TestGeminiServiceFunctionCalling:
    """Test Gemini service function calling."""

    @pytest.fixture
    def mock_genai_client(self):
        """Create mock Gemini client."""
        with patch('app.services.gemini_service.GeminiAPI') as mock:
            yield mock

    def test_schema_to_gemini_tool(self, mock_genai_client):
        """Test converting ToolSchema to Gemini tool format."""
        service = GeminiService()
        schema = ToolSchema(
            name="test_tool",
            description="A test tool",
            parameters={
                "type": "object",
                "properties": {
                    "param1": {"type": "string", "description": "First param"}
                },
                "required": ["param1"]
            }
        )

        gemini_tool = service._schema_to_gemini_tool(schema)

        assert gemini_tool["name"] == "test_tool"
        assert gemini_tool["description"] == "A test tool"
        assert "parameters" in gemini_tool

    @pytest.mark.anyio
    async def test_generate_with_tools_no_tool_call(self, mock_genai_client):
        """Test generate_with_tools when no tool is called."""
        service = GeminiService()

        # Mock response with no function call - parts have no function_call attribute
        mock_part = Mock()
        mock_part.function_call = None  # No function call

        mock_content = Mock()
        mock_content.parts = [mock_part]  # Make parts iterable

        mock_candidate = Mock()
        mock_candidate.content = mock_content

        mock_response = Mock()
        mock_response.text = "Regular text response"
        mock_response.candidates = [mock_candidate]

        with patch.object(service.api, 'generate_content', return_value=mock_response):
            response = await service.generate_with_tools(
                message="Hello",
                conversation_history=[],
                tools=[]
            )

        assert response["type"] == "text"
        assert response["text"] == "Regular text response"
        assert response["tool_call"] is None

    @pytest.mark.anyio
    async def test_generate_with_tools_with_tool_call(self, mock_genai_client):
        """Test generate_with_tools when tool is called."""
        service = GeminiService()

        # Mock function call on a part (matches actual Gemini API structure)
        mock_function_call = Mock()
        mock_function_call.name = "generate_images"
        mock_function_call.args = {"prompt": "a dragon", "count": 2}

        mock_part = Mock()
        mock_part.function_call = mock_function_call

        mock_content = Mock()
        mock_content.parts = [mock_part]  # Make parts iterable

        mock_candidate = Mock()
        mock_candidate.content = mock_content

        mock_response = Mock()
        mock_response.candidates = [mock_candidate]

        with patch.object(service.api, 'generate_content', return_value=mock_response):
            response = await service.generate_with_tools(
                message="Show me a dragon",
                conversation_history=[],
                tools=[]
            )

        assert response["type"] == "tool_call"
        assert response["tool_call"]["name"] == "generate_images"
        assert response["tool_call"]["parameters"]["prompt"] == "a dragon"

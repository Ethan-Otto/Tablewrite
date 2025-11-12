# Scene Extraction and Artwork Generation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extract physical location descriptions from D&D module XML and generate AI artwork for each scene, then upload to FoundryVTT as a scene gallery journal page.

**Architecture:** Post-processing workflow that analyzes generated XML (no initial tagging). Uses Gemini to (1) extract chapter environmental context, (2) identify physical location sections, (3) generate scene artwork via Gemini Imagen. Creates FoundryVTT journal page with scene images and section hierarchy.

**Tech Stack:** Python 3.11+, Gemini API (text analysis + Imagen), FoundryVTT REST API, Pydantic for data models

---

## Task 1: Create Scene Data Models

**Files:**
- Create: `src/scene_extraction/models.py`
- Test: `tests/scene_extraction/test_models.py`

**Step 1: Write test for Scene model validation**

Create test file:

```python
# tests/scene_extraction/test_models.py
"""Tests for scene extraction data models."""

import pytest
from src.scene_extraction.models import Scene, ChapterContext


class TestSceneModel:
    """Tests for Scene Pydantic model."""

    def test_scene_creation_with_all_fields(self):
        """Test creating a Scene with all fields."""
        scene = Scene(
            section_path="Chapter 2 → The Cragmaw Hideout → Area 1",
            name="Cave Mouth",
            description="A dark cave entrance with rough stone walls",
            xml_section_id="chapter_2_area_1"
        )

        assert scene.section_path == "Chapter 2 → The Cragmaw Hideout → Area 1"
        assert scene.name == "Cave Mouth"
        assert scene.description == "A dark cave entrance with rough stone walls"
        assert scene.xml_section_id == "chapter_2_area_1"

    def test_scene_creation_minimal_fields(self):
        """Test creating a Scene with only required fields."""
        scene = Scene(
            section_path="Chapter 1 → Introduction",
            name="Town Square",
            description="A bustling town square"
        )

        assert scene.section_path == "Chapter 1 → Introduction"
        assert scene.name == "Town Square"
        assert scene.description == "A bustling town square"
        assert scene.xml_section_id is None

    def test_scene_validates_non_empty_name(self):
        """Test that Scene rejects empty name."""
        with pytest.raises(ValueError):
            Scene(
                section_path="Chapter 1",
                name="",
                description="Test description"
            )

    def test_scene_validates_non_empty_description(self):
        """Test that Scene rejects empty description."""
        with pytest.raises(ValueError):
            Scene(
                section_path="Chapter 1",
                name="Test Scene",
                description=""
            )


class TestChapterContextModel:
    """Tests for ChapterContext Pydantic model."""

    def test_chapter_context_creation(self):
        """Test creating ChapterContext with all fields."""
        context = ChapterContext(
            environment_type="underground",
            weather="dry",
            atmosphere="oppressive",
            lighting="dim torchlight",
            terrain="rocky caverns",
            additional_notes="Goblin-infested dungeon"
        )

        assert context.environment_type == "underground"
        assert context.weather == "dry"
        assert context.atmosphere == "oppressive"
        assert context.lighting == "dim torchlight"
        assert context.terrain == "rocky caverns"
        assert context.additional_notes == "Goblin-infested dungeon"

    def test_chapter_context_optional_fields(self):
        """Test ChapterContext with minimal fields."""
        context = ChapterContext(
            environment_type="forest"
        )

        assert context.environment_type == "forest"
        assert context.weather is None
        assert context.atmosphere is None
        assert context.lighting is None
        assert context.terrain is None
        assert context.additional_notes is None
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/scene_extraction/test_models.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'src.scene_extraction'"

**Step 3: Create Scene and ChapterContext models**

```python
# src/scene_extraction/models.py
"""Data models for scene extraction."""

from typing import Optional
from pydantic import BaseModel, field_validator


class Scene(BaseModel):
    """Represents a physical location/scene from a D&D module."""

    section_path: str  # e.g., "Chapter 2 → The Cragmaw Hideout → Area 1"
    name: str
    description: str  # Physical environment description only (no NPCs/monsters)
    xml_section_id: Optional[str] = None  # Reference to XML section element

    @field_validator('name')
    @classmethod
    def validate_name_not_empty(cls, v: str) -> str:
        """Ensure name is not empty."""
        if not v or not v.strip():
            raise ValueError("Scene name cannot be empty")
        return v

    @field_validator('description')
    @classmethod
    def validate_description_not_empty(cls, v: str) -> str:
        """Ensure description is not empty."""
        if not v or not v.strip():
            raise ValueError("Scene description cannot be empty")
        return v


class ChapterContext(BaseModel):
    """Environmental context for a chapter (inferred by Gemini)."""

    environment_type: str  # e.g., "underground", "forest", "urban", "coastal"
    weather: Optional[str] = None  # e.g., "rainy", "foggy", "clear"
    atmosphere: Optional[str] = None  # e.g., "oppressive", "peaceful", "tense"
    lighting: Optional[str] = None  # e.g., "dim torchlight", "bright sunlight", "darkness"
    terrain: Optional[str] = None  # e.g., "rocky caverns", "dense forest", "cobblestone streets"
    additional_notes: Optional[str] = None  # Any other relevant context
```

**Step 4: Create __init__.py for module**

```python
# src/scene_extraction/__init__.py
"""Scene extraction and artwork generation."""

from .models import Scene, ChapterContext

__all__ = ['Scene', 'ChapterContext']
```

**Step 5: Run test to verify it passes**

Run: `uv run pytest tests/scene_extraction/test_models.py -v`
Expected: PASS (all tests green)

**Step 6: Commit**

```bash
git add src/scene_extraction/models.py src/scene_extraction/__init__.py tests/scene_extraction/test_models.py
git commit -m "feat: add Scene and ChapterContext Pydantic models"
```

---

## Task 2: Implement Chapter Context Extraction

**Files:**
- Create: `src/scene_extraction/extract_context.py`
- Test: `tests/scene_extraction/test_extract_context.py`
- Modify: `src/scene_extraction/__init__.py`

**Step 1: Write test for context extraction**

```python
# tests/scene_extraction/test_extract_context.py
"""Tests for chapter context extraction."""

import pytest
from unittest.mock import patch, MagicMock
from src.scene_extraction.extract_context import extract_chapter_context
from src.scene_extraction.models import ChapterContext


@pytest.fixture
def sample_xml_content():
    """Sample XML content for testing."""
    return """
    <chapter name="The Cragmaw Hideout">
        <section name="Overview">
            <p>Deep in the forest, a cave system serves as the hideout for Cragmaw goblins.</p>
        </section>
        <section name="Area 1">
            <p>The cave entrance is dark and foreboding, with rough stone walls.</p>
        </section>
    </chapter>
    """


class TestExtractChapterContext:
    """Tests for extract_chapter_context function."""

    @pytest.mark.integration
    def test_extract_context_calls_gemini(self, sample_xml_content):
        """Test that extract_chapter_context calls Gemini API with correct prompt."""
        with patch('src.scene_extraction.extract_context.genai.GenerativeModel') as mock_model:
            # Mock Gemini response
            mock_response = MagicMock()
            mock_response.text = """
            {
                "environment_type": "underground",
                "weather": "dry",
                "atmosphere": "oppressive",
                "lighting": "dim",
                "terrain": "rocky caverns",
                "additional_notes": "Forest cave system"
            }
            """
            mock_instance = MagicMock()
            mock_instance.generate_content.return_value = mock_response
            mock_model.return_value = mock_instance

            # Call function
            context = extract_chapter_context(sample_xml_content)

            # Verify Gemini was called
            mock_model.assert_called_once()
            mock_instance.generate_content.assert_called_once()

            # Verify result is ChapterContext
            assert isinstance(context, ChapterContext)
            assert context.environment_type == "underground"
            assert context.terrain == "rocky caverns"

    def test_extract_context_handles_json_parsing(self):
        """Test that extract_context properly parses Gemini JSON response."""
        with patch('src.scene_extraction.extract_context.genai.GenerativeModel') as mock_model:
            mock_response = MagicMock()
            mock_response.text = '{"environment_type": "forest", "lighting": "dappled sunlight"}'
            mock_instance = MagicMock()
            mock_instance.generate_content.return_value = mock_response
            mock_model.return_value = mock_instance

            context = extract_chapter_context("<chapter></chapter>")

            assert context.environment_type == "forest"
            assert context.lighting == "dappled sunlight"

    def test_extract_context_raises_on_invalid_json(self):
        """Test that extract_context raises error on malformed JSON."""
        with patch('src.scene_extraction.extract_context.genai.GenerativeModel') as mock_model:
            mock_response = MagicMock()
            mock_response.text = "Not valid JSON at all"
            mock_instance = MagicMock()
            mock_instance.generate_content.return_value = mock_response
            mock_model.return_value = mock_instance

            with pytest.raises(ValueError, match="Failed to parse.*JSON"):
                extract_chapter_context("<chapter></chapter>")
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/scene_extraction/test_extract_context.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'src.scene_extraction.extract_context'"

**Step 3: Implement extract_chapter_context function**

```python
# src/scene_extraction/extract_context.py
"""Extract environmental context from chapter XML using Gemini."""

import logging
import json
import os
from typing import Dict, Any
import google.generativeai as genai

from .models import ChapterContext

logger = logging.getLogger(__name__)

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GeminiImageAPI")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

GEMINI_MODEL_NAME = "gemini-2.0-flash-exp"


def extract_chapter_context(xml_content: str) -> ChapterContext:
    """
    Use Gemini to analyze chapter XML and extract environmental context.

    Args:
        xml_content: Full chapter XML content

    Returns:
        ChapterContext with environment type, weather, atmosphere, etc.

    Raises:
        ValueError: If Gemini response is invalid or unparseable
        RuntimeError: If Gemini API call fails
    """
    logger.info("Extracting chapter environmental context with Gemini")

    prompt = f"""
Analyze this D&D module chapter XML and extract environmental context.

Return ONLY a JSON object with these fields (use null for unknown):
- environment_type: (e.g., "underground", "forest", "urban", "coastal", "dungeon")
- weather: (e.g., "rainy", "foggy", "clear", "stormy") or null if indoors/underground
- atmosphere: (e.g., "oppressive", "peaceful", "tense", "mysterious")
- lighting: (e.g., "dim torchlight", "bright sunlight", "darkness", "well-lit")
- terrain: (e.g., "rocky caverns", "dense forest", "cobblestone streets")
- additional_notes: Any other relevant environmental details

Focus on the PHYSICAL ENVIRONMENT only. Ignore NPCs, monsters, and plot.

XML:
{xml_content}

Return ONLY valid JSON, no markdown formatting:
"""

    try:
        model = genai.GenerativeModel(GEMINI_MODEL_NAME)
        response = model.generate_content(prompt)

        logger.debug(f"Gemini response: {response.text}")

        # Parse JSON response
        response_text = response.text.strip()

        # Remove markdown code blocks if present
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            response_text = "\n".join(lines[1:-1])  # Remove first and last lines
            if response_text.startswith("json"):
                response_text = response_text[4:].strip()

        try:
            context_data = json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response as JSON: {response_text}")
            raise ValueError(f"Failed to parse Gemini response as JSON: {e}") from e

        # Create ChapterContext (Pydantic will validate)
        context = ChapterContext(**context_data)
        logger.info(f"Extracted context: {context.environment_type} environment")

        return context

    except Exception as e:
        logger.error(f"Failed to extract chapter context: {e}")
        raise RuntimeError(f"Failed to extract chapter context: {e}") from e
```

**Step 4: Update __init__.py**

```python
# src/scene_extraction/__init__.py
"""Scene extraction and artwork generation."""

from .models import Scene, ChapterContext
from .extract_context import extract_chapter_context

__all__ = ['Scene', 'ChapterContext', 'extract_chapter_context']
```

**Step 5: Run test to verify it passes**

Run: `uv run pytest tests/scene_extraction/test_extract_context.py -v -m "not integration"`
Expected: PASS (unit tests with mocked Gemini)

**Step 6: Run integration test (optional - requires API key)**

Run: `uv run pytest tests/scene_extraction/test_extract_context.py -v -m integration`
Expected: PASS (makes real Gemini API call)

**Step 7: Commit**

```bash
git add src/scene_extraction/extract_context.py src/scene_extraction/__init__.py tests/scene_extraction/test_extract_context.py
git commit -m "feat: implement chapter context extraction with Gemini"
```

---

## Task 3: Implement Scene Location Identification

**Files:**
- Create: `src/scene_extraction/identify_scenes.py`
- Test: `tests/scene_extraction/test_identify_scenes.py`
- Modify: `src/scene_extraction/__init__.py`

**Step 1: Write test for scene identification**

```python
# tests/scene_extraction/test_identify_scenes.py
"""Tests for scene location identification."""

import pytest
from unittest.mock import patch, MagicMock
from src.scene_extraction.identify_scenes import identify_scene_locations
from src.scene_extraction.models import Scene, ChapterContext


@pytest.fixture
def sample_xml_content():
    """Sample XML for testing."""
    return """
    <chapter name="The Cragmaw Hideout">
        <section name="Area 1" id="area_1">
            <p>The cave entrance is dark and foreboding.</p>
        </section>
    </chapter>
    """


@pytest.fixture
def sample_context():
    """Sample chapter context."""
    return ChapterContext(
        environment_type="underground",
        lighting="dim",
        terrain="rocky caverns"
    )


class TestIdentifySceneLocations:
    """Tests for identify_scene_locations function."""

    @pytest.mark.integration
    def test_identify_scenes_calls_gemini(self, sample_xml_content, sample_context):
        """Test that identify_scene_locations calls Gemini with XML and context."""
        with patch('src.scene_extraction.identify_scenes.genai.GenerativeModel') as mock_model:
            mock_response = MagicMock()
            mock_response.text = """
            [
                {
                    "section_path": "Chapter 1 → Area 1",
                    "name": "Cave Entrance",
                    "description": "Dark cave entrance with rough stone walls",
                    "xml_section_id": "area_1"
                }
            ]
            """
            mock_instance = MagicMock()
            mock_instance.generate_content.return_value = mock_response
            mock_model.return_value = mock_instance

            scenes = identify_scene_locations(sample_xml_content, sample_context)

            # Verify Gemini called
            mock_model.assert_called_once()
            mock_instance.generate_content.assert_called_once()

            # Verify result
            assert len(scenes) == 1
            assert isinstance(scenes[0], Scene)
            assert scenes[0].name == "Cave Entrance"

    def test_identify_scenes_parses_json_array(self, sample_context):
        """Test parsing of JSON array response."""
        with patch('src.scene_extraction.identify_scenes.genai.GenerativeModel') as mock_model:
            mock_response = MagicMock()
            mock_response.text = '[{"section_path": "Ch1", "name": "Room", "description": "A room"}]'
            mock_instance = MagicMock()
            mock_instance.generate_content.return_value = mock_response
            mock_model.return_value = mock_instance

            scenes = identify_scene_locations("<xml></xml>", sample_context)

            assert len(scenes) == 1
            assert scenes[0].name == "Room"

    def test_identify_scenes_returns_empty_list_on_no_scenes(self, sample_context):
        """Test that function returns empty list when no scenes found."""
        with patch('src.scene_extraction.identify_scenes.genai.GenerativeModel') as mock_model:
            mock_response = MagicMock()
            mock_response.text = "[]"
            mock_instance = MagicMock()
            mock_instance.generate_content.return_value = mock_response
            mock_model.return_value = mock_instance

            scenes = identify_scene_locations("<xml></xml>", sample_context)

            assert scenes == []
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/scene_extraction/test_identify_scenes.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'src.scene_extraction.identify_scenes'"

**Step 3: Implement identify_scene_locations function**

```python
# src/scene_extraction/identify_scenes.py
"""Identify physical location scenes from chapter XML using Gemini."""

import logging
import json
import os
from typing import List
import google.generativeai as genai

from .models import Scene, ChapterContext

logger = logging.getLogger(__name__)

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GeminiImageAPI")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

GEMINI_MODEL_NAME = "gemini-2.0-flash-exp"


def identify_scene_locations(xml_content: str, chapter_context: ChapterContext) -> List[Scene]:
    """
    Use Gemini to analyze XML and identify physical location scenes.

    Args:
        xml_content: Full chapter XML content
        chapter_context: Environmental context for the chapter

    Returns:
        List of Scene objects (empty list if no scenes found)

    Raises:
        ValueError: If Gemini response is invalid
        RuntimeError: If Gemini API call fails
    """
    logger.info("Identifying scene locations with Gemini")

    context_summary = f"""
Environment: {chapter_context.environment_type}
Weather: {chapter_context.weather or 'N/A'}
Atmosphere: {chapter_context.atmosphere or 'N/A'}
Lighting: {chapter_context.lighting or 'N/A'}
Terrain: {chapter_context.terrain or 'N/A'}
"""

    prompt = f"""
Analyze this D&D module chapter XML and identify physical location scenes (rooms, areas, outdoor locations).

Chapter Environmental Context:
{context_summary}

For each physical location, extract:
- section_path: Full section hierarchy (e.g., "Chapter 2 → The Cragmaw Hideout → Area 1")
- name: Short descriptive name for the location
- description: Physical environment description ONLY (no NPCs, no monsters, no plot - just the physical space)
- xml_section_id: The 'id' attribute from the XML section element (or null if not present)

Return ONLY a JSON array of scene objects. If no physical locations found, return [].

EXCLUDE from descriptions:
- Named NPCs or monsters
- Combat encounters
- Plot events
- Treasure or items

INCLUDE in descriptions:
- Physical layout and dimensions
- Architectural features
- Natural features (if outdoor)
- Lighting and atmosphere
- Furniture and fixtures
- Environmental hazards (physical only, like pits or traps)

XML:
{xml_content}

Return ONLY valid JSON array, no markdown formatting:
"""

    try:
        model = genai.GenerativeModel(GEMINI_MODEL_NAME)
        response = model.generate_content(prompt)

        logger.debug(f"Gemini response: {response.text}")

        # Parse JSON response
        response_text = response.text.strip()

        # Remove markdown code blocks if present
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            response_text = "\n".join(lines[1:-1])
            if response_text.startswith("json"):
                response_text = response_text[4:].strip()

        try:
            scenes_data = json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response as JSON: {response_text}")
            raise ValueError(f"Failed to parse Gemini response as JSON: {e}") from e

        # Create Scene objects (Pydantic will validate)
        scenes = [Scene(**scene_data) for scene_data in scenes_data]
        logger.info(f"Identified {len(scenes)} scene locations")

        return scenes

    except Exception as e:
        logger.error(f"Failed to identify scene locations: {e}")
        raise RuntimeError(f"Failed to identify scene locations: {e}") from e
```

**Step 4: Update __init__.py**

```python
# src/scene_extraction/__init__.py
"""Scene extraction and artwork generation."""

from .models import Scene, ChapterContext
from .extract_context import extract_chapter_context
from .identify_scenes import identify_scene_locations

__all__ = ['Scene', 'ChapterContext', 'extract_chapter_context', 'identify_scene_locations']
```

**Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/scene_extraction/test_identify_scenes.py -v -m "not integration"`
Expected: PASS (unit tests with mocked Gemini)

**Step 6: Commit**

```bash
git add src/scene_extraction/identify_scenes.py src/scene_extraction/__init__.py tests/scene_extraction/test_identify_scenes.py
git commit -m "feat: implement scene location identification with Gemini"
```

---

## Task 4: Implement Scene Artwork Generation

**Files:**
- Create: `src/scene_extraction/generate_artwork.py`
- Test: `tests/scene_extraction/test_generate_artwork.py`
- Modify: `src/scene_extraction/__init__.py`

**Step 1: Write test for artwork generation**

```python
# tests/scene_extraction/test_generate_artwork.py
"""Tests for scene artwork generation."""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from src.scene_extraction.generate_artwork import generate_scene_image
from src.scene_extraction.models import Scene, ChapterContext


@pytest.fixture
def sample_scene():
    """Sample scene for testing."""
    return Scene(
        section_path="Chapter 1 → Area 1",
        name="Cave Entrance",
        description="A dark cave with rough stone walls and moss-covered rocks"
    )


@pytest.fixture
def sample_context():
    """Sample chapter context."""
    return ChapterContext(
        environment_type="underground",
        lighting="dim",
        terrain="rocky caverns"
    )


class TestGenerateSceneImage:
    """Tests for generate_scene_image function."""

    @pytest.mark.integration
    def test_generate_image_calls_gemini_imagen(self, sample_scene, sample_context):
        """Test that generate_scene_image calls Gemini Imagen API."""
        with patch('src.scene_extraction.generate_artwork.genai.GenerativeModel') as mock_model:
            # Mock Imagen response
            mock_response = MagicMock()
            mock_response._result = MagicMock()
            mock_response._result.candidates = [MagicMock()]
            mock_response._result.candidates[0].content = MagicMock()
            mock_response._result.candidates[0].content.parts = [MagicMock()]
            mock_response._result.candidates[0].content.parts[0].inline_data = MagicMock()
            mock_response._result.candidates[0].content.parts[0].inline_data.data = b"fake_image_data"

            mock_instance = MagicMock()
            mock_instance.generate_content.return_value = mock_response
            mock_model.return_value = mock_instance

            # Call function
            image_bytes = generate_scene_image(sample_scene, sample_context, style_prompt="fantasy art")

            # Verify Gemini called
            mock_model.assert_called_once()
            mock_instance.generate_content.assert_called_once()

            # Verify result
            assert isinstance(image_bytes, bytes)
            assert image_bytes == b"fake_image_data"

    def test_generate_image_constructs_prompt_with_context(self, sample_scene, sample_context):
        """Test that prompt includes scene description and chapter context."""
        with patch('src.scene_extraction.generate_artwork.genai.GenerativeModel') as mock_model:
            mock_response = MagicMock()
            mock_response._result = MagicMock()
            mock_response._result.candidates = [MagicMock()]
            mock_response._result.candidates[0].content = MagicMock()
            mock_response._result.candidates[0].content.parts = [MagicMock()]
            mock_response._result.candidates[0].content.parts[0].inline_data = MagicMock()
            mock_response._result.candidates[0].content.parts[0].inline_data.data = b"data"

            mock_instance = MagicMock()
            mock_instance.generate_content.return_value = mock_response
            mock_model.return_value = mock_instance

            generate_scene_image(sample_scene, sample_context)

            # Verify prompt contains scene description and context
            call_args = mock_instance.generate_content.call_args
            prompt = call_args[0][0]
            assert "cave" in prompt.lower()
            assert "underground" in prompt.lower()
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/scene_extraction/test_generate_artwork.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'src.scene_extraction.generate_artwork'"

**Step 3: Implement generate_scene_image function**

```python
# src/scene_extraction/generate_artwork.py
"""Generate scene artwork using Gemini Imagen."""

import logging
import os
from typing import Optional
import google.generativeai as genai

from .models import Scene, ChapterContext

logger = logging.getLogger(__name__)

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GeminiImageAPI")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

IMAGEN_MODEL_NAME = "imagen-3.0-generate-001"
DEFAULT_STYLE_PROMPT = "fantasy illustration, D&D 5e art style, detailed environment, high quality"


def generate_scene_image(
    scene: Scene,
    chapter_context: ChapterContext,
    style_prompt: Optional[str] = None
) -> bytes:
    """
    Generate artwork for a scene using Gemini Imagen.

    Args:
        scene: Scene object with description
        chapter_context: Chapter environmental context
        style_prompt: Optional custom style prompt (uses default if not provided)

    Returns:
        Image data as bytes (PNG format)

    Raises:
        RuntimeError: If image generation fails
    """
    logger.info(f"Generating artwork for scene: {scene.name}")

    style = style_prompt or DEFAULT_STYLE_PROMPT

    # Construct comprehensive prompt
    prompt = f"""
{scene.description}

Environment: {chapter_context.environment_type}
Lighting: {chapter_context.lighting or 'natural'}
Terrain: {chapter_context.terrain or 'varied'}
Atmosphere: {chapter_context.atmosphere or 'neutral'}

Style: {style}
"""

    logger.debug(f"Image generation prompt: {prompt}")

    try:
        model = genai.GenerativeModel(IMAGEN_MODEL_NAME)
        response = model.generate_content(prompt)

        # Extract image data from response
        # Gemini Imagen returns image in response.candidates[0].content.parts[0].inline_data
        image_data = response._result.candidates[0].content.parts[0].inline_data.data

        logger.info(f"Generated image for '{scene.name}' ({len(image_data)} bytes)")
        return image_data

    except Exception as e:
        logger.error(f"Failed to generate image for scene '{scene.name}': {e}")
        raise RuntimeError(f"Failed to generate scene image: {e}") from e


def save_scene_image(image_bytes: bytes, output_path: str) -> None:
    """
    Save image bytes to file.

    Args:
        image_bytes: Image data as bytes
        output_path: Path to save image file

    Raises:
        IOError: If file write fails
    """
    from pathlib import Path

    try:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'wb') as f:
            f.write(image_bytes)
        logger.info(f"Saved image to {output_path}")
    except IOError as e:
        logger.error(f"Failed to save image to '{output_path}': {e}")
        raise
```

**Step 4: Update __init__.py**

```python
# src/scene_extraction/__init__.py
"""Scene extraction and artwork generation."""

from .models import Scene, ChapterContext
from .extract_context import extract_chapter_context
from .identify_scenes import identify_scene_locations
from .generate_artwork import generate_scene_image, save_scene_image

__all__ = [
    'Scene',
    'ChapterContext',
    'extract_chapter_context',
    'identify_scene_locations',
    'generate_scene_image',
    'save_scene_image'
]
```

**Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/scene_extraction/test_generate_artwork.py -v -m "not integration"`
Expected: PASS (unit tests with mocked Gemini)

**Step 6: Commit**

```bash
git add src/scene_extraction/generate_artwork.py src/scene_extraction/__init__.py tests/scene_extraction/test_generate_artwork.py
git commit -m "feat: implement scene artwork generation with Gemini Imagen"
```

---

## Task 5: Create Scene Gallery Journal HTML Generator

**Files:**
- Create: `src/scene_extraction/create_gallery.py`
- Test: `tests/scene_extraction/test_create_gallery.py`
- Modify: `src/scene_extraction/__init__.py`

**Step 1: Write test for gallery HTML generation**

```python
# tests/scene_extraction/test_create_gallery.py
"""Tests for scene gallery journal page creation."""

import pytest
from pathlib import Path
from src.scene_extraction.create_gallery import create_scene_gallery_html
from src.scene_extraction.models import Scene


@pytest.fixture
def sample_scenes():
    """Sample scenes for testing."""
    return [
        Scene(
            section_path="Chapter 1 → Introduction → Town Square",
            name="Phandalin Town Square",
            description="A bustling market square"
        ),
        Scene(
            section_path="Chapter 2 → The Cragmaw Hideout → Area 1",
            name="Cave Entrance",
            description="A dark cave entrance"
        )
    ]


@pytest.fixture
def sample_image_paths():
    """Sample image paths for testing."""
    return {
        "Phandalin Town Square": "images/scene_001_phandalin_town_square.png",
        "Cave Entrance": "images/scene_002_cave_entrance.png"
    }


class TestCreateSceneGalleryHTML:
    """Tests for create_scene_gallery_html function."""

    def test_create_gallery_basic_structure(self, sample_scenes, sample_image_paths):
        """Test that gallery HTML has correct structure."""
        html = create_scene_gallery_html(sample_scenes, sample_image_paths)

        assert "<h1>Scene Gallery</h1>" in html
        assert "Phandalin Town Square" in html
        assert "Cave Entrance" in html

    def test_create_gallery_includes_section_paths(self, sample_scenes, sample_image_paths):
        """Test that section hierarchy is included."""
        html = create_scene_gallery_html(sample_scenes, sample_image_paths)

        assert "Chapter 1 → Introduction → Town Square" in html
        assert "Chapter 2 → The Cragmaw Hideout → Area 1" in html

    def test_create_gallery_includes_image_tags(self, sample_scenes, sample_image_paths):
        """Test that image tags are included with correct paths."""
        html = create_scene_gallery_html(sample_scenes, sample_image_paths)

        assert '<img src="images/scene_001_phandalin_town_square.png"' in html
        assert '<img src="images/scene_002_cave_entrance.png"' in html

    def test_create_gallery_handles_missing_image(self, sample_scenes):
        """Test that gallery handles scenes with missing images."""
        image_paths = {
            "Phandalin Town Square": "images/scene_001.png"
            # Cave Entrance missing
        }

        html = create_scene_gallery_html(sample_scenes, image_paths)

        # Should include both scenes but only one image
        assert "Phandalin Town Square" in html
        assert "Cave Entrance" in html
        assert '<img src="images/scene_001.png"' in html
        assert "No image available" in html or "scene_002" not in html

    def test_create_gallery_empty_scenes(self):
        """Test gallery with no scenes."""
        html = create_scene_gallery_html([], {})

        assert "<h1>Scene Gallery</h1>" in html
        assert "No scenes found" in html or "<p>This chapter contains no scene artwork.</p>" in html
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/scene_extraction/test_create_gallery.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'src.scene_extraction.create_gallery'"

**Step 3: Implement create_scene_gallery_html function**

```python
# src/scene_extraction/create_gallery.py
"""Create FoundryVTT journal page HTML for scene gallery."""

import logging
from typing import List, Dict

from .models import Scene

logger = logging.getLogger(__name__)


def create_scene_gallery_html(scenes: List[Scene], image_paths: Dict[str, str]) -> str:
    """
    Create HTML for a FoundryVTT journal page with scene gallery.

    Args:
        scenes: List of Scene objects
        image_paths: Dict mapping scene name to image file path (relative to FoundryVTT)

    Returns:
        HTML string for journal page

    Example image_paths:
        {
            "Cave Entrance": "worlds/my-world/images/scene_001_cave_entrance.png",
            "Town Square": "worlds/my-world/images/scene_002_town_square.png"
        }
    """
    logger.info(f"Creating scene gallery HTML for {len(scenes)} scenes")

    if not scenes:
        return """
<h1>Scene Gallery</h1>
<p>This chapter contains no scene artwork.</p>
"""

    html_parts = ["<h1>Scene Gallery</h1>"]

    for scene in scenes:
        # Section header
        html_parts.append(f'<h2 style="margin-top: 2em; border-bottom: 2px solid #444;">{scene.name}</h2>')

        # Section path (breadcrumb)
        html_parts.append(f'<p style="color: #888; font-size: 0.9em; margin-bottom: 0.5em;">{scene.section_path}</p>')

        # Image (if available)
        image_path = image_paths.get(scene.name)
        if image_path:
            html_parts.append(f'<img src="{image_path}" alt="{scene.name}" style="max-width: 100%; height: auto; border: 1px solid #333; margin: 1em 0;" />')
        else:
            html_parts.append('<p style="color: #666; font-style: italic;">No image available for this scene.</p>')

        # Scene description
        html_parts.append(f'<p style="margin-top: 1em;">{scene.description}</p>')

        # Divider
        html_parts.append('<hr style="margin: 2em 0; border: none; border-top: 1px solid #333;" />')

    return "\n".join(html_parts)
```

**Step 4: Update __init__.py**

```python
# src/scene_extraction/__init__.py
"""Scene extraction and artwork generation."""

from .models import Scene, ChapterContext
from .extract_context import extract_chapter_context
from .identify_scenes import identify_scene_locations
from .generate_artwork import generate_scene_image, save_scene_image
from .create_gallery import create_scene_gallery_html

__all__ = [
    'Scene',
    'ChapterContext',
    'extract_chapter_context',
    'identify_scene_locations',
    'generate_scene_image',
    'save_scene_image',
    'create_scene_gallery_html'
]
```

**Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/scene_extraction/test_create_gallery.py -v`
Expected: PASS (all tests green)

**Step 6: Commit**

```bash
git add src/scene_extraction/create_gallery.py src/scene_extraction/__init__.py tests/scene_extraction/test_create_gallery.py
git commit -m "feat: implement scene gallery journal HTML generator"
```

---

## Task 6: Create Main Scene Processing Script

**Files:**
- Create: `scripts/generate_scene_art.py`
- Test: `tests/scene_extraction/test_full_workflow.py`

**Step 1: Write end-to-end test for scene processing**

```python
# tests/scene_extraction/test_full_workflow.py
"""End-to-end tests for scene extraction workflow."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


@pytest.fixture
def test_xml_file(tmp_path):
    """Create test XML file."""
    xml_content = """
<chapter name="Test Chapter">
    <section name="Area 1" id="area_1">
        <p>A dark forest clearing with ancient trees.</p>
    </section>
</chapter>
"""
    xml_file = tmp_path / "test_chapter.xml"
    xml_file.write_text(xml_content)
    return xml_file


class TestSceneProcessingWorkflow:
    """End-to-end workflow tests."""

    @pytest.mark.integration
    def test_full_workflow_with_mocked_gemini(self, test_xml_file, tmp_path):
        """Test complete workflow with mocked Gemini calls."""
        # Import here to avoid issues if module doesn't exist yet
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

        from src.scene_extraction import (
            extract_chapter_context,
            identify_scene_locations,
            generate_scene_image,
            save_scene_image,
            create_scene_gallery_html
        )

        xml_content = test_xml_file.read_text()
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Mock Gemini calls
        with patch('src.scene_extraction.extract_context.genai.GenerativeModel') as mock_context_model, \
             patch('src.scene_extraction.identify_scenes.genai.GenerativeModel') as mock_scenes_model, \
             patch('src.scene_extraction.generate_artwork.genai.GenerativeModel') as mock_image_model:

            # Mock context extraction
            mock_context_response = MagicMock()
            mock_context_response.text = '{"environment_type": "forest", "lighting": "dappled sunlight"}'
            mock_context_instance = MagicMock()
            mock_context_instance.generate_content.return_value = mock_context_response
            mock_context_model.return_value = mock_context_instance

            # Mock scene identification
            mock_scenes_response = MagicMock()
            mock_scenes_response.text = '''
            [
                {
                    "section_path": "Test Chapter → Area 1",
                    "name": "Forest Clearing",
                    "description": "A dark forest clearing",
                    "xml_section_id": "area_1"
                }
            ]
            '''
            mock_scenes_instance = MagicMock()
            mock_scenes_instance.generate_content.return_value = mock_scenes_response
            mock_scenes_model.return_value = mock_scenes_instance

            # Mock image generation
            mock_image_response = MagicMock()
            mock_image_response._result = MagicMock()
            mock_image_response._result.candidates = [MagicMock()]
            mock_image_response._result.candidates[0].content = MagicMock()
            mock_image_response._result.candidates[0].content.parts = [MagicMock()]
            mock_image_response._result.candidates[0].content.parts[0].inline_data = MagicMock()
            mock_image_response._result.candidates[0].content.parts[0].inline_data.data = b"fake_png_data"
            mock_image_instance = MagicMock()
            mock_image_instance.generate_content.return_value = mock_image_response
            mock_image_model.return_value = mock_image_instance

            # Run workflow
            context = extract_chapter_context(xml_content)
            scenes = identify_scene_locations(xml_content, context)
            assert len(scenes) == 1

            image_bytes = generate_scene_image(scenes[0], context)
            image_path = output_dir / "scene_001_forest_clearing.png"
            save_scene_image(image_bytes, str(image_path))

            assert image_path.exists()
            assert image_path.read_bytes() == b"fake_png_data"

            # Create gallery HTML
            image_paths = {"Forest Clearing": str(image_path)}
            html = create_scene_gallery_html(scenes, image_paths)

            assert "Scene Gallery" in html
            assert "Forest Clearing" in html
            assert str(image_path) in html
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/scene_extraction/test_full_workflow.py -v`
Expected: FAIL with "No such file: scripts/generate_scene_art.py"

**Step 3: Create main processing script**

```python
# scripts/generate_scene_art.py
#!/usr/bin/env python3
"""
Generate scene artwork from D&D module XML.

This script:
1. Extracts chapter environmental context using Gemini
2. Identifies physical location scenes in the XML
3. Generates AI artwork for each scene using Gemini Imagen
4. Creates a FoundryVTT journal page with scene gallery
5. Saves images and gallery HTML to output directory

Usage:
    uv run python scripts/generate_scene_art.py --run-dir output/runs/20241023_123456
    uv run python scripts/generate_scene_art.py --xml-file output/runs/latest/documents/chapter_01.xml
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.logging_config import setup_logging
from src.scene_extraction import (
    extract_chapter_context,
    identify_scene_locations,
    generate_scene_image,
    save_scene_image,
    create_scene_gallery_html
)

logger = setup_logging(__name__)


def sanitize_filename(name: str) -> str:
    """Convert scene name to safe filename."""
    import re
    # Remove special characters, replace spaces with underscores
    safe_name = re.sub(r'[^\w\s-]', '', name.lower())
    safe_name = re.sub(r'[-\s]+', '_', safe_name)
    return safe_name


def process_chapter(
    xml_file: Path,
    output_dir: Path,
    style_prompt: str = None
) -> dict:
    """
    Process a single chapter XML file to generate scene artwork.

    Args:
        xml_file: Path to chapter XML file
        output_dir: Directory to save images and HTML
        style_prompt: Optional custom style prompt for image generation

    Returns:
        Dict with processing statistics
    """
    logger.info(f"Processing chapter: {xml_file.name}")

    # Read XML
    xml_content = xml_file.read_text()

    # Step 1: Extract chapter context
    logger.info("Step 1: Extracting chapter environmental context...")
    context = extract_chapter_context(xml_content)
    logger.info(f"  Environment: {context.environment_type}")

    # Step 2: Identify scenes
    logger.info("Step 2: Identifying scene locations...")
    scenes = identify_scene_locations(xml_content, context)
    logger.info(f"  Found {len(scenes)} scenes")

    if not scenes:
        logger.warning("No scenes found in chapter")
        return {"scenes_found": 0, "images_generated": 0}

    # Create images directory
    images_dir = output_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    # Step 3: Generate images
    logger.info("Step 3: Generating scene artwork...")
    image_paths = {}
    for i, scene in enumerate(scenes, start=1):
        logger.info(f"  [{i}/{len(scenes)}] Generating image for: {scene.name}")

        try:
            # Generate image
            image_bytes = generate_scene_image(scene, context, style_prompt)

            # Save image
            safe_name = sanitize_filename(scene.name)
            image_filename = f"scene_{i:03d}_{safe_name}.png"
            image_path = images_dir / image_filename
            save_scene_image(image_bytes, str(image_path))

            # Store relative path for FoundryVTT (will be updated during upload)
            image_paths[scene.name] = f"images/{image_filename}"

        except Exception as e:
            logger.error(f"Failed to generate image for '{scene.name}': {e}")
            # Continue with other scenes

    # Step 4: Create gallery HTML
    logger.info("Step 4: Creating scene gallery HTML...")
    gallery_html = create_scene_gallery_html(scenes, image_paths)

    # Save gallery HTML
    gallery_file = output_dir / "scene_gallery.html"
    gallery_file.write_text(gallery_html)
    logger.info(f"  Saved gallery to: {gallery_file}")

    return {
        "scenes_found": len(scenes),
        "images_generated": len(image_paths),
        "gallery_file": str(gallery_file)
    }


def main():
    """Main entry point."""
    load_dotenv()

    parser = argparse.ArgumentParser(description="Generate scene artwork from D&D module XML")
    parser.add_argument("--run-dir", help="Run directory containing documents/ folder")
    parser.add_argument("--xml-file", help="Single XML file to process")
    parser.add_argument("--style", help="Custom style prompt for image generation")
    parser.add_argument("--output-dir", help="Custom output directory (default: <run-dir>/scene_artwork)")

    args = parser.parse_args()

    if not args.run_dir and not args.xml_file:
        parser.error("Must specify either --run-dir or --xml-file")

    # Determine XML files to process
    if args.xml_file:
        xml_files = [Path(args.xml_file)]
        output_dir = Path(args.output_dir) if args.output_dir else Path(args.xml_file).parent / "scene_artwork"
    else:
        run_dir = Path(args.run_dir)
        xml_files = list((run_dir / "documents").glob("*.xml"))
        output_dir = Path(args.output_dir) if args.output_dir else run_dir / "scene_artwork"

    if not xml_files:
        logger.error("No XML files found to process")
        return 1

    logger.info(f"Found {len(xml_files)} XML files to process")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Process each chapter
    total_scenes = 0
    total_images = 0

    for xml_file in xml_files:
        try:
            stats = process_chapter(xml_file, output_dir, args.style)
            total_scenes += stats["scenes_found"]
            total_images += stats["images_generated"]
        except Exception as e:
            logger.error(f"Failed to process {xml_file.name}: {e}")
            continue

    # Summary
    logger.info("=" * 60)
    logger.info("Scene artwork generation complete!")
    logger.info(f"  Total scenes identified: {total_scenes}")
    logger.info(f"  Total images generated: {total_images}")
    logger.info(f"  Output directory: {output_dir}")
    logger.info("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
```

**Step 4: Make script executable**

Run: `chmod +x scripts/generate_scene_art.py`
Expected: File permissions updated

**Step 5: Run end-to-end test**

Run: `uv run pytest tests/scene_extraction/test_full_workflow.py -v -m integration`
Expected: PASS (with mocked Gemini calls)

**Step 6: Commit**

```bash
git add scripts/generate_scene_art.py tests/scene_extraction/test_full_workflow.py
git commit -m "feat: add scene artwork generation script"
```

---

## Task 7: Integrate with full_pipeline.py

**Files:**
- Modify: `scripts/full_pipeline.py`
- Test: Manual testing

**Step 1: Read current full_pipeline.py structure**

Run: `uv run python -c "from pathlib import Path; print(Path('scripts/full_pipeline.py').read_text()[:2000])"`
Expected: See current pipeline structure

**Step 2: Add scene artwork generation step**

Add imports at top:

```python
# After existing imports, add:
from generate_scene_art import process_chapter as process_scenes
```

Add new function after `run_pdf_to_xml`:

```python
def run_scene_artwork_generation(run_dir: Path, style_prompt: str = None) -> None:
    """
    Generate scene artwork from chapter XML files.

    Args:
        run_dir: Run directory containing documents/ folder
        style_prompt: Optional custom style prompt

    Raises:
        RuntimeError: If scene generation fails
    """
    logger.info("=" * 60)
    logger.info("STEP 2.5: Generating scene artwork")
    logger.info("=" * 60)

    output_dir = run_dir / "scene_artwork"

    try:
        from generate_scene_art import process_chapter, sanitize_filename

        xml_files = list((run_dir / "documents").glob("*.xml"))

        if not xml_files:
            logger.warning("No XML files found, skipping scene artwork generation")
            return

        logger.info(f"Processing {len(xml_files)} chapter files...")

        total_scenes = 0
        total_images = 0

        for xml_file in xml_files:
            try:
                stats = process_chapter(xml_file, output_dir, style_prompt)
                total_scenes += stats["scenes_found"]
                total_images += stats["images_generated"]
            except Exception as e:
                logger.error(f"Failed to process {xml_file.name}: {e}")

        logger.info(f"✓ Scene artwork generation completed")
        logger.info(f"  Total scenes: {total_scenes}, Images: {total_images}")

    except Exception as e:
        logger.error(f"Scene artwork generation failed: {e}")
        raise RuntimeError(f"Scene artwork generation failed: {e}") from e
```

**Step 3: Update main() to include scene generation step**

In `main()` function, after `run_pdf_to_xml` call, add:

```python
    # Step 2.5: Generate scene artwork (optional)
    if not args.skip_scenes:
        try:
            run_scene_artwork_generation(run_dir, style_prompt=os.getenv("IMAGE_STYLE_PROMPT"))
        except Exception as e:
            logger.error(f"Scene artwork generation failed: {e}")
            if not args.continue_on_error:
                raise
```

Add argument to argparse:

```python
    parser.add_argument("--skip-scenes", action="store_true", help="Skip scene artwork generation")
```

**Step 4: Test integration manually**

Run: `uv run python scripts/full_pipeline.py --skip-split --skip-xml --skip-upload --skip-export --run-dir output/runs/latest`
Expected: Pipeline runs without errors, skipping scene generation

**Step 5: Commit**

```bash
git add scripts/full_pipeline.py
git commit -m "feat: integrate scene artwork generation into full pipeline"
```

---

## Task 8: Update FoundryVTT Upload to Include Scene Gallery

**Files:**
- Modify: `src/foundry/upload_journal_to_foundry.py`
- Test: Manual testing with FoundryVTT

**Step 1: Read current upload script**

Run: `uv run python -c "from pathlib import Path; print(Path('src/foundry/upload_journal_to_foundry.py').read_text()[:1000])"`
Expected: See current upload logic

**Step 2: Add scene gallery page to journal upload**

Modify upload logic to:

1. Upload scene images to FoundryVTT
2. Update image paths in gallery HTML
3. Append scene gallery as final journal page

```python
# After creating regular journal pages, add:

def upload_scene_gallery(client, run_dir: Path, journal_name: str) -> Optional[dict]:
    """
    Upload scene artwork and create gallery journal page.

    Args:
        client: FoundryClient instance
        run_dir: Run directory
        journal_name: Name of journal to append gallery to

    Returns:
        Gallery page dict or None if no scenes
    """
    scene_artwork_dir = run_dir / "scene_artwork"
    images_dir = scene_artwork_dir / "images"
    gallery_file = scene_artwork_dir / "scene_gallery.html"

    if not gallery_file.exists():
        logger.info("No scene gallery found, skipping")
        return None

    logger.info("Uploading scene artwork...")

    # Upload images to FoundryVTT
    image_path_mapping = {}
    if images_dir.exists():
        for image_file in images_dir.glob("*.png"):
            # Upload to worlds/<world-name>/images/
            target_path = f"worlds/{client.client_id}/images/{image_file.name}"

            try:
                client.upload_file(str(image_file), target_path)
                image_path_mapping[f"images/{image_file.name}"] = target_path
                logger.debug(f"  Uploaded {image_file.name}")
            except Exception as e:
                logger.error(f"Failed to upload {image_file.name}: {e}")

    # Update gallery HTML with FoundryVTT paths
    gallery_html = gallery_file.read_text()
    for old_path, new_path in image_path_mapping.items():
        gallery_html = gallery_html.replace(old_path, new_path)

    # Create gallery page
    gallery_page = {
        "name": "Scene Gallery",
        "type": "text",
        "text": {
            "content": gallery_html,
            "format": 1
        }
    }

    logger.info("✓ Scene gallery uploaded")
    return gallery_page
```

**Step 3: Update journal creation to include gallery**

In main upload function:

```python
    # Create regular pages
    pages = [...]

    # Add scene gallery page
    gallery_page = upload_scene_gallery(client, run_dir, journal_name)
    if gallery_page:
        pages.append(gallery_page)

    # Create/update journal
    client.create_or_replace_journal(journal_name, pages=pages)
```

**Step 4: Test with FoundryVTT (manual)**

Run: `uv run python src/foundry/upload_journal_to_foundry.py --run-dir output/runs/latest`
Expected: Journal created with scene gallery page at end

**Step 5: Commit**

```bash
git add src/foundry/upload_journal_to_foundry.py
git commit -m "feat: upload scene gallery to FoundryVTT as journal page"
```

---

## Task 9: Add Configuration Options

**Files:**
- Modify: `.env.example`
- Create: `docs/plans/scene-artwork-config.md`

**Step 1: Add configuration to .env.example**

```bash
# Scene Artwork Generation
ENABLE_SCENE_ARTWORK=true
IMAGE_STYLE_PROMPT=fantasy illustration, D&D 5e art style, detailed environment, high quality
IMAGE_OUTPUT_DIR=scene_artwork
```

**Step 2: Create configuration documentation**

```markdown
# Scene Artwork Configuration

## Environment Variables

### `ENABLE_SCENE_ARTWORK`
- **Type:** Boolean (`true`/`false`)
- **Default:** `true`
- **Description:** Enable/disable scene artwork generation in full pipeline

### `IMAGE_STYLE_PROMPT`
- **Type:** String
- **Default:** `"fantasy illustration, D&D 5e art style, detailed environment, high quality"`
- **Description:** Style prompt for Gemini Imagen when generating scene artwork

### `IMAGE_OUTPUT_DIR`
- **Type:** String
- **Default:** `"scene_artwork"`
- **Description:** Directory name for scene artwork output (relative to run directory)

## Usage Examples

**Default settings:**
```bash
uv run python scripts/full_pipeline.py
```

**Custom style:**
```bash
IMAGE_STYLE_PROMPT="top-down battle map, grid overlay, tactical view" uv run python scripts/full_pipeline.py
```

**Disable scene generation:**
```bash
ENABLE_SCENE_ARTWORK=false uv run python scripts/full_pipeline.py
# Or use flag:
uv run python scripts/full_pipeline.py --skip-scenes
```

## Cost Considerations

Scene artwork generation uses Gemini Imagen API, which has per-image costs:
- ~$0.02-0.10 per image (check current Gemini pricing)
- A typical D&D module chapter may have 10-30 scenes
- Total cost per chapter: ~$0.20-$3.00

**Recommendations:**
1. Start with a single chapter to test (`--xml-file` flag)
2. Review generated scenes before generating full module
3. Use `--skip-scenes` flag to skip artwork in draft runs
```

**Step 3: Commit**

```bash
git add .env.example docs/plans/scene-artwork-config.md
git commit -m "docs: add scene artwork configuration options"
```

---

## Task 10: Update Documentation

**Files:**
- Modify: `CLAUDE.md`
- Modify: `docs/plans/roadmap.md`

**Step 1: Add scene extraction to CLAUDE.md architecture section**

Under "Processing Pipeline", add new step:

```markdown
2.5. **Scene Artwork Generation** (`scripts/generate_scene_art.py`):
   - Input: Chapter XML from `output/runs/<timestamp>/documents/`
   - Output: Scene images and gallery HTML in `output/runs/<timestamp>/scene_artwork/`
   - Post-processing workflow using Gemini for context extraction and scene identification
   - Gemini Imagen for artwork generation
```

Add to "Common Commands":

```bash
# Generate scene artwork for a run
uv run python scripts/generate_scene_art.py --run-dir output/runs/20241023_123456

# Generate for single chapter with custom style
uv run python scripts/generate_scene_art.py --xml-file output/runs/latest/documents/chapter_01.xml --style "top-down battle map"
```

**Step 2: Update roadmap.md to mark feature as completed**

Change status from "💭 Conceptual" to "✔️ Completed":

```markdown
### 1. AI-Generated Scene Artwork

**Status:** ✔️ Completed (2025-10-23)

**Implementation:** Post-processing workflow with Gemini context extraction, scene identification, and Imagen artwork generation. Creates FoundryVTT journal page with scene gallery.

**Files:**
- `src/scene_extraction/` - Core extraction and generation modules
- `scripts/generate_scene_art.py` - Main processing script
- Integrated into `scripts/full_pipeline.py` as optional step
```

**Step 3: Commit**

```bash
git add CLAUDE.md docs/plans/roadmap.md
git commit -m "docs: update docs for scene artwork feature"
```

---

## Execution Complete

**Plan saved to:** `docs/plans/2025-10-23-scene-extraction-and-artwork.md`

**Total tasks:** 10
**Estimated time:** 4-6 hours (with TDD workflow)

---

## Execution Options

**Plan complete and saved to `docs/plans/2025-10-23-scene-extraction-and-artwork.md`. Two execution options:**

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

**Which approach?**

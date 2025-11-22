# Actor/NPC Extraction and Management Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extract D&D 5e stat blocks and NPCs from module PDFs, create FoundryVTT Actor entities with compendium linking.

**Architecture:** Three-stage pipeline: (1) Tag stat blocks during XML generation, (2) Parse stat blocks into structured data with Gemini, (3) Extract NPCs via post-processing analysis, (4) Create FoundryVTT Actors with compendium reuse. Named NPCs are bio-only Actors that link to creature stat block compendium entries via @UUID syntax.

**Tech Stack:** Pydantic for data validation, Gemini API for parsing, FoundryVTT REST API, pytest for testing

---

## Prerequisites

- Gemini API configured (`GeminiImageAPI` in `.env`)
- FoundryVTT REST API configured (relay server, API key, client ID)
- Existing `src/util/gemini.py` and `src/foundry/client.py` infrastructure
- Test PDF with stat blocks (`Lost_Mine_of_Phandelver_test.pdf`)

---

## Task 1: Create Pydantic Models for Stat Blocks and NPCs

**Files:**
- Create: `src/actors/__init__.py`
- Create: `src/actors/models.py`
- Test: `tests/actors/__init__.py`
- Test: `tests/actors/test_models.py`

### Step 1: Write failing test for StatBlock model

Create test file structure and write first model validation test.

```python
# tests/actors/__init__.py
"""Tests for actor/NPC extraction modules."""
```

```python
# tests/actors/test_models.py
"""Tests for actor Pydantic models."""

import pytest
from pydantic import ValidationError
from actors.models import StatBlock


@pytest.mark.unit
class TestStatBlockModel:
    """Test StatBlock Pydantic model."""

    def test_stat_block_valid_minimal(self):
        """Test StatBlock with minimal required fields."""
        stat_block = StatBlock(
            name="Goblin",
            raw_text="Goblin stat block text...",
            armor_class=15,
            hit_points=7,
            challenge_rating=0.25
        )
        assert stat_block.name == "Goblin"
        assert stat_block.armor_class == 15
        assert stat_block.hit_points == 7
        assert stat_block.challenge_rating == 0.25
        assert stat_block.raw_text == "Goblin stat block text..."

    def test_stat_block_valid_complete(self):
        """Test StatBlock with all optional fields."""
        stat_block = StatBlock(
            name="Goblin Boss",
            raw_text="Goblin Boss stat block...",
            armor_class=17,
            hit_points=21,
            challenge_rating=1.0,
            size="Small",
            type="humanoid",
            alignment="neutral evil",
            abilities={"STR": 10, "DEX": 14, "CON": 10, "INT": 10, "WIS": 8, "CHA": 10},
            speed="30 ft.",
            senses="darkvision 60 ft.",
            languages="Common, Goblin"
        )
        assert stat_block.size == "Small"
        assert stat_block.type == "humanoid"
        assert stat_block.abilities["DEX"] == 14

    def test_stat_block_invalid_ac(self):
        """Test StatBlock rejects invalid armor class."""
        with pytest.raises(ValidationError):
            StatBlock(
                name="Invalid",
                raw_text="text",
                armor_class=50,  # Too high
                hit_points=10,
                challenge_rating=1.0
            )

    def test_stat_block_missing_required(self):
        """Test StatBlock requires all required fields."""
        with pytest.raises(ValidationError):
            StatBlock(
                name="Missing Fields",
                raw_text="text"
                # Missing AC, HP, CR
            )
```

### Step 2: Run test to verify it fails

```bash
uv run pytest tests/actors/test_models.py::TestStatBlockModel::test_stat_block_valid_minimal -v
```

Expected: `ModuleNotFoundError: No module named 'actors'`

### Step 3: Write minimal StatBlock model implementation

```python
# src/actors/__init__.py
"""Actor and NPC extraction modules."""

from .models import StatBlock, NPC

__all__ = ["StatBlock", "NPC"]
```

```python
# src/actors/models.py
"""Pydantic models for D&D 5e stat blocks and NPCs."""

from typing import Optional, Dict
from pydantic import BaseModel, field_validator


class StatBlock(BaseModel):
    """D&D 5e stat block structure."""

    # Always preserve original text
    name: str
    raw_text: str

    # Required D&D 5e fields
    armor_class: int
    hit_points: int
    challenge_rating: float

    # Optional fields
    size: Optional[str] = None
    type: Optional[str] = None
    alignment: Optional[str] = None
    abilities: Optional[Dict[str, int]] = None  # STR, DEX, CON, INT, WIS, CHA
    speed: Optional[str] = None
    senses: Optional[str] = None
    languages: Optional[str] = None
    traits: Optional[str] = None  # Special traits/features
    actions: Optional[str] = None  # Actions section

    @field_validator('armor_class')
    @classmethod
    def validate_ac(cls, v: int) -> int:
        """Validate armor class is in valid range."""
        if not (1 <= v <= 30):
            raise ValueError(f"Armor class {v} out of range (1-30)")
        return v

    @field_validator('hit_points')
    @classmethod
    def validate_hp(cls, v: int) -> int:
        """Validate hit points are positive."""
        if v < 1:
            raise ValueError(f"Hit points must be positive, got {v}")
        return v

    @field_validator('challenge_rating')
    @classmethod
    def validate_cr(cls, v: float) -> float:
        """Validate challenge rating is valid."""
        valid_crs = [0, 0.125, 0.25, 0.5] + list(range(1, 31))
        if v not in valid_crs:
            raise ValueError(f"Invalid challenge rating: {v}")
        return v


class NPC(BaseModel):
    """Named NPC with plot context and stat block reference."""

    name: str
    creature_stat_block_name: str  # Name of creature stat block this NPC uses
    description: str
    plot_relevance: str
    location: Optional[str] = None
    first_appearance_section: Optional[str] = None  # Where NPC first appears in module
```

### Step 4: Run tests to verify they pass

```bash
uv run pytest tests/actors/test_models.py::TestStatBlockModel -v
```

Expected: All 4 tests PASS

### Step 5: Write test for NPC model

```python
# Add to tests/actors/test_models.py

from actors.models import NPC


@pytest.mark.unit
class TestNPCModel:
    """Test NPC Pydantic model."""

    def test_npc_valid_minimal(self):
        """Test NPC with minimal required fields."""
        npc = NPC(
            name="Klarg",
            creature_stat_block_name="Goblin Boss",
            description="Leader of the Cragmaw goblins",
            plot_relevance="Guards the stolen supplies"
        )
        assert npc.name == "Klarg"
        assert npc.creature_stat_block_name == "Goblin Boss"
        assert npc.location is None

    def test_npc_valid_complete(self):
        """Test NPC with all optional fields."""
        npc = NPC(
            name="Sildar Hallwinter",
            creature_stat_block_name="Human Fighter",
            description="Member of the Lords' Alliance",
            plot_relevance="Captured by goblins, needs rescue",
            location="Cragmaw Hideout",
            first_appearance_section="Chapter 1 → Goblin Ambush"
        )
        assert npc.location == "Cragmaw Hideout"
        assert npc.first_appearance_section == "Chapter 1 → Goblin Ambush"

    def test_npc_missing_required(self):
        """Test NPC requires all required fields."""
        with pytest.raises(ValidationError):
            NPC(
                name="Incomplete",
                description="Missing creature type"
                # Missing creature_stat_block_name and plot_relevance
            )
```

### Step 6: Run NPC tests to verify they pass

```bash
uv run pytest tests/actors/test_models.py::TestNPCModel -v
```

Expected: All 3 tests PASS

### Step 7: Commit models

```bash
git add src/actors/ tests/actors/
git commit -m "feat: add StatBlock and NPC Pydantic models

- StatBlock model with validation for AC, HP, CR
- NPC model with creature reference and plot context
- Comprehensive unit tests for both models

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 2: Create Stat Block Parser with Gemini

**Files:**
- Create: `src/actors/parse_stat_blocks.py`
- Test: `tests/actors/test_parse_stat_blocks.py`
- Test fixtures: `tests/actors/fixtures/sample_stat_block.txt`

### Step 1: Create sample stat block fixture

```bash
mkdir -p tests/actors/fixtures
```

```text
# tests/actors/fixtures/sample_stat_block.txt
GOBLIN
Small humanoid (goblinoid), neutral evil

Armor Class 15 (leather armor, shield)
Hit Points 7 (2d6)
Speed 30 ft.

STR     DEX     CON     INT     WIS     CHA
8 (-1)  14 (+2) 10 (+0) 10 (+0) 8 (-1)  8 (-1)

Skills Stealth +6
Senses darkvision 60 ft., passive Perception 9
Languages Common, Goblin
Challenge 1/4 (50 XP)

Nimble Escape. The goblin can take the Disengage or Hide action as a bonus action on each of its turns.

ACTIONS
Scimitar. Melee Weapon Attack: +4 to hit, reach 5 ft., one target. Hit: 5 (1d6 + 2) slashing damage.
Shortbow. Ranged Weapon Attack: +4 to hit, range 80/320 ft., one target. Hit: 5 (1d6 + 2) piercing damage.
```

### Step 2: Write failing test for stat block parsing

```python
# tests/actors/test_parse_stat_blocks.py
"""Tests for stat block parsing with Gemini."""

import pytest
from pathlib import Path
from actors.parse_stat_blocks import parse_stat_block_with_gemini
from actors.models import StatBlock


@pytest.mark.integration
@pytest.mark.requires_api
class TestStatBlockParsing:
    """Test stat block parsing with real Gemini API calls."""

    def test_parse_goblin_stat_block(self, check_api_key):
        """Test parsing a complete goblin stat block."""
        # Load sample stat block
        fixture_path = Path(__file__).parent / "fixtures" / "sample_stat_block.txt"
        with open(fixture_path, 'r') as f:
            raw_text = f.read()

        # Parse with Gemini
        stat_block = parse_stat_block_with_gemini(raw_text)

        # Verify structured data
        assert isinstance(stat_block, StatBlock)
        assert stat_block.name == "Goblin"
        assert stat_block.armor_class == 15
        assert stat_block.hit_points == 7
        assert stat_block.challenge_rating == 0.25
        assert stat_block.size == "Small"
        assert stat_block.type == "humanoid"
        assert stat_block.raw_text == raw_text

        # Verify abilities parsed
        assert stat_block.abilities is not None
        assert stat_block.abilities["STR"] == 8
        assert stat_block.abilities["DEX"] == 14


@pytest.mark.unit
class TestStatBlockParsingUnit:
    """Unit tests for stat block parsing (mocked)."""

    def test_parse_returns_stat_block_model(self):
        """Test parser returns StatBlock model (integration test required for full test)."""
        # This is a placeholder - real testing requires API
        # Just verify the function exists and has correct signature
        from actors.parse_stat_blocks import parse_stat_block_with_gemini
        import inspect

        sig = inspect.signature(parse_stat_block_with_gemini)
        assert 'raw_text' in sig.parameters
```

### Step 3: Run test to verify it fails

```bash
uv run pytest tests/actors/test_parse_stat_blocks.py::TestStatBlockParsingUnit::test_parse_returns_stat_block_model -v
```

Expected: `ModuleNotFoundError: No module named 'actors.parse_stat_blocks'`

### Step 4: Implement stat block parser

```python
# src/actors/parse_stat_blocks.py
"""Parse D&D 5e stat blocks using Gemini."""

import logging
import json
from typing import Optional
from util.gemini import GeminiAPI
from .models import StatBlock

logger = logging.getLogger(__name__)


def parse_stat_block_with_gemini(raw_text: str, api: Optional[GeminiAPI] = None) -> StatBlock:
    """
    Parse a D&D 5e stat block using Gemini.

    Args:
        raw_text: Raw stat block text
        api: Optional GeminiAPI instance (creates new one if not provided)

    Returns:
        Parsed StatBlock object

    Raises:
        ValueError: If parsing fails or result is invalid
        RuntimeError: If Gemini API call fails
    """
    if api is None:
        api = GeminiAPI()

    logger.debug(f"Parsing stat block (length: {len(raw_text)} chars)")

    # Construct parsing prompt
    prompt = f"""Parse this D&D 5e stat block into structured JSON.

Extract the following fields:
- name (string): Creature name
- armor_class (integer): AC value only (not the parenthetical armor type)
- hit_points (integer): HP value only (not the dice formula)
- challenge_rating (float): CR as decimal (1/4 = 0.25, 1/2 = 0.5)
- size (string, optional): Creature size
- type (string, optional): Creature type
- alignment (string, optional): Alignment
- abilities (object, optional): {{STR: int, DEX: int, CON: int, INT: int, WIS: int, CHA: int}}
- speed (string, optional): Speed description
- senses (string, optional): Senses description
- languages (string, optional): Languages
- traits (string, optional): Special traits (everything between stats and ACTIONS)
- actions (string, optional): Actions section (everything after ACTIONS header)

Return ONLY valid JSON with these exact field names. Do not include any markdown formatting or explanation.

Stat block:
{raw_text}"""

    try:
        # Call Gemini
        response = api.generate_content(prompt)
        response_text = response.text.strip()

        # Remove markdown code blocks if present
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            # Remove first and last lines (``` markers)
            response_text = "\n".join(lines[1:-1])
            # Remove language identifier if present
            if response_text.startswith("json"):
                response_text = response_text[4:].strip()

        # Parse JSON
        parsed_data = json.loads(response_text)

        # Add raw_text to parsed data
        parsed_data["raw_text"] = raw_text

        # Create and validate StatBlock
        stat_block = StatBlock(**parsed_data)

        logger.info(f"Successfully parsed stat block: {stat_block.name} (CR {stat_block.challenge_rating})")
        return stat_block

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Gemini response as JSON: {e}")
        logger.debug(f"Response text: {response_text}")
        raise ValueError(f"Invalid JSON from Gemini: {e}") from e

    except Exception as e:
        logger.error(f"Failed to parse stat block: {e}")
        raise RuntimeError(f"Stat block parsing failed: {e}") from e
```

### Step 5: Run unit test to verify it passes

```bash
uv run pytest tests/actors/test_parse_stat_blocks.py::TestStatBlockParsingUnit -v
```

Expected: PASS

### Step 6: Run integration test with real API

```bash
uv run pytest tests/actors/test_parse_stat_blocks.py::TestStatBlockParsing::test_parse_goblin_stat_block -v
```

Expected: PASS (makes real Gemini API call)

### Step 7: Commit stat block parser

```bash
git add src/actors/parse_stat_blocks.py tests/actors/test_parse_stat_blocks.py tests/actors/fixtures/
git commit -m "feat: add Gemini-powered stat block parser

- Parse raw D&D 5e stat blocks into StatBlock models
- Gemini extracts structured data (AC, HP, CR, abilities, etc.)
- Integration tests with real API calls
- Sample fixture for testing

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 3: Extract Stat Blocks from Generated XML

**Files:**
- Create: `src/actors/extract_stat_blocks.py`
- Test: `tests/actors/test_extract_stat_blocks.py`
- Test fixtures: `tests/actors/fixtures/sample_chapter_with_stat_blocks.xml`

### Step 1: Create XML fixture with stat blocks

```xml
<!-- tests/actors/fixtures/sample_chapter_with_stat_blocks.xml -->
<Chapter_01_Introduction>
    <page number="1">
        <section>Goblin Ambush</section>
        <p>The party encounters goblins on the road.</p>

        <stat_block name="Goblin">
GOBLIN
Small humanoid (goblinoid), neutral evil

Armor Class 15 (leather armor, shield)
Hit Points 7 (2d6)
Speed 30 ft.

STR     DEX     CON     INT     WIS     CHA
8 (-1)  14 (+2) 10 (+0) 10 (+0) 8 (-1)  8 (-1)

Challenge 1/4 (50 XP)
        </stat_block>
    </page>

    <page number="2">
        <section>Cragmaw Hideout</section>
        <p>Area 1 contains the goblin boss Klarg.</p>

        <stat_block name="Goblin Boss">
GOBLIN BOSS
Small humanoid (goblinoid), neutral evil

Armor Class 17 (chain shirt, shield)
Hit Points 21 (6d6)
Speed 30 ft.

STR     DEX     CON     INT     WIS     CHA
10 (+0) 14 (+2) 10 (+0) 10 (+0) 8 (-1)  10 (+0)

Challenge 1 (200 XP)
        </stat_block>
    </page>
</Chapter_01_Introduction>
```

### Step 2: Write failing test for XML extraction

```python
# tests/actors/test_extract_stat_blocks.py
"""Tests for extracting stat blocks from XML."""

import pytest
from pathlib import Path
from actors.extract_stat_blocks import extract_stat_blocks_from_xml


@pytest.mark.unit
class TestExtractStatBlocksFromXML:
    """Test extracting raw stat block text from XML."""

    def test_extract_finds_stat_blocks(self):
        """Test extraction finds all stat block elements."""
        fixture_path = Path(__file__).parent / "fixtures" / "sample_chapter_with_stat_blocks.xml"

        stat_blocks = extract_stat_blocks_from_xml(str(fixture_path))

        assert len(stat_blocks) == 2
        assert stat_blocks[0]["name"] == "Goblin"
        assert stat_blocks[1]["name"] == "Goblin Boss"
        assert "Small humanoid" in stat_blocks[0]["raw_text"]
        assert "Challenge 1/4" in stat_blocks[0]["raw_text"]

    def test_extract_empty_xml(self):
        """Test extraction with XML containing no stat blocks."""
        # Create temporary XML without stat blocks
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write("<Chapter><page>No stat blocks here</page></Chapter>")
            temp_path = f.name

        stat_blocks = extract_stat_blocks_from_xml(temp_path)

        assert len(stat_blocks) == 0

    def test_extract_invalid_xml(self):
        """Test extraction handles malformed XML."""
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write("<Chapter><unclosed>")
            temp_path = f.name

        with pytest.raises(Exception):  # xml.etree.ElementTree.ParseError
            extract_stat_blocks_from_xml(temp_path)


@pytest.mark.integration
@pytest.mark.requires_api
class TestExtractAndParseStatBlocks:
    """Integration test: extract from XML and parse with Gemini."""

    def test_full_extraction_pipeline(self, check_api_key):
        """Test complete workflow: XML → raw text → parsed StatBlock."""
        from actors.extract_stat_blocks import extract_and_parse_stat_blocks

        fixture_path = Path(__file__).parent / "fixtures" / "sample_chapter_with_stat_blocks.xml"

        parsed_stat_blocks = extract_and_parse_stat_blocks(str(fixture_path))

        assert len(parsed_stat_blocks) == 2

        # Check first stat block
        goblin = parsed_stat_blocks[0]
        assert goblin.name == "Goblin"
        assert goblin.armor_class == 15
        assert goblin.hit_points == 7
        assert goblin.challenge_rating == 0.25

        # Check second stat block
        boss = parsed_stat_blocks[1]
        assert boss.name == "Goblin Boss"
        assert boss.challenge_rating == 1.0
```

### Step 3: Run test to verify it fails

```bash
uv run pytest tests/actors/test_extract_stat_blocks.py::TestExtractStatBlocksFromXML::test_extract_finds_stat_blocks -v
```

Expected: `ModuleNotFoundError: No module named 'actors.extract_stat_blocks'`

### Step 4: Implement XML extraction

```python
# src/actors/extract_stat_blocks.py
"""Extract stat blocks from generated XML files."""

import logging
import xml.etree.ElementTree as ET
from typing import List, Dict
from pathlib import Path
from util.gemini import GeminiAPI
from .models import StatBlock
from .parse_stat_blocks import parse_stat_block_with_gemini

logger = logging.getLogger(__name__)


def extract_stat_blocks_from_xml(xml_file: str) -> List[Dict[str, str]]:
    """
    Extract raw stat block text from XML file.

    Finds all <stat_block name="...">raw text</stat_block> elements.

    Args:
        xml_file: Path to XML file

    Returns:
        List of dicts with 'name' and 'raw_text' keys

    Raises:
        FileNotFoundError: If XML file doesn't exist
        xml.etree.ElementTree.ParseError: If XML is malformed
    """
    xml_path = Path(xml_file)
    if not xml_path.exists():
        raise FileNotFoundError(f"XML file not found: {xml_file}")

    logger.debug(f"Extracting stat blocks from: {xml_file}")

    # Parse XML
    tree = ET.parse(xml_file)
    root = tree.getroot()

    # Find all stat_block elements
    stat_block_elements = root.findall(".//stat_block")

    stat_blocks = []
    for elem in stat_block_elements:
        name = elem.get("name")
        raw_text = elem.text.strip() if elem.text else ""

        if not name:
            logger.warning(f"Found stat_block without name attribute, skipping")
            continue

        if not raw_text:
            logger.warning(f"Stat block '{name}' has no text content, skipping")
            continue

        stat_blocks.append({
            "name": name,
            "raw_text": raw_text
        })

    logger.info(f"Extracted {len(stat_blocks)} stat block(s) from {xml_file}")
    return stat_blocks


def extract_and_parse_stat_blocks(
    xml_file: str,
    api: GeminiAPI = None
) -> List[StatBlock]:
    """
    Extract stat blocks from XML and parse into structured data.

    Args:
        xml_file: Path to XML file
        api: Optional GeminiAPI instance (creates new one if not provided)

    Returns:
        List of parsed StatBlock objects

    Raises:
        FileNotFoundError: If XML file doesn't exist
        ValueError: If parsing fails
    """
    if api is None:
        api = GeminiAPI()

    # Extract raw stat blocks
    raw_stat_blocks = extract_stat_blocks_from_xml(xml_file)

    if not raw_stat_blocks:
        logger.info(f"No stat blocks found in {xml_file}")
        return []

    # Parse each stat block
    parsed_stat_blocks = []
    for raw_block in raw_stat_blocks:
        try:
            stat_block = parse_stat_block_with_gemini(raw_block["raw_text"], api=api)
            parsed_stat_blocks.append(stat_block)
        except Exception as e:
            logger.error(f"Failed to parse stat block '{raw_block['name']}': {e}")
            # Continue with other stat blocks

    logger.info(f"Successfully parsed {len(parsed_stat_blocks)}/{len(raw_stat_blocks)} stat blocks")
    return parsed_stat_blocks
```

### Step 5: Run unit tests

```bash
uv run pytest tests/actors/test_extract_stat_blocks.py::TestExtractStatBlocksFromXML -v
```

Expected: All 3 tests PASS

### Step 6: Run integration test

```bash
uv run pytest tests/actors/test_extract_stat_blocks.py::TestExtractAndParseStatBlocks -v
```

Expected: PASS (makes real Gemini API calls)

### Step 7: Commit XML extraction

```bash
git add src/actors/extract_stat_blocks.py tests/actors/test_extract_stat_blocks.py tests/actors/fixtures/sample_chapter_with_stat_blocks.xml
git commit -m "feat: extract and parse stat blocks from XML

- Extract <stat_block> elements from generated XML
- Full pipeline: XML → raw text → parsed StatBlock models
- Integration tests with Gemini API
- Handles missing/malformed stat blocks gracefully

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 4: Create FoundryVTT Actor Manager

**Files:**
- Create: `src/foundry/actors.py`
- Test: `tests/foundry/test_actors.py`

### Step 1: Write failing test for actor search

```python
# tests/foundry/test_actors.py
"""Tests for FoundryVTT Actor manager."""

import pytest
from unittest.mock import Mock, patch
from foundry.actors import ActorManager


@pytest.mark.unit
class TestActorManagerSearch:
    """Test actor search operations."""

    def test_search_all_compendiums_found(self):
        """Test searching for actor returns UUID when found."""
        manager = ActorManager(
            relay_url="http://test",
            foundry_url="http://test",
            api_key="test",
            client_id="test"
        )

        # Mock search response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"uuid": "Actor.abc123", "name": "Goblin", "type": "npc"}
        ]

        with patch('requests.get', return_value=mock_response):
            uuid = manager.search_all_compendiums("Goblin")

        assert uuid == "Actor.abc123"

    def test_search_all_compendiums_not_found(self):
        """Test searching for actor returns None when not found."""
        manager = ActorManager(
            relay_url="http://test",
            foundry_url="http://test",
            api_key="test",
            client_id="test"
        )

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []

        with patch('requests.get', return_value=mock_response):
            uuid = manager.search_all_compendiums("Nonexistent")

        assert uuid is None

    def test_search_handles_network_error(self):
        """Test search handles network errors gracefully."""
        manager = ActorManager(
            relay_url="http://test",
            foundry_url="http://test",
            api_key="test",
            client_id="test"
        )

        with patch('requests.get', side_effect=Exception("Network error")):
            uuid = manager.search_all_compendiums("Goblin")

        assert uuid is None
```

### Step 2: Run test to verify it fails

```bash
uv run pytest tests/foundry/test_actors.py::TestActorManagerSearch::test_search_all_compendiums_found -v
```

Expected: `ModuleNotFoundError: No module named 'foundry.actors'`

### Step 3: Implement ActorManager with search

```python
# src/foundry/actors.py
"""FoundryVTT Actor operations."""

import logging
import requests
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class ActorManager:
    """Manages actor operations for FoundryVTT."""

    def __init__(self, relay_url: str, foundry_url: str, api_key: str, client_id: str):
        """
        Initialize actor manager.

        Args:
            relay_url: URL of the relay server
            foundry_url: URL of the FoundryVTT instance
            api_key: API key for authentication
            client_id: Client ID for the FoundryVTT instance
        """
        self.relay_url = relay_url
        self.foundry_url = foundry_url
        self.api_key = api_key
        self.client_id = client_id

    def search_all_compendiums(self, name: str) -> Optional[str]:
        """
        Search all user compendiums for actor by name.

        Args:
            name: Actor name to search for

        Returns:
            Actor UUID if found, None otherwise
        """
        url = f"{self.relay_url}/search"

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }

        # Use filter parameter (not type) for Actor filtering
        params = {
            "clientId": self.client_id,
            "filter": "Actor",
            "query": name
        }

        logger.debug(f"Searching for actor: {name}")

        try:
            response = requests.get(url, params=params, headers=headers, timeout=30)

            if response.status_code != 200:
                logger.warning(f"Actor search failed: {response.status_code}")
                return None

            results = response.json()

            # Handle empty results
            if not results or (isinstance(results, dict) and results.get("error")):
                logger.debug(f"No actor found with name: {name}")
                return None

            # Handle both list and dict response formats
            search_results = results if isinstance(results, list) else results.get("results", [])

            # Find exact name match
            for actor in search_results:
                if actor.get("name") == name:
                    uuid = actor.get("uuid")
                    logger.debug(f"Found actor: {name} (UUID: {uuid})")
                    return uuid

            logger.debug(f"No exact match found for actor: {name}")
            return None

        except Exception as e:
            logger.warning(f"Actor search request failed: {e}")
            return None
```

### Step 4: Run search tests

```bash
uv run pytest tests/foundry/test_actors.py::TestActorManagerSearch -v
```

Expected: All 3 tests PASS

### Step 5: Write test for creating creature actor

```python
# Add to tests/foundry/test_actors.py

from actors.models import StatBlock


@pytest.mark.unit
class TestActorManagerCreate:
    """Test actor creation operations."""

    def test_create_creature_actor(self):
        """Test creating a creature actor from stat block."""
        manager = ActorManager(
            relay_url="http://test",
            foundry_url="http://test",
            api_key="test",
            client_id="test"
        )

        stat_block = StatBlock(
            name="Goblin",
            raw_text="Goblin stat block...",
            armor_class=15,
            hit_points=7,
            challenge_rating=0.25,
            size="Small",
            type="humanoid",
            abilities={"STR": 8, "DEX": 14, "CON": 10, "INT": 10, "WIS": 8, "CHA": 8}
        )

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "entity": {"_id": "abc123"},
            "uuid": "Actor.abc123"
        }

        with patch('requests.post', return_value=mock_response) as mock_post:
            uuid = manager.create_creature_actor(stat_block)

        assert uuid == "Actor.abc123"

        # Verify request payload
        call_args = mock_post.call_args
        payload = call_args[1]["json"]
        assert payload["entityType"] == "Actor"
        assert payload["data"]["name"] == "Goblin"
        assert payload["data"]["type"] == "npc"
        assert payload["data"]["system"]["attributes"]["ac"]["value"] == 15
        assert payload["data"]["system"]["attributes"]["hp"]["value"] == 7

    def test_create_npc_actor_with_stat_block_link(self):
        """Test creating NPC actor with link to creature stat block."""
        from actors.models import NPC

        manager = ActorManager(
            relay_url="http://test",
            foundry_url="http://test",
            api_key="test",
            client_id="test"
        )

        npc = NPC(
            name="Klarg",
            creature_stat_block_name="Goblin Boss",
            description="Leader of the Cragmaw goblins",
            plot_relevance="Guards the stolen supplies",
            location="Cragmaw Hideout"
        )

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "entity": {"_id": "xyz789"},
            "uuid": "Actor.xyz789"
        }

        with patch('requests.post', return_value=mock_response) as mock_post:
            uuid = manager.create_npc_actor(npc, stat_block_uuid="Actor.boss123")

        assert uuid == "Actor.xyz789"

        # Verify biography includes stat block link
        payload = mock_post.call_args[1]["json"]
        bio = payload["data"]["system"]["details"]["biography"]["value"]
        assert "Klarg" in bio
        assert "Leader of the Cragmaw goblins" in bio
        assert "@UUID[Actor.boss123]" in bio

    def test_create_npc_actor_without_stat_block(self):
        """Test creating NPC actor when stat block not found."""
        from actors.models import NPC

        manager = ActorManager(
            relay_url="http://test",
            foundry_url="http://test",
            api_key="test",
            client_id="test"
        )

        npc = NPC(
            name="Mysterious Stranger",
            creature_stat_block_name="Unknown",
            description="A hooded figure",
            plot_relevance="Provides quest information"
        )

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "entity": {"_id": "mystery123"},
            "uuid": "Actor.mystery123"
        }

        with patch('requests.post', return_value=mock_response) as mock_post:
            uuid = manager.create_npc_actor(npc, stat_block_uuid=None)

        assert uuid == "Actor.mystery123"

        # Verify no stat block link in biography
        payload = mock_post.call_args[1]["json"]
        bio = payload["data"]["system"]["details"]["biography"]["value"]
        assert "@UUID" not in bio
```

### Step 6: Run test to verify it fails

```bash
uv run pytest tests/foundry/test_actors.py::TestActorManagerCreate::test_create_creature_actor -v
```

Expected: `AttributeError: 'ActorManager' object has no attribute 'create_creature_actor'`

### Step 7: Implement actor creation methods

```python
# Add to src/foundry/actors.py

from actors.models import StatBlock, NPC


class ActorManager:
    # ... (existing __init__ and search_all_compendiums methods)

    def create_creature_actor(self, stat_block: StatBlock) -> str:
        """
        Create a creature Actor from a stat block.

        Args:
            stat_block: Parsed StatBlock object

        Returns:
            Actor UUID

        Raises:
            RuntimeError: If creation fails
        """
        url = f"{self.relay_url}/create?clientId={self.client_id}"

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }

        # Map stat block to D&D 5e Actor structure
        actor_data = {
            "name": stat_block.name,
            "type": "npc",
            "system": {
                "attributes": {
                    "ac": {"value": stat_block.armor_class},
                    "hp": {
                        "value": stat_block.hit_points,
                        "max": stat_block.hit_points
                    }
                },
                "details": {
                    "cr": stat_block.challenge_rating,
                    "type": {
                        "value": stat_block.type or "",
                        "subtype": ""
                    },
                    "alignment": stat_block.alignment or "",
                    "biography": {
                        "value": f"<pre>{stat_block.raw_text}</pre>"
                    }
                }
            }
        }

        # Add abilities if present
        if stat_block.abilities:
            actor_data["system"]["abilities"] = {
                ability.lower(): {"value": value}
                for ability, value in stat_block.abilities.items()
            }

        payload = {
            "entityType": "Actor",
            "data": actor_data
        }

        logger.debug(f"Creating creature actor: {stat_block.name}")

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)

            if response.status_code != 200:
                logger.error(f"Failed to create actor: {response.status_code} - {response.text}")
                raise RuntimeError(
                    f"Failed to create actor: {response.status_code} - {response.text}"
                )

            result = response.json()
            uuid = result.get("uuid")
            logger.info(f"Created creature actor: {stat_block.name} (UUID: {uuid})")
            return uuid

        except requests.exceptions.RequestException as e:
            logger.error(f"Actor creation request failed: {e}")
            raise RuntimeError(f"Failed to create actor: {e}") from e

    def create_npc_actor(self, npc: NPC, stat_block_uuid: Optional[str] = None) -> str:
        """
        Create an NPC Actor with biography and optional stat block link.

        NPCs are bio-only Actors with no stats. If stat_block_uuid provided,
        biography includes @UUID link to the creature's stat block.

        Args:
            npc: NPC object with description and plot info
            stat_block_uuid: Optional UUID of creature stat block actor

        Returns:
            Actor UUID

        Raises:
            RuntimeError: If creation fails
        """
        url = f"{self.relay_url}/create?clientId={self.client_id}"

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }

        # Build biography HTML
        bio_parts = [
            f"<h2>{npc.name}</h2>",
            f"<p><strong>Description:</strong> {npc.description}</p>",
            f"<p><strong>Plot Role:</strong> {npc.plot_relevance}</p>"
        ]

        if npc.location:
            bio_parts.append(f"<p><strong>Location:</strong> {npc.location}</p>")

        if stat_block_uuid:
            bio_parts.append(
                f'<p><strong>Creature Stats:</strong> '
                f'@UUID[{stat_block_uuid}]{{View {npc.creature_stat_block_name} stats}}</p>'
            )

        bio_html = "\n".join(bio_parts)

        # Create bio-only NPC actor (no stats)
        actor_data = {
            "name": npc.name,
            "type": "npc",
            "system": {
                "details": {
                    "biography": {
                        "value": bio_html
                    }
                }
            }
        }

        payload = {
            "entityType": "Actor",
            "data": actor_data
        }

        logger.debug(f"Creating NPC actor: {npc.name}")

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)

            if response.status_code != 200:
                logger.error(f"Failed to create NPC: {response.status_code} - {response.text}")
                raise RuntimeError(
                    f"Failed to create NPC: {response.status_code} - {response.text}"
                )

            result = response.json()
            uuid = result.get("uuid")
            logger.info(f"Created NPC actor: {npc.name} (UUID: {uuid})")
            return uuid

        except requests.exceptions.RequestException as e:
            logger.error(f"NPC creation request failed: {e}")
            raise RuntimeError(f"Failed to create NPC: {e}") from e
```

### Step 8: Run actor creation tests

```bash
uv run pytest tests/foundry/test_actors.py::TestActorManagerCreate -v
```

Expected: All 3 tests PASS

### Step 9: Commit ActorManager

```bash
git add src/foundry/actors.py tests/foundry/test_actors.py
git commit -m "feat: add FoundryVTT ActorManager for creature/NPC creation

- Search all compendiums for existing actors by name
- Create creature actors from StatBlock models
- Create NPC bio actors with @UUID links to stat blocks
- Comprehensive unit tests with mocked API calls

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 5: Integrate ActorManager into FoundryClient

**Files:**
- Modify: `src/foundry/client.py`
- Test: `tests/foundry/test_client.py`

### Step 1: Write test for client delegation

```python
# Add to tests/foundry/test_client.py (if it exists, otherwise create it)

import pytest
from unittest.mock import Mock, patch
from foundry.client import FoundryClient


@pytest.mark.unit
class TestFoundryClientActorDelegation:
    """Test FoundryClient delegates to ActorManager."""

    def test_client_initializes_actor_manager(self):
        """Test client creates ActorManager instance."""
        with patch.dict('os.environ', {
            'FOUNDRY_RELAY_URL': 'http://relay',
            'FOUNDRY_URL': 'http://local',
            'FOUNDRY_API_KEY': 'key123',
            'FOUNDRY_CLIENT_ID': 'client123'
        }):
            client = FoundryClient(target="local")

        assert hasattr(client, 'actors')
        assert client.actors is not None

    def test_client_search_actors_delegates(self):
        """Test client.search_actor delegates to ActorManager."""
        with patch.dict('os.environ', {
            'FOUNDRY_RELAY_URL': 'http://relay',
            'FOUNDRY_URL': 'http://local',
            'FOUNDRY_API_KEY': 'key123',
            'FOUNDRY_CLIENT_ID': 'client123'
        }):
            client = FoundryClient(target="local")

        # Mock the actors manager
        client.actors = Mock()
        client.actors.search_all_compendiums.return_value = "Actor.abc123"

        uuid = client.search_actor("Goblin")

        client.actors.search_all_compendiums.assert_called_once_with("Goblin")
        assert uuid == "Actor.abc123"
```

### Step 2: Run test to verify it fails

```bash
uv run pytest tests/foundry/test_client.py::TestFoundryClientActorDelegation::test_client_initializes_actor_manager -v
```

Expected: `AttributeError: 'FoundryClient' object has no attribute 'actors'`

### Step 3: Integrate ActorManager into FoundryClient

```python
# Modify src/foundry/client.py

# Add import at top
from .actors import ActorManager

# In FoundryClient.__init__, after initializing journals and items:

        self.actors = ActorManager(
            relay_url=self.relay_url,
            foundry_url=self.foundry_url,
            api_key=self.api_key,
            client_id=self.client_id
        )

# Add delegation methods at end of class:

    # Actor operations (delegated to ActorManager)

    def search_actor(self, name: str) -> Optional[str]:
        """Search for actor by name in all compendiums."""
        return self.actors.search_all_compendiums(name)

    def create_creature_actor(self, stat_block) -> str:
        """Create creature actor from stat block."""
        return self.actors.create_creature_actor(stat_block)

    def create_npc_actor(self, npc, stat_block_uuid: Optional[str] = None) -> str:
        """Create NPC actor with optional stat block link."""
        return self.actors.create_npc_actor(npc, stat_block_uuid)
```

### Step 4: Run client delegation tests

```bash
uv run pytest tests/foundry/test_client.py::TestFoundryClientActorDelegation -v
```

Expected: All tests PASS

### Step 5: Commit client integration

```bash
git add src/foundry/client.py tests/foundry/test_client.py
git commit -m "feat: integrate ActorManager into FoundryClient

- Initialize ActorManager alongside JournalManager and ItemManager
- Add delegation methods: search_actor, create_creature_actor, create_npc_actor
- Tests verify proper delegation

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 6: Create NPC Extraction with Gemini

**Files:**
- Create: `src/actors/extract_npcs.py`
- Test: `tests/actors/test_extract_npcs.py`
- Test fixtures: `tests/actors/fixtures/sample_chapter_with_npcs.xml`

### Step 1: Create XML fixture with NPCs

```xml
<!-- tests/actors/fixtures/sample_chapter_with_npcs.xml -->
<Chapter_01_Introduction>
    <page number="1">
        <section>Goblin Ambush</section>
        <p>On the road to Phandalin, the party encounters a group of goblins led by a scout.</p>
    </page>

    <page number="2">
        <section>Cragmaw Hideout</section>
        <subsection>Area 1: Cave Mouth</subsection>
        <p>The entrance is guarded by goblins.</p>

        <subsection>Area 6: Goblin Den</subsection>
        <p>Klarg, a bugbear, leads the Cragmaw goblins from this chamber. He has taken Sildar Hallwinter prisoner.</p>
        <p>Klarg wears a tattered cloak and wields a morningstar. He is accompanied by his pet wolf, Ripper.</p>

        <stat_block name="Bugbear">
BUGBEAR
Medium humanoid (goblinoid), chaotic evil
Armor Class 16 (hide armor, shield)
Hit Points 27 (5d8 + 5)
Challenge 1 (200 XP)
        </stat_block>
    </page>

    <page number="3">
        <section>Prisoners</section>
        <p>Sildar Hallwinter is a human fighter and member of the Lords' Alliance.
        He was escorting Gundren Rockseeker to Phandalin when they were ambushed by goblins.
        Sildar knows that Gundren was taken to Cragmaw Castle but doesn't know where it is.</p>

        <stat_block name="Human Fighter">
HUMAN FIGHTER
Medium humanoid (human), lawful good
Armor Class 17 (chain mail)
Hit Points 32 (5d8 + 10)
Challenge 2 (450 XP)
        </stat_block>
    </page>
</Chapter_01_Introduction>
```

### Step 2: Write failing test for NPC extraction

```python
# tests/actors/test_extract_npcs.py
"""Tests for NPC extraction with Gemini."""

import pytest
from pathlib import Path
from actors.extract_npcs import identify_npcs_with_gemini
from actors.models import NPC


@pytest.mark.integration
@pytest.mark.requires_api
class TestNPCExtraction:
    """Test NPC extraction with real Gemini API calls."""

    def test_identify_npcs_from_xml(self, check_api_key):
        """Test Gemini identifies named NPCs from XML."""
        fixture_path = Path(__file__).parent / "fixtures" / "sample_chapter_with_npcs.xml"

        with open(fixture_path, 'r') as f:
            xml_content = f.read()

        npcs = identify_npcs_with_gemini(xml_content)

        # Should find at least Klarg and Sildar
        assert len(npcs) >= 2

        npc_names = [npc.name for npc in npcs]
        assert "Klarg" in npc_names
        assert "Sildar Hallwinter" in npc_names

        # Check Klarg details
        klarg = next(npc for npc in npcs if npc.name == "Klarg")
        assert klarg.creature_stat_block_name == "Bugbear"
        assert "goblin" in klarg.description.lower() or "cragmaw" in klarg.description.lower()
        assert klarg.location is not None

        # Check Sildar details
        sildar = next(npc for npc in npcs if npc.name == "Sildar Hallwinter")
        assert sildar.creature_stat_block_name == "Human Fighter"
        assert "lords" in sildar.description.lower() or "alliance" in sildar.description.lower()

    def test_identify_npcs_no_npcs(self, check_api_key):
        """Test extraction from XML with no named NPCs."""
        xml_content = """
        <Chapter>
            <page>
                <section>Empty Room</section>
                <p>This room contains nothing of interest.</p>
            </page>
        </Chapter>
        """

        npcs = identify_npcs_with_gemini(xml_content)

        assert len(npcs) == 0


@pytest.mark.unit
class TestNPCExtractionUnit:
    """Unit tests for NPC extraction."""

    def test_function_exists(self):
        """Verify function exists with correct signature."""
        from actors.extract_npcs import identify_npcs_with_gemini
        import inspect

        sig = inspect.signature(identify_npcs_with_gemini)
        assert 'xml_content' in sig.parameters
```

### Step 3: Run test to verify it fails

```bash
uv run pytest tests/actors/test_extract_npcs.py::TestNPCExtractionUnit::test_function_exists -v
```

Expected: `ModuleNotFoundError: No module named 'actors.extract_npcs'`

### Step 4: Implement NPC extraction

```python
# src/actors/extract_npcs.py
"""Extract named NPCs from generated XML using Gemini."""

import logging
import json
from typing import List, Optional
from util.gemini import GeminiAPI
from .models import NPC

logger = logging.getLogger(__name__)


def identify_npcs_with_gemini(
    xml_content: str,
    api: Optional[GeminiAPI] = None
) -> List[NPC]:
    """
    Identify named NPCs from XML content using Gemini.

    Analyzes the XML structure and narrative text to find named characters
    with plot relevance. Links NPCs to their creature stat blocks if available.

    Args:
        xml_content: XML content to analyze
        api: Optional GeminiAPI instance (creates new one if not provided)

    Returns:
        List of NPC objects

    Raises:
        RuntimeError: If Gemini API call fails
    """
    if api is None:
        api = GeminiAPI()

    logger.debug(f"Analyzing XML for NPCs (length: {len(xml_content)} chars)")

    # Construct NPC identification prompt
    prompt = f"""Analyze this D&D module XML and identify all named NPCs (non-player characters).

For each named NPC, extract:
- name (string): The NPC's name (e.g., "Klarg", "Sildar Hallwinter")
- creature_stat_block_name (string): The creature type/stat block this NPC uses (e.g., "Bugbear", "Human Fighter")
  - Look for nearby <stat_block> tags or descriptions like "Klarg, a bugbear" → "Bugbear"
  - Use the stat block name exactly as it appears in <stat_block name="...">
- description (string): Brief physical or personality description (1-2 sentences)
- plot_relevance (string): Why this NPC matters to the story (1-2 sentences)
- location (string, optional): Where the NPC is found (e.g., "Cragmaw Hideout", "Area 6")
- first_appearance_section (string, optional): Section where NPC first appears (e.g., "Chapter 1 → Goblin Ambush")

IMPORTANT:
- Only include NAMED characters (e.g., "Klarg", "Sildar"), NOT generic enemies ("goblins", "bandits")
- Link NPCs to stat blocks by finding nearby <stat_block name="..."> tags or creature type mentions
- If a stat block isn't found, infer the creature type from context (e.g., "human fighter" → "Human Fighter")

Return ONLY valid JSON array with these exact field names:
[
  {{
    "name": "Klarg",
    "creature_stat_block_name": "Bugbear",
    "description": "Leader of the Cragmaw goblins, wears a tattered cloak",
    "plot_relevance": "Guards stolen supplies, has taken Sildar prisoner",
    "location": "Cragmaw Hideout, Area 6",
    "first_appearance_section": "Chapter 1 → Cragmaw Hideout"
  }}
]

If no named NPCs found, return empty array: []

Do not include markdown formatting or explanation.

XML content:
{xml_content}"""

    try:
        # Call Gemini
        response = api.generate_content(prompt)
        response_text = response.text.strip()

        # Remove markdown code blocks if present
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            response_text = "\n".join(lines[1:-1])
            if response_text.startswith("json"):
                response_text = response_text[4:].strip()

        # Parse JSON
        parsed_data = json.loads(response_text)

        # Validate and create NPC objects
        npcs = []
        for npc_data in parsed_data:
            try:
                npc = NPC(**npc_data)
                npcs.append(npc)
            except Exception as e:
                logger.warning(f"Failed to validate NPC data: {e}")
                logger.debug(f"Invalid NPC data: {npc_data}")
                continue

        logger.info(f"Identified {len(npcs)} NPC(s) from XML")
        return npcs

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Gemini response as JSON: {e}")
        logger.debug(f"Response text: {response_text}")
        raise RuntimeError(f"Invalid JSON from Gemini: {e}") from e

    except Exception as e:
        logger.error(f"Failed to extract NPCs: {e}")
        raise RuntimeError(f"NPC extraction failed: {e}") from e
```

### Step 5: Run unit test

```bash
uv run pytest tests/actors/test_extract_npcs.py::TestNPCExtractionUnit -v
```

Expected: PASS

### Step 6: Run integration test with real API

```bash
uv run pytest tests/actors/test_extract_npcs.py::TestNPCExtraction::test_identify_npcs_from_xml -v
```

Expected: PASS (makes real Gemini API call)

### Step 7: Commit NPC extraction

```bash
git add src/actors/extract_npcs.py tests/actors/test_extract_npcs.py tests/actors/fixtures/sample_chapter_with_npcs.xml
git commit -m "feat: add Gemini-powered NPC extraction from XML

- Analyze XML narrative to identify named NPCs
- Link NPCs to creature stat blocks automatically
- Extract plot relevance and location context
- Integration tests with real Gemini API calls

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 7: Create Actor Processing Script

**Files:**
- Create: `src/actors/process_actors.py` (orchestration script)
- Test: `tests/actors/test_process_actors.py`

### Step 1: Write failing test for actor processing workflow

```python
# tests/actors/test_process_actors.py
"""Tests for actor processing workflow."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from actors.process_actors import process_actors_for_run


@pytest.mark.unit
class TestActorProcessingWorkflow:
    """Test complete actor processing workflow (mocked)."""

    def test_process_actors_workflow(self):
        """Test complete workflow: extract stat blocks → parse → extract NPCs → create actors."""

        # Mock XML file
        run_dir = "/tmp/test_run"
        xml_file = f"{run_dir}/documents/chapter_01.xml"

        # Mock dependencies
        with patch('actors.process_actors.extract_and_parse_stat_blocks') as mock_extract_sb, \
             patch('actors.process_actors.identify_npcs_with_gemini') as mock_extract_npcs, \
             patch('actors.process_actors.FoundryClient') as mock_client_class, \
             patch('pathlib.Path.glob') as mock_glob:

            # Setup mocks
            mock_glob.return_value = [Path(xml_file)]

            # Mock stat blocks
            from actors.models import StatBlock
            mock_stat_block = StatBlock(
                name="Goblin",
                raw_text="Goblin text",
                armor_class=15,
                hit_points=7,
                challenge_rating=0.25
            )
            mock_extract_sb.return_value = [mock_stat_block]

            # Mock NPCs
            from actors.models import NPC
            mock_npc = NPC(
                name="Klarg",
                creature_stat_block_name="Goblin Boss",
                description="Leader",
                plot_relevance="Guards supplies"
            )
            mock_extract_npcs.return_value = [mock_npc]

            # Mock FoundryClient
            mock_client = MagicMock()
            mock_client.search_actor.return_value = None  # Not found in compendium
            mock_client.create_creature_actor.return_value = "Actor.creature123"
            mock_client.create_npc_actor.return_value = "Actor.npc456"
            mock_client_class.return_value = mock_client

            # Run workflow
            result = process_actors_for_run(run_dir, target="local")

            # Verify calls
            mock_extract_sb.assert_called_once()
            mock_extract_npcs.assert_called_once()
            mock_client.search_actor.assert_called()
            mock_client.create_creature_actor.assert_called_once_with(mock_stat_block)
            mock_client.create_npc_actor.assert_called_once()

            # Verify result
            assert result["stat_blocks_found"] == 1
            assert result["stat_blocks_created"] == 1
            assert result["npcs_found"] == 1
            assert result["npcs_created"] == 1

    def test_process_actors_reuses_compendium(self):
        """Test workflow reuses existing compendium actors."""

        run_dir = "/tmp/test_run"
        xml_file = f"{run_dir}/documents/chapter_01.xml"

        with patch('actors.process_actors.extract_and_parse_stat_blocks') as mock_extract_sb, \
             patch('actors.process_actors.identify_npcs_with_gemini') as mock_extract_npcs, \
             patch('actors.process_actors.FoundryClient') as mock_client_class, \
             patch('pathlib.Path.glob') as mock_glob:

            mock_glob.return_value = [Path(xml_file)]

            from actors.models import StatBlock, NPC
            mock_stat_block = StatBlock(
                name="Goblin",
                raw_text="text",
                armor_class=15,
                hit_points=7,
                challenge_rating=0.25
            )
            mock_extract_sb.return_value = [mock_stat_block]

            mock_npc = NPC(
                name="Snarf",
                creature_stat_block_name="Goblin",
                description="Scout",
                plot_relevance="Ambushes party"
            )
            mock_extract_npcs.return_value = [mock_npc]

            # Mock client finds Goblin in compendium
            mock_client = MagicMock()
            mock_client.search_actor.return_value = "Actor.existing_goblin"
            mock_client.create_npc_actor.return_value = "Actor.npc789"
            mock_client_class.return_value = mock_client

            result = process_actors_for_run(run_dir, target="local")

            # Verify Goblin NOT created (reused from compendium)
            mock_client.create_creature_actor.assert_not_called()

            # Verify NPC created with existing Goblin UUID
            call_args = mock_client.create_npc_actor.call_args
            assert call_args[0][1] == "Actor.existing_goblin"  # stat_block_uuid

            assert result["stat_blocks_reused"] == 1
```

### Step 2: Run test to verify it fails

```bash
uv run pytest tests/actors/test_process_actors.py::TestActorProcessingWorkflow::test_process_actors_workflow -v
```

Expected: `ModuleNotFoundError: No module named 'actors.process_actors'`

### Step 3: Implement actor processing orchestration

```python
# src/actors/process_actors.py
"""Orchestrate actor processing workflow for a run directory."""

import logging
from pathlib import Path
from typing import Dict, Any, Literal
from foundry.client import FoundryClient
from util.gemini import GeminiAPI
from .extract_stat_blocks import extract_and_parse_stat_blocks
from .extract_npcs import identify_npcs_with_gemini

logger = logging.getLogger(__name__)


def process_actors_for_run(
    run_dir: str,
    target: Literal["local", "forge"] = "local"
) -> Dict[str, Any]:
    """
    Process all actors for a run directory.

    Complete workflow:
    1. Extract and parse stat blocks from XML files
    2. Extract NPCs from XML files
    3. Create/lookup creature actors in FoundryVTT
    4. Create NPC actors with stat block links

    Args:
        run_dir: Path to run directory (contains documents/ folder)
        target: FoundryVTT target environment

    Returns:
        Dict with processing statistics

    Raises:
        FileNotFoundError: If run directory doesn't exist
        RuntimeError: If processing fails
    """
    run_path = Path(run_dir)
    if not run_path.exists():
        raise FileNotFoundError(f"Run directory not found: {run_dir}")

    documents_dir = run_path / "documents"
    if not documents_dir.exists():
        raise FileNotFoundError(f"Documents directory not found: {documents_dir}")

    logger.info(f"Processing actors for run: {run_dir}")

    # Initialize APIs
    gemini_api = GeminiAPI()
    foundry_client = FoundryClient(target=target)

    # Statistics
    stats = {
        "stat_blocks_found": 0,
        "stat_blocks_created": 0,
        "stat_blocks_reused": 0,
        "npcs_found": 0,
        "npcs_created": 0,
        "errors": []
    }

    # Step 1: Extract and parse stat blocks from all XML files
    logger.info("Step 1: Extracting stat blocks from XML files")
    all_stat_blocks = []
    xml_files = list(documents_dir.glob("*.xml"))

    for xml_file in xml_files:
        try:
            stat_blocks = extract_and_parse_stat_blocks(str(xml_file), api=gemini_api)
            all_stat_blocks.extend(stat_blocks)
            logger.info(f"Found {len(stat_blocks)} stat block(s) in {xml_file.name}")
        except Exception as e:
            logger.error(f"Failed to extract stat blocks from {xml_file.name}: {e}")
            stats["errors"].append(f"Stat block extraction failed for {xml_file.name}: {e}")

    stats["stat_blocks_found"] = len(all_stat_blocks)
    logger.info(f"Total stat blocks found: {len(all_stat_blocks)}")

    # Step 2: Extract NPCs from all XML files
    logger.info("Step 2: Extracting NPCs from XML files")
    all_npcs = []

    for xml_file in xml_files:
        try:
            with open(xml_file, 'r') as f:
                xml_content = f.read()

            npcs = identify_npcs_with_gemini(xml_content, api=gemini_api)
            all_npcs.extend(npcs)
            logger.info(f"Found {len(npcs)} NPC(s) in {xml_file.name}")
        except Exception as e:
            logger.error(f"Failed to extract NPCs from {xml_file.name}: {e}")
            stats["errors"].append(f"NPC extraction failed for {xml_file.name}: {e}")

    stats["npcs_found"] = len(all_npcs)
    logger.info(f"Total NPCs found: {len(all_npcs)}")

    # Step 3: Create/lookup creature actors
    logger.info("Step 3: Creating creature actors in FoundryVTT")
    creature_uuid_map = {}  # Map creature name → UUID

    for stat_block in all_stat_blocks:
        try:
            # Search compendium first
            existing_uuid = foundry_client.search_actor(stat_block.name)

            if existing_uuid:
                logger.info(f"Found existing actor in compendium: {stat_block.name}")
                creature_uuid_map[stat_block.name] = existing_uuid
                stats["stat_blocks_reused"] += 1
            else:
                # Create new actor
                logger.info(f"Creating new creature actor: {stat_block.name}")
                new_uuid = foundry_client.create_creature_actor(stat_block)
                creature_uuid_map[stat_block.name] = new_uuid
                stats["stat_blocks_created"] += 1

        except Exception as e:
            logger.error(f"Failed to process creature actor '{stat_block.name}': {e}")
            stats["errors"].append(f"Creature actor creation failed for {stat_block.name}: {e}")

    # Step 4: Create NPC actors
    logger.info("Step 4: Creating NPC actors in FoundryVTT")

    for npc in all_npcs:
        try:
            # Get stat block UUID if available
            stat_block_uuid = creature_uuid_map.get(npc.creature_stat_block_name)

            if not stat_block_uuid:
                # Try searching compendium for the creature type
                stat_block_uuid = foundry_client.search_actor(npc.creature_stat_block_name)

            if not stat_block_uuid:
                logger.warning(
                    f"NPC '{npc.name}' references unknown creature '{npc.creature_stat_block_name}', "
                    f"creating without stat block link"
                )

            # Create NPC actor
            logger.info(f"Creating NPC actor: {npc.name}")
            foundry_client.create_npc_actor(npc, stat_block_uuid=stat_block_uuid)
            stats["npcs_created"] += 1

        except Exception as e:
            logger.error(f"Failed to create NPC actor '{npc.name}': {e}")
            stats["errors"].append(f"NPC actor creation failed for {npc.name}: {e}")

    # Summary
    logger.info("=" * 60)
    logger.info("Actor processing complete!")
    logger.info(f"Stat blocks: {stats['stat_blocks_found']} found, "
                f"{stats['stat_blocks_created']} created, "
                f"{stats['stat_blocks_reused']} reused")
    logger.info(f"NPCs: {stats['npcs_found']} found, {stats['npcs_created']} created")
    if stats["errors"]:
        logger.warning(f"Errors encountered: {len(stats['errors'])}")
    logger.info("=" * 60)

    return stats
```

### Step 4: Run workflow tests

```bash
uv run pytest tests/actors/test_process_actors.py -v
```

Expected: All tests PASS

### Step 5: Commit actor processing workflow

```bash
git add src/actors/process_actors.py tests/actors/test_process_actors.py
git commit -m "feat: add actor processing orchestration workflow

- Complete pipeline: extract stat blocks → parse → extract NPCs → create actors
- Automatic compendium reuse (search before creating)
- Comprehensive statistics and error tracking
- Links NPCs to creature stat blocks via @UUID

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 8: Add Actor Processing to Full Pipeline Script

**Files:**
- Modify: `scripts/full_pipeline.py`
- Test: Manual verification (integration test)

### Step 1: Review current full_pipeline.py structure

```bash
cat scripts/full_pipeline.py | head -50
```

### Step 2: Add actor processing flag and imports

Add to imports section:
```python
from actors.process_actors import process_actors_for_run
```

Add to argument parser:
```python
parser.add_argument(
    "--skip-actors",
    action="store_true",
    help="Skip actor/NPC extraction and creation"
)
parser.add_argument(
    "--actors-only",
    action="store_true",
    help="Only process actors (skip PDF splitting, XML generation, upload)"
)
```

### Step 3: Add actor processing step to pipeline

After XML generation completes and before FoundryVTT upload:

```python
    # Step 4: Process actors (stat blocks and NPCs)
    if not args.skip_actors and not args.actors_only:
        logger.info("\n" + "=" * 60)
        logger.info("Step 4: Processing actors and NPCs")
        logger.info("=" * 60)

        try:
            actor_stats = process_actors_for_run(run_dir, target=args.target)
            logger.info(f"Actor processing complete: {actor_stats['stat_blocks_created']} creatures, "
                       f"{actor_stats['npcs_created']} NPCs created")
        except Exception as e:
            logger.error(f"Actor processing failed: {e}")
            if not args.continue_on_error:
                raise

    # Actors-only mode
    if args.actors_only:
        logger.info("\n" + "=" * 60)
        logger.info("Running in actors-only mode")
        logger.info("=" * 60)

        # Need to find latest run or use specified run-dir
        if not args.run_dir:
            # Find latest run
            runs_dir = PROJECT_ROOT / "output" / "runs"
            run_dirs = sorted(runs_dir.glob("*"), reverse=True)
            if not run_dirs:
                logger.error("No run directories found. Run full pipeline first.")
                sys.exit(1)
            run_dir = str(run_dirs[0])
            logger.info(f"Using latest run: {run_dir}")
        else:
            run_dir = args.run_dir

        try:
            actor_stats = process_actors_for_run(run_dir, target=args.target)
            logger.info(f"Actor processing complete: {actor_stats['stat_blocks_created']} creatures, "
                       f"{actor_stats['npcs_created']} NPCs created")
        except Exception as e:
            logger.error(f"Actor processing failed: {e}")
            sys.exit(1)

        sys.exit(0)
```

### Step 4: Update pipeline step numbers in comments

Update subsequent step numbers (upload becomes Step 5, export becomes Step 6, etc.)

### Step 5: Test actors-only mode manually

```bash
# Assuming a run directory already exists from previous pipeline run
uv run python scripts/full_pipeline.py --actors-only
```

Expected: Processes actors from latest run directory

### Step 6: Test full pipeline with actor processing

```bash
uv run python scripts/full_pipeline.py --journal-name "Test Module"
```

Expected: Complete pipeline including actor creation

### Step 7: Commit pipeline integration

```bash
git add scripts/full_pipeline.py
git commit -m "feat: integrate actor processing into full pipeline

- Add --skip-actors flag to skip actor processing
- Add --actors-only flag for standalone actor processing
- Actor processing runs after XML generation, before upload
- Update step numbering in pipeline

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 9: Update Documentation

**Files:**
- Modify: `CLAUDE.md` (add actor processing documentation)
- Modify: `docs/plans/roadmap.md` (update feature status)

### Step 1: Add actor processing section to CLAUDE.md

Add after "FoundryVTT Integration" section:

```markdown
### Actor/NPC Extraction

The project includes automatic extraction and creation of D&D 5e actors and NPCs from module PDFs.

**Architecture:**
- **Stat Block Tagging**: During XML generation, Gemini tags stat blocks with `<stat_block name="...">raw text</stat_block>`
- **Stat Block Parsing**: Gemini parses raw stat blocks into structured Pydantic `StatBlock` models
- **NPC Extraction**: Post-processing analyzes XML to identify named NPCs and link them to stat blocks
- **Actor Creation**: Creates FoundryVTT Actor entities with compendium reuse

**Processing Pipeline:**
```
PDF → XML (with <stat_block> tags)
    ↓
parse_stat_blocks.py (Gemini parses → StatBlock models)
    ↓
extract_npcs.py (Gemini identifies NPCs → NPC models)
    ↓
ActorManager (creates/reuses FoundryVTT Actors)
```

**Actor Types:**
1. **Creature Actors**: Full stat blocks from the module (e.g., "Goblin", "Bugbear")
   - Contains complete D&D 5e stats (AC, HP, abilities, actions)
   - Created from `StatBlock` models
   - Reuses compendium actors if name matches

2. **NPC Actors**: Named characters with plot context (e.g., "Klarg", "Sildar Hallwinter")
   - Bio-only actors (no stats directly)
   - Biography includes description, plot role, location
   - Links to creature stat block via @UUID syntax
   - Example: "Klarg" (NPC) → links to → "Bugbear" (creature actor)

**Usage:**
```bash
# Full pipeline with actors
uv run python scripts/full_pipeline.py --journal-name "Lost Mine of Phandelver"

# Skip actor processing
uv run python scripts/full_pipeline.py --skip-actors

# Process actors only (from existing run)
uv run python scripts/full_pipeline.py --actors-only

# Process actors for specific run
uv run python scripts/full_pipeline.py --actors-only --run-dir output/runs/20241023_143022
```

**Compendium Reuse:**
- Before creating creature actors, searches ALL user compendiums by name
- If match found, uses existing actor UUID (avoids duplicates)
- NPCs link to existing compendium entries when possible
- Example: "Goblin" found in dnd5e.monsters → reuse instead of creating new

**Data Models** (see `src/actors/models.py`):
```python
class StatBlock(BaseModel):
    name: str
    raw_text: str  # Original stat block text preserved
    armor_class: int
    hit_points: int
    challenge_rating: float
    # Optional: size, type, alignment, abilities, etc.

class NPC(BaseModel):
    name: str
    creature_stat_block_name: str  # Links to creature (e.g., "Bugbear")
    description: str
    plot_relevance: str
    location: Optional[str]
    first_appearance_section: Optional[str]
```

**Key Modules:**
- `src/actors/models.py`: Pydantic models for StatBlock and NPC
- `src/actors/parse_stat_blocks.py`: Gemini-powered stat block parser
- `src/actors/extract_stat_blocks.py`: Extract stat blocks from XML
- `src/actors/extract_npcs.py`: Gemini-powered NPC identification
- `src/actors/process_actors.py`: Orchestration workflow
- `src/foundry/actors.py`: FoundryVTT Actor creation and search
```

### Step 2: Update roadmap.md feature status

Find "Feature 2: Stat Block & NPC Extraction" and update status:

```markdown
### 2. Stat Block & NPC Extraction with Actor Generation

**Status:** ✔️ Completed

**Description:**
Extract and structure D&D 5e stat blocks and NPCs from modules, then create FoundryVTT Actor objects.
[Keep existing description]

**Implementation Complete:**
- ✅ Stat block tagging during XML generation
- ✅ Gemini-powered stat block parsing into Pydantic models
- ✅ NPC extraction from narrative with stat block linking
- ✅ FoundryVTT Actor creation with compendium reuse
- ✅ Bio-only NPC actors with @UUID links to creature stats
- ✅ Integrated into full_pipeline.py
- ✅ Comprehensive test coverage (unit + integration)

**Resolved Design Questions:**
[Keep existing]

**Remaining Open Questions:**
- **Token Images**: Generate token art for actors, or leave blank?
- **Compendium Pack Name**: Auto-generate (e.g., "lost-mine-of-phandelver-creatures") or user configurable?
```

### Step 3: Commit documentation updates

```bash
git add CLAUDE.md docs/plans/roadmap.md
git commit -m "docs: add actor/NPC extraction documentation

- Add comprehensive actor processing section to CLAUDE.md
- Document architecture, usage, data models, key modules
- Update roadmap.md to mark feature as completed
- List resolved and remaining design questions

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 10: Update XML Generation Prompt (Stat Block Tagging)

**Files:**
- Modify: `src/pdf_processing/pdf_to_xml.py` (update Gemini prompt)

### Step 1: Locate XML generation prompt in pdf_to_xml.py

```bash
grep -n "def generate_xml" src/pdf_processing/pdf_to_xml.py
```

### Step 2: Add stat block tagging instructions to prompt

Find the prompt construction section and add after formatting instructions:

```python
**STAT BLOCK TAGGING:**
- Tag all D&D 5e stat blocks with: <stat_block name="Creature Name">raw text</stat_block>
- Preserve COMPLETE original stat block text inside the tag
- Do NOT parse or structure the stat block - keep it as raw text
- Stat blocks are typically boxed sections with creature stats:
  - Name and type/size (e.g., "GOBLIN / Small humanoid")
  - Armor Class, Hit Points, Speed
  - Ability scores (STR, DEX, CON, INT, WIS, CHA)
  - Challenge rating
  - Traits and actions

Example stat block tagging:
<stat_block name="Goblin">
GOBLIN
Small humanoid (goblinoid), neutral evil

Armor Class 15 (leather armor, shield)
Hit Points 7 (2d6)
Speed 30 ft.

STR     DEX     CON     INT     WIS     CHA
8 (-1)  14 (+2) 10 (+0) 10 (+0) 8 (-1)  8 (-1)

Challenge 1/4 (50 XP)

Nimble Escape. The goblin can take the Disengage or Hide action...

ACTIONS
Scimitar. Melee Weapon Attack: +4 to hit...
</stat_block>
```

### Step 3: Test updated prompt with test PDF

```bash
# Process test PDF to verify stat blocks are tagged
uv run python src/pdf_processing/pdf_to_xml.py --file "data/data/pdf_sections/Lost_Mine_of_Phandelver_test/01_Introduction.pdf"
```

Expected: Generated XML contains `<stat_block name="...">` tags

### Step 4: Verify stat block extraction works

```bash
# Test extraction from generated XML
uv run pytest tests/actors/test_extract_stat_blocks.py -v
```

Expected: All tests PASS

### Step 5: Commit prompt update

```bash
git add src/pdf_processing/pdf_to_xml.py
git commit -m "feat: add stat block tagging to XML generation prompt

- Instruct Gemini to tag stat blocks with <stat_block name=\"...\">
- Preserve complete original stat block text (no parsing)
- Add detailed example to prompt
- Required for actor extraction pipeline

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 11: End-to-End Integration Test

**Files:**
- Test: Manual end-to-end test with real PDFs and API calls

### Step 1: Run complete pipeline with test PDF

```bash
uv run python scripts/full_pipeline.py \
    --journal-name "Actor Test Module" \
    --pdf-path "data/pdfs/Lost_Mine_of_Phandelver_test.pdf"
```

Expected: Complete pipeline runs successfully, creates actors in FoundryVTT

### Step 2: Verify actors created in FoundryVTT

Log into FoundryVTT and check:
- [ ] Creature actors created in compendium or world
- [ ] NPC actors created with bio content
- [ ] NPC biographies contain @UUID links to creature actors
- [ ] Clicking @UUID link navigates to creature stat block

### Step 3: Test compendium reuse

Run pipeline again with same PDF:
```bash
uv run python scripts/full_pipeline.py \
    --journal-name "Actor Test Module 2" \
    --pdf-path "data/pdfs/Lost_Mine_of_Phandelver_test.pdf"
```

Check logs:
- [ ] "Found existing actor in compendium" messages appear
- [ ] `stat_blocks_reused` > 0 in final statistics
- [ ] No duplicate actors created

### Step 4: Test actors-only mode

```bash
uv run python scripts/full_pipeline.py --actors-only
```

Expected: Processes actors from latest run without regenerating XML

### Step 5: Document test results

Create test report:
```bash
echo "# Actor Extraction Integration Test Results

Date: $(date)

## Test 1: Full Pipeline
- Status: [PASS/FAIL]
- Creatures created: X
- NPCs created: Y
- Notes: [any issues]

## Test 2: Compendium Reuse
- Status: [PASS/FAIL]
- Creatures reused: X
- Notes: [any issues]

## Test 3: Actors-Only Mode
- Status: [PASS/FAIL]
- Notes: [any issues]

## Issues Found
- [list any bugs or problems]
" > docs/plans/actor-extraction-test-results.md
```

### Step 6: Fix any issues found

If bugs discovered during testing:
1. Write failing test reproducing the bug
2. Fix the bug
3. Verify test passes
4. Commit fix

### Step 7: Final verification commit

```bash
git add docs/plans/actor-extraction-test-results.md
git commit -m "test: verify end-to-end actor extraction workflow

- Complete pipeline test with real PDFs and APIs
- Compendium reuse verification
- Actors-only mode verification
- Document test results and any issues

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Completion Checklist

Before marking this feature complete, verify:

- [ ] All unit tests pass: `uv run pytest -m "not integration and not slow"`
- [ ] All integration tests pass: `uv run pytest`
- [ ] End-to-end pipeline test successful
- [ ] Documentation updated (CLAUDE.md, roadmap.md)
- [ ] Code follows project conventions (PEP 8, type hints, docstrings)
- [ ] All commits follow conventional commit format
- [ ] No sensitive data (API keys, secrets) in repository
- [ ] Feature branch ready for merge to main

---

## Future Enhancements

Ideas for future iterations (NOT in this plan):

1. **Token Image Generation**: Auto-generate token images for actors using Gemini Imagen
2. **Compendium Pack Configuration**: User-configurable compendium pack names
3. **Actor Folders**: Organize actors into folders by chapter or type
4. **Duplicate Detection**: Fuzzy matching for similar creature names
5. **Stat Block Validation**: Compare parsed stats against official SRD for accuracy
6. **Batch Actor Import**: Import multiple actors from external sources
7. **Actor Templates**: Reusable templates for common NPC types

---

## Notes

**Testing Strategy:**
- Unit tests mock external dependencies (Gemini API, FoundryVTT API)
- Integration tests use real APIs (marked with `@pytest.mark.integration`)
- Manual end-to-end test verifies complete workflow
- Test fixtures provide realistic sample data

**Error Handling:**
- Graceful degradation: Continue processing other actors if one fails
- Comprehensive logging at all stages
- Statistics tracking for visibility into success/failure rates

**Performance Considerations:**
- Reuse GeminiAPI and FoundryClient instances across batch operations
- Parallel processing not implemented (sequential for now, can optimize later)
- Compendium search happens once per creature type (cached in memory)

**Design Decisions:**
- Stat blocks preserved as raw text (not over-structured)
- NPCs are bio-only actors (no duplicate stats)
- @UUID links provide seamless navigation in FoundryVTT
- Compendium reuse prevents duplicate content

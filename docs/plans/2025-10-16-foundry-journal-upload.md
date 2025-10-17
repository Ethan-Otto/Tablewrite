# FoundryVTT Journal Upload Integration Implementation Plan

> **For Claude:** Use `${SUPERPOWERS_SKILLS_ROOT}/skills/collaboration/executing-plans/SKILL.md` to implement this plan task-by-task.

**Goal:** Automatically upload generated HTML content to FoundryVTT journal entries after the xml_to_html.py conversion completes.

**Architecture:** Integrate ThreeHats REST API module using Python requests library. Create new module `src/foundry/` containing client code for FoundryVTT REST API. The client will read HTML files from latest run and create/update corresponding journal entries via REST API relay server. Pipeline modified to optionally call uploader after HTML generation.

**Tech Stack:** Python 3.x, requests library, FoundryVTT REST API module (ThreeHats), python-dotenv

---

## Prerequisites (Manual Setup)

Before implementing code, complete these manual setup steps:

### Setup 1: Install FoundryVTT REST API Module

**Local Foundry:**
1. Open FoundryVTT on `localhost:30000`
2. Go to Add-on Modules > Install Module
3. Paste manifest URL: `https://github.com/ThreeHats/foundryvtt-rest-api/releases/latest/download/module.json`
4. Click Install
5. Enable the module in your world
6. In Module Settings, generate an API key (save for .env file)

**The Forge:**
1. Log into forge-vtt.com
2. Navigate to your game's Setup > Add-on Modules
3. Install using same manifest URL
4. Enable in your world
5. Generate API key in Module Settings

Expected: Module installed and API keys generated for both environments.

### Setup 2: Verify Relay Server Access

Test that the public relay server is accessible:

```bash
curl -I https://foundryvtt-rest-api-relay.fly.dev/
```

Expected: HTTP 200 or 404 (server is up). If timeout/error, relay server may be down.

---

## Task 1: Environment Configuration

**Files:**
- Modify: `.env` (add Foundry config)
- Read: `.env.example` (if exists) or create

**Step 1: Add environment variables to .env**

Add these lines to `.env`:

```bash
# FoundryVTT Configuration
FOUNDRY_LOCAL_URL=http://localhost:30000
FOUNDRY_LOCAL_API_KEY=your_local_api_key_here
FOUNDRY_FORGE_URL=https://your-game.forge-vtt.com
FOUNDRY_FORGE_API_KEY=your_forge_api_key_here
FOUNDRY_RELAY_URL=https://foundryvtt-rest-api-relay.fly.dev
FOUNDRY_AUTO_UPLOAD=false
FOUNDRY_TARGET=local
```

**Step 2: Update .gitignore to ensure .env is excluded**

Verify `.env` is in `.gitignore`:

```bash
grep -q "^\.env$" .gitignore && echo "Already ignored" || echo ".env" >> .gitignore
```

Expected: ".env" is in .gitignore

**Step 3: Document environment variables**

Create or update `.env.example`:

```bash
# Gemini API
GeminiImageAPI=your_gemini_api_key

# FoundryVTT Configuration
FOUNDRY_LOCAL_URL=http://localhost:30000
FOUNDRY_LOCAL_API_KEY=your_local_api_key
FOUNDRY_FORGE_URL=https://your-game.forge-vtt.com
FOUNDRY_FORGE_API_KEY=your_forge_api_key
FOUNDRY_RELAY_URL=https://foundryvtt-rest-api-relay.fly.dev
FOUNDRY_AUTO_UPLOAD=false
FOUNDRY_TARGET=local
```

**Step 4: Commit environment setup**

```bash
git add .env.example .gitignore
git commit -m "feat: add FoundryVTT API configuration to environment"
```

---

## Task 2: Add Dependencies

**Files:**
- Modify: `pyproject.toml`

**Step 1: Add requests library to dependencies**

Add `requests` to dependencies in `pyproject.toml`:

```toml
dependencies = [
    "google-generativeai",
    "PyMuPDF",
    "pytesseract",
    "Pillow",
    "python-dotenv",
    "requests>=2.31.0",
]
```

**Step 2: Sync dependencies**

```bash
uv pip sync
```

Expected: requests library installed successfully

**Step 3: Verify installation**

```bash
uv run python -c "import requests; print(requests.__version__)"
```

Expected: Version number printed (e.g., "2.31.0")

**Step 4: Commit dependency update**

```bash
git add pyproject.toml
git commit -m "feat: add requests library for FoundryVTT API client"
```

---

## Task 3: Create Foundry Module Structure

**Files:**
- Create: `src/foundry/__init__.py`
- Create: `src/foundry/client.py`

**Step 1: Create foundry module directory and __init__.py**

```bash
mkdir -p src/foundry
touch src/foundry/__init__.py
```

**Step 2: Write minimal __init__.py**

`src/foundry/__init__.py`:

```python
"""FoundryVTT API integration module."""

from .client import FoundryClient

__all__ = ["FoundryClient"]
```

**Step 3: Create empty client.py**

```bash
touch src/foundry/client.py
```

**Step 4: Commit module structure**

```bash
git add src/foundry/__init__.py src/foundry/client.py
git commit -m "feat: create foundry module structure"
```

---

## Task 4: Implement FoundryClient Configuration (TDD)

**Files:**
- Create: `tests/foundry/__init__.py`
- Create: `tests/foundry/test_client.py`
- Modify: `src/foundry/client.py`

**Step 1: Create test directory structure**

```bash
mkdir -p tests/foundry
touch tests/foundry/__init__.py
```

**Step 2: Write failing test for client initialization**

`tests/foundry/test_client.py`:

```python
"""Tests for FoundryVTT API client."""

import pytest
import os
from src.foundry.client import FoundryClient


class TestFoundryClientInit:
    """Tests for FoundryClient initialization."""

    def test_client_initialization_with_env_vars(self, monkeypatch):
        """Test client initializes with environment variables."""
        monkeypatch.setenv("FOUNDRY_LOCAL_URL", "http://localhost:30000")
        monkeypatch.setenv("FOUNDRY_LOCAL_API_KEY", "test-api-key")
        monkeypatch.setenv("FOUNDRY_RELAY_URL", "https://relay.example.com")

        client = FoundryClient(target="local")

        assert client.foundry_url == "http://localhost:30000"
        assert client.api_key == "test-api-key"
        assert client.relay_url == "https://relay.example.com"

    def test_client_initialization_forge(self, monkeypatch):
        """Test client initializes with forge environment."""
        monkeypatch.setenv("FOUNDRY_FORGE_URL", "https://game.forge-vtt.com")
        monkeypatch.setenv("FOUNDRY_FORGE_API_KEY", "forge-api-key")
        monkeypatch.setenv("FOUNDRY_RELAY_URL", "https://relay.example.com")

        client = FoundryClient(target="forge")

        assert client.foundry_url == "https://game.forge-vtt.com"
        assert client.api_key == "forge-api-key"

    def test_client_raises_on_missing_env_vars(self):
        """Test client raises ValueError when required env vars missing."""
        with pytest.raises(ValueError, match="FOUNDRY_LOCAL_URL not set"):
            FoundryClient(target="local")
```

**Step 3: Run test to verify it fails**

```bash
uv run pytest tests/foundry/test_client.py::TestFoundryClientInit -v
```

Expected: FAIL with "cannot import name 'FoundryClient'"

**Step 4: Write minimal FoundryClient class**

`src/foundry/client.py`:

```python
"""FoundryVTT REST API client."""

import os
import logging
from typing import Literal

logger = logging.getLogger(__name__)


class FoundryClient:
    """Client for interacting with FoundryVTT via REST API."""

    def __init__(self, target: Literal["local", "forge"] = "local"):
        """
        Initialize FoundryVTT API client.

        Args:
            target: Target environment ('local' or 'forge')

        Raises:
            ValueError: If required environment variables are not set
        """
        self.target = target
        self.relay_url = os.getenv("FOUNDRY_RELAY_URL")

        if not self.relay_url:
            raise ValueError("FOUNDRY_RELAY_URL not set in environment")

        if target == "local":
            self.foundry_url = os.getenv("FOUNDRY_LOCAL_URL")
            self.api_key = os.getenv("FOUNDRY_LOCAL_API_KEY")
            if not self.foundry_url:
                raise ValueError("FOUNDRY_LOCAL_URL not set in environment")
            if not self.api_key:
                raise ValueError("FOUNDRY_LOCAL_API_KEY not set in environment")
        elif target == "forge":
            self.foundry_url = os.getenv("FOUNDRY_FORGE_URL")
            self.api_key = os.getenv("FOUNDRY_FORGE_API_KEY")
            if not self.foundry_url:
                raise ValueError("FOUNDRY_FORGE_URL not set in environment")
            if not self.api_key:
                raise ValueError("FOUNDRY_FORGE_API_KEY not set in environment")
        else:
            raise ValueError(f"Invalid target: {target}. Must be 'local' or 'forge'")

        logger.info(f"Initialized FoundryClient for {target} at {self.foundry_url}")
```

**Step 5: Run test to verify it passes**

```bash
uv run pytest tests/foundry/test_client.py::TestFoundryClientInit -v
```

Expected: 3 tests PASS

**Step 6: Commit client initialization**

```bash
git add src/foundry/client.py tests/foundry/
git commit -m "feat: implement FoundryClient initialization with env config"
```

---

## Task 5: Implement Journal Entry Creation (TDD)

**Files:**
- Modify: `tests/foundry/test_client.py`
- Modify: `src/foundry/client.py`

**Step 1: Write failing test for journal creation**

Add to `tests/foundry/test_client.py`:

```python
from unittest.mock import Mock, patch


class TestJournalOperations:
    """Tests for journal entry operations."""

    @pytest.fixture
    def mock_client(self, monkeypatch):
        """Create a FoundryClient with mocked environment."""
        monkeypatch.setenv("FOUNDRY_LOCAL_URL", "http://localhost:30000")
        monkeypatch.setenv("FOUNDRY_LOCAL_API_KEY", "test-key")
        monkeypatch.setenv("FOUNDRY_RELAY_URL", "https://relay.example.com")
        return FoundryClient(target="local")

    @patch('requests.post')
    def test_create_journal_entry_success(self, mock_post, mock_client):
        """Test creating a journal entry via REST API."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "_id": "journal123",
            "name": "Test Journal",
            "content": "<p>Test content</p>"
        }
        mock_post.return_value = mock_response

        result = mock_client.create_journal_entry(
            name="Test Journal",
            content="<p>Test content</p>"
        )

        assert result["_id"] == "journal123"
        assert result["name"] == "Test Journal"
        mock_post.assert_called_once()

        # Verify API key header
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["headers"]["x-api-key"] == "test-key"

    @patch('requests.post')
    def test_create_journal_entry_failure(self, mock_post, mock_client):
        """Test journal creation handles API errors."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"
        mock_post.return_value = mock_response

        with pytest.raises(RuntimeError, match="Failed to create journal"):
            mock_client.create_journal_entry(
                name="Test Journal",
                content="<p>Test content</p>"
            )
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/foundry/test_client.py::TestJournalOperations -v
```

Expected: FAIL with "FoundryClient has no attribute 'create_journal_entry'"

**Step 3: Implement create_journal_entry method**

Add to `src/foundry/client.py`:

```python
import requests
from typing import Dict, Any


class FoundryClient:
    # ... existing __init__ code ...

    def create_journal_entry(
        self,
        name: str,
        content: str,
        folder: str = None
    ) -> Dict[str, Any]:
        """
        Create a new journal entry in FoundryVTT.

        Args:
            name: Name of the journal entry
            content: HTML content for the journal
            folder: Optional folder ID to organize the journal

        Returns:
            Dict containing created journal entry data

        Raises:
            RuntimeError: If API request fails
        """
        url = f"{self.relay_url}/create"

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }

        payload = {
            "type": "JournalEntry",
            "data": {
                "name": name,
                "content": content
            }
        }

        if folder:
            payload["data"]["folder"] = folder

        logger.debug(f"Creating journal entry: {name}")

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)

            if response.status_code != 200:
                logger.error(f"Failed to create journal: {response.status_code} - {response.text}")
                raise RuntimeError(
                    f"Failed to create journal entry: {response.status_code} - {response.text}"
                )

            result = response.json()
            logger.info(f"Created journal entry: {name} (ID: {result.get('_id')})")
            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise RuntimeError(f"Failed to create journal entry: {e}") from e
```

**Step 4: Run test to verify it passes**

```bash
uv run pytest tests/foundry/test_client.py::TestJournalOperations -v
```

Expected: 2 tests PASS

**Step 5: Commit journal creation feature**

```bash
git add src/foundry/client.py tests/foundry/test_client.py
git commit -m "feat: implement journal entry creation via REST API"
```

---

## Task 6: Implement Journal Entry Update (TDD)

**Files:**
- Modify: `tests/foundry/test_client.py`
- Modify: `src/foundry/client.py`

**Step 1: Write test for updating existing journal**

Add to `tests/foundry/test_client.py` in `TestJournalOperations`:

```python
    @patch('requests.put')
    def test_update_journal_entry_success(self, mock_put, mock_client):
        """Test updating an existing journal entry."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "_id": "journal123",
            "name": "Updated Journal",
            "content": "<p>Updated content</p>"
        }
        mock_put.return_value = mock_response

        result = mock_client.update_journal_entry(
            journal_id="journal123",
            content="<p>Updated content</p>"
        )

        assert result["_id"] == "journal123"
        mock_put.assert_called_once()

    @patch('requests.get')
    def test_find_journal_by_name(self, mock_get, mock_client):
        """Test finding a journal entry by name."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"_id": "journal123", "name": "Test Journal"},
            {"_id": "journal456", "name": "Other Journal"}
        ]
        mock_get.return_value = mock_response

        result = mock_client.find_journal_by_name("Test Journal")

        assert result is not None
        assert result["_id"] == "journal123"
        assert result["name"] == "Test Journal"

    @patch('requests.get')
    def test_find_journal_by_name_not_found(self, mock_get, mock_client):
        """Test finding returns None when journal doesn't exist."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        result = mock_client.find_journal_by_name("Nonexistent")

        assert result is None
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/foundry/test_client.py::TestJournalOperations::test_update_journal_entry_success -v
```

Expected: FAIL with "no attribute 'update_journal_entry'"

**Step 3: Implement update and search methods**

Add to `src/foundry/client.py`:

```python
from typing import Dict, Any, Optional, List


class FoundryClient:
    # ... existing code ...

    def find_journal_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Find a journal entry by name.

        Args:
            name: Name of the journal entry to find

        Returns:
            Journal entry dict if found, None otherwise

        Raises:
            RuntimeError: If API request fails
        """
        url = f"{self.relay_url}/search"

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }

        params = {
            "type": "JournalEntry",
            "name": name
        }

        logger.debug(f"Searching for journal: {name}")

        try:
            response = requests.get(url, params=params, headers=headers, timeout=30)

            if response.status_code != 200:
                logger.error(f"Search failed: {response.status_code}")
                raise RuntimeError(f"Failed to search journals: {response.status_code}")

            results = response.json()

            if not results:
                logger.debug(f"No journal found with name: {name}")
                return None

            # Return first exact match
            for journal in results:
                if journal.get("name") == name:
                    logger.debug(f"Found journal: {name} (ID: {journal.get('_id')})")
                    return journal

            return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Search request failed: {e}")
            raise RuntimeError(f"Failed to search journals: {e}") from e

    def update_journal_entry(
        self,
        journal_id: str,
        content: str = None,
        name: str = None
    ) -> Dict[str, Any]:
        """
        Update an existing journal entry.

        Args:
            journal_id: ID of the journal entry to update
            content: New HTML content (optional)
            name: New name (optional)

        Returns:
            Dict containing updated journal entry data

        Raises:
            RuntimeError: If API request fails
        """
        url = f"{self.relay_url}/update"

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }

        payload = {
            "type": "JournalEntry",
            "id": journal_id,
            "data": {}
        }

        if content is not None:
            payload["data"]["content"] = content
        if name is not None:
            payload["data"]["name"] = name

        logger.debug(f"Updating journal entry: {journal_id}")

        try:
            response = requests.put(url, json=payload, headers=headers, timeout=30)

            if response.status_code != 200:
                logger.error(f"Update failed: {response.status_code}")
                raise RuntimeError(f"Failed to update journal: {response.status_code}")

            result = response.json()
            logger.info(f"Updated journal entry: {journal_id}")
            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"Update request failed: {e}")
            raise RuntimeError(f"Failed to update journal: {e}") from e

    def create_or_update_journal(
        self,
        name: str,
        content: str,
        folder: str = None
    ) -> Dict[str, Any]:
        """
        Create a new journal or update existing one with same name.

        Args:
            name: Name of the journal entry
            content: HTML content for the journal
            folder: Optional folder ID

        Returns:
            Dict containing journal entry data
        """
        existing = self.find_journal_by_name(name)

        if existing:
            logger.info(f"Journal '{name}' exists, updating...")
            return self.update_journal_entry(
                journal_id=existing["_id"],
                content=content
            )
        else:
            logger.info(f"Journal '{name}' not found, creating...")
            return self.create_journal_entry(
                name=name,
                content=content,
                folder=folder
            )
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/foundry/test_client.py::TestJournalOperations -v
```

Expected: All tests PASS

**Step 5: Commit update functionality**

```bash
git add src/foundry/client.py tests/foundry/test_client.py
git commit -m "feat: implement journal search and update operations"
```

---

## Task 7: Create Upload Script

**Files:**
- Create: `src/foundry/upload_to_foundry.py`
- Create: `tests/foundry/test_upload_script.py`

**Step 1: Write test for HTML file reading and upload**

`tests/foundry/test_upload_script.py`:

```python
"""Tests for upload_to_foundry script."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from src.foundry.upload_to_foundry import (
    find_latest_run,
    read_html_files,
    upload_run_to_foundry
)


class TestUploadScript:
    """Tests for upload script functions."""

    def test_find_latest_run(self, tmp_path):
        """Test finding the most recent run directory."""
        output_dir = tmp_path / "output" / "runs"
        output_dir.mkdir(parents=True)

        # Create mock run directories
        (output_dir / "20250101_120000").mkdir()
        (output_dir / "20250102_120000").mkdir()
        (output_dir / "20250103_120000").mkdir()

        latest = find_latest_run(str(tmp_path / "output" / "runs"))

        assert latest == str(output_dir / "20250103_120000")

    def test_read_html_files(self, tmp_path):
        """Test reading HTML files from run directory."""
        html_dir = tmp_path / "documents" / "html"
        html_dir.mkdir(parents=True)

        # Create test HTML files
        (html_dir / "01_Chapter_One.html").write_text("<h1>Chapter 1</h1>")
        (html_dir / "02_Chapter_Two.html").write_text("<h1>Chapter 2</h1>")

        html_files = read_html_files(str(html_dir))

        assert len(html_files) == 2
        assert html_files[0]["name"] == "01_Chapter_One"
        assert html_files[0]["content"] == "<h1>Chapter 1</h1>"

    @patch('src.foundry.upload_to_foundry.FoundryClient')
    def test_upload_run_to_foundry(self, mock_client_class, tmp_path):
        """Test uploading HTML files to Foundry."""
        html_dir = tmp_path / "documents" / "html"
        html_dir.mkdir(parents=True)
        (html_dir / "01_Test.html").write_text("<p>Test</p>")

        mock_client = Mock()
        mock_client.create_or_update_journal.return_value = {"_id": "journal123"}
        mock_client_class.return_value = mock_client

        result = upload_run_to_foundry(str(html_dir), target="local")

        assert result["uploaded"] == 1
        assert result["failed"] == 0
        mock_client.create_or_update_journal.assert_called_once_with(
            name="01_Test",
            content="<p>Test</p>"
        )
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/foundry/test_upload_script.py -v
```

Expected: FAIL with "cannot import name 'find_latest_run'"

**Step 3: Implement upload script**

`src/foundry/upload_to_foundry.py`:

```python
#!/usr/bin/env python3
"""Upload generated HTML files to FoundryVTT as journal entries."""

import os
import sys
import logging
from pathlib import Path
from typing import List, Dict, Any
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from foundry.client import FoundryClient
from logging_config import setup_logging

logger = setup_logging(__name__)


def find_latest_run(runs_dir: str) -> str:
    """
    Find the most recent run directory.

    Args:
        runs_dir: Path to output/runs directory

    Returns:
        Path to latest run directory

    Raises:
        ValueError: If no run directories found
    """
    runs_path = Path(runs_dir)

    if not runs_path.exists():
        raise ValueError(f"Runs directory does not exist: {runs_dir}")

    run_dirs = [d for d in runs_path.iterdir() if d.is_dir()]

    if not run_dirs:
        raise ValueError(f"No run directories found in: {runs_dir}")

    # Sort by directory name (timestamp format YYYYMMDD_HHMMSS)
    latest = sorted(run_dirs, key=lambda d: d.name)[-1]

    logger.info(f"Latest run: {latest.name}")
    return str(latest)


def read_html_files(html_dir: str) -> List[Dict[str, str]]:
    """
    Read all HTML files from directory.

    Args:
        html_dir: Path to HTML directory

    Returns:
        List of dicts with 'name' and 'content' keys
    """
    html_path = Path(html_dir)

    if not html_path.exists():
        raise ValueError(f"HTML directory does not exist: {html_dir}")

    html_files = []

    for html_file in sorted(html_path.glob("*.html")):
        name = html_file.stem  # Filename without extension
        content = html_file.read_text(encoding="utf-8")

        html_files.append({
            "name": name,
            "content": content,
            "path": str(html_file)
        })

        logger.debug(f"Read HTML file: {name} ({len(content)} chars)")

    logger.info(f"Found {len(html_files)} HTML files")
    return html_files


def upload_run_to_foundry(
    html_dir: str,
    target: str = "local"
) -> Dict[str, Any]:
    """
    Upload all HTML files from a run to FoundryVTT.

    Args:
        html_dir: Path to HTML directory
        target: Target environment ('local' or 'forge')

    Returns:
        Dict with upload statistics
    """
    logger.info(f"Uploading to FoundryVTT ({target})")

    # Read HTML files
    html_files = read_html_files(html_dir)

    if not html_files:
        logger.warning("No HTML files to upload")
        return {"uploaded": 0, "failed": 0}

    # Initialize client
    client = FoundryClient(target=target)

    # Upload each file
    uploaded = 0
    failed = 0
    errors = []

    for html_file in html_files:
        try:
            logger.info(f"Uploading: {html_file['name']}")

            result = client.create_or_update_journal(
                name=html_file["name"],
                content=html_file["content"]
            )

            uploaded += 1
            logger.info(f"✓ Uploaded: {html_file['name']} (ID: {result.get('_id')})")

        except Exception as e:
            failed += 1
            error_msg = f"✗ Failed: {html_file['name']} - {e}"
            logger.error(error_msg)
            errors.append(error_msg)

    logger.info(f"Upload complete: {uploaded} succeeded, {failed} failed")

    return {
        "uploaded": uploaded,
        "failed": failed,
        "errors": errors
    }


def main():
    """Main entry point for upload script."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Upload HTML files to FoundryVTT journal entries"
    )
    parser.add_argument(
        "--run-dir",
        help="Specific run directory (default: latest)"
    )
    parser.add_argument(
        "--target",
        choices=["local", "forge"],
        default="local",
        help="Target environment (default: local)"
    )

    args = parser.parse_args()

    # Load environment variables
    load_dotenv()

    # Determine run directory
    if args.run_dir:
        run_dir = args.run_dir
    else:
        project_root = Path(__file__).parent.parent.parent
        runs_dir = project_root / "output" / "runs"
        run_dir = find_latest_run(str(runs_dir))

    # Find HTML directory
    html_dir = Path(run_dir) / "documents" / "html"

    if not html_dir.exists():
        logger.error(f"HTML directory not found: {html_dir}")
        sys.exit(1)

    # Upload
    try:
        result = upload_run_to_foundry(str(html_dir), target=args.target)

        if result["failed"] > 0:
            sys.exit(1)
        else:
            logger.info("All files uploaded successfully!")
            sys.exit(0)

    except Exception as e:
        logger.error(f"Upload failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/foundry/test_upload_script.py -v
```

Expected: All tests PASS

**Step 5: Make script executable**

```bash
chmod +x src/foundry/upload_to_foundry.py
```

**Step 6: Test script manually (dry run)**

```bash
uv run python src/foundry/upload_to_foundry.py --help
```

Expected: Help message printed

**Step 7: Commit upload script**

```bash
git add src/foundry/upload_to_foundry.py tests/foundry/test_upload_script.py
git commit -m "feat: implement HTML to FoundryVTT journal upload script"
```

---

## Task 8: Integrate with xml_to_html.py Pipeline

**Files:**
- Modify: `src/pdf_processing/xml_to_html.py`

**Step 1: Read current xml_to_html.py**

```bash
uv run python -m py_compile src/pdf_processing/xml_to_html.py
```

Expected: No syntax errors

**Step 2: Add import and environment check**

Add at top of `src/pdf_processing/xml_to_html.py` after existing imports:

```python
# Add after existing imports
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
```

Add after `setup_logging` call in `main()`:

```python
def main():
    logger = setup_logging(__name__)

    # Check if auto-upload is enabled
    auto_upload = os.getenv("FOUNDRY_AUTO_UPLOAD", "false").lower() == "true"
    foundry_target = os.getenv("FOUNDRY_TARGET", "local")

    logger.info(f"Starting XML to HTML conversion (auto-upload: {auto_upload})")
```

**Step 3: Add upload call after HTML generation**

Add at end of `main()` function, after HTML files are written:

```python
    # Auto-upload to Foundry if enabled
    if auto_upload:
        logger.info(f"Auto-upload enabled, uploading to {foundry_target}...")
        try:
            from foundry.upload_to_foundry import upload_run_to_foundry

            result = upload_run_to_foundry(
                html_dir=str(html_output_dir),
                target=foundry_target
            )

            if result["failed"] > 0:
                logger.warning(
                    f"Upload completed with errors: "
                    f"{result['uploaded']} succeeded, {result['failed']} failed"
                )
            else:
                logger.info(f"Successfully uploaded {result['uploaded']} journals to Foundry")

        except Exception as e:
            logger.error(f"Auto-upload failed: {e}")
            logger.info("HTML files are still available locally")
    else:
        logger.info("Auto-upload disabled (set FOUNDRY_AUTO_UPLOAD=true to enable)")
```

**Step 4: Test xml_to_html with auto-upload disabled**

```bash
uv run python src/pdf_processing/xml_to_html.py
```

Expected: Completes normally, logs "Auto-upload disabled"

**Step 5: Commit integration**

```bash
git add src/pdf_processing/xml_to_html.py
git commit -m "feat: integrate FoundryVTT auto-upload into xml_to_html pipeline"
```

---

## Task 9: Update Documentation

**Files:**
- Modify: `CLAUDE.md`

**Step 1: Add Foundry upload section to CLAUDE.md**

Add after the "Common Commands" section:

```markdown
## FoundryVTT Integration

**Upload HTML to Journal Entries:**

```bash
# Configure .env first with Foundry credentials
# Set FOUNDRY_AUTO_UPLOAD=true for automatic upload after HTML generation

# Manual upload of latest run (local Foundry)
uv run python src/foundry/upload_to_foundry.py

# Manual upload to The Forge
uv run python src/foundry/upload_to_foundry.py --target forge

# Manual upload of specific run
uv run python src/foundry/upload_to_foundry.py --run-dir output/runs/20250101_120000
```

**Setup Requirements:**
1. Install ThreeHats REST API module in FoundryVTT
2. Generate API keys for both local and Forge instances
3. Add credentials to `.env` (see `.env.example`)
4. Set `FOUNDRY_AUTO_UPLOAD=true` to enable automatic upload after `xml_to_html.py`
```

**Step 2: Update environment setup section**

Add to "Required Configuration" section:

```markdown
4. **FoundryVTT Integration (Optional)**: For automatic journal upload:
   ```
   FOUNDRY_LOCAL_URL=http://localhost:30000
   FOUNDRY_LOCAL_API_KEY=<your_api_key>
   FOUNDRY_FORGE_URL=https://your-game.forge-vtt.com
   FOUNDRY_FORGE_API_KEY=<your_forge_api_key>
   FOUNDRY_RELAY_URL=https://foundryvtt-rest-api-relay.fly.dev
   FOUNDRY_AUTO_UPLOAD=false
   FOUNDRY_TARGET=local
   ```
```

**Step 3: Commit documentation**

```bash
git add CLAUDE.md
git commit -m "docs: add FoundryVTT integration documentation"
```

---

## Task 10: End-to-End Integration Test

**Files:**
- Create: `tests/test_foundry_integration.py`

**Step 1: Write integration test**

`tests/test_foundry_integration.py`:

```python
"""Integration test for FoundryVTT upload pipeline."""

import pytest
import os
from pathlib import Path


@pytest.mark.integration
@pytest.mark.requires_api
def test_foundry_upload_integration(tmp_path, monkeypatch):
    """
    Test complete pipeline: HTML generation → Foundry upload.

    This test requires:
    - FOUNDRY_LOCAL_URL set in environment
    - FOUNDRY_LOCAL_API_KEY set in environment
    - FoundryVTT running locally with REST API module installed
    """
    # Check prerequisites
    if not os.getenv("FOUNDRY_LOCAL_URL"):
        pytest.skip("FOUNDRY_LOCAL_URL not set - skipping integration test")

    # Create test HTML file
    html_dir = tmp_path / "documents" / "html"
    html_dir.mkdir(parents=True)

    test_content = """
    <h1>Test Chapter</h1>
    <p>This is a test journal entry created by automated testing.</p>
    <p>If you see this in FoundryVTT, the integration is working!</p>
    """

    (html_dir / "00_Test_Chapter.html").write_text(test_content)

    # Import after path is set up
    from src.foundry.upload_to_foundry import upload_run_to_foundry

    # Upload
    result = upload_run_to_foundry(str(html_dir), target="local")

    # Verify
    assert result["uploaded"] == 1
    assert result["failed"] == 0

    # Cleanup: Try to find and delete the test journal
    try:
        from src.foundry.client import FoundryClient
        client = FoundryClient(target="local")

        test_journal = client.find_journal_by_name("00_Test_Chapter")
        if test_journal:
            # Note: Would need delete_journal_entry method to clean up
            pass
    except Exception:
        pass  # Cleanup is best-effort
```

**Step 2: Add integration test marker to pytest.ini**

If `pytest.ini` doesn't exist, create it:

```ini
[pytest]
markers =
    unit: Unit tests (no external dependencies)
    integration: Integration tests (make real API calls)
    slow: Slow tests (API calls, large file processing)
    requires_api: Tests requiring API keys
    requires_pdf: Tests requiring PDF files
```

**Step 3: Document how to run integration tests**

Add to CLAUDE.md under Testing section:

```markdown
**FoundryVTT Integration Tests:**
```bash
# Run with local Foundry instance running
uv run pytest tests/test_foundry_integration.py -v

# Skip integration tests
uv run pytest -m "not integration"
```
```

**Step 4: Commit integration test**

```bash
git add tests/test_foundry_integration.py pytest.ini CLAUDE.md
git commit -m "test: add FoundryVTT integration test"
```

---

## Task 11: Manual Testing & Validation

**Manual Testing Steps:**

**Step 1: Install REST API Module in Local Foundry**

1. Start local FoundryVTT
2. Install module using manifest URL
3. Enable in world
4. Generate API key
5. Add to `.env`

**Step 2: Test upload script**

```bash
# Set environment
export FOUNDRY_AUTO_UPLOAD=false

# Generate some HTML first
uv run python src/pdf_processing/xml_to_html.py

# Test upload
uv run python src/foundry/upload_to_foundry.py --target local
```

Expected: Journals appear in FoundryVTT

**Step 3: Test automatic upload**

```bash
# Enable auto-upload
export FOUNDRY_AUTO_UPLOAD=true

# Run full pipeline
uv run python src/pdf_processing/xml_to_html.py
```

Expected: HTML files generated AND uploaded automatically

**Step 4: Verify in FoundryVTT**

1. Open FoundryVTT
2. Check Journal Entries tab
3. Verify chapters appear with correct HTML formatting
4. Verify content matches HTML files

**Step 5: Test Forge upload (if available)**

```bash
# Configure Forge in .env first
uv run python src/foundry/upload_to_foundry.py --target forge
```

Expected: Journals appear in Forge-hosted game

---

## Task 12: Error Handling & Resilience

**Files:**
- Modify: `src/foundry/client.py`
- Modify: `tests/foundry/test_client.py`

**Step 1: Add retry logic test**

Add to `tests/foundry/test_client.py`:

```python
import time
from unittest.mock import call


class TestRetryLogic:
    """Tests for retry behavior on failures."""

    @patch('requests.post')
    @patch('time.sleep')
    def test_create_journal_retries_on_500(self, mock_sleep, mock_post, mock_client):
        """Test that transient failures trigger retries."""
        # Fail twice, succeed on third attempt
        mock_post.side_effect = [
            Mock(status_code=500, text="Server error"),
            Mock(status_code=500, text="Server error"),
            Mock(status_code=200, json=lambda: {"_id": "journal123"})
        ]

        result = mock_client.create_journal_entry_with_retry(
            name="Test",
            content="<p>Test</p>",
            max_retries=3
        )

        assert result["_id"] == "journal123"
        assert mock_post.call_count == 3
        assert mock_sleep.call_count == 2  # Sleep between retries
```

**Step 2: Implement retry logic**

Add to `src/foundry/client.py`:

```python
import time


class FoundryClient:
    # ... existing code ...

    def create_journal_entry_with_retry(
        self,
        name: str,
        content: str,
        folder: str = None,
        max_retries: int = 3,
        retry_delay: float = 2.0
    ) -> Dict[str, Any]:
        """
        Create journal entry with automatic retry on failure.

        Args:
            name: Name of the journal entry
            content: HTML content
            folder: Optional folder ID
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds

        Returns:
            Created journal entry data

        Raises:
            RuntimeError: If all retries fail
        """
        last_error = None

        for attempt in range(max_retries):
            try:
                return self.create_journal_entry(name, content, folder)
            except RuntimeError as e:
                last_error = e
                if attempt < max_retries - 1:
                    logger.warning(
                        f"Attempt {attempt + 1} failed, retrying in {retry_delay}s: {e}"
                    )
                    time.sleep(retry_delay)
                else:
                    logger.error(f"All {max_retries} attempts failed")

        raise RuntimeError(f"Failed after {max_retries} attempts: {last_error}")
```

**Step 3: Update upload script to use retry logic**

In `src/foundry/upload_to_foundry.py`, change `create_or_update_journal` to `create_journal_entry_with_retry` where appropriate.

**Step 4: Run tests**

```bash
uv run pytest tests/foundry/ -v
```

Expected: All tests PASS

**Step 5: Commit resilience improvements**

```bash
git add src/foundry/client.py tests/foundry/test_client.py src/foundry/upload_to_foundry.py
git commit -m "feat: add retry logic for transient API failures"
```

---

## Task 13: Final Testing & Documentation

**Step 1: Run full test suite**

```bash
# Unit tests only
uv run pytest -m "not integration and not slow" -v

# All tests (if Foundry is running)
uv run pytest -v
```

Expected: All tests PASS

**Step 2: Update README (if exists)**

If `README.md` exists, add a section about Foundry integration.

**Step 3: Create user guide**

Create `docs/FOUNDRY_SETUP.md` with step-by-step setup instructions:

```markdown
# FoundryVTT Integration Setup Guide

## Prerequisites

- FoundryVTT v10+ installed locally OR The Forge subscription
- Python environment set up (see main README)

## Installation Steps

### 1. Install REST API Module

**Local FoundryVTT:**
1. Launch FoundryVTT
2. Navigate to "Add-on Modules"
3. Click "Install Module"
4. Paste: `https://github.com/ThreeHats/foundryvtt-rest-api/releases/latest/download/module.json`
5. Click "Install"

**The Forge:**
- Same process in your Forge-hosted game

### 2. Generate API Keys

1. Launch your world
2. Go to "Game Settings" → "Configure Settings"
3. Find "Foundry REST API" module settings
4. Click "Generate API Key"
5. Copy the key (you'll need it for .env)

Repeat for both local and Forge if using both.

### 3. Configure Environment

Add to `.env`:

```bash
FOUNDRY_LOCAL_URL=http://localhost:30000
FOUNDRY_LOCAL_API_KEY=<paste_your_key>
FOUNDRY_FORGE_URL=https://your-game.forge-vtt.com
FOUNDRY_FORGE_API_KEY=<paste_forge_key>
FOUNDRY_RELAY_URL=https://foundryvtt-rest-api-relay.fly.dev
FOUNDRY_AUTO_UPLOAD=false
FOUNDRY_TARGET=local
```

### 4. Test Upload

```bash
# Generate HTML if you haven't already
uv run python src/pdf_processing/xml_to_html.py

# Test manual upload
uv run python src/foundry/upload_to_foundry.py --target local
```

Check FoundryVTT → Journal Entries for your chapters.

### 5. Enable Auto-Upload (Optional)

Edit `.env`:
```bash
FOUNDRY_AUTO_UPLOAD=true
```

Now `xml_to_html.py` will automatically upload after generation.

## Troubleshooting

**"FOUNDRY_LOCAL_URL not set"**
- Check `.env` file exists and has correct values
- Ensure you ran `source .venv/bin/activate` or used `uv run`

**"Connection timeout"**
- Verify FoundryVTT is running
- Check URL in `.env` matches actual Foundry address
- Test relay server: `curl https://foundryvtt-rest-api-relay.fly.dev/`

**Journals not appearing**
- Check FoundryVTT logs for errors
- Verify API key is correct
- Ensure REST API module is enabled in world

## Architecture Notes

The integration uses a relay server architecture:
- Your script → HTTP → Relay Server → WebSocket → Foundry Module → FoundryVTT

This allows the script to work even when Foundry is behind a firewall.
```

**Step 4: Commit documentation**

```bash
git add docs/FOUNDRY_SETUP.md
git commit -m "docs: add FoundryVTT setup guide"
```

**Step 5: Final commit and summary**

```bash
git log --oneline -15
```

Review commit history to ensure all tasks are complete.

---

## Execution Complete

Plan complete and saved to `docs/plans/2025-10-16-foundry-journal-upload.md`. Two execution options:

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

Which approach?

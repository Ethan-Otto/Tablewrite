"""Orchestrate full actor creation pipeline from description to FoundryVTT."""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Union
from pydantic import BaseModel

logger = logging.getLogger(__name__)


def _create_output_directory(base_dir: str = "output/runs") -> Path:
    """
    Create timestamped output directory for actor creation files.

    Args:
        base_dir: Base directory for runs (default: "output/runs")

    Returns:
        Path to created directory: output/runs/<timestamp>/actors/

    Example:
        output/runs/20241103_143022/actors/
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(base_dir) / timestamp / "actors"
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Created output directory: {output_dir}")
    return output_dir


def _save_intermediate_file(
    content: Union[str, dict, BaseModel],
    filepath: Path,
    description: str = "file"
) -> Path:
    """
    Save intermediate output to file (text or JSON).

    Args:
        content: Content to save (str for text, dict/BaseModel for JSON)
        filepath: Full path to save file
        description: Human-readable description for logging

    Returns:
        Path to saved file

    Raises:
        IOError: If file write fails

    Examples:
        # Save raw text
        _save_intermediate_file("Goblin\\nSmall humanoid...",
                               output_dir / "raw_text.txt",
                               "raw stat block text")

        # Save Pydantic model as JSON
        _save_intermediate_file(stat_block,
                               output_dir / "stat_block.json",
                               "StatBlock model")
    """
    try:
        filepath.parent.mkdir(parents=True, exist_ok=True)

        if isinstance(content, str):
            # Save as text file
            filepath.write_text(content, encoding='utf-8')
        elif isinstance(content, BaseModel):
            # Save Pydantic model as JSON
            filepath.write_text(content.model_dump_json(indent=2), encoding='utf-8')
        elif isinstance(content, dict):
            # Save dict as JSON
            filepath.write_text(json.dumps(content, indent=2), encoding='utf-8')
        else:
            raise ValueError(f"Unsupported content type: {type(content)}")

        logger.debug(f"Saved {description} to: {filepath}")
        return filepath

    except Exception as e:
        logger.error(f"Failed to save {description} to {filepath}: {e}")
        raise IOError(f"Failed to save {description}: {e}") from e

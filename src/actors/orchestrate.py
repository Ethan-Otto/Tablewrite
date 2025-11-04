"""Orchestrate full actor creation pipeline from description to FoundryVTT."""

import logging
from pathlib import Path
from datetime import datetime

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

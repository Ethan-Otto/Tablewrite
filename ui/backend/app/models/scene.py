"""Scene models - reusing existing Scene from src/scene_extraction."""

import sys
from pathlib import Path
import importlib.util

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent

# Import models module directly without triggering package __init__
models_path = project_root / "src" / "scene_extraction" / "models.py"
spec = importlib.util.spec_from_file_location("scene_extraction_models", models_path)
models_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(models_module)

# Export the models
Scene = models_module.Scene
ChapterContext = models_module.ChapterContext

__all__ = ["Scene", "ChapterContext"]

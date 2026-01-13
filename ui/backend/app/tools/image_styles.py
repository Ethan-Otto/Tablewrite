"""Image style prompts - re-exported from shared src/image_styles.py.

This module re-exports all styles from the central source of truth.
Import from here in backend code for convenience.
"""

import sys
from pathlib import Path

# Add src to path for imports
_src_dir = Path(__file__).parent.parent.parent.parent.parent / "src"
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

# Re-export everything from the shared module
from image_styles import (  # noqa: E402, F401
    # Scene styles
    SCENE_STYLE,
    SCENE_STYLE_CHARCOAL,
    SCENE_STYLE_SIMPLE,
    # Actor styles
    ACTOR_STYLE_WATERCOLOR,
    ACTOR_STYLE_OIL,
    ACTOR_STYLE_PIXEL,
    ACTOR_STYLE_CHARCOAL,
    ACTOR_STYLE_JOURNAL,
    # Battle map styles
    BATTLEMAP_STYLE,
    # Helper functions
    get_actor_style,
    get_scene_style,
)

# Backward compatibility aliases
ACTOR_STYLE = ACTOR_STYLE_WATERCOLOR

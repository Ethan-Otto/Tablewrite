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

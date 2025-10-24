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

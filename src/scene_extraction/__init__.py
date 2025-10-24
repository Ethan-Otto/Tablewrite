"""Scene extraction and artwork generation."""

from .models import Scene, ChapterContext
from .extract_context import extract_chapter_context

__all__ = ['Scene', 'ChapterContext', 'extract_chapter_context']

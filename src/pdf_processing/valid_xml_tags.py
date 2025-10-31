"""
Valid XML tags for D&D module conversion.

This module defines all approved XML tags that can be used in the PDF to XML
conversion process. Any tags not in this list will trigger a validation error.
"""

# Approved XML tags for generated content
APPROVED_XML_TAGS = {
    # Structure
    'page', 'header', 'footer', 'page_number', 'chapter_title',

    # Headings (semantic hierarchy: Chapter > Section > Subsection)
    'title', 'section', 'subsection', 'subsubsection',

    # Content
    'p', 'boxed_text',

    # Formatting (used internally, converted to Markdown)
    'b', 'i', 'italic', 'bold', 'em', 'strong',

    # Lists
    'list', 'item',

    # Tables
    'table', 'table_row', 'table_cell',

    # Monsters/Stats
    'stat_block',  # D&D 5e stat blocks (raw text preserved)
    'monster', 'name', 'size', 'type', 'alignment',
    'armor_class', 'hit_points', 'speed',
    'strength', 'dexterity', 'constitution', 'intelligence', 'wisdom', 'charisma',
    'skills', 'senses', 'languages', 'challenge_rating',
    'abilities', 'actions',

    # Definition lists
    'definition_list', 'definition_item', 'term', 'definition',

    # Special cases
    'error',  # For error handling
}

# Tags organized by category for prompt generation
TAGS_BY_CATEGORY = {
    "Structure": ['page', 'header', 'footer', 'page_number', 'chapter_title'],
    "Headings": ['title', 'section', 'subsection', 'subsubsection'],
    "Content": ['p', 'boxed_text'],
    "Lists": ['list', 'item'],
    "Tables": ['table', 'table_row', 'table_cell'],
    "Monsters": [
        'stat_block',  # D&D 5e stat blocks (raw text)
        'monster', 'name', 'size', 'type', 'alignment',
        'armor_class', 'hit_points', 'speed',
        'strength', 'dexterity', 'constitution',
        'intelligence', 'wisdom', 'charisma',
        'skills', 'senses', 'languages', 'challenge_rating',
        'abilities', 'actions'
    ],
    "Definition Lists": ['definition_list', 'definition_item', 'term', 'definition'],
}

def get_approved_tags_text() -> str:
    """
    Returns a formatted string of approved tags organized by category.
    Suitable for including in prompts to Gemini.
    """
    return "\n".join([
        f"- **{category}**: {', '.join(f'<{tag}>' for tag in tags)}"
        for category, tags in TAGS_BY_CATEGORY.items()
    ])

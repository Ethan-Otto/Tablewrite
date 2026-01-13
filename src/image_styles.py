"""Shared image style prompts for Imagen generation.

This is the single source of truth for all image generation style prompts.
Both the backend tools and src modules should import from here.

Usage:
    from image_styles import SCENE_STYLE_CHARCOAL, get_actor_style
"""

# =============================================================================
# SCENE STYLES (for environment/location images)
# =============================================================================

# Detailed digital painting style for scenes
SCENE_STYLE = (
    "realistic digital painting, dark fantasy art style, "
    "detailed environment painting, moody atmospheric lighting, "
    "subtle volumetric light, loose painterly brushstrokes, "
    "muted dark earthy tones with green and brown, "
    "deep shadows, atmospheric depth, "
    "textured realistic surfaces, "
    "professional concept art, no text or labels"
)

# Charcoal sketch style for scenes (default)
SCENE_STYLE_CHARCOAL = (
    "messy rushed charcoal sketch on textured paper, "
    "loose unfinished environment drawing, heavy smudging, blurry edges, "
    "quick gestural rendering, intentionally rough and imprecise, "
    "raw unpolished sketch, scribbled shading for depth, "
    "grainy texture, monochromatic grayscale, atmospheric, no text"
)

# Simple fantasy style
SCENE_STYLE_SIMPLE = "fantasy illustration, D&D 5e art style, detailed environment, high quality"

# =============================================================================
# ACTOR STYLES (for character/creature portraits)
# =============================================================================

# Watercolor style for actors
ACTOR_STYLE_WATERCOLOR = (
    "fantasy watercolor painting, soft wet-on-wet blending, "
    "muted earthy color palette, loose expressive brushwork, "
    "atmospheric washes, subtle color bleeding at edges, "
    "storybook illustration quality, no text"
)

# Oil painting style for actors
ACTOR_STYLE_OIL = (
    "traditional oil painting style, thick impasto brushstrokes, "
    "rich dark fantasy colors, dramatic chiaroscuro lighting, "
    "classical portrait composition, museum quality fine art, "
    "deep shadows and warm highlights, no text"
)

# 16-bit pixel art style for actors
ACTOR_STYLE_PIXEL = (
    "low resolution pixel art, 64x64 sprite style, "
    "very limited 16-color palette, chunky visible pixels, "
    "retro SNES RPG character portrait, no gradients, "
    "classic 1990s video game aesthetic, crisp hard pixel edges, "
    "no anti-aliasing, no smoothing, blocky simple shapes, no text"
)

# Charcoal sketch style for actors (default)
ACTOR_STYLE_CHARCOAL = (
    "messy rushed charcoal sketch on textured paper, "
    "loose unfinished strokes, heavy smudging, blurry edges, "
    "quick gestural drawing, intentionally rough and imprecise, "
    "not sharp, raw unpolished sketch, scribbled shading, "
    "grainy texture, monochromatic grayscale, no text"
)

# Pen and ink journal sketch style for actors
ACTOR_STYLE_JOURNAL = (
    "pen and ink sketch on aged parchment paper, "
    "fine crosshatching, naturalist field journal illustration, "
    "detailed linework, sepia and brown ink tones, "
    "Victorian explorer's notebook style, hand-drawn quality, "
    "slightly rough edges, scientific illustration aesthetic, no text"
)

# =============================================================================
# BATTLE MAP STYLES
# =============================================================================

# Style for battle maps (top-down view)
BATTLEMAP_STYLE = (
    "top-down battle map, tabletop RPG style, "
    "clear grid-friendly layout, detailed terrain textures, "
    "muted fantasy colors, parchment tones, "
    "clear boundaries and pathways, "
    "professional cartography style, no text or labels"
)

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_actor_style(style_name: str = "charcoal") -> str:
    """Get actor style prompt by name.

    Args:
        style_name: "charcoal", "watercolor", "oil", "pixel", or "journal"

    Returns:
        The style prompt string
    """
    styles = {
        "watercolor": ACTOR_STYLE_WATERCOLOR,
        "oil": ACTOR_STYLE_OIL,
        "pixel": ACTOR_STYLE_PIXEL,
        "charcoal": ACTOR_STYLE_CHARCOAL,
        "journal": ACTOR_STYLE_JOURNAL,
    }
    return styles.get(style_name, ACTOR_STYLE_CHARCOAL)


def get_scene_style(style_name: str = "charcoal") -> str:
    """Get scene style prompt by name.

    Args:
        style_name: "charcoal", "detailed", or "simple"

    Returns:
        The style prompt string
    """
    styles = {
        "charcoal": SCENE_STYLE_CHARCOAL,
        "detailed": SCENE_STYLE,
        "simple": SCENE_STYLE_SIMPLE,
    }
    return styles.get(style_name, SCENE_STYLE_CHARCOAL)

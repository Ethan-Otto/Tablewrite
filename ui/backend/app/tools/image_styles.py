"""Shared image style prompts for Imagen generation."""

# Default style for D&D fantasy scene illustrations
SCENE_STYLE = (
    "realistic digital painting, dark fantasy art style, "
    "detailed environment painting, moody atmospheric lighting, "
    "subtle volumetric light, loose painterly brushstrokes, "
    "muted dark earthy tones with green and brown, "
    "deep shadows, atmospheric depth, "
    "textured realistic surfaces, "
    "professional concept art, no text or labels"
)

# Style for D&D character/actor portraits (default: watercolor)
ACTOR_STYLE = (
    "fantasy watercolor painting, soft wet-on-wet blending, "
    "muted earthy color palette, loose expressive brushwork, "
    "atmospheric washes, subtle color bleeding at edges, "
    "storybook illustration quality, no text"
)

# Alternative: Oil painting style for actors
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

# Rough charcoal sketch style for actors
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

def get_actor_style(style_name: str = "watercolor") -> str:
    """Get actor style prompt by name.

    Args:
        style_name: "watercolor", "oil", "pixel", "charcoal", or "journal"

    Returns:
        The style prompt string
    """
    if style_name == "oil":
        return ACTOR_STYLE_OIL
    if style_name == "pixel":
        return ACTOR_STYLE_PIXEL
    if style_name == "charcoal":
        return ACTOR_STYLE_CHARCOAL
    if style_name == "journal":
        return ACTOR_STYLE_JOURNAL
    return ACTOR_STYLE  # Default to watercolor


# Style for battle maps (top-down view)
BATTLEMAP_STYLE = (
    "top-down battle map, tabletop RPG style, "
    "clear grid-friendly layout, detailed terrain textures, "
    "muted fantasy colors, parchment tones, "
    "clear boundaries and pathways, "
    "professional cartography style, no text or labels"
)

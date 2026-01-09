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

def get_actor_style(style_name: str = "watercolor") -> str:
    """Get actor style prompt by name.

    Args:
        style_name: Either "watercolor" or "oil"

    Returns:
        The style prompt string
    """
    if style_name == "oil":
        return ACTOR_STYLE_OIL
    return ACTOR_STYLE  # Default to watercolor


# Style for battle maps (top-down view)
BATTLEMAP_STYLE = (
    "top-down battle map, tabletop RPG style, "
    "clear grid-friendly layout, detailed terrain textures, "
    "muted fantasy colors, parchment tones, "
    "clear boundaries and pathways, "
    "professional cartography style, no text or labels"
)

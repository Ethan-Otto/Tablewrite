# Scene Artwork Configuration

## Environment Variables

### `ENABLE_SCENE_ARTWORK`
- **Type:** Boolean (`true`/`false`)
- **Default:** `true`
- **Description:** Enable/disable scene artwork generation in full pipeline

### `IMAGE_STYLE_PROMPT`
- **Type:** String
- **Default:** `"fantasy illustration, D&D 5e art style, detailed environment, high quality"`
- **Description:** Style prompt for Gemini Imagen when generating scene artwork

### `IMAGE_OUTPUT_DIR`
- **Type:** String
- **Default:** `"scene_artwork"`
- **Description:** Directory name for scene artwork output (relative to run directory)

## Usage Examples

**Default settings:**
```bash
uv run python scripts/full_pipeline.py
```

**Custom style:**
```bash
IMAGE_STYLE_PROMPT="top-down battle map, grid overlay, tactical view" uv run python scripts/full_pipeline.py
```

**Disable scene generation:**
```bash
ENABLE_SCENE_ARTWORK=false uv run python scripts/full_pipeline.py
# Or use flag:
uv run python scripts/full_pipeline.py --skip-scenes
```

## Cost Considerations

Scene artwork generation uses Gemini Imagen API, which has per-image costs:
- ~$0.02-0.10 per image (check current Gemini pricing)
- A typical D&D module chapter may have 10-30 scenes
- Total cost per chapter: ~$0.20-$3.00

**Recommendations:**
1. Start with a single chapter to test (`--xml-file` flag)
2. Review generated scenes before generating full module
3. Use `--skip-scenes` flag to skip artwork in draft runs

# Long-Term Features Roadmap

**Date:** 2025-10-18
**Status:** Planning / Conceptual

## Overview

This document captures long-term feature ideas and enhancements for the D&D module converter. These are conceptual features that require design discussion before implementation.

## Architecture: Initial Generation vs Post-Processing

**Core Design Principle:** Keep the initial XML generation focused on document structure, use specialized post-processing for feature extraction.

### Initial XML Generation (pdf_to_xml.py)
**Focus:** Document structure and foundational elements
- Extract semantic structure (sections, headings, paragraphs, lists)
- Preserve formatting (bold, italic, tables)
- **Tag stat blocks only** (`<stat_block name="...">`)

**Why stat blocks are the exception:**
- Visually distinct in PDFs (boxed, formatted blocks)
- Foundational - other features reference them (NPCs, scenes)
- Unambiguous and easy to identify
- Low risk of confusion

### Post-Processing (specialized Gemini analysis)
**Focus:** Use case-specific entity extraction
- Scene identification (analyze XML for location descriptions)
- NPC extraction (analyze XML for named characters, link to stat blocks)
- Magic item extraction (analyze XML for item descriptions)

**Benefits:**
- ✅ Focused prompts = better accuracy
- ✅ Easier debugging (each step isolated)
- ✅ Iterative improvement (refine extractors independently)
- ✅ Optional features (enable/disable as needed)

---

## Feature Ideas

### 1. AI-Generated Scene Artwork

**Status:** ✔️ Completed (2025-10-24)

**Implementation:** Post-processing workflow with Gemini context extraction, scene identification, and Imagen artwork generation. Creates FoundryVTT journal page with scene gallery.

**Key Files:**
- `src/scene_extraction/` - Core extraction and generation modules
  - `models.py` - Scene and ChapterContext Pydantic models
  - `extract_context.py` - Chapter environmental context extraction
  - `identify_scenes.py` - Physical location scene identification
  - `generate_artwork.py` - Scene artwork generation with Gemini Imagen
  - `create_gallery.py` - FoundryVTT journal gallery HTML generator
- `scripts/generate_scene_art.py` - Main processing script
- Integrated into `scripts/full_pipeline.py` as optional step (use `--skip-scenes` to disable)

**Description:**
Automatically generate artwork for room/location descriptions in D&D modules:
1. Analyze generated XML with Gemini to identify physical location sections (post-processing)
2. Extract scene descriptions (no XML tagging during initial generation)
3. Generate images using Gemini Imagen
4. Inputs: scene name, description text, chapter environmental context, configurable style prompt

**Motivation:**
- Visual aids enhance D&D gameplay and immersion
- Manual art commissioning is expensive and time-consuming
- Module PDFs contain rich location descriptions perfect for image generation
- Could embed generated images into FoundryVTT journals or export separately

**Design Decisions:**
- **Processing Stage**: Post-processing (analyzes generated XML, does NOT tag during initial generation)
- **Scene Identification**: Separate Gemini call analyzes section/subsection structure to identify rooms/locations, extracts physical descriptions (NO NPCs, NO monsters - physical environment only)
- **Image Generator**: Gemini Imagen (reuse existing API integration)
- **Chapter Context**: Gemini infers environmental context from full chapter XML automatically (tropical vs temperate, foggy/sunny, underground, lighting, terrain, etc.)
- **Output Format**:
  - Images saved to `output/runs/<timestamp>/images/`
  - New FoundryVTT journal page appended at end with all scene images
  - Each scene includes header showing section/subsection path (e.g., "Chapter 2 → The Cragmaw Hideout → Area 1")
- **Scene Scope**: Physical locations only - rooms, outdoor areas, environments. Exclude NPCs, monsters, items

**Open Questions:**
- **Style Configuration**: Single global style or configurable per-chapter/per-scene?
- **Cost Management**: Image generation can be expensive - batch limits, preview mode, approval workflow before generating all images?
- **Image Naming**: How to name image files? (section name, sequential numbers, UUIDs?)
- **Preview Mode**: Generate low-res previews first before full resolution?

**Dependencies:**
- Stable XML schema (need consistent structure for scene extraction)
- Image generation API integration (new module, similar to Gemini integration)
- Configuration system for style prompts and generator settings

**Notes:**
- Could start simple: extract `<art_scene>` → generate → save to `output/runs/<timestamp>/images/`
- Future enhancement: embed images into FoundryVTT as journal images or scene backgrounds
- Example style prompts: "fantasy illustration, D&D 5e art style, detailed environment" or "top-down battle map, grid overlay"
- Gemini has built-in image generation (Imagen), could reuse existing API setup

**Technical Sketch:**
```python
# New module: src/image_generation/generate_scene_art.py

def extract_chapter_context(xml_content):
    """
    Use Gemini to analyze chapter XML and extract environmental context.
    Returns: dict with environment type, weather, atmosphere, etc.
    """

def identify_scene_locations(xml_content, chapter_context):
    """
    Use Gemini to analyze XML structure and identify room/location sections.
    Input: Full chapter XML + environmental context
    Output: List of scenes with {section_path, name, description, context}

    Prompt asks Gemini to:
    - Find sections/subsections that describe physical locations
    - Extract ONLY physical/environmental descriptions (no NPCs/monsters)
    - Include section hierarchy for naming (e.g., "Chapter 2 → Area 1")
    """

def generate_scene_image(scene, style_prompt):
    """
    Call Gemini Imagen to generate image.
    Input: scene dict with name, description, chapter context
    Output: image bytes
    """

def create_scene_gallery_page(scenes, images):
    """
    Create FoundryVTT journal page HTML with all scenes.
    Format: [Section Header] → [Image] for each scene
    """

def process_chapter(xml_file, output_dir, style_config):
    """
    Main workflow:
    1. Load chapter XML
    2. Extract chapter environmental context (Gemini call)
    3. Identify scene locations (Gemini call with XML + context)
    4. Generate images for each scene (Gemini Imagen calls)
    5. Save images to output_dir/images/
    6. Create scene gallery journal page
    """
```

**Workflow Integration:**
```
pdf_to_xml.py → [generates XML]
    ↓
generate_scene_art.py → [analyzes XML, generates images]
    ↓
upload_to_foundry.py → [uploads journal + scene gallery page]
```

**Configuration (in .env or config file):**
```
IMAGE_GENERATOR=gemini  # or dalle, sd, etc.
IMAGE_API_KEY=...
IMAGE_STYLE_PROMPT=fantasy illustration, D&D 5e art style, detailed environment
IMAGE_OUTPUT_DIR=images
```

---

### 2. Stat Block & NPC Extraction with Actor Generation

**Status:** 💭 Conceptual

**Description:**
Extract and structure D&D 5e stat blocks and NPCs from modules, then create FoundryVTT Actor objects:

1. **Stat Block Tagging** (during XML generation):
   - Update Gemini prompt to identify D&D 5e stat blocks in PDF
   - Tag with `<stat_block name="creature_name">...</stat_block>` in XML
   - Preserve stat block formatting and structure

2. **NPC Extraction** (post-XML analysis):
   - Analyze generated XML to identify NPCs mentioned in narrative
   - Extract NPC summary and plot relevance
   - Link NPCs to stat blocks if creature has stats
   - Generate structured NPC data: {name, description, plot_role, stat_block_ref}

3. **Actor Management** (FoundryVTT integration):
   - Create FoundryVTT Actor objects from stat blocks
   - Two types: Named NPCs (unique) and Generic Creatures (shared stat block)
   - Import into FoundryVTT compendium or world actors
   - Link journal entries to actors for easy reference

**Motivation:**
- Stat blocks are critical for D&D gameplay but tedious to manually input
- NPCs with context help DMs understand story and character motivations
- FoundryVTT Actors enable drag-and-drop gameplay, combat tracking, automated rolls
- Linking NPCs to stat blocks provides complete character information in one place

**Design Decisions:**
- **Processing Stages**:
  - **Stat Block Tagging**: During initial XML generation (tagged as `<stat_block name="...">raw text</stat_block>`)
  - **NPC Extraction**: Post-processing (Gemini analyzes generated XML to identify named NPCs)
- **Stat Block Parsing**: Gemini parses raw text into Pydantic StatBlock model (structured D&D 5e fields)
- **Validation**: Field validation only (check required fields exist: name, AC, HP, CR)
- **Compendium Lookup**: Search ALL user's FoundryVTT compendiums by name. If match found, use that actor (no stat comparison)
- **NPC Actors**: Create bio-only Actors with link to creature stat block compendium entry (@UUID syntax)
- **NPC Stats**: NPCs have NO stats directly - bio links to creature stat block (e.g., "Klarg" links to "Goblin Boss")
- **Stat Block Not Found**: If NPC's creature_stat_block_name doesn't exist in compendiums, create it from stat block
- **Unnamed Creatures**: Do nothing - assume DM will drag from compendium manually
- **Actor Import**: Create new Actors in module-specific compendium pack

**Resolved Design Questions:**
- ✅ **Stat Block Parsing**: Gemini parses raw XML text → Pydantic StatBlock
- ✅ **Compendium Reuse**: Always use compendium if name matches (any compendium in user's FoundryVTT)
- ✅ **NPC Implementation**: Bio-only Actor with @UUID link to creature stat block
- ✅ **Missing Stat Block**: Create Actor from stat block directly
- ✅ **Generic Creatures**: No special handling (already in compendium)

**Open Questions:**
- **Token Images**: Generate token art for actors, or leave blank?
- **Compendium Pack Name**: Auto-generate (e.g., "lost-mine-of-phandelver-creatures") or user configurable?

**Dependencies:**
- Stat block tagging requires updated Gemini XML prompt
- FoundryVTT Actor creation requires understanding D&D 5e system's data schema
- May need foundry-vtt-types or documentation for Actor structure

**Notes:**
- D&D 5e stat blocks have standard format: name, size/type, AC, HP, stats, traits, actions
- FoundryVTT's D&D 5e system has specific Actor data structure (see dnd5e system docs)
- Could leverage existing parsers (e.g., 5e-statblock-parser libraries) if available

**Technical Sketch:**
```python
# Step 1: Updated Gemini prompt in src/pdf_processing/pdf_to_xml.py
# "Tag D&D 5e stat blocks with <stat_block name='creature_name'>raw text</stat_block>"

# Step 2: New module: src/stat_blocks/parse_stat_blocks.py

from pydantic import BaseModel, validator

class StatBlock(BaseModel):
    """D&D 5e stat block structure."""
    name: str
    raw_text: str  # Always preserve original

    # Required fields
    armor_class: int
    hit_points: int
    challenge_rating: float

    # Optional validated fields
    size: Optional[str]
    type: Optional[str]
    alignment: Optional[str]
    abilities: Optional[Dict[str, int]]  # STR, DEX, CON, INT, WIS, CHA
    # ... etc

    @validator('armor_class')
    def validate_ac(cls, v):
        if not (1 <= v <= 30):
            raise ValueError(f"AC {v} out of range")
        return v

def parse_stat_block_with_gemini(raw_text: str) -> StatBlock:
    """Use Gemini to parse raw stat block text into structured data."""
    # Gemini prompt: "Parse this D&D 5e stat block into JSON with fields: name, armor_class, hit_points..."
    # Returns validated StatBlock object

def extract_stat_blocks_from_xml(xml_file: str) -> List[StatBlock]:
    """Extract all <stat_block> elements and parse them."""

# Step 3: New module: src/npc_extraction/extract_npcs.py

class NPC(BaseModel):
    """Named NPC with plot context."""
    name: str
    creature_stat_block_name: str  # Name of creature stat block this NPC uses
    description: str
    plot_relevance: str
    location: Optional[str]

def identify_npcs_with_gemini(xml_content: str) -> List[NPC]:
    """
    Use Gemini to analyze XML and identify named NPCs.

    Prompt asks Gemini to:
    - Find named NPCs in narrative
    - Provide summary and plot role
    - Identify creature stat block name (e.g., "Klarg" → "Goblin Boss")
    """

# Step 4: New module: src/foundry/actors.py

class ActorManager:
    """Manages FoundryVTT Actor creation."""

    def search_all_compendiums(self, name: str) -> Optional[str]:
        """Search all user compendiums for actor by name. Returns UUID or None."""

    def create_creature_actor(self, stat_block: StatBlock) -> str:
        """Create Actor from stat block. Returns UUID."""
        actor_data = {
            "name": stat_block.name,
            "type": "npc",
            "system": {
                "attributes": {
                    "ac": {"value": stat_block.armor_class},
                    "hp": {"value": stat_block.hit_points}
                },
                # ... map all stat block fields to D&D 5e system schema
            }
        }
        return self.client.create_actor(actor_data)

    def create_npc_actor(self, npc: NPC, stat_block_uuid: Optional[str]) -> str:
        """Create bio-only NPC Actor with link to creature stat block."""
        bio = f"""
        <h2>{npc.name}</h2>
        <p>{npc.description}</p>
        <p><strong>Plot Role:</strong> {npc.plot_relevance}</p>
        """
        if stat_block_uuid:
            bio += f'<p><strong>Stats:</strong> @UUID[{stat_block_uuid}]{{See {npc.creature_stat_block_name}}}</p>'

        actor_data = {
            "name": npc.name,
            "type": "npc",
            "system": {},  # No stats
            "biography": {"value": bio}
        }
        return self.client.create_actor(actor_data)

# Step 5: Integration in scripts/full_pipeline.py

def process_actors(run_dir: str):
    """Main actor processing workflow."""

    # 1. Extract and parse stat blocks
    stat_blocks = extract_stat_blocks_from_xml(f"{run_dir}/documents/*.xml")

    # 2. Extract NPCs
    npcs = identify_npcs_with_gemini(xml_content)

    # 3. Process stat blocks (create or lookup)
    creature_refs = {}
    for stat_block in stat_blocks:
        existing_uuid = actor_mgr.search_all_compendiums(stat_block.name)
        if existing_uuid:
            creature_refs[stat_block.name] = existing_uuid
        else:
            new_uuid = actor_mgr.create_creature_actor(stat_block)
            creature_refs[stat_block.name] = new_uuid

    # 4. Create NPC actors
    for npc in npcs:
        stat_block_uuid = creature_refs.get(npc.creature_stat_block_name)
        actor_mgr.create_npc_actor(npc, stat_block_uuid)
```

**Workflow Integration:**
```
pdf_to_xml.py → [generates XML with <stat_block> tags (ONLY stat blocks tagged)]
    ↓
parse_stat_blocks.py → [parses <stat_block> into Pydantic StatBlock objects]
    ↓
extract_npcs.py → [Gemini identifies NPCs from XML, links to stat blocks]
    ↓
actors.py (ActorManager) → [creates creature Actors + NPC Actors]
    ↓
upload_to_foundry.py → [uploads actors + journals]
```

**Configuration (.env):**
```
ACTOR_IMPORT_MODE=compendium  # or "world"
ACTOR_COMPENDIUM_NAME=module-creatures
PARSE_STAT_BLOCKS=true  # parse into structured data (Pydantic) vs raw text only
ACTOR_SEARCH_ALL_COMPENDIUMS=true  # search all user compendiums or just specified ones
```

---

### 3. Magic Item Extraction & Compendium Linking

**Status:** 💭 Conceptual

**Description:**
Extract magic items from D&D modules and create FoundryVTT Item entities with compendium linking:

1. **Item Identification** (post-processing):
   - Gemini analyzes generated XML to identify magic item descriptions
   - Extract: name, type, rarity, attunement, properties, description
   - NO tagging during initial XML generation

2. **Item Parsing**:
   - Use Gemini to parse item descriptions into structured data (Pydantic MagicItem model)
   - Validate against D&D 5e item schema

3. **Compendium Linking** (FoundryVTT integration):
   - Search ALL user compendiums for matching item by name
   - If found: create journal links using @UUID syntax
   - If not found: create new Item entity from description
   - Link items to NPCs/locations where they appear

4. **Journal Integration**:
   - Replace item mentions in text with clickable @UUID links
   - Example: "The *+1 longsword*" → "@UUID[Compendium.dnd5e.items.longsword-1]{+1 longsword}"

**Motivation:**
- Magic items are core D&D rewards and gameplay drivers
- Manual item creation is time-consuming and error-prone
- Linking items in journals provides instant reference (stats, properties)
- Compendium reuse avoids duplicating SRD items
- Custom items from modules need to be accessible in FoundryVTT

**Design Decisions:**
- **Processing Stage**: Post-processing (analyzes generated XML, does NOT tag during initial generation)
- **Item Identification**: Gemini analyzes XML to identify magic item descriptions
- **Item Parsing**: Gemini parses item descriptions into Pydantic MagicItem model
- **Compendium Lookup**: Search all user compendiums by name, use if match found
- **No Match Found**: Create new Item entity in module compendium
- **Journal Linking**: Auto-replace item mentions with @UUID links in journal HTML

**Open Questions:**
- **Item Detection**: How to distinguish magic items from mundane gear? (Gemini infers, or only tag explicitly described items?)
- **Partial Matches**: "Longsword +1" vs "+1 Longsword" - fuzzy matching or exact?
- **Item Location Tracking**: Should we track which NPCs/locations have which items?
- **Mundane Items**: Tag regular equipment too, or only magic items?
- **Consumables**: Handle potions, scrolls separately from permanent items?

**Dependencies:**
- Item tagging requires updated Gemini XML prompt
- FoundryVTT Item creation requires D&D 5e item schema
- May need item type taxonomy (weapon, armor, wondrous, consumable, etc.)

**Notes:**
- D&D 5e items have properties: type, rarity, attunement, damage/AC, magical properties
- FoundryVTT's D&D 5e system has specific Item data structure
- Could leverage SRD item compendium for common items
- Example items: +1 Longsword, Potion of Healing, Cloak of Protection

**Technical Sketch:**
```python
# Step 1: New module: src/items/extract_items.py

def identify_magic_items_with_gemini(xml_content: str) -> List[Dict]:
    """
    Use Gemini to analyze XML and identify magic item descriptions.

    Prompt asks Gemini to:
    - Find magic item descriptions in the XML
    - Extract item name, description text, location/context
    - Distinguish magic items from mundane gear mentions

    Returns: List of raw item descriptions for parsing
    """

# Step 2: New module: src/items/parse_items.py

from pydantic import BaseModel

class MagicItem(BaseModel):
    """D&D 5e magic item structure."""
    name: str
    raw_text: str  # Always preserve original

    # Required fields
    type: str  # weapon, armor, wondrous, potion, scroll, etc.
    rarity: str  # common, uncommon, rare, very rare, legendary, artifact

    # Optional fields
    attunement: Optional[bool]
    description: str
    properties: Optional[List[str]]
    damage: Optional[str]  # For weapons
    armor_class: Optional[int]  # For armor

    # Location context
    source_section: Optional[str]
    found_with: Optional[str]  # NPC or location name

def parse_magic_item_with_gemini(raw_text: str) -> MagicItem:
    """Use Gemini to parse item description into structured data."""
    # Gemini prompt: "Parse this D&D 5e magic item into JSON..."

def extract_magic_items_from_xml(xml_file: str) -> List[MagicItem]:
    """Extract all <magic_item> elements and parse them."""

# Step 3: New module: src/foundry/items.py

class ItemManager:
    """Manages FoundryVTT Item creation."""

    def search_all_compendiums(self, name: str) -> Optional[str]:
        """Search all user compendiums for item by name. Returns UUID or None."""

    def create_item(self, magic_item: MagicItem) -> str:
        """Create Item entity from magic item data. Returns UUID."""
        item_data = {
            "name": magic_item.name,
            "type": magic_item.type,
            "system": {
                "rarity": magic_item.rarity,
                "attunement": magic_item.attunement,
                "description": {"value": magic_item.description},
                # ... map all fields to D&D 5e item schema
            }
        }
        return self.client.create_item(item_data)

# Step 4: Journal linking in src/foundry/xml_to_journal_html.py

def replace_item_mentions_with_links(html: str, item_refs: Dict[str, str]) -> str:
    """
    Find item mentions in journal text and replace with @UUID links.

    Example:
    Input: "<p>You find a <em>+1 longsword</em></p>"
    Output: "<p>You find a @UUID[Compendium.dnd5e.items.xyz]{+1 longsword}</p>"
    """

# Step 5: Integration in scripts/full_pipeline.py

def process_items(run_dir: str):
    """Main item processing workflow."""

    # 1. Extract and parse magic items
    items = extract_magic_items_from_xml(f"{run_dir}/documents/*.xml")

    # 2. Process items (create or lookup)
    item_refs = {}
    for item in items:
        existing_uuid = item_mgr.search_all_compendiums(item.name)
        if existing_uuid:
            item_refs[item.name] = existing_uuid
        else:
            new_uuid = item_mgr.create_item(item)
            item_refs[item.name] = new_uuid

    # 3. Update journal HTML with item links
    for journal_file in journals:
        html = replace_item_mentions_with_links(html, item_refs)
```

**Workflow Integration:**
```
pdf_to_xml.py → [generates XML (structure only, no item tags)]
    ↓
extract_items.py → [Gemini identifies magic items from XML]
    ↓
parse_items.py → [Gemini parses into structured MagicItem objects]
    ↓
items.py (ItemManager) → [creates Items or links to compendium]
    ↓
xml_to_journal_html.py → [replaces item mentions with @UUID links]
    ↓
upload_to_foundry.py → [uploads items + journals]
```

**Configuration (.env):**
```
ITEM_IMPORT_MODE=compendium  # or "world"
ITEM_COMPENDIUM_NAME=module-magic-items
PARSE_ITEMS=true  # parse into structured data
LINK_ITEMS_IN_JOURNALS=true  # auto-replace mentions with @UUID
TAG_MUNDANE_ITEMS=false  # only tag magic items by default
```

---

### 4. [Feature Name]

**Status:** 💭 Conceptual

**Description:**
[What the feature does]

**Motivation:**
[Why we want this]

**Open Questions:**
- [Question 1]

---

## Complete Pipeline Architecture

This shows how all features integrate into a cohesive workflow:

### Phase 1: Initial XML Generation
```
pdf_to_xml.py
├─ Input: PDF pages
├─ Focus: Document structure + stat blocks ONLY
└─ Output: XML with semantic structure + <stat_block> tags
```

**Gemini Prompt Focus:**
- Extract document hierarchy (sections, headings, paragraphs)
- Preserve formatting (bold, italic, lists, tables)
- **Tag stat blocks with `<stat_block name="...">raw text</stat_block>`**

### Phase 2: Post-Processing (Parallel Execution)

All post-processing steps analyze the generated XML independently:

```
Generated XML
    ├─→ parse_stat_blocks.py (parse tagged stat blocks)
    ├─→ extract_scenes.py (identify location descriptions)
    ├─→ extract_npcs.py (identify named characters)
    └─→ extract_items.py (identify magic items)
```

### Phase 3: Entity Creation

```
FoundryVTT Integration
    ├─→ actors.py: Create Actors (creatures + NPCs)
    ├─→ items.py: Create Items (magic items)
    ├─→ generate_scene_art.py: Generate scene images
    └─→ journals.py: Create journal pages with @UUID links
```

### Phase 4: Upload

```
upload_to_foundry.py
    ├─ Upload Actors to compendium
    ├─ Upload Items to compendium
    ├─ Upload scene images
    └─ Upload journals with embedded links
```

### Key Architectural Decisions

**Why only stat blocks are tagged initially:**
- Stat blocks are visually distinct and unambiguous in PDFs
- They're foundational - other features reference them
- Tagging them doesn't risk confusing the structure extraction prompt

**Why everything else is post-processing:**
- Context-dependent identification (scenes, NPCs, items)
- Each feature gets a focused, specialized Gemini prompt
- Easier to debug, iterate, and enable/disable features
- Can run post-processors in parallel for speed

---

## Status Legend

- 💭 **Conceptual** - Initial idea, needs discussion
- 📋 **Defined** - Requirements clear, ready for design
- 🎨 **Design Phase** - Actively designing solution
- ✅ **Ready to Implement** - Design approved, implementation can begin
- 🚧 **In Progress** - Currently being implemented
- ✔️ **Completed** - Shipped

---

## Discussion Notes

### [Date] - [Topic]
[Notes from discussions about specific features]


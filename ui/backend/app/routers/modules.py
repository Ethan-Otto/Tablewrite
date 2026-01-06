"""Module processing endpoints.

Orchestrates the full PDF-to-FoundryVTT pipeline for D&D modules.
"""

import asyncio
import logging
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

# Add src to path for imports
_src_path = str(Path(__file__).parent.parent.parent.parent.parent / "src")
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)

from config import PROJECT_ROOT
from pdf_processing.pdf_to_xml import main as pdf_to_xml_main, configure_gemini
from actor_pipeline.process_actors import process_actors_for_run
from pdf_processing.image_asset_processing.extract_map_assets import extract_maps_from_pdf, save_metadata
from foundry.upload_journal_to_foundry import upload_run_to_foundry
from scenes.orchestrate import create_scene_from_map

from app.websocket.push import get_or_create_folder, broadcast_progress_sync


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/modules", tags=["modules"])


def _split_pdf_to_sections(pdf_path: Path, output_dir: Path) -> Path:
    """
    Split the uploaded PDF into sections in the output directory.

    For now, we just copy the PDF as a single "section" since the original
    split_pdf.py is hardcoded for Lost Mine of Phandelver page boundaries.
    In the future, this could use AI to detect chapter boundaries.

    Args:
        pdf_path: Path to the source PDF
        output_dir: Directory to save the sections

    Returns:
        Path to the sections directory
    """
    sections_dir = output_dir / "pdf_sections"
    sections_dir.mkdir(parents=True, exist_ok=True)

    # For now, just copy the whole PDF as section 01
    # A more sophisticated approach would detect chapter boundaries
    pdf_name = pdf_path.stem
    section_path = sections_dir / f"01_{pdf_name}.pdf"
    shutil.copy(pdf_path, section_path)

    logger.info(f"Created section: {section_path}")
    return sections_dir


def _run_scene_artwork_generation(run_dir: Path) -> Dict[str, Any]:
    """
    Generate scene artwork from chapter XML files.

    Args:
        run_dir: Run directory containing documents/ folder

    Returns:
        Dict with generation statistics
    """
    # Import here to avoid circular dependencies at module load time
    scripts_dir = str(PROJECT_ROOT / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    from generate_scene_art import process_chapter

    output_dir = run_dir / "scene_artwork"
    output_dir.mkdir(parents=True, exist_ok=True)

    xml_files = list((run_dir / "documents").glob("*.xml"))

    if not xml_files:
        logger.warning("No XML files found for scene artwork generation")
        return {"scenes_found": 0, "images_generated": 0}

    total_scenes = 0
    total_images = 0

    for xml_file in xml_files:
        try:
            stats = process_chapter(xml_file, output_dir, style_prompt=None)
            total_scenes += stats.get("scenes_found", 0)
            total_images += stats.get("images_generated", 0)
        except Exception as e:
            logger.error(f"Failed to process {xml_file.name} for scene artwork: {e}")
            # Continue with other files

    return {
        "scenes_found": total_scenes,
        "images_generated": total_images,
        "output_dir": str(output_dir)
    }


async def create_folders_for_module(module_name: str) -> Dict[str, str]:
    """
    Create folder structure for module assets.

    Creates nested folder structure:
      /Tablewrite/<module_name>/
        ├── Actors
        ├── Scenes
        └── Journals

    Args:
        module_name: Name for the module subfolder

    Returns:
        Dict mapping document type to folder ID (the module subfolder for each type)

    Raises:
        RuntimeError: If folder creation fails (Foundry not connected or other error)
    """
    folders = {}

    for doc_type, key in [("Actor", "actors"), ("Scene", "scenes"), ("JournalEntry", "journals")]:
        # First create/get the Tablewrite root folder
        root_result = await get_or_create_folder("Tablewrite", doc_type)
        if not root_result.success or not root_result.folder_id:
            raise RuntimeError(f"Failed to create Tablewrite folder for {doc_type}: {root_result.error}")

        # Then create/get the module subfolder under Tablewrite
        module_result = await get_or_create_folder(
            module_name,
            doc_type,
            parent=root_result.folder_id
        )
        if not module_result.success or not module_result.folder_id:
            raise RuntimeError(f"Failed to create {doc_type} subfolder: {module_result.error}")

        folders[key] = module_result.folder_id
        logger.info(f"Created/found {doc_type} folder: Tablewrite/{module_name} -> {module_result.folder_id}")

    return folders


def process_module_sync(
    pdf_path: Path,
    *,
    module_name: str,
    extract_journal: bool = True,
    extract_actors: bool = True,
    extract_battle_maps: bool = True,
    generate_scene_artwork: bool = True,
    folder_ids: Dict[str, str] = None,
) -> Dict[str, Any]:
    """
    Process a D&D module PDF and create FoundryVTT content.

    Orchestrates the full pipeline:
    1. Split PDF into chapters
    2. Convert chapters to XML using Gemini
    3. Extract actors if enabled
    4. Extract battle maps if enabled
    5. Generate scene artwork if enabled
    6. Upload journal to FoundryVTT if enabled

    Args:
        pdf_path: Path to the uploaded PDF file
        module_name: Name for the module in FoundryVTT
        extract_journal: Whether to extract journal content
        extract_actors: Whether to extract actors/NPCs
        extract_battle_maps: Whether to extract battle maps
        generate_scene_artwork: Whether to generate scene artwork
        folder_ids: Dict mapping document type ("actors", "journals", "scenes") to folder IDs

    Returns:
        Dict with success status, folders created, and resources created
    """
    folder_ids = folder_ids or {}
    logger.info(f"Processing module '{module_name}' from {pdf_path}")
    logger.info(f"Options: journal={extract_journal}, actors={extract_actors}, "
                f"maps={extract_battle_maps}, artwork={generate_scene_artwork}")

    result = {
        "success": True,
        "name": module_name,
        "run_dir": None,
        "folders": {},
        # Flat structure for frontend compatibility
        "journal_uuid": None,
        "journal_name": None,
        "actors": [],  # List of {uuid, name}
        "scenes": [],  # List of {uuid, name}
        # Legacy nested structure for backwards compatibility
        "created": {
            "journal": None,
            "actors": [],
            "scenes": [],
            "artwork_journal": None
        }
    }

    # Create timestamped run directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    runs_dir = PROJECT_ROOT / "output" / "runs"
    run_dir = runs_dir / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)
    result["run_dir"] = str(run_dir)

    logger.info(f"Created run directory: {run_dir}")

    try:
        # Step 1: Split PDF into sections
        broadcast_progress_sync("splitting_pdf", "Splitting PDF into sections...", 5, module_name)
        logger.info("Step 1: Splitting PDF into sections...")
        sections_dir = _split_pdf_to_sections(pdf_path, run_dir)
        logger.info(f"PDF sections saved to: {sections_dir}")

        # Step 2: Convert sections to XML using Gemini
        broadcast_progress_sync("extracting_text", "Converting PDF to structured content...", 15, module_name)
        logger.info("Step 2: Converting PDF sections to XML...")
        configure_gemini()  # Initialize the Gemini API

        # The pdf_to_xml main function writes to output/runs/<timestamp>/documents/
        # We need to pass the sections dir and the runs base dir
        documents_dir = run_dir / "documents"
        documents_dir.mkdir(parents=True, exist_ok=True)
        logs_dir = run_dir / "intermediate_logs"
        logs_dir.mkdir(parents=True, exist_ok=True)

        # Process each section PDF
        from pdf_processing.pdf_to_xml import process_chapter

        section_files = sorted(sections_dir.glob("*.pdf"))
        for section_pdf in section_files:
            section_name = section_pdf.stem
            output_xml_path = documents_dir / f"{section_name}.xml"
            try:
                process_chapter(str(section_pdf), str(output_xml_path), str(logs_dir))
                logger.info(f"Converted {section_pdf.name} to XML")
            except Exception as e:
                logger.error(f"Failed to convert {section_pdf.name}: {e}")
                result["error"] = {"stage": "pdf_to_xml", "message": str(e)}
                result["success"] = False
                return result

        logger.info(f"XML documents saved to: {documents_dir}")
        broadcast_progress_sync("processing_journal", "Processing journal content...", 35, module_name)

    except Exception as e:
        logger.error(f"Failed during PDF processing: {e}")
        result["error"] = {"stage": "pdf_processing", "message": str(e)}
        result["success"] = False
        return result

    # Step 3: Extract actors if enabled
    if extract_actors:
        broadcast_progress_sync("extracting_actors", "Extracting actors and NPCs...", 45, module_name)
        logger.info("Step 3: Extracting actors...")
        try:
            # TODO: Make target configurable (currently hardcoded to "local", also supports "forge")
            actor_stats = process_actors_for_run(
                str(run_dir),
                target="local",
                folder_id=folder_ids.get("actors")
            )
            # Capture created actor UUIDs for frontend
            created_actors = actor_stats.get("created_actors", [])
            result["actors"] = created_actors
            result["created"]["actors"] = [a["uuid"] for a in created_actors]
            logger.info(f"Actors processed: {actor_stats.get('stat_blocks_created', 0)} stat blocks, "
                       f"{actor_stats.get('npcs_created', 0)} NPCs created")
        except Exception as e:
            logger.error(f"Failed to extract actors: {e}")
            result["error"] = {"stage": "extract_actors", "message": str(e)}
            result["success"] = False
            return result
    else:
        logger.info("Step 3: Skipping actor extraction (disabled)")

    # Step 4: Extract battle maps if enabled
    if extract_battle_maps:
        broadcast_progress_sync("extracting_maps", "Detecting and extracting battle maps...", 55, module_name)
        logger.info("Step 4: Extracting battle maps...")
        try:
            map_output_dir = run_dir / "map_assets"
            map_output_dir.mkdir(parents=True, exist_ok=True)

            # Run the async extraction in a new event loop
            maps = asyncio.run(extract_maps_from_pdf(
                str(pdf_path),
                str(map_output_dir),
                chapter_name=module_name
            ))

            if maps:
                save_metadata(maps, str(map_output_dir))
                logger.info(f"Extracted {len(maps)} map(s)")

                # Create scenes from extracted maps
                broadcast_progress_sync("creating_scenes", f"Creating {len(maps)} scene(s) with walls...", 60, module_name)
                logger.info(f"Step 4b: Creating scenes from {len(maps)} extracted map(s)...")

                scenes_folder_id = folder_ids.get("scenes")
                created_scenes = []

                for i, map_meta in enumerate(maps):
                    map_filename = f"page_{map_meta.page_num:03d}_{map_meta.name.lower().replace(' ', '_')}.png"
                    map_path = map_output_dir / map_filename

                    if map_path.exists():
                        try:
                            broadcast_progress_sync(
                                "creating_scenes",
                                f"Creating scene {i+1}/{len(maps)}: {map_meta.name}...",
                                60 + (i * 5 // len(maps)),
                                module_name
                            )

                            scene_result = asyncio.run(create_scene_from_map(
                                image_path=map_path,
                                name=map_meta.name,
                                folder=scenes_folder_id
                            ))

                            created_scenes.append({
                                "uuid": scene_result.uuid,
                                "name": scene_result.name,
                                "wall_count": scene_result.wall_count,
                                "grid_size": scene_result.grid_size
                            })
                            logger.info(f"Created scene: {scene_result.name} ({scene_result.uuid}) with {scene_result.wall_count} walls")

                        except Exception as e:
                            logger.warning(f"Failed to create scene from {map_path.name}: {e}")
                    else:
                        logger.warning(f"Map file not found: {map_path}")

                result["created"]["scenes"] = [s["uuid"] for s in created_scenes]
                logger.info(f"Created {len(created_scenes)} scene(s)")
            else:
                logger.info("No maps found in PDF")

        except Exception as e:
            logger.error(f"Failed to extract battle maps: {e}")
            result["error"] = {"stage": "extract_battle_maps", "message": str(e)}
            result["success"] = False
            return result
    else:
        logger.info("Step 4: Skipping battle map extraction (disabled)")

    # Step 5: Generate scene artwork if enabled (non-fatal)
    if generate_scene_artwork:
        broadcast_progress_sync("generating_artwork", "Generating scene artwork...", 70, module_name)
        logger.info("Step 5: Generating scene artwork...")
        try:
            artwork_stats = _run_scene_artwork_generation(run_dir)
            logger.info(f"Scene artwork: {artwork_stats.get('images_generated', 0)} images generated")
        except Exception as e:
            # Scene artwork is non-fatal - log and continue
            logger.warning(f"Scene artwork generation failed (non-fatal): {e}")
    else:
        logger.info("Step 5: Skipping scene artwork generation (disabled)")

    # Step 6: Upload journal if enabled
    if extract_journal:
        broadcast_progress_sync("uploading_to_foundry", "Uploading content to FoundryVTT...", 85, module_name)
        logger.info("Step 6: Uploading journal to FoundryVTT...")
        try:
            # TODO: Make target configurable (currently hardcoded to "local", also supports "forge")
            upload_result = upload_run_to_foundry(
                str(run_dir),
                target="local",
                journal_name=module_name,
                folder_id=folder_ids.get("journals")
            )

            if upload_result.get("journal_uuid"):
                result["journal_uuid"] = upload_result["journal_uuid"]
                result["journal_name"] = module_name
                result["created"]["journal"] = upload_result["journal_uuid"]
                logger.info(f"Journal uploaded: {upload_result['journal_uuid']}")
            else:
                logger.warning("Journal upload completed but no UUID returned")

            if upload_result.get("errors"):
                logger.warning(f"Upload had errors: {upload_result['errors']}")

        except Exception as e:
            logger.error(f"Failed to upload journal: {e}")
            result["error"] = {"stage": "upload_journal", "message": str(e)}
            result["success"] = False
            return result
    else:
        logger.info("Step 6: Skipping journal upload (disabled)")

    broadcast_progress_sync("complete", "Module processing complete!", 100, module_name)
    logger.info("Module processing complete!")
    return result


@router.post("/process")
async def process_module(
    file: UploadFile = File(...),
    module_name: str = Form(...),
    extract_journal: bool = Form(True),
    extract_actors: bool = Form(True),
    extract_battle_maps: bool = Form(True),
    generate_scene_artwork: bool = Form(True),
):
    """
    Process a D&D module PDF and create FoundryVTT content.

    Accepts a PDF file and extraction options, runs the processing pipeline
    in a background thread, and returns the created resources.

    Args:
        file: PDF file to process
        module_name: Name for the module in FoundryVTT
        extract_journal: Extract journal content (default: True)
        extract_actors: Extract actors/NPCs (default: True)
        extract_battle_maps: Extract battle maps (default: True)
        generate_scene_artwork: Generate scene artwork (default: True)

    Returns:
        {
            "success": True,
            "folders": {"journal": "uuid", "actors": "uuid", ...},
            "created": {
                "journal": "JournalEntry.uuid" or None,
                "actors": ["Actor.uuid", ...],
                "scenes": ["Scene.uuid", ...],
                "artwork_journal": "JournalEntry.uuid" or None
            }
        }

    Raises:
        HTTPException 500: If processing fails
    """
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    # Save uploaded file to temp location
    temp_dir = Path(tempfile.mkdtemp())
    temp_file = temp_dir / file.filename

    try:
        content = await file.read()
        with open(temp_file, "wb") as f:
            f.write(content)

        logger.info(f"Saved uploaded PDF to {temp_file}")

        # Create folder structure first (async, before entering thread pool)
        folder_ids = await create_folders_for_module(module_name)
        logger.info(f"Created folders: {folder_ids}")

        # Run pipeline in thread pool (blocking operations)
        result = await asyncio.to_thread(
            process_module_sync,
            pdf_path=temp_file,
            module_name=module_name,
            extract_journal=extract_journal,
            extract_actors=extract_actors,
            extract_battle_maps=extract_battle_maps,
            generate_scene_artwork=generate_scene_artwork,
            folder_ids=folder_ids,
        )

        # Include folder IDs in result
        result["folders"] = folder_ids

        return result

    except Exception as e:
        logger.exception(f"Failed to process module: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        # Cleanup temp file
        shutil.rmtree(temp_dir, ignore_errors=True)

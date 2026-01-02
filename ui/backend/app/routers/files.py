"""File serving and upload router."""

import base64
import re

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse

from app.config import settings
from app.websocket.push import upload_file


router = APIRouter(prefix="/api", tags=["files"])


# Security constants
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

# Allowed destinations (whitelist approach)
ALLOWED_DESTINATIONS = {
    "uploaded-maps",
    "uploaded-maps/tests",
    "tokens",
    "tiles",
    "scenes",
    "assets",
}


def sanitize_filename(filename: str | None) -> str:
    """
    Remove unsafe characters from filename.

    Args:
        filename: Original filename (may be None)

    Returns:
        Sanitized filename safe for filesystem operations
    """
    if not filename:
        return "unnamed"
    # Keep only alphanumeric, dots, hyphens, underscores
    safe = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
    # Remove leading dots (hidden files) BEFORE replacing ..
    safe = safe.lstrip('.')
    # Remove path traversal sequences (.. becomes __)
    safe = safe.replace('..', '__')
    # Remove any remaining leading dots/underscores from the replacement
    safe = safe.lstrip('._')
    # Limit length
    return safe[:255] if safe else "unnamed"


def validate_destination(destination: str) -> str:
    """
    Validate destination is a safe, allowed path.

    Args:
        destination: Destination subdirectory path

    Returns:
        Validated destination

    Raises:
        HTTPException: If destination is invalid or not allowed
    """
    # Normalize and check for path traversal
    if '..' in destination or destination.startswith('/') or destination.startswith('\\'):
        raise HTTPException(status_code=400, detail="Invalid destination path: path traversal not allowed")

    # Check against whitelist
    if destination not in ALLOWED_DESTINATIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid destination: must be one of {sorted(ALLOWED_DESTINATIONS)}"
        )

    return destination


@router.get("/images/{filename}")
async def serve_image(filename: str):
    """
    Serve generated images from chat_images directory.

    Args:
        filename: Image filename

    Returns:
        Image file

    Raises:
        HTTPException: If file not found or invalid filename
    """
    # Security: validate filename (no path traversal)
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    # Only serve .png files
    if not filename.endswith(".png"):
        raise HTTPException(status_code=400, detail="Only PNG files supported")

    file_path = settings.IMAGE_OUTPUT_DIR / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")

    return FileResponse(file_path, media_type="image/png")


@router.post("/foundry/files/upload")
async def upload_file_endpoint(
    file: UploadFile = File(...),
    destination: str = Form("uploaded-maps")
):
    """
    Upload a file to FoundryVTT world folder.

    The file is sent to the connected Foundry client via WebSocket,
    which saves it to: worlds/<current-world>/<destination>/<filename>

    Args:
        file: The file to upload
        destination: Subdirectory in world folder (default: "uploaded-maps")

    Returns:
        {"success": true, "path": "worlds/.../<filename>"}

    Raises:
        HTTPException 400: Invalid destination or filename
        HTTPException 413: File too large (>50MB)
        HTTPException 503: Foundry not connected
    """
    # 1. Validate destination (whitelist check, path traversal)
    validated_destination = validate_destination(destination)

    # 2. Check file size BEFORE reading entire content
    # First check Content-Length header if available
    if file.size is not None and file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large: {file.size} bytes exceeds {MAX_FILE_SIZE} byte limit"
        )

    # Read file content
    content = await file.read()

    # Double-check actual size (in case header was spoofed or unavailable)
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large: {len(content)} bytes exceeds {MAX_FILE_SIZE} byte limit"
        )

    # 3. Sanitize filename
    safe_filename = sanitize_filename(file.filename)

    # Encode content for WebSocket transmission
    content_b64 = base64.b64encode(content).decode('utf-8')

    result = await upload_file(
        filename=safe_filename,
        content=content_b64,
        destination=validated_destination
    )

    if not result.success:
        # Check for connection-related errors and return 503
        if result.error and ("not connected" in result.error.lower() or "timeout" in result.error.lower()):
            raise HTTPException(status_code=503, detail=result.error)
        raise HTTPException(status_code=500, detail=result.error)

    return {
        "success": True,
        "path": result.path
    }

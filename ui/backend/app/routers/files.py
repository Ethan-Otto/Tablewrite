"""File serving and upload router."""

import base64

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse

from app.config import settings
from app.websocket.push import upload_file


router = APIRouter(prefix="/api", tags=["files"])


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
    """
    content = await file.read()
    content_b64 = base64.b64encode(content).decode('utf-8')

    result = await upload_file(
        filename=file.filename,
        content=content_b64,
        destination=destination
    )

    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    return {
        "success": True,
        "path": result.path
    }

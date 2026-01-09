"""Tools router for direct tool execution."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, Optional, List
from app.tools import registry

router = APIRouter(prefix="/api/tools", tags=["tools"])


class ToolRequest(BaseModel):
    """Generic tool request model."""
    # Common parameters
    entity_type: Optional[str] = None
    search_query: Optional[str] = None
    uuid: Optional[str] = None
    folder_name: Optional[str] = None
    actor_uuid: Optional[str] = None
    item_names: Optional[List[str]] = None
    confirm_bulk: Optional[bool] = False
    # Generic extra parameters
    extra: Optional[Dict[str, Any]] = None


class ToolResponse(BaseModel):
    """Generic tool response model."""
    type: str
    message: str
    data: Optional[Dict[str, Any]] = None


@router.post("/delete_assets", response_model=ToolResponse)
async def execute_delete_assets(request: ToolRequest) -> ToolResponse:
    """
    Execute the delete_assets tool directly.

    This endpoint is primarily for integration testing.
    """
    try:
        # Build kwargs from request
        kwargs = {}
        if request.entity_type:
            kwargs["entity_type"] = request.entity_type
        if request.search_query:
            kwargs["search_query"] = request.search_query
        if request.uuid:
            kwargs["uuid"] = request.uuid
        if request.folder_name:
            kwargs["folder_name"] = request.folder_name
        if request.actor_uuid:
            kwargs["actor_uuid"] = request.actor_uuid
        if request.item_names:
            kwargs["item_names"] = request.item_names
        if request.confirm_bulk is not None:
            kwargs["confirm_bulk"] = request.confirm_bulk
        if request.extra:
            kwargs.update(request.extra)

        result = await registry.execute_tool("delete_assets", **kwargs)

        return ToolResponse(
            type=result.type,
            message=result.message,
            data=result.data
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

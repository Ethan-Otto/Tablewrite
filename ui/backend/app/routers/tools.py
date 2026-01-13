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


class JournalQueryRequest(BaseModel):
    """Request model for query_journal tool."""
    query: str
    query_type: str  # "question", "summary", "extraction"
    journal_name: Optional[str] = None
    folder: Optional[str] = None
    session_id: Optional[str] = None


class ActorQueryRequest(BaseModel):
    """Request model for query_actor tool."""
    actor_uuid: str
    query: str
    query_type: str  # "abilities", "combat", "general"


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
    # Validate required parameter
    if not request.entity_type:
        raise HTTPException(status_code=400, detail="entity_type is required")

    try:
        # Build kwargs from request
        kwargs = {"entity_type": request.entity_type}
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


@router.post("/query_journal", response_model=ToolResponse)
async def execute_query_journal(request: JournalQueryRequest) -> ToolResponse:
    """
    Execute the query_journal tool directly.

    This endpoint is primarily for integration testing and allows
    filtering by folder to target specific journals.
    """
    try:
        result = await registry.execute_tool(
            "query_journal",
            query=request.query,
            query_type=request.query_type,
            journal_name=request.journal_name,
            folder=request.folder,
            session_id=request.session_id
        )

        return ToolResponse(
            type=result.type,
            message=result.message,
            data=result.data
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query_actor", response_model=ToolResponse)
async def execute_query_actor(request: ActorQueryRequest) -> ToolResponse:
    """
    Execute the query_actor tool directly.

    This endpoint is used when the AI calls the query_actor tool
    to answer questions about an @mentioned actor.
    """
    try:
        result = await registry.execute_tool(
            "query_actor",
            actor_uuid=request.actor_uuid,
            query=request.query,
            query_type=request.query_type
        )

        return ToolResponse(
            type=result.type,
            message=result.message,
            data=result.data
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

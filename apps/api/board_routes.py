"""API routes for the Kanban Board UI.

Provides matrix view and drag-and-drop mutation endpoints for the kanban board feature.
Reuses ProjectDashboardSession data model and storage.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException

from apps.api.dashboard_routes import _get_session

router = APIRouter(prefix="/api/board", tags=["kanban-board"])


@router.get("/{session_id}/snapshot")
def board_snapshot(session_id: str):
    """Fetch current board state (same as dashboard snapshot, suitable for matrix view)."""
    session = _get_session(session_id)
    return session.snapshot()


@router.put("/{session_id}/tasks/{task_key}/status")
async def update_task_status(session_id: str, task_key: str, payload: dict):
    """Update a task's status (supports drag-and-drop mutations).

    Payload: {new_status: "NOT_STARTED" | "IN_PROGRESS" | "AWAITING_REVIEW" | "COMPLETED"}
    """
    session = _get_session(session_id)
    new_status = payload.get("new_status")
    if not new_status:
        raise HTTPException(status_code=400, detail="missing new_status in payload")

    # Find the lane and work product
    for lane in session.lanes.values():
        if task_key in lane.work_products:
            resolved = await session.update_task_status(lane.key, task_key, new_status)
            if not resolved:
                raise HTTPException(status_code=409, detail="failed to update task status")
            return {"task_key": task_key, "new_status": new_status, "success": True}

    raise HTTPException(status_code=404, detail=f"task {task_key} not found")


@router.get("/{session_id}/tasks/{task_key}/comments")
def fetch_task_comments(session_id: str, task_key: str):
    """Fetch all comments for a task."""
    session = _get_session(session_id)
    comments = session.get_comments(task_key)
    return {"task_key": task_key, "comments": comments}


@router.post("/{session_id}/tasks/{task_key}/comments")
def add_task_comment(session_id: str, task_key: str, payload: dict):
    """Add a comment to a task.

    Payload: {author: str, author_type: "agent" | "human" | "system", body: str}
    """
    session = _get_session(session_id)
    author = payload.get("author", "anonymous")
    author_type = payload.get("author_type", "human")
    body = payload.get("body", "")

    if not body:
        raise HTTPException(status_code=400, detail="comment body cannot be empty")

    comment = session.add_comment(task_key, author, author_type, body)
    return {"task_key": task_key, "comment": comment}


@router.patch("/{session_id}/tasks/{task_key}/checklist/{item_id}")
async def update_checklist_item(session_id: str, task_key: str, item_id: str, payload: dict):
    """Update checklist item completion status.

    Payload: {completed: bool}
    """
    session = _get_session(session_id)
    completed = bool(payload.get("completed", False))

    # Find the lane and work product
    for lane in session.lanes.values():
        if task_key in lane.work_products:
            resolved = await session.update_checklist_item(lane.key, task_key, item_id, completed)
            if not resolved:
                raise HTTPException(status_code=404, detail=f"checklist item {item_id} not found")
            return {"task_key": task_key, "item_id": item_id, "completed": completed, "success": True}

    raise HTTPException(status_code=404, detail=f"task {task_key} not found")

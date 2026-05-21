"""Tags Router"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.core.security import get_current_user

router = APIRouter()
tags_store = {}

class TagCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    color: Optional[str] = Field(default="#C5A059")
    description: Optional[str] = None

class TagResponse(BaseModel):
    id: str
    name: str
    color: str
    description: Optional[str]
    created_at: str
    user_id: str

@router.post("/api/v3/tags")
async def create_tag(data: TagCreate, uid: str = Depends(get_current_user)):
    import uuid
    tag_id = str(uuid.uuid4())
    tag = {"id": tag_id, "name": data.name, "color": data.color or "#C5A059", "description": data.description, "created_at": datetime.utcnow().isoformat(), "user_id": uid}
    tags_store[tag_id] = tag
    return TagResponse(**tag)

@router.get("/api/v3/tags")
async def list_tags(uid: str = Depends(get_current_user)):
    user_tags = [t for t in tags_store.values() if t["user_id"] == uid]
    return [TagResponse(**t) for t in user_tags]

@router.put("/api/v3/tags/{tag_id}")
async def update_tag(tag_id: str, data: TagCreate, uid: str = Depends(get_current_user)):
    if tag_id not in tags_store:
        raise HTTPException(status_code=404, detail="Not found")
    tag = tags_store[tag_id]
    if tag["user_id"] != uid:
        raise HTTPException(status_code=403, detail="Forbidden")
    tag.update({"name": data.name, "color": data.color or "#C5A059", "description": data.description})
    return TagResponse(**tag)

@router.delete("/api/v3/tags/{tag_id}")
async def delete_tag(tag_id: str, uid: str = Depends(get_current_user)):
    if tag_id not in tags_store:
        raise HTTPException(status_code=404, detail="Not found")
    tag = tags_store[tag_id]
    if tag["user_id"] != uid:
        raise HTTPException(status_code=403, detail="Forbidden")
    del tags_store[tag_id]
    return {"ok": True}

@router.post("/api/v3/tags/{tag_id}/assign")
async def assign_tag(tag_id: str, ruc: str, uid: str = Depends(get_current_user)):
    if tag_id not in tags_store:
        raise HTTPException(status_code=404, detail="Not found")
    return {"ok": True, "ruc": ruc, "tag_id": tag_id}

@router.get("/api/v3/tags/search")
async def search_tags(q: str, uid: str = Depends(get_current_user)):
    user_tags = [t for t in tags_store.values() if t["user_id"] == uid]
    results = [t for t in user_tags if q.lower() in t["name"].lower()]
    return [TagResponse(**t) for t in results]

"""
CRUD-эндпоинты для категорий.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException
from sqlalchemy.orm import Session

from src.database.session import get_db
from src.database import crud as db_crud

router = APIRouter(prefix="/api/categories", tags=["categories"])


def _category_to_dict(cat) -> dict:
    return {
        "id": cat.id,
        "name": cat.name,
        "description": cat.description,
        "parent_id": cat.parent_id,
        "created_at": cat.created_at.isoformat() if cat.created_at else None,
    }


@router.post("", response_model=dict)
async def api_create_category(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    parent_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
):
    try:
        cat = db_crud.create_category(db, name=name, description=description, parent_id=parent_id)
        return _category_to_dict(cat)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("", response_model=dict)
async def api_list_categories(parent_id: Optional[int] = None, db: Session = Depends(get_db)):
    cats = db_crud.list_categories(db, parent_id=parent_id)
    return {"categories": [_category_to_dict(c) for c in cats]}


@router.get("/{category_id}", response_model=dict)
async def api_get_category(category_id: int, db: Session = Depends(get_db)):
    cat = db_crud.get_category(db, category_id)
    if cat is None:
        raise HTTPException(status_code=404, detail="Категория не найдена")
    return _category_to_dict(cat)


@router.put("/{category_id}", response_model=dict)
async def api_update_category(
    category_id: int,
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    parent_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
):
    try:
        cat = db_crud.update_category(db, category_id, name=name, description=description, parent_id=parent_id)
        if cat is None:
            raise HTTPException(status_code=404, detail="Категория не найдена")
        return _category_to_dict(cat)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.delete("/{category_id}", response_model=dict)
async def api_delete_category(category_id: int, db: Session = Depends(get_db)):
    ok = db_crud.delete_category(db, category_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Категория не найдена")
    return {"status": "deleted", "id": category_id}

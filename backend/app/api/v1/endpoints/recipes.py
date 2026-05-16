from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import uuid

from app.db.session import get_db
from app.core.deps import require_permission
from app.crud import recipe as crud
from app.models.recipe import RecipeStatus
from app.schemas.recipe import (
    RecipeCreate, RecipeUpdate, RecipeRead, RecipeDetailRead,
    RecipeItemCreate, RecipeItemUpdate, RecipeItemRead,
    ProcessParameterCreate, ProcessParameterUpdate, ProcessParameterRead,
    RecipeDuplicateRequest,
)

router = APIRouter()


def _assert_draft(recipe) -> None:
    if recipe.status != RecipeStatus.DRAFT:
        raise HTTPException(
            status_code=422,
            detail=f"Recipe is {recipe.status.value}. Only DRAFT recipes can be modified.",
        )


# ── Recipe Header ─────────────────────────────────────────────────────────────

@router.get("/", response_model=List[RecipeRead])
async def list_recipes(
    product_id: Optional[uuid.UUID] = None,
    status: Optional[RecipeStatus] = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("recipe", "view")),
):
    recipes = await crud.list_recipes(db, product_id=product_id, status=status, skip=skip, limit=limit)
    result = []
    for r in recipes:
        read = RecipeRead.model_validate(r)
        if r.product:
            read.product_name = r.product.name
            read.product_sku = r.product.sku
        result.append(read)
    return result


@router.post("/", response_model=RecipeRead, status_code=201)
async def create_recipe(
    data: RecipeCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("recipe", "create")),
):
    obj = await crud.create_recipe(db, data, current_user.id)
    await db.commit()
    await db.refresh(obj)
    return RecipeRead.model_validate(obj)


@router.get("/{recipe_id}", response_model=RecipeDetailRead)
async def get_recipe(
    recipe_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("recipe", "view")),
):
    obj = await crud.get_recipe(db, recipe_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Recipe not found")

    detail = RecipeDetailRead.model_validate(obj)
    if obj.product:
        detail.product_name = obj.product.name
        detail.product_sku = obj.product.sku

    detail.items = []
    for item in obj.items:
        item_read = RecipeItemRead.model_validate(item)
        if item.material:
            item_read.material_name = item.material.name
            item_read.material_code = item.material.code
        detail.items.append(item_read)

    return detail


@router.patch("/{recipe_id}", response_model=RecipeRead)
async def update_recipe(
    recipe_id: uuid.UUID,
    data: RecipeUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("recipe", "edit")),
):
    obj = await crud.get_recipe(db, recipe_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Recipe not found")
    _assert_draft(obj)
    obj = await crud.update_recipe(db, obj, data)
    await db.commit()
    await db.refresh(obj)
    return RecipeRead.model_validate(obj)


# ── Delete recipe header ──────────────────────────────────────────────────────

@router.delete("/{recipe_id}", status_code=204)
async def delete_recipe(
    recipe_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("recipe", "delete")),
):
    from fastapi import Response
    obj = await crud.get_recipe(db, recipe_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Recipe not found")
    _assert_draft(obj)
    await db.delete(obj)
    await db.commit()
    return Response(status_code=204)


# ── Approval workflow ─────────────────────────────────────────────────────────

@router.post("/{recipe_id}/approve", response_model=RecipeRead)
async def approve_recipe(
    recipe_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("recipe", "approve")),
):
    obj = await crud.get_recipe(db, recipe_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Recipe not found")
    if obj.status != RecipeStatus.DRAFT:
        raise HTTPException(status_code=422, detail="Only DRAFT recipes can be approved.")
    if not obj.items:
        raise HTTPException(status_code=422, detail="Cannot approve a recipe with no items.")
    obj = await crud.approve_recipe(db, obj, current_user.id)
    await db.commit()
    await db.refresh(obj)
    return RecipeRead.model_validate(obj)


@router.post("/{recipe_id}/obsolete", response_model=RecipeRead)
async def obsolete_recipe(
    recipe_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("recipe", "obsolete")),
):
    obj = await crud.get_recipe(db, recipe_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Recipe not found")
    if obj.status == RecipeStatus.OBSOLETE:
        raise HTTPException(status_code=422, detail="Recipe is already obsolete.")
    obj = await crud.obsolete_recipe(db, obj)
    await db.commit()
    await db.refresh(obj)
    return RecipeRead.model_validate(obj)


@router.post("/{recipe_id}/duplicate", response_model=RecipeRead, status_code=201)
async def duplicate_recipe(
    recipe_id: uuid.UUID,
    req: RecipeDuplicateRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("recipe", "create")),
):
    source = await crud.get_recipe(db, recipe_id)
    if not source:
        raise HTTPException(status_code=404, detail="Recipe not found")
    new_recipe = await crud.duplicate_recipe(
        db, source, req.new_version, req.new_name, current_user.id
    )
    await db.commit()
    await db.refresh(new_recipe)
    return RecipeRead.model_validate(new_recipe)


# ── Recipe Items ──────────────────────────────────────────────────────────────

@router.post("/{recipe_id}/items", response_model=RecipeItemRead, status_code=201)
async def add_recipe_item(
    recipe_id: uuid.UUID,
    data: RecipeItemCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("recipe", "edit")),
):
    recipe = await crud.get_recipe(db, recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    _assert_draft(recipe)
    obj = await crud.create_recipe_item(db, recipe_id, data)
    await db.commit()
    obj = await crud.get_recipe_item(db, obj.id)
    item_read = RecipeItemRead.model_validate(obj)
    if obj.material:
        item_read.material_name = obj.material.name
        item_read.material_code = obj.material.code
    return item_read


@router.patch("/{recipe_id}/items/{item_id}", response_model=RecipeItemRead)
async def update_recipe_item(
    recipe_id: uuid.UUID,
    item_id: uuid.UUID,
    data: RecipeItemUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("recipe", "edit")),
):
    recipe = await crud.get_recipe(db, recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    _assert_draft(recipe)
    item = await crud.get_recipe_item(db, item_id)
    if not item or item.recipe_id != recipe_id:
        raise HTTPException(status_code=404, detail="Recipe item not found")
    item = await crud.update_recipe_item(db, item, data)
    await db.commit()
    item = await crud.get_recipe_item(db, item.id)
    item_read = RecipeItemRead.model_validate(item)
    if item.material:
        item_read.material_name = item.material.name
        item_read.material_code = item.material.code
    return item_read


@router.delete("/{recipe_id}/items/{item_id}", status_code=204)
async def delete_recipe_item(
    recipe_id: uuid.UUID,
    item_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("recipe", "delete")),
):
    recipe = await crud.get_recipe(db, recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    _assert_draft(recipe)
    item = await crud.get_recipe_item(db, item_id)
    if not item or item.recipe_id != recipe_id:
        raise HTTPException(status_code=404, detail="Recipe item not found")
    await crud.delete_recipe_item(db, item)
    await db.commit()


# ── Process Parameters ────────────────────────────────────────────────────────

@router.post("/{recipe_id}/process-parameters", response_model=ProcessParameterRead, status_code=201)
async def add_process_parameter(
    recipe_id: uuid.UUID,
    data: ProcessParameterCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("recipe", "edit")),
):
    recipe = await crud.get_recipe(db, recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    _assert_draft(recipe)
    obj = await crud.create_process_parameter(db, recipe_id, data)
    await db.commit()
    await db.refresh(obj)
    return ProcessParameterRead.model_validate(obj)


@router.patch("/{recipe_id}/process-parameters/{param_id}", response_model=ProcessParameterRead)
async def update_process_parameter(
    recipe_id: uuid.UUID,
    param_id: uuid.UUID,
    data: ProcessParameterUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("recipe", "edit")),
):
    recipe = await crud.get_recipe(db, recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    _assert_draft(recipe)
    param = await crud.get_process_parameter(db, param_id)
    if not param or param.recipe_id != recipe_id:
        raise HTTPException(status_code=404, detail="Process parameter not found")
    param = await crud.update_process_parameter(db, param, data)
    await db.commit()
    await db.refresh(param)
    return ProcessParameterRead.model_validate(param)


@router.delete("/{recipe_id}/process-parameters/{param_id}", status_code=204)
async def delete_process_parameter(
    recipe_id: uuid.UUID,
    param_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("recipe", "delete")),
):
    recipe = await crud.get_recipe(db, recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    _assert_draft(recipe)
    param = await crud.get_process_parameter(db, param_id)
    if not param or param.recipe_id != recipe_id:
        raise HTTPException(status_code=404, detail="Process parameter not found")
    await crud.delete_process_parameter(db, param)
    await db.commit()

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import Optional, List
import uuid

from app.models.recipe import Recipe, RecipeItem, ProcessParameter, RecipeStatus
from app.models.master import Material
from app.schemas.recipe import (
    RecipeCreate, RecipeUpdate,
    RecipeItemCreate, RecipeItemUpdate,
    ProcessParameterCreate, ProcessParameterUpdate,
)


# ── Recipe ────────────────────────────────────────────────────────────────────

async def get_recipe(db: AsyncSession, recipe_id: uuid.UUID) -> Optional[Recipe]:
    result = await db.execute(
        select(Recipe)
        .where(Recipe.id == recipe_id)
        .options(
            selectinload(Recipe.items).selectinload(RecipeItem.material),
            selectinload(Recipe.process_parameters),
            selectinload(Recipe.product),
            selectinload(Recipe.creator),
            selectinload(Recipe.approver),
        )
    )
    return result.scalar_one_or_none()


async def list_recipes(
    db: AsyncSession,
    product_id: Optional[uuid.UUID] = None,
    status: Optional[RecipeStatus] = None,
    skip: int = 0,
    limit: int = 50,
) -> List[Recipe]:
    q = select(Recipe).options(selectinload(Recipe.product))
    if product_id:
        q = q.where(Recipe.product_id == product_id)
    if status:
        q = q.where(Recipe.status == status)
    q = q.order_by(Recipe.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(q)
    return list(result.scalars().all())


async def create_recipe(
    db: AsyncSession, data: RecipeCreate, user_id: uuid.UUID
) -> Recipe:
    obj = Recipe(**data.model_dump(), status=RecipeStatus.DRAFT, created_by=user_id)
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def update_recipe(
    db: AsyncSession, obj: Recipe, data: RecipeUpdate
) -> Recipe:
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    await db.flush()
    await db.refresh(obj)
    return obj


async def approve_recipe(
    db: AsyncSession, obj: Recipe, approver_id: uuid.UUID
) -> Recipe:
    obj.status = RecipeStatus.APPROVED
    obj.approved_by = approver_id
    await db.flush()
    await db.refresh(obj)
    return obj


async def obsolete_recipe(db: AsyncSession, obj: Recipe) -> Recipe:
    obj.status = RecipeStatus.OBSOLETE
    obj.is_active = False
    await db.flush()
    await db.refresh(obj)
    return obj


async def duplicate_recipe(
    db: AsyncSession,
    source: Recipe,
    new_version: str,
    new_name: Optional[str],
    user_id: uuid.UUID,
) -> Recipe:
    new_recipe = Recipe(
        product_id=source.product_id,
        version=new_version,
        name=new_name or f"{source.name} v{new_version}",
        description=source.description,
        status=RecipeStatus.DRAFT,
        is_active=True,
        valid_from=source.valid_from,
        valid_to=source.valid_to,
        created_by=user_id,
        approved_by=None,
    )
    db.add(new_recipe)
    await db.flush()

    # Copy items
    for item in source.items:
        new_item = RecipeItem(
            recipe_id=new_recipe.id,
            material_id=item.material_id,
            line_no=item.line_no,
            quantity=item.quantity,
            unit=item.unit,
            loss_percentage=item.loss_percentage,
            is_optional=item.is_optional,
            alternative_group=item.alternative_group,
            notes=item.notes,
        )
        db.add(new_item)

    # Copy process parameters
    for param in source.process_parameters:
        new_param = ProcessParameter(
            recipe_id=new_recipe.id,
            step_no=param.step_no,
            step_name=param.step_name,
            target_temperature=param.target_temperature,
            target_ph=param.target_ph,
            target_viscosity=param.target_viscosity,
            mixing_time_minutes=param.mixing_time_minutes,
            rpm=param.rpm,
            notes=param.notes,
        )
        db.add(new_param)

    await db.flush()
    await db.refresh(new_recipe)
    return new_recipe


# ── Recipe Items ──────────────────────────────────────────────────────────────

async def get_recipe_item(db: AsyncSession, item_id: uuid.UUID) -> Optional[RecipeItem]:
    result = await db.execute(
        select(RecipeItem)
        .where(RecipeItem.id == item_id)
        .options(selectinload(RecipeItem.material))
    )
    return result.scalar_one_or_none()


async def create_recipe_item(
    db: AsyncSession, recipe_id: uuid.UUID, data: RecipeItemCreate
) -> RecipeItem:
    obj = RecipeItem(recipe_id=recipe_id, **data.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def update_recipe_item(
    db: AsyncSession, obj: RecipeItem, data: RecipeItemUpdate
) -> RecipeItem:
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    await db.flush()
    await db.refresh(obj)
    return obj


async def delete_recipe_item(db: AsyncSession, obj: RecipeItem) -> None:
    await db.delete(obj)
    await db.flush()


# ── Process Parameters ────────────────────────────────────────────────────────

async def get_process_parameter(
    db: AsyncSession, param_id: uuid.UUID
) -> Optional[ProcessParameter]:
    result = await db.execute(
        select(ProcessParameter).where(ProcessParameter.id == param_id)
    )
    return result.scalar_one_or_none()


async def create_process_parameter(
    db: AsyncSession, recipe_id: uuid.UUID, data: ProcessParameterCreate
) -> ProcessParameter:
    obj = ProcessParameter(recipe_id=recipe_id, **data.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def update_process_parameter(
    db: AsyncSession, obj: ProcessParameter, data: ProcessParameterUpdate
) -> ProcessParameter:
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    await db.flush()
    await db.refresh(obj)
    return obj


async def delete_process_parameter(db: AsyncSession, obj: ProcessParameter) -> None:
    await db.delete(obj)
    await db.flush()

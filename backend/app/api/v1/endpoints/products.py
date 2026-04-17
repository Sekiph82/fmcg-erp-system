import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List
import uuid

from app.db.session import get_db
from app.core.deps import get_current_user, require_permission
from app.crud import master as crud
from app.schemas.master import ProductCreate, ProductUpdate, ProductRead
from fastapi import Response

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=List[ProductRead])
async def list_products(skip: int = 0, limit: int = 50, db: AsyncSession = Depends(get_db),
                        _=Depends(get_current_user)):
    return await crud.list_products(db, skip=skip, limit=limit)


@router.post("/", response_model=ProductRead, status_code=201)
async def create_product(data: ProductCreate, db: AsyncSession = Depends(get_db),
                         _=Depends(get_current_user)):
    obj = await crud.create_product(db, data)
    await db.commit()
    return obj


@router.get("/{product_id}", response_model=ProductRead)
async def get_product(product_id: uuid.UUID, db: AsyncSession = Depends(get_db),
                      _=Depends(get_current_user)):
    obj = await crud.get_product(db, product_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Product not found")
    return obj


@router.patch("/{product_id}", response_model=ProductRead)
async def update_product(product_id: uuid.UUID, data: ProductUpdate,
                         db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    obj = await crud.get_product(db, product_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Product not found")
    obj = await crud.update_product(db, obj, data)
    await db.commit()
    return obj


@router.patch("/{product_id}/archive", response_model=ProductRead)
async def archive_product(
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("products", "delete")),
):
    """Deactivate (archive) a product without deleting it."""
    obj = await crud.get_product(db, product_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Product not found")
    from app.schemas.master import ProductUpdate
    obj = await crud.update_product(db, obj, ProductUpdate(is_active=False))
    await db.commit()
    logger.info("Product %s archived by user %s", product_id, current_user.id)
    return obj


@router.delete("/{product_id}", status_code=204)
async def delete_product(
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("products", "delete")),
):
    """
    Delete a product. Blocked if any dependent records exist.
    Returns 409 with structured error listing all dependencies.
    """
    obj = await crud.get_product(db, product_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Product not found")

    # ── Check all FK dependencies before attempting delete ──────────────────────
    from app.models.inventory import Stock, Lot, StockMovement
    references = []

    stock_count = (await db.execute(
        select(func.count()).select_from(Stock).where(Stock.product_id == product_id)
    )).scalar_one()
    if stock_count:
        references.append({
            "module": "Inventory",
            "count": stock_count,
            "hint": "Issue, transfer, or write off all stock to bring quantity to zero first.",
        })

    lot_count = (await db.execute(
        select(func.count()).select_from(Lot).where(Lot.product_id == product_id)
    )).scalar_one()
    if lot_count:
        references.append({
            "module": "Lot / Batch Records",
            "count": lot_count,
            "hint": "Delete associated lot records first.",
        })

    movement_count = (await db.execute(
        select(func.count()).select_from(StockMovement).where(StockMovement.product_id == product_id)
    )).scalar_one()
    if movement_count:
        references.append({
            "module": "Stock Movements",
            "count": movement_count,
            "hint": "Delete or reverse all stock movements for this product first.",
        })

    # Check other modules that may reference this product
    _extra_refs = await _check_extra_product_refs(db, product_id)
    references.extend(_extra_refs)

    if references:
        logger.warning(
            "Product delete blocked: product_id=%s name=%s deps=%s user=%s",
            product_id, obj.name, references, current_user.id,
        )
        raise HTTPException(
            status_code=409,
            detail={
                "code": "PRODUCT_IN_USE",
                "message": "This product cannot be deleted because it is used in other records.",
                "details": {
                    "productId": str(product_id),
                    "productName": obj.name,
                    "references": references,
                },
            },
        )

    await crud.delete_product(db, obj)
    await db.commit()
    logger.info("Product %s deleted by user %s", product_id, current_user.id)
    return Response(status_code=204)


async def _check_extra_product_refs(db: AsyncSession, product_id: uuid.UUID) -> list:
    """Check additional modules for product references. Skips gracefully if models don't exist."""
    from sqlalchemy import inspect as sqlinspect
    refs = []

    extra_checks = [
        ("app.models.sales", "SalesOrderLine", "product_id", "Sales Order Lines",
         "Remove or reassign sales order lines referencing this product."),
        ("app.models.sales", "InvoiceLine", "product_id", "Invoice Lines",
         "Remove or reassign invoice lines referencing this product."),
        ("app.models.procurement", "PurchaseOrderLine", "product_id", "Purchase Order Lines",
         "Remove or reassign purchase order lines referencing this product."),
        ("app.models.production", "RecipeLine", "product_id", "Recipe Lines",
         "Remove recipe lines referencing this product."),
        ("app.models.production", "ProductionOutput", "product_id", "Production Output Records",
         "Delete production output records referencing this product."),
    ]

    for module_path, class_name, fk_field, label, hint in extra_checks:
        try:
            import importlib
            mod = importlib.import_module(module_path)
            model_cls = getattr(mod, class_name, None)
            if model_cls is None:
                continue
            fk_col = getattr(model_cls, fk_field, None)
            if fk_col is None:
                continue
            count = (await db.execute(
                select(func.count()).select_from(model_cls).where(fk_col == product_id)
            )).scalar_one()
            if count:
                refs.append({"module": label, "count": count, "hint": hint})
        except Exception:
            pass  # Module doesn't exist yet – skip silently

    return refs

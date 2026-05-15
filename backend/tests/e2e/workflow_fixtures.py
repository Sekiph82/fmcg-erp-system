from __future__ import annotations

from dataclasses import asdict, dataclass, field
from decimal import Decimal
from uuid import UUID, uuid5


E2E_NAMESPACE = UUID("3db6e629-1742-45af-b188-7c4f06fd3058")


def stable_uuid(name: str) -> str:
    """Return a stable UUID for deterministic E2E fixture records."""
    return str(uuid5(E2E_NAMESPACE, name))


@dataclass(frozen=True)
class ScopeGrant:
    scope_type: str
    scope_id: str
    can_view: bool = True
    can_create: bool = False
    can_edit: bool = False
    can_delete: bool = False
    can_approve: bool = False
    can_post: bool = False
    can_release: bool = False
    can_cancel: bool = False
    can_export: bool = False
    can_import: bool = False
    can_transfer: bool = False
    can_adjust: bool = False
    can_receive: bool = False
    can_dispatch: bool = False


@dataclass(frozen=True)
class E2EPersona:
    key: str
    username: str
    permissions: tuple[str, ...]
    scopes: tuple[ScopeGrant, ...] = field(default_factory=tuple)

    def to_payload(self) -> dict:
        data = asdict(self)
        data["permissions"] = list(self.permissions)
        data["scopes"] = [asdict(scope) for scope in self.scopes]
        return data


@dataclass(frozen=True)
class CoreWorkflowFixture:
    company_id: str
    branch_id: str
    warehouse_id: str
    secondary_warehouse_id: str
    product_id: str
    supplier_id: str
    customer_id: str
    department: str
    sales_region: str
    cost_center_id: str
    quantity: Decimal = Decimal("100.00")

    def to_payload(self) -> dict:
        data = asdict(self)
        data["quantity"] = str(self.quantity)
        return data


def core_workflow_fixture(site: str = "nairobi") -> CoreWorkflowFixture:
    """Build deterministic cross-module fixture ids for one factory/branch scenario."""
    prefix = f"e2e:{site}"
    return CoreWorkflowFixture(
        company_id=stable_uuid(f"{prefix}:company"),
        branch_id=stable_uuid(f"{prefix}:branch"),
        warehouse_id=stable_uuid(f"{prefix}:warehouse:primary"),
        secondary_warehouse_id=stable_uuid(f"{prefix}:warehouse:secondary"),
        product_id=stable_uuid(f"{prefix}:product:sku-001"),
        supplier_id=stable_uuid(f"{prefix}:supplier"),
        customer_id=stable_uuid(f"{prefix}:customer"),
        department="Packaging",
        sales_region=site.title(),
        cost_center_id=stable_uuid(f"{prefix}:cost-center"),
    )


def admin_persona() -> E2EPersona:
    return E2EPersona(
        key="admin",
        username="e2e_admin",
        permissions=("*",),
        scopes=(ScopeGrant("global", "ALL", can_view=True, can_create=True, can_edit=True),),
    )


def scoped_warehouse_manager(fixture: CoreWorkflowFixture) -> E2EPersona:
    return E2EPersona(
        key="warehouse_manager",
        username="e2e_warehouse_manager",
        permissions=(
            "inventory.view_all",
            "inventory.edit_own_scope",
            "inventory.adjust_own_scope",
            "inventory.receive_own_scope",
            "inventory.dispatch_own_scope",
            "inventory.transfer_own_scope",
        ),
        scopes=(
            ScopeGrant(
                "warehouse",
                fixture.warehouse_id,
                can_view=True,
                can_edit=True,
                can_adjust=True,
                can_receive=True,
                can_dispatch=True,
                can_transfer=True,
            ),
            ScopeGrant("warehouse", fixture.secondary_warehouse_id, can_view=True),
        ),
    )


def readonly_auditor(fixture: CoreWorkflowFixture) -> E2EPersona:
    return E2EPersona(
        key="readonly_auditor",
        username="e2e_readonly_auditor",
        permissions=(
            "inventory.view_all",
            "production.view_all",
            "quality.view_all",
            "finance.view_all",
        ),
        scopes=(
            ScopeGrant("company", fixture.company_id, can_view=True, can_export=True),
        ),
    )


def workflow_personas(fixture: CoreWorkflowFixture) -> tuple[E2EPersona, ...]:
    return (
        admin_persona(),
        scoped_warehouse_manager(fixture),
        readonly_auditor(fixture),
    )


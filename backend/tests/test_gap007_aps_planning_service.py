from decimal import Decimal
from types import SimpleNamespace
import inspect

from app.services import planning_capacity_service as svc
from app.api.v1.endpoints import planning as planning_api
from app.core import module_registry
from app.db import seed
from app.models.planning import PlanningRecStatus
from app.schemas.planning import AIRecAction


def test_aps_product_display_uses_existing_product_fields():
    product = SimpleNamespace(name="Mango Juice 250ml", sku="SKU-MANGO-250")

    assert svc._product_display(product) == ("Mango Juice 250ml", "SKU-MANGO-250")


def test_aps_work_center_rate_uses_capacity_with_default_fallback():
    work_center = SimpleNamespace(capacity=Decimal("250.5"))

    assert svc._work_center_rate(work_center) == Decimal("250.5")
    assert svc._work_center_rate(None) == svc._DEFAULT_RATE


def test_aps_operation_minutes_prefers_existing_routing_step_standard_time():
    step = SimpleNamespace(standard_time_minutes=45)

    assert svc._operation_minutes(Decimal("1000"), step, Decimal("100")) == 45
    assert svc._operation_minutes(Decimal("1000"), None, Decimal("100")) == 600


def test_aps_scheduler_does_not_reference_nonexistent_related_model_fields():
    source = inspect.getsource(svc.run_capacity_scheduling)

    assert "line.product_name" not in source
    assert "line.product_code" not in source
    assert "step.step_name" not in source
    assert "output_qty_per_hour" not in source


def test_aps_planning_api_uses_auth_context_instead_of_placeholder_user_ids():
    source = inspect.getsource(planning_api)

    assert "uuid.uuid4" not in source
    assert "_user_id" not in source
    assert "require_any_permission" in source
    assert "current_user.id" in source


def test_aps_ai_action_schema_does_not_require_client_supplied_user_id():
    action = AIRecAction(status=PlanningRecStatus.ACCEPTED)

    assert action.status == PlanningRecStatus.ACCEPTED
    assert action.actioned_by_id is None


def test_aps_planning_module_is_registry_owned_without_duplicate_endpoint_route():
    modules = {module.key: module for module in module_registry.MODULE_DEFINITIONS}
    endpoint_keys = {route.key for route in module_registry.ENDPOINT_ROUTE_DEFINITIONS}

    assert modules["planning"].route_prefix == "/planning"
    assert "calculate" in modules["planning"].permission_actions
    assert "planning" not in endpoint_keys


def test_aps_planning_permissions_are_seeded_for_production_roles():
    permission_codes = {f"{module}.{action}" for module, action, *_ in seed.PERMISSIONS}

    for code in {
        "planning.view_all",
        "planning.view_own_scope",
        "planning.create_own_scope",
        "planning.edit_own_scope",
        "planning.calculate_own_scope",
        "planning.approve_own_scope",
    }:
        assert code in permission_codes

    assert "planning.view_all" in seed.ROLE_DEFINITIONS["production_manager"]["permissions"]
    assert "planning.calculate_own_scope" in seed.ROLE_DEFINITIONS["production_manager"]["permissions"]
    assert "planning.view_own_scope" in seed.ROLE_DEFINITIONS["production_supervisor"]["permissions"]

from __future__ import annotations

from tests.e2e.workflow_fixtures import (
    admin_persona,
    core_workflow_fixture,
    readonly_auditor,
    scoped_warehouse_manager,
    stable_uuid,
    workflow_personas,
)


def test_core_workflow_fixture_is_deterministic():
    first = core_workflow_fixture("nairobi")
    second = core_workflow_fixture("nairobi")
    other_site = core_workflow_fixture("mombasa")

    assert first == second
    assert first.company_id == stable_uuid("e2e:nairobi:company")
    assert first.company_id != other_site.company_id
    assert first.to_payload()["quantity"] == "100.00"


def test_scoped_warehouse_manager_has_broad_view_but_scoped_mutation():
    fixture = core_workflow_fixture()
    persona = scoped_warehouse_manager(fixture)
    payload = persona.to_payload()

    assert "inventory.view_all" in payload["permissions"]
    assert "inventory.adjust_own_scope" in payload["permissions"]
    assert "inventory.adjust_all" not in payload["permissions"]

    scopes = {scope["scope_id"]: scope for scope in payload["scopes"]}
    assert scopes[fixture.warehouse_id]["can_adjust"] is True
    assert scopes[fixture.secondary_warehouse_id]["can_view"] is True
    assert scopes[fixture.secondary_warehouse_id]["can_adjust"] is False


def test_default_e2e_personas_are_distinct_and_safe():
    fixture = core_workflow_fixture()
    personas = workflow_personas(fixture)
    keys = {persona.key for persona in personas}

    assert keys == {"admin", "warehouse_manager", "readonly_auditor"}
    assert admin_persona().permissions == ("*",)
    assert "finance.view_all" in readonly_auditor(fixture).permissions
    assert all(persona.username.startswith("e2e_") for persona in personas)


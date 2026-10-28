"""Route dependency checks for planner and quality substitution approvals."""
from __future__ import annotations

import inspect

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints.bom import (
    create_substitution_request,
    decide_substitution_as_planner,
    decide_substitution_as_quality,
)
from app.models.role import Permission, Role
from app.models.user import User


def _permission_for(endpoint):
    dependency = inspect.signature(endpoint).parameters["current_user"].default
    return dependency.dependency


def _user_with(permission_code: str) -> User:
    permission = Permission(
        code=permission_code,
        name=permission_code,
        module=permission_code.split(".", 1)[0],
        action=permission_code.split(".", 1)[1],
        is_active=True,
    )
    role = Role(name=f"test-{permission_code}", is_active=True, permissions=[permission])
    return User(
        email=f"test-{permission_code}@example.invalid",
        username=f"test-{permission_code}",
        full_name="Synthetic Permission User",
        hashed_password="synthetic-test-only",
        is_active=True,
        roles=[role],
    )


@pytest.mark.asyncio
async def test_substitution_routes_require_their_distinct_permissions():
    planner_guard = _permission_for(decide_substitution_as_planner)
    quality_guard = _permission_for(decide_substitution_as_quality)
    request_guard = _permission_for(create_substitution_request)
    planner = _user_with("bom.approve")
    quality = _user_with("quality.approve")
    requester = _user_with("bom.edit")

    assert await planner_guard(current_user=planner) is planner
    assert await quality_guard(current_user=quality) is quality
    assert await request_guard(current_user=requester) is requester
    with pytest.raises(HTTPException) as planner_denied:
        await planner_guard(current_user=quality)
    assert planner_denied.value.status_code == 403
    with pytest.raises(HTTPException) as quality_denied:
        await quality_guard(current_user=planner)
    assert quality_denied.value.status_code == 403
    with pytest.raises(HTTPException) as request_denied:
        await request_guard(current_user=quality)
    assert request_denied.value.status_code == 403

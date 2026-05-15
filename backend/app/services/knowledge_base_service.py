"""Knowledge-base visibility and publishing helpers."""
from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status

from app.core.access_control import can_modify_record, can_view_record, forbidden_detail, has_permission, permission_code


KB_ACTION_STATUSES: dict[str, set[str]] = {
    "edit": {"DRAFT", "PUBLISHED"},
    "publish": {"DRAFT"},
    "archive": {"DRAFT", "PUBLISHED"},
    "delete": {"DRAFT"},
}


def article_status(article: Any) -> str:
    value = getattr(article, "status", "DRAFT")
    return str(getattr(value, "value", value)).upper()


def article_author_id(article: Any) -> str | None:
    value = getattr(article, "author_id", None)
    return str(value) if value is not None else None


def can_change_article_status(article: Any, action: str) -> bool:
    allowed_statuses = KB_ACTION_STATUSES.get(action)
    if allowed_statuses is None:
        return True
    if not allowed_statuses:
        return False
    return article_status(article) in allowed_statuses


def can_view_article(user: Any, article: Any) -> bool:
    if getattr(user, "is_superuser", False):
        return True
    if article_status(article) == "PUBLISHED" and has_permission(user, permission_code("knowledge_base", "view")):
        return True
    if article_author_id(article) == str(getattr(user, "id", "")) and has_permission(user, permission_code("knowledge_base", "create")):
        return True
    return can_view_record(user, "knowledge_base", article)


def can_modify_article(user: Any, article: Any, action: str) -> bool:
    if getattr(user, "is_superuser", False):
        return True
    if not can_change_article_status(article, action):
        return False
    if has_permission(user, permission_code("knowledge_base", action)):
        return True
    return can_modify_record(user, "knowledge_base", action, article)


def build_article_access_hint(user: Any, article: Any) -> dict[str, Any]:
    can_view = can_view_article(user, article)
    actions = {
        "can_edit": can_modify_article(user, article, "edit"),
        "can_publish": can_modify_article(user, article, "publish"),
        "can_archive": can_modify_article(user, article, "archive"),
        "can_delete": can_modify_article(user, article, "delete"),
    }
    mutation_allowed = any(actions.values())
    reason = None
    if can_view and not mutation_allowed:
        reason = "You can view this knowledge article but cannot modify it in this scope or publication status."
    return {
        "can_view": can_view,
        "view_only": can_view and not mutation_allowed,
        "reason": reason,
        **actions,
    }


def ensure_article_action_allowed(user: Any, article: Any, action: str) -> dict[str, Any]:
    allowed = can_view_article(user, article) if action == "view" else can_modify_article(user, article, action)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=forbidden_detail("You can view this article only if your permissions and scopes allow it."),
        )
    return build_article_access_hint(user, article)

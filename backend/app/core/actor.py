"""Who did it: actor and approver ids come from the signed-in user, never from the request body (M38 audit-trail fix)."""
from __future__ import annotations

from fastapi import HTTPException

from app.core.access_control import has_any_permission


def stamp(data, user, actor_fields: tuple[str, ...] = (), approver_fields: tuple[str, ...] = (),
          approve_permissions: tuple[str, ...] = ()) -> None:
    """Set every actor field to the signed-in user. An approver field may only name the signed-in user themselves
    (and, when approve_permissions is given, only if they hold one of them) — nobody records someone else's approval."""
    for f in actor_fields:
        setattr(data, f, user.id)
    for f in approver_fields:
        value = getattr(data, f, None)
        if value is None:
            continue
        if value != user.id:
            raise HTTPException(422, "An approval can only be recorded by the approver, from their own login.")
        if approve_permissions and not has_any_permission(user, approve_permissions):
            raise HTTPException(403, "You do not have the right to approve this.")

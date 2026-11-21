"""M40: plain modify rights (e.g. procurement.create) work company-wide only for users with no scopes at all; once
any scope is assigned they work inside those scopes only. *_own_scope rights still need a scope."""
from types import SimpleNamespace as NS

from app.core.access_control import can_modify_record


def _user(*codes, scopes=(), role_scopes=()):
    perms = [NS(code=c, is_active=True) for c in codes]
    return NS(id=1, is_superuser=False, access_scopes=list(scopes),
              roles=[NS(name="r", is_active=True, permissions=perms, access_scopes=list(role_scopes))])


def _scope(dept, **flags):
    return NS(scope_type="department", scope_id=dept, is_active=True, **{f"can_{k}": v for k, v in flags.items()})


PACK = NS(department="PACK", status="DRAFT")
OTHER = NS(department="OTHER", status="DRAFT")
NOSCOPE = NS(status="DRAFT")


def test_plain_rights_follow_scopes():
    unscoped = _user("procurement.create")
    assert can_modify_record(unscoped, "procurement", "create", PACK)
    assert can_modify_record(unscoped, "procurement", "create", NOSCOPE)
    assert not can_modify_record(unscoped, "procurement", "approve", PACK)        # other actions stay closed

    scoped = _user("procurement.create", scopes=[_scope("PACK", create=True)])
    assert can_modify_record(scoped, "procurement", "create", PACK)
    assert not can_modify_record(scoped, "procurement", "create", OTHER)
    assert not can_modify_record(scoped, "procurement", "create", NOSCOPE)

    via_role = _user("procurement.create", role_scopes=[_scope("PACK", create=True)])
    assert not can_modify_record(via_role, "procurement", "create", OTHER)

    own_only = _user("procurement.approve_own_scope")                              # explicit scoped role, no scopes
    assert not can_modify_record(own_only, "procurement", "approve", PACK)
    assert can_modify_record(_user("procurement.approve_all"), "procurement", "approve", NOSCOPE)

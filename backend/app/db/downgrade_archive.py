"""Non-destructive downgrades for CRM evidence tables (M48.S01.T023, M36 audit F3).

Consent records, outbox suppression, signed quote decisions, document links and chats are evidence: a schema
downgrade must not delete them. Instead of DROP TABLE, a downgrade renames the table to
`<name>_archived_<revision>` (then `_2`, `_3`, ... if that name is taken), renames its indexes so a later upgrade can
recreate the originals, and drops its outgoing foreign keys so the archive never blocks an older downgrade.
Archives are not mapped by the ORM; an operator exports or deletes them by hand after review.
"""
from __future__ import annotations

import hashlib

import sqlalchemy as sa


def _q(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def archive_tables(bind, names, revision: str) -> list[str]:
    """Rename each existing table in `names` to an archive; returns the archive names (caller's order)."""
    done = []
    for name in names:
        insp = sa.inspect(bind)
        if not insp.has_table(name):
            continue
        base = f"{name}_archived_{revision}"[:60]
        target, n = base, 1
        while insp.has_table(target):
            n += 1
            target = f"{base}_{n}"
        for fk in insp.get_foreign_keys(name):
            if fk.get("name"):
                bind.exec_driver_sql(f"ALTER TABLE {_q(name)} DROP CONSTRAINT {_q(fk['name'])}")
        idx = bind.execute(sa.text("SELECT indexname FROM pg_indexes WHERE schemaname = current_schema() "
                                   "AND tablename = :t"), {"t": name}).scalars().all()
        for i in idx:   # PK / unique constraints are renamed with their index
            new = f"{target[:40]}_{hashlib.md5(i.encode()).hexdigest()[:12]}"
            bind.exec_driver_sql(f"ALTER INDEX {_q(i)} RENAME TO {_q(new)}")
        bind.exec_driver_sql(f"ALTER TABLE {_q(name)} RENAME TO {_q(target)}")
        done.append(target)
    return done

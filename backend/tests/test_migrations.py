"""Alembic migration chain integrity tests — no DB required."""
from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory


BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _script() -> ScriptDirectory:
    cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
    return ScriptDirectory.from_config(cfg)


def test_single_migration_head():
    """Fail CI if the migration chain is branched (two developers added competing heads)."""
    heads = _script().get_heads()
    assert len(heads) == 1, (
        f"Expected 1 Alembic head, found {len(heads)}: {heads}. "
        "Merge the branches with `alembic merge heads` before merging this PR."
    )


def test_all_migrations_have_downgrade():
    """Every migration must have a downgrade() function (not just `pass`)."""
    script = _script()
    missing = []
    for rev in script.walk_revisions():
        module = rev.module
        downgrade_fn = getattr(module, "downgrade", None)
        if downgrade_fn is None:
            missing.append(rev.revision)
    assert not missing, f"Migrations missing downgrade(): {missing}"


def test_no_duplicate_revision_ids():
    """Each revision ID must be unique across the migration chain."""
    script = _script()
    seen: dict[str, str] = {}
    duplicates = []
    for rev in script.walk_revisions():
        if rev.revision in seen:
            duplicates.append(rev.revision)
        seen[rev.revision] = rev.doc or ""
    assert not duplicates, f"Duplicate revision IDs found: {duplicates}"


def test_migration_files_are_importable():
    """All migration files must be importable without errors."""
    import importlib
    import sys

    versions_dir = BACKEND_ROOT / "alembic" / "versions"
    errors = []
    for py_file in sorted(versions_dir.glob("*.py")):
        module_name = f"alembic_versions_{py_file.stem}"
        spec = importlib.util.spec_from_file_location(module_name, py_file)
        if spec is None:
            errors.append(str(py_file))
            continue
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)  # type: ignore[union-attr]
        except Exception as exc:
            errors.append(f"{py_file.name}: {exc}")
    assert not errors, "Migration files with import errors:\n" + "\n".join(errors)

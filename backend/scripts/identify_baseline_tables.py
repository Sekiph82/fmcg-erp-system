"""Script to identify pre-Alembic tables for baseline migration generation."""
from __future__ import annotations
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Tables created by Alembic migrations
versions_dir = ROOT / "alembic" / "versions"
migration_created: set[str] = set()
for f in sorted(versions_dir.glob("*.py")):
    content = f.read_text(encoding="utf-8", errors="ignore")
    tables = re.findall(r"op\.create_table\(\s*['\"](\w+)['\"]", content)
    migration_created.update(tables)

print(f"Tables created by migrations ({len(migration_created)}):")
print(sorted(migration_created))
print()

# All SQLAlchemy model tables
from app.db.base import Base
import app.models  # noqa

all_tables = set(Base.metadata.tables.keys())
print(f"All model tables ({len(all_tables)})")

pre_alembic = sorted(all_tables - migration_created)
print(f"\nPre-Alembic tables ({len(pre_alembic)}):")
for t in pre_alembic:
    print(f"  {t}")

print(f"\nMigration-only tables NOT in models ({len(migration_created - all_tables)}):")
for t in sorted(migration_created - all_tables):
    print(f"  {t}")

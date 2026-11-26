"""M46 Content & Digital Experience Hub.

Tables are created from their ORM definitions (checkfirst), like 0075. Downgrade drops them: content, media
metadata and studio drafts are lost (media files under MEDIA_STORAGE_PATH stay on disk).
"""

from alembic import op

revision = "20261127_0076"
down_revision = "20261126_0075"
branch_labels = None
depends_on = None

# Parents first (downgrade drops in reverse).
TABLES = [
    "cms_sites", "cms_access_lists", "cms_tables", "cms_table_rows", "cms_pages", "cms_page_versions", "cms_redirects",
    "cms_ctas", "cms_keywords", "cms_experiments", "cms_experiment_events", "cms_media", "cms_media_views",
    "cs_brand_profiles", "cs_drafts", "cs_usage",
]

COLUMNS = [
    ("kb_articles", "access_list_id", "UUID REFERENCES cms_access_lists(id) ON DELETE SET NULL"),
]


def _tables():
    import app.models  # noqa: F401
    from app.db.base import Base
    return [Base.metadata.tables[n] for n in TABLES]


def upgrade() -> None:
    bind = op.get_bind()
    for t in _tables():
        t.create(bind=bind, checkfirst=True)
    for table, col, ddl in COLUMNS:
        op.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {ddl}")


def downgrade() -> None:
    bind = op.get_bind()
    for table, col, _ in reversed(COLUMNS):
        op.execute(f"ALTER TABLE {table} DROP COLUMN IF EXISTS {col}")
    for t in reversed(_tables()):
        t.drop(bind=bind, checkfirst=True)

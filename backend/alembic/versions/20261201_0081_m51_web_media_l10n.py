"""M51 web, media and localization platform: CMS nested layout library (components, versions, site layouts),
Search Console snapshots and sitemap submissions, technical SEO crawls and keywords, AEO measurement, visitor e-mail
verification, AI image jobs, pluggable object storage (objects, upload sessions, quotas, backups) and media jobs.

Tables are created from their ORM definitions (checkfirst), like 0075-0080. Downgrade archives evidence tables
(approvals, submissions, measurements, verification/consent records, storage and media records) instead of dropping
them (audit F3 rule).
"""

from alembic import op

revision = "20261201_0081"
down_revision = "20261130_0080"
branch_labels = None
depends_on = None

TABLES = [
    "cms_components", "cms_component_versions", "cms_site_layouts",                                   # T001-T002
    "m51_gsc_snapshots", "m51_gsc_submissions", "m51_seo_sites", "m51_seo_crawls", "m51_seo_pages", "m51_seo_issues",
    "m51_keywords", "m51_aeo_prompt_sets", "m51_aeo_runs", "m51_aeo_answers",                         # T003-T005
    "m51_visitor_verifications", "m51_visitor_mail_outbox",                                           # T009
    "m51_image_jobs", "m51_image_usage", "m51_storage_objects", "m51_upload_sessions", "m51_storage_quotas",
    "m51_storage_backups", "m51_media_jobs",                                                         # T006/T007/T010
]

EVIDENCE = ["cms_component_versions", "m51_gsc_snapshots", "m51_gsc_submissions", "m51_seo_sites", "m51_aeo_prompt_sets",
            "m51_aeo_runs", "m51_aeo_answers", "m51_visitor_verifications", "m51_image_jobs", "m51_image_usage",
            "m51_storage_objects", "m51_storage_backups", "m51_media_jobs"]


def _tables():
    import app.models  # noqa: F401
    from app.db.base import Base
    return [Base.metadata.tables[n] for n in TABLES]


def upgrade() -> None:
    bind = op.get_bind()
    for t in _tables():
        t.create(bind=bind, checkfirst=True)


def downgrade() -> None:
    from app.db.downgrade_archive import archive_tables
    bind = op.get_bind()
    archive_tables(bind, [n for n in reversed(TABLES) if n in EVIDENCE], "0081")
    for t in reversed(_tables()):
        if t.name not in EVIDENCE:
            t.drop(bind=bind, checkfirst=True)

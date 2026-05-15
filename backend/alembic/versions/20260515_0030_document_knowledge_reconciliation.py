"""document knowledge reconciliation

Revision ID: 20260515_0030
Revises: 20260515_0020
Create Date: 2026-05-15 12:55:00.000000
"""
from __future__ import annotations

from alembic import context, op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260515_0030"
down_revision = "20260515_0020"
branch_labels = None
depends_on = None


UUID = postgresql.UUID(as_uuid=True)
JSONB = postgresql.JSONB


DOCUMENT_CATEGORY_VALUES = (
    "SOP",
    "WORK_INSTRUCTION",
    "QC_DOCUMENT",
    "CUSTOMS_DOCUMENT",
    "INVOICE",
    "SHIPMENT_DOCUMENT",
    "PAYMENT_PROOF",
    "RECONCILIATION",
    "MAINTENANCE_MANUAL",
    "HR_DOCUMENT",
    "CAMPAIGN_DOCUMENT",
    "INFLUENCER_CONTRACT",
    "SURVEY_DOCUMENT",
    "BRAND_SPEND_INVOICE",
    "TRADE_SPEND_APPROVAL",
    "MARKETING_CREATIVE",
    "OTHER",
)
DOCUMENT_STATUS_VALUES = ("DRAFT", "APPROVED", "OBSOLETE", "ARCHIVED")
SIGNATURE_REQUEST_STATUS_VALUES = ("PENDING", "SIGNED", "DECLINED", "EXPIRED")
SIGNATURE_RECORD_STATUS_VALUES = ("PENDING", "SIGNED", "DECLINED")


def _inspector():
    return sa.inspect(op.get_bind())


def _has_table(table_name: str) -> bool:
    if context.is_offline_mode():
        return True
    return table_name in _inspector().get_table_names()


def _columns(table_name: str) -> set[str]:
    if context.is_offline_mode() or not _has_table(table_name):
        return set()
    return {column["name"] for column in _inspector().get_columns(table_name)}


def _indexes(table_name: str) -> set[str]:
    if context.is_offline_mode() or not _has_table(table_name):
        return set()
    return {index["name"] for index in _inspector().get_indexes(table_name)}


def _foreign_keys(table_name: str) -> set[str]:
    if context.is_offline_mode() or not _has_table(table_name):
        return set()
    return {fk["name"] for fk in _inspector().get_foreign_keys(table_name) if fk.get("name")}


def _add_column_once(table_name: str, column: sa.Column) -> None:
    if context.is_offline_mode() or (_has_table(table_name) and column.name not in _columns(table_name)):
        op.add_column(table_name, column)


def _drop_column_if_exists(table_name: str, column_name: str) -> None:
    if _has_table(table_name) and column_name in _columns(table_name):
        op.drop_column(table_name, column_name)


def _create_index_once(name: str, table_name: str, columns: list[str], **kwargs) -> None:
    if context.is_offline_mode() or (_has_table(table_name) and name not in _indexes(table_name)):
        op.create_index(name, table_name, columns, **kwargs)


def _drop_index_if_exists(name: str, table_name: str) -> None:
    if _has_table(table_name) and name in _indexes(table_name):
        op.drop_index(name, table_name=table_name)


def _create_fk_once(
    name: str,
    source_table: str,
    referent_table: str,
    local_cols: list[str],
    remote_cols: list[str],
    **kwargs,
) -> None:
    if context.is_offline_mode() or (_has_table(source_table) and name not in _foreign_keys(source_table)):
        op.create_foreign_key(name, source_table, referent_table, local_cols, remote_cols, **kwargs)


def _drop_fk_if_exists(name: str, table_name: str) -> None:
    if _has_table(table_name) and name in _foreign_keys(table_name):
        op.drop_constraint(name, table_name, type_="foreignkey")


def _create_enum(name: str, *values: str) -> None:
    enum = postgresql.ENUM(*values, name=name)
    enum.create(op.get_bind(), checkfirst=True)


def _enum(name: str, *values: str):
    return postgresql.ENUM(*values, name=name, create_type=False)


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def _create_documents_if_missing() -> None:
    if not context.is_offline_mode() and _has_table("documents"):
        return
    op.create_table(
        "documents",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("category", _enum("documentcategory", *DOCUMENT_CATEGORY_VALUES), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("revision_note", sa.Text(), nullable=True),
        sa.Column("previous_version_id", UUID, nullable=True),
        sa.Column("is_latest", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("status", _enum("documentstatus", *DOCUMENT_STATUS_VALUES), nullable=False, server_default="DRAFT"),
        sa.Column("effective_date", sa.Date(), nullable=True),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("owner_user_id", UUID, nullable=True),
        sa.Column("approved_by_id", UUID, nullable=True),
        sa.Column("related_entity_type", sa.String(100), nullable=True),
        sa.Column("related_entity_id", sa.String(36), nullable=True),
        sa.Column("file_url", sa.Text(), nullable=True),
        sa.Column("file_name", sa.String(255), nullable=True),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("mime_type", sa.String(100), nullable=True),
        *_timestamps(),
        sa.CheckConstraint("version > 0", name="ck_documents_version_positive"),
        sa.CheckConstraint("file_size_bytes IS NULL OR file_size_bytes >= 0", name="ck_documents_file_size_nonnegative"),
        sa.ForeignKeyConstraint(["previous_version_id"], ["documents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["approved_by_id"], ["users.id"], ondelete="SET NULL"),
    )


def _create_document_tags_if_missing() -> None:
    if not context.is_offline_mode() and _has_table("document_tags"):
        return
    op.create_table(
        "document_tags",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("document_id", UUID, nullable=False),
        sa.Column("tag", sa.String(100), nullable=False),
        sa.Column("created_by", sa.String(200), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
    )


def _create_kb_tables_if_missing() -> None:
    if context.is_offline_mode() or not _has_table("kb_categories"):
        op.create_table(
            "kb_categories",
            sa.Column("id", UUID, primary_key=True),
            sa.Column("slug", sa.String(100), nullable=False),
            sa.Column("name", sa.String(200), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("parent_id", UUID, nullable=True),
            sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("icon", sa.String(50), nullable=True),
            *_timestamps(),
            sa.ForeignKeyConstraint(["parent_id"], ["kb_categories.id"], ondelete="SET NULL"),
            sa.UniqueConstraint("slug", name="uq_kb_categories_slug"),
        )

    if context.is_offline_mode() or not _has_table("kb_articles"):
        op.create_table(
            "kb_articles",
            sa.Column("id", UUID, primary_key=True),
            sa.Column("slug", sa.String(200), nullable=False),
            sa.Column("title", sa.String(300), nullable=False),
            sa.Column("summary", sa.Text(), nullable=True),
            sa.Column("content_md", sa.Text(), nullable=False, server_default=""),
            sa.Column("category_id", UUID, nullable=True),
            sa.Column("tags", JSONB, nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="DRAFT"),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("author_id", UUID, nullable=True),
            sa.Column("last_editor_id", UUID, nullable=True),
            sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("view_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("is_featured", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("access_level", sa.String(30), nullable=False, server_default="all"),
            *_timestamps(),
            sa.ForeignKeyConstraint(["category_id"], ["kb_categories.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["last_editor_id"], ["users.id"], ondelete="SET NULL"),
            sa.UniqueConstraint("slug", name="uq_kb_articles_slug"),
            sa.CheckConstraint("version > 0", name="ck_kb_articles_version_positive"),
            sa.CheckConstraint("view_count >= 0", name="ck_kb_articles_view_count_nonnegative"),
        )

    if context.is_offline_mode() or not _has_table("kb_article_revisions"):
        op.create_table(
            "kb_article_revisions",
            sa.Column("id", UUID, primary_key=True),
            sa.Column("article_id", UUID, nullable=False),
            sa.Column("version_no", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(300), nullable=False),
            sa.Column("content_md", sa.Text(), nullable=False),
            sa.Column("change_summary", sa.String(500), nullable=True),
            sa.Column("changed_by_id", UUID, nullable=True),
            *_timestamps(),
            sa.ForeignKeyConstraint(["article_id"], ["kb_articles.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["changed_by_id"], ["users.id"], ondelete="SET NULL"),
            sa.CheckConstraint("version_no > 0", name="ck_kb_article_revisions_version_positive"),
        )


def _create_signature_tables_if_missing() -> None:
    if context.is_offline_mode() or not _has_table("signature_requests"):
        op.create_table(
            "signature_requests",
            sa.Column("id", UUID, primary_key=True),
            sa.Column("request_no", sa.String(50), nullable=False),
            sa.Column("document_id", UUID, nullable=True),
            sa.Column("document_type", sa.String(100), nullable=False),
            sa.Column("document_ref", sa.String(255), nullable=False),
            sa.Column("requester_id", UUID, nullable=True),
            sa.Column("subject", sa.String(255), nullable=False),
            sa.Column("message", sa.Text(), nullable=True),
            sa.Column("status", _enum("signaturerequeststatus", *SIGNATURE_REQUEST_STATUS_VALUES), nullable=False, server_default="PENDING"),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("required_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("signed_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("declined_count", sa.Integer(), nullable=False, server_default="0"),
            *_timestamps(),
            sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["requester_id"], ["users.id"], ondelete="SET NULL"),
            sa.UniqueConstraint("request_no", name="uq_signature_requests_request_no"),
            sa.CheckConstraint("required_count >= 0", name="ck_signature_requests_required_count_nonnegative"),
            sa.CheckConstraint("signed_count >= 0", name="ck_signature_requests_signed_count_nonnegative"),
            sa.CheckConstraint("declined_count >= 0", name="ck_signature_requests_declined_count_nonnegative"),
        )

    if context.is_offline_mode() or not _has_table("signature_records"):
        op.create_table(
            "signature_records",
            sa.Column("id", UUID, primary_key=True),
            sa.Column("request_id", UUID, nullable=False),
            sa.Column("signer_id", UUID, nullable=True),
            sa.Column("status", _enum("signaturerecordstatus", *SIGNATURE_RECORD_STATUS_VALUES), nullable=False, server_default="PENDING"),
            sa.Column("signed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("declined_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("ip_address", sa.String(45), nullable=True),
            sa.Column("user_agent", sa.String(500), nullable=True),
            sa.Column("signature_data", sa.Text(), nullable=True),
            *_timestamps(),
            sa.ForeignKeyConstraint(["request_id"], ["signature_requests.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["signer_id"], ["users.id"], ondelete="SET NULL"),
        )


def _add_document_governance_columns() -> None:
    table = "documents"
    if not context.is_offline_mode() and not _has_table(table):
        return
    for column in (
        sa.Column("document_no", sa.String(80), nullable=True),
        sa.Column("lineage_id", UUID, nullable=True),
        sa.Column("document_type", sa.String(100), nullable=True),
        sa.Column("company_id", UUID, nullable=True),
        sa.Column("branch_id", UUID, nullable=True),
        sa.Column("department_id", sa.String(100), nullable=True),
        sa.Column("factory_id", sa.String(100), nullable=True),
        sa.Column("product_category_id", sa.String(100), nullable=True),
        sa.Column("supplier_id", UUID, nullable=True),
        sa.Column("customer_id", UUID, nullable=True),
        sa.Column("confidentiality_level", sa.String(30), nullable=False, server_default="INTERNAL"),
        sa.Column("retention_until", sa.Date(), nullable=True),
        sa.Column("legal_hold", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("review_due_date", sa.Date(), nullable=True),
        sa.Column("next_review_owner_id", UUID, nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("obsolete_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_by_id", UUID, nullable=True),
        sa.Column("storage_provider", sa.String(30), nullable=True),
        sa.Column("storage_key", sa.Text(), nullable=True),
        sa.Column("file_checksum_sha256", sa.String(64), nullable=True),
        sa.Column("file_scan_status", sa.String(30), nullable=False, server_default="NOT_SCANNED"),
        sa.Column("file_scan_result", sa.Text(), nullable=True),
        sa.Column("file_locked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_by_id", UUID, nullable=True),
        sa.Column("updated_by_id", UUID, nullable=True),
    ):
        _add_column_once(table, column)

    for fk_name, local_col in (
        ("fk_documents_next_review_owner_id", "next_review_owner_id"),
        ("fk_documents_locked_by_id", "locked_by_id"),
        ("fk_documents_created_by_id", "created_by_id"),
        ("fk_documents_updated_by_id", "updated_by_id"),
    ):
        _create_fk_once(fk_name, table, "users", [local_col], ["id"], ondelete="SET NULL")


def _add_kb_governance_columns() -> None:
    table = "kb_articles"
    if not context.is_offline_mode() and not _has_table(table):
        return
    for column in (
        sa.Column("company_id", UUID, nullable=True),
        sa.Column("department_id", sa.String(100), nullable=True),
        sa.Column("factory_id", sa.String(100), nullable=True),
        sa.Column("module_key", sa.String(100), nullable=True),
        sa.Column("published_by_id", UUID, nullable=True),
        sa.Column("archived_by_id", UUID, nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_due_date", sa.Date(), nullable=True),
        sa.Column("access_scope_type", sa.String(50), nullable=True),
        sa.Column("access_scope_id", sa.String(100), nullable=True),
        sa.Column("is_internal_only", sa.Boolean(), nullable=False, server_default=sa.true()),
    ):
        _add_column_once(table, column)

    _create_fk_once("fk_kb_articles_published_by_id", table, "users", ["published_by_id"], ["id"], ondelete="SET NULL")
    _create_fk_once("fk_kb_articles_archived_by_id", table, "users", ["archived_by_id"], ["id"], ondelete="SET NULL")


def _add_signature_governance_columns() -> None:
    table = "signature_requests"
    if context.is_offline_mode() or _has_table(table):
        for column in (
            sa.Column("company_id", UUID, nullable=True),
            sa.Column("branch_id", UUID, nullable=True),
            sa.Column("department_id", sa.String(100), nullable=True),
            sa.Column("factory_id", sa.String(100), nullable=True),
            sa.Column("module_key", sa.String(100), nullable=True),
            sa.Column("related_entity_type", sa.String(100), nullable=True),
            sa.Column("related_entity_id", sa.String(100), nullable=True),
            sa.Column("document_hash_sha256", sa.String(64), nullable=True),
            sa.Column("payload_hash_sha256", sa.String(64), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("expired_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("cancelled_by_id", UUID, nullable=True),
            sa.Column("evidence_summary", JSONB, nullable=True),
            sa.Column("audit_request_id", sa.String(100), nullable=True),
        ):
            _add_column_once(table, column)
        _create_fk_once("fk_signature_requests_cancelled_by_id", table, "users", ["cancelled_by_id"], ["id"], ondelete="SET NULL")

    table = "signature_records"
    if context.is_offline_mode() or _has_table(table):
        for column in (
            sa.Column("signed_payload_hash_sha256", sa.String(64), nullable=True),
            sa.Column("decline_reason", sa.Text(), nullable=True),
            sa.Column("evidence_hash_sha256", sa.String(64), nullable=True),
            sa.Column("auth_method", sa.String(50), nullable=True),
            sa.Column("signed_document_version", sa.Integer(), nullable=True),
            sa.Column("signed_document_id", UUID, nullable=True),
        ):
            _add_column_once(table, column)
        _create_fk_once("fk_signature_records_signed_document_id", table, "documents", ["signed_document_id"], ["id"], ondelete="SET NULL")


def _create_indexes() -> None:
    for name, table, columns in (
        ("ix_documents_title", "documents", ["title"]),
        ("ix_documents_category", "documents", ["category"]),
        ("ix_documents_status", "documents", ["status"]),
        ("ix_documents_owner_user_id", "documents", ["owner_user_id"]),
        ("ix_documents_related_entity_type", "documents", ["related_entity_type"]),
        ("ix_documents_related_entity_id", "documents", ["related_entity_id"]),
        ("ix_documents_document_no", "documents", ["document_no"]),
        ("ix_documents_lineage_id", "documents", ["lineage_id"]),
        ("ix_documents_expiry_date", "documents", ["expiry_date"]),
        ("ix_documents_review_due_date", "documents", ["review_due_date"]),
        ("ix_documents_company_id", "documents", ["company_id"]),
        ("ix_documents_branch_id", "documents", ["branch_id"]),
        ("ix_documents_department_id", "documents", ["department_id"]),
        ("ix_documents_factory_id", "documents", ["factory_id"]),
        ("ix_documents_supplier_id", "documents", ["supplier_id"]),
        ("ix_documents_customer_id", "documents", ["customer_id"]),
        ("ix_documents_file_checksum_sha256", "documents", ["file_checksum_sha256"]),
        ("ix_document_tags_document_id", "document_tags", ["document_id"]),
        ("ix_document_tags_tag", "document_tags", ["tag"]),
        ("ix_kb_categories_slug", "kb_categories", ["slug"]),
        ("ix_kb_articles_slug", "kb_articles", ["slug"]),
        ("ix_kb_articles_category_id", "kb_articles", ["category_id"]),
        ("ix_kb_articles_status", "kb_articles", ["status"]),
        ("ix_kb_articles_module_key", "kb_articles", ["module_key"]),
        ("ix_kb_articles_access_scope", "kb_articles", ["access_scope_type", "access_scope_id"]),
        ("ix_kb_article_revisions_article_id", "kb_article_revisions", ["article_id"]),
        ("ix_signature_requests_request_no", "signature_requests", ["request_no"]),
        ("ix_signature_requests_document_id", "signature_requests", ["document_id"]),
        ("ix_signature_requests_requester_id", "signature_requests", ["requester_id"]),
        ("ix_signature_requests_status", "signature_requests", ["status"]),
        ("ix_signature_requests_company_id", "signature_requests", ["company_id"]),
        ("ix_signature_requests_module_entity", "signature_requests", ["module_key", "related_entity_type", "related_entity_id"]),
        ("ix_signature_records_request_id", "signature_records", ["request_id"]),
        ("ix_signature_records_signer_id", "signature_records", ["signer_id"]),
    ):
        _create_index_once(name, table, columns)


def upgrade() -> None:
    _create_enum("documentcategory", *DOCUMENT_CATEGORY_VALUES)
    _create_enum("documentstatus", *DOCUMENT_STATUS_VALUES)
    _create_enum("signaturerequeststatus", *SIGNATURE_REQUEST_STATUS_VALUES)
    _create_enum("signaturerecordstatus", *SIGNATURE_RECORD_STATUS_VALUES)

    _create_documents_if_missing()
    _create_document_tags_if_missing()
    _create_kb_tables_if_missing()
    _create_signature_tables_if_missing()

    _add_document_governance_columns()
    _add_kb_governance_columns()
    _add_signature_governance_columns()
    _create_indexes()


def downgrade() -> None:
    for name, table in (
        ("ix_signature_records_signer_id", "signature_records"),
        ("ix_signature_records_request_id", "signature_records"),
        ("ix_signature_requests_module_entity", "signature_requests"),
        ("ix_signature_requests_company_id", "signature_requests"),
        ("ix_signature_requests_status", "signature_requests"),
        ("ix_signature_requests_requester_id", "signature_requests"),
        ("ix_signature_requests_document_id", "signature_requests"),
        ("ix_signature_requests_request_no", "signature_requests"),
        ("ix_kb_article_revisions_article_id", "kb_article_revisions"),
        ("ix_kb_articles_access_scope", "kb_articles"),
        ("ix_kb_articles_module_key", "kb_articles"),
        ("ix_kb_articles_status", "kb_articles"),
        ("ix_kb_articles_category_id", "kb_articles"),
        ("ix_kb_articles_slug", "kb_articles"),
        ("ix_kb_categories_slug", "kb_categories"),
        ("ix_document_tags_tag", "document_tags"),
        ("ix_document_tags_document_id", "document_tags"),
        ("ix_documents_file_checksum_sha256", "documents"),
        ("ix_documents_customer_id", "documents"),
        ("ix_documents_supplier_id", "documents"),
        ("ix_documents_factory_id", "documents"),
        ("ix_documents_department_id", "documents"),
        ("ix_documents_branch_id", "documents"),
        ("ix_documents_company_id", "documents"),
        ("ix_documents_review_due_date", "documents"),
        ("ix_documents_expiry_date", "documents"),
        ("ix_documents_lineage_id", "documents"),
        ("ix_documents_document_no", "documents"),
    ):
        _drop_index_if_exists(name, table)

    _drop_fk_if_exists("fk_signature_records_signed_document_id", "signature_records")
    for column_name in (
        "signed_document_id",
        "signed_document_version",
        "auth_method",
        "evidence_hash_sha256",
        "decline_reason",
        "signed_payload_hash_sha256",
    ):
        _drop_column_if_exists("signature_records", column_name)

    _drop_fk_if_exists("fk_signature_requests_cancelled_by_id", "signature_requests")
    for column_name in (
        "audit_request_id",
        "evidence_summary",
        "cancelled_by_id",
        "cancelled_at",
        "expired_at",
        "completed_at",
        "payload_hash_sha256",
        "document_hash_sha256",
        "related_entity_id",
        "related_entity_type",
        "module_key",
        "factory_id",
        "department_id",
        "branch_id",
        "company_id",
    ):
        _drop_column_if_exists("signature_requests", column_name)

    _drop_fk_if_exists("fk_kb_articles_archived_by_id", "kb_articles")
    _drop_fk_if_exists("fk_kb_articles_published_by_id", "kb_articles")
    for column_name in (
        "is_internal_only",
        "access_scope_id",
        "access_scope_type",
        "review_due_date",
        "archived_at",
        "archived_by_id",
        "published_by_id",
        "module_key",
        "factory_id",
        "department_id",
        "company_id",
    ):
        _drop_column_if_exists("kb_articles", column_name)

    for fk_name in (
        "fk_documents_updated_by_id",
        "fk_documents_created_by_id",
        "fk_documents_locked_by_id",
        "fk_documents_next_review_owner_id",
    ):
        _drop_fk_if_exists(fk_name, "documents")
    for column_name in (
        "updated_by_id",
        "created_by_id",
        "file_locked",
        "file_scan_result",
        "file_scan_status",
        "file_checksum_sha256",
        "storage_key",
        "storage_provider",
        "locked_by_id",
        "locked_at",
        "archived_at",
        "obsolete_at",
        "approved_at",
        "next_review_owner_id",
        "review_due_date",
        "legal_hold",
        "retention_until",
        "confidentiality_level",
        "customer_id",
        "supplier_id",
        "product_category_id",
        "factory_id",
        "department_id",
        "branch_id",
        "company_id",
        "document_type",
        "lineage_id",
        "document_no",
    ):
        _drop_column_if_exists("documents", column_name)

"""M35: QC/QA enterprise — specs, QC plans, test methods, SPC signals, concessions,
quality costs, retain samples, change control; audit closure and AQL integrity."""

from alembic import op
import sqlalchemy as sa

revision = "20261110_0028"
down_revision = "20261110_0027b"
branch_labels = None
depends_on = None

UUID = sa.Uuid(as_uuid=True)


def _id():
    return sa.Column("id", UUID, primary_key=True)


def _ts():
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    ]


def _fk(name, target, ondelete, nullable=True):
    return sa.Column(name, UUID, sa.ForeignKey(target, ondelete=ondelete), nullable=nullable)


def upgrade() -> None:
    op.create_table(
        "qc_test_methods",
        _id(),
        sa.Column("method_code", sa.String(50), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("standard_reference", sa.String(200)),
        sa.Column("description", sa.Text()),
        sa.Column("instrument_type", sa.String(100)),
        sa.Column("requires_instrument", sa.Boolean(), nullable=False, server_default=sa.false()),
        _fk("required_skill_id", "training_skills.skill_id", "SET NULL"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        *_ts(),
        sa.UniqueConstraint("method_code", "version", name="uq_qc_test_methods_code_version"),
        sa.CheckConstraint("version >= 1", name="ck_qc_test_methods_version_positive"),
    )
    op.create_index("ix_qc_test_methods_method_code", "qc_test_methods", ["method_code"])

    op.create_table(
        "quality_change_requests",
        _id(),
        sa.Column("cr_no", sa.String(50), nullable=False, unique=True),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("change_type", sa.String(20), nullable=False),
        sa.Column("target_reference", sa.String(100)),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("risk_assessment", sa.Text()),
        sa.Column("status", sa.String(16), nullable=False, server_default="DRAFT"),
        _fk("requested_by_id", "users.id", "RESTRICT", nullable=False),
        _fk("decided_by_id", "users.id", "RESTRICT"),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
        sa.Column("decision_notes", sa.Text()),
        _fk("implemented_by_id", "users.id", "SET NULL"),
        sa.Column("implemented_at", sa.DateTime(timezone=True)),
        sa.Column("verification_notes", sa.Text()),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
        *_ts(),
        sa.CheckConstraint("change_type IN ('SPECIFICATION', 'QC_PLAN', 'TEST_METHOD', 'PROCESS', 'OTHER')",
                           name="ck_quality_change_requests_type"),
        sa.CheckConstraint("status IN ('DRAFT', 'SUBMITTED', 'APPROVED', 'REJECTED', 'IMPLEMENTED', 'CLOSED', 'CANCELLED')",
                           name="ck_quality_change_requests_status"),
        sa.CheckConstraint("status NOT IN ('APPROVED', 'REJECTED', 'IMPLEMENTED', 'CLOSED') "
                           "OR (decided_by_id IS NOT NULL AND decided_by_id != requested_by_id)",
                           name="ck_quality_change_requests_segregation"),
    )
    op.create_index("ix_quality_change_requests_cr_no", "quality_change_requests", ["cr_no"])
    op.create_index("ix_quality_change_requests_target_reference", "quality_change_requests", ["target_reference"])

    op.create_table(
        "qc_specifications",
        _id(),
        sa.Column("spec_code", sa.String(50), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("scope_type", sa.String(16), nullable=False),
        _fk("product_id", "products.id", "RESTRICT"),
        _fk("material_id", "materials.id", "RESTRICT"),
        sa.Column("process_stage", sa.String(100)),
        _fk("template_id", "qc_templates.id", "RESTRICT", nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="DRAFT"),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date()),
        _fk("change_request_id", "quality_change_requests.id", "RESTRICT"),
        sa.Column("change_reason", sa.Text()),
        sa.Column("parameter_snapshot", sa.JSON()),
        _fk("created_by_id", "users.id", "RESTRICT", nullable=False),
        _fk("approved_by_id", "users.id", "RESTRICT"),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        *_ts(),
        sa.UniqueConstraint("spec_code", "version", name="uq_qc_specifications_code_version"),
        sa.CheckConstraint("version >= 1", name="ck_qc_specifications_version_positive"),
        sa.CheckConstraint("status IN ('DRAFT', 'APPROVED', 'SUPERSEDED', 'RETIRED')", name="ck_qc_specifications_status"),
        sa.CheckConstraint("effective_to IS NULL OR effective_to >= effective_from", name="ck_qc_specifications_window"),
        sa.CheckConstraint("(scope_type = 'PRODUCT' AND product_id IS NOT NULL) "
                           "OR (scope_type = 'MATERIAL' AND material_id IS NOT NULL) "
                           "OR (scope_type = 'PROCESS' AND process_stage IS NOT NULL)",
                           name="ck_qc_specifications_scope"),
        sa.CheckConstraint("status = 'DRAFT' OR (approved_by_id IS NOT NULL AND approved_by_id != created_by_id)",
                           name="ck_qc_specifications_segregation"),
    )
    for col in ("spec_code", "product_id", "material_id"):
        op.create_index(f"ix_qc_specifications_{col}", "qc_specifications", [col])

    op.create_table(
        "qc_plans",
        _id(),
        sa.Column("plan_code", sa.String(50), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        _fk("product_id", "products.id", "RESTRICT"),
        _fk("material_id", "materials.id", "RESTRICT"),
        sa.Column("status", sa.String(16), nullable=False, server_default="DRAFT"),
        _fk("created_by_id", "users.id", "RESTRICT", nullable=False),
        _fk("approved_by_id", "users.id", "RESTRICT"),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        *_ts(),
        sa.UniqueConstraint("plan_code", "version", name="uq_qc_plans_code_version"),
        sa.CheckConstraint("status IN ('DRAFT', 'ACTIVE', 'RETIRED')", name="ck_qc_plans_status"),
        sa.CheckConstraint("product_id IS NOT NULL OR material_id IS NOT NULL", name="ck_qc_plans_item"),
        sa.CheckConstraint("status = 'DRAFT' OR (approved_by_id IS NOT NULL AND approved_by_id != created_by_id)",
                           name="ck_qc_plans_segregation"),
    )
    for col in ("plan_code", "product_id", "material_id"):
        op.create_index(f"ix_qc_plans_{col}", "qc_plans", [col])

    op.create_table(
        "qc_plan_steps",
        _id(),
        _fk("plan_id", "qc_plans.id", "CASCADE", nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("qc_type", sa.String(20), nullable=False),
        sa.Column("qc_sub_type", sa.String(50)),
        sa.Column("spec_code", sa.String(50)),
        sa.Column("is_mandatory", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("blocks_progression", sa.Boolean(), nullable=False, server_default=sa.true()),
        *_ts(),
        sa.UniqueConstraint("plan_id", "sequence", name="uq_qc_plan_steps_sequence"),
        sa.CheckConstraint("qc_type IN ('INCOMING', 'IN_PROCESS', 'FINISHED_GOODS', 'RETEST')",
                           name="ck_qc_plan_steps_type"),
    )
    op.create_index("ix_qc_plan_steps_plan_id", "qc_plan_steps", ["plan_id"])

    op.create_table(
        "spc_signals",
        _id(),
        _fk("product_id", "products.id", "SET NULL"),
        sa.Column("parameter_name", sa.String(100), nullable=False),
        _fk("test_result_id", "qc_test_results.id", "CASCADE", nullable=False),
        sa.Column("rule", sa.String(40), nullable=False),
        sa.Column("value", sa.Numeric(14, 4), nullable=False),
        sa.Column("center_line", sa.Numeric(14, 4), nullable=False),
        sa.Column("ucl", sa.Numeric(14, 4), nullable=False),
        sa.Column("lcl", sa.Numeric(14, 4), nullable=False),
        _fk("deviation_id", "qc_deviations.id", "SET NULL"),
        _fk("detected_by_id", "users.id", "SET NULL"),
        *_ts(),
        sa.UniqueConstraint("test_result_id", "rule", name="uq_spc_signals_result_rule"),
    )
    op.create_index("ix_spc_signals_product_id", "spc_signals", ["product_id"])
    op.create_index("ix_spc_signals_parameter_name", "spc_signals", ["parameter_name"])

    op.create_table(
        "quality_concessions",
        _id(),
        sa.Column("concession_no", sa.String(50), nullable=False, unique=True),
        _fk("deviation_id", "qc_deviations.id", "RESTRICT", nullable=False),
        _fk("lot_id", "lots.id", "RESTRICT", nullable=False),
        sa.Column("quantity_limit", sa.Numeric(14, 3)),
        sa.Column("uom", sa.String(20)),
        sa.Column("justification", sa.Text(), nullable=False),
        sa.Column("conditions", sa.Text()),
        sa.Column("status", sa.String(16), nullable=False, server_default="PENDING"),
        sa.Column("valid_until", sa.DateTime(timezone=True)),
        _fk("requested_by_id", "users.id", "RESTRICT", nullable=False),
        _fk("decided_by_id", "users.id", "RESTRICT"),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
        sa.Column("decision_notes", sa.Text()),
        *_ts(),
        sa.CheckConstraint("status IN ('PENDING', 'APPROVED', 'REJECTED', 'REVOKED')", name="ck_quality_concessions_status"),
        sa.CheckConstraint("status = 'PENDING' OR (decided_by_id IS NOT NULL AND decided_by_id != requested_by_id)",
                           name="ck_quality_concessions_segregation"),
        sa.CheckConstraint("status != 'APPROVED' OR (valid_until IS NOT NULL AND length(trim(conditions)) > 0)",
                           name="ck_quality_concessions_approved_terms"),
        sa.CheckConstraint("quantity_limit IS NULL OR quantity_limit > 0", name="ck_quality_concessions_qty"),
    )
    op.create_index("ix_quality_concessions_concession_no", "quality_concessions", ["concession_no"])
    op.create_index("ix_quality_concessions_lot_id", "quality_concessions", ["lot_id"])

    op.create_table(
        "quality_cost_entries",
        _id(),
        sa.Column("entry_no", sa.String(50), nullable=False, unique=True),
        sa.Column("category", sa.String(20), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="KES"),
        sa.Column("cost_date", sa.Date(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("risk_level", sa.String(16)),
        _fk("deviation_id", "qc_deviations.id", "SET NULL"),
        _fk("corrective_action_id", "corrective_actions.id", "SET NULL"),
        _fk("recall_id", "recall_headers.id", "SET NULL"),
        _fk("complaint_id", "consumer_complaints.id", "SET NULL"),
        _fk("lot_id", "lots.id", "SET NULL"),
        _fk("supplier_id", "suppliers.id", "SET NULL"),
        _fk("recorded_by_id", "users.id", "SET NULL"),
        *_ts(),
        sa.CheckConstraint("category IN ('PREVENTION', 'APPRAISAL', 'INTERNAL_FAILURE', 'EXTERNAL_FAILURE')",
                           name="ck_quality_cost_entries_category"),
        sa.CheckConstraint("amount > 0", name="ck_quality_cost_entries_amount_positive"),
        sa.CheckConstraint("risk_level IS NULL OR risk_level IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
                           name="ck_quality_cost_entries_risk"),
    )
    for col in ("entry_no", "category", "cost_date"):
        op.create_index(f"ix_quality_cost_entries_{col}", "quality_cost_entries", [col])

    op.create_table(
        "retain_samples",
        _id(),
        sa.Column("sample_no", sa.String(50), nullable=False, unique=True),
        _fk("lot_id", "lots.id", "RESTRICT", nullable=False),
        _fk("product_id", "products.id", "SET NULL"),
        _fk("material_id", "materials.id", "SET NULL"),
        sa.Column("quantity", sa.Numeric(14, 3), nullable=False),
        sa.Column("quantity_remaining", sa.Numeric(14, 3), nullable=False),
        sa.Column("uom", sa.String(20), nullable=False),
        sa.Column("storage_location", sa.String(200), nullable=False),
        sa.Column("storage_condition", sa.String(200)),
        sa.Column("collected_on", sa.Date(), nullable=False),
        sa.Column("retain_until", sa.Date(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="STORED"),
        _fk("created_by_id", "users.id", "SET NULL"),
        *_ts(),
        sa.CheckConstraint("quantity > 0", name="ck_retain_samples_qty_positive"),
        sa.CheckConstraint("quantity_remaining >= 0 AND quantity_remaining <= quantity", name="ck_retain_samples_remaining"),
        sa.CheckConstraint("status IN ('STORED', 'DEPLETED', 'DISPOSED')", name="ck_retain_samples_status"),
        sa.CheckConstraint("retain_until >= collected_on", name="ck_retain_samples_window"),
    )
    for col in ("sample_no", "lot_id", "retain_until"):
        op.create_index(f"ix_retain_samples_{col}", "retain_samples", [col])

    op.create_table(
        "retain_sample_movements",
        _id(),
        _fk("retain_sample_id", "retain_samples.id", "CASCADE", nullable=False),
        sa.Column("movement_type", sa.String(10), nullable=False),
        sa.Column("quantity", sa.Numeric(14, 3), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        _fk("performed_by_id", "users.id", "SET NULL"),
        *_ts(),
        sa.CheckConstraint("movement_type IN ('WITHDRAW', 'DISPOSE')", name="ck_retain_sample_movements_type"),
        sa.CheckConstraint("quantity >= 0", name="ck_retain_sample_movements_qty"),
    )
    op.create_index("ix_retain_sample_movements_retain_sample_id", "retain_sample_movements", ["retain_sample_id"])

    # Columns on existing tables
    op.add_column("qc_template_parameters", _fk("test_method_id", "qc_test_methods.id", "SET NULL"))
    op.create_index("ix_qc_template_parameters_test_method_id", "qc_template_parameters", ["test_method_id"])
    op.add_column("qc_test_results", _fk("test_method_id", "qc_test_methods.id", "SET NULL"))
    op.create_index("ix_qc_test_results_test_method_id", "qc_test_results", ["test_method_id"])
    op.add_column("qc_test_results", _fk("instrument_calibration_id", "instrument_calibrations.id", "SET NULL"))
    op.create_index("ix_qc_test_results_instrument_calibration_id", "qc_test_results", ["instrument_calibration_id"])
    op.add_column("qms_audit_checklists", sa.Column("closed_at", sa.DateTime(timezone=True)))
    op.add_column("qms_audit_checklists", _fk("closed_by_id", "users.id", "SET NULL"))
    op.add_column("qms_audit_checklists", _fk("corrective_action_id", "corrective_actions.id", "SET NULL"))

    # NOT VALID: enforce for new/updated rows without failing on legacy plans.
    # Skipped when the constraint already exists (fresh databases get it from the squashed baseline).
    for name, check in (
        ("ck_aql_sampling_plans_sample_positive", "sample_size > 0"),
        ("ck_aql_sampling_plans_ac_re", "acceptance_number >= 0 AND rejection_number > acceptance_number"),
        ("ck_aql_sampling_plans_lot_range",
         "lot_size_min >= 1 AND (lot_size_max IS NULL OR lot_size_max >= lot_size_min)"),
    ):
        op.execute(
            f"DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = '{name}') THEN "
            f"ALTER TABLE aql_sampling_plans ADD CONSTRAINT {name} CHECK ({check}) NOT VALID; END IF; END $$"
        )


def downgrade() -> None:
    for name in ("ck_aql_sampling_plans_lot_range", "ck_aql_sampling_plans_ac_re", "ck_aql_sampling_plans_sample_positive"):
        op.drop_constraint(name, "aql_sampling_plans", type_="check")
    op.drop_column("qms_audit_checklists", "corrective_action_id")
    op.drop_column("qms_audit_checklists", "closed_by_id")
    op.drop_column("qms_audit_checklists", "closed_at")
    op.drop_index("ix_qc_test_results_instrument_calibration_id", table_name="qc_test_results")
    op.drop_column("qc_test_results", "instrument_calibration_id")
    op.drop_index("ix_qc_test_results_test_method_id", table_name="qc_test_results")
    op.drop_column("qc_test_results", "test_method_id")
    op.drop_index("ix_qc_template_parameters_test_method_id", table_name="qc_template_parameters")
    op.drop_column("qc_template_parameters", "test_method_id")
    for table in ("retain_sample_movements", "retain_samples", "quality_cost_entries", "quality_concessions",
                  "spc_signals", "qc_plan_steps", "qc_plans", "qc_specifications",
                  "quality_change_requests", "qc_test_methods"):
        op.drop_table(table)

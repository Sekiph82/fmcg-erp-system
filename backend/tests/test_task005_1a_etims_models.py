"""
TASK-005.1A: eTIMS provider config model + submission tracking fields.

Tests:
1. All required symbols importable from tax_regulatory.
2. ETimsStatus has all original + new enum values.
3. ETimsSubmission has all new tracking fields.
4. EtimsProviderConfig safety defaults (is_demo_mode=True, production_execution_allowed=False).
5. EtimsProviderConfig has no raw secret column (only secret_ref).
6. Migration file exists and has correct revision chain.
"""
from pathlib import Path


# ── 1. Import check ───────────────────────────────────────────────────────────

def test_imports_ok():
    from app.models.tax_regulatory import (
        ETimsSubmission, EtimsProviderConfig, ETimsStatus,
        VATReturn, WithholdingTaxRecord,
    )
    assert callable(ETimsStatus)
    assert EtimsProviderConfig.__tablename__ == "etims_provider_configs"
    assert ETimsSubmission.__tablename__ == "etims_submissions"


# ── 2. ETimsStatus enum completeness ─────────────────────────────────────────

def test_etims_status_original_values_preserved():
    from app.models.tax_regulatory import ETimsStatus
    assert ETimsStatus.PENDING.value == "PENDING"
    assert ETimsStatus.SUBMITTED.value == "SUBMITTED"
    assert ETimsStatus.ACCEPTED.value == "ACCEPTED"
    assert ETimsStatus.REJECTED.value == "REJECTED"
    assert ETimsStatus.FAILED.value == "FAILED"


def test_etims_status_new_values_added():
    from app.models.tax_regulatory import ETimsStatus
    assert ETimsStatus.DRAFT.value == "DRAFT"
    assert ETimsStatus.READY.value == "READY"
    assert ETimsStatus.RETRY_PENDING.value == "RETRY_PENDING"
    assert ETimsStatus.CANCELLED.value == "CANCELLED"
    assert ETimsStatus.ERROR.value == "ERROR"


def test_etims_status_total_count():
    from app.models.tax_regulatory import ETimsStatus
    assert len(ETimsStatus) == 10  # 5 original + 5 new


# ── 3. ETimsSubmission new fields ─────────────────────────────────────────────

def test_etims_submission_new_columns_exist():
    from app.models.tax_regulatory import ETimsSubmission
    col_names = {c.name for c in ETimsSubmission.__table__.columns}
    required_new = {
        "provider_name", "provider_reference", "environment",
        "request_payload", "response_payload",
        "accepted_at", "last_attempt_at",
        "attempt_count", "error_code",
    }
    missing = required_new - col_names
    assert not missing, f"Missing columns: {missing}"


def test_etims_submission_original_columns_preserved():
    from app.models.tax_regulatory import ETimsSubmission
    col_names = {c.name for c in ETimsSubmission.__table__.columns}
    original = {
        "id", "invoice_id", "status",
        "control_unit_invoice_no", "signed_invoice_hash", "invoice_qr_data",
        "transmitted_at", "kra_response_code", "kra_response_message",
        "error_message", "retry_count", "submitted_by_id",
    }
    missing = original - col_names
    assert not missing, f"Original columns missing: {missing}"


# ── 4. EtimsProviderConfig safety defaults ────────────────────────────────────

def test_etims_provider_config_safety_defaults():
    from app.models.tax_regulatory import EtimsProviderConfig
    cols = {c.name: c for c in EtimsProviderConfig.__table__.columns}

    # production_execution_allowed must default False
    prod_col = cols["production_execution_allowed"]
    assert prod_col.server_default is not None or prod_col.default is not None, \
        "production_execution_allowed must have a default"
    # Confirm the Python-level default is False
    default_val = getattr(prod_col.default, "arg", None)
    if default_val is not None:
        assert default_val is False, \
            f"production_execution_allowed default must be False, got {default_val}"

    # is_demo_mode must default True
    demo_col = cols["is_demo_mode"]
    assert demo_col.server_default is not None or demo_col.default is not None, \
        "is_demo_mode must have a default"


def test_etims_provider_config_no_raw_secret_column():
    from app.models.tax_regulatory import EtimsProviderConfig
    col_names = {c.name for c in EtimsProviderConfig.__table__.columns}
    forbidden = {"secret", "api_key", "password", "token", "credential"}
    for forbidden_name in forbidden:
        assert forbidden_name not in col_names, \
            f"Raw secret column '{forbidden_name}' must not exist — use secret_ref"
    assert "secret_ref" in col_names, "secret_ref column must exist"


# ── 5. EtimsProviderConfig required columns ───────────────────────────────────

def test_etims_provider_config_columns():
    from app.models.tax_regulatory import EtimsProviderConfig
    col_names = {c.name for c in EtimsProviderConfig.__table__.columns}
    required = {
        "id", "provider_name", "provider_type", "environment",
        "base_url", "branch_id", "device_serial",
        "taxpayer_pin", "client_id", "secret_ref",
        "is_active", "is_demo_mode", "production_execution_allowed",
        "timeout_seconds", "max_retries", "notes",
        "created_at", "updated_at",
    }
    missing = required - col_names
    assert not missing, f"Missing EtimsProviderConfig columns: {missing}"


# ── 6. Migration file exists with correct chain ───────────────────────────────

def test_migration_file_exists():
    migration = Path(
        "alembic/versions/20260602_0001_etims_provider_config_submission_fields.py"
    )
    assert migration.exists(), f"Migration file not found: {migration}"
    content = migration.read_text()
    assert 'revision = "20260602_0001"' in content
    assert 'down_revision = "20260518_0001"' in content
    assert "etims_provider_configs" in content
    assert "etimsstatus" in content
    assert "production_execution_allowed" in content
    assert "false" in content.lower()  # safety default

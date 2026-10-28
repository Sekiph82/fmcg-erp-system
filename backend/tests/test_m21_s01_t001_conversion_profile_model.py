"""Contract checks for the existing bulk-to-pack conversion profile model."""

from app.models.bom import BOMConversionProfile
from app.schemas.bom import ConversionProfileCreate, ConversionProfileOut


def test_conversion_profile_model_exposes_bulk_to_pack_core():
    columns = BOMConversionProfile.__table__.columns
    required = {
        "profile_code",
        "profile_name",
        "source_product_id",
        "target_product_id",
        "theoretical_conversion_ratio",
        "standard_fill_volume",
        "fill_volume_uom",
        "density_g_per_ml",
        "linked_packaging_bom_id",
        "is_active",
    }

    assert required <= set(columns.keys())
    assert columns["source_product_id"].foreign_keys
    assert columns["target_product_id"].foreign_keys
    assert columns["linked_packaging_bom_id"].foreign_keys
    assert columns["profile_code"].unique is True

    create_fields = set(ConversionProfileCreate.model_fields)
    output_fields = set(ConversionProfileOut.model_fields)
    assert required - {"profile_code", "is_active"} <= create_fields
    assert required <= output_fields

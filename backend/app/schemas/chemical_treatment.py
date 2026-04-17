"""
Pydantic schemas for Chemical Water Treatment module.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, field_validator, model_validator


# ── Chemical Master ────────────────────────────────────────────────────────────

class WaterTreatmentChemicalBase(BaseModel):
    chemical_code:    str
    chemical_name:    str
    chemical_category: str
    description:      Optional[str]  = None
    supplier_id:      Optional[UUID] = None
    stock_uom:        str
    dosing_uom:       str
    unit_cost:        Optional[Decimal] = None
    target_dose_min:  Optional[Decimal] = None
    target_dose_max:  Optional[Decimal] = None
    low_stock_threshold: Optional[Decimal] = None
    material_id:      Optional[UUID] = None
    is_active:        bool = True
    notes:            Optional[str]  = None

    @field_validator("chemical_category")
    @classmethod
    def _chk_category(cls, v: str) -> str:
        valid = {
            "BOILER_TREATMENT", "OXYGEN_SCAVENGER", "ANTISCALANT",
            "CORROSION_INHIBITOR", "BIOCIDE", "COAGULANT", "FLOCCULANT",
            "PH_ADJUSTER", "NEUTRALIZER", "DEFOAMER", "CHLORINE",
            "DECHLORINATION", "BIO_NUTRIENT", "OTHER",
        }
        if v.upper() not in valid:
            raise ValueError(f"chemical_category must be one of {sorted(valid)}")
        return v.upper()


class WaterTreatmentChemicalCreate(WaterTreatmentChemicalBase):
    pass


class WaterTreatmentChemicalUpdate(BaseModel):
    chemical_name:    Optional[str]     = None
    chemical_category: Optional[str]    = None
    description:      Optional[str]     = None
    supplier_id:      Optional[UUID]    = None
    stock_uom:        Optional[str]     = None
    dosing_uom:       Optional[str]     = None
    unit_cost:        Optional[Decimal] = None
    target_dose_min:  Optional[Decimal] = None
    target_dose_max:  Optional[Decimal] = None
    low_stock_threshold: Optional[Decimal] = None
    material_id:      Optional[UUID]    = None
    is_active:        Optional[bool]    = None
    notes:            Optional[str]     = None


class WaterTreatmentChemicalRead(WaterTreatmentChemicalBase):
    id:            UUID
    supplier_name: Optional[str] = None
    created_at:    Optional[datetime] = None

    model_config = {"from_attributes": True}


# ── Treatment Records ──────────────────────────────────────────────────────────

class TreatmentRecordCreate(BaseModel):
    asset_id:          UUID
    record_datetime:   datetime
    date:              Optional[date]  = None
    treatment_type:    str

    chemical_id:       Optional[UUID]  = None
    chemical_code:     Optional[str]   = None
    chemical_name:     str
    chemical_category: Optional[str]   = None

    treatment_area:    Optional[str]   = None
    dosing_point:      Optional[str]   = None

    supplier_id:       Optional[UUID]  = None
    batch_lot_no:      Optional[str]   = None
    unit_cost:         Optional[Decimal] = None

    stock_uom:         Optional[str]   = None
    dosing_uom:        Optional[str]   = None

    opening_stock:     Optional[Decimal] = None
    received_qty:      Optional[Decimal] = Decimal("0")
    consumed_qty:      Optional[Decimal] = Decimal("0")
    closing_stock:     Optional[Decimal] = None

    quantity_dosed:    Decimal
    unit:              str
    target_dose_ppm:   Optional[Decimal] = None
    actual_dose_ppm:   Optional[Decimal] = None
    water_volume_m3:   Optional[Decimal] = None

    manual_or_auto_dose: Optional[str] = "MANUAL"

    related_meter_id:  Optional[UUID]  = None
    material_id:       Optional[UUID]  = None

    water_treated_m3:   Optional[Decimal] = None
    steam_produced_ton: Optional[Decimal] = None

    feed_ph:               Optional[Decimal] = None
    product_ph:            Optional[Decimal] = None
    feed_turbidity_ntu:    Optional[Decimal] = None
    product_turbidity_ntu: Optional[Decimal] = None
    residual_chlorine_ppm: Optional[Decimal] = None
    tds_feed_ppm:          Optional[Decimal] = None
    tds_product_ppm:       Optional[Decimal] = None

    source_method: str = "MANUAL"
    is_anomaly:    bool = False
    anomaly_note:  Optional[str] = None
    overdose_flag: bool = False
    underdose_flag: bool = False
    shift_ref:     Optional[str] = None
    notes:         Optional[str] = None

    @field_validator("treatment_type")
    @classmethod
    def _chk_treatment_type(cls, v: str) -> str:
        valid = {
            "COAGULATION", "FLOCCULATION", "DISINFECTION", "SOFTENING",
            "REVERSE_OSMOSIS", "BIOLOGICAL", "PH_ADJUSTMENT",
            "DECHLORINATION", "FILTRATION", "OTHER",
        }
        if v.upper() not in valid:
            raise ValueError(f"treatment_type must be one of {sorted(valid)}")
        return v.upper()

    @field_validator("manual_or_auto_dose")
    @classmethod
    def _chk_dosing_mode(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if v.upper() not in {"MANUAL", "AUTO"}:
            raise ValueError("manual_or_auto_dose must be MANUAL or AUTO")
        return v.upper()

    @model_validator(mode="after")
    def _auto_fill_date(self) -> "TreatmentRecordCreate":
        if self.date is None and self.record_datetime:
            self.date = self.record_datetime.date()
        return self

    @model_validator(mode="after")
    def _detect_dose_anomaly(self) -> "TreatmentRecordCreate":
        """Auto-set overdose/underdose flags based on target_dose_ppm vs actual_dose_ppm."""
        if self.target_dose_ppm and self.actual_dose_ppm:
            tgt = float(self.target_dose_ppm)
            act = float(self.actual_dose_ppm)
            if act > tgt * 1.20:
                self.overdose_flag = True
            elif act < tgt * 0.80:
                self.underdose_flag = True
        return self


class TreatmentRecordUpdate(BaseModel):
    record_datetime:   Optional[datetime] = None
    date:              Optional[date]     = None
    treatment_type:    Optional[str]      = None

    chemical_id:       Optional[UUID]    = None
    chemical_code:     Optional[str]     = None
    chemical_name:     Optional[str]     = None
    chemical_category: Optional[str]     = None

    treatment_area:    Optional[str]     = None
    dosing_point:      Optional[str]     = None

    supplier_id:       Optional[UUID]    = None
    batch_lot_no:      Optional[str]     = None
    unit_cost:         Optional[Decimal] = None

    stock_uom:         Optional[str]     = None
    dosing_uom:        Optional[str]     = None

    opening_stock:     Optional[Decimal] = None
    received_qty:      Optional[Decimal] = None
    consumed_qty:      Optional[Decimal] = None
    closing_stock:     Optional[Decimal] = None

    quantity_dosed:    Optional[Decimal] = None
    unit:              Optional[str]     = None
    target_dose_ppm:   Optional[Decimal] = None
    actual_dose_ppm:   Optional[Decimal] = None
    water_volume_m3:   Optional[Decimal] = None

    manual_or_auto_dose: Optional[str]  = None

    related_meter_id:  Optional[UUID]   = None

    water_treated_m3:   Optional[Decimal] = None
    steam_produced_ton: Optional[Decimal] = None

    feed_ph:               Optional[Decimal] = None
    product_ph:            Optional[Decimal] = None
    feed_turbidity_ntu:    Optional[Decimal] = None
    product_turbidity_ntu: Optional[Decimal] = None
    residual_chlorine_ppm: Optional[Decimal] = None
    tds_feed_ppm:          Optional[Decimal] = None
    tds_product_ppm:       Optional[Decimal] = None

    source_method: Optional[str]  = None
    is_anomaly:    Optional[bool] = None
    anomaly_note:  Optional[str]  = None
    overdose_flag: Optional[bool] = None
    underdose_flag: Optional[bool] = None
    shift_ref:     Optional[str]  = None
    notes:         Optional[str]  = None


class TreatmentRecordRead(BaseModel):
    id:              UUID
    record_no:       str
    asset_id:        UUID
    asset_name:      Optional[str] = None
    asset_no:        Optional[str] = None

    record_datetime: datetime
    date:            Optional[date]   = None
    treatment_type:  str

    chemical_id:      Optional[UUID] = None
    chemical_code:    Optional[str]  = None
    chemical_name:    str
    chemical_category: Optional[str] = None

    treatment_area:   Optional[str] = None
    dosing_point:     Optional[str] = None

    supplier_id:      Optional[UUID] = None
    supplier_name:    Optional[str]  = None
    batch_lot_no:     Optional[str]  = None
    unit_cost:        Optional[Decimal] = None

    stock_uom:        Optional[str] = None
    dosing_uom:       Optional[str] = None

    opening_stock:    Optional[Decimal] = None
    received_qty:     Optional[Decimal] = None
    consumed_qty:     Optional[Decimal] = None
    closing_stock:    Optional[Decimal] = None

    quantity_dosed:   Decimal
    unit:             str
    target_dose_ppm:  Optional[Decimal] = None
    actual_dose_ppm:  Optional[Decimal] = None
    water_volume_m3:  Optional[Decimal] = None

    manual_or_auto_dose: Optional[str] = None

    related_meter_id: Optional[UUID] = None

    water_treated_m3:   Optional[Decimal] = None
    steam_produced_ton: Optional[Decimal] = None

    feed_ph:               Optional[Decimal] = None
    product_ph:            Optional[Decimal] = None
    feed_turbidity_ntu:    Optional[Decimal] = None
    product_turbidity_ntu: Optional[Decimal] = None
    residual_chlorine_ppm: Optional[Decimal] = None
    tds_feed_ppm:          Optional[Decimal] = None
    tds_product_ppm:       Optional[Decimal] = None

    source_method:  str
    is_anomaly:     bool
    anomaly_note:   Optional[str] = None
    overdose_flag:  bool
    underdose_flag: bool
    shift_ref:      Optional[str] = None
    inventory_synced: bool = False
    notes:          Optional[str] = None

    created_at:     Optional[datetime] = None
    updated_at:     Optional[datetime] = None

    model_config = {"from_attributes": True}


# ── KPIs ──────────────────────────────────────────────────────────────────────

class ChemicalKPIs(BaseModel):
    date_from:                Optional[date]    = None
    date_to:                  Optional[date]    = None
    total_records:            int               = 0
    total_quantity_dosed:     Optional[Decimal] = None
    total_consumed_qty:       Optional[Decimal] = None
    total_received_qty:       Optional[Decimal] = None
    total_cost:               Optional[Decimal] = None
    chemical_per_m3_water:    Optional[Decimal] = None   # dosing unit per m3 treated water
    chemical_per_ton_steam:   Optional[Decimal] = None   # dosing unit per ton steam
    overdose_count:           int               = 0
    underdose_count:          int               = 0
    anomaly_count:            int               = 0
    low_stock_chemicals:      List[str]         = []


# ── Trend point ───────────────────────────────────────────────────────────────

class ChemicalTrendPoint(BaseModel):
    day:             str
    quantity_dosed:  Optional[Decimal] = None
    consumed_qty:    Optional[Decimal] = None
    overdose_count:  int = 0
    underdose_count: int = 0


# ── Dropdown ─────────────────────────────────────────────────────────────────

class ChemicalOption(BaseModel):
    id:               UUID
    chemical_code:    str
    chemical_name:    str
    chemical_category: str
    stock_uom:        str
    dosing_uom:       str
    unit_cost:        Optional[Decimal] = None

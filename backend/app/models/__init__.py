from app.models.ai import (
    AIRequest, AIPrediction, AIRecommendation, AIFormulation, AIScenario,
    AIRequestStatus, AIRequestType, AIProvider as AIProviderEnum,
)
from app.models.role import Role, Permission, role_permission
from app.models.user import User, user_role
from app.models.audit_log import AuditLog
from app.models.master import Product, Material, Supplier, Warehouse
from app.models.inventory import Stock, Lot, StockMovement
from app.models.recipe import Recipe, RecipeItem, ProcessParameter
from app.models.production import (
    ProductionPlan, ProductionPlanLine, ProductionOrder,
    MaterialConsumption, FinishedGoodsReceipt, DowntimeLog,
)
from app.models.wms import WarehouseZone, StorageLocation, StockCount, StockCountLine
from app.models.procurement import (
    PurchaseRequisition, PRLine, PurchaseOrder, POLine,
    GoodsReceipt, GRNLine, ImportShipment, SupplierEvaluation, SupplierPayment,
)
from app.models.quality import QCParameter, QCInspection, QCTestResult

# ── Distribution layer (must load before sales) ───────────────────────────────
from app.models.distribution import Distributor, DistributorPricingTier
from app.models.field_sales import SalesRep, SalesRoute, RouteStop, DailyTarget, VisitLog

# ── Sales ─────────────────────────────────────────────────────────────────────
from app.models.sales import (
    Customer, SalesOrder, SOLine, Shipment, ShipmentLine, Invoice, InvoiceLine, Payment,
    MpesaTransaction,
)

# ── Delivery & Returns ─────────────────────────────────────────────────────────
from app.models.delivery import DeliveryTrip, TripOrder, ProofOfDelivery
from app.models.returns_mgmt import ReturnOrder, ReturnLine

# ── Pricing ───────────────────────────────────────────────────────────────────
from app.models.pricing import PricingRule, Promotion, PromotionProduct

from app.models.finance import (
    ChartOfAccount, JournalEntry, JournalLine,
    CashAccount, CashTransaction, MpesaReconciliation,
    ProductCost, ProductionCostEntry,
    Budget, BudgetLine,
    PurchaseInvoice, PurchaseInvoiceLine, PurchasePayment,
    PurchaseInvoiceStatus,
)
from app.models.maintenance import (
    Asset, PMPlan, PMWorkOrder, BreakdownRecord, SparePart, SparePartUsage,
)
from app.models.logistics import (
    InternationalShipment, ShipmentContainer, ShipmentPOLink,
    CustomsDocument, CustomsClearance, ArrivalNotification,
)
from app.models.tax_regulatory import (
    CountryTaxConfig, TaxCategory, TaxRule,
    ProductTaxMapping, RegulatoryFlag, TransactionTax,
)
from app.models.integrations import (
    IntegrationConfig, IntegrationLog, IntegrationMpesaTransaction,
    CrmCustomerMapping, EcommerceOrderMapping, EcommerceProductMapping,
    MachineEvent, BarcodeLabel,
)
from app.models.operational_log import OperationalLog, MpesaStatusHistory

# ── Documents ─────────────────────────────────────────────────────────────────
from app.models.documents import Document, DocumentCategory, DocumentStatus

# ── Import History ─────────────────────────────────────────────────────────────
from app.models.import_history import ImportHistory, ImportStatus

# ── Marketing ─────────────────────────────────────────────────────────────────
from app.models.marketing import (
    # Enums
    CampaignType, CampaignStatus,
    PromotionType as MktPromotionType, PromotionStatus,
    DiscountType, SegmentType, RelationshipStatus, LoyaltyStatus,
    AcquisitionSource, VisitType, TradeSpendType, BrandSpendCategory,
    SurveyType, InfluencerPlatform, InfluencerStatus, ContentType,
    SentimentScore, StorePlatform, StoreStatus, AdPlatform, OptimizerStatus,
    # Models
    Campaign,
    MarketingPromotion as MktPromotion,
    CustomerSegment, CRMProfile, CustomerInteraction,
    CustomerVisit, TradeSpend, BrandSpend, Survey, Influencer,
    InfluencerCampaignLink, InfluencerAttribution, SocialMediaActivity,
    Store as MktStore,
    StorePerformance, ProductChannelPerformance, ChannelStock,
    AdPerformance, ReturnAnalytics, OptimizerRun,
)

# ── HR ────────────────────────────────────────────────────────────────────────
from app.models.hr import (
    Employee, ShiftTemplate, EmployeeShiftAssignment,
    AttendanceRecord, LeaveRequest, LeaveBalance,
    PayrollPeriod, PayrollLine,
    EmployeeStatus, AttendanceStatus, LeaveType, ApprovalStatus,
    PaymentMethod, PayrollStatus,
)

# ── Production AI Intelligence ────────────────────────────────────────────────
from app.models.production_ai import (
    AgentType, AnomalySeverity, AnomalyType, SuggestionType, SuggestionStatus,
    ProductionPrediction, ProductionAnomaly, ProductionSuggestion, ProductionAIMetrics,
)

# ── Production Advanced ───────────────────────────────────────────────────────
from app.models.production_advanced import (
    WorkCenter, WorkCenterType, WorkCenterStatus,
    Routing, RoutingStep,
    WorkOrder, WorkOrderStatus,
    Shift, ProductionSchedule, ScheduleStatus, SchedulePriority,
    TimeTracking, TimeTrackingCategory,
    DowntimeEvent, DowntimeCategory,
    AdvQCInspection, AdvQCResult, QCInspectionType, AdvQCStatus,
    WasteRecord, WasteType, WasteCategory,
    BatchLot, BatchLotStatus,
    LaborLog, LaborActivityType,
    OEERecord,
)

# ── Utility Management ────────────────────────────────────────────────────────
from app.models.utility_management import (
    # Enums
    UtilityType, SourceMethod, DataQuality,
    UtilityAssetStatus, LifecycleStatus, CriticalityLevel,
    DeviceType, ReadingType, ReadingSource, ReadingFrequency, ValidatedStatus,
    TariffType, TxReferenceType,
    AlarmSeverity, AlarmStatus, AlarmOperator,
    AlarmDetectionType, AlarmCategory,
    AllocationMethod, BillStatus,
    SoftenerStatus, BoilerStatus, CompressorStatus,
    TreatmentType, WastewaterProcess, ComplianceStatus,
    ChemicalCategory, DosingMode,
    # Master data
    WaterTreatmentChemical,
    UtilityAssetCategory,
    UtilityAsset,
    UtilityDevice,
    UtilityTariff,
    UtilityAlarmRule,
    # Transactional / Operational
    UtilityReading,
    UtilityTransaction,
    SoftWaterRecord,
    BoilerSteamRecord,
    CompressorRecord,
    SolarRecord,
    TreatmentChemicalRecord,
    WastewaterRecord,
    UtilityBill,
    UtilityCostAllocation,
    UtilityAlarmEvent,
    MachineUtilityMapping,
)

# ── MRP & Demand Forecasting ──────────────────────────────────────────────────
from app.models.mrp import (
    ForecastModelType, PeriodType, ForecastStatus,
    MRPRunStatus, MRPTrigger, SuggestionType, SuggestionStatus,
    DemandForecast, DemandForecastLine,
    MRPRun, MRPResult, MRPSuggestion,
)

# ── Advanced BOM / Formula / Packaging BOM ────────────────────────────────────
from app.models.bom import (
    BOMType, BOMLifecycle, ComponentType, BasisType,
    SubstitutionPolicy, ItemLinkType, LossCategory,
    BOMAgentType, BOMRecStatus,
    AdvancedBOM, AdvancedBOMLine,
    BOMSubstituteGroup, BOMSubstitute,
    BOMConversionProfile, BOMYieldConfig, BOMAIRec,
)

# ── Shop Floor Execution System ───────────────────────────────────────────────
from app.models.shop_floor import (
    SFSessionStatus, WOEventType, SFDowntimeCat, SFImpactLevel,
    OverrideType, SFAIAgentType, SFAIRecStatus, SFLiveStatus,
    SFSession, WOActivityLog, SFDowntimeLog,
    ShiftHandover, SupervisorOverride, SFAIRec,
)

# ── Production Execution System ───────────────────────────────────────────────
from app.models.production_execution import (
    ProdExecStatus, WOExecStatus, ExecSourceType,
    ExecMatStatus, ExecScrapCategory, ExecSplitMergeType,
    ExecAIAgentType, ExecAIRecStatus,
    ProdExecOrder, ExecWorkOrder, ExecOrderMaterial,
    BatchGenealogy, ExecSplitMergeLog, ExecAIRec,
)

# ── Advanced Production Planning Suite ───────────────────────────────────────
from app.models.planning import (
    ScenarioStatus, ScenarioMode, OpQueueStatus, CapacitySlotType,
    BottleneckSeverity, PlanningAgentType, PlanningRecStatus, SimulationStatus,
    PlanningScenario, ResourceCalendar, OperationQueue, CapacityLoadSnapshot,
    ChangeoverMatrix, PlanningBottleneck, PlanningAIRec, PlanningSimulation,
)

# ── MPS (Master Production Scheduling) ───────────────────────────────────────
from app.models.mps import (
    MPSPlanningMode, MPSCapacityMode, MPSStatus, MPSFeasibilityStatus,
    MPSAgentType, MPSRecType, MPSRecStatus, WhatIfStatus, MPSChangeType,
    MPSPlan, MPSLine, MPSCampaign, MPSCapacitySlot,
    MPSWhatIfScenario, MPSAIRecommendation,
)

# ── Machine + Operator Intelligence ──────────────────────────────────────────
from app.models.machine_operator import (
    MachineStatus, MachineFamily, SkillLevel, CertStatus,
    AssignmentType, RuntimeActivity, DowntimeClass, LaborActivity,
    ReviewType, MOAIAgentType, MOAIRecStatus,
    Machine, OperatorProfile, ProductionTeam, TeamMember,
    OperatorSkillCert, WorkOrderAssignment, AssignmentHistory,
    MachineRuntimeLog, LaborTimeLog, MachinePerformanceSnapshot,
    DowntimeIntelligence, SupervisorReview, MOAIRecommendation,
)

# ── Material Flow Engine ──────────────────────────────────────────────────────
from app.models.material_flow import (
    FlowType, FlowStatus, FlowMode, StageType, QualityStatus,
    MovementReason, ReservationStatus, TankStatus, ReconciliationStatus,
    MFAIAgentType, MFAIRecStatus,
    FlowStage, MaterialFlowTransaction, MaterialFlowLine,
    MaterialReservation, MaterialReservationLine,
    ProductionConsumption, PreparedLot, TankOccupancy,
    BatchReconciliation, BatchReconciliationLine, MFAIRecommendation,
)

__all__ = [
    # AI
    "AIRequest", "AIPrediction", "AIRecommendation", "AIFormulation", "AIScenario",
    "AIRequestStatus", "AIRequestType", "AIProviderEnum",
    # Core
    "Role", "Permission", "role_permission",
    "User", "user_role",
    "AuditLog",
    "Product", "Material", "Supplier", "Warehouse",
    "Stock", "Lot", "StockMovement",
    "Recipe", "RecipeItem", "ProcessParameter",
    "ProductionPlan", "ProductionPlanLine", "ProductionOrder",
    "MaterialConsumption", "FinishedGoodsReceipt", "DowntimeLog",
    "WarehouseZone", "StorageLocation", "StockCount", "StockCountLine",
    "PurchaseRequisition", "PRLine", "PurchaseOrder", "POLine",
    "GoodsReceipt", "GRNLine", "ImportShipment", "SupplierEvaluation", "SupplierPayment",
    "QCParameter", "QCInspection", "QCTestResult",
    # Distribution
    "Distributor", "DistributorPricingTier",
    "SalesRep", "SalesRoute", "RouteStop", "DailyTarget", "VisitLog",
    # Sales
    "Customer", "SalesOrder", "SOLine", "Shipment", "ShipmentLine",
    "Invoice", "InvoiceLine", "Payment", "MpesaTransaction",
    # Delivery & Returns
    "DeliveryTrip", "TripOrder", "ProofOfDelivery",
    "ReturnOrder", "ReturnLine",
    # Pricing
    "PricingRule", "Promotion", "PromotionProduct",
    # Finance
    "ChartOfAccount", "JournalEntry", "JournalLine",
    "CashAccount", "CashTransaction", "MpesaReconciliation",
    "ProductCost", "ProductionCostEntry",
    "Budget", "BudgetLine",
    "PurchaseInvoice", "PurchaseInvoiceLine", "PurchasePayment",
    "PurchaseInvoiceStatus",
    "Asset", "PMPlan", "PMWorkOrder", "BreakdownRecord", "SparePart", "SparePartUsage",
    "InternationalShipment", "ShipmentContainer", "ShipmentPOLink",
    "CustomsDocument", "CustomsClearance", "ArrivalNotification",
    "CountryTaxConfig", "TaxCategory", "TaxRule",
    "ProductTaxMapping", "RegulatoryFlag", "TransactionTax",
    "IntegrationConfig", "IntegrationLog", "IntegrationMpesaTransaction",
    "CrmCustomerMapping", "EcommerceOrderMapping", "EcommerceProductMapping",
    "MachineEvent", "BarcodeLabel",
    "OperationalLog", "MpesaStatusHistory",
    # Import History
    "ImportHistory", "ImportStatus",
    # Documents
    "Document", "DocumentCategory", "DocumentStatus",
    # HR
    "Employee", "ShiftTemplate", "EmployeeShiftAssignment",
    "AttendanceRecord", "LeaveRequest", "LeaveBalance",
    "PayrollPeriod", "PayrollLine",
    "EmployeeStatus", "AttendanceStatus", "LeaveType", "ApprovalStatus",
    "PaymentMethod", "PayrollStatus",
    # Marketing
    "Campaign", "MktPromotion", "CustomerSegment", "CRMProfile",
    "CustomerInteraction", "CustomerVisit", "TradeSpend", "BrandSpend",
    "Survey", "Influencer", "InfluencerCampaignLink", "InfluencerAttribution",
    "SocialMediaActivity", "MktStore", "StorePerformance",
    "ProductChannelPerformance", "ChannelStock", "AdPerformance",
    "ReturnAnalytics", "OptimizerRun",
    # Utility Management — enums
    "UtilityType", "SourceMethod", "DataQuality",
    "UtilityAssetStatus", "LifecycleStatus", "CriticalityLevel",
    "DeviceType", "ReadingType", "ReadingSource", "ReadingFrequency", "ValidatedStatus",
    "TariffType", "TxReferenceType",
    "AlarmSeverity", "AlarmStatus", "AlarmOperator",
    "AlarmDetectionType", "AlarmCategory",
    "AllocationMethod", "BillStatus",
    "SoftenerStatus", "BoilerStatus", "CompressorStatus",
    "TreatmentType", "WastewaterProcess", "ComplianceStatus",
    "ChemicalCategory", "DosingMode",
    # Utility Management — master
    "WaterTreatmentChemical",
    "UtilityAssetCategory", "UtilityAsset", "UtilityDevice",
    "UtilityTariff", "UtilityAlarmRule",
    # Utility Management — transactional
    "UtilityReading", "UtilityTransaction",
    "SoftWaterRecord", "BoilerSteamRecord", "CompressorRecord",
    "SolarRecord", "TreatmentChemicalRecord", "WastewaterRecord",
    "UtilityBill", "UtilityCostAllocation",
    "UtilityAlarmEvent", "MachineUtilityMapping",
    # MRP & Demand Forecasting
    "ForecastModelType", "PeriodType", "ForecastStatus",
    "MRPRunStatus", "MRPTrigger", "SuggestionType", "SuggestionStatus",
    "DemandForecast", "DemandForecastLine",
    "MRPRun", "MRPResult", "MRPSuggestion",
    # Shop Floor
    "SFSessionStatus", "WOEventType", "SFDowntimeCat", "SFImpactLevel",
    "OverrideType", "SFAIAgentType", "SFAIRecStatus", "SFLiveStatus",
    "SFSession", "WOActivityLog", "SFDowntimeLog",
    "ShiftHandover", "SupervisorOverride", "SFAIRec",
    # Production Execution
    "ProdExecStatus", "WOExecStatus", "ExecSourceType",
    "ExecMatStatus", "ExecScrapCategory", "ExecSplitMergeType",
    "ExecAIAgentType", "ExecAIRecStatus",
    "ProdExecOrder", "ExecWorkOrder", "ExecOrderMaterial",
    "BatchGenealogy", "ExecSplitMergeLog", "ExecAIRec",
    # Advanced BOM
    "BOMType", "BOMLifecycle", "ComponentType", "BasisType",
    "SubstitutionPolicy", "ItemLinkType", "LossCategory",
    "BOMAgentType", "BOMRecStatus",
    "AdvancedBOM", "AdvancedBOMLine",
    "BOMSubstituteGroup", "BOMSubstitute",
    "BOMConversionProfile", "BOMYieldConfig", "BOMAIRec",
    # Advanced Planning
    "ScenarioStatus", "ScenarioMode", "OpQueueStatus", "CapacitySlotType",
    "BottleneckSeverity", "PlanningAgentType", "PlanningRecStatus", "SimulationStatus",
    "PlanningScenario", "ResourceCalendar", "OperationQueue", "CapacityLoadSnapshot",
    "ChangeoverMatrix", "PlanningBottleneck", "PlanningAIRec", "PlanningSimulation",
    # MPS
    "MPSPlanningMode", "MPSCapacityMode", "MPSStatus", "MPSFeasibilityStatus",
    "MPSAgentType", "MPSRecType", "MPSRecStatus", "WhatIfStatus", "MPSChangeType",
    "MPSPlan", "MPSLine", "MPSCampaign", "MPSCapacitySlot",
    "MPSWhatIfScenario", "MPSAIRecommendation",
    # Machine + Operator Intelligence
    "MachineStatus", "MachineFamily", "SkillLevel", "CertStatus",
    "AssignmentType", "RuntimeActivity", "DowntimeClass", "LaborActivity",
    "ReviewType", "MOAIAgentType", "MOAIRecStatus",
    "Machine", "OperatorProfile", "ProductionTeam", "TeamMember",
    "OperatorSkillCert", "WorkOrderAssignment", "AssignmentHistory",
    "MachineRuntimeLog", "LaborTimeLog", "MachinePerformanceSnapshot",
    "DowntimeIntelligence", "SupervisorReview", "MOAIRecommendation",
    # Material Flow Engine
    "FlowType", "FlowStatus", "FlowMode", "StageType", "QualityStatus",
    "MovementReason", "ReservationStatus", "TankStatus", "ReconciliationStatus",
    "MFAIAgentType", "MFAIRecStatus",
    "FlowStage", "MaterialFlowTransaction", "MaterialFlowLine",
    "MaterialReservation", "MaterialReservationLine",
    "ProductionConsumption", "PreparedLot", "TankOccupancy",
    "BatchReconciliation", "BatchReconciliationLine", "MFAIRecommendation",
]

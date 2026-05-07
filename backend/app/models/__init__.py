from app.models.utilities import (
    ConfigCategory, SystemConfig, UomConversion, NumberSeries, Currency,
)

from app.models.ai import (
    AIRequest, AIPrediction, AIRecommendation, AIFormulation, AIScenario,
    AIRequestStatus, AIRequestType, AIProvider as AIProviderEnum,
)
from app.models.role import Role, Permission, role_permission
from app.models.user import User, user_role
from app.models.audit_log import AuditLog
from app.models.two_factor import User2FASettings, TwoFASession, RecoveryCode, TwoFAMethod, TwoFASessionStatus
from app.models.webhook import (
    EventDefinition, EventLog, Subscription, DeliveryAttempt, InboundEndpoint,
    AuthType, DeliveryStatus, HttpMethod,
)
from app.models.cycle_count import (
    CycleCountPlan, CycleCountTask, CountEntry, CountAdjustment, ABCClassification,
    PlanType, PlanStatus, TaskStatus, ABCClass, AdjustmentStatus,
)
from app.models.fleet import (
    Vehicle, FleetDriver, FleetTrip, FuelLog, MaintenanceRecord, IncidentLog,
    VehicleType, VehicleStatus, FuelType, TripStatus,
    MaintenanceType, IncidentType, IncidentStatus, DriverStatus,
)
from app.models.master import Product, Material, Supplier, Warehouse
from app.models.inventory import Stock, Lot, StockMovement
from app.models.recipe import Recipe, RecipeItem, ProcessParameter
from app.models.production import (
    ProductionPlan, ProductionPlanLine, ProductionOrder,
    MaterialConsumption, FinishedGoodsReceipt, DowntimeLog,
)
from app.models.wms import WarehouseZone, StorageLocation, StockCount, StockCountLine, PutawayRule, PutawayTask, PutawayExecution
from app.models.procurement import (
    PurchaseRequisition, PRLine, PurchaseOrder, POLine,
    GoodsReceipt, GRNLine, ImportShipment, SupplierEvaluation, SupplierPayment,
)
from app.models.quality import (
    QCParameter, QCInspection, QCTestResult,
    QCType, QCStatus, QCDecision, ParameterType,
    QCTemplate, QCTemplateParameter,
    SamplingMethod, HazardType, RiskLevel,
    DeviationStatus, CorrectiveActionStatus, ReleaseStatus,
    QMSAIAgentType, QMSAIRecStatus,
    HazardAnalysis, CriticalControlPoint, CCPMonitoringLog,
    CorrectiveAction, CorrectiveActionStep,
    QCDeviation, LotQualityStatus,
    AllergenValidationRecord, QMSAIRecommendation,
)

# ── Distribution layer (must load before sales) ───────────────────────────────
from app.models.distribution import Distributor, DistributorPricingTier
from app.models.secondary_sales import (
    RetailerMaster, SecondarySalesHeader, SecondarySalesLine, DistributorInventorySnapshot,
)
from app.models.esg import (
    ActivityData, EmissionFactor, EmissionRecord, ResourceMetric, ESGTarget,
)
from app.models.payroll_ke import (
    EmployeePayrollProfile, KeTaxBand, KeStatutoryRate, KeNhifTier,
    PayrollRun, KePayrollLine, Payslip,
)
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

# ── Lot Traceability + Batch Recall Management ───────────────────────────────
from app.models.traceability import (
    TraceEventType, TraceItemStage, GenealogyRelType,
    RecallType, RecallTrigger, RecallSeverity, RecallStatus,
    RecallActionType, RecallActionStatus, RecallRiskStatus,
    TRRecAIAgentType, TRRecAIRecStatus,
    TraceEvent, TraceEventLine, LotGenealogyLink,
    RecallHeader, RecallScopeLine, RecallAction,
    RecallCustomerImpact, RecallReturnRecord, TRRecAIRecommendation,
)

# ── Subcontracting System ─────────────────────────────────────────────────────
from app.models.subcontracting import (
    SCOrderStatus, SCIssueStatus, SCReceiptStatus, SCYieldStatus,
    SCAIAgentType, ScrapReasonCode,
    SubcontractorLocation,
    SubcontractOrder, SubcontractOrderLine,
    SubcontractMaterialIssue, SubcontractMaterialIssueLine,
    SubcontractReceipt, SubcontractReceiptLine,
    SubcontractYieldRecord, SCPerformanceRecord, SCAIRecommendation,
)

# ── Procurement Suggestion Engine ────────────────────────────────────────────
from app.models.procurement_suggestion import (
    PSRunStatus, PSSuggestionStatus, PSUrgencyLevel, PSGroupStatus,
    PSAIAgentType, SupplierItemPriority,
    SupplierItemPrice,
    ProcurementSuggestionRun, ProcurementSuggestionLine,
    ProcurementSuggestionGroup, PSAIRecommendation,
)

# ── 3-Way Invoice Matching ────────────────────────────────────────────────────
from app.models.invoice_match import (
    MatchLineStatus, MatchOverallStatus, MatchReviewAction, DuplicateRisk,
    IMAIAgentType, IMAIRecStatus,
    InvoiceMatchTolerance, InvoiceMatchHeader, InvoiceMatchLine,
    InvoiceMatchGRNLink, DuplicateInvoiceLog, InvoiceMatchReview,
    IMAIRecommendation,
)

# ── Landed Cost Allocation ────────────────────────────────────────────────────
from app.models.landed_cost import (
    LCStatus, LandedCostType, LCAllocationMethod, LCReferenceType,
    LCAIAgentType, LCAIRecStatus,
    LandedCostHeader, LandedCostLine, LandedCostGRNLink,
    LandedCostAllocationLine, LCInventoryAdjustment, LCAIRecommendation,
)

# ── Allergen + Nutrition Management ──────────────────────────────────────────
from app.models.allergen import (
    AllergenCategory, PresenceType, CrossContactRisk, NutrientBasis, NutrientSource,
    LabelBasisType, AllergenChangeType, ANAIAgentType, ANAIRecStatus,
    AllergenMaster, MaterialAllergenProfile, MaterialAllergenLine,
    NutritionProfile, NutritionProfileLine,
    ProductAllergenSummary, ProductNutritionSummary,
    AllergenChangeLog, ProductServingConfig, ANAIRecommendation,
)

# ── GS1 Barcode + Label Printing System ──────────────────────────────────────
from app.models.gs1 import (
    BarcodeType, PackagingLevel, PrintJobStatus, SSCCStatus,
    LabelTemplateStatus, PrintTrigger, GS1AIAgentType, GS1AIRecStatus,
    GS1CompanyConfig, ProductGS1Config, LotBarcodeRecord,
    SSCCPallet, SSCCPalletLot, GS1LabelTemplate, LabelPrintJob,
    LabelPrintJobItem, GS1AIRecommendation,
)

# ── FEFO + Shelf-Life Control ─────────────────────────────────────────────────
from app.models.shelf_life import (
    ShelfLifeStatus, PickingStrategy, ExpiryBlockPolicy, NearExpiryPolicy,
    ShelfLifeCategory, RetestStatus, DispositionAction, DispositionStatus,
    AlertType, AlertSeverity, SLAIAgentType, SLAIRecStatus, StrategyScope,
    CustomerRuleType, FEFOContext,
    ItemShelfLifeConfig, PickingStrategyConfig, CustomerShelfLifeRule,
    LotShelfLifeProfile, RetestRequest, BulkHoldRecord, ShelfLifeAlert,
    DispositionSuggestion, FEFOAuditLog, SLAIRecommendation,
)

# ── Promotional Schemes Auto-Apply ───────────────────────────────────────────
from app.models.promotions import (
    SchemeStatus, SchemeType, TriggerBasis, RewardType,
    PromoApplicationType, PromoImpactType, OverrideStatus,
    PromoAIAgentType, PromoAIRecStatus,
    PromoScheme, PromoEligibility, PromoRuleLine, PromoTierLine,
    SalesOrderPromo, SalesOrderPromoLine, PromoOverrideRequest,
    PromoUsageTally, PromoAIRecommendation,
)

# ── Price List Enhancement ────────────────────────────────────────────────────
from app.models.price_list import (
    PLType, PLStatus, PLDiscountType, PLApprovalAction,
    PLDiscountScope, PLChangeType, PLAIAgentType, PLAIRecStatus,
    PLHeader, PLLine, PLTier, PLAssignment, PLDiscountRule,
    PLApproval, PLChangeHistory, PLAIRecommendation,
)

# ── Dunning / Overdue Collection ─────────────────────────────────────────────
from app.models.dunning import (
    DunningActionType, DunningCaseStatus, DunningActionOutcome,
    PTPStatus, DunningExceptionType, DunningAIAgentType, DunningAIRecStatus,
    DunningPolicy, DunningLevel, DunningTemplate, DunningCase,
    DunningCaseInvoice, DunningActionLog, DunningPTP, DunningException,
    DunningAIRecommendation,
)

# ── Supplier Portal ───────────────────────────────────────────────────────────
from app.models.supplier_portal import (
    SPAccountStatus, SPUserRole, SPActivityType,
    SPPOResponseStatus, SPETAStatus, SPDocUploadType, SPDocReviewStatus,
    SPPaymentVisibility, SPAIAgentType, SPAIRecStatus,
    SPAccount, SPUser, SPPermissionProfile, SPActivityLog,
    SPDocument, SPPOResponse, SPETALog, SPAIRecommendation,
)

# ── Customer / Distributor Portal ─────────────────────────────────────────────
from app.models.portal import (
    PortalAccountType, PortalAccountStatus, PortalUserRole,
    PortalActivityType, PortalClaimType, PortalClaimStatus,
    PortalOrderMode, PortalDraftOrderStatus,
    PortalAIAgentType, PortalAIRecStatus,
    PortalAccount, PortalUser, PortalActivityLog,
    PortalClaim, PortalDraftOrder, PortalDraftOrderLine,
    PortalAIRecommendation,
)

# ── Advanced CRM Pipeline ─────────────────────────────────────────────────────
from app.models.crm import (
    CRMRecordType, CRMAccountType, CRMSourceType, CRMStageType,
    CRMTemperature, CRMStatus, CRMActivityType, CRMActivityResult,
    CRMLossReason, CRMWinReason, CRMAIAgentType, CRMAIRecStatus,
    CRMPipelineStage, CRMRecord, CRMInterestLine, CRMActivity,
    CRMCompetitor, CRMWinLoss, CRMAIRecommendation,
)

# ── Trade Promotion Management (TPM) ─────────────────────────────────────────
from app.models.tpm import (
    TPMPeriodType, TPMPlanStatus, TPMPromotionType, TPMObjectiveType,
    TPMPromotionStatus, TPMBudgetType, TPMBaselineMethod,
    TPMClaimantType, TPMClaimType, TPMClaimStatus,
    TPMAIAgentType, TPMAIRecStatus,
    TPMPlan, TPMPromotion, TPMBudgetLine, TPMExpectedPerf, TPMActualPerf,
    TPMClaim, TPMClaimLine, TPMAIRecommendation,
)

# ── Accounting Dimensions / Cost Centers ─────────────────────────────────────
from app.models.dimensions import (
    DimensionScope, CostCenterType, DimSourceType,
    AllocationBasis, AllocationFrequency, AllocationRunStatus,
    ValidationSeverity, DimAIAgentType, DimAIRecStatus,
    DimType, DimValue, CostCenter, TransactionDimension,
    DimValidationRule, AllocationRule, AllocationRuleLine,
    AllocationRun, AllocationRunLine, DimDefaultRule,
    DimReclassification, DimAIRecommendation,
)

# ── Fixed Asset Accounting + Depreciation ────────────────────────────────────
from app.models.fixed_assets import (
    DepreciationMethod, DepreciationFrequency, DepreciationStartRule,
    FAAssetStatus, ScheduleStatus, AssetEventType, DisposalMethod,
    FAIAgentType, FAIRecStatus,
    FAAssetCategory, FAFixedAsset, FADepreciationSchedule,
    FAAssetEvent, FAAssetDisposal, FAAssetComponent, FAAIRecommendation,
)

# ── Bank Reconciliation ───────────────────────────────────────────────────────
from app.models.bank_reconciliation import (
    BRAccountType, BRImportSource, BRStatementStatus, BRLineMatchStatus,
    BRMatchMethod, BRERPTransactionType, BRAdjustmentType, BRRuleConditionType,
    BRAIAgentType, BRAIRecStatus,
    BRBankAccount, BRStatement, BRStatementLine, BRMatch, BRRule,
    BRAdjustment, BRAIRecommendation,
)

# ── Sales Commission Tracking ─────────────────────────────────────────────────
from app.models.commissions import (
    CommissionAppliesTo, CommissionScope, RuleStatus,
    ConditionType, CommissionType, TxnStatus as CMTxnStatus, PayoutStatus,
    CMAIAgentType, CMAIRecStatus,
    CommissionRule, CommissionRuleLine, CommissionTarget,
    CommissionTxn, CommissionAdjustment, CommissionPayout,
    CMAIRecommendation,
)
from app.models.expenses import (
    ExpenseStatus, ReimbursementMethod, AdvanceSettlementStatus,
    PolicyViolationSeverity, ExpAIAgentType, ExpAIRecStatus,
    ExpenseCategory, ExpensePolicy, ExpenseClaim, ExpenseClaimLine,
    ExpenseAdvance, ExpenseAccountingEntry,
    ExpAIRecommendation as ExpAIRecommendation,
)
from app.models.recruitment import (
    EmploymentType, RequisitionStatus, PostingChannel, PostingStatus,
    CandidateSource, PipelineStatus, InterviewType, InterviewDecision,
    OfferStatus, StageType, RTAIAgentType, RTAIRecStatus,
    RecruitmentStage, JobRequisition, JobPosting, Candidate,
    CandidatePipeline, CandidatePipelineHistory, Interview, Offer,
    RTAIRecommendation,
)
from app.models.ess import (
    ESSAccountStatus, EmploymentStatus as ESSEmploymentStatus, LeaveStatus,
    AttendanceStatus, ESSRequestType, ESSRequestStatus,
    NotificationType, ESSDocumentType, ESSAIAgentType, ESSAIRecStatus,
    ESSAccount, ESSEmployeeProfile, ESSLeaveType, ESSLeaveBalance,
    ESSLeaveRequest, ESSAttendanceRecord, ESSRequest, ESSNotification,
    ESSDocument, ESSActivityLog, ESSAIRecommendation,
)

# ── Performance Appraisals ────────────────────────────────────────────────────
from app.models.appraisals import (
    AppraisalPeriodType, AppraisalPeriodStatus, AppraisalStatus,
    FinalRating, DevelopmentPlanStatus, APAIAgentType, APAIRecStatus,
    AppraisalPeriod, AppraisalTemplate, AppraisalRecord,
    AppraisalKPILine, AppraisalCompetencyLine, AppraisalDevelopmentPlan,
    APAIRecommendation,
)

# ── Custom Report Builder ─────────────────────────────────────────────────────
from app.models.report_builder import (
    ReportVisibility, AggregationType, FilterOperator, LogicalOperator,
    SortDirection, ChartType, ScheduleFrequency, ExportFormat,
    RBAIAgentType, RBAIRecStatus,
    ReportDefinition, ReportField, ReportFilter, ReportCalculatedField,
    ReportSchedule, ReportDashboard, DashboardWidget, RBAIRecommendation,
)

# ── Kanban Boards ─────────────────────────────────────────────────────────────
from app.models.kanban import (
    BoardModuleType, BoardVisibility, ColumnStageType,
    CardPriority, CardStatus, ActivityEventType,
    KBAIAgentType, KBAIRecStatus,
    KanbanBoard, KanbanColumn, KanbanCard,
    KanbanActivity, KanbanComment, KBAIRecommendation,
)

# ── Custom Fields ─────────────────────────────────────────────────────────────
from app.models.custom_fields import (
    FieldType, EntityType, ValidationRuleType,
    CFAIAgentType, CFAIRecStatus,
    CustomFieldDefinition, CustomFieldOption, CustomFieldValue,
    CustomFieldValidationRule, CFAIRecommendation,
)

# ── Chatter / Activity Timeline ───────────────────────────────────────────────
from app.models.chatter import (
    ReferenceType, ActivityType, Visibility,
    ChatterAIAgentType, ChatterAIRecStatus,
    Activity, ActivityComment, ActivityAttachment, Mention, ChatterAIRecommendation,
)

# ── Calendar & Resource Scheduling ───────────────────────────────────────────
from app.models.calendar import (
    EventType, EventStatus, ParticipantRole, ResponseStatus,
    ResourceType, ResourceStatus, BookingStatus, RecurrenceFrequency,
    CAIAgentType, CAIRecStatus,
    CalendarResource, RecurrenceRule, CalendarEvent,
    EventParticipant, ResourceBooking, CAIRecommendation,
)

# ── Notification Center ───────────────────────────────────────────────────────
from app.models.notifications import (
    NotificationType as NCNotifType, NotificationPriority, NotificationChannel,
    NotificationStatus, NCNotifAIAgentType, NCNotifAIRecStatus,
    Notification, NotificationPreference, NotificationTemplate,
    NotificationSchedule, NCNotifAIRecommendation,
)

# ── Timesheet Approval Workflow ───────────────────────────────────────────────
from app.models.timesheets import (
    TimesheetStatus, ActivityType, ApprovalAction as TSApprovalAction,
    TSAIAgentType, TSAIRecStatus,
    TimesheetHeader, TimesheetLine, TimesheetApprovalLog, TSAIRecommendation,
)

# ── Training & Skills Management ──────────────────────────────────────────────
from app.models.training import (
    SkillCategory, SkillLevel, TrainingType,
    SessionStatus, AssignmentStatus, CertificationStatus,
    TRAIAgentType, TRAIRecStatus,
    SkillMaster, EmployeeSkillProfile, TrainingProgram, TrainingSession,
    TrainingAssignment, CertificationRecord, TrainingFeedback, TRAIRecommendation,
)

# ── Moto Sales Extension (part of van_sales module) ─────────────────────────
# Note: VanMpesaPayment, VanFraudAlert, VanRiderPerformance are defined in
# van_sales.py and imported together with the rest of van_sales models below.

# ── Contract Management ───────────────────────────────────────────────────────
from app.models.contracts import (
    ContractType, PartyType, ContractStatus, TermType, ValueType,
    RebateType, CalcBasis, SettlementFreq, ApprovalAction,
    CTAIAgentType, CTAIRecStatus,
    Contract, ContractTerm, ContractRebate, ContractPerformance,
    ContractVersion, ContractApproval, CTAIRecommendation,
)

# ── Van Sales / Mobile POS + Moto Sales Extension ────────────────────────────
from app.models.van_sales import (
    VanStatus, TxnType, TxnStatus, PaymentStatus, PaymentMethod,
    VisitStatus, ReturnReason, ReconciliationStatus,
    VSAIAgentType, VSAIRecStatus,
    Van, VanStock, VanStockMovement, VanVisit,
    VanSalesTxn, VanSalesTxnLine, VanPayment,
    VanReconciliation, VSAIRecommendation,
    # Moto Sales Extension (same module file)
    MpesaStkStatus, VanMpesaPayment,
    FraudType, FraudSeverity, FraudAlertStatus, VanFraudAlert,
    VanRiderPerformance,
)

# ── Subscription / Recurring Orders ──────────────────────────────────────────
from app.models.subscription import (
    RecurrenceType, SubscriptionStatus, GenerationMode,
    PriceSource, GenerationStatus, PauseSkipAction,
    SubAIAgentType, SubAIRecStatus,
    SubscriptionTemplate, SubscriptionLine,
    SubscriptionGenerationLog, SubscriptionPauseSkip,
    SubAIRecommendation,
)

# ── Quote / Estimation Module ─────────────────────────────────────────────────
from app.models.quotation import (
    QuoteStatus, Quotation, QuotationLine,
)

# ── Helpdesk / Customer Complaint Ticketing ───────────────────────────────────
from app.models.helpdesk import (
    TicketStatus, TicketCategory, TicketPriority, TicketSource,
    HelpdeskTicket, TicketComment,
)

# ── Project Management ────────────────────────────────────────────────────────
from app.models.project import (
    ProjectStatus, ProjectTaskStatus, ProjectPriority,
    Project, ProjectMilestone, ProjectTask, TaskDependency,
)

# ── Retail / Shop POS ─────────────────────────────────────────────────────────
from app.models.pos import (
    POSSessionStatus, POSPaymentMethod, POSSaleStatus,
    POSSession, POSSale, POSSaleLine,
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
    # Utilities (system configs, currencies, UOM, number series)
    "ConfigCategory", "SystemConfig", "UomConversion", "NumberSeries", "Currency",
    # AI
    "AIRequest", "AIPrediction", "AIRecommendation", "AIFormulation", "AIScenario",
    "AIRequestStatus", "AIRequestType", "AIProviderEnum",
    # Core
    "Role", "Permission", "role_permission",
    "User", "user_role",
    "AuditLog",
    # 2FA
    "User2FASettings", "TwoFASession", "RecoveryCode", "TwoFAMethod", "TwoFASessionStatus",
    # Cycle Count
    "CycleCountPlan", "CycleCountTask", "CountEntry", "CountAdjustment", "ABCClassification",
    "PlanType", "PlanStatus", "TaskStatus", "ABCClass", "AdjustmentStatus",
    # Webhooks / Event Engine
    "EventDefinition", "EventLog", "Subscription", "DeliveryAttempt", "InboundEndpoint",
    "AuthType", "DeliveryStatus", "HttpMethod",
    # Fleet Management
    "Vehicle", "FleetDriver", "FleetTrip", "FuelLog", "MaintenanceRecord", "IncidentLog",
    "VehicleType", "VehicleStatus", "FuelType", "TripStatus",
    "MaintenanceType", "IncidentType", "IncidentStatus", "DriverStatus",
    "Product", "Material", "Supplier", "Warehouse",
    "Stock", "Lot", "StockMovement",
    "Recipe", "RecipeItem", "ProcessParameter",
    "ProductionPlan", "ProductionPlanLine", "ProductionOrder",
    "MaterialConsumption", "FinishedGoodsReceipt", "DowntimeLog",
    "WarehouseZone", "StorageLocation", "StockCount", "StockCountLine",
    "PurchaseRequisition", "PRLine", "PurchaseOrder", "POLine",
    "GoodsReceipt", "GRNLine", "ImportShipment", "SupplierEvaluation", "SupplierPayment",
    "QCParameter", "QCInspection", "QCTestResult",
    "QCTemplate", "QCTemplateParameter",
    "HazardAnalysis", "CriticalControlPoint", "CCPMonitoringLog",
    "CorrectiveAction", "CorrectiveActionStep",
    "QCDeviation", "LotQualityStatus",
    "AllergenValidationRecord", "QMSAIRecommendation",
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
    # Lot Traceability + Batch Recall Management
    "TraceEventType", "TraceItemStage", "GenealogyRelType",
    "RecallType", "RecallTrigger", "RecallSeverity", "RecallStatus",
    "RecallActionType", "RecallActionStatus", "RecallRiskStatus",
    "TRRecAIAgentType", "TRRecAIRecStatus",
    "TraceEvent", "TraceEventLine", "LotGenealogyLink",
    "RecallHeader", "RecallScopeLine", "RecallAction",
    "RecallCustomerImpact", "RecallReturnRecord", "TRRecAIRecommendation",
    # FEFO + Shelf-Life Control
    "ShelfLifeStatus", "PickingStrategy", "ExpiryBlockPolicy", "NearExpiryPolicy",
    "ShelfLifeCategory", "RetestStatus", "DispositionAction", "DispositionStatus",
    "AlertType", "AlertSeverity", "SLAIAgentType", "SLAIRecStatus", "StrategyScope",
    "CustomerRuleType", "FEFOContext",
    "ItemShelfLifeConfig", "PickingStrategyConfig", "CustomerShelfLifeRule",
    "LotShelfLifeProfile", "RetestRequest", "BulkHoldRecord", "ShelfLifeAlert",
    "DispositionSuggestion", "FEFOAuditLog", "SLAIRecommendation",
    # Subcontracting System
    "SCOrderStatus", "SCIssueStatus", "SCReceiptStatus", "SCYieldStatus",
    "SCAIAgentType", "ScrapReasonCode",
    "SubcontractorLocation",
    "SubcontractOrder", "SubcontractOrderLine",
    "SubcontractMaterialIssue", "SubcontractMaterialIssueLine",
    "SubcontractReceipt", "SubcontractReceiptLine",
    "SubcontractYieldRecord", "SCPerformanceRecord", "SCAIRecommendation",
    # Procurement Suggestion Engine
    "PSRunStatus", "PSSuggestionStatus", "PSUrgencyLevel", "PSGroupStatus",
    "PSAIAgentType", "SupplierItemPriority",
    "SupplierItemPrice",
    "ProcurementSuggestionRun", "ProcurementSuggestionLine",
    "ProcurementSuggestionGroup", "PSAIRecommendation",
    # 3-Way Invoice Matching
    "MatchLineStatus", "MatchOverallStatus", "MatchReviewAction", "DuplicateRisk",
    "IMAIAgentType", "IMAIRecStatus",
    "InvoiceMatchTolerance", "InvoiceMatchHeader", "InvoiceMatchLine",
    "InvoiceMatchGRNLink", "DuplicateInvoiceLog", "InvoiceMatchReview",
    "IMAIRecommendation",
    # Landed Cost Allocation
    "LCStatus", "LandedCostType", "LCAllocationMethod", "LCReferenceType",
    "LCAIAgentType", "LCAIRecStatus",
    "LandedCostHeader", "LandedCostLine", "LandedCostGRNLink",
    "LandedCostAllocationLine", "LCInventoryAdjustment", "LCAIRecommendation",
    # Allergen + Nutrition Management
    "AllergenCategory", "PresenceType", "CrossContactRisk", "NutrientBasis", "NutrientSource",
    "LabelBasisType", "AllergenChangeType", "ANAIAgentType", "ANAIRecStatus",
    "AllergenMaster", "MaterialAllergenProfile", "MaterialAllergenLine",
    "NutritionProfile", "NutritionProfileLine",
    "ProductAllergenSummary", "ProductNutritionSummary",
    "AllergenChangeLog", "ProductServingConfig", "ANAIRecommendation",
    # GS1 Barcode + Label Printing
    "BarcodeType", "PackagingLevel", "PrintJobStatus", "SSCCStatus",
    "LabelTemplateStatus", "PrintTrigger", "GS1AIAgentType", "GS1AIRecStatus",
    "GS1CompanyConfig", "ProductGS1Config", "LotBarcodeRecord",
    "SSCCPallet", "SSCCPalletLot", "GS1LabelTemplate", "LabelPrintJob",
    "LabelPrintJobItem", "GS1AIRecommendation",
    # Sales Commission Tracking
    "CommissionAppliesTo", "CommissionScope", "RuleStatus",
    "ConditionType", "CommissionType", "CMTxnStatus", "PayoutStatus",
    "CMAIAgentType", "CMAIRecStatus",
    "CommissionRule", "CommissionRuleLine", "CommissionTarget",
    "CommissionTxn", "CommissionAdjustment", "CommissionPayout",
    "CMAIRecommendation",
    # Moto Sales Extension
    "MpesaStkStatus", "VanMpesaPayment",
    "FraudType", "FraudSeverity", "FraudAlertStatus", "VanFraudAlert",
    "VanRiderPerformance",
    # Contract Management
    "ContractType", "PartyType", "ContractStatus", "TermType", "ValueType",
    "RebateType", "CalcBasis", "SettlementFreq", "ApprovalAction",
    "CTAIAgentType", "CTAIRecStatus",
    "Contract", "ContractTerm", "ContractRebate", "ContractPerformance",
    "ContractVersion", "ContractApproval", "CTAIRecommendation",
    # Van Sales / Mobile POS
    "VanStatus", "TxnType", "TxnStatus", "PaymentStatus", "PaymentMethod",
    "VisitStatus", "ReturnReason", "ReconciliationStatus",
    "VSAIAgentType", "VSAIRecStatus",
    "Van", "VanStock", "VanStockMovement", "VanVisit",
    "VanSalesTxn", "VanSalesTxnLine", "VanPayment",
    "VanReconciliation", "VSAIRecommendation",
    # Subscription / Recurring Orders
    "RecurrenceType", "SubscriptionStatus", "GenerationMode",
    "PriceSource", "GenerationStatus", "PauseSkipAction",
    "SubAIAgentType", "SubAIRecStatus",
    "SubscriptionTemplate", "SubscriptionLine",
    "SubscriptionGenerationLog", "SubscriptionPauseSkip",
    "SubAIRecommendation",
    # Quote / Estimation Module
    "QuoteStatus", "Quotation", "QuotationLine",
    # Helpdesk / Customer Complaint Ticketing
    "TicketStatus", "TicketCategory", "TicketPriority", "TicketSource",
    "HelpdeskTicket", "TicketComment",
    # Project Management
    "ProjectStatus", "ProjectTaskStatus", "ProjectPriority",
    "Project", "ProjectMilestone", "ProjectTask", "TaskDependency",
    # Retail / Shop POS
    "POSSessionStatus", "POSPaymentMethod", "POSSaleStatus",
    "POSSession", "POSSale", "POSSaleLine",
    # Material Flow Engine
    "FlowType", "FlowStatus", "FlowMode", "StageType", "QualityStatus",
    "MovementReason", "ReservationStatus", "TankStatus", "ReconciliationStatus",
    "MFAIAgentType", "MFAIRecStatus",
    "FlowStage", "MaterialFlowTransaction", "MaterialFlowLine",
    "MaterialReservation", "MaterialReservationLine",
    "ProductionConsumption", "PreparedLot", "TankOccupancy",
    "BatchReconciliation", "BatchReconciliationLine", "MFAIRecommendation",
    # Price List Enhancement
    "PLType", "PLStatus", "PLDiscountType", "PLApprovalAction",
    "PLDiscountScope", "PLChangeType", "PLAIAgentType", "PLAIRecStatus",
    "PLHeader", "PLLine", "PLTier", "PLAssignment", "PLDiscountRule",
    "PLApproval", "PLChangeHistory", "PLAIRecommendation",
    # Dunning / Overdue Collection
    "DunningActionType", "DunningCaseStatus", "DunningActionOutcome",
    "PTPStatus", "DunningExceptionType", "DunningAIAgentType", "DunningAIRecStatus",
    "DunningPolicy", "DunningLevel", "DunningTemplate", "DunningCase",
    "DunningCaseInvoice", "DunningActionLog", "DunningPTP", "DunningException",
    "DunningAIRecommendation",
    # Supplier Portal
    "SPAccountStatus", "SPUserRole", "SPActivityType",
    "SPPOResponseStatus", "SPETAStatus", "SPDocUploadType", "SPDocReviewStatus",
    "SPPaymentVisibility", "SPAIAgentType", "SPAIRecStatus",
    "SPAccount", "SPUser", "SPPermissionProfile", "SPActivityLog",
    "SPDocument", "SPPOResponse", "SPETALog", "SPAIRecommendation",
    # Customer / Distributor Portal
    "PortalAccountType", "PortalAccountStatus", "PortalUserRole",
    "PortalActivityType", "PortalClaimType", "PortalClaimStatus",
    "PortalOrderMode", "PortalDraftOrderStatus",
    "PortalAIAgentType", "PortalAIRecStatus",
    "PortalAccount", "PortalUser", "PortalActivityLog",
    "PortalClaim", "PortalDraftOrder", "PortalDraftOrderLine",
    "PortalAIRecommendation",
    # Advanced CRM Pipeline
    "CRMRecordType", "CRMAccountType", "CRMSourceType", "CRMStageType",
    "CRMTemperature", "CRMStatus", "CRMActivityType", "CRMActivityResult",
    "CRMLossReason", "CRMWinReason", "CRMAIAgentType", "CRMAIRecStatus",
    "CRMPipelineStage", "CRMRecord", "CRMInterestLine", "CRMActivity",
    "CRMCompetitor", "CRMWinLoss", "CRMAIRecommendation",
    # Trade Promotion Management
    "TPMPeriodType", "TPMPlanStatus", "TPMPromotionType", "TPMObjectiveType",
    "TPMPromotionStatus", "TPMBudgetType", "TPMBaselineMethod",
    "TPMClaimantType", "TPMClaimType", "TPMClaimStatus",
    "TPMAIAgentType", "TPMAIRecStatus",
    "TPMPlan", "TPMPromotion", "TPMBudgetLine", "TPMExpectedPerf", "TPMActualPerf",
    "TPMClaim", "TPMClaimLine", "TPMAIRecommendation",
    # Bank Reconciliation
    "BRAccountType", "BRImportSource", "BRStatementStatus", "BRLineMatchStatus",
    "BRMatchMethod", "BRERPTransactionType", "BRAdjustmentType", "BRRuleConditionType",
    "BRAIAgentType", "BRAIRecStatus",
    "BRBankAccount", "BRStatement", "BRStatementLine", "BRMatch", "BRRule",
    "BRAdjustment", "BRAIRecommendation",
    # Fixed Asset Accounting
    "DepreciationMethod", "DepreciationFrequency", "DepreciationStartRule",
    "FAAssetStatus", "ScheduleStatus", "AssetEventType", "DisposalMethod",
    "FAIAgentType", "FAIRecStatus",
    "FAAssetCategory", "FAFixedAsset", "FADepreciationSchedule",
    "FAAssetEvent", "FAAssetDisposal", "FAAssetComponent", "FAAIRecommendation",
    # Expense Claims
    "ExpenseStatus", "ReimbursementMethod", "AdvanceSettlementStatus",
    "PolicyViolationSeverity", "ExpAIAgentType", "ExpAIRecStatus",
    "ExpenseCategory", "ExpensePolicy", "ExpenseClaim", "ExpenseClaimLine",
    "ExpenseAdvance", "ExpenseAccountingEntry", "ExpAIRecommendation",
    # Recruitment / ATS
    "EmploymentType", "RequisitionStatus", "PostingChannel", "PostingStatus",
    "CandidateSource", "PipelineStatus", "InterviewType", "InterviewDecision",
    "OfferStatus", "StageType", "RTAIAgentType", "RTAIRecStatus",
    "RecruitmentStage", "JobRequisition", "JobPosting", "Candidate",
    "CandidatePipeline", "CandidatePipelineHistory", "Interview", "Offer",
    "RTAIRecommendation",
    # Employee Self-Service
    "ESSAccountStatus", "ESSEmploymentStatus", "LeaveStatus", "AttendanceStatus",
    "ESSRequestType", "ESSRequestStatus", "NotificationType", "ESSDocumentType",
    "ESSAIAgentType", "ESSAIRecStatus",
    "ESSAccount", "ESSEmployeeProfile", "ESSLeaveType", "ESSLeaveBalance",
    "ESSLeaveRequest", "ESSAttendanceRecord", "ESSRequest", "ESSNotification",
    "ESSDocument", "ESSActivityLog", "ESSAIRecommendation",
]

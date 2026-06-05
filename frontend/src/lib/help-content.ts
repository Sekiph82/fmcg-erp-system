export type HelpTopic = {
  title: string;
  purpose: string;
  mainActions: string[];
  keyFields?: { label: string; description: string }[];
  statuses?: { status: string; meaning: string }[];
  warnings?: string[];
  relatedManual?: string;
};

export const helpTopics: Record<string, HelpTopic> = {
  "finance-etims": {
    title: "eTIMS — KRA e-Invoice",
    purpose:
      "Submit and manage tax invoices with Kenya Revenue Authority via the electronic Tax Invoice Management System. All VAT-registered businesses must transmit invoices electronically.",
    mainActions: [
      "Submit an invoice to KRA by entering the invoice ID",
      "Retry rejected or failed submissions",
      "Cancel an accepted submission with a written reason",
      "Check live provider health and connection status",
      "Filter the submissions table by status",
    ],
    statuses: [
      { status: "DRAFT", meaning: "Invoice created but not yet queued for submission" },
      { status: "READY", meaning: "Queued — will be picked up by the background worker" },
      { status: "PENDING", meaning: "Sent to KRA; awaiting acknowledgement" },
      { status: "SUBMITTED", meaning: "Received by KRA; awaiting final status" },
      { status: "ACCEPTED", meaning: "KRA confirmed — invoice is valid and registered" },
      { status: "REJECTED", meaning: "KRA rejected — review reason and retry" },
      { status: "RETRY_PENDING", meaning: "Scheduled for automatic retry" },
      { status: "FAILED", meaning: "Submission error — manual retry required" },
      { status: "ERROR", meaning: "Unexpected system error — check logs" },
      { status: "CANCELLED", meaning: "Voided — no further action possible" },
    ],
    warnings: [
      "System runs in simulation mode — no live KRA calls until production_execution_allowed is enabled.",
      "GL journal posting requires an accountant to approve the invoice first.",
    ],
    relatedManual: "Full Reference Manual — Section 8: Finance & Accounting (eTIMS)",
  },

  "sales-invoice-etims": {
    title: "Sales Invoice — eTIMS Submission",
    purpose:
      "Submit an individual approved sales invoice to KRA from the invoice detail view and track its eTIMS submission status.",
    mainActions: [
      "Approve the invoice before attempting eTIMS submission",
      "Click Submit to KRA to queue the invoice",
      "View the current submission status badge",
      "Navigate to the eTIMS global page to retry or cancel",
    ],
    statuses: [
      { status: "ACCEPTED", meaning: "KRA registered the invoice" },
      { status: "REJECTED", meaning: "KRA refused — go to eTIMS page to retry" },
      { status: "PENDING", meaning: "Awaiting KRA acknowledgement" },
    ],
    warnings: [
      "Invoice must be in Approved state before submission to KRA.",
      "Simulation mode is active — submissions do not reach the live KRA endpoint.",
    ],
    relatedManual: "Full Reference Manual — Section 8: Finance & Accounting (eTIMS)",
  },

  "inventory-stock": {
    title: "Inventory & Stock Ledger",
    purpose:
      "View real-time stock positions across all warehouses. Record adjustments, manage lot/batch/serial tracking, and import bulk stock data.",
    mainActions: [
      "Filter stock by product, warehouse, or lot number",
      "Record a manual stock adjustment (positive or negative)",
      "Import bulk stock data via CSV",
      "Drill into a product to see lot-level breakdown",
      "Refresh to see latest quantities",
    ],
    keyFields: [
      { label: "On Hand", description: "Total units physically in the warehouse" },
      { label: "Reserved", description: "Committed to pending sales or production orders" },
      { label: "Available", description: "On Hand minus Reserved — can be allocated to new orders" },
      { label: "Lot / Batch", description: "Unique identifier for a production or receipt batch" },
    ],
    warnings: [
      "Stock adjustments create permanent ledger entries and cannot be deleted.",
      "Use Cycle Count to investigate and resolve discrepancies rather than direct adjustments.",
    ],
    relatedManual: "Supply Chain Manual — Section 7: Inventory & Stock",
  },

  "inventory-shelf-life": {
    title: "FEFO + Shelf-Life Control",
    purpose:
      "Track expiry dates on all stock lots and enforce FEFO (First Expired, First Out) picking. Monitor near-expiry and expired stock to prevent dispatch of out-of-date products.",
    mainActions: [
      "Generate shelf-life alerts to refresh the near-expiry list",
      "View expiry calendar to plan stock rotation",
      "Filter by status to prioritize expired or near-expiry lots",
      "Export expiry report for QA or regulatory submission",
    ],
    statuses: [
      { status: "FRESH", meaning: "Well within shelf life" },
      { status: "NEAR_EXPIRY", meaning: "Within the near-expiry threshold (default 30 days)" },
      { status: "EXPIRING_TODAY", meaning: "Expires today — urgent action required" },
      { status: "EXPIRED", meaning: "Past expiry date — must not be dispatched" },
    ],
    warnings: [
      "FEFO enforcement only works for lots received with an expiry date. Lots without expiry are excluded from FEFO rules.",
      "Expired stock should be quarantined immediately. Contact QA before any write-off.",
    ],
    relatedManual: "Supply Chain Manual — Section 12: Shelf-Life & FEFO",
  },

  "inventory-traceability": {
    title: "Lot Traceability & Recall Management",
    purpose:
      "Run forward and backward traceability queries on lot/serial numbers. Execute product recalls and generate regulatory traceability reports.",
    mainActions: [
      "Search by lot number or serial to open the traceability tree",
      "Forward trace: see where a lot was shipped or consumed",
      "Backward trace: see what inputs or suppliers produced this lot",
      "Initiate a recall: quarantine affected lots across all locations",
      "Export the genealogy report for regulatory submission",
    ],
    keyFields: [
      { label: "Lot Number", description: "Unique batch identifier from production or receiving" },
      { label: "Direction", description: "Forward (downstream) or Backward (upstream)" },
      { label: "Recall Status", description: "Active, Closed, or Quarantined" },
    ],
    warnings: [
      "Recall records cannot be deleted after initiation. Notify QA and management before starting a recall.",
      "Regulatory traceability requires GS1 lot codes — products without GS1 GTINs may not appear correctly.",
    ],
    relatedManual: "Supply Chain Manual — Section 8: Traceability & Recall",
  },

  "inventory-cycle-count": {
    title: "Cycle Count",
    purpose:
      "Conduct periodic inventory accuracy checks by location or product category — without a full warehouse freeze. Compare system quantities against physical counts and post adjustments.",
    mainActions: [
      "Start a new count session for selected locations or SKUs",
      "Assign counters and set the count date",
      "Record physical count quantities",
      "Review discrepancies between system and counted quantities",
      "Post approved adjustments to the stock ledger",
    ],
    keyFields: [
      { label: "Count Accuracy %", description: "Percentage of items counted within tolerance" },
      { label: "Variance", description: "Difference between system quantity and counted quantity" },
      { label: "Discrepancy Value", description: "Financial value of the quantity difference" },
    ],
    warnings: [
      "Posting adjustments updates stock immediately — confirm counts are correct before approving.",
      "A supervisor must review and sign off on adjustments above the variance threshold.",
    ],
    relatedManual: "Supply Chain Manual — Section 9: Cycle Count",
  },

  "wms": {
    title: "Warehouse Management",
    purpose:
      "Manage warehouse zones, bin locations, pick waves, and handling units (pallets and cartons). Supports directed put-away and wave-based order picking.",
    mainActions: [
      "Create and configure warehouse zones and bin locations",
      "Assign received stock to specific bin locations",
      "Create pick waves for outbound orders",
      "Process put-away tasks for inbound receipts",
      "Manage handling units (pallets, cartons, cases)",
    ],
    keyFields: [
      { label: "Zone", description: "Named area of the warehouse (e.g., Dry Goods, Cold Store)" },
      { label: "Location / Bin", description: "Specific slot identifier (e.g., A-01-03)" },
      { label: "Handling Unit", description: "Pallet or carton ID — links stock to physical container" },
      { label: "Pick Wave", description: "Grouped picking task for one or more orders" },
    ],
    warnings: [
      "WMS locations must exactly match your physical warehouse layout. Incorrect setup causes mis-picks.",
      "Do not delete active bin locations — quarantine empty locations instead.",
    ],
    relatedManual: "Supply Chain Manual — Section 10: Warehouse Management (WMS)",
  },

  "planning-mrp": {
    title: "MRP & Material Requirements Planning",
    purpose:
      "Calculate what materials to buy or produce based on demand, bill of materials, lead times, and current stock. Generate purchase and production order suggestions.",
    mainActions: [
      "Run MRP calculation to refresh suggestions",
      "Review purchase suggestions — approve to create purchase orders",
      "Review production suggestions — approve to create work orders",
      "View demand forecasts driving MRP",
      "Navigate to Workbench for detailed planning board",
    ],
    keyFields: [
      { label: "Demand Source", description: "Sales orders, forecasts, or safety stock rules" },
      { label: "Lead Time", description: "Days required to receive or produce the item" },
      { label: "Suggested Quantity", description: "MRP-recommended order quantity" },
      { label: "Action", description: "BUY (purchase) or MAKE (produce)" },
    ],
    warnings: [
      "MRP uses a snapshot of demand at run time. Re-run MRP after updating forecasts or adding large orders.",
      "Safety stock rules must be configured per SKU for MRP to suggest replenishment.",
    ],
    relatedManual: "Supply Chain Manual — Section 11: MRP & Demand Forecasting",
  },

  "production-oee": {
    title: "OEE Tracking",
    purpose:
      "Track Overall Equipment Effectiveness (Availability × Performance × Quality) per machine or production line. Identify chronic losses and prioritize maintenance.",
    mainActions: [
      "Import OEE records from production floor data",
      "View per-machine OEE trend charts",
      "Toggle AI Insights for root-cause analysis",
      "Filter by machine, date range, or OEE band",
      "Export OEE report for management review",
    ],
    keyFields: [
      { label: "OEE %", description: "Combined effectiveness score. Target ≥ 65%." },
      { label: "Availability", description: "Run time ÷ planned time (impacted by downtime)" },
      { label: "Performance", description: "Actual speed ÷ ideal speed" },
      { label: "Quality", description: "Good units ÷ total units produced" },
    ],
    warnings: [
      "OEE below 65% triggers an automatic alert. Review Downtime Tracking for root causes.",
      "AI Insights require Claude AI to be configured with a valid API key.",
    ],
    relatedManual: "Manufacturing Manual — Section 11: OEE Reporting",
  },

  "production-qc": {
    title: "Quality Control",
    purpose:
      "Record, track, and review quality inspection results for production batches. Manage pass/fail decisions and put lots on hold pending investigation.",
    mainActions: [
      "Create a new quality inspection for a batch",
      "Import bulk inspection records",
      "Filter inspections by status, product, or date",
      "Update inspection result and add notes",
      "Release or reject a lot based on inspection outcome",
    ],
    statuses: [
      { status: "PENDING", meaning: "Inspection recorded but not yet reviewed" },
      { status: "PASSED", meaning: "Lot meets quality specifications — cleared for release" },
      { status: "FAILED", meaning: "Lot does not meet specs — must be quarantined or reworked" },
      { status: "ON_HOLD", meaning: "Awaiting further testing or management decision" },
    ],
    warnings: [
      "Failed inspections block production lot release and prevent shipment.",
      "On-hold lots cannot be allocated to sales orders until released or rejected.",
    ],
    relatedManual: "Manufacturing Manual — Section 7: Quality Control",
  },

  "production-downtime": {
    title: "Downtime Tracking",
    purpose:
      "Log machine and line downtime events by category and duration. Downtime data feeds directly into the OEE Availability calculation.",
    mainActions: [
      "Log a new downtime event with machine, category, and duration",
      "Import historical downtime events in bulk",
      "Filter events by category, machine, or date range",
      "View cumulative downtime by category for Pareto analysis",
    ],
    keyFields: [
      { label: "Category", description: "Mechanical, Electrical, Changeover, Quality, or Planned Maintenance" },
      { label: "Duration (min)", description: "Total minutes the machine was stopped" },
      { label: "Machine / Line", description: "Which asset was affected" },
    ],
    warnings: [
      "Downtime category determines how it affects OEE. Planned maintenance is excluded from Availability loss.",
      "Use standard category names for accurate Pareto reporting.",
    ],
    relatedManual: "Manufacturing Manual — Section 12: Downtime Tracking",
  },

  "production-waste": {
    title: "Waste & Yield Tracking",
    purpose:
      "Track material waste and yield losses during production runs. Identify anomalous waste events and trends by product, line, or shift.",
    mainActions: [
      "Log a waste entry with product, quantity, and reason code",
      "Import waste records in bulk",
      "Filter by anomaly flag to review outlier events",
      "View yield trend charts by product or production line",
    ],
    keyFields: [
      { label: "Waste Quantity", description: "Units or weight lost in this event" },
      { label: "Yield %", description: "Good output ÷ total input material" },
      { label: "Anomaly", description: "Flagged when waste exceeds 2 standard deviations from average" },
    ],
    warnings: [
      "Anomalies (shown in red) indicate a process problem. Review with the production manager before the next run.",
      "Yield data is used in costing — inaccurate entries affect product cost calculations.",
    ],
    relatedManual: "Manufacturing Manual — Section 13: Waste & Yield",
  },

  "gs1": {
    title: "GS1 Barcode & Label Printing",
    purpose:
      "Generate and print GS1-compliant barcodes and labels for products and pallets. Supports EAN-13, GTIN-14, and SSCC pallet barcodes in multiple label sizes.",
    mainActions: [
      "Select a product and label size, then generate the barcode",
      "Print labels directly to a connected label printer",
      "Generate SSCC codes for pallet identification",
      "View and reprint from print job history",
      "Configure GS1 company prefix in integrations settings",
    ],
    keyFields: [
      { label: "GTIN", description: "Global Trade Item Number — product barcode (13 or 14 digits)" },
      { label: "SSCC", description: "Serial Shipping Container Code — unique pallet identifier (18 digits)" },
      { label: "Label Size", description: "50×30mm (small), 70×40mm (medium), 100×50mm (large), A4 (sheet)" },
    ],
    warnings: [
      "GS1 access requires GS1 authorization permission. Contact your administrator if access is denied.",
      "Products must have a GTIN assigned before label generation. Assign GTINs in the Products module.",
    ],
    relatedManual: "Full Reference Manual — Section 10: Admin & Security (GS1)",
  },

  "documents": {
    title: "Documents",
    purpose:
      "Central document repository for uploading, versioning, categorizing, and sharing company documents such as contracts, SOPs, certificates, and reports.",
    mainActions: [
      "Upload a new document (requires documents.create permission)",
      "Search and filter documents by type, category, or date",
      "Download the latest or a specific version",
      "Create folders and organize by category",
      "Manage document versions and metadata",
    ],
    keyFields: [
      { label: "Document Type", description: "Contract, SOP, Certificate, Report, or Custom" },
      { label: "Version", description: "Each upload of the same document increments the version number" },
      { label: "Status", description: "Draft (not final), Active (current), Archived (superseded)" },
    ],
    warnings: [
      "File storage is local to the server in the current version. Cloud storage integration is pending.",
      "Deleting a document removes all versions — archive instead of delete for audit trail.",
    ],
    relatedManual: "Full Reference Manual — Section 13: Standalone Operational Pages",
  },

  "knowledge-base": {
    title: "Knowledge Base",
    purpose:
      "Internal wiki for SOPs, training guides, policies, and how-to articles. Search and browse company knowledge organized by category and tags.",
    mainActions: [
      "Search articles by keyword or tag",
      "Create a new article with rich text content",
      "Organize articles by category",
      "Add tags for better discoverability",
      "View article version history",
    ],
    warnings: [
      "Access requires the knowledge_base.view permission. Editing requires knowledge_base.edit.",
      "Articles are visible to all users with view permission — do not store sensitive credentials in articles.",
    ],
    relatedManual: "Full Reference Manual — Section 13: Standalone Operational Pages",
  },

  "esign": {
    title: "Electronic Signatures",
    purpose:
      "Create and track digital signature requests for documents. Collect signatures from internal or external parties without printing.",
    mainActions: [
      "Create a new signing request and attach the document",
      "Add signers (name, email, signing order)",
      "Send reminders to pending signers",
      "Download the completed signed document",
      "Cancel or expire a request if needed",
    ],
    statuses: [
      { status: "PENDING", meaning: "Sent — waiting for all signers" },
      { status: "PARTIALLY_SIGNED", meaning: "Some signers have signed; others remain" },
      { status: "COMPLETED", meaning: "All parties have signed — document is legally executed" },
      { status: "EXPIRED", meaning: "Deadline passed — must be recreated" },
      { status: "CANCELLED", meaning: "Voided by the requester" },
    ],
    warnings: [
      "Access requires the esign.view permission. Creating requests requires esign.create.",
      "Expired signing requests cannot be reopened — create a new request with the same document.",
    ],
    relatedManual: "Full Reference Manual — Section 13: Standalone Operational Pages",
  },

  "ai-forecasting": {
    title: "AI & Intelligence",
    purpose:
      "Access AI-powered demand forecasting (Holt-Winters model), the AI assistant chat, and market intelligence features. All forecasting runs locally — no external API calls for the forecast engine.",
    mainActions: [
      "View demand forecast results by SKU",
      "Check AI provider status and configuration",
      "Use AI chat for business queries and analysis",
      "Access market intelligence dashboards",
      "Review forecast model parameters",
    ],
    keyFields: [
      { label: "Provider", description: "Claude (LLM mode) or local fallback (rules-based)" },
      { label: "Mode", description: "llm = Claude API active; fallback = AI chat unavailable" },
      { label: "Forecast Model", description: "Holt-Winters exponential smoothing (local statsmodels)" },
    ],
    warnings: [
      "Forecast accuracy requires ≥ 3 months of sales history. 1–2 months uses exponential smoothing only. A single data point uses mean.",
      "AI chat requires a valid Claude API key in environment settings. Forecasting works independently without it.",
    ],
    relatedManual: "Full Reference Manual — Section 11: AI & Automation",
  },

  "admin-security": {
    title: "Security Settings",
    purpose:
      "Manage two-factor authentication and security configuration for your user account. View your login history and active sessions.",
    mainActions: [
      "Enable or disable two-factor authentication (TOTP)",
      "Generate and store recovery codes",
      "View recent login history and failed attempts",
      "Terminate other active sessions",
    ],
    keyFields: [
      { label: "2FA Status", description: "Whether TOTP two-factor authentication is active" },
      { label: "Recovery Codes", description: "One-time backup codes — store securely offline" },
      { label: "Last Login", description: "Timestamp and IP of most recent login" },
    ],
    warnings: [
      "Disabling 2FA reduces account security. Management and admin accounts should always have 2FA enabled.",
      "Management user accounts are seeded via environment variables — contact your system administrator to add or remove management-level users.",
    ],
    relatedManual: "Full Reference Manual — Section 10: Admin & Security",
  },
};

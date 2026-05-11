import { apiClient } from "@/lib/api";

export type AccountType = "ASSET" | "LIABILITY" | "EQUITY" | "REVENUE" | "EXPENSE";
export type CashAccountType = "CASH" | "BANK" | "MPESA";
export type TxDirection = "RECEIPT" | "PAYMENT";
export type FinTxStatus = "PENDING" | "CLEARED" | "FAILED" | "REVERSED";
export type ReconciliationStatus = "UNMATCHED" | "MATCHED" | "MANUAL" | "EXCEPTION";
export type BudgetStatus = "DRAFT" | "APPROVED" | "LOCKED";
export type BudgetType = "OPEX" | "CAPEX";
export type CostType = "RAW_MATERIAL" | "PACKAGING" | "LABOR" | "UTILITY" | "OVERHEAD";

export interface COA {
  id: string;
  code: string;
  name: string;
  account_type: AccountType;
  parent_id?: string;
  is_control: boolean;
  currency: string;
  is_active: boolean;
  notes?: string;
  created_at: string;
}

export interface JournalLine {
  id: string;
  account_id: string;
  account_code?: string;
  account_name?: string;
  description?: string;
  debit: number;
  credit: number;
  currency: string;
}

export interface JournalEntry {
  id: string;
  entry_no: string;
  entry_date: string;
  description: string;
  source_module?: string;
  source_ref?: string;
  is_posted: boolean;
  posted_at?: string;
  created_at: string;
  total_debit?: number;
  total_credit?: number;
  lines?: JournalLine[];
}

export interface CashAccount {
  id: string;
  name: string;
  account_type: CashAccountType;
  account_number?: string;
  bank_name?: string;
  currency: string;
  opening_balance: number;
  current_balance: number;
  gl_account_id?: string;
  is_active: boolean;
  notes?: string;
  created_at: string;
}

export interface CashTransaction {
  id: string;
  cash_account_id: string;
  cash_account_name?: string;
  cash_account_type?: CashAccountType;
  transaction_date: string;
  direction: TxDirection;
  amount: number;
  description: string;
  reference?: string;
  status: FinTxStatus;
  mpesa_phone?: string;
  mpesa_receipt?: string;
  mpesa_name?: string;
  source_module?: string;
  source_ref?: string;
  created_at: string;
  reconciliation_status?: ReconciliationStatus;
}

export interface MpesaReconciliation {
  id: string;
  cash_transaction_id: string;
  invoice_id?: string;
  invoice_no?: string;
  so_id?: string;
  so_no?: string;
  status: ReconciliationStatus;
  matched_amount?: number;
  exception_reason?: string;
  notes?: string;
  matched_at?: string;
  created_at: string;
  tx_date?: string;
  tx_amount?: number;
  mpesa_receipt?: string;
  mpesa_phone?: string;
  mpesa_name?: string;
}

export interface ProductionCostEntry {
  id: string;
  production_order_id: string;
  product_id: string;
  product_name?: string;
  cost_type: CostType;
  amount: number;
  quantity?: number;
  unit_cost?: number;
  period_ym: string;
  notes?: string;
  created_at: string;
}

export interface ProductCost {
  id: string;
  product_id: string;
  product_name?: string;
  product_sku?: string;
  period_ym: string;
  raw_material_cost: number;
  packaging_cost: number;
  labor_cost: number;
  utility_cost: number;
  overhead_cost: number;
  total_units_produced: number;
  standard_cost_per_unit?: number;
  actual_cost_per_unit?: number;
  variance_amount?: number;
  variance_pct?: number;
}

export interface BudgetLine {
  id: string;
  category: string;
  account_id?: string;
  month: number;
  budgeted_amount: number;
}

export interface Budget {
  id: string;
  year: number;
  department: string;
  currency: string;
  status: BudgetStatus;
  budget_type: BudgetType;
  version: number;
  notes?: string;
  created_at: string;
  approved_at?: string;
  total_budgeted?: number;
  lines?: BudgetLine[];
}

export interface CashPositionRow {
  account_id: string;
  account_name: string;
  account_type: CashAccountType;
  currency: string;
  balance: number;
  pending_in: number;
  pending_out: number;
  cleared_balance: number;
}

export interface MpesaSummaryRow {
  date: string;
  receipt_count: number;
  total_received: number;
  matched_count: number;
  unmatched_count: number;
  failed_count: number;
}

export interface PaymentChannelRow {
  channel: string;
  receipt_count: number;
  total_amount: number;
  pct_of_total: number;
}

export interface ReceivableRow {
  invoice_id: string;
  invoice_no: string;
  customer_name: string;
  invoice_date: string;
  due_date: string;
  total_amount: number;
  paid_amount: number;
  outstanding: number;
  days_overdue?: number;
  currency: string;
}

export interface ReconciliationExceptionRow {
  transaction_id: string;
  transaction_date: string;
  mpesa_receipt?: string;
  mpesa_phone?: string;
  amount: number;
  description: string;
  status: ReconciliationStatus;
  exception_reason?: string;
}

export interface BudgetVsActualRow {
  department: string;
  category: string;
  month: number;
  budgeted: number;
  actual: number;
  variance: number;
  variance_pct?: number;
  utilization_pct?: number;
}

export interface BudgetAlertRow {
  budget_id: string;
  department: string;
  category: string;
  month: number;
  budgeted: number;
  actual: number;
  utilization_pct: number;
  alert_level: "WARNING" | "CRITICAL";
}

// ── Accounting Module Types ───────────────────────────────────────────────────

export type InvoiceStatus = "DRAFT" | "ISSUED" | "PARTIALLY_PAID" | "PAID" | "OVERDUE" | "CANCELLED";
export type PurchaseInvoiceStatus = "DRAFT" | "RECEIVED" | "PARTIALLY_PAID" | "PAID" | "OVERDUE" | "CANCELLED";
export type FiscalYearStatus = "OPEN" | "CLOSING" | "CLOSED" | "LOCKED";
export type PostingBatchStatus = "DRAFT" | "POSTED" | "FAILED" | "REVERSED";
export type OperationalPostingStatus = "PENDING" | "POSTED" | "FAILED" | "REVERSED" | "NOT_REQUIRED";
export type CurrencyRevaluationStatus = "DRAFT" | "POSTED" | "REVERSED";

export interface FiscalYear {
  id: string;
  year_code: string;
  start_date: string;
  end_date: string;
  status: FiscalYearStatus;
  base_currency: string;
  retained_earnings_account_id?: string;
  closed_at?: string;
  locked_at?: string;
  notes?: string;
  created_at: string;
}

export interface AccountingPostingBatch {
  id: string;
  source_module: string;
  source_event: string;
  source_id: string;
  source_ref?: string;
  status: PostingBatchStatus;
  journal_entry_id?: string;
  idempotency_key: string;
  error_message?: string;
  posted_at?: string;
  created_at: string;
}

export interface AccountingPostingRule {
  id: string;
  source_module: string;
  source_event: string;
  rule_name: string;
  debit_account_id?: string;
  credit_account_id?: string;
  tax_account_id?: string;
  clearing_account_id?: string;
  is_active: boolean;
  priority: number;
  notes?: string;
  created_at: string;
}

export interface OperationalPostingEvent {
  id: string;
  source_module: string;
  source_event: string;
  source_id: string;
  source_line_id?: string;
  stock_movement_id?: string;
  posting_batch_id?: string;
  journal_entry_id?: string;
  status: OperationalPostingStatus;
  event_date: string;
  amount?: number;
  currency?: string;
  idempotency_key: string;
  reversal_event_id?: string;
  error_message?: string;
  created_by_id?: string;
  created_at: string;
}

export interface InventoryAccountMapping {
  id: string;
  stock_type?: string;
  product_id?: string;
  material_id?: string;
  category_key?: string;
  valuation_method?: string;
  inventory_account_id?: string;
  wip_account_id?: string;
  finished_goods_account_id?: string;
  cogs_account_id?: string;
  grni_account_id?: string;
  landed_cost_clearing_account_id?: string;
  variance_account_id?: string;
  scrap_account_id?: string;
  is_active: boolean;
  priority: number;
  notes?: string;
  created_at: string;
}

export interface PaymentAllocation {
  id: string;
  party_type: "CUSTOMER" | "SUPPLIER";
  customer_payment_id?: string;
  supplier_payment_id?: string;
  sales_invoice_id?: string;
  purchase_invoice_id?: string;
  allocated_amount: number;
  allocation_date: string;
  notes?: string;
  created_at: string;
}

export interface CurrencyRevaluationRun {
  id: string;
  run_no: string;
  as_of_date: string;
  currency: string;
  status: CurrencyRevaluationStatus;
  journal_entry_id?: string;
  posted_at?: string;
  created_at: string;
}

export interface SalesInvoice {
  id: string;
  invoice_no: string;
  customer_id: string;
  customer_name?: string;
  customer_code?: string;
  invoice_date: string;
  due_date: string;
  status: InvoiceStatus;
  currency: string;
  subtotal: number;
  tax_amount: number;
  total_amount: number;
  paid_amount: number;
  outstanding: number;
  notes?: string;
  created_at: string;
  lines?: SalesInvoiceLine[];
  payments?: CustomerPayment[];
}

export interface SalesInvoiceLine {
  id: string;
  product_id: string;
  product_name?: string;
  description?: string;
  quantity: number;
  unit: string;
  unit_price: number;
  discount_pct: number;
  tax_rate: number;
  line_total: number;
}

export interface PurchaseInvoice {
  id: string;
  invoice_no: string;
  supplier_id: string;
  supplier_name?: string;
  po_id?: string;
  po_no?: string;
  invoice_date: string;
  due_date: string;
  status: PurchaseInvoiceStatus;
  currency: string;
  subtotal: number;
  tax_amount: number;
  total_amount: number;
  paid_amount: number;
  notes?: string;
  created_at: string;
  lines?: PurchaseInvoiceLine[];
}

export interface PurchaseInvoiceLine {
  id: string;
  material_id?: string;
  product_id?: string;
  material_name?: string;
  product_name?: string;
  description?: string;
  quantity: number;
  unit: string;
  unit_price: number;
  tax_rate: number;
  line_total: number;
}

export interface CustomerPayment {
  id: string;
  invoice_id: string;
  invoice_no?: string;
  customer_name?: string;
  payment_date: string;
  amount: number;
  method: string;
  reference?: string;
  notes?: string;
  created_at: string;
}

export interface PurchasePayment {
  id: string;
  invoice_id: string;
  payment_date: string;
  amount: number;
  method: string;
  reference?: string;
  notes?: string;
  created_at: string;
}

export interface CombinedPayment {
  id: string;
  type: "customer" | "supplier";
  payment_date: string;
  amount: number;
  method: string;
  reference?: string;
  notes?: string;
  invoice_id: string;
  invoice_no?: string;
  party_name?: string;
  created_at: string;
}

export interface CustomerLedgerRow {
  customer_id: string;
  customer_code: string;
  customer_name: string;
  total_invoiced: number;
  total_paid: number;
  outstanding_balance: number;
}

export interface SupplierLedgerRow {
  supplier_id: string;
  supplier_code: string;
  supplier_name: string;
  total_purchases: number;
  total_paid: number;
  outstanding_payable: number;
}

export interface AccountingDashboard {
  total_revenue: number;
  total_receivables: number;
  total_cost: number;
  total_payables: number;
  cash_flow: number;
  overdue_sales_invoices: number;
  overdue_purchase_invoices: number;
  recent_sales_invoices: Array<{
    id: string; invoice_no: string; customer: string;
    date: string; total: number; status: string;
  }>;
  recent_purchase_invoices: Array<{
    id: string; invoice_no: string; supplier: string;
    date: string; total: number; status: string;
  }>;
}

// ── GL Report Types ───────────────────────────────────────────────────────────

export interface TrialBalanceRow {
  account_id: string;
  account_code: string;
  account_name: string;
  account_type: AccountType;
  total_debit: number;
  total_credit: number;
  net_balance: number;
}

export interface GLTransactionRow {
  entry_id: string;
  entry_no: string;
  entry_date: string;
  description: string;
  source_module?: string;
  source_ref?: string;
  debit: number;
  credit: number;
  running_balance: number;
}

export interface GLAccountDrillDown {
  account_id: string;
  account_code: string;
  account_name: string;
  account_type: AccountType;
  opening_balance: number;
  closing_balance: number;
  total_debit: number;
  total_credit: number;
  transactions: GLTransactionRow[];
}

export interface PLLineItem {
  account_id: string;
  account_code: string;
  account_name: string;
  amount: number;
}

export interface PLStatement {
  from_date: string;
  to_date: string;
  revenue_lines: PLLineItem[];
  expense_lines: PLLineItem[];
  total_revenue: number;
  total_expenses: number;
  gross_profit: number;
  net_income: number;
}

export interface BSLineItem {
  account_id: string;
  account_code: string;
  account_name: string;
  balance: number;
}

export interface BalanceSheetStatement {
  as_of_date: string;
  asset_lines: BSLineItem[];
  liability_lines: BSLineItem[];
  equity_lines: BSLineItem[];
  total_assets: number;
  total_liabilities: number;
  total_equity: number;
  is_balanced: boolean;
}

export type PeriodStatus = "OPEN" | "CLOSED" | "LOCKED";

export interface AccountingPeriod {
  id: string;
  period_ym: string;
  fiscal_year_id?: string;
  period_start?: string;
  period_end?: string;
  status: PeriodStatus;
  closed_at?: string;
  close_notes?: string;
  locked_by_id?: string;
  locked_at?: string;
  notes?: string;
  created_at: string;
}

// ── Exchange Rate Types ───────────────────────────────────────────────────────

export type RateSource = "MANUAL" | "CBK" | "ECB" | "API";

export interface ExchangeRate {
  id: string;
  currency: string;
  rate_date: string;
  rate_to_kes: number;
  source: RateSource;
  notes?: string;
  created_at: string;
}

export interface FXConvertResult {
  from_currency: string;
  to_currency: string;
  amount: number;
  rate: number;
  converted_amount: number;
  rate_date: string;
}

export const financeApi = {
  // COA
  async listCOA(activeOnly = true): Promise<COA[]> {
    const res = await apiClient.get<COA[]>("/api/v1/finance/coa/", { params: { active_only: activeOnly } });
    return res.data;
  },
  async createCOA(data: object): Promise<COA> {
    const res = await apiClient.post<COA>("/api/v1/finance/coa/", data);
    return res.data;
  },

  // Journal
  async listJournal(params?: object): Promise<JournalEntry[]> {
    const res = await apiClient.get<JournalEntry[]>("/api/v1/finance/journal/", { params });
    return res.data;
  },
  async createJournalEntry(data: object): Promise<JournalEntry> {
    const res = await apiClient.post<JournalEntry>("/api/v1/finance/journal/", data);
    return res.data;
  },
  async postJournalEntry(id: string): Promise<JournalEntry> {
    const res = await apiClient.post<JournalEntry>(`/api/v1/finance/journal/${id}/post`);
    return res.data;
  },

  // Cash Accounts
  async listCashAccounts(activeOnly = true): Promise<CashAccount[]> {
    const res = await apiClient.get<CashAccount[]>("/api/v1/finance/cash-accounts/", { params: { active_only: activeOnly } });
    return res.data;
  },
  async createCashAccount(data: object): Promise<CashAccount> {
    const res = await apiClient.post<CashAccount>("/api/v1/finance/cash-accounts/", data);
    return res.data;
  },
  async listTransactions(accountId: string, params?: object): Promise<CashTransaction[]> {
    const res = await apiClient.get<CashTransaction[]>(`/api/v1/finance/cash-accounts/${accountId}/transactions`, { params });
    return res.data;
  },
  async addTransaction(accountId: string, data: object): Promise<CashTransaction> {
    const res = await apiClient.post<CashTransaction>(`/api/v1/finance/cash-accounts/${accountId}/transactions`, data);
    return res.data;
  },
  async clearTransaction(txId: string): Promise<CashTransaction> {
    const res = await apiClient.post<CashTransaction>(`/api/v1/finance/transactions/${txId}/clear`);
    return res.data;
  },

  // M-Pesa
  async listMpesaTransactions(params?: object): Promise<CashTransaction[]> {
    const res = await apiClient.get<CashTransaction[]>("/api/v1/finance/mpesa/transactions", { params });
    return res.data;
  },
  async listReconciliations(status?: ReconciliationStatus): Promise<MpesaReconciliation[]> {
    const res = await apiClient.get<MpesaReconciliation[]>("/api/v1/finance/mpesa/reconciliation", {
      params: status ? { status } : undefined,
    });
    return res.data;
  },
  async autoMatchMpesa(): Promise<{ matched: number; skipped: number }> {
    const res = await apiClient.post<{ matched: number; skipped: number }>("/api/v1/finance/mpesa/auto-match");
    return res.data;
  },
  async manualMatch(reconId: string, data: { invoice_id?: string; so_id?: string; matched_amount?: number; notes?: string }): Promise<MpesaReconciliation> {
    const res = await apiClient.post<MpesaReconciliation>(`/api/v1/finance/mpesa/reconciliation/${reconId}/match`, data);
    return res.data;
  },
  async markException(reconId: string, reason: string): Promise<MpesaReconciliation> {
    const res = await apiClient.post<MpesaReconciliation>(`/api/v1/finance/mpesa/reconciliation/${reconId}/exception`, null, {
      params: { reason },
    });
    return res.data;
  },

  // Costing
  async listCostEntries(params?: object): Promise<ProductionCostEntry[]> {
    const res = await apiClient.get<ProductionCostEntry[]>("/api/v1/finance/costing/entries", { params });
    return res.data;
  },
  async addCostEntry(data: object): Promise<ProductionCostEntry> {
    const res = await apiClient.post<ProductionCostEntry>("/api/v1/finance/costing/entries", data);
    return res.data;
  },
  async rollupProductionCosts(productionOrderId: string): Promise<ProductionCostEntry[]> {
    const res = await apiClient.post<ProductionCostEntry[]>(`/api/v1/finance/costing/rollup/${productionOrderId}`);
    return res.data;
  },
  async rollupProductCost(productId: string, periodYm: string): Promise<ProductCost> {
    const res = await apiClient.post<ProductCost>(`/api/v1/finance/costing/product-rollup/${productId}`, null, {
      params: { period_ym: periodYm },
    });
    return res.data;
  },
  async listProductCosts(params?: object): Promise<ProductCost[]> {
    const res = await apiClient.get<ProductCost[]>("/api/v1/finance/costing/products", { params });
    return res.data;
  },

  // Budgets
  async listBudgets(): Promise<Budget[]> {
    const res = await apiClient.get<Budget[]>("/api/v1/finance/budgets/");
    return res.data;
  },
  async getBudget(id: string): Promise<Budget> {
    const res = await apiClient.get<Budget>(`/api/v1/finance/budgets/${id}`);
    return res.data;
  },
  async createBudget(data: object): Promise<Budget> {
    const res = await apiClient.post<Budget>("/api/v1/finance/budgets/", data);
    return res.data;
  },
  async approveBudget(id: string): Promise<Budget> {
    const res = await apiClient.post<Budget>(`/api/v1/finance/budgets/${id}/approve`);
    return res.data;
  },
  async lockBudget(id: string): Promise<Budget> {
    const res = await apiClient.post<Budget>(`/api/v1/finance/budgets/${id}/lock`);
    return res.data;
  },
  async reviseBudget(id: string): Promise<Budget> {
    const res = await apiClient.post<Budget>(`/api/v1/finance/budgets/${id}/revise`);
    return res.data;
  },

  // Reports
  async cashPosition(): Promise<CashPositionRow[]> {
    const res = await apiClient.get<CashPositionRow[]>("/api/v1/finance/reports/cash-position");
    return res.data;
  },
  async mpesaSummary(fromDate: string, toDate: string): Promise<MpesaSummaryRow[]> {
    const res = await apiClient.get<MpesaSummaryRow[]>("/api/v1/finance/reports/mpesa-summary", {
      params: { from_date: fromDate, to_date: toDate },
    });
    return res.data;
  },
  async paymentChannels(fromDate: string, toDate: string): Promise<PaymentChannelRow[]> {
    const res = await apiClient.get<PaymentChannelRow[]>("/api/v1/finance/reports/payment-channels", {
      params: { from_date: fromDate, to_date: toDate },
    });
    return res.data;
  },
  async receivables(): Promise<ReceivableRow[]> {
    const res = await apiClient.get<ReceivableRow[]>("/api/v1/finance/reports/receivables");
    return res.data;
  },
  async reconciliationExceptions(): Promise<ReconciliationExceptionRow[]> {
    const res = await apiClient.get<ReconciliationExceptionRow[]>("/api/v1/finance/reports/reconciliation-exceptions");
    return res.data;
  },
  async budgetVsActual(year: number, department?: string): Promise<BudgetVsActualRow[]> {
    const res = await apiClient.get<BudgetVsActualRow[]>("/api/v1/finance/reports/budget-vs-actual", {
      params: { year, department },
    });
    return res.data;
  },
  async budgetAlerts(year: number, threshold?: number): Promise<BudgetAlertRow[]> {
    const res = await apiClient.get<BudgetAlertRow[]>("/api/v1/finance/reports/budget-alerts", {
      params: { year, threshold },
    });
    return res.data;
  },

  // ── Accounting Module ──────────────────────────────────────────────────────

  async accountingDashboard(): Promise<AccountingDashboard> {
    const res = await apiClient.get<AccountingDashboard>("/api/v1/finance/accounting/dashboard/");
    return res.data;
  },

  async listSalesInvoices(params?: {
    status?: string; customer_id?: string; from_date?: string; to_date?: string; limit?: number;
  }): Promise<SalesInvoice[]> {
    const res = await apiClient.get<SalesInvoice[]>("/api/v1/finance/accounting/sales-invoices/", { params });
    return res.data;
  },

  async getSalesInvoice(id: string): Promise<SalesInvoice> {
    const res = await apiClient.get<SalesInvoice>(`/api/v1/finance/accounting/sales-invoices/${id}`);
    return res.data;
  },

  async createCustomerPayment(invoiceId: string, data: {
    invoice_id: string; payment_date: string; amount: number; method: string;
    reference?: string; notes?: string;
  }): Promise<CustomerPayment> {
    const res = await apiClient.post<CustomerPayment>(
      `/api/v1/finance/accounting/sales-invoices/${invoiceId}/payments`, data
    );
    return res.data;
  },

  async listPurchaseInvoices(params?: {
    status?: string; supplier_id?: string; from_date?: string; to_date?: string; limit?: number;
  }): Promise<PurchaseInvoice[]> {
    const res = await apiClient.get<PurchaseInvoice[]>("/api/v1/finance/accounting/purchase-invoices/", { params });
    return res.data;
  },

  async getPurchaseInvoice(id: string): Promise<PurchaseInvoice> {
    const res = await apiClient.get<PurchaseInvoice>(`/api/v1/finance/accounting/purchase-invoices/${id}`);
    return res.data;
  },

  async createPurchaseInvoice(data: object): Promise<PurchaseInvoice> {
    const res = await apiClient.post<PurchaseInvoice>("/api/v1/finance/accounting/purchase-invoices/", data);
    return res.data;
  },

  async createPurchasePayment(invoiceId: string, data: {
    invoice_id: string; payment_date: string; amount: number; method: string;
    reference?: string; notes?: string;
  }): Promise<PurchasePayment> {
    const res = await apiClient.post<PurchasePayment>(
      `/api/v1/finance/accounting/purchase-invoices/${invoiceId}/payments`, data
    );
    return res.data;
  },

  async listAllPayments(params?: {
    payment_type?: "customer" | "supplier"; from_date?: string; to_date?: string; limit?: number;
  }): Promise<CombinedPayment[]> {
    const res = await apiClient.get<CombinedPayment[]>("/api/v1/finance/accounting/payments/", { params });
    return res.data;
  },

  async customerLedger(): Promise<CustomerLedgerRow[]> {
    const res = await apiClient.get<CustomerLedgerRow[]>("/api/v1/finance/accounting/customer-ledger/");
    return res.data;
  },

  async supplierLedger(): Promise<SupplierLedgerRow[]> {
    const res = await apiClient.get<SupplierLedgerRow[]>("/api/v1/finance/accounting/supplier-ledger/");
    return res.data;
  },

  // ── GL Reports ─────────────────────────────────────────────────────────────

  async trialBalance(params?: { from_date?: string; to_date?: string }): Promise<TrialBalanceRow[]> {
    const res = await apiClient.get<TrialBalanceRow[]>("/api/v1/finance/reports/trial-balance", { params });
    return res.data;
  },

  async profitAndLoss(fromDate: string, toDate: string): Promise<PLStatement> {
    const res = await apiClient.get<PLStatement>("/api/v1/finance/reports/profit-loss", {
      params: { from_date: fromDate, to_date: toDate },
    });
    return res.data;
  },

  async balanceSheet(asOfDate: string): Promise<BalanceSheetStatement> {
    const res = await apiClient.get<BalanceSheetStatement>("/api/v1/finance/reports/balance-sheet", {
      params: { as_of_date: asOfDate },
    });
    return res.data;
  },

  async generalLedger(accountId: string, fromDate: string, toDate: string): Promise<GLAccountDrillDown> {
    const res = await apiClient.get<GLAccountDrillDown>("/api/v1/finance/reports/general-ledger", {
      params: { account_id: accountId, from_date: fromDate, to_date: toDate },
    });
    return res.data;
  },

  // ── Accounting Periods ─────────────────────────────────────────────────────

  async listPeriods(): Promise<AccountingPeriod[]> {
    const res = await apiClient.get<AccountingPeriod[]>("/api/v1/finance/accounting/periods/");
    return res.data;
  },

  async createPeriod(data: { period_ym: string; notes?: string }): Promise<AccountingPeriod> {
    const res = await apiClient.post<AccountingPeriod>("/api/v1/finance/accounting/periods/", data);
    return res.data;
  },

  async closePeriod(id: string): Promise<AccountingPeriod> {
    const res = await apiClient.post<AccountingPeriod>(`/api/v1/finance/accounting/periods/${id}/close`);
    return res.data;
  },

  async lockPeriod(id: string): Promise<AccountingPeriod> {
    const res = await apiClient.post<AccountingPeriod>(`/api/v1/finance/accounting/periods/${id}/lock`);
    return res.data;
  },

  async listFiscalYears(): Promise<FiscalYear[]> {
    const res = await apiClient.get<FiscalYear[]>("/api/v1/finance/accounting/fiscal-years/");
    return res.data;
  },

  async createFiscalYear(data: {
    year_code: string; start_date: string; end_date: string; base_currency?: string; notes?: string;
  }): Promise<FiscalYear> {
    const res = await apiClient.post<FiscalYear>("/api/v1/finance/accounting/fiscal-years/", data);
    return res.data;
  },

  async listPostingBatches(params?: { source_module?: string; source_event?: string; limit?: number }): Promise<AccountingPostingBatch[]> {
    const res = await apiClient.get<AccountingPostingBatch[]>("/api/v1/finance/accounting/posting-batches/", { params });
    return res.data;
  },

  async listOperationalPostingEvents(params?: {
    source_module?: string; source_event?: string; status?: OperationalPostingStatus; limit?: number;
  }): Promise<OperationalPostingEvent[]> {
    const res = await apiClient.get<OperationalPostingEvent[]>(
      "/api/v1/finance/accounting/operational-posting-events/",
      { params }
    );
    return res.data;
  },

  async listPostingRules(params?: { source_module?: string }): Promise<AccountingPostingRule[]> {
    const res = await apiClient.get<AccountingPostingRule[]>("/api/v1/finance/accounting/posting-rules/", { params });
    return res.data;
  },

  async createPostingRule(data: {
    source_module: string; source_event: string; rule_name: string;
    debit_account_id?: string; credit_account_id?: string; tax_account_id?: string;
    clearing_account_id?: string; priority?: number; notes?: string;
  }): Promise<AccountingPostingRule> {
    const res = await apiClient.post<AccountingPostingRule>("/api/v1/finance/accounting/posting-rules/", data);
    return res.data;
  },

  async listInventoryAccountMappings(params?: {
    stock_type?: string; product_id?: string; material_id?: string; active_only?: boolean;
  }): Promise<InventoryAccountMapping[]> {
    const res = await apiClient.get<InventoryAccountMapping[]>(
      "/api/v1/finance/accounting/inventory-account-mappings/",
      { params }
    );
    return res.data;
  },

  async createInventoryAccountMapping(data: {
    stock_type?: string; product_id?: string; material_id?: string; category_key?: string;
    valuation_method?: string; inventory_account_id?: string; wip_account_id?: string;
    finished_goods_account_id?: string; cogs_account_id?: string; grni_account_id?: string;
    landed_cost_clearing_account_id?: string; variance_account_id?: string; scrap_account_id?: string;
    is_active?: boolean; priority?: number; notes?: string;
  }): Promise<InventoryAccountMapping> {
    const res = await apiClient.post<InventoryAccountMapping>(
      "/api/v1/finance/accounting/inventory-account-mappings/",
      data
    );
    return res.data;
  },

  async listPaymentAllocations(params?: { party_type?: "CUSTOMER" | "SUPPLIER"; limit?: number }): Promise<PaymentAllocation[]> {
    const res = await apiClient.get<PaymentAllocation[]>("/api/v1/finance/accounting/payment-allocations/", { params });
    return res.data;
  },

  async listCurrencyRevaluations(params?: { currency?: string; limit?: number }): Promise<CurrencyRevaluationRun[]> {
    const res = await apiClient.get<CurrencyRevaluationRun[]>("/api/v1/finance/accounting/currency-revaluations/", { params });
    return res.data;
  },

  // ── Exchange Rates ──────────────────────────────────────────────────────────

  async listExchangeRates(params?: { currency?: string; limit?: number }): Promise<ExchangeRate[]> {
    const res = await apiClient.get<ExchangeRate[]>("/api/v1/finance/exchange-rates/", { params });
    return res.data;
  },

  async latestExchangeRates(): Promise<ExchangeRate[]> {
    const res = await apiClient.get<ExchangeRate[]>("/api/v1/finance/exchange-rates/latest");
    return res.data;
  },

  async createExchangeRate(data: {
    currency: string; rate_date: string; rate_to_kes: number;
    source?: RateSource; notes?: string;
  }): Promise<ExchangeRate> {
    const res = await apiClient.post<ExchangeRate>("/api/v1/finance/exchange-rates/", data);
    return res.data;
  },

  async convertCurrency(amount: number, currency: string, asOfDate?: string): Promise<FXConvertResult> {
    const res = await apiClient.get<FXConvertResult>("/api/v1/finance/exchange-rates/convert", {
      params: { amount, currency, as_of_date: asOfDate },
    });
    return res.data;
  },
};

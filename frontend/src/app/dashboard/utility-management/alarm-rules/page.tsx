"use client";
import React, { useState, Fragment } from "react";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  alarmApi,
  type AlarmRule,
  type AlarmRuleCreate,
  type AlarmRuleTemplate,
  type AlarmSeverity,
  type AlarmDetectionType,
  type AlarmCategory,
  type AlarmOperator,
  type UtilityType,
  SEVERITY_SOFT_CLASS,
  DETECTION_TYPE_LABELS,
  DETECTION_TYPE_DESCRIPTIONS,
  ALARM_CATEGORY_LABELS,
  ALARM_CATEGORY_ICONS,
  OPERATOR_LABELS,
  OPERATOR_SYMBOLS,
  UTILITY_TYPE_LABELS,
  UTILITY_TYPE_ICONS,
  SEVERITY_COLOR,
} from "@/lib/utilityAlarm";

// ── Constants ─────────────────────────────────────────────────────────────────

const UTILITY_TYPES: UtilityType[] = [
  "ELECTRICITY","WATER","SOFT_WATER","PROCESS_WATER","STEAM","COMPRESSED_AIR",
  "SOLAR","NATURAL_GAS","WASTEWATER","DIESEL","CHILLED_WATER","OTHER",
];
const SEVERITIES: AlarmSeverity[] = ["INFO","WARNING","ALERT","CRITICAL"];
const DETECTION_TYPES: AlarmDetectionType[] = [
  "THRESHOLD","SUDDEN_JUMP","ROLLING_DEVIATION","SHIFT_COMPARISON","MACHINE_COMPARISON","VS_STANDARD",
];
const CATEGORIES: AlarmCategory[] = [
  "ENERGY","WATER","BOILER_STEAM","COMPRESSED_AIR","SOLAR","WASTEWATER","CHEMICAL","COMPLIANCE","COST","GENERAL",
];
const OPERATORS: AlarmOperator[] = ["GT","LT","GTE","LTE","EQ","NEQ","DELTA_PCT"];

// ── Helpers ───────────────────────────────────────────────────────────────────

const ic = "rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white w-full focus:outline-none focus:ring-2 focus:ring-blue-500";
const labelCls = "block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1";

function emptyRule(): Partial<AlarmRuleCreate> {
  return {
    rule_code: "",
    name: "",
    description: "",
    utility_type: "ELECTRICITY",
    alarm_type: "",
    source_module: "",
    alarm_category: "ENERGY",
    detection_type: "THRESHOLD",
    parameter: "",
    operator: "GT",
    threshold_value: 0,
    threshold_unit: "",
    rolling_window_hours: undefined,
    delta_pct_threshold: undefined,
    standard_value: undefined,
    severity: "WARNING",
    cooldown_minutes: 60,
    evaluation_frequency_min: 15,
    is_active: true,
    notification_emails: "",
    notification_channel: "",
    notes: "",
  };
}

// ── SeverityBadge ─────────────────────────────────────────────────────────────

function SeverityBadge({ severity }: { severity: AlarmSeverity }) {
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-bold ${SEVERITY_SOFT_CLASS[severity]}`}>
      {severity}
    </span>
  );
}

// ── StatusToggle ──────────────────────────────────────────────────────────────

function StatusToggle({ rule, onToggle }: { rule: AlarmRule; onToggle: () => void }) {
  return (
    <button
      onClick={onToggle}
      className={`px-2 py-1 rounded text-xs font-semibold transition-colors ${
        rule.is_active
          ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 hover:bg-green-200"
          : "bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400 hover:bg-gray-200"
      }`}
    >
      {rule.is_active ? "Active" : "Inactive"}
    </button>
  );
}

// ── Rule Modal ────────────────────────────────────────────────────────────────

type RuleModalMode = "create" | "edit";

function RuleModal({
  mode,
  initial,
  onClose,
  onSave,
  saving,
}: {
  mode: RuleModalMode;
  initial: Partial<AlarmRuleCreate>;
  onClose: () => void;
  onSave: (data: AlarmRuleCreate) => void;
  saving: boolean;
}) {
  const [tab, setTab] = useState<1 | 2 | 3>(1);
  const [form, setForm] = useState<Partial<AlarmRuleCreate>>(initial);

  function set<K extends keyof AlarmRuleCreate>(key: K, value: AlarmRuleCreate[K]) {
    setForm(f => ({ ...f, [key]: value }));
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    onSave(form as AlarmRuleCreate);
  }

  const tabs = [
    { id: 1 as const, label: "Basic" },
    { id: 2 as const, label: "Detection" },
    { id: 3 as const, label: "Notifications & Settings" },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-bold text-gray-900 dark:text-white">
            {mode === "create" ? "New Alarm Rule" : "Edit Alarm Rule"}
          </h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 text-xl font-bold">&times;</button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-gray-200 dark:border-gray-700">
          {tabs.map(t => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`px-5 py-3 text-sm font-medium transition-colors ${
                tab === t.id
                  ? "border-b-2 border-blue-600 text-blue-600"
                  : "text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* Form body */}
        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-5 space-y-4">

          {/* Tab 1 — Basic */}
          {tab === 1 && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className={labelCls}>Rule Code *</label>
                  <input className={ic} value={form.rule_code ?? ""} onChange={e => set("rule_code", e.target.value)} placeholder="e.g. ELEC-HIGH-DEMAND" required />
                </div>
                <div>
                  <label className={labelCls}>Name *</label>
                  <input className={ic} value={form.name ?? ""} onChange={e => set("name", e.target.value)} placeholder="Alarm rule name" required />
                </div>
              </div>
              <div>
                <label className={labelCls}>Description</label>
                <textarea className={ic + " resize-none"} rows={2} value={form.description ?? ""} onChange={e => set("description", e.target.value)} placeholder="Optional description" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className={labelCls}>Utility Type *</label>
                  <select className={ic} value={form.utility_type ?? "ELECTRICITY"} onChange={e => set("utility_type", e.target.value as UtilityType)}>
                    {UTILITY_TYPES.map(u => (
                      <option key={u} value={u}>{UTILITY_TYPE_ICONS[u]} {UTILITY_TYPE_LABELS[u]}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className={labelCls}>Alarm Category *</label>
                  <select className={ic} value={form.alarm_category ?? "ENERGY"} onChange={e => set("alarm_category", e.target.value as AlarmCategory)}>
                    {CATEGORIES.map(c => (
                      <option key={c} value={c}>{ALARM_CATEGORY_ICONS[c]} {ALARM_CATEGORY_LABELS[c]}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className={labelCls}>Alarm Type</label>
                  <input className={ic} value={form.alarm_type ?? ""} onChange={e => set("alarm_type", e.target.value)} placeholder="e.g. BOILER_EFFICIENCY_DECLINE" />
                </div>
                <div>
                  <label className={labelCls}>Source Module</label>
                  <input className={ic} value={form.source_module ?? ""} onChange={e => set("source_module", e.target.value)} placeholder="e.g. steam, compressor" />
                </div>
              </div>
              <div>
                <label className={labelCls}>Parameter *</label>
                <input className={ic} value={form.parameter ?? ""} onChange={e => set("parameter", e.target.value)} placeholder="Field name being monitored, e.g. boiler_efficiency_pct" required />
              </div>
              <div className="flex items-center gap-3 pt-1">
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Active</label>
                <button
                  type="button"
                  onClick={() => set("is_active", !form.is_active)}
                  className={`relative w-12 h-6 rounded-full transition-colors ${form.is_active ? "bg-green-500" : "bg-gray-300 dark:bg-gray-600"}`}
                >
                  <span className={`absolute top-1 w-4 h-4 rounded-full bg-white shadow transition-transform ${form.is_active ? "translate-x-7" : "translate-x-1"}`} />
                </button>
              </div>
            </div>
          )}

          {/* Tab 2 — Detection */}
          {tab === 2 && (
            <div className="space-y-4">
              <div>
                <label className={labelCls}>Detection Type *</label>
                <select className={ic} value={form.detection_type ?? "THRESHOLD"} onChange={e => set("detection_type", e.target.value as AlarmDetectionType)}>
                  {DETECTION_TYPES.map(d => (
                    <option key={d} value={d}>{DETECTION_TYPE_LABELS[d]}</option>
                  ))}
                </select>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{DETECTION_TYPE_DESCRIPTIONS[form.detection_type ?? "THRESHOLD"]}</p>
              </div>
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className={labelCls}>Operator *</label>
                  <select className={ic} value={form.operator ?? "GT"} onChange={e => set("operator", e.target.value as AlarmOperator)}>
                    {OPERATORS.map(op => (
                      <option key={op} value={op}>{OPERATOR_LABELS[op]}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className={labelCls}>Threshold Value *</label>
                  <input className={ic} type="number" step="any" value={form.threshold_value ?? ""} onChange={e => set("threshold_value", parseFloat(e.target.value))} required />
                </div>
                <div>
                  <label className={labelCls}>Threshold Unit</label>
                  <input className={ic} value={form.threshold_unit ?? ""} onChange={e => set("threshold_unit", e.target.value)} placeholder="kWh, m³, %" />
                </div>
              </div>

              {/* Conditional fields */}
              {form.detection_type === "ROLLING_DEVIATION" && (
                <div>
                  <label className={labelCls}>Rolling Window (hours)</label>
                  <input className={ic} type="number" step="1" min="1" value={form.rolling_window_hours ?? ""} onChange={e => set("rolling_window_hours", parseInt(e.target.value))} placeholder="e.g. 24" />
                </div>
              )}
              {form.detection_type === "SUDDEN_JUMP" && (
                <div>
                  <label className={labelCls}>Delta % Threshold</label>
                  <input className={ic} type="number" step="any" value={form.delta_pct_threshold ?? ""} onChange={e => set("delta_pct_threshold", parseFloat(e.target.value))} placeholder="e.g. 30 for 30% jump" />
                </div>
              )}
              {form.detection_type === "VS_STANDARD" && (
                <div>
                  <label className={labelCls}>Standard Value</label>
                  <input className={ic} type="number" step="any" value={form.standard_value ?? ""} onChange={e => set("standard_value", parseFloat(e.target.value))} placeholder="Benchmark / standard value" />
                </div>
              )}
            </div>
          )}

          {/* Tab 3 — Notifications & Settings */}
          {tab === 3 && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className={labelCls}>Severity *</label>
                  <select className={ic} value={form.severity ?? "WARNING"} onChange={e => set("severity", e.target.value as AlarmSeverity)}>
                    {SEVERITIES.map(s => (
                      <option key={s} value={s}>{s}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className={labelCls}>Cooldown (minutes)</label>
                  <input className={ic} type="number" step="1" min="0" value={form.cooldown_minutes ?? 60} onChange={e => set("cooldown_minutes", parseInt(e.target.value))} />
                </div>
              </div>
              <div>
                <label className={labelCls}>Evaluation Frequency (minutes)</label>
                <input className={ic} type="number" step="1" min="1" value={form.evaluation_frequency_min ?? 15} onChange={e => set("evaluation_frequency_min", parseInt(e.target.value))} />
              </div>
              <div>
                <label className={labelCls}>Notification Emails</label>
                <textarea className={ic + " resize-none"} rows={2} value={form.notification_emails ?? ""} onChange={e => set("notification_emails", e.target.value)} placeholder="Comma-separated email addresses" />
              </div>
              <div>
                <label className={labelCls}>Notification Channel</label>
                <input className={ic} value={form.notification_channel ?? ""} onChange={e => set("notification_channel", e.target.value)} placeholder="e.g. #alerts-slack, teams-webhook" />
              </div>
              <div>
                <label className={labelCls}>Notes</label>
                <textarea className={ic + " resize-none"} rows={3} value={form.notes ?? ""} onChange={e => set("notes", e.target.value)} placeholder="Internal notes about this rule" />
              </div>
            </div>
          )}

          {/* Navigation / submit */}
          <div className="flex items-center justify-between pt-2 border-t border-gray-200 dark:border-gray-700 mt-4">
            <div className="flex gap-2">
              {tab > 1 && (
                <button type="button" onClick={() => setTab((tab - 1) as 1 | 2 | 3)}
                  className="px-4 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700">
                  ← Back
                </button>
              )}
              {tab < 3 && (
                <button type="button" onClick={() => setTab((tab + 1) as 2 | 3)}
                  className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700">
                  Next →
                </button>
              )}
            </div>
            {tab === 3 && (
              <button
                type="submit"
                disabled={saving}
                className="px-5 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {saving ? "Saving…" : mode === "create" ? "Create Rule" : "Update Rule"}
              </button>
            )}
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Templates Modal ───────────────────────────────────────────────────────────

function TemplatesModal({
  onClose,
  onUse,
}: {
  onClose: () => void;
  onUse: (tpl: AlarmRuleTemplate) => void;
}) {
  const { data: templates = [], isLoading } = useQuery({
    queryKey: ["alarm-rule-templates"],
    queryFn: () => alarmApi.getRuleTemplates(),
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl w-full max-w-4xl max-h-[90vh] flex flex-col">
        <div className="flex items-center justify-between p-5 border-b border-gray-200 dark:border-gray-700">
          <div>
            <h2 className="text-lg font-bold text-gray-900 dark:text-white">Predefined Templates</h2>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">Select a template to pre-fill the rule creation form</p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 text-xl font-bold">&times;</button>
        </div>
        <div className="flex-1 overflow-y-auto p-5">
          {isLoading ? (
            <p className="text-center text-gray-400 py-10">Loading templates…</p>
          ) : templates.length === 0 ? (
            <p className="text-center text-gray-400 py-10">No templates available.</p>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {templates.map(tpl => (
                <div key={tpl.template_key} className="border border-gray-200 dark:border-gray-700 rounded-xl p-4 hover:border-blue-400 dark:hover:border-blue-500 transition-colors">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="text-xl">{ALARM_CATEGORY_ICONS[tpl.alarm_category]}</span>
                      <span className="text-sm font-semibold text-gray-900 dark:text-white leading-tight">{tpl.name}</span>
                    </div>
                    <span
                      className="text-[10px] font-bold px-1.5 py-0.5 rounded"
                      style={{ backgroundColor: SEVERITY_COLOR[tpl.severity] + "25", color: SEVERITY_COLOR[tpl.severity] }}
                    >
                      {tpl.severity}
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mb-3 leading-relaxed">{tpl.description}</p>
                  <div className="space-y-1 text-xs text-gray-600 dark:text-gray-400">
                    <div className="flex items-center gap-1.5">
                      <span>{UTILITY_TYPE_ICONS[tpl.utility_type]}</span>
                      <span>{UTILITY_TYPE_LABELS[tpl.utility_type]}</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span className="text-gray-400">⚙</span>
                      <span>{DETECTION_TYPE_LABELS[tpl.detection_type]}</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span className="text-gray-400">📐</span>
                      <span className="font-mono">{tpl.parameter} {OPERATOR_SYMBOLS[tpl.operator]} {tpl.threshold_value} {tpl.threshold_unit}</span>
                    </div>
                  </div>
                  <button
                    onClick={() => onUse(tpl)}
                    className="mt-3 w-full px-3 py-1.5 text-xs bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium"
                  >
                    Use Template
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Delete Confirm ────────────────────────────────────────────────────────────

function DeleteConfirm({ rule, onClose, onDelete, deleting }: {
  rule: AlarmRule; onClose: () => void; onDelete: () => void; deleting: boolean;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl w-full max-w-md p-6">
        <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-2">Delete Rule?</h3>
        <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
          Are you sure you want to delete <strong>{rule.name}</strong> ({rule.rule_code})? This action cannot be undone.
        </p>
        <div className="flex justify-end gap-3">
          <button onClick={onClose} className="px-4 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700">Cancel</button>
          <button onClick={onDelete} disabled={deleting} className="px-4 py-2 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50">
            {deleting ? "Deleting…" : "Delete"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Toast ─────────────────────────────────────────────────────────────────────

function Toast({ message, type, onClose }: { message: string; type: "success" | "error"; onClose: () => void }) {
  return (
    <div className={`fixed bottom-6 right-6 z-[100] flex items-center gap-3 px-4 py-3 rounded-xl shadow-lg text-sm font-medium ${
      type === "success" ? "bg-green-600 text-white" : "bg-red-600 text-white"
    }`}>
      <span>{message}</span>
      <button onClick={onClose} className="font-bold text-white/80 hover:text-white">&times;</button>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function AlarmRulesPage() {
  const qc = useQueryClient();

  const [filterUtility, setFilterUtility] = useState<string>("");
  const [filterSeverity, setFilterSeverity] = useState<string>("");
  const [filterDetection, setFilterDetection] = useState<string>("");
  const [filterActive, setFilterActive] = useState<string>("");

  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editRule, setEditRule] = useState<AlarmRule | null>(null);
  const [deleteRule, setDeleteRule] = useState<AlarmRule | null>(null);
  const [showTemplates, setShowTemplates] = useState(false);
  const [templateInitial, setTemplateInitial] = useState<Partial<AlarmRuleCreate> | null>(null);

  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);

  function showToast(message: string, type: "success" | "error") {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  }

  const rulesQ = useQuery({
    queryKey: ["alarm-rules", filterUtility, filterSeverity, filterDetection, filterActive],
    queryFn: () => alarmApi.listRules({
      utility_type: filterUtility ? filterUtility as UtilityType : undefined,
      severity: filterSeverity ? filterSeverity as AlarmSeverity : undefined,
      detection_type: filterDetection ? filterDetection as AlarmDetectionType : undefined,
      is_active: filterActive === "" ? undefined : filterActive === "true",
      limit: 200,
    }),
  });

  const rules = rulesQ.data ?? [];

  const invalidate = () => qc.invalidateQueries({ queryKey: ["alarm-rules"] });

  const createMut = useMutation({
    mutationFn: (data: AlarmRuleCreate) => alarmApi.createRule(data),
    onSuccess: () => { invalidate(); setShowCreateModal(false); setTemplateInitial(null); showToast("Rule created successfully", "success"); },
    onError: () => showToast("Failed to create rule", "error"),
  });

  const updateMut = useMutation({
    mutationFn: ({ id, data }: { id: string; data: AlarmRuleCreate }) => alarmApi.updateRule(id, data),
    onSuccess: () => { invalidate(); setEditRule(null); showToast("Rule updated successfully", "success"); },
    onError: () => showToast("Failed to update rule", "error"),
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => alarmApi.deleteRule(id),
    onSuccess: () => { invalidate(); setDeleteRule(null); showToast("Rule deleted", "success"); },
    onError: () => showToast("Failed to delete rule", "error"),
  });

  const toggleMut = useMutation({
    mutationFn: (id: string) => alarmApi.toggleRule(id),
    onSuccess: () => invalidate(),
    onError: () => showToast("Failed to toggle rule status", "error"),
  });

  function handleUseTemplate(tpl: AlarmRuleTemplate) {
    const initial: Partial<AlarmRuleCreate> = {
      rule_code: tpl.template_key,
      name: tpl.name,
      description: tpl.description,
      utility_type: tpl.utility_type,
      alarm_type: tpl.alarm_type,
      source_module: tpl.source_module,
      alarm_category: tpl.alarm_category,
      detection_type: tpl.detection_type,
      parameter: tpl.parameter,
      operator: tpl.operator,
      threshold_value: tpl.threshold_value,
      threshold_unit: tpl.threshold_unit,
      severity: tpl.severity,
      rolling_window_hours: tpl.rolling_window_hours ?? undefined,
      delta_pct_threshold: tpl.delta_pct_threshold ?? undefined,
      standard_value: tpl.standard_value ?? undefined,
      cooldown_minutes: 60,
      evaluation_frequency_min: 15,
      is_active: true,
    };
    setTemplateInitial(initial);
    setShowTemplates(false);
    setShowCreateModal(true);
  }

  const selectCls = "rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500";

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6 space-y-5">
      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <Link href="/dashboard/utility-management/alarm-center" className="text-sm text-gray-500 hover:text-blue-600">← Alarm Center</Link>
            <span className="text-gray-300 dark:text-gray-600">|</span>
            <Link href="/dashboard/utility-management/kpi-center" className="text-sm text-gray-500 hover:text-blue-600">KPI Center</Link>
          </div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white" style={{ borderLeft: "4px solid #ef4444", paddingLeft: 12 }}>
            Alarm Rules
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Configure detection rules for utility anomalies and threshold breaches.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setShowTemplates(true)}
            className="px-4 py-2 text-sm border border-blue-600 text-blue-600 rounded-lg hover:bg-blue-50 dark:hover:bg-blue-900/20 font-medium"
          >
            Browse Templates
          </button>
          <button
            onClick={() => { setTemplateInitial(null); setShowCreateModal(true); }}
            className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium"
          >
            + New Rule
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-4">
        <div>
          <p className="text-[10px] font-medium text-gray-500 uppercase mb-1">Utility Type</p>
          <select className={selectCls} value={filterUtility} onChange={e => setFilterUtility(e.target.value)}>
            <option value="">All Types</option>
            {UTILITY_TYPES.map(u => <option key={u} value={u}>{UTILITY_TYPE_LABELS[u]}</option>)}
          </select>
        </div>
        <div>
          <p className="text-[10px] font-medium text-gray-500 uppercase mb-1">Severity</p>
          <select className={selectCls} value={filterSeverity} onChange={e => setFilterSeverity(e.target.value)}>
            <option value="">All Severities</option>
            {SEVERITIES.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
        <div>
          <p className="text-[10px] font-medium text-gray-500 uppercase mb-1">Detection Type</p>
          <select className={selectCls} value={filterDetection} onChange={e => setFilterDetection(e.target.value)}>
            <option value="">All Detection Types</option>
            {DETECTION_TYPES.map(d => <option key={d} value={d}>{DETECTION_TYPE_LABELS[d]}</option>)}
          </select>
        </div>
        <div>
          <p className="text-[10px] font-medium text-gray-500 uppercase mb-1">Status</p>
          <select className={selectCls} value={filterActive} onChange={e => setFilterActive(e.target.value)}>
            <option value="">All</option>
            <option value="true">Active</option>
            <option value="false">Inactive</option>
          </select>
        </div>
        {(filterUtility || filterSeverity || filterDetection || filterActive) && (
          <div className="flex items-end">
            <button
              onClick={() => { setFilterUtility(""); setFilterSeverity(""); setFilterDetection(""); setFilterActive(""); }}
              className="px-3 py-2 text-xs text-gray-500 hover:text-red-600 border border-gray-300 dark:border-gray-600 rounded-lg"
            >
              Clear Filters
            </button>
          </div>
        )}
      </div>

      {/* Table */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        {rulesQ.isLoading ? (
          <p className="text-center text-gray-400 py-14 text-sm">Loading rules…</p>
        ) : rules.length === 0 ? (
          <div className="text-center py-14">
            <p className="text-gray-400 text-sm mb-3">No alarm rules found.</p>
            <button onClick={() => setShowCreateModal(true)} className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg">
              + Create First Rule
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 dark:bg-gray-700/50 border-b border-gray-200 dark:border-gray-700">
                <tr>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Rule Code</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Name</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Utility</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Detection</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Parameter</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Threshold</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Severity</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Status</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Events</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                {rules.map(rule => (
                  <tr key={rule.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/30 transition-colors">
                    <td className="px-4 py-3">
                      <code className="text-xs bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 px-2 py-0.5 rounded font-mono">
                        {rule.rule_code}
                      </code>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1.5">
                        <span title={ALARM_CATEGORY_LABELS[rule.alarm_category]}>
                          {ALARM_CATEGORY_ICONS[rule.alarm_category]}
                        </span>
                        <div>
                          <p className="font-medium text-gray-900 dark:text-white text-xs">{rule.name}</p>
                          {rule.source_module && (
                            <p className="text-[10px] text-gray-400">{rule.source_module}</p>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-xs text-gray-700 dark:text-gray-300">
                        {UTILITY_TYPE_ICONS[rule.utility_type]} {UTILITY_TYPE_LABELS[rule.utility_type]}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-300">
                        {DETECTION_TYPE_LABELS[rule.detection_type]}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <code className="text-xs text-gray-600 dark:text-gray-400 font-mono">{rule.parameter}</code>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-xs text-gray-700 dark:text-gray-300 font-mono whitespace-nowrap">
                        {OPERATOR_SYMBOLS[rule.operator]} {rule.threshold_value}{rule.threshold_unit ? ` ${rule.threshold_unit}` : ""}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <SeverityBadge severity={rule.severity} />
                    </td>
                    <td className="px-4 py-3">
                      <StatusToggle rule={rule} onToggle={() => toggleMut.mutate(rule.id)} />
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold ${
                        rule.event_count > 0
                          ? "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
                          : "bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400"
                      }`}>
                        {rule.event_count}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => setEditRule(rule)}
                          className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 text-xs font-medium"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => setDeleteRule(rule)}
                          className="text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-300 text-xs font-medium"
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Count */}
      {!rulesQ.isLoading && rules.length > 0 && (
        <p className="text-xs text-gray-400 text-right">{rules.length} rule{rules.length !== 1 ? "s" : ""}</p>
      )}

      {/* Create modal */}
      {showCreateModal && (
        <RuleModal
          mode="create"
          initial={templateInitial ?? emptyRule()}
          onClose={() => { setShowCreateModal(false); setTemplateInitial(null); }}
          onSave={data => createMut.mutate(data)}
          saving={createMut.isPending}
        />
      )}

      {/* Edit modal */}
      {editRule && (
        <RuleModal
          mode="edit"
          initial={{ ...editRule }}
          onClose={() => setEditRule(null)}
          onSave={data => updateMut.mutate({ id: editRule.id, data })}
          saving={updateMut.isPending}
        />
      )}

      {/* Delete confirm */}
      {deleteRule && (
        <DeleteConfirm
          rule={deleteRule}
          onClose={() => setDeleteRule(null)}
          onDelete={() => deleteMut.mutate(deleteRule.id)}
          deleting={deleteMut.isPending}
        />
      )}

      {/* Templates modal */}
      {showTemplates && (
        <TemplatesModal
          onClose={() => setShowTemplates(false)}
          onUse={handleUseTemplate}
        />
      )}

      {/* Toast */}
      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
    </div>
  );
}

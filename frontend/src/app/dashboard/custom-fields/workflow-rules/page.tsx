"use client";
import { useEffect, useState } from "react";
import {
  customFieldsApi, WorkflowRule, EntityType,
  ENTITY_LABEL, WF_TRIGGER_LABEL, WF_ACTION_LABEL,
} from "@/lib/custom_fields";

const ENTITY_TYPES: EntityType[] = [
  "customer", "supplier", "product", "sales_order", "purchase_order",
  "production_order", "employee", "asset", "contract", "crm_record", "expense", "lot",
];

const TRIGGER_EVENTS = Object.keys(WF_TRIGGER_LABEL) as Array<keyof typeof WF_TRIGGER_LABEL>;
const ACTION_TYPES = Object.keys(WF_ACTION_LABEL) as Array<keyof typeof WF_ACTION_LABEL>;

const CONDITION_OPERATORS = ["equals", "not_equals", "contains", "greater_than", "less_than", "is_empty", "is_not_empty"];

interface RuleForm {
  rule_name: string;
  entity_type: EntityType;
  trigger_event: string;
  condition_field: string;
  condition_operator: string;
  condition_value: string;
  action_type: string;
  action_message: string;
  notes: string;
  active_flag: boolean;
}

const BLANK: RuleForm = {
  rule_name: "",
  entity_type: "customer",
  trigger_event: "record_created",
  condition_field: "",
  condition_operator: "equals",
  condition_value: "",
  action_type: "send_notification",
  action_message: "",
  notes: "",
  active_flag: true,
};

export default function WorkflowRulesPage() {
  const [rules, setRules] = useState<WorkflowRule[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterEntity, setFilterEntity] = useState("");
  const [showModal, setShowModal] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [form, setForm] = useState<RuleForm>(BLANK);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const data = await customFieldsApi.listWorkflowRules({
        entity_type: filterEntity || undefined,
      });
      setRules(data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [filterEntity]);

  const openCreate = () => {
    setForm(BLANK);
    setEditId(null);
    setError("");
    setShowModal(true);
  };

  const openEdit = (r: WorkflowRule) => {
    setForm({
      rule_name: r.rule_name,
      entity_type: r.entity_type,
      trigger_event: r.trigger_event,
      condition_field: r.condition_field ?? "",
      condition_operator: r.condition_operator ?? "equals",
      condition_value: r.condition_value ?? "",
      action_type: r.action_type,
      action_message: (r.action_payload as Record<string, string>)?.message ?? "",
      notes: r.notes ?? "",
      active_flag: r.active_flag,
    });
    setEditId(r.rule_id);
    setError("");
    setShowModal(true);
  };

  const save = async () => {
    if (!form.rule_name.trim()) { setError("Rule name required"); return; }
    setSaving(true);
    setError("");
    try {
      const payload = {
        rule_name: form.rule_name,
        entity_type: form.entity_type,
        trigger_event: form.trigger_event,
        condition_field: form.condition_field || null,
        condition_operator: form.condition_field ? form.condition_operator : null,
        condition_value: form.condition_field ? form.condition_value : null,
        action_type: form.action_type,
        action_payload: form.action_message ? { message: form.action_message } : {},
        active_flag: form.active_flag,
        notes: form.notes || null,
      };
      if (editId) {
        await customFieldsApi.updateWorkflowRule(editId, payload);
      } else {
        await customFieldsApi.createWorkflowRule(payload);
      }
      setShowModal(false);
      await load();
    } catch {
      setError("Failed to save rule.");
    } finally {
      setSaving(false);
    }
  };

  const toggleActive = async (r: WorkflowRule) => {
    await customFieldsApi.updateWorkflowRule(r.rule_id, { active_flag: !r.active_flag });
    await load();
  };

  const deleteRule = async (id: string) => {
    if (!confirm("Delete this workflow rule?")) return;
    await customFieldsApi.deleteWorkflowRule(id);
    await load();
  };

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Workflow Rules</h1>
          <p className="text-xs text-gray-500 mt-0.5">
            Trigger-based automation rules for custom field events. Define what happens when records change.
          </p>
        </div>
        <button
          onClick={openCreate}
          className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          + New Rule
        </button>
      </div>

      {/* Trigger concepts info strip */}
      <div className="bg-blue-50 border border-blue-100 rounded-lg px-4 py-3">
        <p className="text-xs text-blue-700 font-medium mb-1">How Workflow Rules Work</p>
        <p className="text-xs text-blue-600">
          Rules fire when a trigger event occurs on a record of the selected module.
          Optionally add a condition to narrow when the rule applies.
          Then define the action (notify, set field, call webhook, etc.).
          Rules are evaluated by backend automation — the engine stub is wired for future full execution.
        </p>
      </div>

      <div className="flex gap-3 flex-wrap items-center">
        <select
          className="border rounded px-2 py-1.5 text-sm"
          value={filterEntity}
          onChange={e => setFilterEntity(e.target.value)}
        >
          <option value="">All Modules</option>
          {ENTITY_TYPES.map(t => <option key={t} value={t}>{ENTITY_LABEL[t]}</option>)}
        </select>
        <span className="text-xs text-gray-500 self-center">{rules.length} rules</span>
      </div>

      {loading ? (
        <p className="text-sm text-gray-500">Loading…</p>
      ) : rules.length === 0 ? (
        <div className="bg-white border rounded-lg p-12 text-center text-gray-400">
          <p className="text-2xl mb-2">⚡</p>
          <p className="text-sm">No workflow rules yet. Create your first rule.</p>
          <button onClick={openCreate} className="mt-3 text-xs text-blue-600 hover:underline">
            Create rule →
          </button>
        </div>
      ) : (
        <div className="bg-white border rounded-lg shadow-sm overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                {["Rule Name", "Module", "Trigger", "Condition", "Action", "Status", "Actions"].map(h => (
                  <th key={h} className="px-4 py-2 text-left text-xs font-semibold text-gray-600">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y">
              {rules.map(r => (
                <tr key={r.rule_id} className={`hover:bg-gray-50 ${!r.active_flag ? "opacity-60" : ""}`}>
                  <td className="px-4 py-3 font-medium text-gray-800">
                    {r.rule_name}
                    {r.notes && <p className="text-xs text-gray-400 font-normal truncate max-w-xs">{r.notes}</p>}
                  </td>
                  <td className="px-4 py-3 text-gray-600 text-xs">{ENTITY_LABEL[r.entity_type] ?? r.entity_type}</td>
                  <td className="px-4 py-3">
                    <span className="text-xs bg-amber-50 text-amber-700 rounded px-2 py-0.5">
                      {WF_TRIGGER_LABEL[r.trigger_event] ?? r.trigger_event}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-600">
                    {r.condition_field ? (
                      <span>
                        <code className="bg-gray-100 px-1 rounded">{r.condition_field}</code>
                        {" "}{r.condition_operator}{" "}
                        <code className="bg-gray-100 px-1 rounded">{r.condition_value}</code>
                      </span>
                    ) : (
                      <span className="text-gray-400">Always</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-xs bg-green-50 text-green-700 rounded px-2 py-0.5">
                      {WF_ACTION_LABEL[r.action_type] ?? r.action_type}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`text-xs rounded-full px-2 py-0.5 ${r.active_flag ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                      {r.active_flag ? "active" : "disabled"}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex gap-2">
                      <button onClick={() => openEdit(r)} className="text-xs text-blue-600 hover:underline">Edit</button>
                      <button onClick={() => toggleActive(r)} className="text-xs text-yellow-600 hover:underline">
                        {r.active_flag ? "Disable" : "Enable"}
                      </button>
                      <button onClick={() => deleteRule(r.rule_id)} className="text-xs text-red-500 hover:underline">Delete</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Create/Edit Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
            <div className="px-6 py-4 border-b flex items-center justify-between">
              <h2 className="text-base font-semibold text-gray-900">
                {editId ? "Edit Workflow Rule" : "New Workflow Rule"}
              </h2>
              <button onClick={() => setShowModal(false)} className="text-gray-400 hover:text-gray-600 text-xl">×</button>
            </div>
            <div className="p-6 space-y-4">
              {error && <p className="text-xs text-red-500 bg-red-50 border border-red-200 rounded px-3 py-2">{error}</p>}

              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Rule Name <span className="text-red-400">*</span></label>
                <input
                  type="text"
                  value={form.rule_name}
                  onChange={e => setForm(f => ({ ...f, rule_name: e.target.value }))}
                  placeholder="e.g. Notify sales team on new CRM record"
                  className="w-full border rounded px-3 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Module</label>
                  <select
                    value={form.entity_type}
                    onChange={e => setForm(f => ({ ...f, entity_type: e.target.value as EntityType }))}
                    className="w-full border rounded px-3 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none"
                  >
                    {ENTITY_TYPES.map(t => <option key={t} value={t}>{ENTITY_LABEL[t]}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Trigger Event</label>
                  <select
                    value={form.trigger_event}
                    onChange={e => setForm(f => ({ ...f, trigger_event: e.target.value }))}
                    className="w-full border rounded px-3 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none"
                  >
                    {TRIGGER_EVENTS.map(t => <option key={t} value={t}>{WF_TRIGGER_LABEL[t]}</option>)}
                  </select>
                </div>
              </div>

              <div className="border rounded-lg p-4 space-y-3 bg-gray-50">
                <p className="text-xs font-semibold text-gray-600">Condition (optional)</p>
                <div>
                  <label className="block text-xs text-gray-500 mb-1">Field Code (if condition applies to a specific field)</label>
                  <input
                    type="text"
                    value={form.condition_field}
                    onChange={e => setForm(f => ({ ...f, condition_field: e.target.value }))}
                    placeholder="e.g. customer_tier"
                    className="w-full border rounded px-3 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none bg-white"
                  />
                </div>
                {form.condition_field && (
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs text-gray-500 mb-1">Operator</label>
                      <select
                        value={form.condition_operator}
                        onChange={e => setForm(f => ({ ...f, condition_operator: e.target.value }))}
                        className="w-full border rounded px-3 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none bg-white"
                      >
                        {CONDITION_OPERATORS.map(o => <option key={o} value={o}>{o.replace("_", " ")}</option>)}
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs text-gray-500 mb-1">Value</label>
                      <input
                        type="text"
                        value={form.condition_value}
                        onChange={e => setForm(f => ({ ...f, condition_value: e.target.value }))}
                        placeholder="e.g. gold"
                        className="w-full border rounded px-3 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none bg-white"
                      />
                    </div>
                  </div>
                )}
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Action</label>
                <select
                  value={form.action_type}
                  onChange={e => setForm(f => ({ ...f, action_type: e.target.value }))}
                  className="w-full border rounded px-3 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none"
                >
                  {ACTION_TYPES.map(t => <option key={t} value={t}>{WF_ACTION_LABEL[t]}</option>)}
                </select>
              </div>

              {form.action_type === "send_notification" && (
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Notification Message</label>
                  <textarea
                    value={form.action_message}
                    onChange={e => setForm(f => ({ ...f, action_message: e.target.value }))}
                    rows={2}
                    placeholder="e.g. New high-value customer record created"
                    className="w-full border rounded px-3 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none resize-none"
                  />
                </div>
              )}

              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Notes</label>
                <textarea
                  value={form.notes}
                  onChange={e => setForm(f => ({ ...f, notes: e.target.value }))}
                  rows={2}
                  placeholder="Internal notes about this rule…"
                  className="w-full border rounded px-3 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none resize-none"
                />
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="active_flag"
                  checked={form.active_flag}
                  onChange={e => setForm(f => ({ ...f, active_flag: e.target.checked }))}
                  className="h-4 w-4 rounded border-gray-300 text-blue-600"
                />
                <label htmlFor="active_flag" className="text-sm text-gray-700">Active</label>
              </div>
            </div>
            <div className="px-6 pb-5 flex gap-3">
              <button
                onClick={save}
                disabled={saving}
                className="flex-1 rounded bg-blue-600 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {saving ? "Saving…" : editId ? "Update Rule" : "Create Rule"}
              </button>
              <button
                onClick={() => setShowModal(false)}
                className="flex-1 rounded border py-2 text-sm text-gray-600 hover:bg-gray-50"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="flex gap-3 text-xs">
        <a href="/dashboard/custom-fields" className="text-blue-600 hover:underline">Custom Fields Dashboard</a>
        <span className="text-gray-300">|</span>
        <a href="/dashboard/custom-fields/form-builder" className="text-blue-600 hover:underline">Form Builder</a>
      </div>
    </div>
  );
}

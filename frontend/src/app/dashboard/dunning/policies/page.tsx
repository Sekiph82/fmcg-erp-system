"use client";
import { useState, useEffect } from "react";
import { dunningApi, DunningPolicy, DunningLevel, DunningActionType } from "@/lib/dunning";

export default function PoliciesPage() {
  const [policies, setPolicies] = useState<DunningPolicy[]>([]);
  const [levels, setLevels] = useState<Record<string, DunningLevel[]>>({});
  const [selected, setSelected] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [addingLevel, setAddingLevel] = useState(false);
  const [form, setForm] = useState({ policy_code: "", policy_name: "", default_flag: false, auto_credit_hold_days: "", notes: "" });
  const [lvlForm, setLvlForm] = useState({
    level_no: 1, level_name: "", days_overdue_from: 0, action_type: "EMAIL" as DunningActionType,
    auto_send_flag: true, apply_credit_hold_flag: false, template_code: "",
  });

  const load = () => dunningApi.listPolicies().then(setPolicies);
  useEffect(() => { load(); }, []);

  const loadLevels = (policyId: string) => {
    setSelected(policyId);
    if (!levels[policyId]) {
      dunningApi.listLevels(policyId).then((lvls) => setLevels((prev) => ({ ...prev, [policyId]: lvls })));
    }
  };

  const createPolicy = async () => {
    await dunningApi.createPolicy({
      ...form,
      auto_credit_hold_days: form.auto_credit_hold_days ? Number(form.auto_credit_hold_days) : undefined,
    } as any);
    setCreating(false);
    setForm({ policy_code: "", policy_name: "", default_flag: false, auto_credit_hold_days: "", notes: "" });
    load();
  };

  const addLevel = async () => {
    if (!selected) return;
    await dunningApi.addLevel(selected, lvlForm as any);
    setAddingLevel(false);
    dunningApi.listLevels(selected).then((lvls) => setLevels((prev) => ({ ...prev, [selected]: lvls })));
  };

  const selectedPolicy = policies.find((p) => p.id === selected);

  const ACTION_COLORS: Record<DunningActionType, string> = {
    EMAIL: "bg-blue-100 text-blue-800",
    SMS: "bg-green-100 text-green-800",
    WHATSAPP: "bg-teal-100 text-teal-800",
    TASK: "bg-gray-100 text-gray-700",
    CALL_REMINDER: "bg-purple-100 text-purple-800",
    CREDIT_HOLD: "bg-red-100 text-red-800",
    MANAGER_ESCALATION: "bg-orange-100 text-orange-800",
    FINAL_NOTICE: "bg-red-200 text-red-900",
    LEGAL_REVIEW_FLAG: "bg-red-300 text-red-900",
    PORTAL_NOTIFICATION: "bg-indigo-100 text-indigo-800",
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">Dunning Policies</h1>
        <button onClick={() => setCreating(true)} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">
          + New Policy
        </button>
      </div>

      <div className="grid grid-cols-3 gap-5">
        {/* Policy list */}
        <div className="col-span-1 space-y-2">
          {policies.map((p) => (
            <button key={p.id} onClick={() => loadLevels(p.id)}
              className={`w-full text-left p-4 rounded-xl border transition ${selected === p.id ? "border-blue-500 bg-blue-50" : "border-gray-200 bg-white hover:border-blue-300"}`}>
              <div className="flex items-center justify-between">
                <span className="font-semibold text-sm text-gray-900">{p.policy_name}</span>
                <div className="flex gap-1">
                  {p.default_flag && <span className="px-1.5 py-0.5 bg-green-100 text-green-700 rounded text-xs">DEFAULT</span>}
                  {!p.active_flag && <span className="px-1.5 py-0.5 bg-gray-100 text-gray-500 rounded text-xs">INACTIVE</span>}
                </div>
              </div>
              <div className="text-xs text-gray-500 mt-0.5">{p.policy_code}</div>
              {p.auto_credit_hold_days && (
                <div className="text-xs text-red-600 mt-1">Auto-hold at {p.auto_credit_hold_days}d overdue</div>
              )}
            </button>
          ))}
          {policies.length === 0 && <div className="text-gray-400 text-sm p-3">No policies yet.</div>}
        </div>

        {/* Level editor */}
        <div className="col-span-2">
          {!selected ? (
            <div className="bg-white rounded-xl border border-gray-200 p-8 text-center text-gray-400">Select a policy to view its dunning levels.</div>
          ) : (
            <div className="bg-white rounded-xl border border-gray-200">
              <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
                <div>
                  <h2 className="font-semibold text-gray-900">{selectedPolicy?.policy_name} — Dunning Levels</h2>
                  <p className="text-xs text-gray-500 mt-0.5">Ordered escalation steps from polite reminder to legal review</p>
                </div>
                <button onClick={() => setAddingLevel(true)}
                  className="px-3 py-1.5 bg-blue-600 text-white rounded-lg text-xs font-medium hover:bg-blue-700">
                  + Add Level
                </button>
              </div>
              <div className="divide-y divide-gray-100">
                {(levels[selected] || []).map((lvl) => (
                  <div key={lvl.id} className="px-5 py-4 flex items-center gap-4">
                    <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center text-sm font-bold text-blue-700 shrink-0">
                      {lvl.level_no}
                    </div>
                    <div className="flex-1">
                      <div className="font-medium text-sm text-gray-900">{lvl.level_name}</div>
                      <div className="text-xs text-gray-500 mt-0.5">
                        {lvl.days_overdue_from}+ days overdue
                        {lvl.days_overdue_to ? ` → ${lvl.days_overdue_to}d` : ""}
                      </div>
                    </div>
                    <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${ACTION_COLORS[lvl.action_type]}`}>
                      {lvl.action_type.replace(/_/g, " ")}
                    </span>
                    {lvl.apply_credit_hold_flag && (
                      <span className="px-2 py-0.5 bg-red-100 text-red-700 rounded-full text-xs">HOLD</span>
                    )}
                    {lvl.auto_send_flag ? (
                      <span className="text-xs text-green-600">Auto</span>
                    ) : (
                      <span className="text-xs text-gray-400">Manual</span>
                    )}
                  </div>
                ))}
                {(levels[selected] || []).length === 0 && (
                  <div className="px-5 py-8 text-center text-gray-400 text-sm">No levels defined. Add your first dunning level.</div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Create Policy Modal */}
      {creating && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-2xl p-6 w-full max-w-md space-y-4">
            <h2 className="text-lg font-bold text-gray-900">New Dunning Policy</h2>
            <div>
              <label className="text-xs font-medium text-gray-700">Policy Code</label>
              <input value={form.policy_code} onChange={(e) => setForm({ ...form, policy_code: e.target.value })}
                className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" placeholder="e.g. STANDARD-30" />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-700">Policy Name</label>
              <input value={form.policy_name} onChange={(e) => setForm({ ...form, policy_name: e.target.value })}
                className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-700">Auto Credit Hold After (days overdue)</label>
              <input type="number" value={form.auto_credit_hold_days} onChange={(e) => setForm({ ...form, auto_credit_hold_days: e.target.value })}
                className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" placeholder="30" />
            </div>
            <div className="flex items-center gap-2">
              <input type="checkbox" checked={form.default_flag} onChange={(e) => setForm({ ...form, default_flag: e.target.checked })} />
              <label className="text-sm text-gray-700">Set as default policy</label>
            </div>
            <div>
              <label className="text-xs font-medium text-gray-700">Notes</label>
              <textarea value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })}
                rows={2} className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
            </div>
            <div className="flex justify-end gap-3">
              <button onClick={() => setCreating(false)} className="px-4 py-2 border border-gray-300 rounded-lg text-sm">Cancel</button>
              <button onClick={createPolicy} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium">Create</button>
            </div>
          </div>
        </div>
      )}

      {/* Add Level Modal */}
      {addingLevel && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-2xl p-6 w-full max-w-md space-y-4">
            <h2 className="text-lg font-bold text-gray-900">Add Dunning Level</h2>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-medium text-gray-700">Level #</label>
                <input type="number" value={lvlForm.level_no} onChange={(e) => setLvlForm({ ...lvlForm, level_no: Number(e.target.value) })}
                  className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="text-xs font-medium text-gray-700">Days Overdue From</label>
                <input type="number" value={lvlForm.days_overdue_from} onChange={(e) => setLvlForm({ ...lvlForm, days_overdue_from: Number(e.target.value) })}
                  className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
              </div>
            </div>
            <div>
              <label className="text-xs font-medium text-gray-700">Level Name</label>
              <input value={lvlForm.level_name} onChange={(e) => setLvlForm({ ...lvlForm, level_name: e.target.value })}
                className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" placeholder="e.g. Polite Reminder" />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-700">Action Type</label>
              <select value={lvlForm.action_type} onChange={(e) => setLvlForm({ ...lvlForm, action_type: e.target.value as DunningActionType })}
                className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
                {(["EMAIL", "SMS", "WHATSAPP", "CALL_REMINDER", "CREDIT_HOLD", "MANAGER_ESCALATION", "FINAL_NOTICE", "LEGAL_REVIEW_FLAG"] as DunningActionType[]).map((a) => (
                  <option key={a} value={a}>{a.replace(/_/g, " ")}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs font-medium text-gray-700">Template Code (optional)</label>
              <input value={lvlForm.template_code} onChange={(e) => setLvlForm({ ...lvlForm, template_code: e.target.value })}
                className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
            </div>
            <div className="flex gap-4">
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={lvlForm.auto_send_flag} onChange={(e) => setLvlForm({ ...lvlForm, auto_send_flag: e.target.checked })} />
                Auto-send
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={lvlForm.apply_credit_hold_flag} onChange={(e) => setLvlForm({ ...lvlForm, apply_credit_hold_flag: e.target.checked })} />
                Apply Credit Hold
              </label>
            </div>
            <div className="flex justify-end gap-3">
              <button onClick={() => setAddingLevel(false)} className="px-4 py-2 border border-gray-300 rounded-lg text-sm">Cancel</button>
              <button onClick={addLevel} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium">Add Level</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

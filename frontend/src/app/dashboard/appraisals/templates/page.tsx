"use client";
import { useEffect, useState } from "react";
import { appraisalsApi, AppraisalTemplate } from "@/lib/appraisals";
import { tx } from "@/lib/i18n/core";

export default function AppraisalTemplatesPage() {
  const [templates, setTemplates] = useState<AppraisalTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    template_code: "", template_name: "", department_id: "", role_id: "",
    employee_grade_id: "", kpi_weight_pct: 60, competency_weight_pct: 40,
    active_flag: true, notes: "",
  });

  const load = () => appraisalsApi.listTemplates().then(setTemplates).finally(() => setLoading(false));
  useEffect(() => { load(); }, []);

  const submit = async () => {
    if (form.kpi_weight_pct + form.competency_weight_pct !== 100) {
      alert(tx("KPI + Competency weights must sum to 100%"));
      return;
    }
    await appraisalsApi.createTemplate({
      ...form,
      department_id: form.department_id || undefined,
      role_id: form.role_id || undefined,
      employee_grade_id: form.employee_grade_id || undefined,
      notes: form.notes || undefined,
    });
    setShowForm(false);
    load();
  };

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">{tx("Appraisal Templates")}</h1>
        <button
          onClick={() => setShowForm(true)}
          className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          {tx("+ New Template")}
        </button>
      </div>

      {showForm && (
        <div className="bg-white border rounded-lg p-4 shadow-sm space-y-3">
          <h2 className="font-semibold text-gray-800">{tx("New Appraisal Template")}</h2>
          <div className="grid grid-cols-2 gap-3">
            {(["template_code","template_name","department_id","role_id","employee_grade_id"] as const).map((f) => (
              <div key={f}>
                <label className="text-xs text-gray-500 capitalize">{f.replace(/_/g," ")}</label>
                <input
                  className="w-full border rounded px-2 py-1 text-sm mt-1"
                  value={String(form[f])}
                  onChange={(e) => setForm({ ...form, [f]: e.target.value })}
                />
              </div>
            ))}
            <div>
              <label className="text-xs text-gray-500">{tx("KPI Weight %")}</label>
              <input
                type="number" min={0} max={100}
                className="w-full border rounded px-2 py-1 text-sm mt-1"
                value={form.kpi_weight_pct}
                onChange={(e) => setForm({ ...form, kpi_weight_pct: Number(e.target.value), competency_weight_pct: 100 - Number(e.target.value) })}
              />
            </div>
            <div>
              <label className="text-xs text-gray-500">{tx("Competency Weight % (auto)")}</label>
              <input
                type="number" readOnly
                className="w-full border rounded px-2 py-1 text-sm mt-1 bg-gray-50"
                value={form.competency_weight_pct}
              />
            </div>
            <div className="col-span-2">
              <label className="text-xs text-gray-500">{tx("Notes")}</label>
              <textarea
                className="w-full border rounded px-2 py-1 text-sm mt-1"
                rows={2}
                value={form.notes}
                onChange={(e) => setForm({ ...form, notes: e.target.value })}
              />
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={form.active_flag}
                onChange={(e) => setForm({ ...form, active_flag: e.target.checked })}
              />
              <label className="text-sm text-gray-700">{tx("Active")}</label>
            </div>
          </div>
          <div className="flex gap-2">
            <button onClick={submit} className="rounded bg-blue-600 px-4 py-1.5 text-sm text-white hover:bg-blue-700">{tx("Save")}</button>
            <button onClick={() => setShowForm(false)} className="rounded border px-4 py-1.5 text-sm text-gray-600 hover:bg-gray-50">{tx("Cancel")}</button>
          </div>
        </div>
      )}

      {loading ? (
        <p className="text-gray-500 text-sm">{tx("Loading…")}</p>
      ) : (
        <div className="bg-white border rounded-lg shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                {[tx("Code"),tx("Name"),tx("Dept"),tx("Role"),tx("Grade"),tx("KPI %"),tx("Comp %"),tx("Active")].map((h) => (
                  <th key={h} className="px-4 py-2 text-left text-xs font-semibold text-gray-600">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y">
              {templates.map((t) => (
                <tr key={t.template_id} className="hover:bg-gray-50">
                  <td className="px-4 py-2 font-mono text-xs">{t.template_code}</td>
                  <td className="px-4 py-2 font-medium text-gray-800">{t.template_name}</td>
                  <td className="px-4 py-2 text-gray-600">{t.department_id ?? "—"}</td>
                  <td className="px-4 py-2 text-gray-600">{t.role_id ?? "—"}</td>
                  <td className="px-4 py-2 text-gray-600">{t.employee_grade_id ?? "—"}</td>
                  <td className="px-4 py-2 text-blue-700 font-semibold">{t.kpi_weight_pct}%</td>
                  <td className="px-4 py-2 text-purple-700 font-semibold">{t.competency_weight_pct}%</td>
                  <td className="px-4 py-2">
                    <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${t.active_flag ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                      {t.active_flag ? tx("Active") : tx("Inactive")}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {templates.length === 0 && <p className="text-center text-gray-400 py-8 text-sm">{tx("No templates yet.")}</p>}
        </div>
      )}
    </div>
  );
}

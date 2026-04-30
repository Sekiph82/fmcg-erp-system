"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { appraisalsApi, AppraisalPeriod, AppraisalTemplate } from "@/lib/appraisals";

const DEFAULT_COMPETENCIES = [
  "Teamwork","Leadership","Communication","Problem Solving",
  "Attendance & Discipline","Technical Skill","Quality Focus","Safety Compliance",
];

export default function NewAppraisalPage() {
  const router = useRouter();
  const [periods, setPeriods] = useState<AppraisalPeriod[]>([]);
  const [templates, setTemplates] = useState<AppraisalTemplate[]>([]);
  const [form, setForm] = useState({
    appraisal_period_id: "", employee_id: "", employee_name: "",
    manager_id: "", manager_name: "", department_id: "", department_name: "",
    template_id: "", notes: "",
  });
  const [kpiLines, setKpiLines] = useState([
    { kpi_name: "", target_value: "", unit: "", weight_pct: "" }
  ]);
  const [compLines, setCompLines] = useState(
    DEFAULT_COMPETENCIES.map((c) => ({ competency_name: c, weight_pct: String((100 / DEFAULT_COMPETENCIES.length).toFixed(1)) }))
  );
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    Promise.all([appraisalsApi.listPeriods("active"), appraisalsApi.listTemplates(true)])
      .then(([p, t]) => { setPeriods(p); setTemplates(t); });
  }, []);

  const submit = async () => {
    if (!form.appraisal_period_id || !form.employee_id) {
      alert("Period and Employee ID are required");
      return;
    }
    setSaving(true);
    try {
      const rec = await appraisalsApi.createRecord({
        ...form,
        template_id: form.template_id || undefined,
      });
      const appraisalId = rec.appraisal_id;
      const validKpi = kpiLines.filter((l) => l.kpi_name && l.weight_pct);
      for (const l of validKpi) {
        await appraisalsApi.addKPILine(appraisalId, {
          kpi_name: l.kpi_name,
          target_value: l.target_value ? Number(l.target_value) : undefined,
          unit: l.unit || undefined,
          weight_pct: Number(l.weight_pct),
        });
      }
      const validComp = compLines.filter((l) => l.competency_name && l.weight_pct);
      for (const l of validComp) {
        await appraisalsApi.addCompetencyLine(appraisalId, {
          competency_name: l.competency_name,
          weight_pct: Number(l.weight_pct),
        });
      }
      router.push("/dashboard/appraisals/records");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-6 space-y-6 max-w-4xl">
      <h1 className="text-xl font-bold text-gray-900">New Appraisal</h1>

      <div className="bg-white border rounded-lg p-4 shadow-sm space-y-3">
        <h2 className="font-semibold text-gray-800">Employee & Period</h2>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-gray-500">Appraisal Period *</label>
            <select
              className="w-full border rounded px-2 py-1 text-sm mt-1"
              value={form.appraisal_period_id}
              onChange={(e) => setForm({ ...form, appraisal_period_id: e.target.value })}
            >
              <option value="">Select period…</option>
              {periods.map((p) => <option key={p.appraisal_period_id} value={p.appraisal_period_id}>{p.period_name}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-500">Template</label>
            <select
              className="w-full border rounded px-2 py-1 text-sm mt-1"
              value={form.template_id}
              onChange={(e) => setForm({ ...form, template_id: e.target.value })}
            >
              <option value="">No template</option>
              {templates.map((t) => <option key={t.template_id} value={t.template_id}>{t.template_name}</option>)}
            </select>
          </div>
          {(["employee_id","employee_name","manager_id","manager_name","department_id","department_name"] as const).map((f) => (
            <div key={f}>
              <label className="text-xs text-gray-500 capitalize">{f.replace(/_/g," ")}{f === "employee_id" ? " *" : ""}</label>
              <input
                className="w-full border rounded px-2 py-1 text-sm mt-1"
                value={form[f]}
                onChange={(e) => setForm({ ...form, [f]: e.target.value })}
              />
            </div>
          ))}
          <div className="col-span-2">
            <label className="text-xs text-gray-500">Notes</label>
            <textarea className="w-full border rounded px-2 py-1 text-sm mt-1" rows={2}
              value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
          </div>
        </div>
      </div>

      <div className="bg-white border rounded-lg p-4 shadow-sm space-y-3">
        <div className="flex justify-between items-center">
          <h2 className="font-semibold text-gray-800">KPI Lines</h2>
          <button
            onClick={() => setKpiLines([...kpiLines, { kpi_name: "", target_value: "", unit: "", weight_pct: "" }])}
            className="text-xs text-blue-600 hover:underline"
          >
            + Add KPI
          </button>
        </div>
        {kpiLines.map((l, i) => (
          <div key={i} className="grid grid-cols-4 gap-2">
            <input placeholder="KPI Name *" className="border rounded px-2 py-1 text-sm col-span-2"
              value={l.kpi_name} onChange={(e) => { const n=[...kpiLines]; n[i].kpi_name=e.target.value; setKpiLines(n); }} />
            <input placeholder="Target" type="number" className="border rounded px-2 py-1 text-sm"
              value={l.target_value} onChange={(e) => { const n=[...kpiLines]; n[i].target_value=e.target.value; setKpiLines(n); }} />
            <input placeholder="Weight %" type="number" className="border rounded px-2 py-1 text-sm"
              value={l.weight_pct} onChange={(e) => { const n=[...kpiLines]; n[i].weight_pct=e.target.value; setKpiLines(n); }} />
          </div>
        ))}
        <p className="text-xs text-gray-400">Total KPI weight: {kpiLines.reduce((s,l)=>s+Number(l.weight_pct||0),0)}%</p>
      </div>

      <div className="bg-white border rounded-lg p-4 shadow-sm space-y-3">
        <h2 className="font-semibold text-gray-800">Competency Lines</h2>
        {compLines.map((l, i) => (
          <div key={i} className="grid grid-cols-4 gap-2">
            <input placeholder="Competency *" className="border rounded px-2 py-1 text-sm col-span-3"
              value={l.competency_name} onChange={(e) => { const n=[...compLines]; n[i].competency_name=e.target.value; setCompLines(n); }} />
            <input placeholder="Weight %" type="number" className="border rounded px-2 py-1 text-sm"
              value={l.weight_pct} onChange={(e) => { const n=[...compLines]; n[i].weight_pct=e.target.value; setCompLines(n); }} />
          </div>
        ))}
        <p className="text-xs text-gray-400">Total competency weight: {compLines.reduce((s,l)=>s+Number(l.weight_pct||0),0).toFixed(1)}%</p>
      </div>

      <div className="flex gap-2">
        <button
          onClick={submit}
          disabled={saving}
          className="rounded bg-blue-600 px-6 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {saving ? "Saving…" : "Create Appraisal"}
        </button>
        <button onClick={() => router.back()} className="rounded border px-6 py-2 text-sm text-gray-600 hover:bg-gray-50">
          Cancel
        </button>
      </div>
    </div>
  );
}

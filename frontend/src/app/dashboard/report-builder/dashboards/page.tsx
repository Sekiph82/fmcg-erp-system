"use client";
import { useEffect, useState } from "react";
import { reportBuilderApi, Dashboard, Report, ChartType, CHART_TYPES, CHART_LABEL } from "@/lib/report_builder";

export default function DashboardsPage() {
  const [dashboards, setDashboards] = useState<Dashboard[]>([]);
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [selected, setSelected] = useState<Dashboard | null>(null);
  const [showWidgetForm, setShowWidgetForm] = useState(false);
  const [form, setForm] = useState({ dashboard_code: "", dashboard_name: "", description: "", visibility: "team" });
  const [widgetForm, setWidgetForm] = useState({
    report_id: "", widget_title: "", chart_type: "table" as ChartType,
    x_axis_field: "", y_axis_field: "", position: 0, width: 6,
  });

  const load = () =>
    Promise.all([reportBuilderApi.listDashboards(), reportBuilderApi.listReports()])
      .then(([d, r]) => { setDashboards(d); setReports(r); }).finally(() => setLoading(false));
  useEffect(() => { load(); }, []);

  const createDash = async () => {
    await reportBuilderApi.createDashboard({ ...form, description: form.description || undefined });
    setShowForm(false);
    load();
  };

  const openDash = async (d: Dashboard) => {
    const fresh = await reportBuilderApi.getDashboard(d.dashboard_id);
    setSelected(fresh);
  };

  const addWidget = async () => {
    if (!selected) return;
    await reportBuilderApi.addWidget(selected.dashboard_id, {
      report_id: widgetForm.report_id || undefined,
      widget_title: widgetForm.widget_title || undefined,
      chart_type: widgetForm.chart_type,
      x_axis_field: widgetForm.x_axis_field || undefined,
      y_axis_field: widgetForm.y_axis_field || undefined,
      position: widgetForm.position,
      width: widgetForm.width,
    });
    setShowWidgetForm(false);
    const fresh = await reportBuilderApi.getDashboard(selected.dashboard_id);
    setSelected(fresh);
  };

  const removeWidget = async (widgetId: string) => {
    await reportBuilderApi.deleteWidget(widgetId);
    if (selected) {
      const fresh = await reportBuilderApi.getDashboard(selected.dashboard_id);
      setSelected(fresh);
    }
  };

  const CHART_ICONS: Record<ChartType, string> = {
    table: "⊞", bar: "📊", line: "📈", pie: "🥧", kpi: "💡", area: "📉", scatter: "⋯"
  };

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">Dashboards</h1>
        <button onClick={() => setShowForm(true)}
          className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
          + New Dashboard
        </button>
      </div>

      {showForm && (
        <div className="bg-white border rounded-lg p-4 shadow-sm space-y-3">
          <h2 className="font-semibold text-gray-800">New Dashboard</h2>
          <div className="grid grid-cols-2 gap-3">
            {(["dashboard_code","dashboard_name"] as const).map(f => (
              <div key={f}><label className="text-xs text-gray-500 capitalize">{f.replace(/_/g," ")}</label>
                <input className="w-full border rounded px-2 py-1 text-sm mt-1" value={form[f]}
                  onChange={(e) => setForm({ ...form, [f]: e.target.value })} /></div>
            ))}
            <div><label className="text-xs text-gray-500">Visibility</label>
              <select className="w-full border rounded px-2 py-1 text-sm mt-1" value={form.visibility}
                onChange={(e) => setForm({ ...form, visibility: e.target.value })}>
                {["private","team","global"].map(v => <option key={v} value={v}>{v}</option>)}
              </select></div>
            <div className="col-span-2"><label className="text-xs text-gray-500">Description</label>
              <textarea className="w-full border rounded px-2 py-1 text-sm mt-1" rows={2} value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })} /></div>
          </div>
          <div className="flex gap-2">
            <button onClick={createDash} className="rounded bg-blue-600 px-4 py-1.5 text-sm text-white hover:bg-blue-700">Create</button>
            <button onClick={() => setShowForm(false)} className="rounded border px-4 py-1.5 text-sm text-gray-600 hover:bg-gray-50">Cancel</button>
          </div>
        </div>
      )}

      {loading ? <p className="text-gray-500 text-sm">Loading…</p> : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {dashboards.map(d => (
            <div key={d.dashboard_id} className="bg-white border rounded-lg p-4 shadow-sm cursor-pointer hover:shadow-md"
              onClick={() => openDash(d)}>
              <p className="font-semibold text-gray-800">{d.dashboard_name}</p>
              <p className="text-xs text-gray-400 mt-0.5">{d.dashboard_code} · {d.visibility}</p>
              {d.description && <p className="text-sm text-gray-500 mt-1">{d.description}</p>}
              <div className="mt-2 flex gap-1 flex-wrap">
                {d.widgets.map(w => (
                  <span key={w.widget_id} className="text-xs bg-gray-100 text-gray-600 rounded px-2 py-0.5">
                    {CHART_ICONS[w.chart_type]} {w.widget_title ?? CHART_LABEL[w.chart_type]}
                  </span>
                ))}
                {d.widgets.length === 0 && <span className="text-xs text-gray-400">No widgets</span>}
              </div>
            </div>
          ))}
          {dashboards.length === 0 && <p className="text-gray-400 text-sm col-span-3 text-center py-8">No dashboards yet.</p>}
        </div>
      )}

      {selected && (
        <div className="fixed inset-0 bg-black/50 flex items-start justify-center z-50 p-4 overflow-auto">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl my-4 p-6 space-y-4">
            <div className="flex justify-between items-start">
              <div>
                <h2 className="text-lg font-bold text-gray-900">{selected.dashboard_name}</h2>
                <p className="text-xs text-gray-400">{selected.dashboard_code} · {selected.visibility}</p>
              </div>
              <div className="flex gap-2">
                <button onClick={() => setShowWidgetForm(true)}
                  className="rounded bg-blue-600 px-3 py-1.5 text-xs text-white hover:bg-blue-700">+ Add Widget</button>
                <button onClick={() => setSelected(null)} className="text-gray-400 hover:text-gray-700 text-xl">✕</button>
              </div>
            </div>

            {showWidgetForm && (
              <div className="bg-gray-50 border rounded-lg p-3 space-y-3">
                <h3 className="text-sm font-semibold text-gray-800">Add Widget</h3>
                <div className="grid grid-cols-2 gap-3">
                  <div><label className="text-xs text-gray-500">Report</label>
                    <select className="w-full border rounded px-2 py-1 text-sm mt-1" value={widgetForm.report_id}
                      onChange={(e) => setWidgetForm({ ...widgetForm, report_id: e.target.value })}>
                      <option value="">No report</option>
                      {reports.map(r => <option key={r.report_id} value={r.report_id}>{r.report_name}</option>)}
                    </select></div>
                  <div><label className="text-xs text-gray-500">Chart Type</label>
                    <select className="w-full border rounded px-2 py-1 text-sm mt-1" value={widgetForm.chart_type}
                      onChange={(e) => setWidgetForm({ ...widgetForm, chart_type: e.target.value as ChartType })}>
                      {CHART_TYPES.map(t => <option key={t} value={t}>{CHART_LABEL[t]}</option>)}
                    </select></div>
                  <div><label className="text-xs text-gray-500">Widget Title</label>
                    <input className="w-full border rounded px-2 py-1 text-sm mt-1" value={widgetForm.widget_title}
                      onChange={(e) => setWidgetForm({ ...widgetForm, widget_title: e.target.value })} /></div>
                  <div><label className="text-xs text-gray-500">Width (1-12)</label>
                    <input type="number" min={1} max={12} className="w-full border rounded px-2 py-1 text-sm mt-1"
                      value={widgetForm.width} onChange={(e) => setWidgetForm({ ...widgetForm, width: Number(e.target.value) })} /></div>
                  <div><label className="text-xs text-gray-500">X Axis Field</label>
                    <input className="w-full border rounded px-2 py-1 text-sm mt-1" value={widgetForm.x_axis_field}
                      onChange={(e) => setWidgetForm({ ...widgetForm, x_axis_field: e.target.value })} /></div>
                  <div><label className="text-xs text-gray-500">Y Axis Field</label>
                    <input className="w-full border rounded px-2 py-1 text-sm mt-1" value={widgetForm.y_axis_field}
                      onChange={(e) => setWidgetForm({ ...widgetForm, y_axis_field: e.target.value })} /></div>
                </div>
                <div className="flex gap-2">
                  <button onClick={addWidget} className="rounded bg-blue-600 px-3 py-1.5 text-xs text-white hover:bg-blue-700">Add</button>
                  <button onClick={() => setShowWidgetForm(false)} className="rounded border px-3 py-1.5 text-xs text-gray-600 hover:bg-gray-50">Cancel</button>
                </div>
              </div>
            )}

            <div className="grid grid-cols-2 gap-3">
              {selected.widgets.map(w => (
                <div key={w.widget_id} className="bg-gray-50 border rounded-lg p-3">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-medium text-gray-800 text-sm">
                      {CHART_ICONS[w.chart_type]} {w.widget_title ?? CHART_LABEL[w.chart_type]}
                    </span>
                    <button onClick={() => removeWidget(w.widget_id)} className="text-red-400 hover:text-red-600 text-xs">Remove</button>
                  </div>
                  <div className="text-xs text-gray-500 space-y-0.5">
                    <p>Type: {CHART_LABEL[w.chart_type]}</p>
                    {w.report_id && <p>Report linked</p>}
                    {w.x_axis_field && <p>X: {w.x_axis_field} · Y: {w.y_axis_field}</p>}
                    <p>Width: {w.width} cols</p>
                  </div>
                  {w.report_id && (
                    <a href={`/dashboard/report-builder/viewer?id=${w.report_id}`}
                      className="inline-block mt-2 text-xs text-blue-600 hover:underline">View Report →</a>
                  )}
                </div>
              ))}
            </div>
            {selected.widgets.length === 0 && <p className="text-gray-400 text-sm text-center py-4">No widgets yet. Add one above.</p>}
          </div>
        </div>
      )}
    </div>
  );
}

"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { advProductionApi } from "@/lib/productionAdvanced";
import { extractApiError } from "@/lib/inventory";
import { Table } from "@/components/ui/Table";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { ToastContainer } from "@/components/ui/Toast";
import { useToast } from "@/hooks/useToast";
import { ImportModal } from "@/components/import/ImportModal";
import { PageHelpTooltip } from "@/components/help/PageHelpTooltip";

const fmt = (v?: number | null) => v != null ? `${(Number(v)*100).toFixed(1)}%` : "—";
const oeeColor = (v?: number | null) => !v ? "text-gray-500" : Number(v)>=0.85?"text-green-600":Number(v)>=0.65?"text-yellow-600":"text-red-600";

const today = new Date().toISOString().slice(0,10);

export default function OEEPage() {
  const qc = useQueryClient();
  const { toasts, toast, dismiss } = useToast();
  const [open, setOpen]       = useState(false);
  const [deletingId, setDel]  = useState<string|null>(null);
  const [showSummary, setShowSummary] = useState(false);
  const [showInsights, setShowInsights] = useState(false);
  const [form, setForm] = useState({ oee_id:"", work_center_id:"", machine_id:"", record_date:today, planned_production_time_min:"480", actual_production_time_min:"", downtime_min:"0", total_units_produced:"", good_units_produced:"", availability:"", performance:"", quality:"", oee_score:"" });

  const { data: wcs     = [] } = useQuery({ queryKey:["work-centers"],  queryFn:()=>advProductionApi.listWorkCenters() });
  const { data: items   = [], isLoading } = useQuery({ queryKey:["oee"], queryFn:()=>advProductionApi.listOEE() });
  const { data: summary = [] } = useQuery({ queryKey:["oee-summary"],   queryFn:()=>advProductionApi.oeeeSummary(), enabled: showSummary });
  const { data: insights } = useQuery({ queryKey:["ai-insights"],       queryFn:()=>advProductionApi.aiInsights(), enabled: showInsights });

  const lowOEE    = items.filter(i=>i.is_low_oee).length;
  const highDT    = items.filter(i=>i.is_high_downtime).length;
  const avgOEE    = items.length ? items.reduce((s,i)=>s+Number(i.oee_score??0),0)/items.length : null;

  const create = useMutation({
    mutationFn:()=>advProductionApi.createOEE({
      ...form,
      work_center_id:form.work_center_id||undefined,
      planned_production_time_min: parseInt(form.planned_production_time_min)||480,
      actual_production_time_min:  form.actual_production_time_min  ? parseInt(form.actual_production_time_min)  : undefined,
      downtime_min:                form.downtime_min                ? parseInt(form.downtime_min)                : 0,
      total_units_produced:        form.total_units_produced        ? parseInt(form.total_units_produced)        : undefined,
      good_units_produced:         form.good_units_produced         ? parseInt(form.good_units_produced)         : undefined,
      availability:                form.availability                ? parseFloat(form.availability)              : undefined,
      performance:                 form.performance                 ? parseFloat(form.performance)               : undefined,
      quality:                     form.quality                     ? parseFloat(form.quality)                   : undefined,
      oee_score:                   form.oee_score                   ? parseFloat(form.oee_score)                 : undefined,
    }),
    onSuccess:()=>{ qc.invalidateQueries({queryKey:["oee"]}); qc.invalidateQueries({queryKey:["oee-summary"]}); setOpen(false); toast("success","Saved","OEE record added."); },
    onError:(e)=>toast("error","Failed",extractApiError(e))
  });
  const del = useMutation({ mutationFn:(id:string)=>advProductionApi.deleteOEE(id), onSuccess:()=>{ qc.invalidateQueries({queryKey:["oee"]}); setDel(null); toast("success","Deleted",""); }, onError:(e)=>toast("error","Failed",extractApiError(e)) });

  const severityVariant = (s:string) => s==="HIGH"?"red":s==="MEDIUM"?"yellow":"blue";

  return (
    <div>
      <ToastContainer toasts={toasts} onDismiss={dismiss}/>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">OEE Tracking</h1>
          <p className="text-sm text-gray-500 mt-1">
            Avg OEE: <strong className={oeeColor(avgOEE)}>{avgOEE!=null?`${(avgOEE*100).toFixed(1)}%`:"—"}</strong>
            &nbsp;·&nbsp;<span className="text-red-600">{lowOEE} below 65%</span>
            &nbsp;·&nbsp;<span className="text-yellow-600">{highDT} high downtime</span>
          </p>
        </div>
        <div className="flex gap-2 items-center">
          <PageHelpTooltip topic="production-oee" />
          <ImportModal module="oee_records" onSuccess={()=>qc.invalidateQueries({queryKey:["oee"]})}/>
          <Button variant="secondary" onClick={()=>{ setShowInsights(v=>!v); setShowSummary(false); }}>{showInsights?"Hide AI Insights":"AI Insights"}</Button>
          <Button variant="secondary" onClick={()=>{ setShowSummary(v=>!v); setShowInsights(false); }}>{showSummary?"Hide Summary":"KPI Summary"}</Button>
          <Button onClick={()=>setOpen(true)}>+ Add OEE Record</Button>
        </div>
      </div>

      {/* AI Insights */}
      {showInsights && (
        <div className="mb-6 rounded-xl border border-indigo-200 bg-indigo-50 p-4">
          <h2 className="text-sm font-semibold text-indigo-900 mb-3">AI Production Insights</h2>
          {!insights ? <p className="text-xs text-indigo-600">Loading…</p> : insights.insights.length===0 ? <p className="text-xs text-indigo-600">No anomalies or issues detected.</p> : (
            <div className="space-y-2">
              {insights.insights.map((ins,i)=>(
                <div key={i} className="flex gap-3 items-start text-xs">
                  <Badge label={ins.severity} variant={severityVariant(ins.severity)}/>
                  <span className="text-indigo-800 font-medium">{ins.type.replace(/_/g," ")}</span>
                  <span className="text-indigo-700">{ins.recommendation}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* KPI Summary */}
      {showSummary && (
        <div className="mb-6 rounded-xl border border-gray-200 bg-gray-50 p-4">
          <h2 className="text-sm font-semibold text-gray-800 mb-3">OEE Summary by Work Center</h2>
          {summary.length===0 ? <p className="text-xs text-gray-500">No data.</p> : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead><tr className="text-gray-500 border-b"><th className="text-left py-1">Work Center</th><th>Availability</th><th>Performance</th><th>Quality</th><th>OEE</th><th>Downtime (min)</th></tr></thead>
                <tbody>{summary.map((r,i)=>(
                  <tr key={i} className="border-b">
                    <td className="py-1 font-medium">{r.work_center_name??r.work_center_id}</td>
                    <td className="text-center">{fmt(r.avg_availability)}</td>
                    <td className="text-center">{fmt(r.avg_performance)}</td>
                    <td className="text-center">{fmt(r.avg_quality)}</td>
                    <td className={`text-center font-semibold ${oeeColor(r.avg_oee)}`}>{fmt(r.avg_oee)}</td>
                    <td className="text-center">{r.total_downtime_min?.toLocaleString()}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {isLoading ? <div className="flex justify-center py-16"><div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent"/></div> : (
        <Table keyField="id" data={items} emptyMessage="No OEE records yet." columns={[
          { header:"OEE ID",      accessor:(r)=><span className="font-mono text-xs font-medium">{r.oee_id}</span> },
          { header:"Work Center", accessor:(r)=>r.work_center_name??r.work_center_id },
          { header:"Machine ID",  accessor:(r)=>r.machine_id??"—" },
          { header:"Date",        accessor:(r)=>r.record_date },
          { header:"Shift",       accessor:(r)=>r.shift_name??"—" },
          { header:"Planned (min)", accessor:(r)=>r.planned_production_time_min },
          { header:"Downtime (min)",accessor:(r)=>r.downtime_min??0 },
          { header:"Availability",  accessor:(r)=><span className={oeeColor(r.availability)}>{fmt(r.availability)}</span> },
          { header:"Performance",   accessor:(r)=><span className={oeeColor(r.performance)}>{fmt(r.performance)}</span> },
          { header:"Quality",       accessor:(r)=><span className={oeeColor(r.quality)}>{fmt(r.quality)}</span> },
          { header:"OEE",           accessor:(r)=><span className={`font-bold ${oeeColor(r.oee_score)}`}>{fmt(r.oee_score)}</span> },
          { header:"Alerts", accessor:(r)=>(
            <div className="flex gap-1">
              {r.is_low_oee       && <Badge label="Low OEE"  variant="red"/>}
              {r.is_high_downtime && <Badge label="High DT"  variant="yellow"/>}
              {!r.is_low_oee && !r.is_high_downtime && <Badge label="OK" variant="green"/>}
            </div>
          )},
          { header:"", accessor:(r)=><button onClick={()=>setDel(r.id)} className="text-xs text-red-500 hover:underline">Delete</button> },
        ]}/>
      )}

      {/* Create */}
      <Modal open={open} onClose={()=>setOpen(false)} title="Add OEE Record">
        <form onSubmit={e=>{e.preventDefault();create.mutate();}} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Input label="OEE ID *" value={form.oee_id} onChange={e=>setForm(f=>({...f,oee_id:e.target.value}))} required placeholder="OEE001"/>
            <Select label="Work Center" options={[{value:"",label:"— select —"},...wcs.map(w=>({value:w.id,label:`${w.work_center_id} – ${w.name}`}))]} value={form.work_center_id} onChange={e=>setForm(f=>({...f,work_center_id:e.target.value}))}/>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input label="Machine ID (free text)" value={form.machine_id} onChange={e=>setForm(f=>({...f,machine_id:e.target.value}))} placeholder="M001"/>
            <Input label="Date *" type="date" value={form.record_date} onChange={e=>setForm(f=>({...f,record_date:e.target.value}))} required/>
          </div>
          <div className="grid grid-cols-3 gap-4">
            <Input label="Planned Time (min)" type="number" value={form.planned_production_time_min} onChange={e=>setForm(f=>({...f,planned_production_time_min:e.target.value}))}/>
            <Input label="Actual Time (min)"  type="number" value={form.actual_production_time_min}  onChange={e=>setForm(f=>({...f,actual_production_time_min:e.target.value}))}/>
            <Input label="Downtime (min)"     type="number" value={form.downtime_min}                onChange={e=>setForm(f=>({...f,downtime_min:e.target.value}))}/>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input label="Total Units" type="number" value={form.total_units_produced} onChange={e=>setForm(f=>({...f,total_units_produced:e.target.value}))}/>
            <Input label="Good Units"  type="number" value={form.good_units_produced}  onChange={e=>setForm(f=>({...f,good_units_produced:e.target.value}))}/>
          </div>
          <p className="text-xs text-gray-500">Optional: enter pre-computed KPIs from CSV (0–1 scale). If left blank, they are auto-calculated.</p>
          <div className="grid grid-cols-4 gap-3">
            <Input label="Availability" type="number" step="0.0001" placeholder="0.9"  value={form.availability} onChange={e=>setForm(f=>({...f,availability:e.target.value}))}/>
            <Input label="Performance"  type="number" step="0.0001" placeholder="0.85" value={form.performance}  onChange={e=>setForm(f=>({...f,performance:e.target.value}))}/>
            <Input label="Quality"      type="number" step="0.0001" placeholder="0.95" value={form.quality}      onChange={e=>setForm(f=>({...f,quality:e.target.value}))}/>
            <Input label="OEE Score"    type="number" step="0.0001" placeholder="0.726" value={form.oee_score}   onChange={e=>setForm(f=>({...f,oee_score:e.target.value}))}/>
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={()=>setOpen(false)}>Cancel</Button>
            <Button type="submit" loading={create.isPending}>Save OEE</Button>
          </div>
        </form>
      </Modal>

      <Modal open={!!deletingId} onClose={()=>setDel(null)} title="Delete OEE Record">
        <p className="text-sm text-gray-600 mb-4">Remove this OEE record?</p>
        <div className="flex justify-end gap-3">
          <Button variant="secondary" onClick={()=>setDel(null)}>Cancel</Button>
          <Button variant="danger" loading={del.isPending} onClick={()=>deletingId&&del.mutate(deletingId)}>Delete</Button>
        </div>
      </Modal>
    </div>
  );
}

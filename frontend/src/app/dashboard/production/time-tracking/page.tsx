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

const CAT_OPTS = [{value:"productive",label:"Productive"},{value:"idle",label:"Idle"},{value:"setup",label:"Setup"},{value:"cleaning",label:"Cleaning"},{value:"downtime",label:"Downtime"}];

export default function TimeTrackingPage() {
  const qc = useQueryClient();
  const { toasts, toast, dismiss } = useToast();
  const [open, setOpen]       = useState(false);
  const [deletingId, setDel]  = useState<string|null>(null);
  const [form, setForm] = useState({ log_id:"", work_order_id:"", actual_start:"", actual_end:"", duration_planned_min:"", downtime_minutes:"0", category:"productive", reason:"" });

  const { data: wos = [] } = useQuery({ queryKey:["work-orders"], queryFn:()=>advProductionApi.listWorkOrders() });
  const { data: items = [], isLoading } = useQuery({ queryKey:["time-tracking"], queryFn:()=>advProductionApi.listTimeTracking() });

  const create = useMutation({ mutationFn:()=>advProductionApi.createTimeTracking({...form, work_order_id: form.work_order_id||undefined, duration_planned_min: form.duration_planned_min ? parseInt(form.duration_planned_min) : undefined, downtime_minutes: parseInt(form.downtime_minutes)||0 }), onSuccess:()=>{ qc.invalidateQueries({queryKey:["time-tracking"]}); setOpen(false); toast("success","Logged","Time entry saved."); }, onError:(e)=>toast("error","Failed",extractApiError(e)) });
  const del    = useMutation({ mutationFn:(id:string)=>advProductionApi.deleteTimeTracking(id), onSuccess:()=>{ qc.invalidateQueries({queryKey:["time-tracking"]}); setDel(null); toast("success","Deleted",""); }, onError:(e)=>toast("error","Failed",extractApiError(e)) });

  const effColor = (pct?: number) => !pct ? "text-gray-500" : pct >= 90 ? "text-green-600" : pct >= 70 ? "text-yellow-600" : "text-red-600";

  return (
    <div>
      <ToastContainer toasts={toasts} onDismiss={dismiss}/>
      <div className="mb-6 flex items-center justify-between">
        <div><h1 className="text-2xl font-bold text-gray-900">Time Tracking</h1><p className="text-sm text-gray-500 mt-1">Actual vs planned production time per work order</p></div>
        <div className="flex gap-2">
          <ImportModal module="time_tracking" onSuccess={()=>qc.invalidateQueries({queryKey:["time-tracking"]})}/>
          <Button onClick={()=>setOpen(true)}>+ Log Time</Button>
        </div>
      </div>
      {isLoading ? <div className="flex justify-center py-16"><div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent"/></div> : (
        <Table keyField="id" data={items} emptyMessage="No time logs yet." columns={[
          { header:"Log ID",      accessor:(r)=><span className="font-mono text-xs font-medium">{r.log_id}</span> },
          { header:"Work Order",  accessor:(r)=>r.work_order_code??r.work_order_id },
          { header:"Start",       accessor:(r)=>new Date(r.actual_start).toLocaleString() },
          { header:"End",         accessor:(r)=>r.actual_end ? new Date(r.actual_end).toLocaleString() : "—" },
          { header:"Actual (min)",  accessor:(r)=>r.duration_actual_min??r.downtime_minutes??0 },
          { header:"Planned (min)", accessor:(r)=>r.duration_planned_min??"—" },
          { header:"Downtime (min)",accessor:(r)=>r.downtime_minutes??0 },
          { header:"Category",    accessor:(r)=><Badge label={r.category} variant={r.category==="productive"?"green":r.category==="downtime"?"red":"blue"}/> },
          { header:"Efficiency",  accessor:(r)=><span className={effColor(r.efficiency_pct)}>{r.efficiency_pct ? `${Number(r.efficiency_pct).toFixed(1)}%` : "—"}</span> },
          { header:"", accessor:(r)=><button onClick={()=>setDel(r.id)} className="text-xs text-red-500 hover:underline">Delete</button> },
        ]}/>
      )}

      <Modal open={open} onClose={()=>setOpen(false)} title="Log Time Entry">
        <form onSubmit={e=>{e.preventDefault();create.mutate();}} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Input label="Log ID *" value={form.log_id} onChange={e=>setForm(f=>({...f,log_id:e.target.value}))} required placeholder="LOG001"/>
            <Select label="Work Order" options={[{value:"",label:"— select —"},...wos.map(w=>({value:w.id,label:`${w.work_order_id} – ${w.operation}`}))]} value={form.work_order_id} onChange={e=>setForm(f=>({...f,work_order_id:e.target.value}))}/>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input label="Actual Start *" type="datetime-local" onChange={e=>setForm(f=>({...f,actual_start:e.target.value}))} required/>
            <Input label="Actual End"     type="datetime-local" onChange={e=>setForm(f=>({...f,actual_end:e.target.value}))}/>
          </div>
          <div className="grid grid-cols-3 gap-4">
            <Input label="Planned (min)" type="number" value={form.duration_planned_min} onChange={e=>setForm(f=>({...f,duration_planned_min:e.target.value}))}/>
            <Input label="Downtime (min)" type="number" value={form.downtime_minutes} onChange={e=>setForm(f=>({...f,downtime_minutes:e.target.value}))}/>
            <Select label="Category" options={CAT_OPTS} value={form.category} onChange={e=>setForm(f=>({...f,category:e.target.value}))}/>
          </div>
          <Input label="Reason / Notes" value={form.reason} onChange={e=>setForm(f=>({...f,reason:e.target.value}))} placeholder="Delay reason, downtime cause…"/>
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={()=>setOpen(false)}>Cancel</Button>
            <Button type="submit" loading={create.isPending}>Save Log</Button>
          </div>
        </form>
      </Modal>

      <Modal open={!!deletingId} onClose={()=>setDel(null)} title="Delete Log">
        <p className="text-sm text-gray-600 mb-4">Remove this time log entry?</p>
        <div className="flex justify-end gap-3">
          <Button variant="secondary" onClick={()=>setDel(null)}>Cancel</Button>
          <Button variant="danger" loading={del.isPending} onClick={()=>deletingId&&del.mutate(deletingId)}>Delete</Button>
        </div>
      </Modal>
    </div>
  );
}

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

const CAT_OPTS    = [{value:"",label:"All"}         ,{value:"planned",label:"Planned"},{value:"unplanned",label:"Unplanned"},{value:"external",label:"External"}];
const CAT_CREATE  = [{value:"planned",label:"Planned"},{value:"unplanned",label:"Unplanned"},{value:"external",label:"External"}];

const catVariant = (c:string) => c==="planned"?"blue":c==="external"?"yellow":"red";

export default function DowntimePage() {
  const qc = useQueryClient();
  const { toasts, toast, dismiss } = useToast();
  const [open, setOpen]       = useState(false);
  const [catFilter, setCat]   = useState("");
  const [deletingId, setDel]  = useState<string|null>(null);
  const [form, setForm] = useState({ downtime_id:"", work_center_id:"", machine_id:"", start_time:"", end_time:"", reason:"", category:"unplanned", reported_by:"" });

  const { data: wcs   = [] } = useQuery({ queryKey:["work-centers"], queryFn:()=>advProductionApi.listWorkCenters() });
  const { data: items = [], isLoading } = useQuery({ queryKey:["downtime",catFilter], queryFn:()=>advProductionApi.listDowntime(catFilter?{category:catFilter}:undefined) });

  const totalMin = items.reduce((s,i)=>s+(i.duration_min??0),0);
  const create = useMutation({ mutationFn:()=>advProductionApi.createDowntime(form), onSuccess:()=>{ qc.invalidateQueries({queryKey:["downtime"]}); setOpen(false); toast("success","Logged","Downtime event recorded."); }, onError:(e)=>toast("error","Failed",extractApiError(e)) });
  const del    = useMutation({ mutationFn:(id:string)=>advProductionApi.deleteDowntime(id), onSuccess:()=>{ qc.invalidateQueries({queryKey:["downtime"]}); setDel(null); toast("success","Deleted",""); }, onError:(e)=>toast("error","Failed",extractApiError(e)) });

  return (
    <div>
      <ToastContainer toasts={toasts} onDismiss={dismiss}/>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Downtime Tracking</h1>
          <p className="text-sm text-gray-500 mt-1">Total downtime: <strong>{totalMin.toLocaleString()} min</strong> ({items.length} events)</p>
        </div>
        <div className="flex gap-2 items-center">
          <PageHelpTooltip topic="production-downtime" />
          <ImportModal module="downtime_events" onSuccess={()=>qc.invalidateQueries({queryKey:["downtime"]})}/>
          <Button onClick={()=>setOpen(true)}>+ Log Downtime</Button>
        </div>
      </div>
      <div className="mb-4">
        <Select options={CAT_OPTS} value={catFilter} onChange={e=>setCat(e.target.value)} className="w-44"/>
      </div>
      {isLoading ? <div className="flex justify-center py-16"><div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent"/></div> : (
        <Table keyField="id" data={items} emptyMessage="No downtime events." columns={[
          { header:"Event ID",    accessor:(r)=><span className="font-mono text-xs font-medium">{r.downtime_id}</span> },
          { header:"Work Center", accessor:(r)=>r.work_center_name??r.work_center_id },
          { header:"Machine ID",  accessor:(r)=>r.machine_id??"—" },
          { header:"Start",       accessor:(r)=>new Date(r.start_time).toLocaleString() },
          { header:"End",         accessor:(r)=>r.end_time ? new Date(r.end_time).toLocaleString() : <span className="text-yellow-600 text-xs font-semibold">Ongoing</span> },
          { header:"Duration (min)", accessor:(r)=>r.duration_min??<span className="text-yellow-600">—</span> },
          { header:"Category",    accessor:(r)=><Badge label={r.category} variant={catVariant(r.category)}/> },
          { header:"Reason",      accessor:(r)=><span className="text-xs text-gray-600 max-w-[200px] truncate block">{r.reason}</span> },
          { header:"Reported By", accessor:(r)=>r.reported_by??"—" },
          { header:"", accessor:(r)=><button onClick={()=>setDel(r.id)} className="text-xs text-red-500 hover:underline">Delete</button> },
        ]}/>
      )}

      <Modal open={open} onClose={()=>setOpen(false)} title="Log Downtime Event">
        <form onSubmit={e=>{e.preventDefault();create.mutate();}} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Input label="Downtime ID *" value={form.downtime_id} onChange={e=>setForm(f=>({...f,downtime_id:e.target.value}))} required placeholder="DT001"/>
            <Select label="Work Center" options={[{value:"",label:"— select —"},...wcs.map(w=>({value:w.id,label:`${w.work_center_id} – ${w.name}`}))]} value={form.work_center_id} onChange={e=>setForm(f=>({...f,work_center_id:e.target.value}))}/>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input label="Machine ID (free text)" value={form.machine_id} onChange={e=>setForm(f=>({...f,machine_id:e.target.value}))} placeholder="e.g. M001"/>
            <Select label="Category" options={CAT_CREATE} value={form.category} onChange={e=>setForm(f=>({...f,category:e.target.value}))}/>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input label="Start Time *" type="datetime-local" onChange={e=>setForm(f=>({...f,start_time:e.target.value}))} required/>
            <Input label="End Time"     type="datetime-local" onChange={e=>setForm(f=>({...f,end_time:e.target.value}))}/>
          </div>
          <Input label="Reason *" value={form.reason} onChange={e=>setForm(f=>({...f,reason:e.target.value}))} required placeholder="Power outage, equipment failure…"/>
          <Input label="Reported By" value={form.reported_by} onChange={e=>setForm(f=>({...f,reported_by:e.target.value}))}/>
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={()=>setOpen(false)}>Cancel</Button>
            <Button type="submit" loading={create.isPending}>Log Event</Button>
          </div>
        </form>
      </Modal>

      <Modal open={!!deletingId} onClose={()=>setDel(null)} title="Delete Downtime Event">
        <p className="text-sm text-gray-600 mb-4">Remove this downtime record?</p>
        <div className="flex justify-end gap-3">
          <Button variant="secondary" onClick={()=>setDel(null)}>Cancel</Button>
          <Button variant="danger" loading={del.isPending} onClick={()=>deletingId&&del.mutate(deletingId)}>Delete</Button>
        </div>
      </Modal>
    </div>
  );
}

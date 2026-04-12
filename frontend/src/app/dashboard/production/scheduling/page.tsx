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

const PRIORITY_OPTS = [{value:"low",label:"Low"},{value:"medium",label:"Medium"},{value:"high",label:"High"},{value:"urgent",label:"Urgent"}];
const STATUS_OPTS   = [{value:"planned",label:"Planned"},{value:"confirmed",label:"Confirmed"},{value:"in_progress",label:"In Progress"},{value:"completed",label:"Completed"},{value:"cancelled",label:"Cancelled"}];
const FILTER_OPTS   = [{value:"",label:"All"},...STATUS_OPTS];

const priorityVariant = (p:string) => p==="urgent"?"red":p==="high"?"yellow":p==="medium"?"blue":"green";
const statusVariant   = (s:string) => s==="completed"?"green":s==="in_progress"?"yellow":s==="cancelled"?"red":"blue";

export default function SchedulingPage() {
  const qc = useQueryClient();
  const { toasts, toast, dismiss } = useToast();
  const [open, setOpen]       = useState(false);
  const [sfStatus, setSf]     = useState("");
  const [deletingId, setDel]  = useState<string|null>(null);
  const [showConflicts, setShowConflicts] = useState(false);
  const [form, setForm] = useState({ schedule_id:"", production_order_id:"", work_center_id:"", shift_name:"", start_time:"", end_time:"", status:"planned", priority:"medium" });

  const { data: wcs   = [] } = useQuery({ queryKey:["work-centers"],  queryFn:()=>advProductionApi.listWorkCenters() });
  const { data: shifts = [] } = useQuery({ queryKey:["shifts"],       queryFn:()=>advProductionApi.listShifts() });
  const { data: items = [], isLoading } = useQuery({ queryKey:["schedules",sfStatus], queryFn:()=>advProductionApi.listSchedules(sfStatus?{status:sfStatus}:undefined) });
  const { data: conflicts = [] } = useQuery({ queryKey:["schedule-conflicts"], queryFn:()=>advProductionApi.getConflicts(), enabled: showConflicts });

  const create = useMutation({ mutationFn:()=>advProductionApi.createSchedule(form), onSuccess:(res:any)=>{ qc.invalidateQueries({queryKey:["schedules"]}); qc.invalidateQueries({queryKey:["schedule-conflicts"]}); setOpen(false); if(res.conflict_flag) toast("warning","Conflict Detected","This schedule overlaps with another on the same work center."); else toast("success","Scheduled","Schedule created."); }, onError:(e)=>toast("error","Failed",extractApiError(e)) });
  const del    = useMutation({ mutationFn:(id:string)=>advProductionApi.deleteSchedule(id), onSuccess:()=>{ qc.invalidateQueries({queryKey:["schedules"]}); setDel(null); toast("success","Deleted",""); }, onError:(e)=>toast("error","Failed",extractApiError(e)) });

  return (
    <div>
      <ToastContainer toasts={toasts} onDismiss={dismiss}/>
      <div className="mb-6 flex items-center justify-between">
        <div><h1 className="text-2xl font-bold text-gray-900">Production Scheduling</h1><p className="text-sm text-gray-500 mt-1">Machine-level scheduling with conflict detection</p></div>
        <div className="flex gap-2">
          <ImportModal module="production_schedules" onSuccess={()=>qc.invalidateQueries({queryKey:["schedules"]})}/>
          <Button variant="secondary" onClick={()=>setShowConflicts(v=>!v)}>{showConflicts?"Hide Conflicts":"View Conflicts"}</Button>
          <Button onClick={()=>setOpen(true)}>+ New Schedule</Button>
        </div>
      </div>

      {showConflicts && (
        <div className="mb-6 rounded-xl border border-red-200 bg-red-50 p-4">
          <h2 className="text-sm font-semibold text-red-800 mb-2">Conflicting Schedules ({conflicts.length})</h2>
          {conflicts.length === 0 ? <p className="text-xs text-red-600">No conflicts detected.</p> : (
            <ul className="space-y-1">{conflicts.map(c=><li key={c.id} className="text-xs text-red-700">{c.schedule_id} · {c.work_center_name} · {new Date(c.start_time).toLocaleString()} – {new Date(c.end_time).toLocaleString()}</li>)}</ul>
          )}
        </div>
      )}

      <div className="mb-4 flex gap-3">
        <Select options={FILTER_OPTS} value={sfStatus} onChange={e=>setSf(e.target.value)} className="w-44"/>
      </div>

      {isLoading ? <div className="flex justify-center py-16"><div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent"/></div> : (
        <Table keyField="id" data={items} emptyMessage="No schedules yet." columns={[
          { header:"Schedule ID", accessor:(r)=><span className="font-mono text-xs font-medium">{r.schedule_id}</span> },
          { header:"Work Center", accessor:(r)=>r.work_center_name??r.work_center_id },
          { header:"Shift",       accessor:(r)=>r.shift_name??"—" },
          { header:"Start",       accessor:(r)=>new Date(r.start_time).toLocaleString() },
          { header:"End",         accessor:(r)=>new Date(r.end_time).toLocaleString() },
          { header:"Priority",    accessor:(r)=><Badge label={r.priority} variant={priorityVariant(r.priority)}/> },
          { header:"Status",      accessor:(r)=><Badge label={r.status}   variant={statusVariant(r.status)}/> },
          { header:"Conflict",    accessor:(r)=>r.conflict_flag ? <span className="text-xs text-red-600 font-semibold">⚠ Conflict</span> : <span className="text-xs text-green-600">OK</span> },
          { header:"", accessor:(r)=><button onClick={()=>setDel(r.id)} className="text-xs text-red-500 hover:underline">Delete</button> },
        ]}/>
      )}

      <Modal open={open} onClose={()=>setOpen(false)} title="New Production Schedule">
        <form onSubmit={e=>{e.preventDefault();create.mutate();}} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Input label="Schedule ID *" value={form.schedule_id} onChange={e=>setForm(f=>({...f,schedule_id:e.target.value}))} required placeholder="SCH001"/>
            <Input label="Production Order ID" value={form.production_order_id} onChange={e=>setForm(f=>({...f,production_order_id:e.target.value}))} placeholder="UUID"/>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Select label="Work Center" options={[{value:"",label:"— select —"},...wcs.map(w=>({value:w.id,label:`${w.work_center_id} – ${w.name}`}))]} value={form.work_center_id} onChange={e=>setForm(f=>({...f,work_center_id:e.target.value}))}/>
            <Select label="Shift" options={[{value:"",label:"— none —"},...shifts.map(s=>({value:s.shift_code,label:s.name}))]} value={form.shift_name} onChange={e=>setForm(f=>({...f,shift_name:e.target.value}))}/>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input label="Start Time *" type="datetime-local" onChange={e=>setForm(f=>({...f,start_time:e.target.value}))} required/>
            <Input label="End Time *"   type="datetime-local" onChange={e=>setForm(f=>({...f,end_time:e.target.value}))}   required/>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Select label="Priority" options={PRIORITY_OPTS} value={form.priority} onChange={e=>setForm(f=>({...f,priority:e.target.value}))}/>
            <Select label="Status"   options={STATUS_OPTS}   value={form.status}   onChange={e=>setForm(f=>({...f,status:e.target.value}))}/>
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={()=>setOpen(false)}>Cancel</Button>
            <Button type="submit" loading={create.isPending}>Create</Button>
          </div>
        </form>
      </Modal>

      <Modal open={!!deletingId} onClose={()=>setDel(null)} title="Delete Schedule">
        <p className="text-sm text-gray-600 mb-4">Remove this production schedule?</p>
        <div className="flex justify-end gap-3">
          <Button variant="secondary" onClick={()=>setDel(null)}>Cancel</Button>
          <Button variant="danger" loading={del.isPending} onClick={()=>deletingId&&del.mutate(deletingId)}>Delete</Button>
        </div>
      </Modal>
    </div>
  );
}

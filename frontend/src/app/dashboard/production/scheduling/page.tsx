"use client";
import { EntityPicker } from "@/components/EntityPicker";
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
import { tx, lx } from "@/lib/i18n/core";

const PRIORITY_OPTS = lx(() => [{value:"low",label:tx("Low")},{value:"medium",label:tx("Medium")},{value:"high",label:tx("High")},{value:"urgent",label:tx("Urgent")}]);
const STATUS_OPTS   = lx(() => [{value:"planned",label:tx("Planned")},{value:"confirmed",label:tx("Confirmed")},{value:"in_progress",label:tx("In Progress")},{value:"completed",label:tx("Completed")},{value:"cancelled",label:tx("Cancelled")}]);
const FILTER_OPTS   = lx(() => [{value:"",label:tx("All")},...STATUS_OPTS]);

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

  const create = useMutation({ mutationFn:()=>advProductionApi.createSchedule(form), onSuccess:(res:any)=>{ qc.invalidateQueries({queryKey:["schedules"]}); qc.invalidateQueries({queryKey:["schedule-conflicts"]}); setOpen(false); if(res.conflict_flag) toast("warning",tx("Conflict Detected"),tx("This schedule overlaps with another on the same work center.")); else toast("success",tx("Scheduled"),tx("Schedule created.")); }, onError:(e)=>toast("error",tx("Failed"),extractApiError(e)) });
  const del    = useMutation({ mutationFn:(id:string)=>advProductionApi.deleteSchedule(id), onSuccess:()=>{ qc.invalidateQueries({queryKey:["schedules"]}); setDel(null); toast("success",tx("Deleted"),""); }, onError:(e)=>toast("error",tx("Failed"),extractApiError(e)) });

  return (
    <div>
      <ToastContainer toasts={toasts} onDismiss={dismiss}/>
      <div className="mb-6 flex items-center justify-between">
        <div><h1 className="text-2xl font-bold text-gray-900">{tx("Production Scheduling")}</h1><p className="text-sm text-gray-500 mt-1">{tx("Machine-level scheduling with conflict detection")}</p></div>
        <div className="flex gap-2">
          <ImportModal module="production_schedules" onSuccess={()=>qc.invalidateQueries({queryKey:["schedules"]})}/>
          <Button variant="secondary" onClick={()=>setShowConflicts(v=>!v)}>{showConflicts?tx("Hide Conflicts"):tx("View Conflicts")}</Button>
          <Button onClick={()=>setOpen(true)}>{tx("+ New Schedule")}</Button>
        </div>
      </div>

      {showConflicts && (
        <div className="mb-6 rounded-xl border border-red-200 bg-red-50 p-4">
          <h2 className="text-sm font-semibold text-red-800 mb-2">{tx("Conflicting Schedules (")}{conflicts.length})</h2>
          {conflicts.length === 0 ? <p className="text-xs text-red-600">{tx("No conflicts detected.")}</p> : (
            <ul className="space-y-1">{conflicts.map(c=><li key={c.id} className="text-xs text-red-700">{c.schedule_id} · {c.work_center_name} · {new Date(c.start_time).toLocaleString()} – {new Date(c.end_time).toLocaleString()}</li>)}</ul>
          )}
        </div>
      )}

      <div className="mb-4 flex gap-3">
        <Select options={FILTER_OPTS} value={sfStatus} onChange={e=>setSf(e.target.value)} className="w-44"/>
      </div>

      {isLoading ? <div className="flex justify-center py-16"><div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent"/></div> : (
        <Table keyField="id" data={items} emptyMessage="No schedules yet." columns={[
          { header:tx("Schedule ID"), accessor:(r)=><span className="font-mono text-xs font-medium">{r.schedule_id}</span> },
          { header:tx("Work Center"), accessor:(r)=>r.work_center_name??r.work_center_id },
          { header:tx("Shift"),       accessor:(r)=>r.shift_name??"—" },
          { header:tx("Start"),       accessor:(r)=>new Date(r.start_time).toLocaleString() },
          { header:tx("End"),         accessor:(r)=>new Date(r.end_time).toLocaleString() },
          { header:tx("Priority"),    accessor:(r)=><Badge label={r.priority} variant={priorityVariant(r.priority)}/> },
          { header:tx("Status"),      accessor:(r)=><Badge label={r.status}   variant={statusVariant(r.status)}/> },
          { header:tx("Conflict"),    accessor:(r)=>r.conflict_flag ? <span className="text-xs text-red-600 font-semibold">{tx("⚠ Conflict")}</span> : <span className="text-xs text-green-600">OK</span> },
          { header:"", accessor:(r)=><button onClick={()=>setDel(r.id)} className="text-xs text-red-500 hover:underline">{tx("Delete")}</button> },
        ]}/>
      )}

      <Modal open={open} onClose={()=>setOpen(false)} title={tx("New Production Schedule")}>
        <form onSubmit={e=>{e.preventDefault();create.mutate();}} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Input label={tx("Schedule ID *")} value={form.schedule_id} onChange={e=>setForm(f=>({...f,schedule_id:e.target.value}))} required placeholder="SCH001"/>
            <div><label className="block text-sm font-medium text-gray-700 mb-1">{tx("Production Order")}</label><EntityPicker kind="production_order" label={tx("Production order")} value={form.production_order_id} onChange={(id) => setForm((f) => ({ ...f, production_order_id: id }))} /></div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Select label={tx("Work Center")} options={[{value:"",label:tx("— select —")},...wcs.map(w=>({value:w.id,label:`${w.work_center_id} – ${w.name}`}))]} value={form.work_center_id} onChange={e=>setForm(f=>({...f,work_center_id:e.target.value}))}/>
            <Select label={tx("Shift")} options={[{value:"",label:tx("— none —")},...shifts.map(s=>({value:s.shift_code,label:s.name}))]} value={form.shift_name} onChange={e=>setForm(f=>({...f,shift_name:e.target.value}))}/>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input label={tx("Start Time *")} type="datetime-local" onChange={e=>setForm(f=>({...f,start_time:e.target.value}))} required/>
            <Input label={tx("End Time *")}   type="datetime-local" onChange={e=>setForm(f=>({...f,end_time:e.target.value}))}   required/>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Select label={tx("Priority")} options={PRIORITY_OPTS} value={form.priority} onChange={e=>setForm(f=>({...f,priority:e.target.value}))}/>
            <Select label={tx("Status")}   options={STATUS_OPTS}   value={form.status}   onChange={e=>setForm(f=>({...f,status:e.target.value}))}/>
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={()=>setOpen(false)}>{tx("Cancel")}</Button>
            <Button type="submit" loading={create.isPending}>{tx("Create")}</Button>
          </div>
        </form>
      </Modal>

      <Modal open={!!deletingId} onClose={()=>setDel(null)} title={tx("Delete Schedule")}>
        <p className="text-sm text-gray-600 mb-4">{tx("Remove this production schedule?")}</p>
        <div className="flex justify-end gap-3">
          <Button variant="secondary" onClick={()=>setDel(null)}>{tx("Cancel")}</Button>
          <Button variant="danger" loading={del.isPending} onClick={()=>deletingId&&del.mutate(deletingId)}>{tx("Delete")}</Button>
        </div>
      </Modal>
    </div>
  );
}

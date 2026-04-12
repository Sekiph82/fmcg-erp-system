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
import { ToastContainer } from "@/components/ui/Toast";
import { useToast } from "@/hooks/useToast";

export default function ShiftsPage() {
  const qc = useQueryClient();
  const { toasts, toast, dismiss } = useToast();
  const [open, setOpen]       = useState(false);
  const [deletingId, setDel]  = useState<string|null>(null);
  const [form, setForm] = useState({ shift_code:"", name:"", start_time_str:"08:00", end_time_str:"16:00", duration_hours:"8", is_active: true });

  const { data: items = [], isLoading } = useQuery({ queryKey:["shifts"], queryFn:()=>advProductionApi.listShifts() });

  const create = useMutation({ mutationFn:()=>advProductionApi.createShift({...form, duration_hours: parseFloat(form.duration_hours)}), onSuccess:()=>{ qc.invalidateQueries({queryKey:["shifts"]}); setOpen(false); toast("success","Created","Shift added."); }, onError:(e)=>toast("error","Failed",extractApiError(e)) });
  const del    = useMutation({ mutationFn:(id:string)=>advProductionApi.deleteShift(id), onSuccess:()=>{ qc.invalidateQueries({queryKey:["shifts"]}); setDel(null); toast("success","Deleted",""); }, onError:(e)=>toast("error","Failed",extractApiError(e)) });

  return (
    <div>
      <ToastContainer toasts={toasts} onDismiss={dismiss}/>
      <div className="mb-6 flex items-center justify-between">
        <div><h1 className="text-2xl font-bold text-gray-900">Shifts</h1><p className="text-sm text-gray-500 mt-1">Define factory shift patterns</p></div>
        <Button onClick={()=>setOpen(true)}>+ Add Shift</Button>
      </div>
      {isLoading ? <div className="flex justify-center py-16"><div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent"/></div> : (
        <Table keyField="id" data={items} emptyMessage="No shifts defined yet." columns={[
          { header:"Code",     accessor:(r)=><span className="font-mono text-xs font-medium">{r.shift_code}</span> },
          { header:"Name",     accessor:"name" },
          { header:"Start",    accessor:(r)=>r.start_time_str },
          { header:"End",      accessor:(r)=>r.end_time_str },
          { header:"Duration", accessor:(r)=>`${r.duration_hours}h` },
          { header:"Active",   accessor:(r)=><Badge label={r.is_active?"Active":"Inactive"} variant={r.is_active?"green":"red"}/> },
          { header:"", accessor:(r)=><button onClick={()=>setDel(r.id)} className="text-xs text-red-500 hover:underline">Delete</button> },
        ]}/>
      )}

      <Modal open={open} onClose={()=>setOpen(false)} title="Add Shift">
        <form onSubmit={e=>{e.preventDefault();create.mutate();}} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Input label="Shift Code *" value={form.shift_code} onChange={e=>setForm(f=>({...f,shift_code:e.target.value}))} required placeholder="SHIFT-A"/>
            <Input label="Name *" value={form.name} onChange={e=>setForm(f=>({...f,name:e.target.value}))} required placeholder="Morning Shift"/>
          </div>
          <div className="grid grid-cols-3 gap-4">
            <Input label="Start Time" value={form.start_time_str} onChange={e=>setForm(f=>({...f,start_time_str:e.target.value}))} placeholder="08:00"/>
            <Input label="End Time"   value={form.end_time_str}   onChange={e=>setForm(f=>({...f,end_time_str:e.target.value}))}   placeholder="16:00"/>
            <Input label="Duration (h)" type="number" step="0.5" value={form.duration_hours} onChange={e=>setForm(f=>({...f,duration_hours:e.target.value}))}/>
          </div>
          <div className="flex items-center gap-2">
            <input id="is_active" type="checkbox" checked={form.is_active} onChange={e=>setForm(f=>({...f,is_active:e.target.checked}))} className="h-4 w-4 rounded border-gray-300 text-indigo-600"/>
            <label htmlFor="is_active" className="text-sm text-gray-700">Active</label>
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={()=>setOpen(false)}>Cancel</Button>
            <Button type="submit" loading={create.isPending}>Create Shift</Button>
          </div>
        </form>
      </Modal>

      <Modal open={!!deletingId} onClose={()=>setDel(null)} title="Delete Shift">
        <p className="text-sm text-gray-600 mb-4">Remove this shift? Schedules referencing it will lose the shift link.</p>
        <div className="flex justify-end gap-3">
          <Button variant="secondary" onClick={()=>setDel(null)}>Cancel</Button>
          <Button variant="danger" loading={del.isPending} onClick={()=>deletingId&&del.mutate(deletingId)}>Delete</Button>
        </div>
      </Modal>
    </div>
  );
}

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

const ACTIVITY_OPTS = [{value:"production",label:"Production"},{value:"setup",label:"Setup"},{value:"qc",label:"QC"},{value:"cleaning",label:"Cleaning"},{value:"other",label:"Other"}];

export default function LaborPage() {
  const qc = useQueryClient();
  const { toasts, toast, dismiss } = useToast();
  const [open, setOpen]       = useState(false);
  const [deletingId, setDel]  = useState<string|null>(null);
  const [form, setForm] = useState({ labor_id:"", work_order_id:"", employee_code:"", operator_name:"", hours_worked:"", role:"operator", activity_type:"production", pieces_produced:"" });

  const { data: wos   = [] } = useQuery({ queryKey:["work-orders"], queryFn:()=>advProductionApi.listWorkOrders() });
  const { data: items = [], isLoading } = useQuery({ queryKey:["labor"], queryFn:()=>advProductionApi.listLabor() });

  const totalHours = items.reduce((s,i)=>s+Number(i.hours_worked??0),0);

  const create = useMutation({ mutationFn:()=>advProductionApi.createLabor({...form, work_order_id:form.work_order_id||undefined, hours_worked:parseFloat(form.hours_worked)||undefined, pieces_produced:parseInt(form.pieces_produced)||undefined}), onSuccess:()=>{ qc.invalidateQueries({queryKey:["labor"]}); setOpen(false); toast("success","Logged","Labor entry saved."); }, onError:(e)=>toast("error","Failed",extractApiError(e)) });
  const del    = useMutation({ mutationFn:(id:string)=>advProductionApi.deleteLabor(id), onSuccess:()=>{ qc.invalidateQueries({queryKey:["labor"]}); setDel(null); toast("success","Deleted",""); }, onError:(e)=>toast("error","Failed",extractApiError(e)) });

  return (
    <div>
      <ToastContainer toasts={toasts} onDismiss={dismiss}/>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Labor Tracking</h1>
          <p className="text-sm text-gray-500 mt-1">{items.length} entries — total <strong>{totalHours.toFixed(1)}h</strong> logged</p>
        </div>
        <div className="flex gap-2">
          <ImportModal module="labor_logs" onSuccess={()=>qc.invalidateQueries({queryKey:["labor"]})}/>
          <Button onClick={()=>setOpen(true)}>+ Log Labor</Button>
        </div>
      </div>
      {isLoading ? <div className="flex justify-center py-16"><div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent"/></div> : (
        <Table keyField="id" data={items} emptyMessage="No labor logs." columns={[
          { header:"Labor ID",    accessor:(r)=><span className="font-mono text-xs font-medium">{r.labor_id}</span> },
          { header:"Work Order",  accessor:(r)=>r.work_order_code??r.work_order_id },
          { header:"Employee",    accessor:(r)=>r.operator_name??r.employee_code??"—" },
          { header:"Role",        accessor:(r)=>r.role??"—" },
          { header:"Activity",    accessor:(r)=><Badge label={r.activity_type} variant="blue"/> },
          { header:"Hours",       accessor:(r)=>r.hours_worked ? `${Number(r.hours_worked).toFixed(1)}h` : "—" },
          { header:"Pieces",      accessor:(r)=>r.pieces_produced?.toLocaleString()??"—" },
          { header:"Date",        accessor:(r)=>new Date(r.created_at).toLocaleDateString() },
          { header:"", accessor:(r)=><button onClick={()=>setDel(r.id)} className="text-xs text-red-500 hover:underline">Delete</button> },
        ]}/>
      )}

      <Modal open={open} onClose={()=>setOpen(false)} title="Log Labor Entry">
        <form onSubmit={e=>{e.preventDefault();create.mutate();}} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Input label="Labor ID *" value={form.labor_id} onChange={e=>setForm(f=>({...f,labor_id:e.target.value}))} required placeholder="LAB001"/>
            <Select label="Work Order" options={[{value:"",label:"— select —"},...wos.map(w=>({value:w.id,label:`${w.work_order_id} – ${w.operation}`}))]} value={form.work_order_id} onChange={e=>setForm(f=>({...f,work_order_id:e.target.value}))}/>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input label="Employee Code" value={form.employee_code} onChange={e=>setForm(f=>({...f,employee_code:e.target.value}))} placeholder="E001"/>
            <Input label="Operator Name" value={form.operator_name} onChange={e=>setForm(f=>({...f,operator_name:e.target.value}))}/>
          </div>
          <div className="grid grid-cols-3 gap-4">
            <Input label="Hours Worked" type="number" step="0.5" value={form.hours_worked} onChange={e=>setForm(f=>({...f,hours_worked:e.target.value}))}/>
            <Input label="Pieces"       type="number" value={form.pieces_produced} onChange={e=>setForm(f=>({...f,pieces_produced:e.target.value}))}/>
            <Input label="Role"         value={form.role} onChange={e=>setForm(f=>({...f,role:e.target.value}))} placeholder="operator, supervisor"/>
          </div>
          <Select label="Activity Type" options={ACTIVITY_OPTS} value={form.activity_type} onChange={e=>setForm(f=>({...f,activity_type:e.target.value}))}/>
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={()=>setOpen(false)}>Cancel</Button>
            <Button type="submit" loading={create.isPending}>Save Entry</Button>
          </div>
        </form>
      </Modal>

      <Modal open={!!deletingId} onClose={()=>setDel(null)} title="Delete Labor Log">
        <p className="text-sm text-gray-600 mb-4">Remove this labor entry?</p>
        <div className="flex justify-end gap-3">
          <Button variant="secondary" onClick={()=>setDel(null)}>Cancel</Button>
          <Button variant="danger" loading={del.isPending} onClick={()=>deletingId&&del.mutate(deletingId)}>Delete</Button>
        </div>
      </Modal>
    </div>
  );
}

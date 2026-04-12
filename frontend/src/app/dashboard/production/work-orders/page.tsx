"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { advProductionApi, WorkOrder } from "@/lib/productionAdvanced";
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

const STATUS_FILTER = [
  {value:"",label:"All Statuses"},{value:"planned",label:"Planned"},
  {value:"in_progress",label:"In Progress"},{value:"completed",label:"Completed"},
  {value:"cancelled",label:"Cancelled"},{value:"on_hold",label:"On Hold"},
];

const statusVariant = (s: string) =>
  s==="completed"?"green":s==="in_progress"?"yellow":s==="cancelled"?"red":s==="on_hold"?"yellow":"blue";

export default function WorkOrdersPage() {
  const qc = useQueryClient();
  const { toasts, toast, dismiss } = useToast();
  const [open, setOpen]       = useState(false);
  const [statusFilter, setSF] = useState("");
  const [search, setSearch]   = useState("");
  const [deletingId, setDel]  = useState<string|null>(null);
  const [form, setForm]       = useState({ work_order_id:"", production_order_id:"", work_center_id:"", operation:"", operator:"", status:"planned", planned_start:"", planned_end:"" });

  const { data: wcs = [] }   = useQuery({ queryKey:["work-centers"], queryFn:()=>advProductionApi.listWorkCenters() });
  const { data: items = [], isLoading } = useQuery({ queryKey:["work-orders",statusFilter], queryFn:()=>advProductionApi.listWorkOrders(statusFilter?{status:statusFilter}:undefined) });

  const create = useMutation({ mutationFn:()=>advProductionApi.createWorkOrder({...form, production_order_id: form.production_order_id||undefined, work_center_id:form.work_center_id||undefined}), onSuccess:()=>{ qc.invalidateQueries({queryKey:["work-orders"]}); setOpen(false); toast("success","Created","Work order added."); }, onError:(e)=>toast("error","Failed",extractApiError(e)) });
  const startWO = useMutation({ mutationFn:(id:string)=>advProductionApi.startWorkOrder(id), onSuccess:()=>{ qc.invalidateQueries({queryKey:["work-orders"]}); toast("success","Started","Work order started."); }, onError:(e)=>toast("error","Failed",extractApiError(e)) });
  const completeWO = useMutation({ mutationFn:(id:string)=>advProductionApi.completeWorkOrder(id), onSuccess:()=>{ qc.invalidateQueries({queryKey:["work-orders"]}); toast("success","Completed","Work order completed."); }, onError:(e)=>toast("error","Failed",extractApiError(e)) });
  const del = useMutation({ mutationFn:(id:string)=>advProductionApi.deleteWorkOrder(id), onSuccess:()=>{ qc.invalidateQueries({queryKey:["work-orders"]}); setDel(null); toast("success","Deleted",""); }, onError:(e)=>toast("error","Failed",extractApiError(e)) });

  const filtered = items.filter(i => i.work_order_id.toLowerCase().includes(search.toLowerCase()) || i.operation.toLowerCase().includes(search.toLowerCase()));

  return (
    <div>
      <ToastContainer toasts={toasts} onDismiss={dismiss}/>
      <div className="mb-6 flex items-center justify-between">
        <div><h1 className="text-2xl font-bold text-gray-900">Work Orders</h1><p className="text-sm text-gray-500 mt-1">{items.length} total — executable operations</p></div>
        <div className="flex gap-2">
          <ImportModal module="work_orders" onSuccess={()=>qc.invalidateQueries({queryKey:["work-orders"]})}/>
          <Button onClick={()=>setOpen(true)}>+ New Work Order</Button>
        </div>
      </div>
      <div className="mb-4 flex gap-3">
        <Input placeholder="Search ID or operation…" value={search} onChange={e=>setSearch(e.target.value)} className="max-w-xs"/>
        <Select options={STATUS_FILTER} value={statusFilter} onChange={e=>setSF(e.target.value)} className="w-44"/>
      </div>
      {isLoading ? <div className="flex justify-center py-16"><div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent"/></div> : (
        <Table keyField="id" data={filtered} emptyMessage="No work orders yet." columns={[
          { header:"Work Order ID", accessor:(r)=><span className="font-mono text-xs font-medium">{r.work_order_id}</span> },
          { header:"Operation",    accessor:"operation" },
          { header:"Work Center",  accessor:(r)=>r.work_center_name??r.work_center_id },
          { header:"Operator",     accessor:(r)=>r.operator??"—" },
          { header:"Status",       accessor:(r)=><Badge label={r.status} variant={statusVariant(r.status)}/> },
          { header:"Start",        accessor:(r)=>r.start_time ? new Date(r.start_time).toLocaleString() : "—" },
          { header:"End",          accessor:(r)=>r.end_time   ? new Date(r.end_time).toLocaleString()   : "—" },
          { header:"", accessor:(r)=>(
            <div className="flex gap-2">
              {r.status==="planned"    && <button onClick={()=>startWO.mutate(r.id)}    className="text-xs text-green-600 hover:underline">Start</button>}
              {r.status==="in_progress"&& <button onClick={()=>completeWO.mutate(r.id)} className="text-xs text-indigo-600 hover:underline">Complete</button>}
              <button onClick={()=>setDel(r.id)} className="text-xs text-red-500 hover:underline">Delete</button>
            </div>
          )},
        ]}/>
      )}

      <Modal open={open} onClose={()=>setOpen(false)} title="New Work Order">
        <form onSubmit={e=>{e.preventDefault();create.mutate();}} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Input label="Work Order ID *" value={form.work_order_id} onChange={e=>setForm(f=>({...f,work_order_id:e.target.value}))} required placeholder="WO001"/>
            <Input label="Production Order ID" value={form.production_order_id} onChange={e=>setForm(f=>({...f,production_order_id:e.target.value}))} placeholder="UUID of production order"/>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Select label="Work Center" options={[{value:"",label:"— select —"},...wcs.map(w=>({value:w.id,label:`${w.work_center_id} – ${w.name}`}))]} value={form.work_center_id} onChange={e=>setForm(f=>({...f,work_center_id:e.target.value}))}/>
            <Input label="Operation *" value={form.operation} onChange={e=>setForm(f=>({...f,operation:e.target.value}))} required placeholder="Mixing, Filling…"/>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input label="Operator" value={form.operator} onChange={e=>setForm(f=>({...f,operator:e.target.value}))}/>
            <Select label="Status" options={[{value:"planned",label:"Planned"},{value:"in_progress",label:"In Progress"}]} value={form.status} onChange={e=>setForm(f=>({...f,status:e.target.value}))}/>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input label="Planned Start" type="datetime-local" onChange={e=>setForm(f=>({...f,planned_start:e.target.value}))}/>
            <Input label="Planned End"   type="datetime-local" onChange={e=>setForm(f=>({...f,planned_end:e.target.value}))}/>
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={()=>setOpen(false)}>Cancel</Button>
            <Button type="submit" loading={create.isPending}>Create</Button>
          </div>
        </form>
      </Modal>

      <Modal open={!!deletingId} onClose={()=>setDel(null)} title="Delete Work Order">
        <p className="text-sm text-gray-600 mb-4">Delete this work order? Time logs and labor logs will also be removed.</p>
        <div className="flex justify-end gap-3">
          <Button variant="secondary" onClick={()=>setDel(null)}>Cancel</Button>
          <Button variant="danger" loading={del.isPending} onClick={()=>deletingId&&del.mutate(deletingId)}>Delete</Button>
        </div>
      </Modal>
    </div>
  );
}

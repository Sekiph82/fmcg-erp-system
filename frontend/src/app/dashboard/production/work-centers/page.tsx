"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { advProductionApi, WorkCenter } from "@/lib/productionAdvanced";
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

const TYPE_OPTS  = [{ value:"MACHINE",label:"Machine"},{ value:"LINE",label:"Line"},{ value:"CELL",label:"Cell"},{ value:"MANUAL",label:"Manual"}];
const STATUS_OPTS = [{ value:"active",label:"Active"},{ value:"inactive",label:"Inactive"},{ value:"maintenance",label:"Maintenance"}];
const FILTER_OPTS = [{ value:"",label:"All"},...STATUS_OPTS];

const empty = { work_center_id:"", name:"", type:"MACHINE", capacity:"", capacity_uom:"", location:"", department:"", status:"active", notes:"" };

export default function WorkCentersPage() {
  const qc = useQueryClient();
  const { toasts, toast, dismiss } = useToast();
  const [open, setOpen]       = useState(false);
  const [form, setForm]       = useState<typeof empty>(empty);
  const [editing, setEditing] = useState<WorkCenter | null>(null);
  const [editForm, setEdit]   = useState<Partial<WorkCenter>>({});
  const [statusFilter, setStatus] = useState("");
  const [deletingId, setDel]  = useState<string|null>(null);
  const [search, setSearch]   = useState("");

  const { data: items = [], isLoading } = useQuery({ queryKey:["work-centers",statusFilter], queryFn:()=>advProductionApi.listWorkCenters(statusFilter ? {status:statusFilter} : undefined) });

  const create = useMutation({ mutationFn:()=>advProductionApi.createWorkCenter({...form, capacity: form.capacity ? parseFloat(form.capacity) : undefined}), onSuccess:()=>{ qc.invalidateQueries({queryKey:["work-centers"]}); setOpen(false); setForm(empty); toast("success","Created","Work center added."); }, onError:(e)=>toast("error","Failed",extractApiError(e)) });
  const update = useMutation({ mutationFn:()=>advProductionApi.updateWorkCenter(editing!.id,editForm), onSuccess:()=>{ qc.invalidateQueries({queryKey:["work-centers"]}); setEditing(null); toast("success","Updated","Work center saved."); }, onError:(e)=>toast("error","Failed",extractApiError(e)) });
  const del    = useMutation({ mutationFn:(id:string)=>advProductionApi.deleteWorkCenter(id), onSuccess:()=>{ qc.invalidateQueries({queryKey:["work-centers"]}); setDel(null); toast("success","Deleted","Work center removed."); }, onError:(e)=>toast("error","Failed",extractApiError(e)) });

  const filtered = items.filter(i => i.name.toLowerCase().includes(search.toLowerCase()) || i.work_center_id.toLowerCase().includes(search.toLowerCase()));

  const statusVariant = (s:string) => s==="active"?"green":s==="maintenance"?"yellow":"red";

  return (
    <div>
      <ToastContainer toasts={toasts} onDismiss={dismiss}/>
      <div className="mb-6 flex items-center justify-between">
        <div><h1 className="text-2xl font-bold text-gray-900">Work Centers</h1><p className="text-sm text-gray-500 mt-1">{items.length} total — machines, lines, cells</p></div>
        <div className="flex items-center gap-2">
          <ImportModal module="work_centers" onSuccess={()=>qc.invalidateQueries({queryKey:["work-centers"]})}/>
          <Button onClick={()=>setOpen(true)}>+ Add Work Center</Button>
        </div>
      </div>
      <div className="mb-4 flex gap-3">
        <Input placeholder="Search…" value={search} onChange={e=>setSearch(e.target.value)} className="max-w-xs"/>
        <Select options={FILTER_OPTS} value={statusFilter} onChange={e=>setStatus(e.target.value)} className="w-40"/>
      </div>
      {isLoading ? <div className="flex justify-center py-16"><div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent"/></div> : (
        <Table keyField="id" data={filtered} emptyMessage="No work centers yet." columns={[
          { header:"ID",    accessor:(r)=><span className="font-mono text-xs font-medium">{r.work_center_id}</span> },
          { header:"Name",  accessor:"name" },
          { header:"Type",  accessor:(r)=><Badge label={r.type} variant="blue"/> },
          { header:"Capacity", accessor:(r)=>r.capacity ? `${Number(r.capacity).toLocaleString()} ${r.capacity_uom??''}` : "—" },
          { header:"Location", accessor:(r)=>r.location??"—" },
          { header:"Status", accessor:(r)=><Badge label={r.status} variant={statusVariant(r.status)}/> },
          { header:"", accessor:(r)=>(
            <div className="flex gap-3">
              <button onClick={()=>{ setEditing(r); setEdit({name:r.name,type:r.type,capacity:r.capacity,capacity_uom:r.capacity_uom,location:r.location,department:r.department,status:r.status,notes:r.notes}); }} className="text-xs text-indigo-600 hover:underline">Edit</button>
              <button onClick={()=>setDel(r.id)} className="text-xs text-red-500 hover:underline">Delete</button>
            </div>
          )},
        ]}/>
      )}

      {/* Add */}
      <Modal open={open} onClose={()=>setOpen(false)} title="Add Work Center">
        <form onSubmit={e=>{e.preventDefault();create.mutate();}} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Input label="ID *" value={form.work_center_id} onChange={e=>setForm(f=>({...f,work_center_id:e.target.value}))} required placeholder="e.g. WC001"/>
            <Input label="Name *" value={form.name} onChange={e=>setForm(f=>({...f,name:e.target.value}))} required/>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Select label="Type" options={TYPE_OPTS} value={form.type} onChange={e=>setForm(f=>({...f,type:e.target.value}))}/>
            <Select label="Status" options={STATUS_OPTS} value={form.status} onChange={e=>setForm(f=>({...f,status:e.target.value}))}/>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input label="Capacity" type="number" value={form.capacity} onChange={e=>setForm(f=>({...f,capacity:e.target.value}))} placeholder="e.g. 2000"/>
            <Input label="Capacity UOM" value={form.capacity_uom} onChange={e=>setForm(f=>({...f,capacity_uom:e.target.value}))} placeholder="e.g. L, KG, units/hr"/>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input label="Location" value={form.location} onChange={e=>setForm(f=>({...f,location:e.target.value}))}/>
            <Input label="Department" value={form.department} onChange={e=>setForm(f=>({...f,department:e.target.value}))}/>
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={()=>setOpen(false)}>Cancel</Button>
            <Button type="submit" loading={create.isPending}>Create</Button>
          </div>
        </form>
      </Modal>

      {/* Edit */}
      <Modal open={!!editing} onClose={()=>setEditing(null)} title={`Edit — ${editing?.work_center_id}`}>
        <form onSubmit={e=>{e.preventDefault();update.mutate();}} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Input label="Name *" value={editForm.name??""} onChange={e=>setEdit(f=>({...f,name:e.target.value}))} required/>
            <Select label="Type" options={TYPE_OPTS} value={editForm.type??"MACHINE"} onChange={e=>setEdit(f=>({...f,type:e.target.value}))}/>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input label="Capacity" type="number" value={editForm.capacity??""} onChange={e=>setEdit(f=>({...f,capacity:parseFloat(e.target.value)||undefined}))}/>
            <Input label="Capacity UOM" value={editForm.capacity_uom??""} onChange={e=>setEdit(f=>({...f,capacity_uom:e.target.value}))}/>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input label="Location" value={editForm.location??""} onChange={e=>setEdit(f=>({...f,location:e.target.value}))}/>
            <Select label="Status" options={STATUS_OPTS} value={editForm.status??"active"} onChange={e=>setEdit(f=>({...f,status:e.target.value}))}/>
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={()=>setEditing(null)}>Cancel</Button>
            <Button type="submit" loading={update.isPending}>Save</Button>
          </div>
        </form>
      </Modal>

      {/* Delete */}
      <Modal open={!!deletingId} onClose={()=>setDel(null)} title="Delete Work Center">
        <p className="text-sm text-gray-600 mb-4">Are you sure? This will block if work orders reference this center.</p>
        <div className="flex justify-end gap-3">
          <Button variant="secondary" onClick={()=>setDel(null)}>Cancel</Button>
          <Button variant="danger" loading={del.isPending} onClick={()=>deletingId&&del.mutate(deletingId)}>Delete</Button>
        </div>
      </Modal>
    </div>
  );
}

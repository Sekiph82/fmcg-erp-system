"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { advProductionApi, Routing } from "@/lib/productionAdvanced";
import { productsApi } from "@/lib/products";
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

export default function RoutingPage() {
  const qc = useQueryClient();
  const { toasts, toast, dismiss } = useToast();
  const [open, setOpen]       = useState(false);
  const [detail, setDetail]   = useState<Routing|null>(null);
  const [stepOpen, setStepOpen] = useState(false);
  const [deletingId, setDel]  = useState<string|null>(null);
  const [form, setForm]       = useState({ routing_id:"", product_id:"", version:"1", name:"", is_active:true });
  const [stepForm, setStepForm] = useState({ step_number:"", operation:"", work_center_id:"", standard_time_minutes:"", setup_time_minutes:"" });

  const { data: products = [] } = useQuery({ queryKey:["products"], queryFn:()=>productsApi.list(0,200) });
  const { data: wcs      = [] } = useQuery({ queryKey:["work-centers"], queryFn:()=>advProductionApi.listWorkCenters() });
  const { data: items    = [], isLoading } = useQuery({ queryKey:["routings"], queryFn:()=>advProductionApi.listRoutings() });

  const create    = useMutation({ mutationFn:()=>advProductionApi.createRouting({...form,version:parseInt(form.version)||1, product_id:form.product_id||undefined}), onSuccess:()=>{ qc.invalidateQueries({queryKey:["routings"]}); setOpen(false); toast("success","Created","Routing added."); }, onError:(e)=>toast("error","Failed",extractApiError(e)) });
  const del       = useMutation({ mutationFn:(id:string)=>advProductionApi.deleteRouting(id), onSuccess:()=>{ qc.invalidateQueries({queryKey:["routings"]}); setDel(null); toast("success","Deleted",""); }, onError:(e)=>toast("error","Failed",extractApiError(e)) });
  const addStep   = useMutation({
    mutationFn:()=>advProductionApi.addRoutingStep(detail!.id,{
      step_number:parseInt(stepForm.step_number)||1,
      operation:stepForm.operation, work_center_id:stepForm.work_center_id,
      standard_time_minutes:parseInt(stepForm.standard_time_minutes)||0,
      setup_time_minutes:stepForm.setup_time_minutes?parseInt(stepForm.setup_time_minutes):undefined,
    }),
    onSuccess:()=>{
      qc.invalidateQueries({queryKey:["routings"]});
      setStepOpen(false);
      toast("success","Step Added","Routing step saved.");
      // Refresh detail
      const updated = items.find(r=>r.id===detail?.id);
      if(updated) setDetail(updated);
    },
    onError:(e)=>toast("error","Failed",extractApiError(e))
  });

  return (
    <div>
      <ToastContainer toasts={toasts} onDismiss={dismiss}/>
      <div className="mb-6 flex items-center justify-between">
        <div><h1 className="text-2xl font-bold text-gray-900">Routing</h1><p className="text-sm text-gray-500 mt-1">Step-by-step production flow per product</p></div>
        <div className="flex gap-2">
          <ImportModal module="routings" onSuccess={()=>qc.invalidateQueries({queryKey:["routings"]})}/>
          <Button onClick={()=>setOpen(true)}>+ Add Routing</Button>
        </div>
      </div>
      {isLoading ? <div className="flex justify-center py-16"><div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent"/></div> : (
        <Table keyField="id" data={items} emptyMessage="No routings defined." columns={[
          { header:"Routing ID",  accessor:(r)=><button onClick={()=>setDetail(r)} className="font-mono text-xs text-indigo-600 hover:underline">{r.routing_id}</button> },
          { header:"Product",     accessor:(r)=>r.product_name??r.product_sku??"—" },
          { header:"Version",     accessor:(r)=>`v${r.version}` },
          { header:"Name",        accessor:(r)=>r.name??"—" },
          { header:"Steps",       accessor:(r)=><Badge label={`${r.steps.length} steps`} variant="blue"/> },
          { header:"Active",      accessor:(r)=><Badge label={r.is_active?"Active":"Inactive"} variant={r.is_active?"green":"red"}/> },
          { header:"", accessor:(r)=><button onClick={()=>setDel(r.id)} className="text-xs text-red-500 hover:underline">Delete</button> },
        ]}/>
      )}

      {/* Create Routing */}
      <Modal open={open} onClose={()=>setOpen(false)} title="Add Routing">
        <form onSubmit={e=>{e.preventDefault();create.mutate();}} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Input label="Routing ID *" value={form.routing_id} onChange={e=>setForm(f=>({...f,routing_id:e.target.value}))} required placeholder="R001"/>
            <Select label="Product *" options={[{value:"",label:"— select —"},...products.map(p=>({value:p.id,label:`${p.sku} – ${p.name}`}))]} value={form.product_id} onChange={e=>setForm(f=>({...f,product_id:e.target.value}))}/>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input label="Version" type="number" value={form.version} onChange={e=>setForm(f=>({...f,version:e.target.value}))}/>
            <Input label="Name" value={form.name} onChange={e=>setForm(f=>({...f,name:e.target.value}))}/>
          </div>
          <div className="flex items-center gap-2">
            <input id="r_active" type="checkbox" checked={form.is_active} onChange={e=>setForm(f=>({...f,is_active:e.target.checked}))} className="h-4 w-4 rounded border-gray-300 text-indigo-600"/>
            <label htmlFor="r_active" className="text-sm text-gray-700">Active routing</label>
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={()=>setOpen(false)}>Cancel</Button>
            <Button type="submit" loading={create.isPending}>Create</Button>
          </div>
        </form>
      </Modal>

      {/* Routing Detail / Steps */}
      <Modal open={!!detail} onClose={()=>setDetail(null)} title={`Routing: ${detail?.routing_id}`}>
        {detail && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <p className="text-sm text-gray-600">Product: <strong>{detail.product_name??detail.product_sku??"—"}</strong> · Version {detail.version}</p>
              <Button onClick={()=>setStepOpen(true)}>+ Add Step</Button>
            </div>
            {detail.steps.length===0 ? <p className="text-sm text-gray-500">No steps yet.</p> : (
              <table className="w-full text-xs">
                <thead><tr className="text-gray-500 border-b"><th className="text-left py-1">#</th><th className="text-left">Operation</th><th className="text-left">Work Center</th><th>Std Time (min)</th><th>Parallel</th></tr></thead>
                <tbody>{detail.steps.sort((a,b)=>a.step_number-b.step_number).map(s=>(
                  <tr key={s.id} className="border-b">
                    <td className="py-1">{s.step_number}</td>
                    <td>{s.operation}</td>
                    <td>{s.work_center_name??s.work_center_id}</td>
                    <td className="text-center">{s.standard_time_minutes}</td>
                    <td className="text-center">{s.is_parallel?"Yes":"No"}</td>
                  </tr>
                ))}</tbody>
              </table>
            )}
            <div className="flex justify-end"><Button variant="secondary" onClick={()=>setDetail(null)}>Close</Button></div>
          </div>
        )}
      </Modal>

      {/* Add Step */}
      <Modal open={stepOpen} onClose={()=>setStepOpen(false)} title="Add Routing Step">
        <form onSubmit={e=>{e.preventDefault();addStep.mutate();}} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Input label="Step Number *" type="number" value={stepForm.step_number} onChange={e=>setStepForm(f=>({...f,step_number:e.target.value}))} required/>
            <Input label="Operation *"   value={stepForm.operation} onChange={e=>setStepForm(f=>({...f,operation:e.target.value}))} required placeholder="Mixing, Filling…"/>
          </div>
          <Select label="Work Center *" options={[{value:"",label:"— select —"},...wcs.map(w=>({value:w.id,label:`${w.work_center_id} – ${w.name}`}))]} value={stepForm.work_center_id} onChange={e=>setStepForm(f=>({...f,work_center_id:e.target.value}))}/>
          <div className="grid grid-cols-2 gap-4">
            <Input label="Standard Time (min) *" type="number" value={stepForm.standard_time_minutes} onChange={e=>setStepForm(f=>({...f,standard_time_minutes:e.target.value}))} required/>
            <Input label="Setup Time (min)"       type="number" value={stepForm.setup_time_minutes}    onChange={e=>setStepForm(f=>({...f,setup_time_minutes:e.target.value}))}/>
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={()=>setStepOpen(false)}>Cancel</Button>
            <Button type="submit" loading={addStep.isPending}>Add Step</Button>
          </div>
        </form>
      </Modal>

      <Modal open={!!deletingId} onClose={()=>setDel(null)} title="Delete Routing">
        <p className="text-sm text-gray-600 mb-4">Delete this routing and all its steps?</p>
        <div className="flex justify-end gap-3">
          <Button variant="secondary" onClick={()=>setDel(null)}>Cancel</Button>
          <Button variant="danger" loading={del.isPending} onClick={()=>deletingId&&del.mutate(deletingId)}>Delete</Button>
        </div>
      </Modal>
    </div>
  );
}

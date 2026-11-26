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
import { tx } from "@/lib/i18n/core";

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

  const create    = useMutation({ mutationFn:()=>advProductionApi.createRouting({...form,version:parseInt(form.version)||1, product_id:form.product_id||undefined}), onSuccess:()=>{ qc.invalidateQueries({queryKey:["routings"]}); setOpen(false); toast("success",tx("Created"),tx("Routing added.")); }, onError:(e)=>toast("error",tx("Failed"),extractApiError(e)) });
  const del       = useMutation({ mutationFn:(id:string)=>advProductionApi.deleteRouting(id), onSuccess:()=>{ qc.invalidateQueries({queryKey:["routings"]}); setDel(null); toast("success",tx("Deleted"),""); }, onError:(e)=>toast("error",tx("Failed"),extractApiError(e)) });
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
      toast("success",tx("Step Added"),tx("Routing step saved."));
      // Refresh detail
      const updated = items.find(r=>r.id===detail?.id);
      if(updated) setDetail(updated);
    },
    onError:(e)=>toast("error",tx("Failed"),extractApiError(e))
  });

  return (
    <div>
      <ToastContainer toasts={toasts} onDismiss={dismiss}/>
      <div className="mb-6 flex items-center justify-between">
        <div><h1 className="text-2xl font-bold text-gray-900">{tx("Routing")}</h1><p className="text-sm text-gray-500 mt-1">{tx("Step-by-step production flow per product")}</p></div>
        <div className="flex gap-2">
          <ImportModal module="routings" onSuccess={()=>qc.invalidateQueries({queryKey:["routings"]})}/>
          <Button onClick={()=>setOpen(true)}>{tx("+ Add Routing")}</Button>
        </div>
      </div>
      {isLoading ? <div className="flex justify-center py-16"><div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent"/></div> : (
        <Table keyField="id" data={items} emptyMessage="No routings defined." columns={[
          { header:tx("Routing ID"),  accessor:(r)=><button onClick={()=>setDetail(r)} className="font-mono text-xs text-indigo-600 hover:underline">{r.routing_id}</button> },
          { header:tx("Product"),     accessor:(r)=>r.product_name??r.product_sku??"—" },
          { header:tx("Version"),     accessor:(r)=>`v${r.version}` },
          { header:tx("Name"),        accessor:(r)=>r.name??"—" },
          { header:tx("Steps"),       accessor:(r)=><Badge label={tx("{length} steps", { length: r.steps.length })} variant="blue"/> },
          { header:tx("Active"),      accessor:(r)=><Badge label={r.is_active?tx("Active"):tx("Inactive")} variant={r.is_active?"green":"red"}/> },
          { header:"", accessor:(r)=><button onClick={()=>setDel(r.id)} className="text-xs text-red-500 hover:underline">{tx("Delete")}</button> },
        ]}/>
      )}

      {/* Create Routing */}
      <Modal open={open} onClose={()=>setOpen(false)} title={tx("Add Routing")}>
        <form onSubmit={e=>{e.preventDefault();create.mutate();}} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Input label={tx("Routing ID *")} value={form.routing_id} onChange={e=>setForm(f=>({...f,routing_id:e.target.value}))} required placeholder="R001"/>
            <Select label={tx("Product *")} options={[{value:"",label:tx("— select —")},...products.map(p=>({value:p.id,label:`${p.sku} – ${p.name}`}))]} value={form.product_id} onChange={e=>setForm(f=>({...f,product_id:e.target.value}))}/>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input label={tx("Version")} type="number" value={form.version} onChange={e=>setForm(f=>({...f,version:e.target.value}))}/>
            <Input label={tx("Name")} value={form.name} onChange={e=>setForm(f=>({...f,name:e.target.value}))}/>
          </div>
          <div className="flex items-center gap-2">
            <input id="r_active" type="checkbox" checked={form.is_active} onChange={e=>setForm(f=>({...f,is_active:e.target.checked}))} className="h-4 w-4 rounded border-gray-300 text-indigo-600"/>
            <label htmlFor="r_active" className="text-sm text-gray-700">{tx("Active routing")}</label>
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={()=>setOpen(false)}>{tx("Cancel")}</Button>
            <Button type="submit" loading={create.isPending}>{tx("Create")}</Button>
          </div>
        </form>
      </Modal>

      {/* Routing Detail / Steps */}
      <Modal open={!!detail} onClose={()=>setDetail(null)} title={tx("Routing: {routing_id}", { routing_id: detail?.routing_id })}>
        {detail && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <p className="text-sm text-gray-600">{tx("Product:")} <strong>{detail.product_name??detail.product_sku??"—"}</strong> {tx("· Version")} {detail.version}</p>
              <Button onClick={()=>setStepOpen(true)}>{tx("+ Add Step")}</Button>
            </div>
            {detail.steps.length===0 ? <p className="text-sm text-gray-500">{tx("No steps yet.")}</p> : (
              <table className="w-full text-xs">
                <thead><tr className="text-gray-500 border-b"><th className="text-left py-1">#</th><th className="text-left">{tx("Operation")}</th><th className="text-left">{tx("Work Center")}</th><th>{tx("Std Time (min)")}</th><th>{tx("Parallel")}</th></tr></thead>
                <tbody>{detail.steps.sort((a,b)=>a.step_number-b.step_number).map(s=>(
                  <tr key={s.id} className="border-b">
                    <td className="py-1">{s.step_number}</td>
                    <td>{s.operation}</td>
                    <td>{s.work_center_name??s.work_center_id}</td>
                    <td className="text-center">{s.standard_time_minutes}</td>
                    <td className="text-center">{s.is_parallel?tx("Yes"):tx("No")}</td>
                  </tr>
                ))}</tbody>
              </table>
            )}
            <div className="flex justify-end"><Button variant="secondary" onClick={()=>setDetail(null)}>{tx("Close")}</Button></div>
          </div>
        )}
      </Modal>

      {/* Add Step */}
      <Modal open={stepOpen} onClose={()=>setStepOpen(false)} title={tx("Add Routing Step")}>
        <form onSubmit={e=>{e.preventDefault();addStep.mutate();}} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Input label={tx("Step Number *")} type="number" value={stepForm.step_number} onChange={e=>setStepForm(f=>({...f,step_number:e.target.value}))} required/>
            <Input label={tx("Operation *")}   value={stepForm.operation} onChange={e=>setStepForm(f=>({...f,operation:e.target.value}))} required placeholder={tx("Mixing, Filling…")}/>
          </div>
          <Select label={tx("Work Center *")} options={[{value:"",label:tx("— select —")},...wcs.map(w=>({value:w.id,label:`${w.work_center_id} – ${w.name}`}))]} value={stepForm.work_center_id} onChange={e=>setStepForm(f=>({...f,work_center_id:e.target.value}))}/>
          <div className="grid grid-cols-2 gap-4">
            <Input label={tx("Standard Time (min) *")} type="number" value={stepForm.standard_time_minutes} onChange={e=>setStepForm(f=>({...f,standard_time_minutes:e.target.value}))} required/>
            <Input label={tx("Setup Time (min)")}       type="number" value={stepForm.setup_time_minutes}    onChange={e=>setStepForm(f=>({...f,setup_time_minutes:e.target.value}))}/>
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={()=>setStepOpen(false)}>{tx("Cancel")}</Button>
            <Button type="submit" loading={addStep.isPending}>{tx("Add Step")}</Button>
          </div>
        </form>
      </Modal>

      <Modal open={!!deletingId} onClose={()=>setDel(null)} title={tx("Delete Routing")}>
        <p className="text-sm text-gray-600 mb-4">{tx("Delete this routing and all its steps?")}</p>
        <div className="flex justify-end gap-3">
          <Button variant="secondary" onClick={()=>setDel(null)}>{tx("Cancel")}</Button>
          <Button variant="danger" loading={del.isPending} onClick={()=>deletingId&&del.mutate(deletingId)}>{tx("Delete")}</Button>
        </div>
      </Modal>
    </div>
  );
}

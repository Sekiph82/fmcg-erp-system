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

const TYPE_OPTS = [{value:"MATERIAL",label:"Material"},{value:"PRODUCT",label:"Product"},{value:"PACKAGING",label:"Packaging"}];
const CAT_OPTS  = [{value:"normal",label:"Normal"},{value:"abnormal",label:"Abnormal"}];
const FILTER    = [{value:"",label:"All"},{value:"true",label:"Anomalies Only"},{value:"false",label:"Normal Only"}];

export default function WasteYieldPage() {
  const qc = useQueryClient();
  const { toasts, toast, dismiss } = useToast();
  const [open, setOpen]       = useState(false);
  const [anomalyFilter, setAF] = useState("");
  const [deletingId, setDel]  = useState<string|null>(null);
  const [form, setForm] = useState({ waste_id:"", production_order_id:"", material_code:"", waste_type:"MATERIAL", waste_category:"normal", expected_qty:"", actual_qty:"", uom:"KG", reason:"" });

  const { data: items = [], isLoading } = useQuery({ queryKey:["waste",anomalyFilter], queryFn:()=>advProductionApi.listWaste(anomalyFilter!==""?{is_anomaly:anomalyFilter==="true"}:undefined) });

  const anomalies  = items.filter(i=>i.is_anomaly).length;
  const totalLoss  = items.reduce((s,i)=>s+Number(i.loss_qty),0);

  const create = useMutation({ mutationFn:()=>advProductionApi.createWaste({...form, production_order_id:form.production_order_id||undefined, expected_qty:parseFloat(form.expected_qty), actual_qty:parseFloat(form.actual_qty)}), onSuccess:()=>{ qc.invalidateQueries({queryKey:["waste"]}); setOpen(false); toast("success","Logged","Waste record saved."); }, onError:(e)=>toast("error","Failed",extractApiError(e)) });
  const del    = useMutation({ mutationFn:(id:string)=>advProductionApi.deleteWaste(id), onSuccess:()=>{ qc.invalidateQueries({queryKey:["waste"]}); setDel(null); toast("success","Deleted",""); }, onError:(e)=>toast("error","Failed",extractApiError(e)) });

  return (
    <div>
      <ToastContainer toasts={toasts} onDismiss={dismiss}/>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Waste & Yield Tracking</h1>
          <p className="text-sm text-gray-500 mt-1">Total loss: <strong>{totalLoss.toFixed(2)} units</strong> · <span className="text-red-600">{anomalies} anomal{anomalies===1?"y":"ies"}</span></p>
        </div>
        <div className="flex gap-2">
          <ImportModal module="waste_records" onSuccess={()=>qc.invalidateQueries({queryKey:["waste"]})}/>
          <Button onClick={()=>setOpen(true)}>+ Log Waste</Button>
        </div>
      </div>
      <div className="mb-4">
        <Select options={FILTER} value={anomalyFilter} onChange={e=>setAF(e.target.value)} className="w-44"/>
      </div>
      {isLoading ? <div className="flex justify-center py-16"><div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent"/></div> : (
        <Table keyField="id" data={items} emptyMessage="No waste records." columns={[
          { header:"Waste ID",   accessor:(r)=><span className="font-mono text-xs font-medium">{r.waste_id}</span> },
          { header:"Order No",   accessor:(r)=>r.order_no??"—" },
          { header:"Material",   accessor:(r)=>r.material_code??"—" },
          { header:"Type",       accessor:(r)=><Badge label={r.waste_type} variant="blue"/> },
          { header:"Expected",   accessor:(r)=>Number(r.expected_qty).toLocaleString() },
          { header:"Actual",     accessor:(r)=>Number(r.actual_qty).toLocaleString() },
          { header:"Loss",       accessor:(r)=><span className="font-medium text-red-600">{Number(r.loss_qty).toLocaleString()} ({r.loss_pct ? `${Number(r.loss_pct).toFixed(1)}%` : "—"})</span> },
          { header:"UOM",        accessor:"uom" },
          { header:"Anomaly",    accessor:(r)=>r.is_anomaly ? <Badge label="Anomaly" variant="red"/> : <Badge label="Normal" variant="green"/> },
          { header:"Reason",     accessor:(r)=><span className="text-xs text-gray-600 max-w-[180px] truncate block">{r.reason??"—"}</span> },
          { header:"", accessor:(r)=><button onClick={()=>setDel(r.id)} className="text-xs text-red-500 hover:underline">Delete</button> },
        ]}/>
      )}

      <Modal open={open} onClose={()=>setOpen(false)} title="Log Waste Record">
        <form onSubmit={e=>{e.preventDefault();create.mutate();}} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Input label="Waste ID *" value={form.waste_id} onChange={e=>setForm(f=>({...f,waste_id:e.target.value}))} required placeholder="W001"/>
            <Input label="Production Order ID" value={form.production_order_id} onChange={e=>setForm(f=>({...f,production_order_id:e.target.value}))} placeholder="UUID"/>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input label="Material Code" value={form.material_code} onChange={e=>setForm(f=>({...f,material_code:e.target.value}))} placeholder="e.g. SLES"/>
            <Select label="Waste Type" options={TYPE_OPTS} value={form.waste_type} onChange={e=>setForm(f=>({...f,waste_type:e.target.value}))}/>
          </div>
          <div className="grid grid-cols-3 gap-4">
            <Input label="Expected Qty *" type="number" step="any" value={form.expected_qty} onChange={e=>setForm(f=>({...f,expected_qty:e.target.value}))} required/>
            <Input label="Actual Qty *"   type="number" step="any" value={form.actual_qty}   onChange={e=>setForm(f=>({...f,actual_qty:e.target.value}))}   required/>
            <Input label="UOM"            value={form.uom}           onChange={e=>setForm(f=>({...f,uom:e.target.value}))}/>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Select label="Category" options={CAT_OPTS} value={form.waste_category} onChange={e=>setForm(f=>({...f,waste_category:e.target.value}))}/>
            <Input label="Reason"  value={form.reason} onChange={e=>setForm(f=>({...f,reason:e.target.value}))} placeholder="spillage, evaporation…"/>
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={()=>setOpen(false)}>Cancel</Button>
            <Button type="submit" loading={create.isPending}>Save</Button>
          </div>
        </form>
      </Modal>

      <Modal open={!!deletingId} onClose={()=>setDel(null)} title="Delete Waste Record">
        <p className="text-sm text-gray-600 mb-4">Remove this waste record?</p>
        <div className="flex justify-end gap-3">
          <Button variant="secondary" onClick={()=>setDel(null)}>Cancel</Button>
          <Button variant="danger" loading={del.isPending} onClick={()=>deletingId&&del.mutate(deletingId)}>Delete</Button>
        </div>
      </Modal>
    </div>
  );
}

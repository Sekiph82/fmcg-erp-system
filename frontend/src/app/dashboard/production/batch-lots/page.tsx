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

const STATUS_OPTS  = [{value:"quarantine",label:"Quarantine"},{value:"released",label:"Released"},{value:"rejected",label:"Rejected"},{value:"consumed",label:"Consumed"}];
const FILTER_OPTS  = [{value:"",label:"All"},...STATUS_OPTS];
const statusVariant = (s:string) => s==="released"?"green":s==="quarantine"?"yellow":s==="rejected"?"red":"blue";

const today = new Date().toISOString().slice(0,10);

export default function BatchLotsPage() {
  const qc = useQueryClient();
  const { toasts, toast, dismiss } = useToast();
  const [open, setOpen]       = useState(false);
  const [sfStatus, setSf]     = useState("");
  const [deletingId, setDel]  = useState<string|null>(null);
  const [releaseId, setRelease] = useState<string|null>(null);
  const [releasedBy, setReleasedBy] = useState("");
  const [form, setForm] = useState({ batch_id:"", production_order_id:"", product_id:"", product_sku:"", quantity:"", uom:"KG", manufacture_date:today, expiry_date:"", status:"quarantine" });

  const { data: items = [], isLoading } = useQuery({ queryKey:["batch-lots",sfStatus], queryFn:()=>advProductionApi.listBatchLots(sfStatus?{status:sfStatus}:undefined) });

  const quarantine = items.filter(i=>i.status==="quarantine").length;
  const released   = items.filter(i=>i.status==="released").length;

  const create  = useMutation({ mutationFn:()=>advProductionApi.createBatchLot({...form, production_order_id:form.production_order_id||undefined, product_id:form.product_id||undefined, quantity:parseFloat(form.quantity)}), onSuccess:()=>{ qc.invalidateQueries({queryKey:["batch-lots"]}); setOpen(false); toast("success","Created","Batch lot created."); }, onError:(e)=>toast("error","Failed",extractApiError(e)) });
  const release = useMutation({ mutationFn:()=>advProductionApi.updateBatchLot(releaseId!,{status:"released",released_by:releasedBy||undefined}), onSuccess:()=>{ qc.invalidateQueries({queryKey:["batch-lots"]}); setRelease(null); toast("success","Released","Batch released to production."); }, onError:(e)=>toast("error","Failed",extractApiError(e)) });
  const del     = useMutation({ mutationFn:(id:string)=>advProductionApi.deleteBatchLot(id), onSuccess:()=>{ qc.invalidateQueries({queryKey:["batch-lots"]}); setDel(null); toast("success","Deleted",""); }, onError:(e)=>toast("error","Failed",extractApiError(e)) });

  return (
    <div>
      <ToastContainer toasts={toasts} onDismiss={dismiss}/>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Batch / Lot Tracking</h1>
          <p className="text-sm text-gray-500 mt-1">{items.length} lots — <span className="text-yellow-600 font-medium">{quarantine} quarantine</span> · <span className="text-green-600 font-medium">{released} released</span></p>
        </div>
        <div className="flex gap-2">
          <ImportModal module="batch_lots" onSuccess={()=>qc.invalidateQueries({queryKey:["batch-lots"]})}/>
          <Button onClick={()=>setOpen(true)}>+ New Batch Lot</Button>
        </div>
      </div>
      <div className="mb-4">
        <Select options={FILTER_OPTS} value={sfStatus} onChange={e=>setSf(e.target.value)} className="w-44"/>
      </div>
      {isLoading ? <div className="flex justify-center py-16"><div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent"/></div> : (
        <Table keyField="id" data={items} emptyMessage="No batch lots." columns={[
          { header:"Batch ID",   accessor:(r)=><span className="font-mono text-xs font-medium">{r.batch_id}</span> },
          { header:"Product",    accessor:(r)=>r.product_name?? r.product_sku??"—" },
          { header:"Qty",        accessor:(r)=>`${Number(r.quantity).toLocaleString()} ${r.uom}` },
          { header:"Mfg Date",   accessor:(r)=>r.manufacture_date ?? "—" },
          { header:"Expiry",     accessor:(r)=>{
            if (!r.expiry_date) return "—";
            const daysLeft = Math.ceil((new Date(r.expiry_date).getTime()-Date.now())/(1000*86400));
            return <span className={daysLeft<90?"text-red-600":"text-gray-700"}>{r.expiry_date} ({daysLeft}d)</span>;
          }},
          { header:"Status",     accessor:(r)=><Badge label={r.status} variant={statusVariant(r.status)}/> },
          { header:"Order No",   accessor:(r)=>r.order_no??"—" },
          { header:"", accessor:(r)=>(
            <div className="flex gap-2">
              {r.status==="quarantine" && <button onClick={()=>{ setRelease(r.id); setReleasedBy(""); }} className="text-xs text-green-600 hover:underline">Release</button>}
              <button onClick={()=>setDel(r.id)} className="text-xs text-red-500 hover:underline">Delete</button>
            </div>
          )},
        ]}/>
      )}

      {/* Create */}
      <Modal open={open} onClose={()=>setOpen(false)} title="New Batch / Lot">
        <form onSubmit={e=>{e.preventDefault();create.mutate();}} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Input label="Batch ID *" value={form.batch_id} onChange={e=>setForm(f=>({...f,batch_id:e.target.value}))} required placeholder="BATCH001"/>
            <Input label="Production Order ID" value={form.production_order_id} onChange={e=>setForm(f=>({...f,production_order_id:e.target.value}))} placeholder="UUID"/>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input label="Product ID (UUID)" value={form.product_id} onChange={e=>setForm(f=>({...f,product_id:e.target.value}))} placeholder="UUID"/>
            <Input label="Product SKU"       value={form.product_sku} onChange={e=>setForm(f=>({...f,product_sku:e.target.value}))} placeholder="DET001"/>
          </div>
          <div className="grid grid-cols-3 gap-4">
            <Input label="Quantity *" type="number" step="any" value={form.quantity} onChange={e=>setForm(f=>({...f,quantity:e.target.value}))} required/>
            <Input label="UOM"        value={form.uom} onChange={e=>setForm(f=>({...f,uom:e.target.value}))}/>
            <Select label="Status" options={STATUS_OPTS} value={form.status} onChange={e=>setForm(f=>({...f,status:e.target.value}))}/>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input label="Manufacture Date" type="date" value={form.manufacture_date} onChange={e=>setForm(f=>({...f,manufacture_date:e.target.value}))}/>
            <Input label="Expiry Date"      type="date" value={form.expiry_date}      onChange={e=>setForm(f=>({...f,expiry_date:e.target.value}))}/>
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={()=>setOpen(false)}>Cancel</Button>
            <Button type="submit" loading={create.isPending}>Create Lot</Button>
          </div>
        </form>
      </Modal>

      {/* Release */}
      <Modal open={!!releaseId} onClose={()=>setRelease(null)} title="Release Batch Lot">
        <div className="space-y-4">
          <p className="text-sm text-gray-600">Confirm release of this batch from quarantine.</p>
          <Input label="Released By" value={releasedBy} onChange={e=>setReleasedBy(e.target.value)} placeholder="QA officer name"/>
          <div className="flex justify-end gap-3">
            <Button variant="secondary" onClick={()=>setRelease(null)}>Cancel</Button>
            <Button loading={release.isPending} onClick={()=>release.mutate()}>Confirm Release</Button>
          </div>
        </div>
      </Modal>

      <Modal open={!!deletingId} onClose={()=>setDel(null)} title="Delete Batch Lot">
        <p className="text-sm text-gray-600 mb-4">Remove this batch lot record?</p>
        <div className="flex justify-end gap-3">
          <Button variant="secondary" onClick={()=>setDel(null)}>Cancel</Button>
          <Button variant="danger" loading={del.isPending} onClick={()=>deletingId&&del.mutate(deletingId)}>Delete</Button>
        </div>
      </Modal>
    </div>
  );
}

"use client";
import { EntityPicker } from "@/components/EntityPicker";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { advProductionApi, QCInspection } from "@/lib/productionAdvanced";
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
import { PageHelpTooltip } from "@/components/help/PageHelpTooltip";
import { tx, lx } from "@/lib/i18n/core";

const TYPE_OPTS   = lx(() => [{value:"inline",label:tx("Inline")},{value:"final",label:tx("Final")},{value:"input",label:tx("Input")}]);
const STATUS_OPTS = lx(() => [{value:"pending",label:tx("Pending")},{value:"pass",label:tx("Passed")},{value:"fail",label:tx("Failed")},{value:"on_hold",label:tx("On Hold")}]);
const FILTER      = lx(() => [{value:"",label:tx("All")},...STATUS_OPTS]);

const statusVariant = (s:string) => s==="pass"?"green":s==="fail"?"red":s==="on_hold"?"yellow":"blue";

export default function QualityControlPage() {
  const qc = useQueryClient();
  const { toasts, toast, dismiss } = useToast();
  const [open, setOpen]       = useState(false);
  const [sfStatus, setSf]     = useState("");
  const [detail, setDetail]   = useState<QCInspection|null>(null);
  const [deletingId, setDel]  = useState<string|null>(null);
  const [form, setForm] = useState({ qc_id:"", production_order_id:"", inspection_type:"inline", status:"pending", checked_by:"", inspected_at:"", batch_ref:"" });
  const [results, setResults] = useState([{ test_type:"", actual_value:"", unit:"", result:"pass" }]);

  const { data: items = [], isLoading } = useQuery({ queryKey:["qc",sfStatus], queryFn:()=>advProductionApi.listQC(sfStatus?{status:sfStatus}:undefined) });

  const pass = items.filter(i=>i.status==="pass").length;
  const fail = items.filter(i=>i.status==="fail").length;

  const addResult    = ()=> setResults(r=>[...r,{test_type:"",actual_value:"",unit:"",result:"pass"}]);
  const updateResult = (idx:number, key:string, val:string) => setResults(r=>r.map((x,i)=>i===idx?{...x,[key]:val}:x));

  const create = useMutation({
    mutationFn:()=>advProductionApi.createQC({
      ...form, production_order_id: form.production_order_id||undefined,
      results: results.filter(r=>r.test_type).map(r=>({
        test_type: r.test_type, actual_value: r.actual_value ? parseFloat(r.actual_value) : undefined,
        unit: r.unit||undefined, result: r.result,
      })),
    }),
    onSuccess:()=>{ qc.invalidateQueries({queryKey:["qc"]}); setOpen(false); toast("success",tx("Created"),tx("QC inspection saved.")); },
    onError:(e)=>toast("error",tx("Failed"),extractApiError(e))
  });
  const updateStatus = useMutation({ mutationFn:({id,status}:{id:string;status:string})=>advProductionApi.updateQC(id,{status}), onSuccess:()=>{ qc.invalidateQueries({queryKey:["qc"]}); toast("success",tx("Updated"),tx("QC status changed.")); }, onError:(e)=>toast("error",tx("Failed"),extractApiError(e)) });
  const del = useMutation({ mutationFn:(id:string)=>advProductionApi.deleteQC(id), onSuccess:()=>{ qc.invalidateQueries({queryKey:["qc"]}); setDel(null); toast("success",tx("Deleted"),""); }, onError:(e)=>toast("error",tx("Failed"),extractApiError(e)) });

  return (
    <div>
      <ToastContainer toasts={toasts} onDismiss={dismiss}/>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{tx("Quality Control")}</h1>
          <p className="text-sm text-gray-500 mt-1">{items.length} {tx("inspections —")} <span className="text-green-600 font-medium">{pass} {tx("passed")}</span> · <span className="text-red-600 font-medium">{fail} {tx("failed")}</span></p>
        </div>
        <div className="flex gap-2 items-center">
          <PageHelpTooltip topic="production-qc" />
          <ImportModal module="qc_inspections" onSuccess={()=>qc.invalidateQueries({queryKey:["qc"]})}/>
          <Button onClick={()=>setOpen(true)}>{tx("+ New Inspection")}</Button>
        </div>
      </div>
      <div className="mb-4">
        <Select options={FILTER} value={sfStatus} onChange={e=>setSf(e.target.value)} className="w-44"/>
      </div>
      {isLoading ? <div className="flex justify-center py-16"><div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent"/></div> : (
        <Table keyField="id" data={items} emptyMessage="No QC inspections yet." columns={[
          { header:tx("QC ID"),          accessor:(r)=><button onClick={()=>setDetail(r)} className="font-mono text-xs text-indigo-600 hover:underline">{r.qc_id}</button> },
          { header:tx("Type"),           accessor:(r)=><Badge label={r.inspection_type} variant="blue"/> },
          { header:tx("Order No"),       accessor:(r)=>r.order_no??"—" },
          { header:tx("Checked By"),     accessor:(r)=>r.checked_by??"—" },
          { header:tx("Date"),           accessor:(r)=>r.inspected_at ? new Date(r.inspected_at).toLocaleDateString() : "—" },
          { header:tx("Results"),        accessor:(r)=><span className="text-xs text-gray-600">{r.results.length} {tx("test")}{r.results.length!==1?tx("s"):""}</span> },
          { header:tx("Status"),         accessor:(r)=><Badge label={r.status} variant={statusVariant(r.status)}/> },
          { header:"", accessor:(r)=>(
            <div className="flex gap-2">
              {r.status==="pending" && <button onClick={()=>updateStatus.mutate({id:r.id,status:"pass"})} className="text-xs text-green-600 hover:underline">{tx("Pass")}</button>}
              {r.status==="pending" && <button onClick={()=>updateStatus.mutate({id:r.id,status:"fail"})} className="text-xs text-red-600 hover:underline">{tx("Fail")}</button>}
              <button onClick={()=>setDel(r.id)} className="text-xs text-red-500 hover:underline">{tx("Delete")}</button>
            </div>
          )},
        ]}/>
      )}

      {/* Create */}
      <Modal open={open} onClose={()=>setOpen(false)} title={tx("New QC Inspection")}>
        <form onSubmit={e=>{e.preventDefault();create.mutate();}} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Input label={tx("QC ID *")}        value={form.qc_id}               onChange={e=>setForm(f=>({...f,qc_id:e.target.value}))}               required placeholder="QC001"/>
            <div><label className="block text-sm font-medium text-gray-700 mb-1">{tx("Production Order")}</label><EntityPicker kind="production_order" label={tx("Production order")} value={form.production_order_id} onChange={(id) => setForm((f) => ({ ...f, production_order_id: id }))} /></div>
          </div>
          <div className="grid grid-cols-3 gap-4">
            <Select label={tx("Type")}       options={TYPE_OPTS}   value={form.inspection_type} onChange={e=>setForm(f=>({...f,inspection_type:e.target.value}))}/>
            <Input label={tx("Checked By")}  value={form.checked_by}  onChange={e=>setForm(f=>({...f,checked_by:e.target.value}))}/>
            <Input label={tx("Date")}        type="datetime-local" onChange={e=>setForm(f=>({...f,inspected_at:e.target.value}))}/>
          </div>
          <Input label={tx("Batch Ref")} value={form.batch_ref} onChange={e=>setForm(f=>({...f,batch_ref:e.target.value}))}/>

          <div className="border-t pt-3">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm font-semibold text-gray-800">{tx("Test Results")}</p>
              <button type="button" onClick={addResult} className="text-xs text-indigo-600 hover:underline">{tx("+ Add Test")}</button>
            </div>
            {results.map((r,i)=>(
              <div key={i} className="grid grid-cols-4 gap-2 mb-2">
                <Input placeholder={tx("Test type (pH, viscosity…)")} value={r.test_type}     onChange={e=>updateResult(i,"test_type",e.target.value)}/>
                <Input placeholder={tx("Value")}                       value={r.actual_value}  onChange={e=>updateResult(i,"actual_value",e.target.value)} type="number" step="any"/>
                <Input placeholder={tx("Unit (pH, cP…)")}             value={r.unit}          onChange={e=>updateResult(i,"unit",e.target.value)}/>
                <Select options={[{value:"pass",label:tx("Pass")},{value:"fail",label:tx("Fail")}]} value={r.result} onChange={e=>updateResult(i,"result",e.target.value)}/>
              </div>
            ))}
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={()=>setOpen(false)}>{tx("Cancel")}</Button>
            <Button type="submit" loading={create.isPending}>{tx("Save Inspection")}</Button>
          </div>
        </form>
      </Modal>

      {/* Detail */}
      <Modal open={!!detail} onClose={()=>setDetail(null)} title={tx("QC Inspection — {qc_id}", { qc_id: detail?.qc_id })}>
        {detail && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div><span className="text-gray-500">{tx("Type:")}</span> <Badge label={detail.inspection_type} variant="blue"/></div>
              <div><span className="text-gray-500">{tx("Status:")}</span> <Badge label={detail.status} variant={statusVariant(detail.status)}/></div>
              <div><span className="text-gray-500">{tx("Checked by:")}</span> {detail.checked_by??"—"}</div>
              <div><span className="text-gray-500">{tx("Date:")}</span> {detail.inspected_at ? new Date(detail.inspected_at).toLocaleString() : "—"}</div>
            </div>
            <div className="border-t pt-3">
              <p className="text-sm font-semibold mb-2">{tx("Test Results")}</p>
              {detail.results.length === 0 ? <p className="text-xs text-gray-500">{tx("No test results.")}</p> : (
                <table className="w-full text-xs"><thead><tr className="text-gray-500"><th className="text-left py-1">{tx("Test")}</th><th>{tx("Value")}</th><th>{tx("Unit")}</th><th>{tx("Result")}</th></tr></thead>
                  <tbody>{detail.results.map(r=>(
                    <tr key={r.id} className="border-t">
                      <td className="py-1">{r.test_type}</td>
                      <td className="text-center">{r.actual_value??"—"}</td>
                      <td className="text-center">{r.unit??"—"}</td>
                      <td className="text-center"><Badge label={r.result} variant={r.result==="pass"?"green":"red"}/></td>
                    </tr>
                  ))}</tbody>
                </table>
              )}
            </div>
            <div className="flex justify-end"><Button variant="secondary" onClick={()=>setDetail(null)}>{tx("Close")}</Button></div>
          </div>
        )}
      </Modal>

      <Modal open={!!deletingId} onClose={()=>setDel(null)} title={tx("Delete Inspection")}>
        <p className="text-sm text-gray-600 mb-4">{tx("Remove this QC inspection and all test results?")}</p>
        <div className="flex justify-end gap-3">
          <Button variant="secondary" onClick={()=>setDel(null)}>{tx("Cancel")}</Button>
          <Button variant="danger" loading={del.isPending} onClick={()=>deletingId&&del.mutate(deletingId)}>{tx("Delete")}</Button>
        </div>
      </Modal>
    </div>
  );
}

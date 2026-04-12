"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { logisticsApi, CustomsDocument, CustomsDocType, CustomsDocStatus } from "@/lib/logistics";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";

const statusBadge = (s: CustomsDocStatus) =>
  s === "APPROVED" ? "green" : s === "REJECTED" ? "red" : s === "SUBMITTED" ? "blue" : "yellow";

const DOC_TYPES: { value: CustomsDocType; label: string }[] = [
  { value: "COMMERCIAL_INVOICE", label: "Commercial Invoice" },
  { value: "PACKING_LIST", label: "Packing List" },
  { value: "BILL_OF_LADING", label: "Bill of Lading" },
  { value: "AIRWAY_BILL", label: "Airway Bill" },
  { value: "CERTIFICATE_OF_ORIGIN", label: "Certificate of Origin" },
  { value: "PHYTOSANITARY", label: "Phytosanitary Certificate" },
  { value: "IMPORT_DECLARATION", label: "Import Declaration (IDF)" },
  { value: "DUTY_RECEIPT", label: "Duty Payment Receipt" },
  { value: "OTHER", label: "Other" },
];

export default function DocumentsPage() {
  const qc = useQueryClient();
  const [selectedShipmentId, setSelectedShipmentId] = useState<string>("");
  const [showNew, setShowNew] = useState(false);
  const [editing, setEditing] = useState<CustomsDocument | null>(null);

  const { data: shipments = [] } = useQuery({
    queryKey: ["logistics-shipments"],
    queryFn: () => logisticsApi.listShipments(),
  });

  const { data: documents = [], isLoading } = useQuery({
    queryKey: ["logistics-documents", selectedShipmentId],
    queryFn: () => selectedShipmentId ? logisticsApi.listDocuments(selectedShipmentId) : Promise.resolve([]),
    enabled: !!selectedShipmentId,
  });

  const createDoc = useMutation({
    mutationFn: (d: object) => logisticsApi.createDocument(d),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["logistics-documents"] }); setShowNew(false); },
  });

  const updateDoc = useMutation({
    mutationFn: ({ id, data }: { id: string; data: object }) => logisticsApi.updateDocument(id, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["logistics-documents"] }); setEditing(null); },
  });

  const required: CustomsDocType[] = ["COMMERCIAL_INVOICE", "PACKING_LIST", "BILL_OF_LADING", "CERTIFICATE_OF_ORIGIN", "IMPORT_DECLARATION"];
  const present = new Set(documents.map((d) => d.doc_type));
  const missing = required.filter((t) => !present.has(t));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Customs Documents</h1>
          <p className="text-sm text-gray-500 mt-1">Invoice, B/L, packing list and clearance certificates</p>
        </div>
        {selectedShipmentId && <Button onClick={() => setShowNew(true)}>Add Document</Button>}
      </div>

      {/* Shipment selector */}
      <div className="flex items-center gap-3">
        <label className="text-sm font-medium text-gray-600">Shipment:</label>
        <select
          className="border rounded px-3 py-2 text-sm min-w-64"
          value={selectedShipmentId}
          onChange={(e) => setSelectedShipmentId(e.target.value)}
        >
          <option value="">Select shipment…</option>
          {shipments.map((s) => (
            <option key={s.id} value={s.id}>{s.shipment_no} — {s.vessel_name || s.carrier || s.origin_port}</option>
          ))}
        </select>
      </div>

      {/* Missing documents alert */}
      {selectedShipmentId && missing.length > 0 && (
        <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
          <p className="text-sm font-semibold text-orange-800 mb-1">Missing required documents ({missing.length})</p>
          <div className="flex flex-wrap gap-2">
            {missing.map((t) => (
              <span key={t} className="px-2 py-0.5 bg-orange-100 text-orange-700 rounded text-xs font-medium">
                {DOC_TYPES.find((d) => d.value === t)?.label ?? t}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Document checklist */}
      {selectedShipmentId && (
        <div className="grid grid-cols-3 gap-3">
          {DOC_TYPES.map(({ value, label }) => {
            const doc = documents.find((d) => d.doc_type === value);
            return (
              <div key={value} className={`bg-white border rounded-lg p-4 ${doc ? "" : "border-dashed border-gray-300"}`}>
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-xs font-semibold text-gray-700">{label}</p>
                    {doc ? (
                      <>
                        <p className="text-xs text-gray-500 mt-1 font-mono">{doc.doc_no}</p>
                        {doc.doc_date && <p className="text-xs text-gray-400">{doc.doc_date}</p>}
                        {doc.issuer && <p className="text-xs text-gray-400">{doc.issuer}</p>}
                        {doc.file_ref && <p className="text-xs text-indigo-500 mt-1 truncate">{doc.file_ref}</p>}
                      </>
                    ) : (
                      <p className="text-xs text-gray-400 mt-1">Not uploaded</p>
                    )}
                  </div>
                  {doc && <Badge label={doc.status} variant={statusBadge(doc.status)} />}
                </div>
                {doc ? (
                  <button className="mt-2 text-xs text-indigo-600 hover:underline" onClick={() => setEditing(doc)}>Update</button>
                ) : (
                  <button className="mt-2 text-xs text-green-600 hover:underline" onClick={() => setShowNew(true)}>Upload</button>
                )}
              </div>
            );
          })}
        </div>
      )}

      {!selectedShipmentId && (
        <div className="bg-white rounded-lg border p-12 text-center text-gray-400">
          Select a shipment to view and manage its documents
        </div>
      )}

      {/* All documents table */}
      {selectedShipmentId && documents.length > 0 && (
        <div className="bg-white rounded-lg border">
          <div className="px-5 py-3 border-b font-semibold text-gray-800">All Documents</div>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-xs text-gray-500 uppercase">
                <th className="px-5 py-2 text-left">Type</th>
                <th className="px-5 py-2 text-left">Doc No</th>
                <th className="px-5 py-2 text-left">Date</th>
                <th className="px-5 py-2 text-left">Issuer</th>
                <th className="px-5 py-2 text-left">File Ref</th>
                <th className="px-5 py-2 text-left">Status</th>
                <th className="px-5 py-2" />
              </tr>
            </thead>
            <tbody className="divide-y">
              {documents.map((d) => (
                <tr key={d.id} className="hover:bg-gray-50">
                  <td className="px-5 py-3 font-medium">{DOC_TYPES.find((x) => x.value === d.doc_type)?.label ?? d.doc_type}</td>
                  <td className="px-5 py-3 font-mono text-xs">{d.doc_no}</td>
                  <td className="px-5 py-3 text-gray-500">{d.doc_date || "—"}</td>
                  <td className="px-5 py-3 text-gray-600">{d.issuer || "—"}</td>
                  <td className="px-5 py-3 text-indigo-500 text-xs truncate max-w-xs">{d.file_ref || "—"}</td>
                  <td className="px-5 py-3"><Badge label={d.status} variant={statusBadge(d.status)} /></td>
                  <td className="px-5 py-3">
                    <button className="text-xs text-indigo-600 hover:underline" onClick={() => setEditing(d)}>Edit</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showNew && selectedShipmentId && (
        <DocModal title="Add Document" shipmentId={selectedShipmentId}
          onClose={() => setShowNew(false)} onSubmit={(d) => createDoc.mutate(d)} loading={createDoc.isPending} />
      )}
      {editing && (
        <DocModal title="Update Document" initial={editing} shipmentId={editing.shipment_id}
          onClose={() => setEditing(null)} onSubmit={(d) => updateDoc.mutate({ id: editing.id, data: d })} loading={updateDoc.isPending} />
      )}
    </div>
  );
}

function DocModal({ title, initial, shipmentId, onClose, onSubmit, loading }: {
  title: string; initial?: CustomsDocument; shipmentId: string;
  onClose: () => void; onSubmit: (d: object) => void; loading: boolean;
}) {
  const [form, setForm] = useState({
    shipment_id: shipmentId,
    doc_type: initial?.doc_type ?? "COMMERCIAL_INVOICE",
    doc_no: initial?.doc_no ?? "",
    doc_date: initial?.doc_date ?? "",
    issuer: initial?.issuer ?? "",
    description: initial?.description ?? "",
    file_ref: initial?.file_ref ?? "",
    status: initial?.status ?? "DRAFT",
  });
  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6 space-y-4">
        <h2 className="font-semibold text-lg">{title}</h2>
        <div className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Document Type</label>
            <select className="w-full border rounded px-3 py-2 text-sm" value={form.doc_type} onChange={(e) => set("doc_type", e.target.value)}>
              {DOC_TYPES.map((d) => <option key={d.value} value={d.value}>{d.label}</option>)}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Document No</label>
              <input className="w-full border rounded px-3 py-2 text-sm" value={form.doc_no} onChange={(e) => set("doc_no", e.target.value)} />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Date</label>
              <input type="date" className="w-full border rounded px-3 py-2 text-sm" value={form.doc_date} onChange={(e) => set("doc_date", e.target.value)} />
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Issuer</label>
            <input className="w-full border rounded px-3 py-2 text-sm" value={form.issuer} onChange={(e) => set("issuer", e.target.value)} placeholder="Company / authority name" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">File Reference (path / URL placeholder)</label>
            <input className="w-full border rounded px-3 py-2 text-sm" value={form.file_ref} onChange={(e) => set("file_ref", e.target.value)} placeholder="e.g. docs/ISH-00001/invoice.pdf" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Status</label>
            <select className="w-full border rounded px-3 py-2 text-sm" value={form.status} onChange={(e) => set("status", e.target.value)}>
              <option value="DRAFT">Draft</option>
              <option value="SUBMITTED">Submitted</option>
              <option value="APPROVED">Approved</option>
              <option value="REJECTED">Rejected</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Description / Notes</label>
            <textarea className="w-full border rounded px-3 py-2 text-sm" rows={2} value={form.description} onChange={(e) => set("description", e.target.value)} />
          </div>
        </div>
        <div className="flex gap-2 justify-end">
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button loading={loading} onClick={() => onSubmit({ ...form, doc_date: form.doc_date || undefined })}>Save</Button>
        </div>
      </div>
    </div>
  );
}

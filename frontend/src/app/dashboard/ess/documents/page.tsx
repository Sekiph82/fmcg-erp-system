"use client";
import { useEffect, useState } from "react";
import { essApi, ESSDocument, ESSDocumentType } from "@/lib/ess";

const DEMO_EMPLOYEE = "00000000-0000-0000-0000-000000000001";

const DOC_ICONS: Record<ESSDocumentType, string> = {
  payslip: "💰", contract: "📝", offer_letter: "📨",
  experience_cert: "🏆", salary_cert: "💼", hr_letter: "📮",
  appraisal: "⭐", other: "📄",
};

const DOC_TYPES: ESSDocumentType[] = ["payslip", "contract", "offer_letter", "experience_cert", "salary_cert", "hr_letter", "appraisal", "other"];

export default function DocumentsPage() {
  const [docs, setDocs] = useState<ESSDocument[]>([]);
  const [filter, setFilter] = useState<string>("");

  useEffect(() => {
    essApi.listDocuments(DEMO_EMPLOYEE, filter || undefined).then(setDocs).catch(console.error);
  }, [filter]);

  const grouped = DOC_TYPES.reduce((acc, t) => {
    const items = docs.filter((d) => d.document_type === t);
    if (items.length > 0) acc[t] = items;
    return acc;
  }, {} as Record<string, ESSDocument[]>);

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">Document Center</h1>
        <select value={filter} onChange={(e) => setFilter(e.target.value)} className="border rounded px-3 py-2 text-sm">
          <option value="">All Types</option>
          {DOC_TYPES.map((t) => <option key={t} value={t}>{t.replace("_", " ")}</option>)}
        </select>
      </div>

      {Object.keys(grouped).length === 0 && (
        <div className="bg-white border rounded-xl p-8 text-center text-gray-400 text-sm">
          No documents available. HR will upload documents here.
        </div>
      )}

      {Object.entries(grouped).map(([type, items]) => (
        <div key={type} className="space-y-2">
          <h2 className="text-sm font-semibold text-gray-600 flex items-center gap-2">
            <span>{DOC_ICONS[type as ESSDocumentType]}</span>
            {type.replace("_", " ").toUpperCase()}
            <span className="text-xs font-normal text-gray-400">({items.length})</span>
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {items.map((doc) => (
              <div key={doc.document_id} className="bg-white border rounded-xl p-4 flex items-start gap-3 hover:bg-gray-50">
                <span className="text-2xl">{DOC_ICONS[doc.document_type]}</span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{doc.document_name}</p>
                  {doc.period && <p className="text-xs text-gray-400">{doc.period}</p>}
                  <p className="text-xs text-gray-300">{new Date(doc.created_at).toLocaleDateString()}</p>
                  {doc.document_ref && (
                    <a href={doc.document_ref} target="_blank" rel="noopener noreferrer"
                      className="text-xs text-blue-600 hover:underline mt-1 block">Download / View</a>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

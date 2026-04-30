"use client";
import { useEffect, useState } from "react";
import { essApi, ESSDocument, ESSDocumentType } from "@/lib/ess";

const DEMO_EMPLOYEE = "00000000-0000-0000-0000-000000000001";
const DOC_ICONS: Record<ESSDocumentType, string> = { payslip: "💰", contract: "📝", offer_letter: "📨", experience_cert: "🏆", salary_cert: "💼", hr_letter: "📮", appraisal: "⭐", other: "📄" };
const DOC_TYPES: ESSDocumentType[] = ["payslip", "contract", "offer_letter", "experience_cert", "salary_cert", "hr_letter", "appraisal", "other"];

export default function DocumentsPage() {
  const [docs, setDocs] = useState<ESSDocument[]>([]);
  const [filter, setFilter] = useState<string>("");

  useEffect(() => { essApi.listDocuments(DEMO_EMPLOYEE, filter || undefined).then(setDocs).catch(console.error); }, [filter]);

  const grouped = DOC_TYPES.reduce((acc, t) => {
    const items = docs.filter((d) => d.document_type === t);
    if (items.length > 0) acc[t] = items;
    return acc;
  }, {} as Record<string, ESSDocument[]>);

  return (
    <div className="p-6 space-y-5 min-h-screen bg-[#060d18] text-slate-200">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Document Center</h1>
          <p className="text-slate-500 text-sm mt-0.5">{docs.length} documents available</p>
        </div>
        <select value={filter} onChange={(e) => setFilter(e.target.value)}
          className="bg-[#0d1829] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white focus:outline-none">
          <option value="">All Types</option>
          {DOC_TYPES.map((t) => <option key={t} value={t}>{t.replace("_", " ")}</option>)}
        </select>
      </div>

      {Object.keys(grouped).length === 0 && (
        <div className="rounded-xl border border-white/[0.07] bg-[#0d1829] p-8 text-center text-slate-600">
          No documents available. HR will upload documents here.
        </div>
      )}

      {Object.entries(grouped).map(([type, items]) => (
        <div key={type} className="space-y-2">
          <p className="text-[10px] text-slate-500 uppercase tracking-widest flex items-center gap-2">
            <span>{DOC_ICONS[type as ESSDocumentType]}</span>{type.replace("_", " ")} <span className="text-slate-600">({items.length})</span>
          </p>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {items.map((doc) => (
              <div key={doc.document_id} className="rounded-xl border border-white/[0.07] bg-[#0d1829] hover:bg-white/[0.04] p-4 flex items-start gap-3 transition-colors">
                <span className="text-2xl">{DOC_ICONS[doc.document_type]}</span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-white font-medium truncate">{doc.document_name}</p>
                  {doc.period && <p className="text-xs text-slate-500">{doc.period}</p>}
                  <p className="text-xs text-slate-600">{new Date(doc.created_at).toLocaleDateString()}</p>
                  {doc.document_ref && (
                    <a href={doc.document_ref} target="_blank" rel="noopener noreferrer"
                      className="text-xs text-indigo-400 hover:text-indigo-300 mt-1 block">Download / View →</a>
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

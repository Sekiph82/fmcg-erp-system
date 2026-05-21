"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  taxApi, CountryTaxConfig, RegulatoryFlag, RegulatoryFlagType, ComplianceStatus,
} from "@/lib/tax_regulatory";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";

const STATUS_VARIANT: Record<string, "green" | "red" | "yellow" | "gray" | "blue"> = {
  COMPLIANT: "green",
  NON_COMPLIANT: "red",
  EXPIRED: "red",
  PENDING: "yellow",
  NOT_APPLICABLE: "gray",
};

const FLAG_TYPES: RegulatoryFlagType[] = [
  "CHEMICAL_COMPLIANCE", "RESTRICTED_GOODS", "IMPORT_LICENSE", "EXPORT_LICENSE",
  "PHYTOSANITARY", "HALAL_CERTIFICATION", "KEBS_STANDARD", "KEPHIS", "REACH_COMPLIANCE", "OTHER",
];

const STATUSES: ComplianceStatus[] = ["COMPLIANT", "NON_COMPLIANT", "PENDING", "EXPIRED", "NOT_APPLICABLE"];

export default function RegulatoryFlagsPage() {
  const qc = useQueryClient();
  const [filterCountry, setFilterCountry] = useState("");
  const [filterStatus, setFilterStatus] = useState<ComplianceStatus | "ALL">("ALL");
  const [showNew, setShowNew] = useState(false);
  const [editing, setEditing] = useState<RegulatoryFlag | null>(null);

  const { data: countries = [] } = useQuery({ queryKey: ["tax-countries"], queryFn: taxApi.listCountries });

  const { data: flags = [], isLoading } = useQuery({
    queryKey: ["regulatory-flags", filterCountry, filterStatus],
    queryFn: () => taxApi.listFlags({
      country_code: filterCountry || undefined,
      status: filterStatus !== "ALL" ? filterStatus : undefined,
    }),
  });

  const { data: expiring = [] } = useQuery({
    queryKey: ["expiring-flags"],
    queryFn: () => taxApi.getExpiringFlags(30),
  });

  const createFlag = useMutation({
    mutationFn: (d: object) => taxApi.createFlag(d),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["regulatory-flags"] }); setShowNew(false); },
  });
  const updateFlag = useMutation({
    mutationFn: ({ id, data }: { id: string; data: object }) => taxApi.updateFlag(id, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["regulatory-flags"] }); setEditing(null); },
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Regulatory Flags</h1>
          <p className="text-sm text-gray-500 mt-1">Chemical compliance, licenses, certifications (KEBS, KEPHIS, REACH, Halal…)</p>
        </div>
        <Button onClick={() => setShowNew(true)}>Add Flag</Button>
      </div>

      {/* Expiry alert */}
      {expiring.length > 0 && (
        <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
          <p className="font-semibold text-orange-800 text-sm mb-2">{expiring.length} certificate(s) expiring within 30 days</p>
          <div className="flex flex-wrap gap-2">
            {expiring.map((f: RegulatoryFlag) => (
              <span key={f.id} className="px-2 py-0.5 bg-orange-100 text-orange-700 rounded text-xs">
                {f.country_code} · {f.flag_type.replace(/_/g, " ")} · exp {f.expiry_date}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap gap-3 items-center">
        <select className="border rounded px-3 py-2 text-sm" value={filterCountry} onChange={(e) => setFilterCountry(e.target.value)}>
          <option value="">All countries</option>
          {countries.map((c: CountryTaxConfig) => <option key={c.country_code} value={c.country_code}>{c.country_code} — {c.country_name}</option>)}
        </select>
        <div className="flex flex-wrap gap-2">
          {(["ALL", ...STATUSES] as const).map((s) => (
            <button key={s} onClick={() => setFilterStatus(s)}
              className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${filterStatus === s ? "bg-indigo-600 text-white" : "bg-white border text-gray-600 hover:border-indigo-300"}`}>
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* Flags table */}
      <div className="bg-white rounded-lg border overflow-x-auto">
        {isLoading ? <p className="px-5 py-8 text-center text-gray-400">Loading…</p> : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-xs text-gray-500 uppercase">
                <th className="px-5 py-2 text-left">Country</th>
                <th className="px-5 py-2 text-left">Flag Type</th>
                <th className="px-5 py-2 text-left">HS Code</th>
                <th className="px-5 py-2 text-left">Status</th>
                <th className="px-5 py-2 text-left">Authority</th>
                <th className="px-5 py-2 text-left">License No</th>
                <th className="px-5 py-2 text-left">Issue Date</th>
                <th className="px-5 py-2 text-left">Expiry Date</th>
                <th className="px-5 py-2 text-left">Doc Ref</th>
                <th className="px-5 py-2" />
              </tr>
            </thead>
            <tbody className="divide-y">
              {flags.map((f: RegulatoryFlag) => {
                const isExpiringSoon = expiring.some((e: RegulatoryFlag) => e.id === f.id);
                return (
                  <tr key={f.id} className={`hover:bg-gray-50 ${isExpiringSoon ? "bg-orange-50" : ""}`}>
                    <td className="px-5 py-3 font-mono font-bold text-indigo-700">{f.country_code}</td>
                    <td className="px-5 py-3 font-medium">{f.flag_type.replace(/_/g, " ")}</td>
                    <td className="px-5 py-3 font-mono text-xs">{f.hs_code || "—"}</td>
                    <td className="px-5 py-3"><Badge label={f.status} variant={STATUS_VARIANT[f.status]} /></td>
                    <td className="px-5 py-3 text-gray-600">{f.authority || "—"}</td>
                    <td className="px-5 py-3 font-mono text-xs">{f.license_no || "—"}</td>
                    <td className="px-5 py-3 text-gray-500">{f.issue_date || "—"}</td>
                    <td className={`px-5 py-3 ${isExpiringSoon ? "text-orange-600 font-semibold" : "text-gray-500"}`}>
                      {f.expiry_date || "—"}
                    </td>
                    <td className="px-5 py-3 text-indigo-500 text-xs truncate max-w-xs">{f.document_ref || "—"}</td>
                    <td className="px-5 py-3">
                      <button className="text-xs text-indigo-600 hover:underline" onClick={() => setEditing(f)}>Edit</button>
                    </td>
                  </tr>
                );
              })}
              {flags.length === 0 && <tr><td colSpan={10} className="px-5 py-8 text-center text-gray-400">No flags found</td></tr>}
            </tbody>
          </table>
        )}
      </div>

      {showNew && (
        <FlagModal countries={countries.map((c: CountryTaxConfig) => ({ code: c.country_code, name: c.country_name }))}
          onClose={() => setShowNew(false)} onSubmit={(d) => createFlag.mutate(d)} loading={createFlag.isPending} />
      )}
      {editing && (
        <FlagModal initial={editing} countries={countries.map((c: CountryTaxConfig) => ({ code: c.country_code, name: c.country_name }))}
          onClose={() => setEditing(null)} onSubmit={(d) => updateFlag.mutate({ id: editing.id, data: d })} loading={updateFlag.isPending} />
      )}
    </div>
  );
}

function FlagModal({ initial, countries, onClose, onSubmit, loading }: {
  initial?: RegulatoryFlag; countries: { code: string; name: string }[];
  onClose: () => void; onSubmit: (d: object) => void; loading: boolean;
}) {
  const isEdit = !!initial;
  const [form, setForm] = useState({
    country_code: initial?.country_code ?? "",
    flag_type: initial?.flag_type ?? ("IMPORT_LICENSE" as RegulatoryFlagType),
    hs_code: initial?.hs_code ?? "",
    status: initial?.status ?? ("PENDING" as ComplianceStatus),
    authority: initial?.authority ?? "",
    license_no: initial?.license_no ?? "",
    issue_date: initial?.issue_date ?? "",
    expiry_date: initial?.expiry_date ?? "",
    document_ref: initial?.document_ref ?? "",
    restriction_details: initial?.restriction_details ?? "",
    notes: initial?.notes ?? "",
  });
  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg p-6 space-y-4 max-h-[90vh] overflow-y-auto">
        <h2 className="font-semibold text-lg">{isEdit ? "Edit Regulatory Flag" : "Add Regulatory Flag"}</h2>
        <div className="grid grid-cols-2 gap-3">
          {!isEdit && (
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Country</label>
              <select className="w-full border rounded px-3 py-2 text-sm" value={form.country_code} onChange={(e) => set("country_code", e.target.value)}>
                <option value="">Select…</option>
                {countries.map((c) => <option key={c.code} value={c.code}>{c.code} — {c.name}</option>)}
              </select>
            </div>
          )}
          {!isEdit && (
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Flag Type</label>
              <select className="w-full border rounded px-3 py-2 text-sm" value={form.flag_type} onChange={(e) => set("flag_type", e.target.value)}>
                {FLAG_TYPES.map((t) => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
              </select>
            </div>
          )}
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Status</label>
            <select className="w-full border rounded px-3 py-2 text-sm" value={form.status} onChange={(e) => set("status", e.target.value)}>
              {STATUSES.map((s) => <option key={s} value={s}>{s.replace(/_/g, " ")}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Authority</label>
            <input className="w-full border rounded px-3 py-2 text-sm" value={form.authority} onChange={(e) => set("authority", e.target.value)} placeholder="e.g. KEBS, KEPHIS, KRA" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">License / Cert No</label>
            <input className="w-full border rounded px-3 py-2 text-sm font-mono" value={form.license_no} onChange={(e) => set("license_no", e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">HS Code</label>
            <input className="w-full border rounded px-3 py-2 text-sm font-mono" value={form.hs_code} onChange={(e) => set("hs_code", e.target.value)} placeholder="e.g. 3402.20" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Issue Date</label>
            <input type="date" className="w-full border rounded px-3 py-2 text-sm" value={form.issue_date} onChange={(e) => set("issue_date", e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Expiry Date</label>
            <input type="date" className="w-full border rounded px-3 py-2 text-sm" value={form.expiry_date} onChange={(e) => set("expiry_date", e.target.value)} />
          </div>
          <div className="col-span-2">
            <label className="block text-xs font-medium text-gray-600 mb-1">Document Reference</label>
            <input className="w-full border rounded px-3 py-2 text-sm" value={form.document_ref} onChange={(e) => set("document_ref", e.target.value)} placeholder="e.g. docs/kebs/cert-12345.pdf" />
          </div>
          <div className="col-span-2">
            <label className="block text-xs font-medium text-gray-600 mb-1">Restriction Details</label>
            <textarea className="w-full border rounded px-3 py-2 text-sm" rows={2} value={form.restriction_details} onChange={(e) => set("restriction_details", e.target.value)} />
          </div>
          <div className="col-span-2">
            <label className="block text-xs font-medium text-gray-600 mb-1">Notes</label>
            <textarea className="w-full border rounded px-3 py-2 text-sm" rows={2} value={form.notes} onChange={(e) => set("notes", e.target.value)} />
          </div>
        </div>
        <div className="flex gap-2 justify-end">
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button loading={loading} onClick={() => onSubmit({
            ...form,
            issue_date: form.issue_date || null,
            expiry_date: form.expiry_date || null,
          })}>Save</Button>
        </div>
      </div>
    </div>
  );
}

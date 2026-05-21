"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { moApi, SkillCert, CertStatus, CERT_STATUS_COLORS } from "@/lib/machineOperator";

export default function CertsPage() {
  const qc = useQueryClient();
  const [expiringOnly, setExpiringOnly] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({
    operator_id: "", machine_id: "", operation_code: "",
    skill_level: "BASIC", certification_required: false,
    certification_expiry: "", notes: "",
  });

  const { data, isLoading } = useQuery<SkillCert[]>({
    queryKey: ["mo-certs", expiringOnly],
    queryFn: () => moApi.listSkills(expiringOnly ? { expiring_only: "true" } : {}),
  });

  const refresh = useMutation({
    mutationFn: () => moApi.refreshCertStatuses(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["mo-certs"] }),
  });

  const create = useMutation({
    mutationFn: () => moApi.createSkill({
      ...form,
      certification_expiry: form.certification_expiry || undefined,
    } as unknown as import("@/lib/machineOperator").SkillCert),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["mo-certs"] });
      setShowCreate(false);
    },
  });

  const certs = data || [];
  const expired = certs.filter((c) => c.cert_status === "EXPIRED").length;
  const expiring = certs.filter((c) => c.cert_status === "EXPIRING_SOON").length;
  const valid = certs.filter((c) => c.cert_status === "VALID").length;

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <a href="/dashboard/machine-ops" className="text-sm text-indigo-600 hover:underline">← Dashboard</a>
          <h1 className="text-xl font-bold text-gray-900">Certification Expiry Monitor</h1>
        </div>
        <div className="flex gap-2">
          <button onClick={() => refresh.mutate()} disabled={refresh.isPending} className="border border-gray-300 text-gray-600 px-3 py-2 rounded-lg text-sm hover:bg-gray-50 disabled:opacity-50">
            {refresh.isPending ? "Refreshing…" : "Refresh Statuses"}
          </button>
          <button onClick={() => setShowCreate(true)} className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700">+ Add Cert</button>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-3">
        {[
          { label: "Total Certs", value: certs.length },
          { label: "Valid", value: valid, color: "text-green-700" },
          { label: "Expiring Soon", value: expiring, color: expiring > 0 ? "text-yellow-600" : "text-gray-700" },
          { label: "Expired", value: expired, color: expired > 0 ? "text-red-600" : "text-gray-700" },
        ].map((s) => (
          <div key={s.label} className="bg-white rounded-lg border p-3 text-center">
            <p className="text-xs text-gray-500">{s.label}</p>
            <p className={`text-2xl font-bold ${s.color || "text-gray-900"}`}>{s.value}</p>
          </div>
        ))}
      </div>

      {(expired > 0 || expiring > 0) && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 text-sm text-yellow-800">
          ⚠ {expired > 0 ? `${expired} expired certification(s) — these operators are blocked from certified assignments. ` : ""}
          {expiring > 0 ? `${expiring} certification(s) expiring within 30 days.` : ""}
        </div>
      )}

      <div className="bg-white rounded-lg border p-3 flex items-center gap-3">
        <label className="flex items-center gap-2 text-sm cursor-pointer">
          <input type="checkbox" checked={expiringOnly} onChange={(e) => setExpiringOnly(e.target.checked)} className="rounded" />
          Show expiring / expired only
        </label>
      </div>

      <div className="bg-white rounded-lg border overflow-x-auto">
        {isLoading && <div className="p-6 text-gray-400 text-sm">Loading…</div>}
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>{["Operator", "Machine", "Operation", "Skill Level", "Required", "Expiry", "Status"].map((h) => (
              <th key={h} className="px-4 py-2 text-left text-xs font-medium text-gray-600">{h}</th>
            ))}</tr>
          </thead>
          <tbody className="divide-y">
            {certs.map((c) => (
              <tr key={c.id} className={`hover:bg-gray-50 ${c.cert_status === "EXPIRED" ? "bg-red-50" : c.cert_status === "EXPIRING_SOON" ? "bg-yellow-50" : ""}`}>
                <td className="px-4 py-2.5 text-xs">{c.operator_name || c.operator_id?.slice(0, 8)}</td>
                <td className="px-4 py-2.5 text-xs">{c.machine_name || c.machine_id?.slice(0, 8) || "—"}</td>
                <td className="px-4 py-2.5 font-mono text-xs">{c.operation_code || "—"}</td>
                <td className="px-4 py-2.5 text-xs">{c.skill_level}</td>
                <td className="px-4 py-2.5 text-xs">{c.certification_required ? "Yes" : "No"}</td>
                <td className={`px-4 py-2.5 text-xs font-medium ${c.cert_status === "EXPIRED" ? "text-red-600" : c.cert_status === "EXPIRING_SOON" ? "text-yellow-600" : "text-gray-700"}`}>
                  {c.certification_expiry || "—"}
                </td>
                <td className="px-4 py-2.5">
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${CERT_STATUS_COLORS[c.cert_status]}`}>{c.cert_status.replace("_", " ")}</span>
                </td>
              </tr>
            ))}
            {!isLoading && !certs.length && (
              <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400 text-sm">No certifications found.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {showCreate && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl p-6 w-[480px] space-y-4">
            <h2 className="font-bold text-gray-900">Add Skill / Certification</h2>
            <div className="grid grid-cols-2 gap-3">
              {[
                { label: "Operator ID *", field: "operator_id", placeholder: "UUID" },
                { label: "Machine ID", field: "machine_id", placeholder: "UUID (optional)" },
                { label: "Operation Code", field: "operation_code", placeholder: "e.g. FILLING-OPS" },
                { label: "Expiry Date", field: "certification_expiry", type: "date" },
              ].map(({ label, field, placeholder, type }) => (
                <div key={field}>
                  <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
                  <input
                    type={type || "text"}
                    value={(form as unknown as Record<string, string>)[field]}
                    onChange={(e) => setForm((p) => ({ ...p, [field]: e.target.value }))}
                    className="w-full border rounded px-3 py-2 text-sm"
                    placeholder={placeholder}
                  />
                </div>
              ))}
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Skill Level</label>
                <select value={form.skill_level} onChange={(e) => setForm((p) => ({ ...p, skill_level: e.target.value }))} className="w-full border rounded px-3 py-2 text-sm">
                  {["TRAINEE", "BASIC", "INTERMEDIATE", "ADVANCED", "EXPERT"].map((s) => <option key={s}>{s}</option>)}
                </select>
              </div>
              <div className="flex items-center gap-2 mt-5">
                <input type="checkbox" id="cert_req" checked={form.certification_required} onChange={(e) => setForm((p) => ({ ...p, certification_required: e.target.checked }))} />
                <label htmlFor="cert_req" className="text-sm text-gray-700">Certification Required</label>
              </div>
            </div>
            <div className="flex gap-2 justify-end pt-2">
              <button onClick={() => setShowCreate(false)} className="px-4 py-2 text-sm text-gray-600 border rounded-lg hover:bg-gray-50">Cancel</button>
              <button onClick={() => create.mutate()} disabled={!form.operator_id} className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50">
                {create.isPending ? "Saving…" : "Add Cert"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

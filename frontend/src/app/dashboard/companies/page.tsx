"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  companyApi, Company, Branch, UserAccess, CompanySummary,
  CompanyUserRole, setActiveCompanyId,
} from "@/lib/company";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";

const ROLE_COLOR: Record<CompanyUserRole, "green" | "blue" | "gray"> = {
  ADMIN:  "green",
  USER:   "blue",
  VIEWER: "gray",
};

const BRANCH_TYPE_COLOR: Record<string, string> = {
  FACTORY:   "bg-purple-100 text-purple-700",
  WAREHOUSE: "bg-blue-100 text-blue-700",
  OFFICE:    "bg-green-100 text-green-700",
  RETAIL:    "bg-amber-100 text-amber-700",
};

export default function CompaniesPage() {
  const qc = useQueryClient();
  const [selected, setSelected] = useState<Company | null>(null);
  const [tab, setTab] = useState<"overview" | "branches" | "users">("overview");
  const [showNewCompany, setShowNewCompany] = useState(false);
  const [showNewBranch, setShowNewBranch] = useState(false);

  const { data: companies = [], isLoading } = useQuery({
    queryKey: ["companies"],
    queryFn: () => companyApi.list(),
  });

  const { data: branches = [] } = useQuery({
    queryKey: ["branches", selected?.id],
    queryFn: () => companyApi.listBranches(selected!.id),
    enabled: !!selected && tab === "branches",
  });

  const { data: users = [] } = useQuery({
    queryKey: ["company-users", selected?.id],
    queryFn: () => companyApi.listUsers(selected!.id),
    enabled: !!selected && tab === "users",
  });

  const { data: summary } = useQuery({
    queryKey: ["company-summary", selected?.id],
    queryFn: () => companyApi.getSummary(selected!.id),
    enabled: !!selected && tab === "overview",
  });

  const setDefault = useMutation({
    mutationFn: (id: string) => companyApi.setDefault(id),
    onSuccess: (c) => {
      setActiveCompanyId(c.id);
      qc.invalidateQueries({ queryKey: ["companies"] });
    },
  });

  const revokeAccess = useMutation({
    mutationFn: ({ userId }: { userId: string }) => companyApi.revokeAccess(selected!.id, userId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["company-users"] }),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Companies</h1>
          <p className="text-sm text-gray-500 mt-1">Multi-company structure — manage entities, branches, and user access</p>
        </div>
        <Button onClick={() => setShowNewCompany(true)}>+ New Company</Button>
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* Company list */}
        <div className="bg-white rounded-lg border">
          <div className="px-5 py-3 border-b font-semibold text-gray-800">
            Companies ({companies.length})
          </div>
          {isLoading ? (
            <p className="px-5 py-8 text-center text-gray-400">Loading…</p>
          ) : (
            <div className="divide-y">
              {companies.map((c) => (
                <button
                  key={c.id}
                  className={`w-full text-left px-5 py-3 hover:bg-gray-50 ${selected?.id === c.id ? "bg-indigo-50" : ""}`}
                  onClick={() => { setSelected(c); setTab("overview"); }}
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <p className={`font-medium text-sm ${c.is_default ? "text-indigo-700" : "text-gray-800"}`}>
                        {c.name} {c.is_default && <span className="text-xs bg-indigo-100 text-indigo-600 px-1.5 py-0.5 rounded ml-1">Default</span>}
                      </p>
                      <p className="text-xs text-gray-400 mt-0.5">{c.short_code} · {c.country} · {c.base_currency}</p>
                    </div>
                    <span className={`text-xs px-1.5 py-0.5 rounded ${c.is_active ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                      {c.is_active ? "Active" : "Inactive"}
                    </span>
                  </div>
                  <div className="flex gap-3 mt-1 text-xs text-gray-400">
                    <span>{c.branch_count} branches</span>
                    <span>{c.user_count} users</span>
                  </div>
                </button>
              ))}
              {companies.length === 0 && (
                <p className="px-5 py-8 text-center text-gray-400">No companies — create one to get started</p>
              )}
            </div>
          )}
        </div>

        {/* Detail panel */}
        <div className="col-span-2 bg-white rounded-lg border">
          {!selected ? (
            <p className="px-5 py-12 text-center text-gray-400">Select a company</p>
          ) : (
            <>
              <div className="px-5 py-4 border-b flex items-center justify-between">
                <div>
                  <h2 className="font-semibold text-gray-900 text-lg">{selected.name}</h2>
                  <p className="text-sm text-gray-500">{selected.short_code} · {selected.country} · {selected.base_currency}</p>
                </div>
                {!selected.is_default && (
                  <Button variant="secondary" onClick={() => setDefault.mutate(selected.id)}>
                    Set as Default
                  </Button>
                )}
              </div>

              {/* Tabs */}
              <div className="flex border-b">
                {(["overview", "branches", "users"] as const).map((t) => (
                  <button
                    key={t}
                    className={`px-5 py-2.5 text-sm font-medium capitalize border-b-2 -mb-px ${tab === t ? "border-indigo-600 text-indigo-600" : "border-transparent text-gray-500"}`}
                    onClick={() => setTab(t)}
                  >
                    {t}
                  </button>
                ))}
              </div>

              {/* Overview */}
              {tab === "overview" && (
                <div className="p-5 space-y-5">
                  <div className="grid grid-cols-2 gap-4">
                    {[
                      ["Registration No.", selected.registration_no ?? "—"],
                      ["Tax PIN (KRA)",   selected.tax_pin ?? "—"],
                      ["Phone",           selected.phone ?? "—"],
                      ["Email",           selected.email ?? "—"],
                      ["Website",         selected.website ?? "—"],
                      ["Address",         selected.address ?? "—"],
                    ].map(([label, value]) => (
                      <div key={label}>
                        <p className="text-xs text-gray-400">{label}</p>
                        <p className="text-sm text-gray-700 mt-0.5">{value}</p>
                      </div>
                    ))}
                  </div>

                  {summary && (
                    <div>
                      <p className="text-xs font-semibold text-gray-500 uppercase mb-3">KPI Snapshot</p>
                      <div className="grid grid-cols-3 gap-3">
                        {[
                          { label: "Products", value: summary.product_count },
                          { label: "Warehouses", value: summary.warehouse_count },
                          { label: "Open POs", value: summary.open_po_count },
                          { label: "Open SOs", value: summary.open_so_count },
                          { label: "Branches", value: summary.branch_count },
                          { label: "Users", value: summary.user_count },
                        ].map((k) => (
                          <div key={k.label} className="bg-gray-50 rounded-lg p-3 text-center">
                            <p className="text-xl font-bold text-gray-800">{k.value}</p>
                            <p className="text-xs text-gray-500">{k.label}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Branches */}
              {tab === "branches" && (
                <div className="p-5 space-y-3">
                  <div className="flex justify-end">
                    <Button onClick={() => setShowNewBranch(true)}>+ Add Branch</Button>
                  </div>
                  {branches.length === 0 ? (
                    <p className="text-center text-gray-400 py-8">No branches yet</p>
                  ) : (
                    <div className="space-y-2">
                      {branches.map((b) => (
                        <div key={b.id} className="border rounded-lg p-4 flex items-start justify-between">
                          <div>
                            <div className="flex items-center gap-2">
                              <span className="font-medium text-gray-800">{b.name}</span>
                              <span className="font-mono text-xs text-gray-400">{b.branch_code}</span>
                              {b.branch_type && (
                                <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${BRANCH_TYPE_COLOR[b.branch_type] ?? "bg-gray-100 text-gray-600"}`}>
                                  {b.branch_type}
                                </span>
                              )}
                              {b.is_default && <Badge label="Default" variant="blue" />}
                            </div>
                            <p className="text-xs text-gray-500 mt-1">
                              {[b.city, b.address].filter(Boolean).join(" · ") || "—"}
                            </p>
                          </div>
                          <span className={`text-xs ${b.is_active ? "text-green-600" : "text-gray-400"}`}>
                            {b.is_active ? "Active" : "Inactive"}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Users */}
              {tab === "users" && (
                <div className="p-5">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b bg-gray-50 text-xs text-gray-500 uppercase">
                        <th className="px-3 py-2 text-left">User</th>
                        <th className="px-3 py-2 text-left">Role</th>
                        <th className="px-3 py-2 text-center">Default</th>
                        <th className="px-3 py-2" />
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {users.map((u) => (
                        <tr key={u.id} className="hover:bg-gray-50">
                          <td className="px-3 py-2.5">
                            <p className="font-medium text-gray-800">{u.full_name ?? u.username}</p>
                            <p className="text-xs text-gray-400">{u.username}</p>
                          </td>
                          <td className="px-3 py-2.5">
                            <Badge label={u.role} variant={ROLE_COLOR[u.role]} />
                          </td>
                          <td className="px-3 py-2.5 text-center">
                            {u.is_default ? <span className="text-green-600 text-xs font-medium">✓</span> : "—"}
                          </td>
                          <td className="px-3 py-2.5 text-right">
                            <button
                              className="text-xs text-red-500 hover:underline"
                              onClick={() => revokeAccess.mutate({ userId: u.user_id })}
                            >
                              Revoke
                            </button>
                          </td>
                        </tr>
                      ))}
                      {users.length === 0 && (
                        <tr><td colSpan={4} className="px-3 py-6 text-center text-gray-400">No users assigned</td></tr>
                      )}
                    </tbody>
                  </table>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {showNewCompany && (
        <NewCompanyModal
          onClose={() => setShowNewCompany(false)}
          onSave={(c) => { qc.invalidateQueries({ queryKey: ["companies"] }); setSelected(c); setShowNewCompany(false); }}
        />
      )}

      {showNewBranch && selected && (
        <NewBranchModal
          companyId={selected.id}
          onClose={() => setShowNewBranch(false)}
          onSave={() => { qc.invalidateQueries({ queryKey: ["branches"] }); setShowNewBranch(false); }}
        />
      )}
    </div>
  );
}

function NewCompanyModal({ onClose, onSave }: { onClose: () => void; onSave: (c: Company) => void }) {
  const [form, setForm] = useState({ name: "", short_code: "", country: "Kenya", base_currency: "KES", tax_pin: "", registration_no: "", email: "", phone: "" });
  const [saving, setSaving] = useState(false);
  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  async function save() {
    if (!form.name.trim() || !form.short_code.trim()) return;
    setSaving(true);
    try {
      const c = await companyApi.create({
        name: form.name, short_code: form.short_code.toUpperCase(), country: form.country,
        base_currency: form.base_currency, tax_pin: form.tax_pin || undefined,
        registration_no: form.registration_no || undefined, email: form.email || undefined,
        phone: form.phone || undefined,
      });
      onSave(c);
    } finally { setSaving(false); }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6 space-y-4">
        <h2 className="font-semibold text-lg">New Company</h2>
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Company Name *</label>
              <input className="w-full border rounded px-3 py-2 text-sm" value={form.name} onChange={(e) => set("name", e.target.value)} />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Short Code * (e.g. ACME)</label>
              <input className="w-full border rounded px-3 py-2 text-sm uppercase" value={form.short_code} onChange={(e) => set("short_code", e.target.value.toUpperCase())} placeholder="MAX 20 chars" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Country</label>
              <input className="w-full border rounded px-3 py-2 text-sm" value={form.country} onChange={(e) => set("country", e.target.value)} />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Base Currency</label>
              <input className="w-full border rounded px-3 py-2 text-sm" value={form.base_currency} onChange={(e) => set("base_currency", e.target.value)} />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">KRA PIN</label>
              <input className="w-full border rounded px-3 py-2 text-sm" value={form.tax_pin} onChange={(e) => set("tax_pin", e.target.value)} placeholder="P051234567M" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Reg. No.</label>
              <input className="w-full border rounded px-3 py-2 text-sm" value={form.registration_no} onChange={(e) => set("registration_no", e.target.value)} />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Email</label>
              <input className="w-full border rounded px-3 py-2 text-sm" value={form.email} onChange={(e) => set("email", e.target.value)} />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Phone</label>
              <input className="w-full border rounded px-3 py-2 text-sm" value={form.phone} onChange={(e) => set("phone", e.target.value)} />
            </div>
          </div>
        </div>
        <div className="flex gap-2 justify-end">
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button loading={saving} onClick={save} disabled={!form.name.trim() || !form.short_code.trim()}>Create</Button>
        </div>
      </div>
    </div>
  );
}

function NewBranchModal({ companyId, onClose, onSave }: { companyId: string; onClose: () => void; onSave: () => void }) {
  const [form, setForm] = useState({ name: "", branch_code: "", branch_type: "FACTORY", city: "", address: "", phone: "" });
  const [saving, setSaving] = useState(false);
  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  async function save() {
    if (!form.name.trim() || !form.branch_code.trim()) return;
    setSaving(true);
    try {
      await companyApi.addBranch(companyId, {
        name: form.name, branch_code: form.branch_code.toUpperCase(),
        branch_type: form.branch_type, city: form.city || undefined,
        address: form.address || undefined, phone: form.phone || undefined,
      });
      onSave();
    } finally { setSaving(false); }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-sm p-6 space-y-4">
        <h2 className="font-semibold text-lg">Add Branch</h2>
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Branch Name *</label>
              <input className="w-full border rounded px-3 py-2 text-sm" value={form.name} onChange={(e) => set("name", e.target.value)} />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Code *</label>
              <input className="w-full border rounded px-3 py-2 text-sm uppercase" value={form.branch_code} onChange={(e) => set("branch_code", e.target.value.toUpperCase())} />
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Type</label>
            <select className="w-full border rounded px-3 py-2 text-sm" value={form.branch_type} onChange={(e) => set("branch_type", e.target.value)}>
              {["FACTORY", "WAREHOUSE", "OFFICE", "RETAIL"].map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">City</label>
              <input className="w-full border rounded px-3 py-2 text-sm" value={form.city} onChange={(e) => set("city", e.target.value)} />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Phone</label>
              <input className="w-full border rounded px-3 py-2 text-sm" value={form.phone} onChange={(e) => set("phone", e.target.value)} />
            </div>
          </div>
        </div>
        <div className="flex gap-2 justify-end">
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button loading={saving} onClick={save} disabled={!form.name.trim() || !form.branch_code.trim()}>Save</Button>
        </div>
      </div>
    </div>
  );
}

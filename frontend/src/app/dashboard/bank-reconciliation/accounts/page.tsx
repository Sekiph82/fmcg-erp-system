"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { brApi, BRBankAccount } from "@/lib/bank_reconciliation";

export default function BankAccountsPage() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    bank_name: "", branch_name: "", account_name: "",
    account_number_masked: "", currency: "KES", country: "KE",
    account_type: "CURRENT", reconciliation_enabled: true,
    mobile_money_flag: false, mpesa_till_or_paybill_no: "", notes: "",
  });

  const { data: accounts = [], isLoading } = useQuery<BRBankAccount[]>({
    queryKey: ["br-accounts-all"],
    queryFn: () => brApi.listAccounts(false),
  });

  const create = useMutation({
    mutationFn: () => brApi.createAccount(form as unknown as Partial<BRBankAccount>),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["br-accounts-all"] });
      setShowForm(false);
      setForm({ bank_name: "", branch_name: "", account_name: "", account_number_masked: "", currency: "KES", country: "KE", account_type: "CURRENT", reconciliation_enabled: true, mobile_money_flag: false, mpesa_till_or_paybill_no: "", notes: "" });
    },
  });

  const toggle = useMutation({
    mutationFn: ({ id, active }: { id: string; active: boolean }) => brApi.updateAccount(id, { active }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["br-accounts-all"] }),
  });

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Bank Accounts</h1>
        <button onClick={() => setShowForm(!showForm)}
          className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700">
          {showForm ? "Cancel" : "+ New Account"}
        </button>
      </div>

      {showForm && (
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-5 space-y-4">
          <h2 className="text-sm font-semibold text-blue-800">New Bank Account</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[
              { key: "bank_name", label: "Bank Name *", type: "text" },
              { key: "branch_name", label: "Branch", type: "text" },
              { key: "account_name", label: "Account Name *", type: "text" },
              { key: "account_number_masked", label: "Account No (masked)", type: "text" },
              { key: "currency", label: "Currency", type: "text" },
              { key: "country", label: "Country", type: "text" },
              { key: "mpesa_till_or_paybill_no", label: "M-Pesa Till/Paybill", type: "text" },
              { key: "notes", label: "Notes", type: "text" },
            ].map(({ key, label, type }) => (
              <div key={key}>
                <label className="text-xs text-gray-500 font-medium">{label}</label>
                <input type={type} value={(form as unknown as Record<string, string>)[key]}
                  onChange={(e) => setForm({ ...form, [key]: e.target.value })}
                  className="mt-1 w-full border rounded-lg px-3 py-2 text-sm" />
              </div>
            ))}
            <div>
              <label className="text-xs text-gray-500 font-medium">Account Type</label>
              <select value={form.account_type} onChange={(e) => setForm({ ...form, account_type: e.target.value })}
                className="mt-1 w-full border rounded-lg px-3 py-2 text-sm">
                {["CURRENT", "SAVINGS", "MOBILE_MONEY", "OVERDRAFT"].map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </div>
            <div className="flex items-center gap-4 pt-4">
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input type="checkbox" checked={form.reconciliation_enabled}
                  onChange={(e) => setForm({ ...form, reconciliation_enabled: e.target.checked })}
                  className="rounded" />
                Reconciliation Enabled
              </label>
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input type="checkbox" checked={form.mobile_money_flag}
                  onChange={(e) => setForm({ ...form, mobile_money_flag: e.target.checked })}
                  className="rounded" />
                Mobile Money
              </label>
            </div>
          </div>
          <button onClick={() => create.mutate()}
            disabled={create.isPending || !form.bank_name || !form.account_name}
            className="px-5 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50">
            {create.isPending ? "Creating…" : "Create Account"}
          </button>
        </div>
      )}

      {isLoading ? (
        <p className="text-gray-400">Loading…</p>
      ) : (
        <div className="bg-white border rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
              <tr>
                {["Account Name", "Bank", "Type", "Currency", "M-Pesa", "Recon", "Active", ""].map((h) => (
                  <th key={h} className="px-4 py-2 text-left font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y">
              {accounts.map((a: BRBankAccount) => (
                <tr key={a.id} className={`hover:bg-gray-50 ${!a.active ? "opacity-50" : ""}`}>
                  <td className="px-4 py-2 font-medium">
                    {a.account_name}
                    {a.account_number_masked && <span className="ml-2 text-gray-400 text-xs">···{a.account_number_masked}</span>}
                  </td>
                  <td className="px-4 py-2 text-gray-600">{a.bank_name}{a.branch_name ? ` / ${a.branch_name}` : ""}</td>
                  <td className="px-4 py-2 text-xs">{a.account_type}</td>
                  <td className="px-4 py-2 text-xs">{a.currency}</td>
                  <td className="px-4 py-2 text-xs">{a.mpesa_till_or_paybill_no || "—"}</td>
                  <td className="px-4 py-2">
                    <span className={`px-2 py-0.5 rounded-full text-xs ${a.reconciliation_enabled ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                      {a.reconciliation_enabled ? "Yes" : "No"}
                    </span>
                  </td>
                  <td className="px-4 py-2">
                    <span className={`px-2 py-0.5 rounded-full text-xs ${a.active ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                      {a.active ? "Active" : "Inactive"}
                    </span>
                  </td>
                  <td className="px-4 py-2">
                    <button onClick={() => toggle.mutate({ id: a.id, active: !a.active })}
                      className="text-xs text-gray-500 hover:text-gray-800 underline">
                      {a.active ? "Deactivate" : "Activate"}
                    </button>
                  </td>
                </tr>
              ))}
              {accounts.length === 0 && (
                <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-400 text-sm">No bank accounts configured.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

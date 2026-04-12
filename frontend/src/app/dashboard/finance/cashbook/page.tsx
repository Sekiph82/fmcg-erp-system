"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { financeApi, CashAccount, CashTransaction, CashAccountType } from "@/lib/finance";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";

type Tab = "accounts" | "transactions" | "journal";

const acctTypeBadge = (t: CashAccountType) =>
  t === "MPESA" ? "blue" : t === "BANK" ? "green" : "gray";

const txStatusBadge = (s: string) =>
  s === "CLEARED" ? "green" : s === "FAILED" ? "red" : s === "REVERSED" ? "gray" : "yellow";

export default function CashbookPage() {
  const qc = useQueryClient();
  const [tab, setTab] = useState<Tab>("accounts");
  const [selectedAccount, setSelectedAccount] = useState<CashAccount | null>(null);
  const [showNewAccount, setShowNewAccount] = useState(false);
  const [showNewTx, setShowNewTx] = useState(false);

  const { data: accounts = [] } = useQuery({
    queryKey: ["finance-cash-accounts"],
    queryFn: () => financeApi.listCashAccounts(false),
  });

  const { data: transactions = [], isLoading: txLoading } = useQuery({
    queryKey: ["finance-transactions", selectedAccount?.id],
    queryFn: () => (selectedAccount ? financeApi.listTransactions(selectedAccount.id) : Promise.resolve([])),
    enabled: !!selectedAccount,
  });

  const { data: journals = [] } = useQuery({
    queryKey: ["finance-journals"],
    queryFn: () => financeApi.listJournal(),
    enabled: tab === "journal",
  });

  const createAccount = useMutation({
    mutationFn: (data: object) => financeApi.createCashAccount(data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["finance-cash-accounts"] }); setShowNewAccount(false); },
  });

  const addTx = useMutation({
    mutationFn: ({ accountId, data }: { accountId: string; data: object }) =>
      financeApi.addTransaction(accountId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["finance-transactions"] });
      qc.invalidateQueries({ queryKey: ["finance-cash-position"] });
      setShowNewTx(false);
    },
  });

  const clearTx = useMutation({
    mutationFn: (txId: string) => financeApi.clearTransaction(txId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["finance-transactions"] });
      qc.invalidateQueries({ queryKey: ["finance-cash-accounts"] });
      qc.invalidateQueries({ queryKey: ["finance-cash-position"] });
    },
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Cashbook</h1>
          <p className="text-sm text-gray-500 mt-1">Cash, bank and M-Pesa account management</p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => { setTab("accounts"); setShowNewAccount(true); }}>New Account</Button>
          {selectedAccount && <Button onClick={() => setShowNewTx(true)}>Add Transaction</Button>}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b">
        {(["accounts", "transactions", "journal"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium capitalize transition-colors border-b-2 -mb-px ${
              tab === t ? "border-indigo-600 text-indigo-700" : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {t === "transactions" && selectedAccount ? `Transactions — ${selectedAccount.name}` : t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      {/* Accounts tab */}
      {tab === "accounts" && (
        <div className="bg-white rounded-lg border">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-xs text-gray-500 uppercase">
                <th className="px-5 py-2 text-left">Name</th>
                <th className="px-5 py-2 text-left">Type</th>
                <th className="px-5 py-2 text-left">Bank / Number</th>
                <th className="px-5 py-2 text-right">Opening</th>
                <th className="px-5 py-2 text-right">Current Balance</th>
                <th className="px-5 py-2 text-left">Status</th>
                <th className="px-5 py-2" />
              </tr>
            </thead>
            <tbody className="divide-y">
              {accounts.map((acc) => (
                <tr key={acc.id} className="hover:bg-gray-50">
                  <td className="px-5 py-3 font-medium text-gray-900">{acc.name}</td>
                  <td className="px-5 py-3"><Badge label={acc.account_type} variant={acctTypeBadge(acc.account_type)} /></td>
                  <td className="px-5 py-3 text-gray-500">{[acc.bank_name, acc.account_number].filter(Boolean).join(" · ") || "—"}</td>
                  <td className="px-5 py-3 text-right">{Number(acc.opening_balance).toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
                  <td className="px-5 py-3 text-right font-semibold">{Number(acc.current_balance).toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
                  <td className="px-5 py-3"><Badge label={acc.is_active ? "Active" : "Inactive"} variant={acc.is_active ? "green" : "gray"} /></td>
                  <td className="px-5 py-3">
                    <button
                      className="text-xs text-indigo-600 hover:underline"
                      onClick={() => { setSelectedAccount(acc); setTab("transactions"); }}
                    >
                      Transactions
                    </button>
                  </td>
                </tr>
              ))}
              {accounts.length === 0 && (
                <tr><td colSpan={7} className="px-5 py-8 text-center text-gray-400">No accounts yet</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Transactions tab */}
      {tab === "transactions" && (
        <div className="bg-white rounded-lg border">
          {txLoading ? (
            <p className="px-5 py-8 text-center text-gray-400">Loading…</p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-gray-50 text-xs text-gray-500 uppercase">
                  <th className="px-5 py-2 text-left">Date</th>
                  <th className="px-5 py-2 text-left">Description</th>
                  <th className="px-5 py-2 text-left">Direction</th>
                  <th className="px-5 py-2 text-right">Amount</th>
                  <th className="px-5 py-2 text-left">Status</th>
                  <th className="px-5 py-2 text-left">Reference</th>
                  <th className="px-5 py-2" />
                </tr>
              </thead>
              <tbody className="divide-y">
                {transactions.map((tx) => (
                  <tr key={tx.id} className="hover:bg-gray-50">
                    <td className="px-5 py-3">{tx.transaction_date}</td>
                    <td className="px-5 py-3 text-gray-700">{tx.description}</td>
                    <td className="px-5 py-3">
                      <Badge label={tx.direction} variant={tx.direction === "RECEIPT" ? "green" : "red"} />
                    </td>
                    <td className="px-5 py-3 text-right font-semibold">{Number(tx.amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
                    <td className="px-5 py-3"><Badge label={tx.status} variant={txStatusBadge(tx.status)} /></td>
                    <td className="px-5 py-3 text-gray-500">{tx.reference || "—"}</td>
                    <td className="px-5 py-3">
                      {tx.status === "PENDING" && (
                        <button
                          className="text-xs text-indigo-600 hover:underline"
                          onClick={() => clearTx.mutate(tx.id)}
                        >
                          Clear
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
                {transactions.length === 0 && (
                  <tr><td colSpan={7} className="px-5 py-8 text-center text-gray-400">No transactions</td></tr>
                )}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* Journal tab */}
      {tab === "journal" && (
        <div className="bg-white rounded-lg border">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-xs text-gray-500 uppercase">
                <th className="px-5 py-2 text-left">Entry No</th>
                <th className="px-5 py-2 text-left">Date</th>
                <th className="px-5 py-2 text-left">Description</th>
                <th className="px-5 py-2 text-left">Module</th>
                <th className="px-5 py-2 text-right">Debit</th>
                <th className="px-5 py-2 text-right">Credit</th>
                <th className="px-5 py-2 text-left">Posted</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {journals.map((je) => (
                <tr key={je.id} className="hover:bg-gray-50">
                  <td className="px-5 py-3 font-mono text-xs">{je.entry_no}</td>
                  <td className="px-5 py-3">{je.entry_date}</td>
                  <td className="px-5 py-3 text-gray-700">{je.description}</td>
                  <td className="px-5 py-3 text-gray-500">{je.source_module || "—"}</td>
                  <td className="px-5 py-3 text-right">{je.total_debit != null ? Number(je.total_debit).toLocaleString(undefined, { minimumFractionDigits: 2 }) : "—"}</td>
                  <td className="px-5 py-3 text-right">{je.total_credit != null ? Number(je.total_credit).toLocaleString(undefined, { minimumFractionDigits: 2 }) : "—"}</td>
                  <td className="px-5 py-3"><Badge label={je.is_posted ? "Posted" : "Draft"} variant={je.is_posted ? "green" : "yellow"} /></td>
                </tr>
              ))}
              {journals.length === 0 && (
                <tr><td colSpan={7} className="px-5 py-8 text-center text-gray-400">No journal entries</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* New Account modal */}
      {showNewAccount && (
        <NewAccountModal
          onClose={() => setShowNewAccount(false)}
          onSubmit={(data) => createAccount.mutate(data)}
          loading={createAccount.isPending}
        />
      )}

      {/* New Transaction modal */}
      {showNewTx && selectedAccount && (
        <NewTransactionModal
          account={selectedAccount}
          onClose={() => setShowNewTx(false)}
          onSubmit={(data) => addTx.mutate({ accountId: selectedAccount.id, data })}
          loading={addTx.isPending}
        />
      )}
    </div>
  );
}

function NewAccountModal({ onClose, onSubmit, loading }: { onClose: () => void; onSubmit: (d: object) => void; loading: boolean }) {
  const [form, setForm] = useState({ name: "", account_type: "BANK", account_number: "", bank_name: "", currency: "KES", opening_balance: "0", notes: "" });
  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6 space-y-4">
        <h2 className="font-semibold text-lg">New Cash Account</h2>
        <div className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Name</label>
            <input className="w-full border rounded px-3 py-2 text-sm" value={form.name} onChange={(e) => set("name", e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Type</label>
            <select className="w-full border rounded px-3 py-2 text-sm" value={form.account_type} onChange={(e) => set("account_type", e.target.value)}>
              <option value="CASH">Cash</option>
              <option value="BANK">Bank</option>
              <option value="MPESA">M-Pesa</option>
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Bank Name</label>
              <input className="w-full border rounded px-3 py-2 text-sm" value={form.bank_name} onChange={(e) => set("bank_name", e.target.value)} />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Account No.</label>
              <input className="w-full border rounded px-3 py-2 text-sm" value={form.account_number} onChange={(e) => set("account_number", e.target.value)} />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Currency</label>
              <input className="w-full border rounded px-3 py-2 text-sm" value={form.currency} onChange={(e) => set("currency", e.target.value)} />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Opening Balance</label>
              <input className="w-full border rounded px-3 py-2 text-sm" type="number" value={form.opening_balance} onChange={(e) => set("opening_balance", e.target.value)} />
            </div>
          </div>
        </div>
        <div className="flex gap-2 justify-end pt-2">
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button loading={loading} onClick={() => onSubmit({ ...form, opening_balance: parseFloat(form.opening_balance) || 0 })}>Create</Button>
        </div>
      </div>
    </div>
  );
}

function NewTransactionModal({ account, onClose, onSubmit, loading }: { account: CashAccount; onClose: () => void; onSubmit: (d: object) => void; loading: boolean }) {
  const today = new Date().toISOString().slice(0, 10);
  const [form, setForm] = useState({ transaction_date: today, direction: "RECEIPT", amount: "", description: "", reference: "", status: "CLEARED", mpesa_phone: "", mpesa_receipt: "" });
  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));
  const isMpesa = account.account_type === "MPESA";

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6 space-y-4">
        <h2 className="font-semibold text-lg">Add Transaction — {account.name}</h2>
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Date</label>
              <input className="w-full border rounded px-3 py-2 text-sm" type="date" value={form.transaction_date} onChange={(e) => set("transaction_date", e.target.value)} />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Direction</label>
              <select className="w-full border rounded px-3 py-2 text-sm" value={form.direction} onChange={(e) => set("direction", e.target.value)}>
                <option value="RECEIPT">Receipt (in)</option>
                <option value="PAYMENT">Payment (out)</option>
              </select>
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Amount (KES)</label>
            <input className="w-full border rounded px-3 py-2 text-sm" type="number" value={form.amount} onChange={(e) => set("amount", e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Description</label>
            <input className="w-full border rounded px-3 py-2 text-sm" value={form.description} onChange={(e) => set("description", e.target.value)} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Reference</label>
              <input className="w-full border rounded px-3 py-2 text-sm" value={form.reference} onChange={(e) => set("reference", e.target.value)} />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Status</label>
              <select className="w-full border rounded px-3 py-2 text-sm" value={form.status} onChange={(e) => set("status", e.target.value)}>
                <option value="CLEARED">Cleared</option>
                <option value="PENDING">Pending</option>
              </select>
            </div>
          </div>
          {isMpesa && (
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">M-Pesa Phone</label>
                <input className="w-full border rounded px-3 py-2 text-sm" value={form.mpesa_phone} onChange={(e) => set("mpesa_phone", e.target.value)} />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">M-Pesa Receipt</label>
                <input className="w-full border rounded px-3 py-2 text-sm" value={form.mpesa_receipt} onChange={(e) => set("mpesa_receipt", e.target.value)} />
              </div>
            </div>
          )}
        </div>
        <div className="flex gap-2 justify-end pt-2">
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button loading={loading} onClick={() => onSubmit({ ...form, amount: parseFloat(form.amount) || 0 })}>Add</Button>
        </div>
      </div>
    </div>
  );
}

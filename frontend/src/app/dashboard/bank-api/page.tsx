"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  BANK_CLASSIFICATIONS,
  BankConnection,
  BankTransaction,
  BankTxnClassification,
  bankApi,
  classificationLabel,
  fmtMoney,
} from "@/lib/bank_api";
import { Button } from "@/components/ui/Button";

function KpiCard({ label, value, tone }: { label: string; value: string | number; tone?: string }) {
  return (
    <div className="bg-white rounded-xl border p-4">
      <p className="text-xs text-gray-500 uppercase tracking-wide">{label}</p>
      <p className={`text-2xl font-bold mt-1 ${tone ?? "text-gray-900"}`}>{value}</p>
    </div>
  );
}

function fmtDate(v: string | null) {
  if (!v) return "-";
  return new Date(v).toLocaleString("en-KE", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function DirectionBadge({ direction }: { direction: BankTransaction["direction"] }) {
  const cls = direction === "CREDIT" ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700";
  return <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${cls}`}>{direction}</span>;
}

function CreateConnectionPanel() {
  const qc = useQueryClient();
  const [form, setForm] = useState({
    bank_name: "KCB Bank Kenya",
    account_name: "FMCG Operations Account",
    account_number: "",
    bank_code: "KCB",
    currency: "KES",
    api_type: "MOCK" as const,
    credentials_ref: "",
  });

  const mut = useMutation({
    mutationFn: () =>
      bankApi.createConnection({
        ...form,
        bank_code: form.bank_code || undefined,
        credentials_ref: form.credentials_ref || undefined,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["bank-api-connections"] });
      qc.invalidateQueries({ queryKey: ["bank-api-dashboard"] });
      setForm((prev) => ({ ...prev, account_number: "", credentials_ref: "" }));
    },
  });

  return (
    <div className="bg-white rounded-xl border p-4 flex flex-col gap-3">
      <div>
        <h2 className="text-sm font-semibold text-gray-800">New Bank Connection</h2>
        <p className="text-xs text-gray-500 mt-0.5">Use MOCK for demo sync; DIRECT is reserved for bank adapters.</p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <label className="flex flex-col gap-1 text-xs font-medium text-gray-600">
          Bank Name
          <input className="border rounded-lg px-3 py-2 text-sm font-normal" value={form.bank_name} onChange={(e) => setForm({ ...form, bank_name: e.target.value })} />
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium text-gray-600">
          Account Name
          <input className="border rounded-lg px-3 py-2 text-sm font-normal" value={form.account_name} onChange={(e) => setForm({ ...form, account_name: e.target.value })} />
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium text-gray-600">
          Account Number
          <input className="border rounded-lg px-3 py-2 text-sm font-normal" placeholder="e.g. 0123456789" value={form.account_number} onChange={(e) => setForm({ ...form, account_number: e.target.value })} />
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium text-gray-600">
          Bank Code
          <input className="border rounded-lg px-3 py-2 text-sm font-normal" value={form.bank_code} onChange={(e) => setForm({ ...form, bank_code: e.target.value })} />
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium text-gray-600">
          Currency
          <select className="border rounded-lg px-3 py-2 text-sm font-normal bg-white" value={form.currency} onChange={(e) => setForm({ ...form, currency: e.target.value })}>
            {["KES", "USD", "EUR", "GBP"].map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium text-gray-600">
          API Type
          <select className="border rounded-lg px-3 py-2 text-sm font-normal bg-white" value={form.api_type} onChange={(e) => setForm({ ...form, api_type: e.target.value as "MOCK" })}>
            <option value="MOCK">MOCK</option>
            <option value="DIRECT">DIRECT</option>
          </select>
        </label>
      </div>
      <div className="flex items-center justify-between gap-3">
        <input
          className="border rounded-lg px-3 py-2 text-sm flex-1"
          placeholder="Credentials ref or vault key (optional)"
          value={form.credentials_ref}
          onChange={(e) => setForm({ ...form, credentials_ref: e.target.value })}
        />
        <Button loading={mut.isPending} disabled={!form.bank_name || !form.account_name || !form.account_number} onClick={() => mut.mutate()}>
          Add Connection
        </Button>
      </div>
      {mut.isError && <p className="text-sm text-red-600">{String((mut.error as Error).message)}</p>}
    </div>
  );
}

function ConnectionsPanel({ connections }: { connections: BankConnection[] }) {
  const qc = useQueryClient();
  const syncMut = useMutation({
    mutationFn: (id: string) => bankApi.syncConnection(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["bank-api-dashboard"] });
      qc.invalidateQueries({ queryKey: ["bank-api-connections"] });
      qc.invalidateQueries({ queryKey: ["bank-api-transactions"] });
    },
  });

  return (
    <div className="bg-white rounded-xl border overflow-hidden">
      <div className="px-4 py-3 border-b flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-800">Connections</h2>
        <span className="text-xs text-gray-400">{connections.length} configured</span>
      </div>
      <div className="divide-y">
        {connections.map((c) => (
          <div key={c.id} className="p-4 flex flex-col md:flex-row md:items-center justify-between gap-3">
            <div>
              <div className="flex items-center gap-2">
                <p className="text-sm font-semibold text-gray-900">{c.account_name}</p>
                <span className="px-2 py-0.5 rounded-full bg-blue-100 text-blue-700 text-xs font-medium">{c.api_type}</span>
                <span className="px-2 py-0.5 rounded-full bg-green-100 text-green-700 text-xs font-medium">{c.status}</span>
              </div>
              <p className="text-xs text-gray-500 mt-1">{c.bank_name} | {c.account_number} | {c.currency}</p>
              <p className="text-xs text-gray-400 mt-0.5">Last sync: {fmtDate(c.last_synced_at)}</p>
            </div>
            <Button loading={syncMut.isPending} onClick={() => syncMut.mutate(c.id)}>Sync Now</Button>
          </div>
        ))}
        {connections.length === 0 && <div className="p-8 text-center text-sm text-gray-400">No bank connections configured.</div>}
      </div>
      {syncMut.isError && <p className="p-4 text-sm text-red-600">{String((syncMut.error as Error).message)}</p>}
    </div>
  );
}

function TransactionsTable({ transactions, selectedConnection }: { transactions: BankTransaction[]; selectedConnection?: BankConnection }) {
  const qc = useQueryClient();
  const classifyMut = useMutation({
    mutationFn: ({ id, classification }: { id: string; classification: BankTxnClassification }) =>
      bankApi.classifyTransaction(id, classification),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["bank-api-transactions"] }),
  });
  const reconcileMut = useMutation({
    mutationFn: (id: string) => bankApi.reconcileTransaction(id, "manual_bank_api_review"),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["bank-api-dashboard"] });
      qc.invalidateQueries({ queryKey: ["bank-api-transactions"] });
    },
  });

  return (
    <div className="bg-white rounded-xl border overflow-hidden">
      <div className="px-4 py-3 border-b flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-800">Synced Transactions</h2>
        <span className="text-xs text-gray-400">{transactions.length} rows</span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs uppercase tracking-wide text-gray-500">
            <tr>
              <th className="px-4 py-3 text-left">Date</th>
              <th className="px-4 py-3 text-left">Description</th>
              <th className="px-4 py-3 text-left">Direction</th>
              <th className="px-4 py-3 text-right">Amount</th>
              <th className="px-4 py-3 text-right">Balance</th>
              <th className="px-4 py-3 text-left">Classification</th>
              <th className="px-4 py-3 text-left">Reference</th>
              <th className="px-4 py-3 text-left">Status</th>
              <th className="px-4 py-3 text-left">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {transactions.map((t) => (
              <tr key={t.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 text-gray-600">{t.txn_date}</td>
                <td className="px-4 py-3 min-w-[240px]">
                  <p className="font-medium text-gray-800">{t.description}</p>
                  <p className="text-xs text-gray-400">Value date: {t.value_date ?? "-"}</p>
                </td>
                <td className="px-4 py-3"><DirectionBadge direction={t.direction} /></td>
                <td className="px-4 py-3 text-right font-semibold">{fmtMoney(t.amount, selectedConnection?.currency ?? "KES")}</td>
                <td className="px-4 py-3 text-right text-gray-600">{t.balance_after === null ? "-" : fmtMoney(t.balance_after, selectedConnection?.currency ?? "KES")}</td>
                <td className="px-4 py-3">
                  <select
                    className="border rounded-lg px-2 py-1 text-xs bg-white"
                    value={t.classification}
                    onChange={(e) => classifyMut.mutate({ id: t.id, classification: e.target.value as BankTxnClassification })}
                  >
                    {BANK_CLASSIFICATIONS.map((c) => <option key={c} value={c}>{classificationLabel(c)}</option>)}
                  </select>
                </td>
                <td className="px-4 py-3 font-mono text-xs text-blue-700">{t.reference}</td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${t.is_reconciled ? "bg-green-100 text-green-700" : "bg-yellow-100 text-yellow-700"}`}>
                    {t.is_reconciled ? "RECONCILED" : "OPEN"}
                  </span>
                </td>
                <td className="px-4 py-3">
                  {!t.is_reconciled && (
                    <button
                      className="text-xs text-blue-600 hover:underline"
                      onClick={() => reconcileMut.mutate(t.id)}
                    >
                      Mark reconciled
                    </button>
                  )}
                </td>
              </tr>
            ))}
            {transactions.length === 0 && (
              <tr>
                <td colSpan={9} className="px-4 py-10 text-center text-gray-400">No synced transactions yet.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default function BankApiPage() {
  const [connectionFilter, setConnectionFilter] = useState("");
  const [reconciledFilter, setReconciledFilter] = useState<"open" | "all" | "reconciled">("open");

  const { data: dashboard } = useQuery({ queryKey: ["bank-api-dashboard"], queryFn: bankApi.dashboard });
  const { data: connections = [], isLoading: loadingConnections } = useQuery({ queryKey: ["bank-api-connections"], queryFn: bankApi.listConnections });
  const selectedConnection = useMemo(
    () => connections.find((c) => c.id === connectionFilter),
    [connections, connectionFilter],
  );

  const txParams = {
    connection_id: connectionFilter || undefined,
    reconciled: reconciledFilter === "all" ? undefined : reconciledFilter === "reconciled",
    limit: 200,
  };
  const { data: transactions = [], isLoading: loadingTransactions } = useQuery({
    queryKey: ["bank-api-transactions", txParams],
    queryFn: () => bankApi.listTransactions(txParams),
  });

  return (
    <div className="p-6 flex flex-col gap-6 min-h-screen bg-gray-50">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Open Banking</h1>
        <p className="text-sm text-gray-500 mt-0.5">Bank API connections, mock sync, classification, and reconciliation staging</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <KpiCard label="Connections" value={dashboard?.total_connections ?? 0} tone="text-blue-700" />
        <KpiCard label="Active" value={dashboard?.active_connections ?? 0} tone="text-green-700" />
        <KpiCard label="Bank Balance" value={fmtMoney(dashboard?.total_balance ?? 0)} tone="text-gray-900" />
        <KpiCard label="Unreconciled" value={dashboard?.unreconciled_count ?? 0} tone="text-yellow-700" />
        <KpiCard label="Open Amount" value={fmtMoney(dashboard?.unreconciled_amount ?? 0)} tone="text-red-700" />
      </div>

      <CreateConnectionPanel />

      {loadingConnections ? (
        <div className="p-8 text-sm text-gray-400">Loading connections...</div>
      ) : (
        <ConnectionsPanel connections={connections} />
      )}

      <div className="flex flex-wrap items-center gap-3">
        <select
          className="border rounded-lg px-3 py-2 text-sm bg-white"
          value={connectionFilter}
          onChange={(e) => setConnectionFilter(e.target.value)}
        >
          <option value="">All connections</option>
          {connections.map((c) => (
            <option key={c.id} value={c.id}>{c.account_name} - {c.bank_name}</option>
          ))}
        </select>
        <select
          className="border rounded-lg px-3 py-2 text-sm bg-white"
          value={reconciledFilter}
          onChange={(e) => setReconciledFilter(e.target.value as "open" | "all" | "reconciled")}
        >
          <option value="open">Open only</option>
          <option value="reconciled">Reconciled only</option>
          <option value="all">All transactions</option>
        </select>
        {dashboard?.last_sync_at && <span className="text-xs text-gray-400">Last sync: {fmtDate(dashboard.last_sync_at)}</span>}
      </div>

      {loadingTransactions ? (
        <div className="p-8 text-sm text-gray-400">Loading transactions...</div>
      ) : (
        <TransactionsTable transactions={transactions} selectedConnection={selectedConnection} />
      )}
    </div>
  );
}

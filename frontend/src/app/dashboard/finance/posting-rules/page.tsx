"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { tx, lx } from "@/lib/i18n/core";

interface Acc { id: string; code: string; name: string }
interface RuleRow {
  module: string; event: string; name: string; purpose: string; rule_id: string | null;
  status: "missing" | "proposed" | "active" | "inactive"; debit: Acc | null; credit: Acc | null; tax: Acc | null; clearing: Acc | null;
}
interface Catalog { mandatory: boolean; rules: RuleRow[]; accounts: (Acc & { type: string })[] }

const BASE = "/api/v1/finance/accounting/posting-rules";
const SIDES: { key: "debit" | "credit" | "tax" | "clearing"; label: string }[] = lx(() => [
  { key: "debit", label: tx("Debit") }, { key: "credit", label: tx("Credit") }, { key: "tax", label: tx("Tax") }, { key: "clearing", label: tx("Cash/bank") },
]);
const STATUS: Record<RuleRow["status"], string> = {
  missing: "bg-red-100 text-red-700", inactive: "bg-gray-100 text-gray-600", proposed: "bg-amber-100 text-amber-800", active: "bg-green-100 text-green-700",
};

export default function PostingRulesPage() {
  const qc = useQueryClient();
  const { hasPermission } = useAuth();
  const canEdit = hasPermission("finance.configure");
  const canApprove = hasPermission("finance.approve");
  const { data } = useQuery<Catalog>({ queryKey: ["posting-rules-catalog"], queryFn: async () => (await apiClient.get(`${BASE}/catalog`)).data });
  const set = (d: Catalog) => qc.setQueryData(["posting-rules-catalog"], d);
  const propose = useMutation({ mutationFn: async () => (await apiClient.post(`${BASE}/propose`)).data, onSuccess: set });
  const edit = useMutation({
    mutationFn: async (v: { id: string; side: string; account: string }) =>
      (await apiClient.patch(`${BASE}/${v.id}/accounts`, { [v.side]: v.account || null })).data,
    onSuccess: set,
  });
  const approve = useMutation({ mutationFn: async () => (await apiClient.post(`${BASE}/approve`)).data, onSuccess: set });
  if (!data) return <div className="p-6 text-sm text-gray-500">{tx("Loading…")}</div>;
  const missing = data.rules.filter((r) => r.status === "missing").length;
  const proposed = data.rules.filter((r) => r.status === "proposed").length;
  const err = (propose.error || edit.error || approve.error) as { response?: { data?: { detail?: unknown } } } | null;

  return (
    <div className="p-4 md:p-6 space-y-4">
      <div>
        <h2 className="text-lg font-semibold">{tx("Accounting posting rules")}</h2>
        <p className="text-sm text-gray-500 max-w-3xl">
          {tx("Which accounts each business event is booked to. The system proposed a complete set from the chart of accounts; change any account, then approve. After approval the rules are mandatory: an event without a rule is refused instead of being saved without a ledger entry.")}
        </p>
        <p className={`mt-2 text-sm font-medium ${data.mandatory ? "text-green-700" : "text-amber-700"}`}>
          {data.mandatory ? tx("Rules are mandatory (approved by finance).") : tx("Not approved yet: events without a rule are saved without a ledger entry.")}
        </p>
      </div>
      <div className="flex flex-wrap gap-2">
        {canEdit && missing > 0 && (
          <button type="button" onClick={() => propose.mutate()} disabled={propose.isPending}
            className="px-3 py-2 text-sm border rounded-lg disabled:opacity-50">{tx("Propose the missing")} {missing} {tx("rules")}</button>
        )}
        {canApprove && proposed > 0 && (
          <button type="button" disabled={approve.isPending}
            onClick={() => { if (confirm(tx("Approve {proposed} proposed rules? From now on events without a rule are refused.", { proposed }))) approve.mutate(); }}
            className="px-3 py-2 text-sm bg-green-600 text-white rounded-lg disabled:opacity-50">{tx("Approve the rule set (")}{proposed})</button>
        )}
      </div>
      {typeof err?.response?.data?.detail === "string" && <p className="text-sm text-red-600">{err.response.data.detail}</p>}
      <div className="border rounded-lg bg-white overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead className="bg-gray-50 text-xs text-gray-500"><tr>
            <th className="px-3 py-2 text-left">{tx("Event")}</th><th className="px-3 py-2 text-left">{tx("Status")}</th>
            {SIDES.map((s) => <th key={s.key} className="px-3 py-2 text-left">{s.label}</th>)}
          </tr></thead>
          <tbody>{data.rules.map((r) => (
            <tr key={`${r.module}/${r.event}`} className="border-t align-top">
              <td className="px-3 py-2 min-w-[220px]"><div className="font-medium">{r.name}</div><div className="text-xs text-gray-500">{r.purpose}</div></td>
              <td className="px-3 py-2"><span className={`text-xs px-2 py-0.5 rounded ${STATUS[r.status]}`}>{r.status}</span></td>
              {SIDES.map((s) => (
                <td key={s.key} className="px-3 py-2 min-w-[170px]">
                  {r.rule_id && canEdit ? (
                    <select aria-label={`${r.name} ${s.label}`} className="w-full border rounded px-2 py-1 text-xs" value={r[s.key]?.id ?? ""}
                      onChange={(e) => edit.mutate({ id: r.rule_id as string, side: s.key, account: e.target.value })}>
                      <option value="">—</option>
                      {data.accounts.map((a) => <option key={a.id} value={a.id}>{a.code} {a.name}</option>)}
                    </select>
                  ) : <span className="text-xs">{r[s.key] ? `${r[s.key]?.code} ${r[s.key]?.name}` : "—"}</span>}
                </td>
              ))}
            </tr>))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

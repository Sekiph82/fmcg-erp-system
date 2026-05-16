"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  aiApi,
  NLCommandHistoryItem,
  NLCommandResult,
  NLRiskLevel,
  parseAIError,
} from "@/lib/aiApi";
import { useState } from "react";
import { RequirePermission } from "@/components/PermissionGuard";

const RISK_PILL: Record<NLRiskLevel, string> = {
  LOW: "bg-green-100 text-green-700 border-green-200",
  MEDIUM: "bg-amber-100 text-amber-700 border-amber-200",
  HIGH: "bg-red-100 text-red-700 border-red-200",
};

const STATUS_PILL: Record<string, string> = {
  PENDING_CONFIRMATION: "bg-amber-100 text-amber-700 border-amber-200",
  CONFIRMED: "bg-blue-100 text-blue-700 border-blue-200",
  EXECUTED: "bg-green-100 text-green-700 border-green-200",
  REJECTED: "bg-gray-100 text-gray-600 border-gray-200",
  FAILED: "bg-red-100 text-red-700 border-red-200",
};

const EXAMPLES = [
  "Approve all POs under 50,000 KES",
  "Run MRP for next 30 days",
  "Send dunning emails to overdue customers",
  "Trigger reorder for low stock items",
  "Initiate recall for batch LOT-2026-05",
  "Generate monthly sales report",
  "Run payroll for April 2026",
];

function label(value?: string | null) {
  return value ? value.replace(/_/g, " ") : "-";
}

function formatDate(value: string) {
  if (!value) return "-";
  return new Date(value).toLocaleString("en-GB", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function KpiCard({ label, value, sub, color }: { label: string; value: string | number; sub?: string; color?: string }) {
  return (
    <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
      <p className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-1">{label}</p>
      <p className={`text-xl font-bold ${color ?? "text-gray-900"}`}>{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
    </div>
  );
}

export default function NLCommandPage() {
  const qc = useQueryClient();
  const [command, setCommand] = useState("");
  const [confirmedBy, setConfirmedBy] = useState("");
  const [parsed, setParsed] = useState<NLCommandResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const historyQuery = useQuery<NLCommandHistoryItem[]>({
    queryKey: ["ai-nl-command-history"],
    queryFn: () => aiApi.listNLCommandHistory(40),
    refetchInterval: 20_000,
  });
  const statusQuery = useQuery({
    queryKey: ["ai-status"],
    queryFn: () => aiApi.status(),
  });

  const submit = useMutation({
    mutationFn: () => aiApi.submitNLCommand(command.trim()),
    onSuccess: (result) => {
      setParsed(result);
      setConfirmedBy("");
      setError(null);
      qc.invalidateQueries({ queryKey: ["ai-nl-command-history"] });
    },
    onError: (err) => setError(parseAIError(err).message),
  });

  const execute = useMutation({
    mutationFn: () => {
      if (!parsed) throw new Error("No command selected");
      return aiApi.executeNLCommand(parsed.id, confirmedBy.trim());
    },
    onSuccess: (result) => {
      setParsed((prev) => prev ? { ...prev, status: result.status } : prev);
      setError(null);
      qc.invalidateQueries({ queryKey: ["ai-nl-command-history"] });
    },
    onError: (err) => setError(parseAIError(err).message),
  });

  const reject = useMutation({
    mutationFn: () => {
      if (!parsed) throw new Error("No command selected");
      return aiApi.rejectNLCommand(parsed.id);
    },
    onSuccess: (result) => {
      setParsed((prev) => prev ? { ...prev, status: result.status } : prev);
      setError(null);
      qc.invalidateQueries({ queryKey: ["ai-nl-command-history"] });
    },
    onError: (err) => setError(parseAIError(err).message),
  });

  const history = historyQuery.data ?? [];
  const highRisk = history.filter((item) => item.risk_level === "HIGH").length;
  const pending = history.filter((item) => item.status === "PENDING_CONFIRMATION").length;
  const executionEnabled = statusQuery.data?.nl_command_execution_enabled === true;

  return (
    <RequirePermission permission="ai.view">
    <div className="p-6 space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Natural Language ERP Control</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Parse plain-English ERP actions, review risk, and record human confirmation before execution.
          </p>
        </div>
        <button
          onClick={() => historyQuery.refetch()}
          disabled={historyQuery.isFetching}
          className="px-3 py-2 text-sm border border-gray-200 rounded-lg text-gray-600 hover:bg-gray-50 disabled:opacity-50"
        >
          Refresh
        </button>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <KpiCard label="Commands" value={history.length} sub="latest history window" color="text-indigo-600" />
        <KpiCard label="Pending" value={pending} sub="awaiting action" color={pending ? "text-amber-600" : "text-gray-900"} />
        <KpiCard label="High Risk" value={highRisk} sub="confirmation required" color={highRisk ? "text-red-600" : "text-gray-900"} />
        <KpiCard label="Executed" value={history.filter((item) => item.status === "EXECUTED").length} sub="stub execution log" color="text-green-600" />
      </div>

      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5 space-y-4">
        <div>
          <label className="block text-sm font-semibold text-gray-700 mb-2">Command</label>
          <div className="flex flex-col sm:flex-row gap-2">
            <input
              value={command}
              onChange={(event) => setCommand(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && command.trim() && !submit.isPending) submit.mutate();
              }}
              className="flex-1 border border-gray-300 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder="e.g. Trigger reorder for low stock items"
            />
            <button
              onClick={() => submit.mutate()}
              disabled={!command.trim() || submit.isPending}
              className="px-4 py-2.5 text-sm font-medium bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50"
            >
              {submit.isPending ? "Parsing..." : "Parse Command"}
            </button>
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          {EXAMPLES.map((example) => (
            <button
              key={example}
              onClick={() => setCommand(example)}
              className="text-xs px-3 py-1 rounded-full border border-indigo-200 bg-indigo-50 text-indigo-700 hover:bg-indigo-100"
            >
              {example}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {parsed && (
        <div className={`bg-white rounded-xl border shadow-sm p-5 space-y-4 ${RISK_PILL[parsed.risk_level]}`}>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-widest">Parsed Intent</p>
              <h2 className="text-xl font-bold text-gray-900 mt-1">{label(parsed.parsed_intent)}</h2>
            </div>
            <div className="flex flex-wrap gap-2">
              <span className={`text-xs px-3 py-1 rounded-full border font-semibold ${RISK_PILL[parsed.risk_level]}`}>
                {parsed.risk_level} risk
              </span>
              <span className={`text-xs px-3 py-1 rounded-full border font-semibold ${STATUS_PILL[parsed.status] ?? "bg-gray-100 text-gray-600 border-gray-200"}`}>
                {label(parsed.status)}
              </span>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <div className="lg:col-span-2">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-widest mb-1">Action Plan</p>
              <p className="text-sm text-gray-800">{parsed.parsed_action}</p>
            </div>
            <div>
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-widest mb-1">Target Endpoint</p>
              <code className="text-xs text-gray-700 bg-gray-50 border border-gray-100 rounded px-2 py-1 block">
                {parsed.target_endpoint ?? "No executable endpoint"}
              </code>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <div>
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-widest mb-1">Parameters Needed</p>
              <p className="text-sm text-gray-700">{parsed.params_needed ?? "No additional parameters identified"}</p>
            </div>
            <div>
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-widest mb-1">Confirmation</p>
              <p className="text-sm text-gray-700">{parsed.requires_confirmation ? "Human confirmation required" : "Low-risk manual execution allowed"}</p>
            </div>
            <div>
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-widest mb-1">Mode</p>
              <p className="text-sm text-gray-700">
                {executionEnabled ? "Execution requires approval and idempotency." : "Dry-run only. Execution is disabled by configuration."}
              </p>
            </div>
          </div>

          {parsed.status === "PENDING_CONFIRMATION" && (
            <div className="rounded-lg border border-gray-200 bg-white p-4">
              <p className="text-sm font-semibold text-gray-800 mb-3">
                Confirm or reject this parsed command
              </p>
              <div className="flex flex-col sm:flex-row gap-2">
                <input
                  value={confirmedBy}
                  onChange={(event) => setConfirmedBy(event.target.value)}
                  className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  placeholder="Approver name for audit trail"
                />
                <button
                  onClick={() => execute.mutate()}
                  disabled={!executionEnabled || !confirmedBy.trim() || execute.isPending}
                  className="px-4 py-2 text-sm font-medium bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
                >
                  {executionEnabled ? (execute.isPending ? "Executing..." : "Confirm & Execute") : "Execution Disabled"}
                </button>
                <button
                  onClick={() => reject.mutate()}
                  disabled={reject.isPending}
                  className="px-4 py-2 text-sm font-medium border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 disabled:opacity-50"
                >
                  Reject
                </button>
              </div>
            </div>
          )}

          {parsed.status !== "PENDING_CONFIRMATION" && (
            <div className="rounded-lg bg-gray-50 border border-gray-100 p-3 text-sm text-gray-700">
              Current status: {label(parsed.status)}
            </div>
          )}

          <p className="text-xs text-gray-500">{parsed.note}</p>
        </div>
      )}

      <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-50 flex items-center justify-between">
          <h2 className="font-semibold text-gray-800">Command History</h2>
          {historyQuery.isFetching && <span className="text-xs text-gray-400">Refreshing...</span>}
        </div>
        {historyQuery.isLoading ? (
          <p className="p-8 text-center text-gray-400">Loading command history...</p>
        ) : history.length === 0 ? (
          <p className="p-8 text-center text-gray-400">No command history yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-100">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Command</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Intent</th>
                  <th className="px-4 py-3 text-center text-xs font-semibold text-gray-500 uppercase">Risk</th>
                  <th className="px-4 py-3 text-center text-xs font-semibold text-gray-500 uppercase">Status</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Confirmed By</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Time</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {history.map((item) => (
                  <tr key={item.id} className="hover:bg-gray-50 align-top">
                    <td className="px-4 py-3 max-w-sm">
                      <p className="font-medium text-gray-800 truncate">{item.command_text}</p>
                      {item.result_summary && <p className="text-xs text-gray-400 truncate mt-1">{item.result_summary}</p>}
                    </td>
                    <td className="px-4 py-3 text-gray-600">{label(item.parsed_intent)}</td>
                    <td className="px-4 py-3 text-center">
                      <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${RISK_PILL[item.risk_level]}`}>
                        {item.risk_level}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${STATUS_PILL[item.status] ?? "bg-gray-100 text-gray-600 border-gray-200"}`}>
                        {label(item.status)}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-500">{item.confirmed_by ?? "-"}</td>
                    <td className="px-4 py-3 text-gray-500 whitespace-nowrap">{formatDate(item.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
    </RequirePermission>
  );
}

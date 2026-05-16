"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  aiApi,
  AIAgentPolicy,
  AIAgentRun,
  AIAgentRunStatus,
  AIGovernanceDashboard,
  parseAIError,
} from "@/lib/aiApi";
import { useMemo, useState } from "react";
import { RequirePermission } from "@/components/PermissionGuard";

const RUN_STATUS: AIAgentRunStatus[] = ["COMPLETED", "FAILED", "BLOCKED", "FLAGGED", "STARTED"];

const STATUS_PILL: Record<string, string> = {
  STARTED: "bg-blue-100 text-blue-700 border-blue-200",
  COMPLETED: "bg-green-100 text-green-700 border-green-200",
  FAILED: "bg-red-100 text-red-700 border-red-200",
  BLOCKED: "bg-amber-100 text-amber-700 border-amber-200",
  FLAGGED: "bg-orange-100 text-orange-700 border-orange-200",
};

const EMPTY_POLICY = {
  agent_name: "",
  description: "",
  allowed_actions: "",
  forbidden_actions: "",
  allowed_modules: "",
  max_cost_per_run_tokens: "",
  max_runs_per_hour: "",
  requires_human_approval: true,
  hallucination_guardrail: true,
  rag_enabled: false,
  notes: "",
};

const EMPTY_RUN = {
  agent_name: "",
  trigger: "user_request",
  triggered_by: "",
  actions_taken: "",
  tokens_used: "",
  cost_usd: "",
  status: "COMPLETED" as AIAgentRunStatus,
  result_summary: "",
  anomaly_flag: false,
  anomaly_reason: "",
};

function splitList(value: string) {
  const items = value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
  return items.length ? items : undefined;
}

function numberOrUndefined(value: string) {
  if (!value.trim()) return undefined;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : undefined;
}

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

function ListText({ items }: { items: string[] | null }) {
  if (!items || items.length === 0) return <span className="text-gray-400">None configured</span>;
  return (
    <div className="flex flex-wrap gap-1">
      {items.map((item) => (
        <span key={item} className="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-700">
          {item}
        </span>
      ))}
    </div>
  );
}

export default function AIGovernancePage() {
  const qc = useQueryClient();
  const [policyForm, setPolicyForm] = useState(EMPTY_POLICY);
  const [runForm, setRunForm] = useState(EMPTY_RUN);
  const [activeOnly, setActiveOnly] = useState(false);
  const [flaggedOnly, setFlaggedOnly] = useState(false);
  const [agentFilter, setAgentFilter] = useState("");
  const [error, setError] = useState<string | null>(null);

  const dashboardQuery = useQuery<AIGovernanceDashboard>({
    queryKey: ["ai-governance-dashboard"],
    queryFn: () => aiApi.governanceDashboard(),
    refetchInterval: 20_000,
  });

  const policiesQuery = useQuery<AIAgentPolicy[]>({
    queryKey: ["ai-agent-policies", activeOnly],
    queryFn: () => aiApi.listAgentPolicies(activeOnly),
  });

  const runsQuery = useQuery<AIAgentRun[]>({
    queryKey: ["ai-agent-runs", agentFilter, flaggedOnly],
    queryFn: () => aiApi.listAgentRuns({
      agent_name: agentFilter || undefined,
      flagged_only: flaggedOnly,
      limit: 75,
    }),
    refetchInterval: 20_000,
  });

  const agentNames = useMemo(() => {
    const set = new Set<string>();
    (policiesQuery.data ?? []).forEach((policy) => set.add(policy.agent_name));
    (runsQuery.data ?? []).forEach((run) => set.add(run.agent_name));
    return Array.from(set).sort();
  }, [policiesQuery.data, runsQuery.data]);

  const createPolicy = useMutation({
    mutationFn: () => aiApi.createAgentPolicy({
      agent_name: policyForm.agent_name.trim(),
      description: policyForm.description.trim() || undefined,
      allowed_actions: splitList(policyForm.allowed_actions),
      forbidden_actions: splitList(policyForm.forbidden_actions),
      allowed_modules: splitList(policyForm.allowed_modules),
      max_cost_per_run_tokens: numberOrUndefined(policyForm.max_cost_per_run_tokens),
      max_runs_per_hour: numberOrUndefined(policyForm.max_runs_per_hour),
      requires_human_approval: policyForm.requires_human_approval,
      hallucination_guardrail: policyForm.hallucination_guardrail,
      rag_enabled: policyForm.rag_enabled,
      notes: policyForm.notes.trim() || undefined,
    }),
    onSuccess: () => {
      setPolicyForm(EMPTY_POLICY);
      setError(null);
      qc.invalidateQueries({ queryKey: ["ai-agent-policies"] });
      qc.invalidateQueries({ queryKey: ["ai-governance-dashboard"] });
    },
    onError: (err) => setError(parseAIError(err).message),
  });

  const togglePolicy = useMutation({
    mutationFn: (id: string) => aiApi.toggleAgentPolicy(id),
    onSuccess: () => {
      setError(null);
      qc.invalidateQueries({ queryKey: ["ai-agent-policies"] });
      qc.invalidateQueries({ queryKey: ["ai-governance-dashboard"] });
    },
    onError: (err) => setError(parseAIError(err).message),
  });

  const logRun = useMutation({
    mutationFn: () => aiApi.logAgentRun({
      agent_name: runForm.agent_name.trim(),
      trigger: runForm.trigger.trim() || undefined,
      triggered_by: runForm.triggered_by.trim() || undefined,
      actions_taken: splitList(runForm.actions_taken),
      tokens_used: numberOrUndefined(runForm.tokens_used),
      cost_usd: numberOrUndefined(runForm.cost_usd),
      status: runForm.status,
      result_summary: runForm.result_summary.trim() || undefined,
      anomaly_flag: runForm.anomaly_flag,
      anomaly_reason: runForm.anomaly_reason.trim() || undefined,
    }),
    onSuccess: () => {
      setRunForm(EMPTY_RUN);
      setError(null);
      qc.invalidateQueries({ queryKey: ["ai-agent-runs"] });
      qc.invalidateQueries({ queryKey: ["ai-governance-dashboard"] });
    },
    onError: (err) => setError(parseAIError(err).message),
  });

  const dash = dashboardQuery.data;
  const policies = policiesQuery.data ?? [];
  const runs = runsQuery.data ?? [];
  const statusCounts = dash?.runs_by_status ?? {};

  return (
    <RequirePermission permission="ai.view">
    <div className="p-6 space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">AI Agent Governance</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Control agent permissions, human approval rules, guardrails, run logs, and cost visibility.
          </p>
        </div>
        <button
          onClick={() => {
            dashboardQuery.refetch();
            policiesQuery.refetch();
            runsQuery.refetch();
          }}
          disabled={dashboardQuery.isFetching || policiesQuery.isFetching || runsQuery.isFetching}
          className="px-3 py-2 text-sm border border-gray-200 rounded-lg text-gray-600 hover:bg-gray-50 disabled:opacity-50"
        >
          Refresh
        </button>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <KpiCard label="Active Policies" value={dash?.active_policies ?? 0} sub="governed agents" color="text-indigo-600" />
        <KpiCard label="Agent Runs" value={dash?.total_runs ?? 0} sub="audit log entries" color="text-gray-900" />
        <KpiCard label="Flagged Runs" value={dash?.flagged_runs ?? 0} sub="anomaly review" color={(dash?.flagged_runs ?? 0) > 0 ? "text-red-600" : "text-gray-900"} />
        <KpiCard label="Tokens" value={(dash?.total_tokens_consumed ?? 0).toLocaleString()} sub="tracked usage" color="text-teal-600" />
      </div>

      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
        <p className="text-sm font-semibold text-gray-800 mb-3">Run Status Mix</p>
        <div className="flex flex-wrap gap-2">
          {RUN_STATUS.map((status) => (
            <span key={status} className={`text-xs px-3 py-1 rounded-full border font-medium ${STATUS_PILL[status]}`}>
              {label(status)}: {statusCounts[status] ?? 0}
            </span>
          ))}
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <form
          onSubmit={(event) => {
            event.preventDefault();
            if (policyForm.agent_name.trim()) createPolicy.mutate();
          }}
          className="bg-white rounded-xl border border-gray-100 shadow-sm p-5 space-y-4"
        >
          <div>
            <h2 className="font-semibold text-gray-800">Policy Registry</h2>
            <p className="text-xs text-gray-500 mt-0.5">Define tool access, module scope, approval rules, and guardrails.</p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-gray-500 mb-1">Agent Name</label>
              <input
                value={policyForm.agent_name}
                onChange={(event) => setPolicyForm((prev) => ({ ...prev, agent_name: event.target.value }))}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                placeholder="inventory_reorder_agent"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-500 mb-1">Allowed Modules</label>
              <input
                value={policyForm.allowed_modules}
                onChange={(event) => setPolicyForm((prev) => ({ ...prev, allowed_modules: event.target.value }))}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                placeholder="inventory, procurement"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-500 mb-1">Description</label>
            <textarea
              value={policyForm.description}
              onChange={(event) => setPolicyForm((prev) => ({ ...prev, description: event.target.value }))}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
              rows={2}
              placeholder="Operational purpose and owner"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-gray-500 mb-1">Allowed Actions</label>
              <input
                value={policyForm.allowed_actions}
                onChange={(event) => setPolicyForm((prev) => ({ ...prev, allowed_actions: event.target.value }))}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                placeholder="READ_STOCK, CREATE_REQUISITION"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-500 mb-1">Forbidden Actions</label>
              <input
                value={policyForm.forbidden_actions}
                onChange={(event) => setPolicyForm((prev) => ({ ...prev, forbidden_actions: event.target.value }))}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                placeholder="DELETE_ORDER, POST_GL"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-gray-500 mb-1">Token Budget / Run</label>
              <input
                value={policyForm.max_cost_per_run_tokens}
                onChange={(event) => setPolicyForm((prev) => ({ ...prev, max_cost_per_run_tokens: event.target.value }))}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                placeholder="5000"
                inputMode="numeric"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-500 mb-1">Max Runs / Hour</label>
              <input
                value={policyForm.max_runs_per_hour}
                onChange={(event) => setPolicyForm((prev) => ({ ...prev, max_runs_per_hour: event.target.value }))}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                placeholder="10"
                inputMode="numeric"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {[
              ["requires_human_approval", "Human Approval"],
              ["hallucination_guardrail", "Guardrail"],
              ["rag_enabled", "RAG Enabled"],
            ].map(([key, text]) => (
              <label key={key} className="flex items-center gap-2 text-sm text-gray-700 border border-gray-200 rounded-lg px-3 py-2">
                <input
                  type="checkbox"
                  checked={Boolean(policyForm[key as keyof typeof policyForm])}
                  onChange={(event) => setPolicyForm((prev) => ({ ...prev, [key]: event.target.checked }))}
                />
                {text}
              </label>
            ))}
          </div>

          <button
            type="submit"
            disabled={!policyForm.agent_name.trim() || createPolicy.isPending}
            className="px-4 py-2 text-sm font-medium bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50"
          >
            {createPolicy.isPending ? "Saving..." : "Create Policy"}
          </button>
        </form>

        <form
          onSubmit={(event) => {
            event.preventDefault();
            if (runForm.agent_name.trim()) logRun.mutate();
          }}
          className="bg-white rounded-xl border border-gray-100 shadow-sm p-5 space-y-4"
        >
          <div>
            <h2 className="font-semibold text-gray-800">Run Audit Logger</h2>
            <p className="text-xs text-gray-500 mt-0.5">Record agent executions for testing, exception review, and cost tracking.</p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-gray-500 mb-1">Agent Name</label>
              <input
                value={runForm.agent_name}
                onChange={(event) => setRunForm((prev) => ({ ...prev, agent_name: event.target.value }))}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                list="agent-names"
                placeholder="inventory_reorder_agent"
              />
              <datalist id="agent-names">
                {agentNames.map((name) => <option key={name} value={name} />)}
              </datalist>
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-500 mb-1">Status</label>
              <select
                value={runForm.status}
                onChange={(event) => setRunForm((prev) => ({ ...prev, status: event.target.value as AIAgentRunStatus }))}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
              >
                {RUN_STATUS.map((status) => <option key={status} value={status}>{label(status)}</option>)}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-gray-500 mb-1">Trigger</label>
              <input
                value={runForm.trigger}
                onChange={(event) => setRunForm((prev) => ({ ...prev, trigger: event.target.value }))}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                placeholder="user_request"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-500 mb-1">Triggered By</label>
              <input
                value={runForm.triggered_by}
                onChange={(event) => setRunForm((prev) => ({ ...prev, triggered_by: event.target.value }))}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                placeholder="planner@factory"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-500 mb-1">Actions Taken</label>
            <input
              value={runForm.actions_taken}
              onChange={(event) => setRunForm((prev) => ({ ...prev, actions_taken: event.target.value }))}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
              placeholder="READ_STOCK, CREATE_REQUISITION"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-gray-500 mb-1">Tokens Used</label>
              <input
                value={runForm.tokens_used}
                onChange={(event) => setRunForm((prev) => ({ ...prev, tokens_used: event.target.value }))}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                inputMode="numeric"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-500 mb-1">Cost USD</label>
              <input
                value={runForm.cost_usd}
                onChange={(event) => setRunForm((prev) => ({ ...prev, cost_usd: event.target.value }))}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                inputMode="decimal"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-500 mb-1">Result Summary</label>
            <textarea
              value={runForm.result_summary}
              onChange={(event) => setRunForm((prev) => ({ ...prev, result_summary: event.target.value }))}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
              rows={2}
              placeholder="Outcome, blocked action, or exception summary"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <label className="flex items-center gap-2 text-sm text-gray-700 border border-gray-200 rounded-lg px-3 py-2">
              <input
                type="checkbox"
                checked={runForm.anomaly_flag}
                onChange={(event) => setRunForm((prev) => ({ ...prev, anomaly_flag: event.target.checked }))}
              />
              Flag anomaly
            </label>
            <input
              value={runForm.anomaly_reason}
              onChange={(event) => setRunForm((prev) => ({ ...prev, anomaly_reason: event.target.value }))}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
              placeholder="Reason if flagged"
            />
          </div>

          <button
            type="submit"
            disabled={!runForm.agent_name.trim() || logRun.isPending}
            className="px-4 py-2 text-sm font-medium bg-teal-600 text-white rounded-lg hover:bg-teal-700 disabled:opacity-50"
          >
            {logRun.isPending ? "Logging..." : "Log Run"}
          </button>
        </form>
      </div>

      <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-50 flex flex-wrap items-center justify-between gap-3">
          <h2 className="font-semibold text-gray-800">Agent Policies</h2>
          <label className="flex items-center gap-2 text-sm text-gray-600">
            <input type="checkbox" checked={activeOnly} onChange={(event) => setActiveOnly(event.target.checked)} />
            Active only
          </label>
        </div>
        {policiesQuery.isLoading ? (
          <p className="p-8 text-center text-gray-400">Loading policies...</p>
        ) : policies.length === 0 ? (
          <p className="p-8 text-center text-gray-400">No agent policies configured.</p>
        ) : (
          <div className="divide-y divide-gray-50">
            {policies.map((policy) => (
              <div key={policy.id} className="p-5 grid grid-cols-1 lg:grid-cols-4 gap-4">
                <div>
                  <div className="flex items-center gap-2">
                    <p className="font-semibold text-gray-900">{policy.agent_name}</p>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${policy.is_active ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                      {policy.is_active ? "Active" : "Inactive"}
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">{policy.description ?? "No description provided"}</p>
                  <button
                    onClick={() => togglePolicy.mutate(policy.id)}
                    disabled={togglePolicy.isPending}
                    className="mt-3 text-xs px-3 py-1 border border-gray-200 rounded-lg text-gray-600 hover:bg-gray-50 disabled:opacity-50"
                  >
                    {policy.is_active ? "Deactivate" : "Activate"}
                  </button>
                </div>
                <div>
                  <p className="text-xs font-semibold text-gray-500 uppercase mb-2">Allowed</p>
                  <ListText items={policy.allowed_actions} />
                </div>
                <div>
                  <p className="text-xs font-semibold text-gray-500 uppercase mb-2">Forbidden</p>
                  <ListText items={policy.forbidden_actions} />
                </div>
                <div className="text-sm text-gray-600 space-y-1">
                  <p>Approval: {policy.requires_human_approval ? "Required" : "Not required"}</p>
                  <p>Guardrail: {policy.hallucination_guardrail ? "On" : "Off"}</p>
                  <p>RAG: {policy.rag_enabled ? "Enabled" : "Disabled"}</p>
                  <p>Budget: {policy.max_cost_per_run_tokens?.toLocaleString() ?? "-"} tokens</p>
                  <p>Rate: {policy.max_runs_per_hour ?? "-"} runs/hour</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-50 flex flex-wrap items-center justify-between gap-3">
          <h2 className="font-semibold text-gray-800">Agent Run Audit Log</h2>
          <div className="flex flex-wrap items-center gap-2">
            <select
              value={agentFilter}
              onChange={(event) => setAgentFilter(event.target.value)}
              className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
            >
              <option value="">All agents</option>
              {agentNames.map((name) => <option key={name} value={name}>{name}</option>)}
            </select>
            <label className="flex items-center gap-2 text-sm text-gray-600">
              <input type="checkbox" checked={flaggedOnly} onChange={(event) => setFlaggedOnly(event.target.checked)} />
              Flagged only
            </label>
          </div>
        </div>
        {runsQuery.isLoading ? (
          <p className="p-8 text-center text-gray-400">Loading run log...</p>
        ) : runs.length === 0 ? (
          <p className="p-8 text-center text-gray-400">No agent runs found.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-100">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Agent</th>
                  <th className="px-4 py-3 text-center text-xs font-semibold text-gray-500 uppercase">Status</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Trigger</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Tokens</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Cost</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Result</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Started</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {runs.map((run) => (
                  <tr key={run.id} className="hover:bg-gray-50 align-top">
                    <td className="px-4 py-3">
                      <p className="font-medium text-gray-800">{run.agent_name}</p>
                      {run.anomaly_flag && <p className="text-xs text-red-600 mt-1">{run.anomaly_reason ?? "Flagged for review"}</p>}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${STATUS_PILL[run.status] ?? "bg-gray-100 text-gray-600 border-gray-200"}`}>
                        {label(run.status)}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-600">
                      <p>{run.trigger ?? "-"}</p>
                      <p className="text-xs text-gray-400">{run.triggered_by ?? ""}</p>
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-xs text-gray-600">{run.tokens_used?.toLocaleString() ?? "-"}</td>
                    <td className="px-4 py-3 text-right font-mono text-xs text-gray-600">{run.cost_usd != null ? `$${run.cost_usd.toFixed(4)}` : "-"}</td>
                    <td className="px-4 py-3 max-w-md text-gray-600">{run.result_summary ?? "-"}</td>
                    <td className="px-4 py-3 text-gray-500 whitespace-nowrap">{formatDate(run.started_at)}</td>
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

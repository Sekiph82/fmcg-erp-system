"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  maintenanceApi,
  MaintenancePrediction,
  MaintenancePredictionRisk,
  MaintenancePredictionStatus,
} from "@/lib/maintenance";
import { useMemo, useState } from "react";

const RISK_PILL: Record<MaintenancePredictionRisk, string> = {
  LOW: "bg-green-100 text-green-700 border-green-200",
  MEDIUM: "bg-amber-100 text-amber-700 border-amber-200",
  HIGH: "bg-orange-100 text-orange-700 border-orange-200",
  CRITICAL: "bg-red-100 text-red-700 border-red-200",
};

const STATUS_PILL: Record<MaintenancePredictionStatus, string> = {
  OPEN: "bg-blue-100 text-blue-700 border-blue-200",
  REVIEWED: "bg-indigo-100 text-indigo-700 border-indigo-200",
  WORK_ORDER_CREATED: "bg-green-100 text-green-700 border-green-200",
  DISMISSED: "bg-gray-100 text-gray-600 border-gray-200",
};

const STATUS_OPTIONS: Array<MaintenancePredictionStatus | ""> = ["", "OPEN", "REVIEWED", "WORK_ORDER_CREATED", "DISMISSED"];
const RISK_OPTIONS: Array<MaintenancePredictionRisk | ""> = ["", "LOW", "MEDIUM", "HIGH", "CRITICAL"];

function label(value?: string | null) {
  return value ? value.replace(/_/g, " ") : "-";
}

function formatDate(value?: string | null) {
  if (!value) return "-";
  return new Date(value).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
}

function daysUntil(value: string) {
  const target = new Date(value).getTime();
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return Math.ceil((target - today.getTime()) / 86_400_000);
}

function KpiCard({ label, value, sub, color }: { label: string; value: string | number; sub?: string; color?: string }) {
  return (
    <div className="bg-white rounded-lg border p-5">
      <p className="text-xs text-gray-500 uppercase tracking-wide">{label}</p>
      <p className={`text-2xl font-bold mt-1 ${color ?? "text-gray-900"}`}>{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
    </div>
  );
}

export default function PredictiveMaintenancePage() {
  const qc = useQueryClient();
  const [statusFilter, setStatusFilter] = useState<MaintenancePredictionStatus | "">("OPEN");
  const [riskFilter, setRiskFilter] = useState<MaintenancePredictionRisk | "">("");
  const [horizonDays, setHorizonDays] = useState(30);
  const [reviewer, setReviewer] = useState("maintenance_planner");
  const [reviewNotes, setReviewNotes] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);

  const predictionsQuery = useQuery<MaintenancePrediction[]>({
    queryKey: ["maintenance-predictions", statusFilter, riskFilter],
    queryFn: () => maintenanceApi.listPredictions({
      status: statusFilter || undefined,
      risk_level: riskFilter || undefined,
      limit: 150,
    }),
  });

  const generate = useMutation({
    mutationFn: () => maintenanceApi.generatePredictions(horizonDays),
    onSuccess: () => {
      setError(null);
      qc.invalidateQueries({ queryKey: ["maintenance-predictions"] });
    },
    onError: (err) => setError(err instanceof Error ? err.message : "Failed to generate predictions"),
  });

  const review = useMutation({
    mutationFn: ({ id, status }: { id: string; status: MaintenancePredictionStatus }) =>
      maintenanceApi.reviewPrediction(id, {
        status,
        reviewed_by: reviewer.trim() || "maintenance_planner",
        review_notes: reviewNotes[id] || undefined,
      }),
    onSuccess: () => {
      setError(null);
      qc.invalidateQueries({ queryKey: ["maintenance-predictions"] });
    },
    onError: (err) => setError(err instanceof Error ? err.message : "Failed to review prediction"),
  });

  const predictions = predictionsQuery.data ?? [];
  const summary = useMemo(() => {
    const open = predictions.filter((p) => p.status === "OPEN").length;
    const critical = predictions.filter((p) => p.risk_level === "CRITICAL" || p.risk_level === "HIGH").length;
    const dueSoon = predictions.filter((p) => daysUntil(p.predicted_failure_date) <= 14).length;
    const avgConfidence = predictions.length
      ? predictions.reduce((sum, p) => sum + p.confidence, 0) / predictions.length
      : 0;
    return { open, critical, dueSoon, avgConfidence };
  }, [predictions]);

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Predictive Maintenance</h1>
          <p className="text-sm text-gray-500 mt-1">
            Rule-based failure predictions from IoT sensor trends, machine states, alerts, and breakdown history.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={horizonDays}
            onChange={(event) => setHorizonDays(Number(event.target.value))}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm bg-white"
          >
            {[14, 30, 60, 90].map((days) => <option key={days} value={days}>{days} days</option>)}
          </select>
          <button
            onClick={() => generate.mutate()}
            disabled={generate.isPending}
            className="px-4 py-2 text-sm font-medium bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50"
          >
            {generate.isPending ? "Analyzing..." : "Generate Predictions"}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard label="Predictions" value={predictions.length} sub="current filter" color="text-indigo-600" />
        <KpiCard label="Open" value={summary.open} sub="awaiting review" color={summary.open ? "text-blue-600" : "text-gray-700"} />
        <KpiCard label="High Risk" value={summary.critical} sub="high or critical" color={summary.critical ? "text-red-600" : "text-gray-700"} />
        <KpiCard label="Avg Confidence" value={`${(summary.avgConfidence * 100).toFixed(0)}%`} sub={`${summary.dueSoon} due within 14 days`} color="text-teal-600" />
      </div>

      <div className="bg-white rounded-lg border p-4 flex flex-wrap items-end gap-3">
        <div>
          <label className="block text-xs font-semibold text-gray-500 mb-1">Status</label>
          <select
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value as MaintenancePredictionStatus | "")}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm bg-white"
          >
            {STATUS_OPTIONS.map((status) => <option key={status || "ALL"} value={status}>{status ? label(status) : "All statuses"}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-xs font-semibold text-gray-500 mb-1">Risk</label>
          <select
            value={riskFilter}
            onChange={(event) => setRiskFilter(event.target.value as MaintenancePredictionRisk | "")}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm bg-white"
          >
            {RISK_OPTIONS.map((risk) => <option key={risk || "ALL"} value={risk}>{risk || "All risks"}</option>)}
          </select>
        </div>
        <div className="min-w-56">
          <label className="block text-xs font-semibold text-gray-500 mb-1">Reviewer</label>
          <input
            value={reviewer}
            onChange={(event) => setReviewer(event.target.value)}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
            placeholder="maintenance_planner"
          />
        </div>
        <button
          onClick={() => predictionsQuery.refetch()}
          disabled={predictionsQuery.isFetching}
          className="px-3 py-2 text-sm border border-gray-200 rounded-lg text-gray-600 hover:bg-gray-50 disabled:opacity-50"
        >
          Refresh
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="bg-white rounded-lg border overflow-hidden">
        <div className="px-5 py-3 border-b flex items-center justify-between">
          <h2 className="font-semibold text-gray-800">Prediction Queue</h2>
          {predictionsQuery.isFetching && <span className="text-xs text-gray-400">Refreshing...</span>}
        </div>
        {predictionsQuery.isLoading ? (
          <p className="px-5 py-8 text-center text-gray-400">Loading predictions...</p>
        ) : predictions.length === 0 ? (
          <p className="px-5 py-8 text-center text-gray-400">
            No predictions found. Run generation after IoT readings, machine state events, alerts, or breakdown history are available.
          </p>
        ) : (
          <div className="divide-y">
            {predictions.map((prediction) => {
              const dueDays = daysUntil(prediction.predicted_failure_date);
              const metrics = prediction.source_metrics?.metric_scores as Record<string, { trend_pct?: number; latest_avg?: number; readings?: number }> | undefined;
              return (
                <div key={prediction.id} className="p-5 space-y-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <h3 className="font-semibold text-gray-900">
                          {prediction.asset_name ?? prediction.machine_name ?? prediction.machine_id}
                        </h3>
                        <span className="text-xs text-gray-400">{prediction.asset_no ?? prediction.machine_id}</span>
                        <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${RISK_PILL[prediction.risk_level]}`}>
                          {prediction.risk_level}
                        </span>
                        <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${STATUS_PILL[prediction.status]}`}>
                          {label(prediction.status)}
                        </span>
                      </div>
                      <p className="text-sm text-gray-600 mt-1">{prediction.failure_mode}</p>
                    </div>
                    <div className="text-right">
                      <p className={`text-xl font-bold ${dueDays <= 7 ? "text-red-600" : dueDays <= 14 ? "text-orange-600" : "text-gray-900"}`}>
                        {dueDays >= 0 ? `${dueDays}d` : "Overdue"}
                      </p>
                      <p className="text-xs text-gray-400">Predicted {formatDate(prediction.predicted_failure_date)}</p>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                    <div className="lg:col-span-2">
                      <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Recommended Action</p>
                      <p className="text-sm text-gray-800">{prediction.recommended_action}</p>
                      <p className="text-xs text-gray-500 mt-2">{prediction.evidence_summary}</p>
                    </div>
                    <div>
                      <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Confidence</p>
                      <div className="h-2 bg-gray-100 rounded overflow-hidden">
                        <div className="h-full bg-indigo-500" style={{ width: `${Math.round(prediction.confidence * 100)}%` }} />
                      </div>
                      <p className="text-xs text-gray-500 mt-1">{(prediction.confidence * 100).toFixed(0)}%</p>
                    </div>
                  </div>

                  {metrics && Object.keys(metrics).length > 0 && (
                    <div className="flex flex-wrap gap-2">
                      {Object.entries(metrics).map(([metric, data]) => (
                        <span key={metric} className="text-xs px-2 py-1 rounded-full bg-gray-100 text-gray-700">
                          {metric}: {data.trend_pct?.toFixed(1)}% trend, {data.readings ?? 0} readings
                        </span>
                      ))}
                    </div>
                  )}

                  {prediction.status === "OPEN" && (
                    <div className="flex flex-col lg:flex-row gap-2">
                      <input
                        value={reviewNotes[prediction.id] ?? ""}
                        onChange={(event) => setReviewNotes((prev) => ({ ...prev, [prediction.id]: event.target.value }))}
                        className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm"
                        placeholder="Review note"
                      />
                      <button
                        onClick={() => review.mutate({ id: prediction.id, status: "REVIEWED" })}
                        disabled={review.isPending}
                        className="px-3 py-2 text-sm font-medium border border-indigo-200 text-indigo-700 rounded-lg hover:bg-indigo-50 disabled:opacity-50"
                      >
                        Mark Reviewed
                      </button>
                      <button
                        onClick={() => review.mutate({ id: prediction.id, status: "WORK_ORDER_CREATED" })}
                        disabled={review.isPending}
                        className="px-3 py-2 text-sm font-medium bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
                      >
                        Work Order Planned
                      </button>
                      <button
                        onClick={() => review.mutate({ id: prediction.id, status: "DISMISSED" })}
                        disabled={review.isPending}
                        className="px-3 py-2 text-sm font-medium border border-gray-300 text-gray-600 rounded-lg hover:bg-gray-50 disabled:opacity-50"
                      >
                        Dismiss
                      </button>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

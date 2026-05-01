"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { putawayApi, PutawayTask } from "@/lib/putaway";
import { wmsApi, StorageLocation } from "@/lib/wms";

export default function ExecutePutawayPage() {
  const params = useParams();
  const router = useRouter();
  const taskId = params.id as string;

  const [task, setTask] = useState<PutawayTask | null>(null);
  const [locations, setLocations] = useState<StorageLocation[]>([]);
  const [suggestion, setSuggestion] = useState<any>(null);
  const [actualLocationId, setActualLocationId] = useState("");
  const [overrideReason, setOverrideReason] = useState("");
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const suggestedId = task?.suggested_location_id;
  const isVariance = actualLocationId && actualLocationId !== suggestedId;

  useEffect(() => {
    putawayApi.getTask(taskId).then((t) => {
      setTask(t);
      if (t.suggested_location_id) setActualLocationId(t.suggested_location_id);
      if (t.warehouse_id) {
        wmsApi.listLocations({ warehouse_id: t.warehouse_id }).then(setLocations);
        putawayApi.suggestLocation({ warehouse_id: t.warehouse_id }).then(setSuggestion);
      }
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [taskId]);

  const handleExecute = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!actualLocationId) return;
    setSubmitting(true);
    setError("");
    try {
      await putawayApi.executeTask(taskId, {
        actual_location_id: actualLocationId,
        override_reason: overrideReason || undefined,
        notes: notes || undefined,
      });
      router.push("/dashboard/putaway");
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Execution failed");
      setSubmitting(false);
    }
  };

  if (loading) {
    return <div className="p-6 text-gray-400">Loading task…</div>;
  }

  if (!task) {
    return <div className="p-6 text-red-600">Task not found</div>;
  }

  return (
    <div className="p-6 max-w-2xl mx-auto space-y-6">
      <div>
        <button
          onClick={() => router.back()}
          className="text-sm text-blue-600 hover:underline mb-4 inline-block"
        >
          ← Back to Tasks
        </button>
        <h1 className="text-2xl font-bold text-gray-900">Execute Putaway</h1>
        <p className="text-sm text-gray-500 mt-1">Task: {task.task_no}</p>
      </div>

      {/* Task Summary */}
      <div className="bg-gray-50 rounded-lg border p-4 grid grid-cols-2 gap-3 text-sm">
        <div>
          <p className="text-xs text-gray-500">Item</p>
          <p className="font-medium">{task.product_name || task.material_name || "—"}</p>
        </div>
        <div>
          <p className="text-xs text-gray-500">Quantity</p>
          <p className="font-medium">{task.quantity}</p>
        </div>
        {task.lot_number && (
          <div>
            <p className="text-xs text-gray-500">Lot Number</p>
            <p className="font-medium font-mono">{task.lot_number}</p>
          </div>
        )}
        {task.receipt_ref && (
          <div>
            <p className="text-xs text-gray-500">Receipt Ref</p>
            <p className="font-medium">{task.receipt_ref}</p>
          </div>
        )}
        <div>
          <p className="text-xs text-gray-500">Suggested Location</p>
          <p className="font-medium font-mono text-blue-700">
            {task.suggested_location_code || <span className="text-gray-400 font-normal">None</span>}
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-500">Status</p>
          <p className="font-medium">{task.status}</p>
        </div>
      </div>

      {/* AI Suggestion Info */}
      {suggestion && suggestion.location_code && (
        <div className="bg-purple-50 border border-purple-200 rounded-lg p-3 text-sm">
          <p className="text-purple-800 font-semibold text-xs mb-1">Rule Engine Suggestion</p>
          <p className="text-purple-700">
            Location <strong>{suggestion.location_code}</strong> in zone <strong>{suggestion.zone_name || "—"}</strong>
            {" · "}Rule: <span className="font-mono text-xs">{suggestion.rule_applied}</span>
            {" · "}Confidence: <span className="font-semibold">{suggestion.confidence}</span>
          </p>
        </div>
      )}

      {/* Execution Form */}
      {task.status === "PENDING" || task.status === "IN_PROGRESS" ? (
        <form onSubmit={handleExecute} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">
              Actual Storage Location *
            </label>
            <select
              required
              value={actualLocationId}
              onChange={(e) => setActualLocationId(e.target.value)}
              className="w-full border rounded-lg px-3 py-2 text-sm"
            >
              <option value="">Select location…</option>
              {locations
                .filter((l) => l.is_active && !l.is_blocked)
                .map((l) => (
                  <option key={l.id} value={l.id}>
                    {l.code} — {l.zone_name || l.zone_id}{l.location_type ? ` (${l.location_type})` : ""}
                    {l.id === suggestedId ? " ★ Suggested" : ""}
                  </option>
                ))}
            </select>
          </div>

          {isVariance && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
              <p className="text-yellow-800 text-sm font-semibold mb-2">
                ⚠ Location differs from suggestion — override reason required
              </p>
              <textarea
                required
                value={overrideReason}
                onChange={(e) => setOverrideReason(e.target.value)}
                className="w-full border rounded-lg px-3 py-2 text-sm"
                rows={2}
                placeholder="Explain why you are using a different location…"
              />
            </div>
          )}

          <div>
            <label className="block text-sm font-medium mb-1">Notes</label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="w-full border rounded-lg px-3 py-2 text-sm"
              rows={2}
            />
          </div>

          {error && <p className="text-red-600 text-sm">{error}</p>}

          <div className="flex gap-3">
            <button
              type="button"
              onClick={() => router.back()}
              className="flex-1 py-2 border rounded-lg text-sm hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting || !actualLocationId}
              className="flex-1 py-2 bg-green-600 text-white rounded-lg text-sm hover:bg-green-700 disabled:opacity-50"
            >
              {submitting ? "Executing…" : "Confirm Putaway"}
            </button>
          </div>
        </form>
      ) : (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-center">
          <p className="text-green-700 font-semibold">Task {task.status}</p>
          {task.status === "COMPLETED" && (
            <p className="text-green-600 text-sm mt-1">Stock has been assigned to location.</p>
          )}
        </div>
      )}
    </div>
  );
}

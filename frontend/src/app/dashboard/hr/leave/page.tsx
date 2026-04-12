"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { hrApi, ApprovalStatus, LeaveRequest } from "@/lib/hr";
import { RequirePermission } from "@/components/PermissionGuard";
import { Badge } from "@/components/ui/Badge";

const APPROVAL_VARIANT: Record<ApprovalStatus, "yellow" | "green" | "red" | "gray"> = {
  PENDING: "yellow",
  APPROVED: "green",
  REJECTED: "red",
  CANCELLED: "gray",
};

function LeaveRequestForm({ employees, onSave, onCancel }: {
  employees: { id: string; full_name: string; department: string }[];
  onSave: (d: Record<string, unknown>) => void;
  onCancel: () => void;
}) {
  const [form, setForm] = useState({ employee_id: "", leave_type: "ANNUAL", start_date: "", end_date: "", reason: "" });
  const f = (k: string) => ({
    value: (form as Record<string, string>)[k],
    onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
      setForm((p) => ({ ...p, [k]: e.target.value })),
  });
  return (
    <div className="bg-white border rounded-lg p-4 space-y-3">
      <h3 className="font-semibold text-sm text-gray-800">New Leave Request</h3>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="text-xs text-gray-500">Employee</label>
          <select className="w-full border rounded px-2 py-1.5 text-sm mt-1" {...f("employee_id")}>
            <option value="">— select —</option>
            {employees.map((e) => <option key={e.id} value={e.id}>{e.full_name} ({e.department})</option>)}
          </select>
        </div>
        <div>
          <label className="text-xs text-gray-500">Leave Type</label>
          <select className="w-full border rounded px-2 py-1.5 text-sm mt-1" {...f("leave_type")}>
            {["ANNUAL", "SICK", "MATERNITY", "PATERNITY", "UNPAID", "COMPASSIONATE", "OTHER"].map((t) => <option key={t}>{t}</option>)}
          </select>
        </div>
        <div><label className="text-xs text-gray-500">Start Date</label><input type="date" className="w-full border rounded px-2 py-1.5 text-sm mt-1" {...f("start_date")} /></div>
        <div><label className="text-xs text-gray-500">End Date</label><input type="date" className="w-full border rounded px-2 py-1.5 text-sm mt-1" {...f("end_date")} /></div>
        <div className="col-span-2"><label className="text-xs text-gray-500">Reason</label><textarea className="w-full border rounded px-2 py-1.5 text-sm mt-1" rows={2} {...f("reason")} /></div>
      </div>
      <div className="flex gap-2">
        <button onClick={() => onSave(Object.fromEntries(Object.entries(form).filter(([, v]) => v !== "")))} className="px-3 py-1.5 bg-indigo-600 text-white rounded text-sm" disabled={!form.employee_id || !form.start_date || !form.end_date}>Submit</button>
        <button onClick={onCancel} className="px-3 py-1.5 border rounded text-sm">Cancel</button>
      </div>
    </div>
  );
}

function ReviewModal({ request, onSubmit, onClose }: {
  request: LeaveRequest;
  onSubmit: (status: ApprovalStatus, note: string) => void;
  onClose: () => void;
}) {
  const [status, setStatus] = useState<ApprovalStatus>("APPROVED");
  const [note, setNote] = useState("");
  return (
    <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-96 space-y-4 shadow-xl">
        <h3 className="font-semibold text-gray-800">Review Leave Request</h3>
        <p className="text-sm text-gray-600">{request.employee?.full_name} · {request.leave_type} · {request.days_requested} day(s)</p>
        <div>
          <label className="text-xs text-gray-500">Decision</label>
          <select className="w-full border rounded px-2 py-1.5 text-sm mt-1" value={status} onChange={(e) => setStatus(e.target.value as ApprovalStatus)}>
            <option value="APPROVED">Approve</option>
            <option value="REJECTED">Reject</option>
          </select>
        </div>
        <div>
          <label className="text-xs text-gray-500">Note (optional)</label>
          <textarea className="w-full border rounded px-2 py-1.5 text-sm mt-1" rows={2} value={note} onChange={(e) => setNote(e.target.value)} />
        </div>
        <div className="flex gap-2">
          <button onClick={() => onSubmit(status, note)} className="px-4 py-2 bg-indigo-600 text-white rounded text-sm">Submit</button>
          <button onClick={onClose} className="px-4 py-2 border rounded text-sm">Cancel</button>
        </div>
      </div>
    </div>
  );
}

function LeaveContent() {
  const qc = useQueryClient();
  const [statusFilter, setStatusFilter] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [reviewing, setReviewing] = useState<LeaveRequest | null>(null);

  const { data: requests = [], isLoading } = useQuery({
    queryKey: ["hr-leave", statusFilter],
    queryFn: () => hrApi.listLeaveRequests({ approval_status: statusFilter || undefined }),
  });

  const { data: employees = [] } = useQuery({ queryKey: ["hr-employees"], queryFn: () => hrApi.listEmployees() });

  const createMutation = useMutation({
    mutationFn: hrApi.createLeaveRequest,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["hr-leave"] }); setShowForm(false); },
  });

  const reviewMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: { approval_status: ApprovalStatus; review_note?: string } }) =>
      hrApi.reviewLeaveRequest(id, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["hr-leave"] }); setReviewing(null); },
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Leave Management</h1>
          <p className="text-sm text-gray-500 mt-1">{requests.length} requests</p>
        </div>
        <button onClick={() => setShowForm(true)} className="px-4 py-2 bg-indigo-600 text-white rounded text-sm hover:bg-indigo-700">
          + Request Leave
        </button>
      </div>

      {showForm && (
        <LeaveRequestForm
          employees={employees}
          onSave={(d) => createMutation.mutate(d)}
          onCancel={() => setShowForm(false)}
        />
      )}

      {reviewing && (
        <ReviewModal
          request={reviewing}
          onSubmit={(status, note) =>
            reviewMutation.mutate({ id: reviewing.id, data: { approval_status: status, review_note: note || undefined } })
          }
          onClose={() => setReviewing(null)}
        />
      )}

      <div className="flex gap-3">
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="border rounded px-3 py-2 text-sm">
          <option value="">All Statuses</option>
          {["PENDING", "APPROVED", "REJECTED", "CANCELLED"].map((s) => <option key={s}>{s}</option>)}
        </select>
      </div>

      <div className="bg-white border rounded-lg overflow-hidden">
        {isLoading ? (
          <p className="p-6 text-sm text-gray-400 text-center">Loading...</p>
        ) : requests.length === 0 ? (
          <p className="p-6 text-sm text-gray-400 text-center">No leave requests</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-xs text-gray-500 uppercase">
                <th className="px-4 py-2 text-left">Employee</th>
                <th className="px-4 py-2 text-left">Type</th>
                <th className="px-4 py-2 text-left">Start</th>
                <th className="px-4 py-2 text-left">End</th>
                <th className="px-4 py-2 text-right">Days</th>
                <th className="px-4 py-2 text-left">Status</th>
                <th className="px-4 py-2 text-left">Notes</th>
                <th className="px-4 py-2"></th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {requests.map((r) => (
                <tr key={r.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-900">{r.employee?.full_name ?? "—"}</td>
                  <td className="px-4 py-3 text-gray-600">{r.leave_type}</td>
                  <td className="px-4 py-3 text-gray-600">{r.start_date}</td>
                  <td className="px-4 py-3 text-gray-600">{r.end_date}</td>
                  <td className="px-4 py-3 text-right font-medium">{r.days_requested}</td>
                  <td className="px-4 py-3">
                    <Badge label={r.approval_status} variant={APPROVAL_VARIANT[r.approval_status]} />
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-500">{r.review_note ?? ""}</td>
                  <td className="px-4 py-3 text-right">
                    {r.approval_status === "PENDING" && (
                      <button onClick={() => setReviewing(r)} className="text-xs text-indigo-600 hover:underline">
                        Review
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

export default function LeavePage() {
  return (
    <RequirePermission permission="hr.view">
      <LeaveContent />
    </RequirePermission>
  );
}

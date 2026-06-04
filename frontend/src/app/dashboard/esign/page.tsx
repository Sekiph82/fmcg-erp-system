"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  esignApi,
  SignatureRequest,
  SignatureRequestStatus,
  statusColor,
  CreateSignatureRequest,
} from "@/lib/esign";
import { apiClient } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/Button";
import { RequirePermission } from "@/components/PermissionGuard";

// ── Types ─────────────────────────────────────────────────────────────────────

interface UserShort {
  id: string;
  full_name: string;
  email: string;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function KpiCard({ label, value, color }: { label: string; value: number; color?: string }) {
  return (
    <div className="bg-white rounded-xl border p-4 flex flex-col gap-1">
      <span className="text-xs text-gray-500 font-medium">{label}</span>
      <span className={`text-2xl font-bold ${color ?? "text-gray-900"}`}>{value}</span>
    </div>
  );
}

function StatusBadge({ s }: { s: SignatureRequestStatus | string }) {
  return (
    <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${statusColor(s as SignatureRequestStatus)}`}>
      {s}
    </span>
  );
}

function fmtDate(d: string | null) {
  if (!d) return "—";
  return new Date(d).toLocaleDateString("en-KE", { day: "2-digit", month: "short", year: "numeric" });
}

// ── Canvas Signature Pad ───────────────────────────────────────────────────────

function SignaturePad({ onSave, onCancel }: { onSave: (data: string) => void; onCancel: () => void }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const drawing = useRef(false);
  const [hasStrokes, setHasStrokes] = useState(false);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.fillStyle = "#f9fafb";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.strokeStyle = "#1e3a5f";
    ctx.lineWidth = 2;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
  }, []);

  const getPos = (e: React.MouseEvent | React.TouchEvent) => {
    const canvas = canvasRef.current!;
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    if ("touches" in e) {
      const t = e.touches[0];
      return { x: (t.clientX - rect.left) * scaleX, y: (t.clientY - rect.top) * scaleY };
    }
    return { x: (e.clientX - rect.left) * scaleX, y: (e.clientY - rect.top) * scaleY };
  };

  const startDraw = useCallback((e: React.MouseEvent | React.TouchEvent) => {
    e.preventDefault();
    drawing.current = true;
    const canvas = canvasRef.current!;
    const ctx = canvas.getContext("2d")!;
    const { x, y } = getPos(e);
    ctx.beginPath();
    ctx.moveTo(x, y);
  }, []);

  const draw = useCallback((e: React.MouseEvent | React.TouchEvent) => {
    if (!drawing.current) return;
    e.preventDefault();
    const canvas = canvasRef.current!;
    const ctx = canvas.getContext("2d")!;
    const { x, y } = getPos(e);
    ctx.lineTo(x, y);
    ctx.stroke();
    setHasStrokes(true);
  }, []);

  const endDraw = useCallback(() => {
    drawing.current = false;
  }, []);

  const clear = () => {
    const canvas = canvasRef.current!;
    const ctx = canvas.getContext("2d")!;
    ctx.fillStyle = "#f9fafb";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    setHasStrokes(false);
  };

  const save = () => {
    if (!hasStrokes) return;
    const data = canvasRef.current!.toDataURL("image/png");
    onSave(data);
  };

  return (
    <div className="flex flex-col gap-3">
      <p className="text-sm text-gray-600">Draw your signature below:</p>
      <canvas
        ref={canvasRef}
        width={500}
        height={180}
        className="w-full border-2 border-dashed border-blue-300 rounded-lg touch-none bg-gray-50 cursor-crosshair"
        style={{ touchAction: "none" }}
        onMouseDown={startDraw}
        onMouseMove={draw}
        onMouseUp={endDraw}
        onMouseLeave={endDraw}
        onTouchStart={startDraw}
        onTouchMove={draw}
        onTouchEnd={endDraw}
      />
      <div className="flex gap-2 justify-end">
        <button onClick={clear} className="text-xs text-gray-500 underline">Clear</button>
        <Button variant="secondary" onClick={onCancel}>Cancel</Button>
        <Button onClick={save} disabled={!hasStrokes}>Sign Document</Button>
      </div>
    </div>
  );
}

// ── Create Request Modal ───────────────────────────────────────────────────────

function CreateModal({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const [form, setForm] = useState<CreateSignatureRequest>({
    document_type: "contract",
    document_ref: "",
    subject: "",
    message: "",
    signer_ids: [],
    expires_at: "",
  });
  const [signerSearch, setSignerSearch] = useState("");
  const [selectedSigners, setSelectedSigners] = useState<UserShort[]>([]);

  const { data: users = [] } = useQuery<UserShort[]>({
    queryKey: ["users-search", signerSearch],
    queryFn: async () => {
      const res = await apiClient.get("/api/v1/users/", {
        params: { search: signerSearch, limit: 20 },
      });
      return res.data.items ?? res.data;
    },
    enabled: signerSearch.length > 0,
  });

  const mut = useMutation({
    mutationFn: () =>
      esignApi.createRequest({
        ...form,
        signer_ids: selectedSigners.map((s) => s.id),
        message: form.message || undefined,
        expires_at: form.expires_at || undefined,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["esign-requests"] });
      qc.invalidateQueries({ queryKey: ["esign-dashboard"] });
      onClose();
    },
  });

  const toggleSigner = (u: UserShort) => {
    setSelectedSigners((prev) =>
      prev.some((s) => s.id === u.id) ? prev.filter((s) => s.id !== u.id) : [...prev, u]
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg max-h-[90vh] overflow-y-auto p-6 flex flex-col gap-4">
        <h2 className="text-lg font-bold text-gray-900">New Signature Request</h2>

        <div className="grid grid-cols-2 gap-3">
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-gray-600">Document Type</label>
            <select
              className="border rounded-lg px-3 py-2 text-sm"
              value={form.document_type}
              onChange={(e) => setForm({ ...form, document_type: e.target.value })}
            >
              {["contract", "quotation", "delivery_note", "agreement", "nda", "purchase_order", "other"].map(
                (t) => <option key={t} value={t}>{t.replace("_", " ").toUpperCase()}</option>
              )}
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-gray-600">Document Reference *</label>
            <input
              className="border rounded-lg px-3 py-2 text-sm"
              placeholder="e.g. Contract CT-2024-001"
              value={form.document_ref}
              onChange={(e) => setForm({ ...form, document_ref: e.target.value })}
            />
          </div>
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-gray-600">Subject *</label>
          <input
            className="border rounded-lg px-3 py-2 text-sm"
            placeholder="Please sign: Supply Agreement 2025"
            value={form.subject}
            onChange={(e) => setForm({ ...form, subject: e.target.value })}
          />
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-gray-600">Message (optional)</label>
          <textarea
            className="border rounded-lg px-3 py-2 text-sm resize-none"
            rows={2}
            placeholder="Please review and sign the attached document."
            value={form.message}
            onChange={(e) => setForm({ ...form, message: e.target.value })}
          />
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-gray-600">Expires At (optional)</label>
          <input
            type="datetime-local"
            className="border rounded-lg px-3 py-2 text-sm"
            value={form.expires_at}
            onChange={(e) => setForm({ ...form, expires_at: e.target.value })}
          />
        </div>

        <div className="flex flex-col gap-2">
          <label className="text-xs font-medium text-gray-600">Add Signers *</label>
          <input
            className="border rounded-lg px-3 py-2 text-sm"
            placeholder="Search users by name..."
            value={signerSearch}
            onChange={(e) => setSignerSearch(e.target.value)}
          />
          {users.length > 0 && signerSearch && (
            <div className="border rounded-lg divide-y max-h-32 overflow-y-auto">
              {users.map((u) => (
                <button
                  key={u.id}
                  onClick={() => toggleSigner(u)}
                  className={`w-full text-left px-3 py-2 text-sm hover:bg-gray-50 flex items-center justify-between ${
                    selectedSigners.some((s) => s.id === u.id) ? "bg-blue-50" : ""
                  }`}
                >
                  <span>{u.full_name} <span className="text-gray-400">({u.email})</span></span>
                  {selectedSigners.some((s) => s.id === u.id) && (
                    <span className="text-blue-600 text-xs font-semibold">✓ Added</span>
                  )}
                </button>
              ))}
            </div>
          )}
          {selectedSigners.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {selectedSigners.map((s) => (
                <span
                  key={s.id}
                  className="inline-flex items-center gap-1 text-xs bg-blue-100 text-blue-800 px-2 py-0.5 rounded-full"
                >
                  {s.full_name}
                  <button
                    onClick={() => setSelectedSigners((prev) => prev.filter((x) => x.id !== s.id))}
                    className="text-blue-500 hover:text-blue-700"
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
          )}
        </div>

        {mut.isError && (
          <p className="text-sm text-red-600">{String((mut.error as Error).message)}</p>
        )}

        <div className="flex gap-2 justify-end pt-2">
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button
            onClick={() => mut.mutate()}
            disabled={
              mut.isPending ||
              !form.subject.trim() ||
              !form.document_ref.trim() ||
              selectedSigners.length === 0
            }
          >
            {mut.isPending ? "Creating…" : "Send for Signature"}
          </Button>
        </div>
      </div>
    </div>
  );
}

// ── Sign Modal ────────────────────────────────────────────────────────────────

function SignModal({
  req,
  onClose,
}: {
  req: SignatureRequest;
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const mut = useMutation({
    mutationFn: (data: string) => esignApi.sign(req.id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["esign-requests"] });
      qc.invalidateQueries({ queryKey: ["esign-dashboard"] });
      onClose();
    },
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg p-6 flex flex-col gap-4">
        <div>
          <h2 className="text-lg font-bold text-gray-900">Sign Document</h2>
          <p className="text-sm text-gray-500 mt-0.5">{req.document_ref}</p>
          <p className="text-sm text-gray-700 mt-1">{req.subject}</p>
          {req.message && <p className="text-sm text-gray-500 mt-1 italic">{req.message}</p>}
        </div>
        {mut.isError && (
          <p className="text-sm text-red-600">{String((mut.error as Error).message)}</p>
        )}
        <SignaturePad onSave={(data) => mut.mutate(data)} onCancel={onClose} />
      </div>
    </div>
  );
}

// ── Decline Modal ─────────────────────────────────────────────────────────────

function DeclineModal({ req, onClose }: { req: SignatureRequest; onClose: () => void }) {
  const qc = useQueryClient();
  const [reason, setReason] = useState("");
  const mut = useMutation({
    mutationFn: () => esignApi.decline(req.id, reason || undefined),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["esign-requests"] });
      qc.invalidateQueries({ queryKey: ["esign-dashboard"] });
      onClose();
    },
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6 flex flex-col gap-4">
        <h2 className="text-lg font-bold text-gray-900">Decline Signature</h2>
        <p className="text-sm text-gray-600">
          You are declining: <strong>{req.document_ref}</strong>
        </p>
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-gray-600">Reason (optional)</label>
          <textarea
            className="border rounded-lg px-3 py-2 text-sm resize-none"
            rows={3}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Explain why you are declining..."
          />
        </div>
        {mut.isError && (
          <p className="text-sm text-red-600">{String((mut.error as Error).message)}</p>
        )}
        <div className="flex gap-2 justify-end">
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button
            onClick={() => mut.mutate()}
            disabled={mut.isPending}
            className="bg-red-600 hover:bg-red-700"
          >
            {mut.isPending ? "Declining…" : "Confirm Decline"}
          </Button>
        </div>
      </div>
    </div>
  );
}

// ── Request Detail Panel ───────────────────────────────────────────────────────

function RequestRow({
  req,
  currentUserId,
  onSign,
  onDecline,
}: {
  req: SignatureRequest;
  currentUserId: string | null;
  onSign: (req: SignatureRequest) => void;
  onDecline: (req: SignatureRequest) => void;
}) {
  const myRecord = currentUserId
    ? req.signature_records.find((r) => r.signer_id === currentUserId)
    : null;
  const canSign = myRecord?.status === "PENDING" && req.status === "PENDING";

  return (
    <tr className="hover:bg-gray-50">
      <td className="px-4 py-3 text-sm font-mono text-blue-700">{req.request_no}</td>
      <td className="px-4 py-3 text-sm">
        <div className="font-medium text-gray-900 truncate max-w-[200px]">{req.document_ref}</div>
        <div className="text-xs text-gray-400">{req.document_type.toUpperCase()}</div>
      </td>
      <td className="px-4 py-3 text-sm text-gray-700 truncate max-w-[180px]">{req.subject}</td>
      <td className="px-4 py-3">
        <StatusBadge s={req.status} />
      </td>
      <td className="px-4 py-3 text-sm text-gray-500">
        {req.signed_count}/{req.required_count}
      </td>
      <td className="px-4 py-3 text-sm text-gray-400">{fmtDate(req.created_at)}</td>
      <td className="px-4 py-3 text-sm text-gray-400">{fmtDate(req.expires_at)}</td>
      <td className="px-4 py-3 text-xs text-gray-500 max-w-[120px]">
        {req.requester_name ?? "—"}
      </td>
      <td className="px-4 py-3">
        {canSign && (
          <div className="flex gap-1">
            <button
              onClick={() => onSign(req)}
              className="text-xs bg-blue-600 text-white px-2 py-1 rounded-md hover:bg-blue-700"
            >
              Sign
            </button>
            <button
              onClick={() => onDecline(req)}
              className="text-xs bg-red-100 text-red-700 px-2 py-1 rounded-md hover:bg-red-200"
            >
              Decline
            </button>
          </div>
        )}
      </td>
    </tr>
  );
}

// ── Signers List ──────────────────────────────────────────────────────────────

function SignersPopover({ req }: { req: SignatureRequest }) {
  return (
    <div className="text-xs space-y-1">
      {req.signature_records.map((r) => (
        <div key={r.id} className="flex items-center gap-1.5">
          <StatusBadge s={r.status} />
          <span>{r.signer_name ?? r.signer_id ?? "Unknown"}</span>
          {r.signed_at && <span className="text-gray-400">· {fmtDate(r.signed_at)}</span>}
        </div>
      ))}
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

function ESignPageInner() {
  const { user } = useAuth();
  const [tab, setTab] = useState<"all" | "mine">("mine");
  const [statusFilter, setStatusFilter] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [signTarget, setSignTarget] = useState<SignatureRequest | null>(null);
  const [declineTarget, setDeclineTarget] = useState<SignatureRequest | null>(null);

  const { data: stats } = useQuery({
    queryKey: ["esign-dashboard"],
    queryFn: esignApi.dashboard,
  });

  const { data: allRequests = [], isLoading: loadingAll } = useQuery({
    queryKey: ["esign-requests", "all", statusFilter],
    queryFn: () => esignApi.listRequests(statusFilter || undefined),
    enabled: tab === "all",
  });

  const { data: mineRequests = [], isLoading: loadingMine } = useQuery({
    queryKey: ["esign-requests", "mine"],
    queryFn: esignApi.pendingForMe,
    enabled: tab === "mine",
  });

  const requests = tab === "all" ? allRequests : mineRequests;
  const loading = tab === "all" ? loadingAll : loadingMine;

  const currentUserId = user?.id ?? null;

  return (
    <div className="p-6 flex flex-col gap-6 min-h-screen bg-gray-50">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Electronic Signatures</h1>
          <p className="text-sm text-gray-500 mt-0.5">Manage and track document signing requests</p>
        </div>
        <Button onClick={() => setShowCreate(true)}>+ New Request</Button>
      </div>

      {/* KPI Cards */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          <KpiCard label="Total" value={stats.total_requests} />
          <KpiCard label="Pending" value={stats.pending} color="text-yellow-600" />
          <KpiCard label="Signed" value={stats.signed} color="text-green-600" />
          <KpiCard label="Declined" value={stats.declined} color="text-red-600" />
          <KpiCard label="Expired" value={stats.expired} color="text-gray-500" />
          <KpiCard label="My Pending" value={stats.my_pending_signatures} color="text-blue-600" />
        </div>
      )}

      {/* Tabs + Filter */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex gap-0.5 bg-gray-100 rounded-lg p-0.5">
          {(["mine", "all"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
                tab === t ? "bg-white text-gray-900 shadow-sm" : "text-gray-500 hover:text-gray-700"
              }`}
            >
              {t === "mine" ? "Pending for Me" : "All Requests"}
            </button>
          ))}
        </div>
        {tab === "all" && (
          <select
            className="border rounded-lg px-3 py-1.5 text-sm bg-white"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="">All Statuses</option>
            <option value="PENDING">Pending</option>
            <option value="SIGNED">Signed</option>
            <option value="DECLINED">Declined</option>
            <option value="EXPIRED">Expired</option>
          </select>
        )}
      </div>

      {/* Requests Table */}
      <div className="bg-white rounded-xl border overflow-x-auto">
        {loading ? (
          <div className="p-8 text-center text-gray-400 text-sm">Loading…</div>
        ) : requests.length === 0 ? (
          <div className="p-10 text-center text-gray-400 text-sm">
            {tab === "mine" ? "No documents waiting for your signature." : "No signature requests found."}
          </div>
        ) : (
          <table className="w-full text-left">
            <thead>
              <tr className="border-b bg-gray-50 text-xs font-semibold text-gray-500 uppercase tracking-wide">
                <th className="px-4 py-3">Request No</th>
                <th className="px-4 py-3">Document</th>
                <th className="px-4 py-3">Subject</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Progress</th>
                <th className="px-4 py-3">Created</th>
                <th className="px-4 py-3">Expires</th>
                <th className="px-4 py-3">Requester</th>
                <th className="px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {requests.map((req) => (
                <RequestRow
                  key={req.id}
                  req={req}
                  currentUserId={currentUserId}
                  onSign={setSignTarget}
                  onDecline={setDeclineTarget}
                />
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Signers detail section for pending-for-me */}
      {tab === "mine" && requests.length > 0 && (
        <div className="flex flex-col gap-3">
          <h2 className="text-sm font-semibold text-gray-700">Signer Details</h2>
          {requests.map((req) => (
            <div key={req.id} className="bg-white rounded-xl border p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-gray-800">{req.document_ref}</span>
                <StatusBadge s={req.status} />
              </div>
              <SignersPopover req={req} />
            </div>
          ))}
        </div>
      )}

      {/* Modals */}
      {showCreate && <CreateModal onClose={() => setShowCreate(false)} />}
      {signTarget && (
        <SignModal req={signTarget} onClose={() => setSignTarget(null)} />
      )}
      {declineTarget && (
        <DeclineModal req={declineTarget} onClose={() => setDeclineTarget(null)} />
      )}
    </div>
  );
}

export default function ESignPage() {
  return (
    <RequirePermission permission="esign.view">
      <ESignPageInner />
    </RequirePermission>
  );
}

"use client";
// IT: register employees' signatures at hiring. The list shows only whether a signature is on file —
// IT never sees anyone's signature image after saving it; each employee sees their own on the e-sign page.
import { useCallback, useEffect, useRef, useState } from "react";
import { RequirePermission } from "@/components/PermissionGuard";
import { esignApi, type RegisteredSignature } from "@/lib/esign";

function errorText(e: unknown) {
  const detail = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
  if (typeof detail === "string") return detail;
  return "Request failed.";
}

function DrawPad({ onDone }: { onDone: (dataUrl: string) => void }) {
  const ref = useRef<HTMLCanvasElement>(null);
  const drawing = useRef(false);
  const [dirty, setDirty] = useState(false);
  useEffect(() => {
    const ctx = ref.current!.getContext("2d")!;
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, 500, 160);
    ctx.lineWidth = 2.5;
    ctx.lineCap = "round";
    ctx.strokeStyle = "#111827";
  }, []);
  const pos = (e: React.PointerEvent<HTMLCanvasElement>) => {
    const r = ref.current!.getBoundingClientRect();
    return { x: ((e.clientX - r.left) * 500) / r.width, y: ((e.clientY - r.top) * 160) / r.height };
  };
  return (
    <div className="space-y-2">
      <canvas ref={ref} width={500} height={160} aria-label="Draw signature" className="w-full max-w-md border-2 border-dashed rounded-lg bg-white touch-none"
        onPointerDown={(e) => { drawing.current = true; const p = pos(e); const c = ref.current!.getContext("2d")!; c.beginPath(); c.moveTo(p.x, p.y); }}
        onPointerMove={(e) => { if (!drawing.current) return; const p = pos(e); const c = ref.current!.getContext("2d")!; c.lineTo(p.x, p.y); c.stroke(); setDirty(true); }}
        onPointerUp={() => { drawing.current = false; }} onPointerLeave={() => { drawing.current = false; }} />
      <button type="button" disabled={!dirty} className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg disabled:opacity-50"
        onClick={() => onDone(ref.current!.toDataURL("image/png"))}>Save drawn signature</button>
    </div>
  );
}

function SignaturesAdmin() {
  const [rows, setRows] = useState<RegisteredSignature[]>([]);
  const [search, setSearch] = useState("");
  const [editing, setEditing] = useState<RegisteredSignature | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  const load = useCallback(async () => {
    try { setRows(await esignApi.listRegistered(search || undefined)); } catch (e) { setError(errorText(e)); }
  }, [search]);
  useEffect(() => { const t = setTimeout(load, 250); return () => clearTimeout(t); }, [load]);

  async function save(user: RegisteredSignature, dataUrl: string) {
    setError(null);
    try {
      await esignApi.register(user.user_id, dataUrl);
      setInfo(`Signature saved for ${user.full_name ?? user.username}. Only they can see it.`);
      setEditing(null);
      await load();
    } catch (e) { setError(errorText(e)); }
  }

  function fromFile(user: RegisteredSignature, file: File | undefined) {
    if (!file) return;
    if (!["image/png", "image/jpeg"].includes(file.type) || file.size > 300 * 1024) {
      setError("Use a PNG or JPEG image up to 300 KB.");
      return;
    }
    const reader = new FileReader();
    reader.onload = () => save(user, String(reader.result));
    reader.readAsDataURL(file);
  }

  return (
    <div className="p-6 space-y-4 max-w-5xl">
      <div>
        <a href="/dashboard/esign" className="text-xs text-indigo-600">← E-signatures</a>
        <h1 className="text-xl font-bold text-gray-900">Employee signatures</h1>
        <p className="text-sm text-gray-500">Register each new employee&apos;s signature when they are hired. It is applied automatically when they sign; only the employee can see it. Revoke it when someone leaves.</p>
      </div>
      {error && <p role="alert" className="rounded-lg p-3 text-sm bg-red-50 border border-red-200 text-red-700">{error}</p>}
      {info && !error && <p role="status" className="rounded-lg p-3 text-sm bg-emerald-50 border border-emerald-200 text-emerald-800">{info}</p>}
      <input aria-label="Search employees" placeholder="Search name or username…" value={search} onChange={(e) => setSearch(e.target.value)}
        className="text-sm border rounded-lg px-3 py-1.5 w-72" />
      <div className="bg-white rounded-xl border overflow-x-auto">
        <table className="w-full text-sm">
          <thead><tr className="text-left text-xs text-gray-500"><th className="p-2">Employee</th><th>Signature</th><th>Registered</th><th /></tr></thead>
          <tbody>{rows.map((r) => (
            <tr key={r.user_id} className="border-t align-top">
              <td className="p-2">{r.full_name ?? r.username}<div className="text-xs text-gray-500">{r.username}</div></td>
              <td>{r.has_signature ? <span className="text-emerald-700">On file</span> : <span className="text-amber-700">Missing</span>}
                {r.image_sha256 && <div className="text-[10px] font-mono text-gray-400">{r.image_sha256.slice(0, 16)}…</div>}</td>
              <td>{r.registered_at ? new Date(r.registered_at).toLocaleString() : "—"}</td>
              <td className="text-right p-2 space-x-2 whitespace-nowrap">
                <button className="text-xs underline" onClick={() => setEditing(editing?.user_id === r.user_id ? null : r)}>
                  {r.has_signature ? "Replace" : "Register"}
                </button>
                {r.has_signature && (
                  <button className="text-xs underline text-red-700" onClick={async () => {
                    try { await esignApi.revoke(r.user_id, "revoked by IT"); setInfo("Signature revoked."); await load(); } catch (e) { setError(errorText(e)); }
                  }}>Revoke</button>
                )}
              </td>
            </tr>
          ))}</tbody>
        </table>
      </div>
      {editing && (
        <div className="bg-white rounded-xl border p-4 space-y-3" aria-label="Register signature">
          <h2 className="font-semibold">Signature for {editing.full_name ?? editing.username}</h2>
          <label className="block text-sm">Upload a scanned signature (PNG/JPEG, max 300 KB)
            <input type="file" accept="image/png,image/jpeg" className="block mt-1 text-sm" onChange={(e) => fromFile(editing, e.target.files?.[0])} />
          </label>
          <div className="text-xs text-gray-500">or let the employee draw it here:</div>
          <DrawPad onDone={(d) => save(editing, d)} />
        </div>
      )}
    </div>
  );
}

export default function EmployeeSignaturesPage() {
  return <RequirePermission permission="esign.admin"><SignaturesAdmin /></RequirePermission>;
}

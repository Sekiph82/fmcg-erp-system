"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { serialApi, SerialNumber, SerialStatus, SerialMovement } from "@/lib/inventory";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";

const STATUS_COLORS: Record<SerialStatus, "green" | "blue" | "red" | "yellow" | "gray"> = {
  IN_STOCK: "green",
  SOLD: "blue",
  SCRAPPED: "red",
  IN_REPAIR: "yellow",
  RETURNED: "gray",
};

const MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];

function fmtDate(d?: string) {
  if (!d) return "—";
  const dt = new Date(d);
  return `${dt.getDate()} ${MONTHS[dt.getMonth()]} ${dt.getFullYear()}`;
}

export default function SerialsPage() {
  const qc = useQueryClient();
  const [search, setSearch] = useState("");
  const [filterStatus, setFilterStatus] = useState<SerialStatus | "">("");
  const [selected, setSelected] = useState<SerialNumber | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [showTransfer, setShowTransfer] = useState(false);
  const [lookupQuery, setLookupQuery] = useState("");
  const [lookupResult, setLookupResult] = useState<SerialNumber | null>(null);
  const [lookupError, setLookupError] = useState("");

  const { data: serials = [], isLoading } = useQuery({
    queryKey: ["serials", search, filterStatus],
    queryFn: () => serialApi.list({
      search: search || undefined,
      status: filterStatus || undefined,
    }),
  });

  const { data: history = [] } = useQuery({
    queryKey: ["serial-history", selected?.id],
    queryFn: () => (selected ? serialApi.history(selected.id) : []),
    enabled: !!selected,
  });

  const createSerial = useMutation({
    mutationFn: (data: Parameters<typeof serialApi.create>[0]) => serialApi.create(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["serials"] });
      setShowCreate(false);
    },
  });

  const transferSerial = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Parameters<typeof serialApi.transfer>[1] }) =>
      serialApi.transfer(id, data),
    onSuccess: (updated) => {
      qc.invalidateQueries({ queryKey: ["serials"] });
      qc.invalidateQueries({ queryKey: ["serial-history"] });
      setSelected(updated);
      setShowTransfer(false);
    },
  });

  async function doLookup() {
    setLookupResult(null);
    setLookupError("");
    if (!lookupQuery.trim()) return;
    try {
      const r = await serialApi.lookup(lookupQuery.trim());
      setLookupResult(r);
    } catch {
      setLookupError("Serial not found");
    }
  }

  const warrantyDaysLeft = (s: SerialNumber) => {
    if (!s.warranty_expiry) return null;
    const diff = Math.ceil((new Date(s.warranty_expiry).getTime() - Date.now()) / 86400000);
    return diff;
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Serial Number Tracking</h1>
          <p className="text-sm text-gray-500 mt-1">Per-unit tracking, status history, warranty visibility</p>
        </div>
        <Button onClick={() => setShowCreate(true)}>+ Assign Serial</Button>
      </div>

      {/* Quick Lookup */}
      <div className="bg-indigo-50 border border-indigo-100 rounded-lg p-4">
        <p className="text-sm font-semibold text-indigo-800 mb-2">Quick Serial Lookup</p>
        <div className="flex gap-2 items-center">
          <input
            className="border rounded px-3 py-2 text-sm flex-1 max-w-xs"
            placeholder="Enter serial number…"
            value={lookupQuery}
            onChange={(e) => setLookupQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && doLookup()}
          />
          <Button onClick={doLookup}>Lookup</Button>
        </div>
        {lookupError && <p className="text-red-600 text-sm mt-2">{lookupError}</p>}
        {lookupResult && (
          <div className="mt-3 flex items-center gap-4 text-sm bg-white rounded border p-3">
            <span className="font-mono font-bold text-indigo-700">{lookupResult.serial_no}</span>
            <span className="text-gray-600">{lookupResult.product_name}</span>
            <Badge label={lookupResult.status} variant={STATUS_COLORS[lookupResult.status]} />
            <span className="text-gray-500">{lookupResult.warehouse_name ?? "—"}</span>
            <button
              className="ml-auto text-xs text-indigo-600 hover:underline"
              onClick={() => { setSelected(lookupResult); setLookupResult(null); setLookupQuery(""); }}
            >
              View details
            </button>
          </div>
        )}
      </div>

      <div className="grid grid-cols-5 gap-4 text-center">
        {(["IN_STOCK", "SOLD", "IN_REPAIR", "RETURNED", "SCRAPPED"] as SerialStatus[]).map((s) => {
          const count = serials.filter((x) => x.status === s).length;
          return (
            <div
              key={s}
              className={`bg-white rounded-lg border p-3 cursor-pointer hover:border-indigo-300 ${filterStatus === s ? "border-indigo-500" : ""}`}
              onClick={() => setFilterStatus(filterStatus === s ? "" : s)}
            >
              <p className="text-2xl font-bold text-gray-800">{count}</p>
              <Badge label={s.replace("_", " ")} variant={STATUS_COLORS[s]} />
            </div>
          );
        })}
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* Serial list */}
        <div className="col-span-2 bg-white rounded-lg border">
          <div className="px-5 py-3 border-b flex items-center gap-3">
            <input
              className="border rounded px-3 py-1.5 text-sm flex-1"
              placeholder="Search serial no…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <select
              className="border rounded px-3 py-1.5 text-sm"
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value as SerialStatus | "")}
            >
              <option value="">All Statuses</option>
              {(["IN_STOCK", "SOLD", "IN_REPAIR", "RETURNED", "SCRAPPED"] as SerialStatus[]).map((s) => (
                <option key={s} value={s}>{s.replace("_", " ")}</option>
              ))}
            </select>
          </div>
          {isLoading ? (
            <p className="px-5 py-8 text-center text-gray-400">Loading…</p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-gray-50 text-xs text-gray-500 uppercase">
                  <th className="px-4 py-2 text-left">Serial No.</th>
                  <th className="px-4 py-2 text-left">Product</th>
                  <th className="px-4 py-2 text-left">Status</th>
                  <th className="px-4 py-2 text-left">Location</th>
                  <th className="px-4 py-2 text-left">Warranty</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {serials.map((s) => {
                  const wdays = warrantyDaysLeft(s);
                  return (
                    <tr
                      key={s.id}
                      className={`hover:bg-gray-50 cursor-pointer ${selected?.id === s.id ? "bg-indigo-50" : ""}`}
                      onClick={() => setSelected(s)}
                    >
                      <td className="px-4 py-2.5 font-mono font-semibold text-indigo-700">{s.serial_no}</td>
                      <td className="px-4 py-2.5 text-gray-700">{s.product_name ?? s.product_id.slice(0, 8)}</td>
                      <td className="px-4 py-2.5"><Badge label={s.status.replace("_", " ")} variant={STATUS_COLORS[s.status]} /></td>
                      <td className="px-4 py-2.5 text-gray-500">{s.warehouse_name ?? "—"}</td>
                      <td className="px-4 py-2.5">
                        {s.warranty_expiry ? (
                          <span className={`text-xs font-medium ${wdays != null && wdays < 30 ? "text-red-600" : wdays != null && wdays < 90 ? "text-amber-600" : "text-gray-600"}`}>
                            {fmtDate(s.warranty_expiry)}
                            {wdays != null && wdays < 0 ? " (expired)" : wdays != null && wdays < 90 ? ` (${wdays}d)` : ""}
                          </span>
                        ) : "—"}
                      </td>
                    </tr>
                  );
                })}
                {serials.length === 0 && (
                  <tr><td colSpan={5} className="px-5 py-8 text-center text-gray-400">No serials found</td></tr>
                )}
              </tbody>
            </table>
          )}
        </div>

        {/* Detail panel */}
        <div className="bg-white rounded-lg border p-5 space-y-4">
          {selected ? (
            <>
              <div className="flex items-start justify-between">
                <div>
                  <p className="font-mono font-bold text-indigo-700 text-lg">{selected.serial_no}</p>
                  <p className="text-sm text-gray-600 mt-0.5">{selected.product_name}</p>
                </div>
                <Badge label={selected.status.replace("_", " ")} variant={STATUS_COLORS[selected.status]} />
              </div>
              <div className="space-y-1.5 text-sm">
                {[
                  ["Lot", selected.lot_number ?? "—"],
                  ["Location", selected.warehouse_name ?? "—"],
                  ["Warranty", selected.warranty_expiry ? fmtDate(selected.warranty_expiry) : "—"],
                  ["Assigned", fmtDate(selected.created_at)],
                ].map(([label, value]) => (
                  <div key={label} className="flex gap-2">
                    <span className="text-gray-400 w-20 shrink-0">{label}</span>
                    <span className="text-gray-700 font-medium">{value}</span>
                  </div>
                ))}
                {selected.notes && <p className="text-gray-500 italic text-xs mt-2">{selected.notes}</p>}
              </div>

              <Button
                variant="secondary"
                onClick={() => setShowTransfer(true)}
                className="w-full"
              >
                Change Status / Location
              </Button>

              {/* History */}
              <div>
                <p className="text-xs font-semibold text-gray-500 uppercase mb-2">Movement History</p>
                {history.length === 0 ? (
                  <p className="text-xs text-gray-400">No history</p>
                ) : (
                  <div className="space-y-2">
                    {history.map((m) => (
                      <div key={m.id} className="text-xs border rounded p-2">
                        <div className="flex items-center gap-2">
                          {m.from_status && (
                            <><Badge label={m.from_status.replace("_", " ")} variant={STATUS_COLORS[m.from_status]} />
                            <span className="text-gray-400">→</span></>
                          )}
                          <Badge label={m.to_status.replace("_", " ")} variant={STATUS_COLORS[m.to_status]} />
                        </div>
                        <div className="text-gray-500 mt-1">
                          {fmtDate(m.created_at)}
                          {m.reference_type && ` · ${m.reference_type}`}
                          {m.reference_no && ` ${m.reference_no}`}
                          {m.moved_by_username && ` · ${m.moved_by_username}`}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </>
          ) : (
            <p className="text-center text-gray-400 text-sm py-12">Select a serial to view details</p>
          )}
        </div>
      </div>

      {showCreate && (
        <CreateSerialModal
          onClose={() => setShowCreate(false)}
          onSubmit={(d) => createSerial.mutate(d)}
          loading={createSerial.isPending}
        />
      )}

      {showTransfer && selected && (
        <TransferModal
          serial={selected}
          onClose={() => setShowTransfer(false)}
          onSubmit={(d) => transferSerial.mutate({ id: selected.id, data: d })}
          loading={transferSerial.isPending}
        />
      )}
    </div>
  );
}

function CreateSerialModal({
  onClose, onSubmit, loading,
}: {
  onClose: () => void;
  onSubmit: (d: Parameters<typeof serialApi.create>[0]) => void;
  loading: boolean;
}) {
  const [form, setForm] = useState({ serial_no: "", product_id: "", lot_id: "", warehouse_id: "", warranty_expiry: "", notes: "" });
  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-sm p-6 space-y-4">
        <h2 className="font-semibold text-lg">Assign Serial Number</h2>
        <div className="space-y-3">
          {[
            { k: "serial_no", label: "Serial No.", required: true, placeholder: "SN-001234" },
            { k: "product_id", label: "Product ID (UUID)", required: true, placeholder: "product UUID" },
            { k: "lot_id", label: "Lot ID (optional)", required: false, placeholder: "lot UUID" },
            { k: "warehouse_id", label: "Warehouse ID (optional)", required: false, placeholder: "warehouse UUID" },
          ].map(({ k, label, placeholder }) => (
            <div key={k}>
              <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
              <input
                className="w-full border rounded px-3 py-2 text-sm"
                value={(form as Record<string, string>)[k]}
                onChange={(e) => set(k, e.target.value)}
                placeholder={placeholder}
              />
            </div>
          ))}
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Warranty Expiry</label>
            <input type="date" className="w-full border rounded px-3 py-2 text-sm" value={form.warranty_expiry} onChange={(e) => set("warranty_expiry", e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Notes</label>
            <textarea className="w-full border rounded px-3 py-2 text-sm" rows={2} value={form.notes} onChange={(e) => set("notes", e.target.value)} />
          </div>
        </div>
        <div className="flex gap-2 justify-end">
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button
            loading={loading}
            onClick={() => onSubmit({
              serial_no: form.serial_no,
              product_id: form.product_id,
              lot_id: form.lot_id || undefined,
              warehouse_id: form.warehouse_id || undefined,
              warranty_expiry: form.warranty_expiry || undefined,
              notes: form.notes || undefined,
            })}
          >
            Assign
          </Button>
        </div>
      </div>
    </div>
  );
}

function TransferModal({
  serial, onClose, onSubmit, loading,
}: {
  serial: SerialNumber;
  onClose: () => void;
  onSubmit: (d: Parameters<typeof serialApi.transfer>[1]) => void;
  loading: boolean;
}) {
  const [form, setForm] = useState({
    to_status: serial.status as SerialStatus,
    to_warehouse_id: serial.warehouse_id ?? "",
    reference_type: "ADJUSTMENT",
    reference_no: "",
  });
  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-sm p-6 space-y-4">
        <h2 className="font-semibold text-lg">Change Status — {serial.serial_no}</h2>
        <div className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">New Status</label>
            <select className="w-full border rounded px-3 py-2 text-sm" value={form.to_status} onChange={(e) => set("to_status", e.target.value)}>
              {(["IN_STOCK", "SOLD", "IN_REPAIR", "RETURNED", "SCRAPPED"] as SerialStatus[]).map((s) => (
                <option key={s} value={s}>{s.replace("_", " ")}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">New Warehouse ID (optional)</label>
            <input className="w-full border rounded px-3 py-2 text-sm" value={form.to_warehouse_id} onChange={(e) => set("to_warehouse_id", e.target.value)} placeholder="warehouse UUID" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Reference Type</label>
            <select className="w-full border rounded px-3 py-2 text-sm" value={form.reference_type} onChange={(e) => set("reference_type", e.target.value)}>
              {["RECEIPT", "DISPATCH", "ADJUSTMENT", "RETURN", "REPAIR"].map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Reference No.</label>
            <input className="w-full border rounded px-3 py-2 text-sm" value={form.reference_no} onChange={(e) => set("reference_no", e.target.value)} placeholder="e.g. DO-0042" />
          </div>
        </div>
        <div className="flex gap-2 justify-end">
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button
            loading={loading}
            onClick={() => onSubmit({
              to_status: form.to_status,
              to_warehouse_id: form.to_warehouse_id || undefined,
              reference_type: form.reference_type || undefined,
              reference_no: form.reference_no || undefined,
            })}
          >
            Update
          </Button>
        </div>
      </div>
    </div>
  );
}

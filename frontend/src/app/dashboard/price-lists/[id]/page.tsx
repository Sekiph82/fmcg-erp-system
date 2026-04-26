"use client";
import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import {
  plApi, PLHeader, PLLine, PLTier, PLAssignment, PLChangeHistory, PLApproval,
  PL_STATUS_COLORS, PL_TYPE_COLORS, PLStatus,
} from "@/lib/price_list";

type Tab = "lines" | "tiers" | "assignments" | "history" | "approvals";

export default function PLDetail() {
  const { id } = useParams<{ id: string }>();
  const [hdr, setHdr] = useState<PLHeader | null>(null);
  const [lines, setLines] = useState<PLLine[]>([]);
  const [selectedLine, setSelectedLine] = useState<PLLine | null>(null);
  const [tiers, setTiers] = useState<PLTier[]>([]);
  const [assignments, setAssignments] = useState<PLAssignment[]>([]);
  const [history, setHistory] = useState<PLChangeHistory[]>([]);
  const [approvals, setApprovals] = useState<PLApproval[]>([]);
  const [tab, setTab] = useState<Tab>("lines");
  const [addingLine, setAddingLine] = useState(false);
  const [addingTier, setAddingTier] = useState(false);
  const [addingAsn, setAddingAsn] = useState(false);
  const [lineForm, setLineForm] = useState({ product_id: "", uom: "KG", base_price: "", minimum_price: "", currency: "KES" });
  const [tierForm, setTierForm] = useState({ min_qty: "", max_qty: "", unit_price: "", discount_pct: "" });
  const [asnForm, setAsnForm] = useState({ customer_id: "", channel: "", region: "", valid_from: "", priority_rank: 50 });
  const [submitter, setSubmitter] = useState("");
  const [reviewer, setReviewer] = useState("");
  const [saving, setSaving] = useState(false);

  const load = async () => {
    const [h, l, asn, hist, approv] = await Promise.all([
      plApi.getHeader(id),
      plApi.listLines(id),
      plApi.listAssignments(id),
      plApi.getHistory(id),
      plApi.getApprovals(id),
    ]);
    setHdr(h);
    setLines(l);
    setAssignments(asn);
    setHistory(hist);
    setApprovals(approv);
    if (l.length > 0 && !selectedLine) {
      setSelectedLine(l[0]);
      plApi.listTiers(l[0].id).then(setTiers);
    }
  };

  useEffect(() => { load(); }, [id]);

  const loadTiers = (line: PLLine) => {
    setSelectedLine(line);
    plApi.listTiers(line.id).then(setTiers);
    setTab("tiers");
  };

  const addLine = async () => {
    setSaving(true);
    await plApi.addLine(id, lineForm as any);
    setAddingLine(false);
    setLineForm({ product_id: "", uom: "KG", base_price: "", minimum_price: "", currency: "KES" });
    const updated = await plApi.listLines(id);
    setLines(updated);
    setSaving(false);
  };

  const addTier = async () => {
    if (!selectedLine) return;
    setSaving(true);
    await plApi.addTier(selectedLine.id, tierForm as any);
    setAddingTier(false);
    plApi.listTiers(selectedLine.id).then(setTiers);
    setSaving(false);
  };

  const addAssignment = async () => {
    setSaving(true);
    await plApi.addAssignment(id, asnForm as any);
    setAddingAsn(false);
    const updated = await plApi.listAssignments(id);
    setAssignments(updated);
    setSaving(false);
  };

  const submitApproval = async () => {
    if (!submitter) return;
    setSaving(true);
    const updated = await plApi.submitForApproval(id, submitter);
    setHdr(updated);
    setSaving(false);
  };

  const reviewApproval = async (action: "APPROVED" | "REJECTED") => {
    if (!reviewer) return;
    setSaving(true);
    const updated = await plApi.reviewApproval(id, action, reviewer);
    setHdr(updated);
    load();
    setSaving(false);
  };

  const activate = async () => {
    setSaving(true);
    const updated = await plApi.activate(id);
    setHdr(updated);
    setSaving(false);
  };

  if (!hdr) return <div className="p-6 text-gray-400">Loading…</div>;

  const canEdit = hdr.status === "DRAFT";

  const TABS: { key: Tab; label: string }[] = [
    { key: "lines", label: `Price Lines (${lines.length})` },
    { key: "tiers", label: `Tier Pricing${selectedLine ? ` — ${selectedLine.uom}` : ""}` },
    { key: "assignments", label: `Assignments (${assignments.length})` },
    { key: "history", label: `Change History (${history.length})` },
    { key: "approvals", label: `Approvals (${approvals.length})` },
  ];

  return (
    <div className="p-6 space-y-5">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3 flex-wrap">
            <a href="/dashboard/price-lists" className="text-blue-600 hover:underline text-sm">← Price Lists</a>
            <h1 className="text-xl font-bold text-gray-900">{hdr.price_list_name}</h1>
            <span className="font-mono text-xs bg-gray-100 px-2 py-0.5 rounded text-gray-600">{hdr.price_list_code}</span>
            <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${PL_TYPE_COLORS[hdr.pl_type]}`}>{hdr.pl_type.replace(/_/g, " ")}</span>
            <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${PL_STATUS_COLORS[hdr.status]}`}>{hdr.status}</span>
          </div>
          <div className="text-sm text-gray-500 mt-1">
            {hdr.currency} · Valid {hdr.valid_from} → {hdr.valid_to || "open"} · Priority {hdr.priority_rank}
            {hdr.minimum_margin_pct && ` · Min margin ${hdr.minimum_margin_pct}%`}
          </div>
        </div>
        <div className="flex gap-2">
          {hdr.status === "DRAFT" && (
            <div className="flex items-center gap-2">
              <input value={submitter} onChange={(e) => setSubmitter(e.target.value)}
                placeholder="Your name" className="border border-gray-300 rounded-lg px-2 py-1.5 text-xs w-28" />
              <button onClick={submitApproval} disabled={saving}
                className="px-3 py-1.5 bg-yellow-500 text-white rounded-lg text-xs font-medium">Submit</button>
            </div>
          )}
          {hdr.status === "UNDER_REVIEW" && (
            <div className="flex items-center gap-2">
              <input value={reviewer} onChange={(e) => setReviewer(e.target.value)}
                placeholder="Reviewer name" className="border border-gray-300 rounded-lg px-2 py-1.5 text-xs w-28" />
              <button onClick={() => reviewApproval("APPROVED")} className="px-3 py-1.5 bg-green-600 text-white rounded-lg text-xs font-medium">Approve</button>
              <button onClick={() => reviewApproval("REJECTED")} className="px-3 py-1.5 bg-red-500 text-white rounded-lg text-xs font-medium">Reject</button>
            </div>
          )}
          {hdr.status === "APPROVED" && (
            <button onClick={activate} disabled={saving} className="px-3 py-1.5 bg-green-600 text-white rounded-lg text-xs font-medium">Activate</button>
          )}
          {hdr.status === "ACTIVE" && (
            <button onClick={() => plApi.archive(id).then(setHdr)} className="px-3 py-1.5 bg-gray-500 text-white rounded-lg text-xs font-medium">Archive</button>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-gray-200">
        {TABS.map((t) => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition ${tab === t.key ? "border-blue-600 text-blue-700" : "border-transparent text-gray-500 hover:text-gray-700"}`}>
            {t.label}
          </button>
        ))}
      </div>

      {/* Price Lines */}
      {tab === "lines" && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
            <span className="text-sm font-semibold text-gray-900">Price Lines</span>
            {canEdit && (
              <button onClick={() => setAddingLine(true)} className="px-3 py-1.5 bg-blue-600 text-white rounded-lg text-xs font-medium">+ Add Line</button>
            )}
          </div>
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                {["Product ID", "UOM", "Base Price", "Min Price", "Rec. Price", "Currency", "Valid", "Actions"].map((h) => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {lines.length === 0 ? (
                <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-400">No lines yet. Add price lines above.</td></tr>
              ) : lines.map((l) => (
                <tr key={l.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono text-xs text-gray-500">{l.product_id.slice(0, 12)}…</td>
                  <td className="px-4 py-3 text-gray-700">{l.uom}</td>
                  <td className="px-4 py-3 font-mono font-semibold text-gray-900">{Number(l.base_price).toLocaleString()}</td>
                  <td className="px-4 py-3 font-mono text-gray-500">{l.minimum_price ? Number(l.minimum_price).toLocaleString() : "—"}</td>
                  <td className="px-4 py-3 font-mono text-gray-500">{l.recommended_price ? Number(l.recommended_price).toLocaleString() : "—"}</td>
                  <td className="px-4 py-3 text-xs">{l.currency}</td>
                  <td className="px-4 py-3 text-xs text-gray-500">{l.valid_from ? `${l.valid_from} →` : "Always"}{l.valid_to ? ` ${l.valid_to}` : ""}</td>
                  <td className="px-4 py-3">
                    <button onClick={() => loadTiers(l)} className="text-blue-600 hover:underline text-xs">Tiers</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Tiers */}
      {tab === "tiers" && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
            <div>
              <span className="text-sm font-semibold text-gray-900">Quantity Break Tiers</span>
              {selectedLine && <span className="text-xs text-gray-500 ml-2">for product {selectedLine.product_id.slice(0, 8)}… / {selectedLine.uom} @ base {Number(selectedLine.base_price).toLocaleString()}</span>}
            </div>
            {canEdit && selectedLine && (
              <button onClick={() => setAddingTier(true)} className="px-3 py-1.5 bg-blue-600 text-white rounded-lg text-xs font-medium">+ Add Tier</button>
            )}
          </div>
          {lines.length > 0 && (
            <div className="flex gap-2 p-3 border-b border-gray-100 flex-wrap">
              {lines.map((l) => (
                <button key={l.id} onClick={() => loadTiers(l)}
                  className={`px-2 py-1 rounded text-xs border ${selectedLine?.id === l.id ? "border-blue-500 bg-blue-50 text-blue-700" : "border-gray-200 text-gray-600"}`}>
                  {l.product_id.slice(0, 8)}… / {l.uom}
                </button>
              ))}
            </div>
          )}
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                {["Min Qty", "Max Qty", "Unit Price", "Discount %", "Fixed Disc.", "Est. Margin %"].map((h) => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {tiers.length === 0 ? (
                <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">No tiers. One price for all quantities.</td></tr>
              ) : tiers.map((t) => (
                <tr key={t.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono font-semibold">{Number(t.min_qty).toLocaleString()}</td>
                  <td className="px-4 py-3 font-mono text-gray-500">{t.max_qty ? Number(t.max_qty).toLocaleString() : "∞"}</td>
                  <td className="px-4 py-3 font-mono text-green-700">{t.unit_price ? Number(t.unit_price).toLocaleString() : "—"}</td>
                  <td className="px-4 py-3 text-blue-700">{t.discount_pct ? `${t.discount_pct}%` : "—"}</td>
                  <td className="px-4 py-3 font-mono text-gray-500">{t.fixed_discount_amount ? Number(t.fixed_discount_amount).toLocaleString() : "—"}</td>
                  <td className="px-4 py-3 text-gray-600">{t.effective_margin_pct ? `${t.effective_margin_pct}%` : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Assignments */}
      {tab === "assignments" && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
            <span className="text-sm font-semibold text-gray-900">Customer / Channel Assignments</span>
            <button onClick={() => setAddingAsn(true)} className="px-3 py-1.5 bg-blue-600 text-white rounded-lg text-xs font-medium">+ Add Assignment</button>
          </div>
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                {["Customer ID", "Channel", "Region", "Country", "Segment", "Valid From", "Valid To", "Priority"].map((h) => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {assignments.length === 0 ? (
                <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-400">No assignments. Price list applies globally by type/default.</td></tr>
              ) : assignments.map((a) => (
                <tr key={a.id}>
                  <td className="px-4 py-3 font-mono text-xs text-gray-500">{a.customer_id?.slice(0, 10) || "—"}</td>
                  <td className="px-4 py-3 text-gray-600">{a.channel || "—"}</td>
                  <td className="px-4 py-3 text-gray-600">{a.region || "—"}</td>
                  <td className="px-4 py-3 text-gray-600">{a.country || "—"}</td>
                  <td className="px-4 py-3 text-gray-600">{a.segment || "—"}</td>
                  <td className="px-4 py-3 text-xs text-gray-500">{a.valid_from}</td>
                  <td className="px-4 py-3 text-xs text-gray-500">{a.valid_to || "Open"}</td>
                  <td className="px-4 py-3 text-center text-xs font-bold">{a.priority_rank}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Change History */}
      {tab === "history" && (
        <div className="space-y-2">
          {history.length === 0 ? (
            <div className="bg-white border border-gray-200 rounded-xl p-8 text-center text-gray-400">No change history.</div>
          ) : history.map((h) => (
            <div key={h.id} className="bg-white border border-gray-200 rounded-xl p-4 flex items-start gap-3">
              <div className="w-2 h-2 rounded-full bg-blue-400 mt-1.5 shrink-0"></div>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-sm text-gray-900">{h.change_type.replace(/_/g, " ")}</span>
                  <span className="text-xs text-gray-400">by {h.changed_by}</span>
                </div>
                {h.new_value_json && (
                  <div className="text-xs text-gray-500 mt-0.5 font-mono">{JSON.stringify(h.new_value_json)}</div>
                )}
                <div className="text-xs text-gray-400 mt-0.5">{new Date(h.changed_at).toLocaleString()}</div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Approvals */}
      {tab === "approvals" && (
        <div className="space-y-2">
          {approvals.length === 0 ? (
            <div className="bg-white border border-gray-200 rounded-xl p-8 text-center text-gray-400">No approval records.</div>
          ) : approvals.map((a) => (
            <div key={a.id} className={`bg-white border rounded-xl p-4 ${a.action === "APPROVED" ? "border-green-200" : a.action === "REJECTED" ? "border-red-200" : "border-gray-200"}`}>
              <div className="flex items-center gap-2">
                <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${a.action === "APPROVED" ? "bg-green-100 text-green-800" : a.action === "REJECTED" ? "bg-red-100 text-red-800" : "bg-yellow-100 text-yellow-800"}`}>
                  {a.action}
                </span>
                <span className="text-sm text-gray-700">Submitted by {a.submitted_by}</span>
                {a.reviewed_by && <span className="text-sm text-gray-500">· Reviewed by {a.reviewed_by}</span>}
              </div>
              {a.notes && <div className="text-xs text-gray-500 mt-1">{a.notes}</div>}
              <div className="text-xs text-gray-400 mt-0.5">{a.created_at ? new Date(a.created_at).toLocaleString() : ""}</div>
            </div>
          ))}
        </div>
      )}

      {/* Add Line Modal */}
      {addingLine && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-2xl p-6 w-full max-w-md space-y-4">
            <h2 className="text-lg font-bold text-gray-900">Add Price Line</h2>
            <div>
              <label className="text-xs font-medium text-gray-700">Product ID</label>
              <input value={lineForm.product_id} onChange={(e) => setLineForm({ ...lineForm, product_id: e.target.value })}
                className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" placeholder="UUID" />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-medium text-gray-700">UOM</label>
                <input value={lineForm.uom} onChange={(e) => setLineForm({ ...lineForm, uom: e.target.value })}
                  className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="text-xs font-medium text-gray-700">Currency</label>
                <input value={lineForm.currency} onChange={(e) => setLineForm({ ...lineForm, currency: e.target.value })}
                  className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-medium text-gray-700">Base Price</label>
                <input type="number" value={lineForm.base_price} onChange={(e) => setLineForm({ ...lineForm, base_price: e.target.value })}
                  className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="text-xs font-medium text-gray-700">Minimum Price</label>
                <input type="number" value={lineForm.minimum_price} onChange={(e) => setLineForm({ ...lineForm, minimum_price: e.target.value })}
                  className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
              </div>
            </div>
            <div className="flex justify-end gap-3">
              <button onClick={() => setAddingLine(false)} className="px-4 py-2 border border-gray-300 rounded-lg text-sm">Cancel</button>
              <button onClick={addLine} disabled={saving} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium">Add</button>
            </div>
          </div>
        </div>
      )}

      {/* Add Tier Modal */}
      {addingTier && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-2xl p-6 w-full max-w-md space-y-4">
            <h2 className="text-lg font-bold text-gray-900">Add Quantity Tier</h2>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-medium text-gray-700">Min Qty</label>
                <input type="number" value={tierForm.min_qty} onChange={(e) => setTierForm({ ...tierForm, min_qty: e.target.value })}
                  className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="text-xs font-medium text-gray-700">Max Qty (blank = unlimited)</label>
                <input type="number" value={tierForm.max_qty} onChange={(e) => setTierForm({ ...tierForm, max_qty: e.target.value })}
                  className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-medium text-gray-700">Override Unit Price</label>
                <input type="number" value={tierForm.unit_price} onChange={(e) => setTierForm({ ...tierForm, unit_price: e.target.value })}
                  className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" placeholder="or use discount" />
              </div>
              <div>
                <label className="text-xs font-medium text-gray-700">Discount %</label>
                <input type="number" value={tierForm.discount_pct} onChange={(e) => setTierForm({ ...tierForm, discount_pct: e.target.value })}
                  className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" placeholder="e.g. 5" />
              </div>
            </div>
            <div className="flex justify-end gap-3">
              <button onClick={() => setAddingTier(false)} className="px-4 py-2 border border-gray-300 rounded-lg text-sm">Cancel</button>
              <button onClick={addTier} disabled={saving} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium">Add Tier</button>
            </div>
          </div>
        </div>
      )}

      {/* Add Assignment Modal */}
      {addingAsn && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-2xl p-6 w-full max-w-md space-y-4">
            <h2 className="text-lg font-bold text-gray-900">Add Assignment</h2>
            <div>
              <label className="text-xs font-medium text-gray-700">Customer ID (optional)</label>
              <input value={asnForm.customer_id} onChange={(e) => setAsnForm({ ...asnForm, customer_id: e.target.value })}
                className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-medium text-gray-700">Channel</label>
                <input value={asnForm.channel} onChange={(e) => setAsnForm({ ...asnForm, channel: e.target.value })}
                  className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="text-xs font-medium text-gray-700">Region</label>
                <input value={asnForm.region} onChange={(e) => setAsnForm({ ...asnForm, region: e.target.value })}
                  className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-medium text-gray-700">Valid From</label>
                <input type="date" value={asnForm.valid_from} onChange={(e) => setAsnForm({ ...asnForm, valid_from: e.target.value })}
                  className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="text-xs font-medium text-gray-700">Priority Rank</label>
                <input type="number" value={asnForm.priority_rank} onChange={(e) => setAsnForm({ ...asnForm, priority_rank: Number(e.target.value) })}
                  className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
              </div>
            </div>
            <div className="flex justify-end gap-3">
              <button onClick={() => setAddingAsn(false)} className="px-4 py-2 border border-gray-300 rounded-lg text-sm">Cancel</button>
              <button onClick={addAssignment} disabled={saving} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium">Assign</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

"use client";
import { useState } from "react";
import { useParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { subscriptionApi, STATUS_COLORS, GEN_STATUS_COLORS, RECURRENCE_LABELS } from "@/lib/subscription";
import Link from "next/link";
import { tx } from "@/lib/i18n/core";

export default function TemplateDetailPage() {
  const { id } = useParams<{ id: string }>();
  const qc = useQueryClient();
  const [tab, setTab] = useState<"lines" | "log" | "pauses">("lines");
  const [pauseForm, setPauseForm] = useState({ reason: "", effective_from: "", effective_to: "" });
  const [showPausePanel, setShowPausePanel] = useState(false);

  const { data: t, isLoading } = useQuery({
    queryKey: ["sub-template", id],
    queryFn: () => subscriptionApi.getTemplate(id),
  });

  const { data: genLog = [] } = useQuery({
    queryKey: ["sub-gen-log", id],
    queryFn: () => subscriptionApi.generationLog(id, { limit: 20 }),
    enabled: tab === "log",
  });

  const { data: pauses = [] } = useQuery({
    queryKey: ["sub-pauses", id],
    queryFn: () => subscriptionApi.pauseHistory(id),
    enabled: tab === "pauses",
  });

  const activateMut = useMutation({
    mutationFn: () => subscriptionApi.activate(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["sub-template", id] }),
  });

  const cancelMut = useMutation({
    mutationFn: () => subscriptionApi.cancel(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["sub-template", id] }),
  });

  const generateNowMut = useMutation({
    mutationFn: () => subscriptionApi.generateNow(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["sub-template", id] });
      qc.invalidateQueries({ queryKey: ["sub-gen-log", id] });
      setTab("log");
    },
  });

  const pauseMut = useMutation({
    mutationFn: (data: any) => subscriptionApi.pause(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["sub-template", id] });
      setShowPausePanel(false);
    },
  });

  const resumeMut = useMutation({
    mutationFn: () => subscriptionApi.resume(id, { action_type: "RESUME", effective_from: new Date().toISOString().split("T")[0] }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["sub-template", id] }),
  });

  if (isLoading) return <div className="p-6 text-slate-500">{tx("Loading…")}</div>;
  if (!t) return <div className="p-6 text-slate-500">{tx("Template not found")}</div>;

  return (
    <div className="p-6 space-y-6 text-slate-200">
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <Link href="/dashboard/recurring-orders/templates" className="text-slate-500 hover:text-slate-300 text-sm">{tx("← Templates")}</Link>
            <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${STATUS_COLORS[t.status]}`}>{t.status}</span>
          </div>
          <h1 className="text-xl font-bold text-white">{t.template_code}</h1>
          <p className="text-slate-400 text-sm">{t.template_name}</p>
        </div>
        <div className="flex gap-2">
          {t.status === "DRAFT" && (
            <button onClick={() => activateMut.mutate()} disabled={activateMut.isPending}
              className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium disabled:opacity-50">
              {tx("Activate")}
            </button>
          )}
          {t.status === "ACTIVE" && (
            <>
              <button onClick={() => generateNowMut.mutate()} disabled={generateNowMut.isPending}
                className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium disabled:opacity-50">
                {generateNowMut.isPending ? tx("Generating…") : tx("Generate Now")}
              </button>
              <button onClick={() => setShowPausePanel(true)}
                className="px-4 py-2 rounded-lg border border-amber-500/40 text-amber-400 hover:bg-amber-500/10 text-sm font-medium">
                {tx("Pause")}
              </button>
            </>
          )}
          {t.status === "PAUSED" && (
            <button onClick={() => resumeMut.mutate()} disabled={resumeMut.isPending}
              className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium disabled:opacity-50">
              {tx("Resume")}
            </button>
          )}
          {["ACTIVE", "PAUSED", "DRAFT"].includes(t.status) && (
            <button onClick={() => cancelMut.mutate()} disabled={cancelMut.isPending}
              className="px-4 py-2 rounded-lg border border-red-500/40 text-red-400 hover:bg-red-500/10 text-sm font-medium disabled:opacity-50">
              {tx("Cancel")}
            </button>
          )}
        </div>
      </div>

      {/* Info grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: tx("Recurrence"), value: RECURRENCE_LABELS[t.recurrence_type] },
          { label: tx("Generation Mode"), value: t.generation_mode.replace(/_/g, " ") },
          { label: tx("Next Generation"), value: t.next_generation_date ?? "—" },
          { label: tx("Last Generated"), value: t.last_generation_date ?? "—" },
          { label: tx("Start Date"), value: t.start_date },
          { label: tx("End Date"), value: t.end_date ?? tx("No end") },
          { label: tx("Currency"), value: t.currency },
          { label: tx("Lines"), value: String(t.lines.length) },
        ].map((item) => (
          <div key={item.label} className="glow-card p-4">
            <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">{item.label}</p>
            <p className="text-sm text-white font-medium">{item.value}</p>
          </div>
        ))}
      </div>

      {/* Pause panel */}
      {showPausePanel && (
        <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-5 space-y-3">
          <h3 className="text-sm font-semibold text-amber-300">{tx("Pause Template")}</h3>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-slate-400 mb-1 block">{tx("Effective From")}</label>
              <input type="date" value={pauseForm.effective_from}
                onChange={(e) => setPauseForm((f) => ({ ...f, effective_from: e.target.value }))}
                className="w-full bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white focus:outline-none" />
            </div>
            <div>
              <label className="text-xs text-slate-400 mb-1 block">{tx("Effective To (optional)")}</label>
              <input type="date" value={pauseForm.effective_to}
                onChange={(e) => setPauseForm((f) => ({ ...f, effective_to: e.target.value }))}
                className="w-full bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white focus:outline-none" />
            </div>
          </div>
          <div>
            <label className="text-xs text-slate-400 mb-1 block">{tx("Reason")}</label>
            <input value={pauseForm.reason}
              onChange={(e) => setPauseForm((f) => ({ ...f, reason: e.target.value }))}
              className="w-full bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white focus:outline-none"
              placeholder={tx("Optional reason...")} />
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => pauseMut.mutate({
                action_type: "PAUSE",
                effective_from: pauseForm.effective_from,
                effective_to: pauseForm.effective_to || undefined,
                reason: pauseForm.reason || undefined,
              })}
              disabled={!pauseForm.effective_from || pauseMut.isPending}
              className="px-4 py-2 rounded-lg bg-amber-600 hover:bg-amber-500 text-white text-sm font-medium disabled:opacity-50">
              {pauseMut.isPending ? tx("Pausing…") : tx("Confirm Pause")}
            </button>
            <button onClick={() => setShowPausePanel(false)}
              className="px-4 py-2 rounded-lg border border-white/[0.08] text-slate-400 text-sm">
              {tx("Cancel")}
            </button>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div>
        <div className="flex gap-1 border-b border-white/[0.07] mb-4">
          {(["lines", "log", "pauses"] as const).map((tb) => (
            <button key={tb} onClick={() => setTab(tb)}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                tab === tb ? "border-indigo-500 text-indigo-300" : "border-transparent text-slate-500 hover:text-slate-300"
              }`}>
              {tb === "lines" ? tx("Order Lines") : tb === "log" ? tx("Generation Log") : tx("Pause / Skip History")}
            </button>
          ))}
        </div>

        {/* Lines tab */}
        {tab === "lines" && (
          <div className="rounded-xl border border-white/[0.07] overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-white/[0.03] text-slate-500 text-xs uppercase tracking-wider">
                <tr>
                  <th className="px-4 py-3 text-left">{tx("Item ID")}</th>
                  <th className="px-4 py-3 text-left">UOM</th>
                  <th className="px-4 py-3 text-right">{tx("Qty")}</th>
                  <th className="px-4 py-3 text-left">{tx("Price Source")}</th>
                  <th className="px-4 py-3 text-right">{tx("Fixed Price")}</th>
                  <th className="px-4 py-3 text-left">{tx("Active")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04]">
                {t.lines.map((l) => (
                  <tr key={l.id} className="hover:bg-white/[0.02]">
                    <td className="px-4 py-3 font-mono text-xs text-slate-400">{l.item_id.slice(0, 8)}…</td>
                    <td className="px-4 py-3 text-slate-300">{l.uom}</td>
                    <td className="px-4 py-3 text-right text-white font-medium">{l.quantity}</td>
                    <td className="px-4 py-3 text-xs text-slate-400">{l.price_source.replace(/_/g, " ")}</td>
                    <td className="px-4 py-3 text-right text-slate-400">{l.fixed_price ?? "—"}</td>
                    <td className="px-4 py-3">
                      <span className={`text-xs px-2 py-0.5 rounded-full ${l.active_flag ? "bg-emerald-500/20 text-emerald-300" : "bg-red-500/20 text-red-400"}`}>
                        {l.active_flag ? tx("Active") : tx("Inactive")}
                      </span>
                    </td>
                  </tr>
                ))}
                {t.lines.length === 0 && (
                  <tr><td colSpan={6} className="text-center py-6 text-slate-600">{tx("No lines — add lines to enable order generation")}</td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}

        {/* Log tab */}
        {tab === "log" && (
          <div className="rounded-xl border border-white/[0.07] overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-white/[0.03] text-slate-500 text-xs uppercase tracking-wider">
                <tr>
                  <th className="px-4 py-3 text-left">{tx("Scheduled")}</th>
                  <th className="px-4 py-3 text-left">{tx("Generated At")}</th>
                  <th className="px-4 py-3 text-left">{tx("Status")}</th>
                  <th className="px-4 py-3 text-left">{tx("Sales Order")}</th>
                  <th className="px-4 py-3 text-left">{tx("Failure Reason")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04]">
                {genLog.map((l) => (
                  <tr key={l.id} className="hover:bg-white/[0.02]">
                    <td className="px-4 py-3 text-slate-300 text-xs">{l.scheduled_date}</td>
                    <td className="px-4 py-3 text-slate-500 text-xs">
                      {l.actual_generation_date ? new Date(l.actual_generation_date).toLocaleString() : "—"}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${GEN_STATUS_COLORS[l.generation_status] ?? "bg-slate-500/20 text-slate-400"}`}>
                        {l.generation_status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-400 font-mono text-xs">
                      {l.generated_so_id ? l.generated_so_id.slice(0, 8) + "…" : "—"}
                    </td>
                    <td className="px-4 py-3 text-red-400 text-xs">{l.failure_reason ?? ""}</td>
                  </tr>
                ))}
                {genLog.length === 0 && (
                  <tr><td colSpan={5} className="text-center py-6 text-slate-600">{tx("No generation history")}</td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}

        {/* Pauses tab */}
        {tab === "pauses" && (
          <div className="rounded-xl border border-white/[0.07] overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-white/[0.03] text-slate-500 text-xs uppercase tracking-wider">
                <tr>
                  <th className="px-4 py-3 text-left">{tx("Action")}</th>
                  <th className="px-4 py-3 text-left">{tx("From")}</th>
                  <th className="px-4 py-3 text-left">{tx("To")}</th>
                  <th className="px-4 py-3 text-left">{tx("Reason")}</th>
                  <th className="px-4 py-3 text-left">{tx("Portal")}</th>
                  <th className="px-4 py-3 text-left">{tx("Created")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04]">
                {pauses.map((p) => (
                  <tr key={p.id} className="hover:bg-white/[0.02]">
                    <td className="px-4 py-3">
                      <span className="text-xs px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300">{p.action_type}</span>
                    </td>
                    <td className="px-4 py-3 text-slate-300 text-xs">{p.effective_from}</td>
                    <td className="px-4 py-3 text-slate-400 text-xs">{p.effective_to ?? "—"}</td>
                    <td className="px-4 py-3 text-slate-400 text-xs">{p.reason ?? "—"}</td>
                    <td className="px-4 py-3 text-xs">{p.portal_request ? tx("Yes") : tx("No")}</td>
                    <td className="px-4 py-3 text-slate-500 text-xs">{new Date(p.created_at).toLocaleDateString()}</td>
                  </tr>
                ))}
                {pauses.length === 0 && (
                  <tr><td colSpan={6} className="text-center py-6 text-slate-600">{tx("No pause / skip history")}</td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

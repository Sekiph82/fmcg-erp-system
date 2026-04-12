"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  marketingApi,
  OptimizerRun,
  OptimizerRecommendations,
  OptimizerStatus,
} from "@/lib/marketingApi";
import { RequirePermission } from "@/components/PermissionGuard";

// ── Status badge ──────────────────────────────────────────────────────────────

const STATUS_CONFIG: Record<OptimizerStatus, { label: string; cls: string }> = {
  PENDING:  { label: "Pending",  cls: "bg-yellow-500/10 text-yellow-400 border-yellow-500/30" },
  COMPLETE: { label: "Complete", cls: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30" },
  APPROVED: { label: "Approved", cls: "bg-blue-500/10 text-blue-400 border-blue-500/30" },
  ARCHIVED: { label: "Archived", cls: "bg-slate-500/10 text-slate-400 border-slate-500/30" },
};

function StatusBadge({ status }: { status: OptimizerStatus }) {
  const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG.PENDING;
  return (
    <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${cfg.cls}`}>
      {cfg.label}
    </span>
  );
}

// ── Section card ──────────────────────────────────────────────────────────────

function Card({ title, accent, children }: { title: string; accent: string; children: React.ReactNode }) {
  return (
    <div className={`rounded-xl border bg-[#131c2e] p-5 ${accent}`}>
      <h3 className="mb-3 text-xs font-semibold uppercase tracking-widest text-slate-400">{title}</h3>
      {children}
    </div>
  );
}

// ── Tag pill ──────────────────────────────────────────────────────────────────

function Tag({ label, sub, cls = "bg-blue-600/10 border-blue-600/30 text-blue-300" }: { label: string; sub?: string; cls?: string }) {
  return (
    <span className={`inline-flex flex-col rounded-lg border px-3 py-1.5 text-sm ${cls}`}>
      <span className="font-medium">{label}</span>
      {sub && <span className="text-[11px] text-slate-400 mt-0.5">{sub}</span>}
    </span>
  );
}

// ── Bullet list ───────────────────────────────────────────────────────────────

function BulletList({ items, dot = "bg-blue-400" }: { items: string[]; dot?: string }) {
  return (
    <ul className="space-y-1.5">
      {items.map((item, i) => (
        <li key={i} className="flex items-start gap-2 text-sm text-slate-300">
          <span className={`mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${dot}`} />
          {item}
        </li>
      ))}
    </ul>
  );
}

// ── Stat row ──────────────────────────────────────────────────────────────────

function StatRow({ label, value, note }: { label: string; value: string | number; note?: string }) {
  return (
    <div className="flex items-center justify-between border-b border-slate-700/40 py-2 text-sm last:border-0">
      <span className="text-slate-400">{label}</span>
      <span className="font-semibold text-white">
        {value}
        {note && <span className="ml-1.5 text-xs text-slate-400 font-normal">{note}</span>}
      </span>
    </div>
  );
}

// ── Recommendations panel ─────────────────────────────────────────────────────

function RecommendationsPanel({ recs }: { recs: OptimizerRecommendations }) {
  return (
    <div className="space-y-4">

      {/* Row 1 — Targeting */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card title="Best Target Segments" accent="border-indigo-500/20">
          <div className="space-y-2">
            {recs.best_target_segments.segments.length > 0 ? (
              recs.best_target_segments.segments.map((s, i) => (
                <div key={i} className="rounded-lg bg-indigo-600/5 border border-indigo-600/20 p-2.5">
                  <p className="text-sm font-medium text-indigo-300">{s.name}</p>
                  <p className="text-[11px] text-slate-400">{s.type}</p>
                  <div className="mt-1 flex gap-3 text-[11px]">
                    <span className="text-emerald-400">LTV KES {s.avg_ltv.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
                    {s.churn_risk > 50 && <span className="text-orange-400">Churn risk {s.churn_risk.toFixed(0)}%</span>}
                  </div>
                </div>
              ))
            ) : (
              <p className="text-xs text-slate-500">No segment data yet — create CRM profiles with segment assignments.</p>
            )}
          </div>
          <p className="mt-2 text-[11px] text-slate-500">{recs.best_target_segments.reason}</p>
        </Card>

        <Card title="Best Regions" accent="border-cyan-500/20">
          <div className="space-y-2">
            {recs.best_target_regions.regions.length > 0 ? (
              recs.best_target_regions.regions.map((r, i) => (
                <div key={i} className="flex items-center justify-between">
                  <span className="text-sm text-slate-200">{r.name}</span>
                  <span className="text-xs text-emerald-400 font-medium">ROI {r.avg_roi.toFixed(2)}x</span>
                </div>
              ))
            ) : (
              <p className="text-xs text-slate-500">No completed campaigns with region data yet.</p>
            )}
          </div>
          <p className="mt-2 text-[11px] text-slate-500">{recs.best_target_regions.reason}</p>
        </Card>

        <Card title="Best Acquisition Channels" accent="border-violet-500/20">
          <div className="space-y-2">
            {recs.best_acquisition_channels.channels.length > 0 ? (
              recs.best_acquisition_channels.channels.map((a, i) => (
                <div key={i} className="flex items-center justify-between">
                  <span className="text-sm text-slate-200">{a.source}</span>
                  <span className="text-xs text-violet-400 font-medium">LTV KES {a.avg_ltv.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
                </div>
              ))
            ) : (
              <p className="text-xs text-slate-500">No CRM acquisition source data yet.</p>
            )}
          </div>
          <p className="mt-2 text-[11px] text-slate-500">{recs.best_acquisition_channels.reason}</p>
        </Card>
      </div>

      {/* Row 2 — Campaign & Promotion type */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card title="Best Campaign Type" accent="border-blue-500/20">
          <div className="mb-3 flex items-center gap-3">
            <span className="rounded-lg bg-blue-600/20 border border-blue-600/30 px-3 py-1.5 text-sm font-bold text-blue-300">
              {recs.best_campaign_type.value}
            </span>
          </div>
          {recs.best_campaign_type.all_types.length > 0 && (
            <div className="space-y-1">
              {recs.best_campaign_type.all_types.map((t, i) => (
                <div key={i} className="flex items-center justify-between text-xs">
                  <span className={t.type === recs.best_campaign_type.value ? "text-blue-300 font-medium" : "text-slate-400"}>{t.type}</span>
                  <span className="text-emerald-400">ROI {t.avg_roi.toFixed(2)}x</span>
                </div>
              ))}
            </div>
          )}
          <p className="mt-2 text-[11px] text-slate-500">{recs.best_campaign_type.reason}</p>
        </Card>

        <Card title="Best Promotion Type" accent="border-pink-500/20">
          <div className="flex gap-2 mb-3">
            <Tag label={recs.best_promotion_type.primary} sub="Primary" cls="bg-pink-600/10 border-pink-600/30 text-pink-300" />
            <Tag label={recs.best_promotion_type.secondary} sub="Secondary" cls="bg-orange-600/10 border-orange-600/30 text-orange-300" />
          </div>
          <p className="text-[11px] text-slate-500">{recs.best_promotion_type.reason}</p>
        </Card>
      </div>

      {/* Row 3 — Budget split */}
      <Card title="Best Budget Split" accent="border-amber-500/20">
        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <div className="mb-3 flex gap-4">
              <div className="text-center">
                <p className="text-3xl font-bold text-amber-400">{recs.best_budget_split.trade_spend_pct}%</p>
                <p className="text-xs text-slate-400">Trade Spend</p>
              </div>
              <div className="text-center">
                <p className="text-3xl font-bold text-blue-400">{recs.best_budget_split.brand_spend_pct}%</p>
                <p className="text-xs text-slate-400">Brand Spend</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-violet-400">{recs.best_budget_split.digital_of_brand_pct}%</p>
                <p className="text-xs text-slate-400">Digital (of brand)</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-pink-400">{recs.best_budget_split.influencer_of_brand_pct}%</p>
                <p className="text-xs text-slate-400">Influencer (of brand)</p>
              </div>
            </div>
            <p className="text-[11px] text-slate-500">{recs.best_budget_split.reason}</p>
          </div>
          {recs.best_budget_split.brand_by_category.length > 0 && (
            <div>
              <p className="text-xs font-medium text-slate-400 mb-2">Brand spend breakdown</p>
              <div className="space-y-1">
                {recs.best_budget_split.brand_by_category.map((c, i) => (
                  <div key={i} className="flex items-center justify-between text-xs">
                    <span className="text-slate-300">{c.category}</span>
                    <span className="text-amber-400 font-medium">KES {c.amount.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </Card>

      {/* Row 4 — Channel mixes */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card title="Store / Channel Mix" accent="border-teal-500/20">
          {recs.best_store_channel_mix.top_stores.length > 0 ? (
            <div className="space-y-1.5">
              {recs.best_store_channel_mix.top_stores.map((s, i) => (
                <div key={i} className="text-xs">
                  <p className="font-medium text-slate-200">{s.store}</p>
                  <p className="text-slate-500">{s.platform} · CVR {(s.cvr * 100).toFixed(1)}%</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-slate-500">No store performance data yet.</p>
          )}
          <p className="mt-2 text-[11px] text-slate-500">{recs.best_store_channel_mix.reason}</p>
        </Card>

        <Card title="Ad Platform Mix" accent="border-blue-500/20">
          {recs.best_ad_platform_mix.platforms.length > 0 ? (
            <div className="space-y-1.5">
              {recs.best_ad_platform_mix.platforms.map((p, i) => (
                <div key={i} className="flex items-center justify-between text-xs">
                  <span className="text-slate-200">{p.platform}</span>
                  <span className={p.roas >= 2 ? "text-emerald-400 font-medium" : p.roas >= 1.2 ? "text-yellow-400" : "text-red-400"}>
                    {p.roas.toFixed(2)}x ROAS
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-slate-500">No ad performance data yet.</p>
          )}
          <p className="mt-2 text-[11px] text-slate-500">{recs.best_ad_platform_mix.reason}</p>
        </Card>

        <Card title="Influencer Mix" accent="border-pink-500/20">
          {recs.best_influencer_mix.platforms.length > 0 ? (
            <div className="space-y-1.5">
              {recs.best_influencer_mix.platforms.map((p, i) => (
                <div key={i} className="text-xs">
                  <p className="font-medium text-slate-200">{p.platform}</p>
                  <p className="text-slate-500">Score {p.score.toFixed(1)} · Rev KES {p.revenue.toLocaleString(undefined, { maximumFractionDigits: 0 })}</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-slate-500">No influencer data yet.</p>
          )}
        </Card>

        <Card title="Social Platforms" accent="border-violet-500/20">
          {recs.best_social_platforms.platforms.length > 0 ? (
            <div className="space-y-1.5">
              {recs.best_social_platforms.platforms.map((p, i) => (
                <div key={i} className="flex items-center justify-between text-xs">
                  <span className="text-slate-200">{p.platform}</span>
                  <span className="text-violet-400 font-medium">{(p.eng_rate * 100).toFixed(1)}% eng</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-slate-500">No social media data yet.</p>
          )}
          <p className="mt-2 text-[11px] text-slate-500">{recs.best_social_platforms.reason}</p>
        </Card>
      </div>

      {/* Row 5 — Product-channel fit + Return risk */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card title="Product-Channel Fit" accent="border-green-500/20">
          {recs.product_channel_fit.top_combos.length > 0 ? (
            <div className="space-y-2">
              {recs.product_channel_fit.top_combos.map((c, i) => (
                <div key={i} className="rounded-lg bg-green-600/5 border border-green-600/15 p-2.5 text-xs">
                  <p className="font-medium text-green-300">{c.store} — {c.platform}</p>
                  <div className="flex gap-3 mt-1 text-slate-400">
                    <span>Rev KES {c.revenue.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
                    <span>CVR {(c.cvr * 100).toFixed(1)}%</span>
                    {c.return_rate > 0.05 && <span className="text-orange-400">Ret {(c.return_rate * 100).toFixed(1)}%</span>}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-slate-500">No product-channel performance data yet.</p>
          )}
          <p className="mt-2 text-[11px] text-slate-500">{recs.product_channel_fit.reason}</p>
        </Card>

        <Card title="Return Risk Signals" accent="border-orange-500/20">
          {recs.return_risk_signals.high_return_channels.length > 0 ? (
            <div className="space-y-2">
              {recs.return_risk_signals.high_return_channels.map((c, i) => (
                <div key={i} className="flex items-center justify-between text-xs">
                  <div>
                    <p className="font-medium text-slate-200">{c.store}</p>
                    <p className="text-slate-500">{c.platform}</p>
                  </div>
                  <span className={`font-semibold ${c.return_rate > 0.15 ? "text-red-400" : c.return_rate > 0.08 ? "text-orange-400" : "text-yellow-400"}`}>
                    {(c.return_rate * 100).toFixed(1)}% returns
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-slate-500">No high-return channels flagged. All clear.</p>
          )}
          <p className="mt-2 text-[11px] text-slate-500">{recs.return_risk_signals.reason}</p>
        </Card>
      </div>

      {/* Row 6 — Predictions */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card title="Predicted ROI Range" accent="border-emerald-500/20">
          <div className="flex items-center gap-4 mb-3">
            <div className="text-center">
              <p className="text-3xl font-bold text-emerald-400">{recs.predicted_roi_range.low}x</p>
              <p className="text-xs text-slate-400">Low estimate</p>
            </div>
            <div className="text-slate-600 text-xl">–</div>
            <div className="text-center">
              <p className="text-3xl font-bold text-emerald-300">{recs.predicted_roi_range.high}x</p>
              <p className="text-xs text-slate-400">High estimate</p>
            </div>
          </div>
          <p className="text-[11px] text-slate-500">{recs.predicted_roi_range.basis}</p>
        </Card>

        <Card title="Predicted Revenue Uplift" accent="border-sky-500/20">
          <div className="mb-3">
            <p className="text-4xl font-bold text-sky-400">+{recs.predicted_uplift.pct}%</p>
            <p className="text-xs text-slate-400 mt-0.5">vs baseline</p>
          </div>
          <p className="text-[11px] text-slate-500">{recs.predicted_uplift.basis}</p>
        </Card>
      </div>

      {/* Row 7 — Risk + Scaling + Improvements */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card title="Risk Notes" accent="border-red-500/20">
          <BulletList items={recs.risk_notes} dot="bg-red-400" />
        </Card>

        <Card title="Scaling Suggestions" accent="border-emerald-500/20">
          <BulletList items={recs.scaling_suggestions} dot="bg-emerald-400" />
        </Card>

        <Card title="Campaign Improvement Suggestions" accent="border-amber-500/20">
          <BulletList items={recs.campaign_improvement_suggestions} dot="bg-amber-400" />
        </Card>
      </div>

      {/* Row 8 — Content suggestions */}
      <Card title="Content Suggestions" accent="border-purple-500/20">
        <div className="flex flex-wrap gap-2">
          {recs.content_suggestions.map((s, i) => (
            <Tag key={i} label={s} cls="bg-purple-600/10 border-purple-600/30 text-purple-300" />
          ))}
        </div>
      </Card>
    </div>
  );
}

// ── Input summary panel ───────────────────────────────────────────────────────

function InputSummaryPanel({ summary }: { summary: Record<string, unknown> }) {
  const entries = [
    { label: "Campaign types analysed",       key: "campaign_types_analysed" },
    { label: "Regions analysed",              key: "regions_analysed" },
    { label: "Ad platforms analysed",         key: "ad_platforms_analysed" },
    { label: "Influencer platforms",          key: "influencer_platforms_used" },
    { label: "Segments evaluated",            key: "segments_evaluated" },
    { label: "Acquisition sources tracked",   key: "acquisition_sources_tracked" },
    { label: "Survey signals",                key: "survey_signals" },
    { label: "High-return channels flagged",  key: "high_return_channels_flagged" },
    { label: "Product-channel pairs",         key: "product_channel_pairs" },
    { label: "Social platforms tracked",      key: "social_platforms_tracked" },
    { label: "At-risk customers",             key: "at_risk_customers" },
    { label: "VIP customers",                 key: "vip_customers" },
    { label: "Total historical spend (KES)",  key: "total_historical_spend_kes", fmt: (v: unknown) => `KES ${Number(v).toLocaleString(undefined, { maximumFractionDigits: 0 })}` },
    { label: "Engine version",                key: "engine_version" },
  ];

  return (
    <div className="rounded-xl border border-slate-700/50 bg-[#0e1728] p-4">
      <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-slate-500">Data sources used in this run</p>
      <div className="grid gap-x-8 md:grid-cols-2">
        {entries.map(({ label, key, fmt }) => {
          const val = summary[key];
          if (val === undefined || val === null) return null;
          return (
            <StatRow
              key={key}
              label={label}
              value={fmt ? fmt(val) : String(val)}
            />
          );
        })}
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function AIOptimizerPage() {
  const qc = useQueryClient();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [context, setContext] = useState("");
  const [notes, setNotes] = useState("");
  const [approveNotes, setApproveNotes] = useState("");
  const [showApproveModal, setShowApproveModal] = useState(false);

  const { data: runs = [], isLoading } = useQuery({
    queryKey: ["optimizer-runs"],
    queryFn: () => marketingApi.optimizer.list({ limit: 20 }).then((r) => r.data),
  });

  const { data: selectedRun, isLoading: loadingSelected } = useQuery({
    queryKey: ["optimizer-run", selectedId],
    queryFn: () => marketingApi.optimizer.get(selectedId!).then((r) => r.data),
    enabled: !!selectedId,
  });

  const runMut = useMutation({
    mutationFn: () =>
      marketingApi.optimizer.run({
        campaign_context: context.trim() || undefined,
        notes: notes.trim() || undefined,
      }),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ["optimizer-runs"] });
      setSelectedId(res.data.id);
    },
  });

  const approveMut = useMutation({
    mutationFn: () =>
      marketingApi.optimizer.approve(selectedId!, approveNotes.trim() || undefined),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["optimizer-runs"] });
      qc.invalidateQueries({ queryKey: ["optimizer-run", selectedId] });
      setShowApproveModal(false);
      setApproveNotes("");
    },
  });

  const recs = selectedRun?.recommendation_json ?? null;

  return (
    <RequirePermission permission="ai_optimizer.view">
      <div className="min-h-screen bg-[#0b1120] p-6 text-white">

        {/* Header */}
        <div className="mb-6 flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 text-white shadow-lg">
                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
              </span>
              <h1 className="text-2xl font-bold">AI Campaign Optimizer</h1>
              <span className="rounded-full border border-indigo-500/30 bg-indigo-600/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-indigo-400">
                v1 · Rules Engine
              </span>
            </div>
            <p className="text-sm text-slate-400">
              Analyses 14 ERP data sources — campaigns, CRM, spend, influencers, ads, e-commerce, surveys, returns — to generate CMO-ready recommendations.
            </p>
          </div>
        </div>

        <div className="grid gap-6 lg:grid-cols-[340px_1fr]">

          {/* ── Left panel: controls + history ── */}
          <div className="space-y-4">

            {/* Input form */}
            <div className="rounded-xl border border-slate-700/50 bg-[#131c2e] p-5">
              <h2 className="mb-4 font-semibold text-white">Run Optimizer</h2>

              <div className="space-y-3">
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-400">
                    Campaign context <span className="text-slate-600">(optional)</span>
                  </label>
                  <textarea
                    value={context}
                    onChange={(e) => setContext(e.target.value)}
                    rows={3}
                    placeholder="E.g. Q3 product launch — Uji Power brand, targeting Nairobi Modern Trade…"
                    className="w-full resize-none rounded-lg border border-slate-700 bg-[#0b1120] px-3 py-2 text-sm text-white placeholder-slate-600 focus:border-indigo-500 focus:outline-none"
                  />
                </div>

                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-400">
                    Notes <span className="text-slate-600">(optional)</span>
                  </label>
                  <input
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    placeholder="Internal notes for this run…"
                    className="w-full rounded-lg border border-slate-700 bg-[#0b1120] px-3 py-2 text-sm text-white placeholder-slate-600 focus:border-indigo-500 focus:outline-none"
                  />
                </div>

                <button
                  onClick={() => runMut.mutate()}
                  disabled={runMut.isPending}
                  className="w-full rounded-lg bg-gradient-to-r from-indigo-600 to-violet-600 py-2.5 text-sm font-semibold text-white shadow transition hover:from-indigo-700 hover:to-violet-700 disabled:opacity-50"
                >
                  {runMut.isPending ? (
                    <span className="flex items-center justify-center gap-2">
                      <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
                      </svg>
                      Analysing…
                    </span>
                  ) : (
                    "Run AI Optimizer"
                  )}
                </button>

                {runMut.isError && (
                  <p className="text-xs text-red-400">Failed to run optimizer. Check your permissions.</p>
                )}
              </div>
            </div>

            {/* Run history */}
            <div className="rounded-xl border border-slate-700/50 bg-[#131c2e] p-4">
              <h2 className="mb-3 text-sm font-semibold text-slate-300">Run History</h2>

              {isLoading ? (
                <div className="space-y-2">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="h-14 animate-pulse rounded-lg bg-slate-800/50" />
                  ))}
                </div>
              ) : runs.length === 0 ? (
                <p className="text-xs text-slate-500">No optimizer runs yet. Run your first analysis above.</p>
              ) : (
                <div className="space-y-2">
                  {(runs as OptimizerRun[]).map((run) => (
                    <button
                      key={run.id}
                      onClick={() => setSelectedId(run.id)}
                      className={[
                        "w-full rounded-lg border p-3 text-left transition-colors",
                        selectedId === run.id
                          ? "border-indigo-500/50 bg-indigo-600/10"
                          : "border-slate-700/40 bg-[#0b1120] hover:border-slate-600",
                      ].join(" ")}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-medium text-slate-200 truncate max-w-[160px]">
                          {run.campaign_context
                            ? run.campaign_context.slice(0, 40)
                            : `Run ${run.run_date}`}
                        </span>
                        <StatusBadge status={run.status} />
                      </div>
                      <p className="mt-1 text-[11px] text-slate-500">
                        {run.run_date} · {(run.input_summary as Record<string, unknown>)?.engine_version as string ?? "v1"}
                      </p>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* ── Right panel: results ── */}
          <div>
            {!selectedId && (
              <div className="flex h-96 flex-col items-center justify-center rounded-xl border border-dashed border-slate-700 text-center">
                <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-indigo-600/10 border border-indigo-600/20">
                  <svg className="h-6 w-6 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                      d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                </div>
                <p className="text-sm font-medium text-slate-300">Run the optimizer to see recommendations</p>
                <p className="mt-1 text-xs text-slate-500">Or click a run in the history to view its results</p>
              </div>
            )}

            {selectedId && loadingSelected && (
              <div className="space-y-4">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-32 animate-pulse rounded-xl bg-slate-800/50" />
                ))}
              </div>
            )}

            {selectedRun && !loadingSelected && (
              <div className="space-y-4">
                {/* Run header */}
                <div className="rounded-xl border border-slate-700/50 bg-[#131c2e] p-5">
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <h2 className="font-semibold text-white">
                          {selectedRun.campaign_context
                            ? selectedRun.campaign_context.slice(0, 60)
                            : `Optimizer Run — ${selectedRun.run_date}`}
                        </h2>
                        <StatusBadge status={selectedRun.status} />
                      </div>
                      <p className="text-xs text-slate-400">
                        {selectedRun.run_date}
                        {selectedRun.notes && ` · ${selectedRun.notes}`}
                      </p>
                    </div>
                    {selectedRun.status === "COMPLETE" && (
                      <RequirePermission permission="ai_optimizer.approve">
                        <button
                          onClick={() => setShowApproveModal(true)}
                          className="rounded-lg border border-emerald-500/30 bg-emerald-600/10 px-3 py-1.5 text-xs font-medium text-emerald-400 hover:bg-emerald-600/20 transition-colors"
                        >
                          Approve
                        </button>
                      </RequirePermission>
                    )}
                    {selectedRun.status === "APPROVED" && (
                      <div className="text-xs text-slate-400">
                        Approved{selectedRun.approved_at && ` · ${selectedRun.approved_at.slice(0, 10)}`}
                      </div>
                    )}
                  </div>
                </div>

                {/* Input summary */}
                {selectedRun.input_summary && (
                  <InputSummaryPanel summary={selectedRun.input_summary} />
                )}

                {/* Recommendations */}
                {recs ? (
                  <RecommendationsPanel recs={recs} />
                ) : (
                  <div className="rounded-xl border border-slate-700/50 bg-[#131c2e] p-8 text-center">
                    <p className="text-sm text-slate-400">No recommendations in this run.</p>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Approve modal */}
        {showApproveModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
            <div className="w-full max-w-md rounded-xl border border-slate-700 bg-[#131c2e] p-6 shadow-2xl">
              <h3 className="mb-1 text-lg font-semibold text-white">Approve Recommendation</h3>
              <p className="mb-4 text-sm text-slate-400">
                Approving marks this optimizer run as validated for use. Add optional notes for the record.
              </p>
              <textarea
                value={approveNotes}
                onChange={(e) => setApproveNotes(e.target.value)}
                rows={3}
                placeholder="Approval notes (optional)…"
                className="mb-4 w-full resize-none rounded-lg border border-slate-700 bg-[#0b1120] px-3 py-2 text-sm text-white placeholder-slate-600 focus:border-emerald-500 focus:outline-none"
              />
              <div className="flex gap-3 justify-end">
                <button
                  onClick={() => setShowApproveModal(false)}
                  className="rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-300 hover:bg-slate-800 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={() => approveMut.mutate()}
                  disabled={approveMut.isPending}
                  className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-50 transition-colors"
                >
                  {approveMut.isPending ? "Approving…" : "Confirm Approve"}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </RequirePermission>
  );
}

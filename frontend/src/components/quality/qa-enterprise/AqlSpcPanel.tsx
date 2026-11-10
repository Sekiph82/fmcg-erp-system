"use client";

import { useState } from "react";
import { type AQLResult, type QCType, type SPCAnalysis, qaEnterpriseApi } from "@/lib/qa-enterprise";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { type Notify, ReadOnlyNotice, Section, statusVariant, useAction, useQualityPermissions } from "./shared";

const fmt = (v: number | null | undefined, digits = 3) => (v == null ? "—" : v.toFixed(digits));

function ControlChart({ analysis }: { analysis: SPCAnalysis }) {
  const points = analysis.points ?? [];
  const W = 640, H = 220, PAD = 32;
  const values = points.map((p) => p.value);
  const lines = [analysis.limits.ucl, analysis.limits.center, analysis.limits.lcl,
    ...(analysis.usl != null ? [analysis.usl] : []), ...(analysis.lsl != null ? [analysis.lsl] : [])];
  const lo = Math.min(...values, ...lines), hi = Math.max(...values, ...lines);
  const span = hi - lo || 1;
  const x = (i: number) => PAD + (i * (W - 2 * PAD)) / Math.max(points.length - 1, 1);
  const y = (v: number) => H - PAD - ((v - lo) / span) * (H - 2 * PAD);
  const flagged = new Set(analysis.violations.map((v) => v.index));
  const ref = (v: number | null, label: string, dash: string, cls: string) => v == null ? null : (
    <g key={label}>
      <line x1={PAD} x2={W - PAD} y1={y(v)} y2={y(v)} strokeDasharray={dash} className={cls} strokeWidth={1} />
      <text x={W - PAD + 2} y={y(v) + 3} className="fill-gray-500 text-[9px]">{label}</text>
    </g>
  );
  return (
    <svg role="img" aria-label={`Individuals control chart, ${points.length} points, ${analysis.violations.length} rule hits`}
      viewBox={`0 0 ${W + 30} ${H}`} className="w-full max-w-3xl">
      {ref(analysis.limits.ucl, "UCL", "4 3", "stroke-red-400")}
      {ref(analysis.limits.center, "CL", "", "stroke-gray-400")}
      {ref(analysis.limits.lcl, "LCL", "4 3", "stroke-red-400")}
      {ref(analysis.usl, "USL", "1 3", "stroke-amber-500")}
      {ref(analysis.lsl, "LSL", "1 3", "stroke-amber-500")}
      <polyline fill="none" className="stroke-indigo-500" strokeWidth={1.5}
        points={points.map((p, i) => `${x(i)},${y(p.value)}`).join(" ")} />
      {points.map((p, i) => (
        <circle key={p.test_result_id} cx={x(i)} cy={y(p.value)} r={flagged.has(i) ? 4.5 : 2.5}
          className={flagged.has(i) ? "fill-red-600" : "fill-indigo-500"}>
          <title>{`${p.value}${flagged.has(i) ? " — out of control" : ""}`}</title>
        </circle>
      ))}
    </svg>
  );
}

export function AqlSpcPanel({ notify }: { notify: Notify }) {
  const perms = useQualityPermissions();
  const [aql, setAql] = useState({ lot_size: "", applies_to: "INCOMING", sample_inspected: "", defects_found: "" });
  const [aqlResult, setAqlResult] = useState<AQLResult | null>(null);
  const [spc, setSpc] = useState({ product_id: "", parameter_name: "", qc_type: "" });
  const [chart, setChart] = useState<SPCAnalysis | null>(null);

  const evaluateAql = useAction(
    () => qaEnterpriseApi.evaluateAql({
      lot_size: Number(aql.lot_size), applies_to: aql.applies_to,
      sample_inspected: Number(aql.sample_inspected), defects_found: Number(aql.defects_found),
    }), notify, (r) => `AQL decision: ${r.decision}`, []);
  const spcParams = () => ({
    product_id: spc.product_id.trim(), parameter_name: spc.parameter_name.trim(),
    ...(spc.qc_type ? { qc_type: spc.qc_type as QCType } : {}),
  });
  const loadChart = useAction(() => qaEnterpriseApi.spcChart(spcParams()), notify,
    (a) => `${a.n} points, ${a.violations.length} rule hits`, []);
  const escalate = useAction(() => qaEnterpriseApi.spcEvaluate(spcParams()), notify,
    (r) => (r.new_signals ? `${r.new_signals} new signal(s); deviation opened` : "No new out-of-control signals"), []);

  if (!perms.canView) return <ReadOnlyNotice>AQL and SPC require quality.view.</ReadOnlyNotice>;

  return (
    <div className="space-y-4">
      <Section title="AQL lot decision" description="Picks the active sampling plan for the lot size (item-specific plans first) and applies its accept/reject numbers.">
        <form className="grid gap-3 md:grid-cols-5" onSubmit={(e) => { e.preventDefault(); evaluateAql.mutate(undefined, { onSuccess: setAqlResult }); }}>
          <Input id="aql-lot-size" label="Lot size" type="number" min={1} required value={aql.lot_size}
            onChange={(e) => setAql((a) => ({ ...a, lot_size: e.target.value }))} />
          <Select id="aql-applies" label="Inspection type" value={aql.applies_to}
            onChange={(e) => setAql((a) => ({ ...a, applies_to: e.target.value }))}
            options={["INCOMING", "IN_PROCESS", "FINISHED_GOODS"].map((v) => ({ value: v, label: v.replace("_", " ") }))} />
          <Input id="aql-sample" label="Units inspected" type="number" min={0} required value={aql.sample_inspected}
            onChange={(e) => setAql((a) => ({ ...a, sample_inspected: e.target.value }))} />
          <Input id="aql-defects" label="Defects found" type="number" min={0} required value={aql.defects_found}
            onChange={(e) => setAql((a) => ({ ...a, defects_found: e.target.value }))} />
          <div className="flex items-end">
            <Button type="submit" loading={evaluateAql.isPending}>Evaluate lot</Button>
          </div>
        </form>
        {aqlResult && (
          <div data-testid="aql-result" className="flex flex-wrap items-center gap-3 text-sm">
            <Badge label={aqlResult.decision.replace("_", " ")} variant={statusVariant(aqlResult.decision)} />
            <span>Plan {aqlResult.plan_code}: sample {aqlResult.sample_size}, Ac {aqlResult.acceptance_number ?? "—"}, Re {aqlResult.rejection_number ?? "—"}</span>
            {aqlResult.reason && <span className="text-gray-500">{aqlResult.reason}</span>}
          </div>
        )}
      </Section>

      <Section title="SPC control chart" description="Individuals chart from recorded numeric results with Western Electric rules 1–4. Pp/Ppk use overall sigma.">
        <form className="grid gap-3 md:grid-cols-4" onSubmit={(e) => { e.preventDefault(); loadChart.mutate(undefined, { onSuccess: setChart }); }}>
          <Input id="spc-product" label="Product ID" required value={spc.product_id}
            onChange={(e) => setSpc((s) => ({ ...s, product_id: e.target.value }))} />
          <Input id="spc-parameter" label="Parameter name" required value={spc.parameter_name}
            onChange={(e) => setSpc((s) => ({ ...s, parameter_name: e.target.value }))} />
          <Select id="spc-qc-type" label="Inspection type" value={spc.qc_type}
            onChange={(e) => setSpc((s) => ({ ...s, qc_type: e.target.value }))}
            options={[{ value: "", label: "All" }, ...["INCOMING", "IN_PROCESS", "FINISHED_GOODS", "RETEST"].map((v) => ({ value: v, label: v.replace("_", " ") }))]} />
          <div className="flex items-end gap-2">
            <Button type="submit" loading={loadChart.isPending} disabled={!spc.product_id || !spc.parameter_name}>Show chart</Button>
            {perms.canCreate && (
              <Button type="button" variant="secondary" loading={escalate.isPending} disabled={!spc.product_id || !spc.parameter_name}
                onClick={() => escalate.mutate(undefined, { onSuccess: (r) => setChart((c) => c ? { ...r.analysis, points: c.points } : r.analysis) })}>
                Record signals &amp; escalate
              </Button>
            )}
          </div>
        </form>
        {chart && (
          <div data-testid="spc-result" className="space-y-3">
            <dl className="grid grid-cols-2 gap-2 text-sm md:grid-cols-6">
              <div><dt className="text-gray-500">Points</dt><dd>{chart.n}</dd></div>
              <div><dt className="text-gray-500">Center</dt><dd>{fmt(chart.limits.center)}</dd></div>
              <div><dt className="text-gray-500">UCL</dt><dd>{fmt(chart.limits.ucl)}</dd></div>
              <div><dt className="text-gray-500">LCL</dt><dd>{fmt(chart.limits.lcl)}</dd></div>
              <div><dt className="text-gray-500">Pp</dt><dd>{fmt(chart.capability.pp, 2)}</dd></div>
              <div><dt className="text-gray-500">Ppk</dt><dd>{fmt(chart.capability.ppk, 2)}</dd></div>
            </dl>
            {chart.points && chart.points.length > 1 && <ControlChart analysis={chart} />}
            {chart.violations.length === 0 ? (
              <p className="text-sm text-green-700">No Western Electric rule violations.</p>
            ) : (
              <ul className="space-y-1 text-sm" aria-label="Rule violations">
                {chart.violations.map((v) => (
                  <li key={`${v.index}-${v.rule}`} className="text-red-700">Point {v.index + 1} ({v.value}): {v.rule.replaceAll("_", " ")}</li>
                ))}
              </ul>
            )}
          </div>
        )}
      </Section>
    </div>
  );
}

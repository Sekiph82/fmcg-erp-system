"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { gs1Api, statusColor, severityColor } from "@/lib/gs1";

function StatCard({ label, value, sub }: { label: string; value: number | string; sub?: string }) {
  return (
    <div className="bg-white border rounded-lg p-4">
      <p className="text-xs text-gray-500 uppercase tracking-wide">{label}</p>
      <p className="text-2xl font-bold text-gray-900 mt-1">{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
    </div>
  );
}

export default function GS1DashboardPage() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ["gs1-dashboard"], queryFn: gs1Api.getDashboard });

  const validator = useMutation({
    mutationFn: gs1Api.runLabelValidator,
    onSuccess: (r) => { qc.invalidateQueries({ queryKey: ["gs1-dashboard"] }); alert(`Label Validator ran — ${r.generated} recommendation(s) generated`); },
  });
  const optimizer = useMutation({
    mutationFn: gs1Api.runPackagingOptimizer,
    onSuccess: (r) => { qc.invalidateQueries({ queryKey: ["gs1-dashboard"] }); alert(`Packaging Optimizer ran — ${r.generated} recommendation(s) generated`); },
  });

  if (isLoading) return <div className="p-8 text-gray-400">Loading GS1 dashboard…</div>;
  if (!data) return null;

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">GS1 Barcode & Label Printing</h1>
          <p className="text-sm text-gray-500">Global product identification · SSCC pallet tracking · Label management</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => validator.mutate()}
            disabled={validator.isPending}
            className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
          >
            {validator.isPending ? "Running…" : "Run Label Validator"}
          </button>
          <button
            onClick={() => optimizer.mutate()}
            disabled={optimizer.isPending}
            className="px-3 py-1.5 text-sm bg-purple-600 text-white rounded hover:bg-purple-700 disabled:opacity-50"
          >
            {optimizer.isPending ? "Running…" : "Packaging Optimizer"}
          </button>
        </div>
      </div>

      {/* KPI Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-4">
        <StatCard label="Products Configured" value={data.total_products_configured} />
        <StatCard label="Total GTINs" value={data.total_gtins} />
        <StatCard label="Barcodes Generated" value={data.total_barcodes_generated} />
        <StatCard label="Labels Printed" value={data.total_labels_printed} />
        <StatCard label="SSCC Pallets" value={data.total_sscc_pallets} sub={`${data.active_sscc_pallets} active`} />
        <StatCard label="Print Jobs" value={data.total_print_jobs} sub={`${data.pending_print_jobs} pending`} />
        <StatCard label="Label Templates" value={data.total_label_templates} />
        <StatCard label="AI Alerts Pending" value={data.ai_recommendations_pending} />
      </div>

      {/* Recent Barcodes */}
      <div className="bg-white border rounded-lg overflow-hidden">
        <div className="px-4 py-3 border-b">
          <h2 className="text-sm font-medium text-gray-700">Recent Barcodes Generated</h2>
        </div>
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
            <tr>
              <th className="px-4 py-2 text-left">GTIN</th>
              <th className="px-4 py-2 text-left">Lot Number</th>
              <th className="px-4 py-2 text-left">Expiry</th>
              <th className="px-4 py-2 text-left">Type</th>
              <th className="px-4 py-2 text-left">GS1 AI String</th>
              <th className="px-4 py-2 text-left">Printed</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {data.recent_barcodes.length === 0 && (
              <tr><td colSpan={6} className="px-4 py-6 text-center text-gray-400">No barcodes generated yet</td></tr>
            )}
            {data.recent_barcodes.map((b) => (
              <tr key={b.id} className="hover:bg-gray-50">
                <td className="px-4 py-2 font-mono text-xs">{b.gtin}</td>
                <td className="px-4 py-2">{b.lot_number}</td>
                <td className="px-4 py-2 text-gray-500">{b.expiry_date || "—"}</td>
                <td className="px-4 py-2"><span className="px-2 py-0.5 bg-blue-50 text-blue-700 rounded text-xs">{b.barcode_type}</span></td>
                <td className="px-4 py-2 font-mono text-xs text-gray-500 max-w-xs truncate">{b.gs1_ai_string}</td>
                <td className="px-4 py-2">{b.is_printed ? <span className="text-green-600">✓</span> : <span className="text-gray-400">—</span>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Recent SSCC */}
      <div className="bg-white border rounded-lg overflow-hidden">
        <div className="px-4 py-3 border-b">
          <h2 className="text-sm font-medium text-gray-700">Recent SSCC Pallets</h2>
        </div>
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
            <tr>
              <th className="px-4 py-2 text-left">SSCC Code</th>
              <th className="px-4 py-2 text-left">Pallet ID</th>
              <th className="px-4 py-2 text-left">Status</th>
              <th className="px-4 py-2 text-left">Lots</th>
              <th className="px-4 py-2 text-left">Location</th>
              <th className="px-4 py-2 text-left">Created</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {data.recent_sscc.length === 0 && (
              <tr><td colSpan={6} className="px-4 py-6 text-center text-gray-400">No SSCC pallets yet</td></tr>
            )}
            {data.recent_sscc.map((p) => (
              <tr key={p.id} className="hover:bg-gray-50">
                <td className="px-4 py-2 font-mono text-xs">{p.sscc_code}</td>
                <td className="px-4 py-2 text-gray-700">{p.pallet_id || "—"}</td>
                <td className="px-4 py-2">
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${statusColor[p.status] ?? ""}`}>{p.status}</span>
                </td>
                <td className="px-4 py-2">{p.lot_count}</td>
                <td className="px-4 py-2 text-gray-500">{p.warehouse_location || "—"}</td>
                <td className="px-4 py-2 text-gray-400">{new Date(p.created_at).toLocaleDateString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

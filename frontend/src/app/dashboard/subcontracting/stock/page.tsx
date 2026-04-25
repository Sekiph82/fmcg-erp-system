"use client";
import { useQuery } from "@tanstack/react-query";
import { scApi, fmt } from "@/lib/subcontracting";

export default function SubcontractorStockPage() {
  const { data, isLoading } = useQuery({ queryKey: ["sc-stock"], queryFn: () => scApi.getStock() });

  const totalValue = (data ?? []).reduce((s, r) => s + Number(r.total_value ?? 0), 0);
  const totalBalance = (data ?? []).reduce((s, r) => s + Number(r.qty_balance), 0);

  const bySupplier = (data ?? []).reduce((acc, r) => {
    const k = r.supplier_id;
    if (!acc[k]) acc[k] = { name: r.supplier_name, rows: [] };
    acc[k].rows.push(r);
    return acc;
  }, {} as Record<string, { name: string; rows: typeof data }>);

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">Subcontractor Stock</h1>
          <p className="text-sm text-gray-500">Materials currently at external subcontractor locations</p>
        </div>
        <div className="flex gap-4 text-sm text-gray-600">
          <span>Total Balance: <strong>{fmt(totalBalance)}</strong></span>
          <span>Total Value: <strong>KES {fmt(totalValue, 0)}</strong></span>
        </div>
      </div>

      {isLoading && <div className="text-gray-400">Loading…</div>}

      {!isLoading && Object.keys(bySupplier).length === 0 && (
        <div className="text-center py-12 text-gray-400">
          No materials currently at subcontractor locations.
        </div>
      )}

      {Object.entries(bySupplier).map(([supId, { name, rows }]) => (
        <div key={supId} className="bg-white border border-gray-200 rounded-lg">
          <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
            <h2 className="font-semibold text-gray-800">{name}</h2>
            <span className="text-sm text-gray-500">
              {rows!.length} material(s) · KES {fmt(rows!.reduce((s, r) => s + Number(r.total_value ?? 0), 0), 0)}
            </span>
          </div>
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
              <tr>
                <th className="text-left px-4 py-2">Material</th>
                <th className="text-right px-4 py-2">Issued</th>
                <th className="text-right px-4 py-2">Returned</th>
                <th className="text-right px-4 py-2">Consumed</th>
                <th className="text-right px-4 py-2">Scrapped</th>
                <th className="text-right px-4 py-2 font-bold">Balance</th>
                <th className="text-right px-4 py-2">Unit Cost</th>
                <th className="text-right px-4 py-2">Value</th>
              </tr>
            </thead>
            <tbody>
              {rows!.map((r) => (
                <tr key={r.material_id} className="border-t border-gray-100 hover:bg-gray-50">
                  <td className="px-4 py-2">
                    <p className="font-medium">{r.material_name}</p>
                    <p className="text-xs text-gray-400 font-mono">{r.material_code}</p>
                  </td>
                  <td className="px-4 py-2 text-right">{fmt(r.qty_issued)} {r.uom}</td>
                  <td className="px-4 py-2 text-right text-gray-500">{fmt(r.qty_returned)}</td>
                  <td className="px-4 py-2 text-right text-gray-500">{fmt(r.qty_consumed)}</td>
                  <td className={`px-4 py-2 text-right ${Number(r.qty_scrapped) > 0 ? "text-red-500" : "text-gray-400"}`}>{fmt(r.qty_scrapped)}</td>
                  <td className={`px-4 py-2 text-right font-bold ${Number(r.qty_balance) > 0 ? "text-blue-700" : "text-gray-400"}`}>{fmt(r.qty_balance)}</td>
                  <td className="px-4 py-2 text-right text-gray-500">{r.unit_cost ? fmt(r.unit_cost) : "—"}</td>
                  <td className="px-4 py-2 text-right">{r.total_value ? `KES ${fmt(r.total_value, 0)}` : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import { warehousesApi } from "@/lib/warehouses";
import { useAuth } from "@/context/AuthContext";
import { tx, lx } from "@/lib/i18n/core";

type Links = Record<string, string | null>;

const LINKS: { key: string; label: string; help: string }[] = lx(() => [
  { key: "raw_material_warehouse_id", label: tx("Raw materials"), help: "Recipe materials are issued from here when the order names no source warehouse." },
  { key: "packaging_warehouse_id", label: tx("Packaging"), help: "Packaging materials (bottles, sachets, cartons) are issued from here." },
  { key: "wip_warehouse_id", label: tx("Semi-finished (WIP)"), help: "Semi-finished materials are issued from here." },
  { key: "finished_goods_warehouse_id", label: tx("Finished goods, ready to ship"), help: "Completed output is received here when the order names no target warehouse." },
]);

export default function ProductionWarehouseLinksPage() {
  const qc = useQueryClient();
  const { hasPermission } = useAuth();
  const canEdit = hasPermission("production.approve");
  const { data: links } = useQuery<Links>({
    queryKey: ["production-warehouse-links"],
    queryFn: async () => (await apiClient.get("/api/v1/production/warehouse-links")).data,
  });
  const { data: warehouses = [] } = useQuery({ queryKey: ["warehouses-all"], queryFn: () => warehousesApi.list(0, 200) });
  const [form, setForm] = useState<Links>({});
  useEffect(() => { if (links) setForm(links); }, [links]);
  const save = useMutation({
    mutationFn: async () => (await apiClient.put("/api/v1/production/warehouse-links", form)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["production-warehouse-links"] }),
  });

  return (
    <div className="p-4 md:p-6 space-y-4 max-w-3xl">
      <div>
        <h2 className="text-lg font-semibold">{tx("Warehouse links")}</h2>
        <p className="text-sm text-gray-500">
          {tx("Where production takes its materials from and where finished goods go. Completing an order moves the stock between these warehouses and books it in the ledger: materials and packaging into work in progress, then work in progress into finished goods.")}
        </p>
      </div>
      {LINKS.map((l) => (
        <label key={l.key} className="block border rounded-lg p-3 bg-white">
          <span className="text-sm font-medium">{l.label}</span>
          <span className="block text-xs text-gray-500 mb-2">{l.help}</span>
          <select
            className="w-full border rounded-lg px-3 py-2 text-sm"
            value={form[l.key] ?? ""}
            disabled={!canEdit}
            onChange={(e) => setForm((f) => ({ ...f, [l.key]: e.target.value || null }))}
          >
            <option value="">{tx("— not linked —")}</option>
            {warehouses.filter((w) => w.is_active).map((w) => (
              <option key={w.id} value={w.id}>{w.code} — {w.name}</option>
            ))}
          </select>
        </label>
      ))}
      {canEdit && (
        <div className="flex items-center gap-3">
          <button type="button" onClick={() => save.mutate()} disabled={save.isPending}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm disabled:opacity-50">
            {save.isPending ? tx("Saving…") : tx("Save links")}
          </button>
          {save.isSuccess && <span className="text-sm text-green-600">{tx("Saved.")}</span>}
          {save.isError && <span className="text-sm text-red-600">{tx("Could not save the links.")}</span>}
        </div>
      )}
    </div>
  );
}

"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { mfApi, TankOccupancy, TankStatus, QualityStatus, TANK_STATUS_COLORS, QUALITY_STATUS_COLORS } from "@/lib/materialFlow";

function TankCard({ tank, onUpdate }: { tank: TankOccupancy; onUpdate: (id: string, d: object) => void }) {
  const fillPct = tank.fill_pct ?? (tank.capacity_max ? (tank.quantity_current / tank.capacity_max) * 100 : 0);
  const barColor = fillPct >= 90 ? "bg-red-500" : fillPct >= 70 ? "bg-yellow-400" : "bg-emerald-400";

  return (
    <div className="bg-white rounded-lg border p-4 space-y-3">
      <div className="flex items-start justify-between">
        <div>
          <p className="font-semibold text-gray-900">{tank.tank_code}</p>
          <p className="text-xs text-gray-500">{tank.tank_name}</p>
        </div>
        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${TANK_STATUS_COLORS[tank.tank_status]}`}>
          {tank.tank_status.replace("_", " ")}
        </span>
      </div>

      <div>
        <div className="flex justify-between text-xs text-gray-500 mb-1">
          <span>{Number(tank.quantity_current).toLocaleString()} {tank.uom}</span>
          <span>{fillPct.toFixed(1)}%</span>
        </div>
        <div className="w-full bg-gray-100 rounded-full h-2">
          <div className={`h-2 rounded-full ${barColor}`} style={{ width: `${Math.min(fillPct, 100)}%` }} />
        </div>
        {tank.capacity_max && (
          <p className="text-xs text-gray-400 mt-0.5">Capacity: {Number(tank.capacity_max).toLocaleString()} {tank.uom}</p>
        )}
      </div>

      <div className="flex items-center justify-between">
        <span className={`text-xs px-2 py-0.5 rounded-full ${QUALITY_STATUS_COLORS[tank.quality_status]}`}>
          {tank.quality_status.replace("_", " ")}
        </span>
        <div className="flex gap-1">
          {tank.tank_status !== "QC_HOLD" && (
            <button
              onClick={() => onUpdate(tank.id, { tank_status: "QC_HOLD" as TankStatus, quality_status: "QC_HOLD" as QualityStatus })}
              className="text-xs text-orange-600 border border-orange-200 px-2 py-0.5 rounded hover:bg-orange-50"
            >QC Hold</button>
          )}
          {tank.tank_status === "QC_HOLD" && (
            <button
              onClick={() => onUpdate(tank.id, { tank_status: "IN_USE" as TankStatus, quality_status: "RELEASED" as QualityStatus })}
              className="text-xs text-green-600 border border-green-200 px-2 py-0.5 rounded hover:bg-green-50"
            >Release</button>
          )}
        </div>
      </div>

      {(tank.product_name || tank.material_name) && (
        <p className="text-xs text-gray-400 border-t pt-2">
          Contents: <span className="font-medium text-gray-600">{tank.product_name || tank.material_name}</span>
        </p>
      )}
    </div>
  );
}

export default function TanksPage() {
  const qc = useQueryClient();
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState({ tank_code: "", tank_name: "", uom: "KG", capacity_max: "" });

  const { data: tanks } = useQuery<TankOccupancy[]>({
    queryKey: ["mf-tanks"],
    queryFn: () => mfApi.listTanks(),
    refetchInterval: 15000,
  });

  const createTank = useMutation({
    mutationFn: () => mfApi.createTank({ ...form, capacity_max: form.capacity_max ? parseFloat(form.capacity_max) : undefined }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["mf-tanks"] });
      setShowAdd(false);
      setForm({ tank_code: "", tank_name: "", uom: "KG", capacity_max: "" });
    },
  });

  const updateTank = useMutation({
    mutationFn: ({ id, d }: { id: string; d: object }) => mfApi.updateTank(id, d),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["mf-tanks"] }),
  });

  const tankList = tanks || [];
  const inUse = tankList.filter((t) => t.tank_status === "IN_USE" || t.tank_status === "FULL").length;
  const qcHold = tankList.filter((t) => t.tank_status === "QC_HOLD").length;
  const empty = tankList.filter((t) => t.tank_status === "EMPTY").length;

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <a href="/dashboard/material-flow" className="text-sm text-indigo-600 hover:underline">← Dashboard</a>
          <h1 className="text-xl font-bold text-gray-900">Tank Occupancy</h1>
        </div>
        <button onClick={() => setShowAdd(true)} className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700">
          + Add Tank
        </button>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-4 gap-3">
        {[
          { label: "Total Tanks", value: tankList.length },
          { label: "In Use", value: inUse, color: "text-emerald-700" },
          { label: "QC Hold", value: qcHold, color: qcHold > 0 ? "text-orange-600" : "text-gray-700" },
          { label: "Empty", value: empty, color: "text-gray-600" },
        ].map((s) => (
          <div key={s.label} className="bg-white rounded-lg border p-3 text-center">
            <p className="text-xs text-gray-500">{s.label}</p>
            <p className={`text-2xl font-bold ${s.color || "text-gray-900"}`}>{s.value}</p>
          </div>
        ))}
      </div>

      {/* Tanks Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {tankList.map((t) => (
          <TankCard key={t.id} tank={t} onUpdate={(id, d) => updateTank.mutate({ id, d })} />
        ))}
        {tankList.length === 0 && (
          <p className="col-span-4 text-sm text-gray-400 py-8 text-center">No tanks configured. Add one to start tracking occupancy.</p>
        )}
      </div>

      {/* Add Tank Modal */}
      {showAdd && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl p-6 w-96 space-y-4">
            <h2 className="font-bold text-gray-900">Add Tank / Container</h2>
            {[
              { label: "Tank Code", field: "tank_code", placeholder: "TANK-001" },
              { label: "Tank Name", field: "tank_name", placeholder: "Bulk Storage Tank 1" },
              { label: "Capacity (max)", field: "capacity_max", placeholder: "5000" },
            ].map(({ label, field, placeholder }) => (
              <div key={field}>
                <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
                <input
                  type={field === "capacity_max" ? "number" : "text"}
                  value={(form as Record<string, string>)[field]}
                  onChange={(e) => setForm((p) => ({ ...p, [field]: e.target.value }))}
                  placeholder={placeholder}
                  className="w-full border rounded px-3 py-2 text-sm"
                />
              </div>
            ))}
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">UOM</label>
              <select value={form.uom} onChange={(e) => setForm((p) => ({ ...p, uom: e.target.value }))} className="w-full border rounded px-3 py-2 text-sm">
                {["KG", "L", "MT", "PCS"].map((u) => <option key={u}>{u}</option>)}
              </select>
            </div>
            <div className="flex gap-2 justify-end pt-2">
              <button onClick={() => setShowAdd(false)} className="px-4 py-2 text-sm text-gray-600 border rounded-lg hover:bg-gray-50">Cancel</button>
              <button onClick={() => createTank.mutate()} disabled={!form.tank_code || !form.tank_name} className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50">
                {createTank.isPending ? "Adding…" : "Add Tank"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

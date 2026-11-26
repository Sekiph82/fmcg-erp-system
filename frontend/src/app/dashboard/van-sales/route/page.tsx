"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { vanSalesApi, VISIT_STATUS_COLORS } from "@/lib/van_sales";
import { positionFix, type Fix } from "@/lib/field";
import { VanOutbox } from "@/components/van-sales/VanOutbox";
import Link from "next/link";
import { tx } from "@/lib/i18n/core";

const errText = (e: unknown) => {
  const d = (e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  return typeof d === "string" ? d : Array.isArray(d) ? d.map((x) => (x as { msg?: string }).msg).join("; ") : (e as Error)?.message ?? "Request failed";
};
const noFixText = (f: Fix) => "error" in f && f.error === "denied"
  ? "Location permission is blocked for this site. Allow location in the browser settings to check in with GPS."
  : "Your location could not be found (no GPS signal or timeout). Move to open sky and try again.";

/** Start / end of the signed-in rep's working day, with GPS (van_rep_day_logs). */
function DayLog({ today, visitsDone }: { today: string; visitsDone: number }) {
  const { data: logs = [], refetch } = useQuery({ queryKey: ["rep-day-log", today], queryFn: () => vanSalesApi.myDayLogs(today) });
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const log = logs[0];
  const mut = useMutation({
    mutationFn: async (kind: "start" | "end") => {
      const f = await positionFix();
      const gps = "error" in f ? {} : kind === "start" ? { start_gps_lat: f.lat, start_gps_lng: f.lng } : { end_gps_lat: f.lat, end_gps_lng: f.lng };
      await vanSalesApi.saveDayLog({ log_date: today, [`${kind}_time`]: new Date().toISOString(), ...gps, ...(kind === "end" ? { total_visits: visitsDone } : {}) });
      return f;
    },
    onSuccess: (f, kind) => { setMsg("error" in f ? { ok: false, text: `Day ${kind} saved without location. ${noFixText(f)}` } : { ok: true, text: `Day ${kind} saved with location (±${f.accuracy} m).` }); refetch(); },
    onError: (e) => setMsg({ ok: false, text: errText(e) }),
  });
  return (
    <div className="glow-card p-4 flex flex-wrap items-center gap-3 text-sm">
      <span className="font-medium text-white">{tx("My day")}</span>
      <span className="text-slate-400">{log?.start_time ? `Started ${new Date(log.start_time + "Z").toLocaleTimeString()}${log.start_gps_lat != null ? " · GPS" : ""}` : tx("Not started")}
        {log?.end_time ? ` · Ended ${new Date(log.end_time + "Z").toLocaleTimeString()}` : ""}</span>
      {!log?.start_time && <button onClick={() => mut.mutate("start")} disabled={mut.isPending} className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium disabled:opacity-50">{tx("Start day")}</button>}
      {log?.start_time && !log.end_time && <button onClick={() => mut.mutate("end")} disabled={mut.isPending} className="px-3 py-1.5 rounded-lg border border-white/[0.15] text-slate-200 text-xs disabled:opacity-50">{tx("End day")}</button>}
      {msg && <p role={msg.ok ? "status" : "alert"} className={`w-full text-xs ${msg.ok ? "text-emerald-400" : "text-amber-300"}`}>{msg.text}</p>}
    </div>
  );
}

export default function RouteExecutionPage() {
  const qc = useQueryClient();
  const today = new Date().toISOString().split("T")[0];
  const [selectedVanId, setSelectedVanId] = useState("");
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [noGps, setNoGps] = useState<string | null>(null);  // visit id whose check-in could not get a GPS fix

  const { data: vans = [] } = useQuery({ queryKey: ["vans"], queryFn: () => vanSalesApi.listVans({ status: "ACTIVE" }) });
  const { data: visits = [], refetch } = useQuery({
    queryKey: ["visits", selectedVanId, today],
    queryFn: () => vanSalesApi.listVisits(selectedVanId, today),
    enabled: !!selectedVanId,
  });

  const checkInMut = useMutation({
    // GPS is required unless the user explicitly checks in without it after a failed fix
    mutationFn: async ({ id, withoutGps }: { id: string; withoutGps?: boolean }) => {
      if (withoutGps) return vanSalesApi.checkIn(id, {});
      const f = await positionFix();
      if ("error" in f) { setNoGps(id); throw new Error(noFixText(f)); }
      return vanSalesApi.checkIn(id, { gps_lat: f.lat, gps_lng: f.lng, gps_accuracy_m: f.accuracy });
    },
    onSuccess: (v) => { setNoGps(null); setMsg({ ok: true, text: v.gps_lat != null ? `Checked in with location (±${v.gps_accuracy_m ?? "?"} m).` : "Checked in without location." }); refetch(); },
    onError: (e) => setMsg({ ok: false, text: errText(e) }),
  });
  const photoMut = useMutation({
    mutationFn: ({ id, file }: { id: string; file: File }) => vanSalesApi.uploadVisitPhoto(id, file),
    onSuccess: () => { setMsg({ ok: true, text: tx("Outlet photo saved.") }); refetch(); },
    onError: (e) => setMsg({ ok: false, text: errText(e) }),
  });
  const checkOutMut = useMutation({
    mutationFn: (id: string) => vanSalesApi.checkOut(id),
    onSuccess: () => refetch(),
  });
  const missedMut = useMutation({
    mutationFn: (id: string) => vanSalesApi.markMissed(id, "Customer unavailable"),
    onSuccess: () => refetch(),
  });

  const completed = visits.filter((v) => v.status === "COMPLETED").length;
  const missed = visits.filter((v) => v.status === "MISSED").length;
  const remaining = visits.filter((v) => v.status === "PLANNED").length;

  return (
    <div className="p-6 space-y-5 text-slate-200">
      <div>
        <h1 className="text-xl font-bold text-white">{tx("Route Execution")}</h1>
        <p className="text-slate-500 text-sm mt-0.5">{today} {tx("— Visit tracking")}</p>
      </div>

      <DayLog today={today} visitsDone={visits.filter((v) => v.status === "COMPLETED").length} />
      {msg && <p role={msg.ok ? "status" : "alert"} className={`text-sm rounded-lg border p-3 ${msg.ok ? "border-emerald-500/30 text-emerald-300" : "border-red-500/30 text-red-300"}`}>{msg.text}</p>}

      <div>
        <label className="text-xs text-slate-400 mb-1 block">{tx("Select Van / Driver")}</label>
        <select value={selectedVanId} onChange={(e) => setSelectedVanId(e.target.value)}
          className="bg-[#0d1829] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500 w-64">
          <option value="">{tx("Select van…")}</option>
          {vans.map((v) => <option key={v.id} value={v.id}>{v.van_code} — {v.plate_number ?? tx("no plate")}</option>)}
        </select>
      </div>

      {selectedVanId && (
        <>
          <VanOutbox vanId={selectedVanId} />
          {/* Progress */}
          <div className="grid grid-cols-3 gap-4">
            <div className="glow-card p-4 text-center">
              <p className="text-2xl font-bold text-emerald-400">{completed}</p>
              <p className="text-xs text-slate-500 mt-0.5">{tx("Completed")}</p>
            </div>
            <div className="glow-card p-4 text-center">
              <p className="text-2xl font-bold text-amber-400">{remaining}</p>
              <p className="text-xs text-slate-500 mt-0.5">{tx("Remaining")}</p>
            </div>
            <div className="glow-card p-4 text-center">
              <p className="text-2xl font-bold text-red-400">{missed}</p>
              <p className="text-xs text-slate-500 mt-0.5">{tx("Missed")}</p>
            </div>
          </div>

          {/* Visit list */}
          <div className="space-y-2">
            {visits.sort((a, b) => (a.sequence_no ?? 99) - (b.sequence_no ?? 99)).map((v) => (
              <div key={v.id} className="glow-card p-4">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className="w-7 h-7 rounded-full bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-xs text-indigo-300 font-bold">
                      {v.sequence_no ?? "?"}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-white font-mono">{v.customer_id.slice(0, 8)}…</p>
                      <p className="text-xs text-slate-500">{v.planned_time ? new Date(v.planned_time).toLocaleTimeString() : tx("No scheduled time")}</p>
                    </div>
                  </div>
                  <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${VISIT_STATUS_COLORS[v.status]}`}>{v.status}</span>
                </div>

                {v.status === "PLANNED" && (
                  <div className="flex gap-2">
                    <button onClick={() => checkInMut.mutate({ id: v.id })} disabled={checkInMut.isPending}
                      className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium disabled:opacity-50">
                      {checkInMut.isPending && checkInMut.variables?.id === v.id ? tx("Getting location…") : tx("Check In")}
                    </button>
                    {noGps === v.id && <button onClick={() => checkInMut.mutate({ id: v.id, withoutGps: true })} disabled={checkInMut.isPending}
                      className="px-3 py-1.5 rounded-lg border border-amber-500/40 text-amber-300 text-xs">
                      {tx("Check in without location")}
                    </button>}
                    <button onClick={() => missedMut.mutate(v.id)}
                      className="px-3 py-1.5 rounded-lg border border-red-500/40 text-red-400 hover:bg-red-500/10 text-xs">
                      {tx("Mark Missed")}
                    </button>
                  </div>
                )}
                {v.status === "CHECKED_IN" && (
                  <div className="flex gap-2">
                    <Link href={`/dashboard/van-sales/pos?van_id=${selectedVanId}`}
                      className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium">
                      {tx("Create Sale")}
                    </Link>
                    <button onClick={() => checkOutMut.mutate(v.id)}
                      className="px-3 py-1.5 rounded-lg border border-white/[0.08] text-slate-400 hover:border-white/20 text-xs">
                      {tx("Check Out")}
                    </button>
                  </div>
                )}
                {(v.status === "CHECKED_IN" || v.status === "COMPLETED") && (
                  <label className="block text-xs text-slate-400 mt-2">
                    {tx("Outlet photo")} {v.outlet_photo_url ? tx("· saved (replace)") : tx("(optional)")}
                    <input type="file" accept="image/jpeg,image/png" capture="environment" aria-label={tx("Outlet photo")} disabled={photoMut.isPending}
                      onChange={(e) => { const f = e.target.files?.[0]; if (f) photoMut.mutate({ id: v.id, file: f }); e.target.value = ""; }}
                      className="mt-1 block w-full text-xs" />
                  </label>
                )}
                {v.check_in_time && (
                  <p className="text-xs text-slate-600 mt-2">
                    {tx("In:")} {new Date(v.check_in_time).toLocaleTimeString()}
                    {v.check_out_time && ` · Out: ${new Date(v.check_out_time).toLocaleTimeString()}`}
                  </p>
                )}
              </div>
            ))}
            {visits.length === 0 && (
              <div className="text-center py-10 text-slate-600">{tx("No visits planned for today on this van.")}</div>
            )}
          </div>
        </>
      )}
    </div>
  );
}

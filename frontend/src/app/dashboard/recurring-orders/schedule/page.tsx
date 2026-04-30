"use client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { subscriptionApi } from "@/lib/subscription";

export default function SchedulePage() {
  const qc = useQueryClient();
  const { data: templates = [] } = useQuery({
    queryKey: ["sub-templates-active"],
    queryFn: () => subscriptionApi.listTemplates({ status: "ACTIVE", limit: 100 }),
  });

  const schedulerMut = useMutation({
    mutationFn: () => subscriptionApi.runScheduler(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["sub-templates-active"] }),
  });

  // Build calendar view for next 8 weeks
  const today = new Date();
  const weeks: Date[][] = [];
  let current = new Date(today);
  current.setDate(current.getDate() - current.getDay()); // start of week
  for (let w = 0; w < 8; w++) {
    const week: Date[] = [];
    for (let d = 0; d < 7; d++) {
      week.push(new Date(current));
      current.setDate(current.getDate() + 1);
    }
    weeks.push(week);
  }

  const templatesByDate: Record<string, typeof templates> = {};
  templates.forEach((t) => {
    if (t.next_generation_date) {
      if (!templatesByDate[t.next_generation_date]) templatesByDate[t.next_generation_date] = [];
      templatesByDate[t.next_generation_date].push(t);
    }
  });

  const fmtDate = (d: Date) => d.toISOString().split("T")[0];

  return (
    <div className="p-6 space-y-5 text-slate-200">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Generation Calendar</h1>
          <p className="text-slate-500 text-sm mt-0.5">Upcoming recurring order generation schedule</p>
        </div>
        <button
          onClick={() => schedulerMut.mutate()}
          disabled={schedulerMut.isPending}
          className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium disabled:opacity-50"
        >
          {schedulerMut.isPending ? "Running…" : "Run Scheduler Now"}
        </button>
      </div>

      {schedulerMut.data && (
        <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm text-emerald-300">
          Scheduler: {schedulerMut.data.generated} generated · {schedulerMut.data.skipped} skipped · {schedulerMut.data.failed} failed
        </div>
      )}

      {/* Calendar grid */}
      <div className="glow-card p-4 overflow-x-auto">
        <div className="grid grid-cols-7 gap-1 min-w-[700px]">
          {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((d) => (
            <div key={d} className="text-center text-[10px] text-slate-500 uppercase pb-2">{d}</div>
          ))}
          {weeks.flat().map((day) => {
            const dateStr = fmtDate(day);
            const events = templatesByDate[dateStr] ?? [];
            const isToday = dateStr === fmtDate(today);
            return (
              <div key={dateStr}
                className={`min-h-[80px] rounded-lg p-1.5 border ${
                  isToday ? "border-indigo-500/60 bg-indigo-500/10" : "border-white/[0.04] bg-white/[0.02]"
                }`}>
                <p className={`text-xs mb-1 font-medium ${isToday ? "text-indigo-300" : "text-slate-500"}`}>
                  {day.getDate()}
                </p>
                {events.map((t) => (
                  <div key={t.id}
                    className="text-[9px] px-1 py-0.5 rounded bg-emerald-500/20 text-emerald-300 mb-0.5 truncate"
                    title={t.template_name}>
                    {t.template_code}
                  </div>
                ))}
              </div>
            );
          })}
        </div>
      </div>

      {/* Template list with next dates */}
      <div className="glow-card p-5">
        <h2 className="text-sm font-semibold text-white mb-4">Active Templates — Next Generation Dates</h2>
        <table className="w-full text-sm">
          <thead className="text-slate-500 text-xs uppercase tracking-wider">
            <tr>
              <th className="px-4 py-2 text-left">Code</th>
              <th className="px-4 py-2 text-left">Name</th>
              <th className="px-4 py-2 text-left">Next Date</th>
              <th className="px-4 py-2 text-left">Last Generated</th>
              <th className="px-4 py-2 text-left">Mode</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/[0.04]">
            {templates
              .filter((t) => t.next_generation_date)
              .sort((a, b) => (a.next_generation_date! < b.next_generation_date! ? -1 : 1))
              .map((t) => {
                const daysUntil = Math.ceil(
                  (new Date(t.next_generation_date!).getTime() - today.getTime()) / 86400000
                );
                return (
                  <tr key={t.id} className="hover:bg-white/[0.02]">
                    <td className="px-4 py-2 font-mono text-indigo-300 text-xs">{t.template_code}</td>
                    <td className="px-4 py-2 text-white">{t.template_name}</td>
                    <td className="px-4 py-2">
                      <span className={`text-xs font-medium ${daysUntil < 0 ? "text-red-400" : daysUntil <= 3 ? "text-amber-400" : "text-slate-300"}`}>
                        {t.next_generation_date}
                        <span className="ml-1 text-slate-600">({daysUntil < 0 ? `${Math.abs(daysUntil)}d overdue` : daysUntil === 0 ? "today" : `in ${daysUntil}d`})</span>
                      </span>
                    </td>
                    <td className="px-4 py-2 text-slate-500 text-xs">{t.last_generation_date ?? "—"}</td>
                    <td className="px-4 py-2 text-xs text-slate-400">{t.generation_mode.replace(/_/g, " ")}</td>
                  </tr>
                );
              })}
            {templates.length === 0 && (
              <tr><td colSpan={5} className="text-center py-6 text-slate-600">No active templates</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

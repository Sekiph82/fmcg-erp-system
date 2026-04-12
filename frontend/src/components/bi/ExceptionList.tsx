"use client";
import { useRouter } from "next/navigation";
import { ExceptionRow } from "@/lib/analytics";

const SEV_COLORS: Record<string, string> = {
  critical: "bg-red-500/20 text-red-400 border-red-500/30",
  high:     "bg-orange-500/20 text-orange-400 border-orange-500/30",
  medium:   "bg-amber-500/20 text-amber-400 border-amber-500/30",
  low:      "bg-slate-500/20 text-slate-400 border-slate-500/30",
};

const SEV_DOT: Record<string, string> = {
  critical: "bg-red-500",
  high:     "bg-orange-500",
  medium:   "bg-amber-500",
  low:      "bg-slate-500",
};

export function ExceptionList({ items, title = "Exceptions" }: { items: ExceptionRow[]; title?: string }) {
  const router = useRouter();
  if (!items.length) return (
    <div className="rounded-xl border border-white/[0.06] p-4">
      <p className="text-xs font-medium text-slate-500 uppercase tracking-widest mb-3">{title}</p>
      <p className="text-sm text-slate-600">No exceptions</p>
    </div>
  );

  return (
    <div className="rounded-xl border border-white/[0.06] p-4">
      <p className="text-xs font-medium text-slate-500 uppercase tracking-widest mb-3">{title}</p>
      <div className="space-y-2">
        {items.map(item => (
          <button
            key={item.id}
            onClick={() => router.push(item.href)}
            className="w-full flex items-start gap-3 rounded-lg border border-white/[0.04] bg-white/[0.02] px-3 py-2.5 hover:bg-white/[0.05] text-left transition-colors"
          >
            <span className={`mt-0.5 h-2 w-2 rounded-full shrink-0 ${SEV_DOT[item.severity] ?? "bg-slate-500"}`} />
            <div className="min-w-0 flex-1">
              <p className="text-[13px] text-slate-300 leading-snug">{item.label}</p>
              <p className="text-[11px] text-slate-600 mt-0.5">{item.detail}</p>
            </div>
            <span className={`shrink-0 text-[10px] px-1.5 py-0.5 rounded border font-medium uppercase ${SEV_COLORS[item.severity] ?? SEV_COLORS.low}`}>
              {item.severity}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}

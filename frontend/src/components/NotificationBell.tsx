"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { disablePush, enablePush, pushState } from "@/lib/webPush";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import { apiClient } from "@/lib/api";
import { tx } from "@/lib/i18n/core";

interface NCNotif {
  notification_id: string;
  title: string;
  message: string;
  notification_type: string;
  priority: string;
  module: string | null;
  read_flag: boolean;
  created_at: string;
}

const POLL_MS = 60_000;

function fmtRelative(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

const PRIORITY_DOT: Record<string, string> = {
  critical: "bg-red-500",
  high: "bg-orange-400",
  normal: "bg-blue-400",
  low: "bg-gray-400",
};

interface Props {
  /** compact=true → icon only (no label), for collapsed sidebar or mobile bar */
  compact?: boolean;
}

export function NotificationBell({ compact = false }: Props) {
  const { user } = useAuth();
  const userId = (user as { id?: string; user_id?: string } | null)?.id ?? (user as { id?: string; user_id?: string } | null)?.user_id ?? "";

  const [count, setCount] = useState(0);
  const [open, setOpen] = useState(false);
  const [notifs, setNotifs] = useState<NCNotif[]>([]);
  const [loading, setLoading] = useState(false);
  const [marking, setMarking] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const fetchCount = useCallback(async () => {
    if (!userId) return;
    try {
      const { data } = await apiClient.get<{ unread_count?: number }>("/api/v1/notifications/me/unread-count");
      setCount(data.unread_count ?? 0);
    } catch {}
  }, [userId]);

  const fetchNotifs = useCallback(async () => {
    if (!userId) return;
    setLoading(true);
    try {
      const { data } = await apiClient.get<NCNotif[]>("/api/v1/notifications/me", { params: { read_flag: false, limit: 8 } });
      setNotifs(data);
    } catch {}
    setLoading(false);
  }, [userId]);

  // Poll unread count
  useEffect(() => {
    fetchCount();
    const timer = setInterval(fetchCount, POLL_MS);
    return () => clearInterval(timer);
  }, [fetchCount]);

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const toggle = () => {
    if (!open) fetchNotifs();
    setOpen((p) => !p);
  };

  const markOne = async (id: string) => {
    await apiClient.post(`/api/v1/notifications/me/${id}/read`);
    setNotifs((prev) => prev.filter((n) => n.notification_id !== id));
    setCount((c) => Math.max(0, c - 1));
  };

  const markAll = async () => {
    if (!userId) return;
    setMarking(true);
    try {
      await apiClient.post("/api/v1/notifications/me/read-all");
      setNotifs([]);
      setCount(0);
    } finally {
      setMarking(false);
    }
  };

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={toggle}
        title={tx("Notifications")}
        className={[
          "relative flex items-center justify-center rounded-md transition-colors",
          compact
            ? "h-7 w-7 text-slate-500 hover:bg-white/[0.07] hover:text-slate-300"
            : "h-8 w-8 text-slate-400 hover:bg-white/10",
        ].join(" ")}
        aria-label={tx("Notifications")}
      >
        <svg
          className={compact ? "h-[14px] w-[14px]" : "h-[17px] w-[17px]"}
          fill="none" stroke="currentColor" viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75}
            d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
          />
        </svg>
        {count > 0 && (
          <span className="absolute -top-0.5 -right-0.5 min-w-[14px] h-[14px] flex items-center justify-center rounded-full bg-red-500 text-[9px] font-bold text-white px-0.5 leading-none">
            {count > 99 ? "99+" : count}
          </span>
        )}
      </button>

      {open && (
        <div
          className={[
            "absolute z-[9999] w-[320px] rounded-xl shadow-2xl border border-white/[0.1]",
            "bg-[#0d1b2e] text-slate-200 overflow-hidden",
            compact
              ? "bottom-full mb-2 left-0"
              : "top-full mt-2 right-0",
          ].join(" ")}
          style={{ boxShadow: "0 8px 32px rgba(0,0,0,0.6)" }}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-white/[0.08]">
            <span className="text-[13px] font-semibold text-slate-100">
              {tx("Notifications")}
              {count > 0 && (
                <span className="ml-2 bg-red-500/20 text-red-400 text-[10px] font-bold rounded-full px-1.5 py-0.5">
                  {count} {tx("unread")}
                </span>
              )}
            </span>
            <div className="flex items-center gap-2">
              {count > 0 && (
                <button
                  onClick={markAll}
                  disabled={marking}
                  className="text-[11px] text-cyan-400 hover:text-cyan-300 disabled:opacity-50"
                >
                  {marking ? tx("Clearing…") : tx("Mark all read")}
                </button>
              )}
            </div>
          </div>

          {/* Body */}
          <div className="max-h-[320px] overflow-y-auto">
            {loading ? (
              <div className="px-4 py-6 text-center text-slate-500 text-xs">{tx("Loading…")}</div>
            ) : notifs.length === 0 ? (
              <div className="px-4 py-6 text-center">
                <p className="text-slate-400 text-sm">{tx("All caught up!")}</p>
                <p className="text-slate-600 text-xs mt-1">{tx("No unread notifications")}</p>
              </div>
            ) : (
              <div className="divide-y divide-white/[0.05]">
                {notifs.map((n) => (
                  <div key={n.notification_id} className="flex items-start gap-3 px-4 py-3 hover:bg-white/[0.04] transition-colors">
                    <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${PRIORITY_DOT[n.priority] ?? "bg-gray-400"}`} />
                    <div className="flex-1 min-w-0">
                      <p className="text-[12px] font-medium text-slate-200 leading-snug truncate">{n.title}</p>
                      <p className="text-[11px] text-slate-500 mt-0.5 line-clamp-2">{n.message}</p>
                      <p className="text-[10px] text-slate-600 mt-1">{fmtRelative(n.created_at)}</p>
                    </div>
                    <button
                      onClick={() => markOne(n.notification_id)}
                      className="shrink-0 text-[10px] text-slate-600 hover:text-cyan-400 mt-0.5"
                      title={tx("Mark as read")}
                    >
                      ✓
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          <PushToggle />
          {/* Footer */}
          <div className="px-4 py-2.5 border-t border-white/[0.08]">
            <Link
              href="/dashboard/notification-center"
              onClick={() => setOpen(false)}
              className="block text-center text-[11px] text-cyan-400 hover:text-cyan-300"
            >
              {tx("View all notifications →")}
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}


// "Notify me on this phone" (M37.S03.T001): Web Push for the installed app.
function PushToggle() {
  const [state, setState] = useState<"unsupported" | "denied" | "on" | "off" | "busy">("off");
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => { pushState().then(setState).catch(() => setState("unsupported")); }, []);
  if (state === "unsupported") return null;
  const flip = async () => {
    setErr(null);
    const was = state; setState("busy");
    try { if (was === "on") { await disablePush(); setState("off"); } else { await enablePush(); setState("on"); } }
    catch (e) { setErr((e as Error).message); setState(await pushState().catch(() => "off" as const)); }
  };
  return (
    <div className="px-4 py-2 border-t border-white/[0.08] text-[11px]">
      {state === "denied" ? <p className="text-slate-400">{tx("Phone notifications are blocked in this browser's settings.")}</p> : (
        <button onClick={flip} disabled={state === "busy"} className="text-cyan-400 hover:text-cyan-300 disabled:opacity-50">
          {state === "on" ? tx("Stop notifications on this device") : tx("Notify me on this device")}
        </button>)}
      {err && <p className="text-red-400 mt-1">{err}</p>}
    </div>
  );
}

"use client";
// M45.S01.T023 always-visible banner while a support person acts as another user.
import { useEffect, useState } from "react";
import { apiClient } from "@/lib/api";
import { tx } from "@/lib/i18n/core";

type Status = { active: boolean; actor?: string; target?: string; expires_at?: string };

export function ImpersonationBanner() {
  const [s, setS] = useState<Status>({ active: false });
  useEffect(() => {
    const check = () => apiClient.get("/api/v1/impersonation/status").then((r) => setS(r.data)).catch(() => setS({ active: false }));
    check();
    const t = setInterval(check, 30000);
    return () => clearInterval(t);
  }, []);
  if (!s.active) return null;
  // a full reload is required: the signed-in identity changes, so every cached user/permission must be dropped
  // eslint-disable-next-line @next/next/no-location-assign-relative-destination
  const end = () => apiClient.post("/api/v1/impersonation/end").finally(() => window.location.assign("/dashboard"));
  return (
    <div role="alert" className="sticky top-0 z-50 bg-red-700 text-white text-sm px-4 py-2 flex flex-wrap items-center justify-between gap-2">
      <span><b>{s.actor}</b> {tx("is acting as")} <b>{s.target}</b> {tx("until")} {s.expires_at ? new Date(s.expires_at).toLocaleTimeString() : "—"}{tx(". Everything you do is logged under both names.")}</span>
      <button className="bg-white text-red-700 rounded px-3 py-0.5 font-semibold" onClick={end}>{tx("End session")}</button>
    </div>
  );
}

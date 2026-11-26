"use client";
// Shows a one-time partner set-password link once, with copy, after an invite or a password reset.
import { useState } from "react";
import { tx } from "@/lib/i18n/core";

export function AccessLinkNotice({ link, who, onClose }: { link: string; who: string; onClose: () => void }) {
  const [copied, setCopied] = useState(false);
  return (
    <div role="status" className="rounded-xl border border-amber-300 bg-amber-50 p-3 text-sm space-y-2">
      <p className="font-medium text-amber-900">{tx("One-time sign-in link for")} {who}</p>
      <p className="text-xs text-amber-800">{tx("Send it to this person only (e-mail or WhatsApp). It works once and expires in 7 days; it is not shown again.")}</p>
      <div className="flex gap-2">
        <input readOnly aria-label={tx("Set-password link")} value={link} className="flex-1 min-w-0 border rounded-lg px-2 py-1 text-xs bg-white" onFocus={(e) => e.target.select()} />
        <button onClick={() => navigator.clipboard?.writeText(link).then(() => setCopied(true))} className="px-3 py-1 rounded-lg bg-amber-600 text-white text-xs">{copied ? tx("Copied") : tx("Copy")}</button>
        <button onClick={onClose} className="px-2 text-xs text-amber-900 underline">{tx("Done")}</button>
      </div>
    </div>
  );
}

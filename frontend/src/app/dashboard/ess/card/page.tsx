"use client";
// M42.S02.T003 — the employee's own digital business card: view, open, share and download the QR code.
import Link from "next/link";
import { BusinessCardPanel } from "@/components/BusinessCardPanel";
import { tx } from "@/lib/i18n/core";

export default function MyBusinessCardPage() {
  return (
    <div className="space-y-4 max-w-3xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">{tx("My business card")}</h1>
          <p className="text-sm text-slate-500">{tx("Show the QR code or share the link; anyone can save your work contact from it.")}</p>
        </div>
        <Link href="/dashboard/ess" className="text-sm text-indigo-600 hover:underline">{tx("My HR")}</Link>
      </div>
      <div className="bg-white text-gray-900 border rounded-lg p-4">
        <BusinessCardPanel />
      </div>
    </div>
  );
}

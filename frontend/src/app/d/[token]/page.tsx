"use client";
// Public shared quotation (no login, M36.S03.T001). The view is recorded by this page after it renders,
// not by opening the URL, so mail scanners that pre-fetch links do not count as views.
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { API_ORIGIN } from "@/lib/api";

interface Line { description: string; sku: string | null; qty: string; unit: string; unit_price: string | null; discount_pct: string; tax_rate: string; line_total: string | null }
interface Doc {
  number: string; version: number; status: string; customer: string | null; quote_date: string; valid_until: string | null;
  currency: string; discount_pct: string; total_amount: string | null; tax_amount: string | null; grand_total: string | null;
  notes: string | null; lines: Line[]; link_expires_at: string;
}

const money = (v: string | null, c: string) => (v == null ? "—" : `${c} ${Number(v).toLocaleString(undefined, { minimumFractionDigits: 2 })}`);

export default function SharedDocumentPage() {
  const token = String(useParams().token ?? "");
  const [doc, setDoc] = useState<Doc | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const url = `${API_ORIGIN}/api/v1/public/documents/${encodeURIComponent(token)}`;
    fetch(url)
      .then(async (r) => {
        if (!r.ok) { setError("This link is not available. Ask your POVU contact for a new one."); return; }
        setDoc(await r.json());
        fetch(`${url}/view`, { method: "POST" }).catch(() => undefined);
      })
      .catch(() => setError("Please try again later."));
  }, [token]);

  return (
    <main className="min-h-screen bg-white text-gray-900 p-4 sm:p-8">
      <div className="max-w-3xl mx-auto space-y-5">
        {error ? <p role="alert" className="text-sm text-red-700">{error}</p> : !doc ? <p className="text-sm text-gray-500">Loading…</p> : (
          <>
            <header className="flex flex-wrap justify-between gap-2 border-b pb-3">
              <div>
                <p className="text-xs uppercase tracking-wide text-gray-500">Quotation</p>
                <h1 className="text-xl font-bold">{doc.number}{doc.version > 1 ? ` (v${doc.version})` : ""}</h1>
                {doc.customer && <p className="text-sm text-gray-600">For {doc.customer}</p>}
              </div>
              <div className="text-sm text-gray-600 sm:text-right">
                <p>Date: {doc.quote_date}</p>
                {doc.valid_until && <p>Valid until: {doc.valid_until}</p>}
              </div>
            </header>
            <ul className="sm:hidden divide-y border-y text-sm">
              {doc.lines.map((l, i) => (
                <li key={i} className="py-2">
                  <p className="font-medium">{l.description}{l.sku && <span className="ml-1 text-xs text-gray-500">{l.sku}</span>}</p>
                  <p className="flex justify-between text-gray-600">
                    <span>{l.qty} {l.unit} × {money(l.unit_price, doc.currency)}{Number(l.discount_pct) > 0 ? ` −${l.discount_pct}%` : ""}</span>
                    <span className="font-medium text-gray-900">{money(l.line_total, doc.currency)}</span>
                  </p>
                </li>
              ))}
            </ul>
            <div className="hidden sm:block">
              <table className="w-full text-sm">
                <thead><tr className="text-left text-xs text-gray-500 border-b"><th className="py-2">Item</th><th className="text-right">Qty</th><th className="text-right">Unit price</th><th className="text-right hidden sm:table-cell">Disc %</th><th className="text-right">Total</th></tr></thead>
                <tbody>
                  {doc.lines.map((l, i) => (
                    <tr key={i} className="border-b">
                      <td className="py-2 pr-2 min-w-[9rem]">{l.description}{l.sku && <span className="block text-xs text-gray-500">{l.sku}</span>}</td>
                      <td className="text-right whitespace-nowrap">{l.qty} {l.unit}</td>
                      <td className="text-right whitespace-nowrap pl-2">{money(l.unit_price, doc.currency)}{Number(l.discount_pct) > 0 && <span className="block text-xs text-gray-500 sm:hidden">−{l.discount_pct}%</span>}</td>
                      <td className="text-right hidden sm:table-cell">{l.discount_pct}</td>
                      <td className="text-right whitespace-nowrap pl-2">{money(l.line_total, doc.currency)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="text-sm space-y-1 sm:w-72 sm:ml-auto">
              {Number(doc.discount_pct) > 0 && <p className="flex justify-between"><span>Overall discount</span><span>{doc.discount_pct}%</span></p>}
              <p className="flex justify-between"><span>Subtotal</span><span>{money(doc.total_amount, doc.currency)}</span></p>
              <p className="flex justify-between"><span>Tax</span><span>{money(doc.tax_amount, doc.currency)}</span></p>
              <p className="flex justify-between font-bold text-base border-t pt-1"><span>Total</span><span>{money(doc.grand_total, doc.currency)}</span></p>
            </div>
            {doc.notes && <p className="text-sm whitespace-pre-wrap border-t pt-3">{doc.notes}</p>}
            <p className="text-xs text-gray-400">This private link works until {new Date(doc.link_expires_at).toLocaleDateString()}.</p>
          </>
        )}
      </div>
    </main>
  );
}

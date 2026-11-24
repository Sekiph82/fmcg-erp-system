"use client";
/* eslint-disable @next/next/no-img-element -- blob/data URLs and the shared brand host; next/image adds nothing here */
// M42 bulk business cards: every employee's card (created automatically), QR ZIP, and a print sheet
// (85×55 mm cards, 10 per A4; fronts first, then backs with columns swapped for duplex printing).
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { RequirePermission } from "@/components/PermissionGuard";
import { Modal } from "@/components/ui/Modal";
import { BusinessCardPanel } from "@/components/BusinessCardPanel";
import { cardsApi, download, type CardRow } from "@/lib/businessCards";
import { extractApiError } from "@/lib/sales";

function chunk<T>(a: T[], n: number): T[][] {
  const out: T[][] = [];
  for (let i = 0; i < a.length; i += n) out.push(a.slice(i, i + n));
  return out;
}

function Front({ c }: { c: CardRow }) {
  return (
    <div className="bc bc-front">
      <img src={`${c.assets_base}/logo.webp`} alt="Povu" className="bc-logo" />
      <div>
        <p className="bc-name">{c.name}</p>
        <p className="bc-title">{c.title_en || c.role}</p>
      </div>
      <div className="bc-contact">
        {c.phone && <p>{c.phone}</p>}
        {c.email && <p>{c.email}</p>}
        <p>www.povu.com</p>
      </div>
    </div>
  );
}

function Back({ c, qr }: { c: CardRow; qr?: string }) {
  return (
    <div className="bc bc-back">
      {qr ? <img src={qr} alt="" className="bc-qr" /> : <span className="bc-qr" />}
      <p className="bc-scan">Scan to save my contact</p>
      <p className="bc-url">{c.url.replace(/^https?:\/\//, "")}</p>
    </div>
  );
}

function CardsContent() {
  const [department, setDepartment] = useState("");
  const [status, setStatus] = useState("");
  const [search, setSearch] = useState("");
  const [open, setOpen] = useState<CardRow | null>(null);
  const [printing, setPrinting] = useState<{ rows: CardRow[]; qr: Record<string, string> } | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const filter = { department: department || undefined, status: status || undefined, search: search || undefined };
  const { data: rows = [], isLoading } = useQuery({ queryKey: ["business-cards", filter], queryFn: () => cardsApi.list(filter) });
  const { data: all = [] } = useQuery({ queryKey: ["business-cards", "all"], queryFn: () => cardsApi.list({}) });
  const departments = useMemo(() => Array.from(new Set(all.map((r) => r.department))).sort(), [all]);
  const live = rows.filter((r) => r.live);

  const zip = async () => {
    setErr(null);
    try { download(await cardsApi.qrZip({ department: filter.department, search: filter.search }), "business-card-qr-codes.zip"); }
    catch (e) { setErr(extractApiError(e)); }
  };
  const print = async () => {
    setErr(null);
    try {
      const qr: Record<string, string> = {};
      for (const r of live) qr[r.employee_id] = await cardsApi.qr(r.employee_id, "svg");
      setPrinting({ rows: live, qr });
      window.setTimeout(() => window.print(), 600);
    } catch (e) { setErr(extractApiError(e)); }
  };

  return (
    <div className="space-y-4">
      <style>{PRINT_CSS}</style>
      <div className="flex flex-wrap items-center justify-between gap-2 no-print">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Business cards</h1>
          <p className="text-sm text-gray-500 mt-1">
            Every employee gets a card and QR code automatically. {live.length} live of {rows.length} shown.
          </p>
        </div>
        <div className="flex gap-2">
          <Link href="/dashboard/hr/employees" className="px-3 py-2 border rounded text-sm">Employees</Link>
          <button type="button" onClick={zip} disabled={!live.length} className="px-3 py-2 border rounded text-sm disabled:opacity-50">QR codes (ZIP)</button>
          <button type="button" onClick={print} disabled={!live.length} className="px-3 py-2 rounded text-sm bg-indigo-600 text-white disabled:opacity-50">Print cards</button>
        </div>
      </div>

      <div className="flex flex-wrap gap-3 no-print">
        <input aria-label="Search name or code" placeholder="Search name or code..." value={search} onChange={(e) => setSearch(e.target.value)} className="border rounded px-3 py-2 text-sm w-56" />
        <select aria-label="Department" value={department} onChange={(e) => setDepartment(e.target.value)} className="border rounded px-3 py-2 text-sm">
          <option value="">All departments</option>
          {departments.map((d) => <option key={d}>{d}</option>)}
        </select>
        <select aria-label="Card status" value={status} onChange={(e) => setStatus(e.target.value)} className="border rounded px-3 py-2 text-sm">
          <option value="">All cards</option>
          <option value="PUBLISHED">Published</option>
          <option value="REVOKED">Closed</option>
        </select>
      </div>
      {err && <p role="alert" className="text-sm text-red-600 no-print">{err}</p>}

      <div className="bg-white border rounded-lg overflow-x-auto no-print">
        {isLoading ? <p className="p-6 text-sm text-gray-400 text-center">Loading...</p> : rows.length === 0 ? (
          <p className="p-6 text-sm text-gray-400 text-center">No cards found</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-xs text-gray-500 uppercase">
                <th className="px-4 py-2 text-left">Name</th><th className="px-4 py-2 text-left">Title</th>
                <th className="px-4 py-2 text-left">Department</th><th className="px-4 py-2 text-left">Card</th>
                <th className="px-4 py-2 text-left">Photo</th><th className="px-4 py-2 text-left">Address</th><th />
              </tr>
            </thead>
            <tbody className="divide-y">
              {rows.map((r) => (
                <tr key={r.card_id}>
                  <td className="px-4 py-3 font-medium text-gray-900">{r.name}</td>
                  <td className="px-4 py-3 text-gray-600">{r.title_en || r.role}</td>
                  <td className="px-4 py-3 text-gray-600">{r.department}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded text-xs ${r.live ? "bg-emerald-100 text-emerald-800" : "bg-red-100 text-red-700"}`}>{r.live ? "Live" : "Closed"}</span>
                  </td>
                  <td className="px-4 py-3 text-gray-600">{r.has_photo ? "Yes" : "—"}</td>
                  <td className="px-4 py-3 text-xs text-gray-500">/kartvizit/{r.slug}</td>
                  <td className="px-4 py-3 text-right"><button type="button" onClick={() => setOpen(r)} className="text-xs text-indigo-600 hover:underline">Manage</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <Modal open={!!open} onClose={() => setOpen(null)} title={open ? `Business card — ${open.name}` : ""}>
        {open && <BusinessCardPanel employeeId={open.employee_id} />}
      </Modal>

      {printing && (
        <div className="print-sheet" aria-hidden="true">
          {chunk(printing.rows, 10).map((page, n) => (
            <div key={`f${n}`} className="sheet">{page.map((c) => <Front key={c.card_id} c={c} />)}</div>
          ))}
          {chunk(printing.rows, 10).map((page, n) => (
            // backs: swap the two columns of each row so they line up with the fronts when printed on both sides
            <div key={`b${n}`} className="sheet">
              {chunk(page, 2).flatMap((pair) => [pair[1], pair[0]]).map((c, i) => c ? <Back key={c.card_id} c={c} qr={printing.qr[c.employee_id]} /> : <div key={`e${i}`} className="bc bc-empty" />)}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

const PRINT_CSS = `
.print-sheet{display:none}
.bc{width:85mm;height:55mm;border:0.2mm dashed #bbb;padding:5mm;box-sizing:border-box;font-family:"Plus Jakarta Sans",system-ui,sans-serif;color:#0e1620;background:#fff;overflow:hidden}
.bc-front{display:flex;flex-direction:column;justify-content:space-between}
.bc-logo{height:9mm;width:auto;align-self:flex-start}
.bc-name{margin:0;font-size:13pt;font-weight:800}
.bc-title{margin:0;font-size:8.5pt;color:#1670b8;font-weight:600}
.bc-contact p{margin:0;font-size:7.5pt;line-height:1.35}
.bc-back{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:1mm}
.bc-qr{width:32mm;height:32mm;display:block}
.bc-scan{margin:0;font-size:8pt;font-weight:700}
.bc-url{margin:0;font-size:6.5pt;color:#555;word-break:break-all;text-align:center}
@media print{
  @page{size:A4;margin:12mm 15mm}
  body *{visibility:hidden}
  .print-sheet,.print-sheet *{visibility:visible}
  .print-sheet{display:block;position:absolute;left:0;top:0}
  .sheet{display:grid;grid-template-columns:repeat(2,85mm);grid-auto-rows:55mm;gap:0;break-after:page}
  .no-print{display:none!important}
}
`;

export default function BusinessCardsPage() {
  return (
    <RequirePermission permission="hr.cards_manage">
      <CardsContent />
    </RequirePermission>
  );
}

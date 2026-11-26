"use client";
// The signed-in employee's own payslips (approved / paid payroll runs only).
import { useEffect, useState } from "react";
import { essSelf, type Payslip } from "@/lib/ess";
import { tx } from "@/lib/i18n/core";

const kes = (n: number) => `KES ${n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

export default function MyPayslips() {
  const [rows, setRows] = useState<Payslip[] | null>(null);
  const [open, setOpen] = useState<string | null>(null);
  const [error, setError] = useState("");
  useEffect(() => { essSelf.payslips().then(setRows).catch((e) => setError(e.message)); }, []);

  return (
    <div className="p-4 sm:p-6 space-y-4 text-slate-200">
      <div>
        <h1 className="text-xl font-bold text-white">{tx("My payslips")}</h1>
        <p className="text-slate-500 text-sm">{tx("Only you can see these. Payslips appear once the payroll for the month is approved.")}</p>
      </div>
      {error && <p role="alert" className="rounded-xl border border-amber-500/20 bg-amber-500/10 p-3 text-sm text-amber-300">{error}</p>}
      {rows && rows.length === 0 && <p className="text-sm text-slate-500">{tx("No payslips yet.")}</p>}
      <div className="space-y-2">
        {(rows ?? []).map((p) => (
          <div key={p.id} className="glow-card p-4">
            <button className="w-full flex justify-between text-left" aria-expanded={open === p.id} onClick={() => setOpen(open === p.id ? null : p.id)}>
              <span><span className="font-semibold text-white">{p.period}</span><span className="block text-xs text-slate-500">{tx("issued")} {p.issue_date}</span></span>
              <span className="text-right"><span className="block text-emerald-400 font-semibold">{kes(p.net)}</span><span className="text-xs text-slate-500">{tx("net pay")}</span></span>
            </button>
            {open === p.id && (
              <table className="w-full text-sm mt-3"><tbody>
                {([["Gross pay", p.gross], ["PAYE", -p.paye], ["SHIF / NHIF", -p.nhif], ["NSSF", -p.nssf], ["Housing levy", -p.housing_levy], ["Net pay", p.net]] as [string, number][]).map(([k, v]) => (
                  <tr key={k} className="border-t border-white/[0.06]"><td className="py-1.5 text-slate-400">{k}</td><td className={`py-1.5 text-right ${v < 0 ? "text-red-300" : "text-white"}`}>{kes(v)}</td></tr>))}
              </tbody></table>)}
            {open === p.id && <button onClick={() => window.print()} className="mt-2 text-xs underline text-slate-400">{tx("Print")}</button>}
          </div>))}
      </div>
    </div>
  );
}

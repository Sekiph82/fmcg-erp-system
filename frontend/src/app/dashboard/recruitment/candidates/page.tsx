"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { recruitmentApi, Candidate, CandidateSource } from "@/lib/recruitment";

const SOURCES: CandidateSource[] = ["portal", "referral", "agency", "manual", "linkedin", "job_portal"];

export default function CandidatesPage() {
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [search, setSearch] = useState("");
  const [source, setSource] = useState("");
  const [debounced, setDebounced] = useState("");

  useEffect(() => { const t = setTimeout(() => setDebounced(search), 300); return () => clearTimeout(t); }, [search]);
  useEffect(() => {
    recruitmentApi.listCandidates({ search: debounced || undefined, source: source || undefined })
      .then(setCandidates).catch(console.error);
  }, [debounced, source]);

  return (
    <div className="p-6 space-y-5 text-slate-200">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Candidates</h1>
          <p className="text-slate-500 text-sm mt-0.5">{candidates.length} candidates</p>
        </div>
        <Link href="/dashboard/recruitment/candidates/new"
          className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium">+ Add Candidate</Link>
      </div>

      <div className="flex gap-3">
        <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search name, email, skills…"
          className="bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500 w-64" />
        <select value={source} onChange={(e) => setSource(e.target.value)}
          className="bg-[#0d1829] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white focus:outline-none">
          <option value="">All Sources</option>
          {SOURCES.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>

      <div className="glass-table">
        <table className="w-full text-sm">
          <thead><tr className="border-b border-white/[0.07]">
            {["Code", "Name", "Email", "Source", "Current Title", "Exp (yrs)", "Skills"].map((h) => (
              <th key={h} className="px-4 py-3 text-[10px] text-slate-500 uppercase tracking-widest text-left">{h}</th>
            ))}
          </tr></thead>
          <tbody>
            {candidates.map((c) => (
              <tr key={c.candidate_id} className="border-b border-white/[0.05] hover:bg-white/[0.02]">
                <td className="px-4 py-3 font-mono text-xs">
                  <Link href={`/dashboard/recruitment/candidates/${c.candidate_id}`} className="text-indigo-400 hover:text-indigo-300">{c.candidate_code}</Link>
                </td>
                <td className="px-4 py-3 text-white font-medium">{c.full_name}</td>
                <td className="px-4 py-3 text-slate-400">{c.email}</td>
                <td className="px-4 py-3"><span className="text-[10px] bg-slate-500/20 text-slate-400 px-2 py-0.5 rounded-full">{c.source}</span></td>
                <td className="px-4 py-3 text-slate-400">{c.current_title || "—"}</td>
                <td className="px-4 py-3 text-slate-400 text-center">{c.years_experience ?? "—"}</td>
                <td className="px-4 py-3 text-slate-500 text-xs max-w-[150px] truncate">{c.skills_tags || "—"}</td>
              </tr>
            ))}
            {candidates.length === 0 && <tr><td colSpan={7} className="px-4 py-8 text-center text-slate-600">No candidates found</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}

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

  useEffect(() => {
    const t = setTimeout(() => setDebounced(search), 300);
    return () => clearTimeout(t);
  }, [search]);

  useEffect(() => {
    recruitmentApi.listCandidates({ search: debounced || undefined, source: source || undefined })
      .then(setCandidates).catch(console.error);
  }, [debounced, source]);

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">Candidates</h1>
        <Link href="/dashboard/recruitment/candidates/new"
          className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700">+ Add Candidate</Link>
      </div>

      <div className="flex gap-3">
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search name, email, skills…"
          className="border rounded px-3 py-2 text-sm w-64"
        />
        <select value={source} onChange={(e) => setSource(e.target.value)} className="border rounded px-3 py-2 text-sm">
          <option value="">All Sources</option>
          {SOURCES.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>

      <div className="bg-white rounded-xl border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs uppercase text-gray-500">
            <tr>
              <th className="px-4 py-3 text-left">Code</th>
              <th className="px-4 py-3 text-left">Name</th>
              <th className="px-4 py-3 text-left">Email</th>
              <th className="px-4 py-3 text-left">Source</th>
              <th className="px-4 py-3 text-left">Current Title</th>
              <th className="px-4 py-3 text-left">Exp (yrs)</th>
              <th className="px-4 py-3 text-left">Skills</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {candidates.map((c) => (
              <tr key={c.candidate_id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-mono text-xs">
                  <Link href={`/dashboard/recruitment/candidates/${c.candidate_id}`}
                    className="text-blue-600 hover:underline">{c.candidate_code}</Link>
                </td>
                <td className="px-4 py-3 font-medium">{c.full_name}</td>
                <td className="px-4 py-3 text-gray-600">{c.email}</td>
                <td className="px-4 py-3 capitalize text-xs">
                  <span className="bg-gray-100 px-2 py-0.5 rounded-full">{c.source}</span>
                </td>
                <td className="px-4 py-3 text-gray-500">{c.current_title || "—"}</td>
                <td className="px-4 py-3 text-center">{c.years_experience ?? "—"}</td>
                <td className="px-4 py-3 text-xs text-gray-400 max-w-[150px] truncate">{c.skills_tags || "—"}</td>
              </tr>
            ))}
            {candidates.length === 0 && (
              <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400">No candidates found</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

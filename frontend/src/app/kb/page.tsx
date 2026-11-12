"use client";
// Public help centre (no login): published articles marked public by an editor with publish rights.
import { useEffect, useState } from "react";
import Link from "next/link";
import { API_ORIGIN } from "@/lib/api";

interface Hit { slug: string; title: string; summary: string | null }

export default function HelpCentre() {
  const [q, setQ] = useState("");
  const [hits, setHits] = useState<Hit[] | null>(null);

  useEffect(() => {
    const t = setTimeout(() => {
      fetch(`${API_ORIGIN}/api/v1/public/kb/search?q=${encodeURIComponent(q)}`)
        .then((r) => (r.ok ? r.json() : []))
        .then(setHits)
        .catch(() => setHits([]));
    }, 250);
    return () => clearTimeout(t);
  }, [q]);

  return (
    <main className="min-h-screen bg-white text-gray-900 p-6">
      <div className="max-w-2xl mx-auto space-y-4">
        <h1 className="text-2xl font-bold">Help centre</h1>
        <input aria-label="Search help articles" placeholder="Search…" value={q} onChange={(e) => setQ(e.target.value)} maxLength={100}
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
        {hits === null ? <p className="text-sm text-gray-500">Loading…</p> : hits.length === 0 ? (
          <p className="text-sm text-gray-500">No articles found.</p>
        ) : (
          <ul className="divide-y">
            {hits.map((h) => (
              <li key={h.slug} className="py-3">
                <Link href={`/kb/${h.slug}`} className="font-medium text-indigo-700 hover:underline">{h.title}</Link>
                {h.summary && <p className="text-sm text-gray-600">{h.summary}</p>}
              </li>
            ))}
          </ul>
        )}
      </div>
    </main>
  );
}

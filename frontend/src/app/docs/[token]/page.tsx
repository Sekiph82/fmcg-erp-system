"use client";
// Public shared sales document (M45.S01.T013): no login; the token is the only credential.
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { API_ORIGIN } from "@/lib/api";

type Meta = { title: string; version: number; file_name: string | null; size_bytes: number | null; sha256: string | null; available: boolean; note: string | null; expires_at: string };

export default function SharedDoc() {
  const { token } = useParams<{ token: string }>();
  const url = `${API_ORIGIN}/api/v1/public/docs/${encodeURIComponent(token)}`;
  const [m, setM] = useState<Meta | null>(null);
  const [gone, setGone] = useState<string | null>(null);
  useEffect(() => {
    fetch(url).then(async (r) => {
      const j = await r.json().catch(() => ({}));
      if (!r.ok) { setGone(typeof j.detail === "string" ? j.detail : "This link is not valid."); return; }
      setM(j);
      fetch(`${url}/view`, { method: "POST" }).catch(() => undefined);   // recorded only once the page rendered
    }).catch(() => setGone("This link is not valid."));
  }, [url]);
  return (
    <main className="min-h-screen bg-gray-50 flex items-start justify-center p-4">
      <div className="w-full max-w-md bg-white rounded-xl border shadow-sm p-5 space-y-3 text-sm">
        <h1 className="text-lg font-semibold">POVU document</h1>
        {gone ? <p className="text-red-600">{gone}</p> : !m ? <p className="text-gray-500">Loading…</p> : <>
          <p className="font-medium">{m.title} <span className="text-gray-500">(version {m.version})</span></p>
          <p className="text-xs text-gray-500">{m.file_name}{m.size_bytes ? ` · ${(m.size_bytes / 1024).toFixed(0)} KB` : ""} · available until {new Date(m.expires_at).toLocaleDateString()}</p>
          {m.sha256 && <p className="text-xs text-gray-500 break-all">SHA-256: {m.sha256}</p>}
          {m.available ? <a className="block text-center bg-indigo-600 text-white rounded py-2 font-semibold" href={`${url}/file`}>Download</a>
            : <p className="text-amber-700 text-xs">{m.note}</p>}
        </>}
      </div>
    </main>
  );
}

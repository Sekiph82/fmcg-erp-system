"use client";
// Public 1-to-1 video message (M47.S01.T009): no login; the token is the only credential. A view is recorded once playback starts.
import { useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { API_ORIGIN } from "@/lib/api";

type Meta = { title: string; contact_name: string | null; mime: string; expires_at: string };

export default function VideoMessage() {
  const { token } = useParams<{ token: string }>();
  const url = `${API_ORIGIN}/api/v1/public/video/${encodeURIComponent(token)}`;
  const [m, setM] = useState<Meta | null>(null);
  const [gone, setGone] = useState<string | null>(null);
  const sent = useRef(false);
  useEffect(() => {
    fetch(url).then(async (r) => {
      const j = await r.json().catch(() => ({}));
      if (!r.ok) { setGone(typeof j.detail === "string" ? j.detail : "This link is not valid."); return; }
      setM(j);
    }).catch(() => setGone("This link is not valid."));
  }, [url]);
  const view = (seconds: number) => fetch(`${url}/view`, { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ seconds: Math.round(seconds) }) }).catch(() => undefined);
  return (
    <main className="min-h-screen bg-gray-50 flex items-start justify-center p-4">
      <div className="w-full max-w-xl bg-white rounded-xl border shadow-sm p-5 space-y-3 text-sm">
        {gone ? <p className="text-red-600">{gone}</p> : !m ? <p className="text-gray-500">Loading…</p> : <>
          <h1 className="text-lg font-semibold">{m.title}</h1>
          {m.contact_name && <p className="text-gray-600">For {m.contact_name}</p>}
          <video className="w-full rounded" controls playsInline src={`${url}/file`}
            onPlay={() => { if (!sent.current) { sent.current = true; view(0); } }}
            onPause={(e) => view(e.currentTarget.currentTime)} />
          <p className="text-xs text-gray-500">Available until {new Date(m.expires_at).toLocaleDateString()}.</p>
        </>}
      </div>
    </main>
  );
}

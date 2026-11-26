"use client";
// M47.S01.T011 point-and-click event tagging: open the website with ?povu_tagger=1, click an element to get its CSS
// selector, then map it here to a defined custom event. The website script sends that event when the element is clicked.
import { useEffect, useState } from "react";
import { apiClient } from "@/lib/api";

type Tag = { selector: string; event: string };

export default function EventTags({ events }: { events: string[] }) {
  const [tags, setTags] = useState<Tag[]>([]);
  const [f, setF] = useState<Tag>({ selector: "", event: "" });
  const [msg, setMsg] = useState<string | null>(null);
  useEffect(() => { apiClient.get("/api/v1/web-analytics/tags").then((r) => setTags(r.data)).catch(() => setTags([])); }, []);
  const save = (next: Tag[]) => apiClient.put("/api/v1/web-analytics/tags", next).then((r) => { setTags(r.data); setMsg("Saved."); })
    .catch((e) => setMsg((e as { response?: { data?: { detail?: string } } }).response?.data?.detail ?? "Could not save."));
  return (
    <details className="border rounded p-3 bg-white"><summary className="font-semibold cursor-pointer">Event tags (point and click)</summary>
      <p className="text-xs text-gray-500 mt-2">Open any page of your website with <code>?povu_tagger=1</code> added to the address, click the button or link you want to measure and copy the selector it shows. Then map it to a defined event here. Clicks are only counted for visitors who accepted analytics.</p>
      {msg && <p role="status" className="text-xs">{msg}</p>}
      <div className="flex flex-wrap gap-2 text-xs my-2">
        <input aria-label="CSS selector" placeholder="#order-now or a.btn-primary" className="border rounded px-1 flex-1 min-w-[12rem]" value={f.selector} onChange={(e) => setF({ ...f, selector: e.target.value })} />
        <select aria-label="Event" className="border rounded" value={f.event} onChange={(e) => setF({ ...f, event: e.target.value })}><option value="">event…</option>{events.map((n) => <option key={n}>{n}</option>)}</select>
        <button className="border rounded px-2" disabled={!f.selector || !f.event} onClick={() => { save([...tags, f]); setF({ selector: "", event: "" }); }}>Add tag</button>
      </div>
      <ul className="text-xs divide-y">{tags.map((t, i) => <li key={i} className="py-1 flex justify-between gap-2"><code className="break-all">{t.selector}</code><span>→ {t.event} <button className="text-red-600 ml-2" onClick={() => save(tags.filter((_, j) => j !== i))}>Remove</button></span></li>)}</ul>
    </details>
  );
}

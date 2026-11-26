"use client";
// M49.S01.T004: queues + agent presence board, callbacks, transfer, dispositions, carrier capability matrix.
// Only SUPPORTED capabilities are enabled; everything else is disabled with the carrier's reason.
import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/lib/api";
import { tx, lx } from "@/lib/i18n/core";

type Cap = { state: "SUPPORTED" | "UNSUPPORTED" | "UNVERIFIED"; reason: string | null };
interface Caps { provider: string | null; matrix: Record<string, Cap> }
interface Agent { user_id: string; name: string; status: string; since: string }
interface Queue { id: string; name: string; direction: string; strategy: string; overflow: string; max_wait_seconds: number; waiting: number; oldest_wait_seconds: number; member_user_ids: string[] }
interface Callback { id: string; phone_number: string; missed_count: number; attempts: number; last_outcome: string | null }
interface Live { id: string; call_ref: string; phone_number: string; direction: string; status: string | null; provider: string | null }
interface Transfer { id: string; kind: string; state: string; to_number: string; error: string | null }

const LABELS: Record<string, string> = lx(() => ({
  outbound_call: tx("Outbound calls"), inbound_ivr: tx("Inbound IVR"), queue_hold: tx("Hold in queue"), recording: tx("Recording (with consent)"),
  voicemail: tx("Voicemail"), cold_transfer: tx("Cold transfer"), warm_transfer: tx("Warm transfer"), signature_verification: tx("Webhook signature"),
}));
const DISPOSITIONS = ["SALE", "QUOTE_REQUESTED", "COMPLAINT", "WRONG_NUMBER", "NO_INTEREST", "CALLBACK_REQUESTED", "ESCALATED"];
const PRESENCE_STYLE: Record<string, string> = { AVAILABLE: "bg-green-100 text-green-700", BUSY: "bg-red-100 text-red-700", AWAY: "bg-amber-100 text-amber-700", OFFLINE: "bg-gray-100 text-gray-600" };

const detail = (e: unknown, fb: string) => {
  const d = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
  return typeof d === "string" ? d : fb;
};

export function ContactCenterPanel() {
  const [caps, setCaps] = useState<Caps | null>(null);
  const [board, setBoard] = useState<{ agents: Agent[]; queues: Queue[] }>({ agents: [], queues: [] });
  const [callbacks, setCallbacks] = useState<Callback[]>([]);
  const [live, setLive] = useState<Live[]>([]);
  const [msg, setMsg] = useState<string | null>(null);
  const [newCb, setNewCb] = useState("");
  const [q, setQ] = useState({ name: "", direction: "INBOUND", strategy: "LONGEST_IDLE", overflow: "CALLBACK", max_wait_seconds: 60, members: [] as string[] });
  const [tr, setTr] = useState({ call: "", kind: "COLD", user: "", number: "" });
  const [transfers, setTransfers] = useState<Transfer[]>([]);
  const [disp, setDisp] = useState({ call: "", code: "SALE", note: "" });

  const load = useCallback(() => {
    apiClient.get("/api/v1/calls/cc/capabilities").then((r) => setCaps(r.data)).catch(() => setCaps(null));
    apiClient.get("/api/v1/calls/cc/board").then((r) => setBoard(r.data)).catch(() => undefined);
    apiClient.get("/api/v1/calls/cc/callbacks").then((r) => setCallbacks(r.data)).catch(() => setCallbacks([]));
    apiClient.get("/api/v1/calls/logs", { params: { limit: 20 } }).then((r) => setLive(r.data)).catch(() => setLive([]));
  }, []);
  useEffect(() => { load(); const t = setInterval(load, 15000); return () => clearInterval(t); }, [load]);
  useEffect(() => {
    if (!tr.call) { setTransfers([]); return; }
    apiClient.get(`/api/v1/calls/cc/calls/${tr.call}/transfers`).then((r) => setTransfers(r.data)).catch(() => setTransfers([]));
  }, [tr.call, msg]);

  async function run(fn: () => Promise<unknown>, ok?: string) {
    try { await fn(); if (ok) setMsg(ok); load(); } catch (e) { setMsg(detail(e, tx("That did not work."))); }
  }
  const cap = (k: string): Cap => caps?.matrix[k] ?? { state: "UNSUPPORTED", reason: tx("Loading carrier capabilities.") };
  const ok = (k: string) => cap(k).state === "SUPPORTED";
  const why = (k: string) => (ok(k) ? undefined : cap(k).reason ?? cap(k).state);
  const box = "border rounded-lg bg-white p-3 space-y-2";
  const btn = "rounded border px-2 py-1 text-xs disabled:opacity-40 disabled:cursor-not-allowed";
  const callable = live.filter((c) => c.direction === "INBOUND" && c.provider === "twilio" && c.status && !["COMPLETED", "NO_ANSWER", "BUSY", "FAILED"].includes(c.status));
  const available = board.agents.filter((a) => a.status === "AVAILABLE");

  return (
    <section className="space-y-3" aria-label={tx("Contact center")}>
      <h2 className="text-base font-semibold">{tx("Contact center")}</h2>
      {msg && <p role="status" className="text-sm rounded bg-blue-50 border border-blue-200 px-3 py-2">{msg}</p>}
      <div className="grid lg:grid-cols-3 gap-3">
        <div className={box}>
          <div className="text-sm font-semibold">{tx("Carrier:")} {caps?.provider ?? tx("none (phone dialler)")}</div>
          <ul className="text-xs space-y-1">
            {Object.keys(LABELS).map((k) => (
              <li key={k} title={cap(k).reason ?? ""}>
                <span className={`inline-block w-24 rounded px-1 mr-1 text-center ${cap(k).state === "SUPPORTED" ? "bg-green-100 text-green-700" : cap(k).state === "UNVERIFIED" ? "bg-amber-100 text-amber-700" : "bg-gray-100 text-gray-500"}`}>{cap(k).state}</span>
                {LABELS[k]}{cap(k).reason && <span className="text-gray-500"> - {cap(k).reason}</span>}
              </li>
            ))}
          </ul>
        </div>
        <div className={box}>
          <div className="text-sm font-semibold">{tx("My presence")}</div>
          <div className="flex gap-2">
            {["AVAILABLE", "AWAY", "OFFLINE"].map((s) => (
              <button key={s} className={btn} onClick={() => run(() => apiClient.put("/api/v1/calls/cc/presence", { status: s }), `You are ${s.toLowerCase()}.`)}>{s}</button>
            ))}
          </div>
          <table className="w-full text-xs">
            <thead><tr className="text-left text-gray-500"><th>{tx("Agent")}</th><th>{tx("Status")}</th></tr></thead>
            <tbody>{board.agents.map((a) => (
              <tr key={a.user_id}><td>{a.name}</td><td><span className={`rounded px-1 ${PRESENCE_STYLE[a.status] ?? ""}`}>{a.status}</span></td></tr>
            ))}</tbody>
          </table>
          {board.agents.length === 0 && <p className="text-xs text-gray-500">{tx("Nobody has set presence yet. Set your answering phone first, then go available.")}</p>}
        </div>
        <div className={box}>
          <div className="text-sm font-semibold">{tx("Queues")}</div>
          {board.queues.map((x) => (
            <div key={x.id} className="text-xs border rounded p-2">
              <b>{x.name}</b> <span className="text-gray-500">{x.direction} · {x.strategy} {tx("· overflow")} {x.overflow}</span>
              <div>{tx("Waiting:")} {x.waiting} {tx("· oldest")} {x.oldest_wait_seconds}{tx("s")}</div>
              {x.direction === "OUTBOUND" && <button className={btn} onClick={() => run(async () => {
                const r = (await apiClient.post(`/api/v1/calls/cc/queues/${x.id}/next`)).data;
                setMsg(r.call ? (r.call.dial ? tx("Dial {dial}", { dial: r.call.dial }) : tx("Your phone will ring; answer it to be connected.")) : tx("The queue is empty."));
              })}>{tx("Next number")}</button>}
            </div>
          ))}
          {board.queues.length === 0 && <p className="text-xs text-gray-500">{tx("No queues yet.")}</p>}
          <details className="text-xs">
            <summary className="cursor-pointer underline">{tx("New queue (managers)")}</summary>
            <form className="space-y-1 mt-1" onSubmit={(e) => { e.preventDefault(); run(() => apiClient.post("/api/v1/calls/cc/queues", { ...q, member_user_ids: q.members }), tx("Queue saved.")); }}>
              <input className="border rounded px-2 py-1 w-full" placeholder={tx("Queue name")} value={q.name} onChange={(e) => setQ({ ...q, name: e.target.value })} required />
              <div className="flex gap-1 flex-wrap">
                <select className="border rounded px-1" value={q.direction} onChange={(e) => setQ({ ...q, direction: e.target.value })}><option>INBOUND</option><option>OUTBOUND</option></select>
                <select className="border rounded px-1" value={q.strategy} onChange={(e) => setQ({ ...q, strategy: e.target.value })}><option>LONGEST_IDLE</option><option>RING_ALL</option></select>
                <select className="border rounded px-1" value={q.overflow} onChange={(e) => setQ({ ...q, overflow: e.target.value })}>
                  <option>CALLBACK</option><option disabled={!ok("voicemail")}>VOICEMAIL</option>
                </select>
              </div>
              {!ok("voicemail") && <p className="text-gray-500">{tx("Voicemail overflow is disabled:")} {cap("voicemail").reason}</p>}
              <label className="block">{tx("Max wait (s)")}<input type="number" min={0} max={600} className="border rounded px-1 ml-1 w-16" value={q.max_wait_seconds} onChange={(e) => setQ({ ...q, max_wait_seconds: Number(e.target.value) })} /></label>
              <div>{tx("Members:")} {board.agents.map((a) => (
                <label key={a.user_id} className="mr-2"><input type="checkbox" checked={q.members.includes(a.user_id)}
                  onChange={(e) => setQ({ ...q, members: e.target.checked ? [...q.members, a.user_id] : q.members.filter((m) => m !== a.user_id) })} /> {a.name}</label>
              ))}</div>
              <button className={btn} type="submit">{tx("Save queue")}</button>
            </form>
          </details>
        </div>
      </div>

      <div className="grid lg:grid-cols-2 gap-3">
        <div className={box}>
          <div className="text-sm font-semibold">{tx("Missed-call callbacks")}</div>
          <table className="w-full text-xs">
            <thead><tr className="text-left text-gray-500"><th>{tx("Number")}</th><th>{tx("Missed")}</th><th>{tx("Tries")}</th><th></th></tr></thead>
            <tbody>{callbacks.map((c) => (
              <tr key={c.id}><td>{c.phone_number}</td><td>{c.missed_count}</td><td>{c.attempts}/3</td>
                <td className="space-x-1">{(["ANSWERED", "NO_ANSWER", "BUSY"] as const).map((o) => (
                  <button key={o} className={btn} onClick={() => run(() => apiClient.post(`/api/v1/calls/cc/callbacks/${c.id}/complete`, { outcome: o }), `Callback marked ${o}.`)}>{o.replace("_", " ")}</button>
                ))}</td></tr>
            ))}</tbody>
          </table>
          {callbacks.length === 0 && <p className="text-xs text-gray-500">{tx("No open callbacks.")}</p>}
          <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); run(async () => {
            const r = (await apiClient.post("/api/v1/calls/cc/callbacks", { phone_number: newCb })).data;
            setMsg(r.duplicate ? tx("This number already has an open callback; the miss was counted on it.") : tx("Callback requested."));
          }); }}>
            <input className="border rounded px-2 py-1 text-xs flex-1" placeholder="+2547..." value={newCb} onChange={(e) => setNewCb(e.target.value)} required />
            <button className={btn} type="submit">{tx("Request callback")}</button>
          </form>
        </div>

        <div className={box}>
          <div className="text-sm font-semibold">{tx("Live call: transfer and outcome")}</div>
          <select className="border rounded px-2 py-1 text-xs w-full" value={tr.call} onChange={(e) => { setTr({ ...tr, call: e.target.value }); setDisp({ ...disp, call: e.target.value }); }}>
            <option value="">{tx("Choose a call")}</option>
            {live.map((c) => <option key={c.id} value={c.id}>{c.call_ref} · {c.direction} · {c.phone_number} · {c.status ?? "-"}</option>)}
          </select>
          {callable.length === 0 && <p className="text-xs text-gray-500">{tx("Transfer works on live inbound calls placed through the carrier (")}{cap("cold_transfer").reason ?? tx("none right now")}).</p>}
          <div className="flex flex-wrap gap-1 items-center text-xs">
            <select className="border rounded px-1" value={tr.kind} onChange={(e) => setTr({ ...tr, kind: e.target.value })}>
              <option value="COLD" disabled={!ok("cold_transfer")}>{tx("Cold")}</option>
              <option value="WARM" disabled={!ok("warm_transfer")}>{tx("Warm (announced)")}</option>
            </select>
            <select className="border rounded px-1" value={tr.user} onChange={(e) => setTr({ ...tr, user: e.target.value })}>
              <option value="">{tx("Agent...")}</option>{available.map((a) => <option key={a.user_id} value={a.user_id}>{a.name}</option>)}
            </select>
            <input className="border rounded px-1 w-32" placeholder={tx("or number")} value={tr.number} onChange={(e) => setTr({ ...tr, number: e.target.value })} />
            <button className={btn} disabled={!tr.call || !ok(tr.kind === "COLD" ? "cold_transfer" : "warm_transfer")}
              title={why(tr.kind === "COLD" ? "cold_transfer" : "warm_transfer")}
              onClick={() => run(() => apiClient.post(`/api/v1/calls/cc/calls/${tr.call}/transfer`, { kind: tr.kind, to_user_id: tr.user || null, to_number: tr.user ? null : tr.number || null }), tx("Transfer requested."))}>{tx("Transfer")}</button>
          </div>
          {!ok("cold_transfer") && <p className="text-xs text-gray-500">{tx("Transfer is disabled:")} {cap("cold_transfer").reason}</p>}
          {transfers.map((t) => (
            <div key={t.id} className="text-xs flex gap-2 items-center">
              <span>{t.kind} {tx("to")} {t.to_number}: <b>{t.state}</b>{t.error && ` (${t.error})`}</span>
              {t.kind === "WARM" && t.state === "READY" && <button className={btn} onClick={() => run(() => apiClient.post(`/api/v1/calls/cc/transfers/${t.id}/complete`), tx("Customer moved."))}>{tx("Complete transfer")}</button>}
            </div>
          ))}
          <div className="flex gap-1 items-center text-xs border-t pt-2">
            <select className="border rounded px-1" value={disp.code} onChange={(e) => setDisp({ ...disp, code: e.target.value })}>{DISPOSITIONS.map((d) => <option key={d}>{d}</option>)}</select>
            <input className="border rounded px-1 flex-1" placeholder={tx("note")} maxLength={500} value={disp.note} onChange={(e) => setDisp({ ...disp, note: e.target.value })} />
            <button className={btn} disabled={!disp.call} onClick={() => run(() => apiClient.put(`/api/v1/calls/cc/calls/${disp.call}/disposition`, { code: disp.code, note: disp.note || null }), tx("Outcome saved."))}>{tx("Save outcome")}</button>
          </div>
        </div>
      </div>
    </section>
  );
}

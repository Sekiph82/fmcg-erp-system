"use client";
/* eslint-disable @next/next/no-img-element -- blob/data URLs and the shared brand host; next/image adds nothing here */
// M42 business card panel: HR mode (employeeId) manages the card; "mine" shows the signed-in employee's own card.
import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { cardsApi, cardPath, download, type CardRow } from "@/lib/businessCards";
import { extractApiError } from "@/lib/sales";

export function BusinessCardPanel({ employeeId }: { employeeId?: string }) {
  const mine = !employeeId;
  const qc = useQueryClient();
  const key = ["business-card", employeeId ?? "mine"];
  const { data: card, error, isLoading } = useQuery({ queryKey: key, queryFn: () => (mine ? cardsApi.mine() : cardsApi.get(employeeId!)) });
  const [qr, setQr] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [consent, setConsent] = useState(false);
  const [title, setTitle] = useState("");

  useEffect(() => { setTitle(card?.title_en ?? ""); }, [card?.title_en]);
  useEffect(() => {
    if (!card) return;
    let url: string | null = null;
    (mine ? cardsApi.myQr("svg") : cardsApi.qr(employeeId!, "svg")).then((u) => { url = u; setQr(u); }).catch(() => setQr(null));
    return () => { if (url) URL.revokeObjectURL(url); };
  }, [card?.slug, mine, employeeId]); // eslint-disable-line react-hooks/exhaustive-deps

  const done = (c: CardRow) => { qc.setQueryData(key, c); qc.invalidateQueries({ queryKey: ["business-cards"] }); setErr(null); };
  const run = useMutation({ mutationFn: (fn: () => Promise<CardRow>) => fn(), onSuccess: done, onError: (e) => setErr(extractApiError(e)) });

  if (isLoading) return <p className="text-sm text-gray-500">Loading…</p>;
  if (error || !card) return <p role="alert" className="text-sm text-red-600">{extractApiError(error)}</p>;
  const pub = cardPath(card.slug);
  const saveQr = async (fmt: "svg" | "png") => download(await (mine ? cardsApi.myQr(fmt) : cardsApi.qr(employeeId!, fmt)), `${card.slug}.${fmt}`);
  const share = () => { const url = new URL(pub, location.origin).toString(); if (navigator.share) navigator.share({ title: card.name, url }).catch(() => undefined); else navigator.clipboard?.writeText(url); };

  return (
    <div className="space-y-4 text-sm">
      <div className="flex flex-wrap gap-4 items-start">
        <div className="w-40 h-40 border rounded-lg bg-white grid place-items-center p-2">
          {qr ? <img src={qr} alt={`QR code for ${card.name}'s card`} className="w-full h-full" /> : <span className="text-xs text-gray-400">QR…</span>}
        </div>
        <div className="flex-1 min-w-[14rem] space-y-1">
          <p className="font-semibold text-base">{card.name}</p>
          <p className="text-gray-600">{card.title_en || card.role}</p>
          <p>
            <span className={`inline-block px-2 py-0.5 rounded text-xs ${card.live ? "bg-emerald-100 text-emerald-800" : "bg-red-100 text-red-700"}`}>
              {card.live ? "Live" : card.status === "REVOKED" ? `Closed${card.revoked_reason ? ` — ${card.revoked_reason}` : ""}` : "Closed (employee not active)"}
            </span>
          </p>
          <p className="break-all text-xs text-gray-500">{card.url}</p>
          <div className="flex flex-wrap gap-2 pt-1">
            <a href={pub} target="_blank" rel="noopener noreferrer" className="px-3 py-1.5 rounded border">Open card</a>
            <button type="button" onClick={() => saveQr("png")} className="px-3 py-1.5 rounded border">QR (PNG)</button>
            <button type="button" onClick={() => saveQr("svg")} className="px-3 py-1.5 rounded border">QR (SVG)</button>
            {mine && <button type="button" onClick={share} className="px-3 py-1.5 rounded border">Share</button>}
          </div>
        </div>
        {card.photo && <img src={card.photo} alt="Profile photo" className="w-24 h-24 rounded-full object-cover border" />}
      </div>

      {mine ? (
        <p className="text-gray-500">Your name, title, phone and e-mail come from your HR record. Ask HR to change them or your photo.</p>
      ) : (
        <>
          <fieldset className="border rounded-lg p-3 space-y-2">
            <legend className="px-1 font-medium">Shown on the card</legend>
            {([["show_phone", "Work phone"], ["show_whatsapp", "WhatsApp"], ["show_email", "Work e-mail"]] as const).map(([k, label]) => (
              <label key={k} className="flex items-center gap-2">
                <input type="checkbox" checked={card[k]} disabled={run.isPending} onChange={(e) => run.mutate(() => cardsApi.update(employeeId!, { [k]: e.target.checked }))} />
                {label}
              </label>
            ))}
            <div className="flex flex-wrap gap-2 items-end">
              <label className="flex-1 min-w-[12rem]">
                <span className="block text-xs text-gray-500">Card title (empty = HR role)</span>
                <input value={title} maxLength={150} onChange={(e) => setTitle(e.target.value)} placeholder={card.role} className="w-full border rounded px-2 py-1" />
              </label>
              <button type="button" disabled={run.isPending || title === (card.title_en ?? "")} onClick={() => run.mutate(() => cardsApi.update(employeeId!, { title_en: title }))} className="px-3 py-1.5 rounded border">Save title</button>
            </div>
          </fieldset>

          <fieldset className="border rounded-lg p-3 space-y-2">
            <legend className="px-1 font-medium">Profile photo</legend>
            <input type="file" accept="image/jpeg,image/png" aria-label="Profile photo file (JPEG or PNG, max 400 KB)" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
            <label className="flex items-start gap-2">
              <input type="checkbox" className="mt-1" checked={consent} onChange={(e) => setConsent(e.target.checked)} />
              <span>The employee agreed that this photo is published on their public business card (recorded with my name and the time).</span>
            </label>
            <div className="flex gap-2">
              <button type="button" disabled={!file || !consent || run.isPending} onClick={() => run.mutate(() => cardsApi.uploadPhoto(employeeId!, file!, consent))} className="px-3 py-1.5 rounded bg-indigo-600 text-white disabled:opacity-50">Upload photo</button>
              {card.has_photo && <button type="button" disabled={run.isPending} onClick={() => run.mutate(() => cardsApi.removePhoto(employeeId!))} className="px-3 py-1.5 rounded border">Remove photo</button>}
            </div>
          </fieldset>

          <div className="flex gap-2">
            {card.status === "PUBLISHED" ? (
              <button type="button" disabled={run.isPending} className="px-3 py-1.5 rounded border border-red-300 text-red-700"
                onClick={() => { const reason = window.prompt("Why is the card closed?"); if (reason !== null) run.mutate(() => cardsApi.revoke(employeeId!, reason || undefined)); }}>Close card</button>
            ) : (
              <button type="button" disabled={run.isPending} className="px-3 py-1.5 rounded border border-emerald-300 text-emerald-800" onClick={() => run.mutate(() => cardsApi.republish(employeeId!))}>Publish again (same QR)</button>
            )}
          </div>
        </>
      )}
      {err && <p role="alert" className="text-red-600">{err}</p>}
    </div>
  );
}

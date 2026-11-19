"use client";
// Public product authenticity check for consumers who scan the QR code on a pack (no login).
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { API_ORIGIN } from "@/lib/api";

interface Trace {
  verified: boolean; lot_number: string; product_name: string | null; manufacture_date: string | null; expiry_date: string | null;
  blockchain_anchored: boolean; blockchain_network: string | null; tx_hash: string | null; integrity_note: string;
}

export default function VerifyProduct() {
  const { token } = useParams<{ token: string }>();
  const [data, setData] = useState<Trace | null>(null);
  const [state, setState] = useState<"loading" | "ok" | "unknown" | "error">("loading");

  useEffect(() => {
    fetch(`${API_ORIGIN}/api/v1/traceability/blockchain/public/${encodeURIComponent(token)}`)
      .then(async (r) => {
        if (r.status === 404) return setState("unknown");
        if (!r.ok) return setState("error");
        setData(await r.json()); setState("ok");
      })
      .catch(() => setState("error"));
  }, [token]);

  const expired = data?.expiry_date ? new Date(data.expiry_date) < new Date(new Date().toDateString()) : false;
  return (
    <main className="min-h-screen bg-gray-50 text-gray-900 flex items-start justify-center p-4">
      <div className="w-full max-w-sm bg-white rounded-2xl shadow p-6 space-y-4 mt-8">
        <h1 className="text-lg font-bold">Product check</h1>
        {state === "loading" && <p className="text-sm text-gray-500">Checking…</p>}
        {state === "unknown" && (
          <div role="alert" className="rounded-xl bg-red-50 border border-red-200 p-4 text-sm text-red-800">
            <p className="font-semibold">This code is not recognised.</p>
            <p>The product may not be genuine. Do not consume it and contact the shop or our customer care.</p>
          </div>)}
        {state === "error" && <p role="alert" className="text-sm text-amber-700">The check could not be completed. Please try again later.</p>}
        {state === "ok" && data && (<>
          <div role="status" className={`rounded-xl border p-4 text-sm ${expired ? "bg-amber-50 border-amber-200 text-amber-900" : "bg-emerald-50 border-emerald-200 text-emerald-900"}`}>
            <p className="font-semibold text-base">{expired ? "Genuine product — past its expiry date" : "Genuine product"}</p>
            <p>{data.integrity_note}</p>
          </div>
          <dl className="text-sm grid grid-cols-[auto_1fr] gap-x-3 gap-y-1">
            {data.product_name && (<><dt className="text-gray-500">Product</dt><dd>{data.product_name}</dd></>)}
            <dt className="text-gray-500">Batch</dt><dd>{data.lot_number}</dd>
            {data.manufacture_date && (<><dt className="text-gray-500">Made on</dt><dd>{data.manufacture_date}</dd></>)}
            {data.expiry_date && (<><dt className="text-gray-500">Best before</dt><dd className={expired ? "text-red-700 font-semibold" : ""}>{data.expiry_date}</dd></>)}
            {data.blockchain_anchored && (<><dt className="text-gray-500">Ledger</dt><dd className="break-all">{data.blockchain_network} · {data.tx_hash}</dd></>)}
          </dl>
        </>)}
      </div>
    </main>
  );
}

"use client";
// M51.S01.T009 public page: the link in the verification e-mail opens here. The token sits in the URL fragment (never
// sent to a server or logged) and nothing happens until the visitor presses the button, so mail scanners that prefetch
// the link verify nothing. Verification works only in the browser that asked for it (same visitor and session ids).
import { useEffect, useState } from "react";
import { API_ORIGIN } from "@/lib/api";

const post = (path: string, body: object) =>
  fetch(`${API_ORIGIN}/api/v1/public/visitor-verify/${path}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

export default function VerifyEmailPage() {
  const [token, setToken] = useState("");
  const [state, setState] = useState<"idle" | "busy" | "ok" | "fail">("idle");
  const ids = () => {
    try { return { visitor: localStorage.getItem("povu_vid") ?? "", session: sessionStorage.getItem("povu_sid") ?? "" }; } catch { return { visitor: "", session: "" }; }
  };
  useEffect(() => {
    const t = new URLSearchParams(window.location.hash.slice(1)).get("t") ?? "";
    setToken(t);
    history.replaceState(null, "", window.location.pathname);      // drop the token from the address bar and history
  }, []);
  async function confirm() {
    setState("busy");
    const r = await post("confirm", { ...ids(), token }).catch(() => null);
    const j = r && r.ok ? await r.json() : null;
    setState(j?.verified ? "ok" : "fail");
  }
  return (
    <main className="min-h-screen bg-white text-gray-900 p-6">
      <meta name="referrer" content="no-referrer" />
      <div className="max-w-md mx-auto space-y-4">
        <h1 className="text-xl font-bold">Confirm your e-mail address</h1>
        {state === "ok" ? <p role="status" className="text-sm">Thank you. Your e-mail address is confirmed in this browser.</p>
          : state === "fail" ? <p role="alert" className="text-sm text-red-700">This link did not work. It may have expired, been used already, or been opened in a different browser than the one you asked from. Please request a new one on the website.</p>
          : !token ? <p role="alert" className="text-sm text-red-700">This page needs the link from your e-mail.</p>
          : <>
            <p className="text-sm">Press the button to confirm that this browser may use your e-mail address on this website.</p>
            <button className="px-4 py-2 rounded bg-indigo-600 text-white disabled:opacity-50" disabled={state === "busy"} onClick={confirm}>Confirm my e-mail</button>
          </>}
      </div>
    </main>
  );
}

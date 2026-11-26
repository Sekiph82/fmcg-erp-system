"use client";

import { useEffect, useRef, useState } from "react";
import { tx } from "@/lib/i18n/core";

type Detector = { detect: (source: HTMLVideoElement) => Promise<{ rawValue: string }[]> };
type DetectorCtor = new (opts?: { formats?: string[] }) => Detector;

/** Native BarcodeDetector (Android Chrome, Edge); elsewhere (iPhone Safari) the zxing WebAssembly ponyfill,
 * loaded only when the camera opens. The .wasm is bundled with the app (no CDN), so it also works offline. */
async function getDetector(): Promise<DetectorCtor> {
  const native = (window as unknown as { BarcodeDetector?: DetectorCtor }).BarcodeDetector;
  if (native) return native;
  const { BarcodeDetector, setZXingModuleOverrides } = await import("barcode-detector/ponyfill");
  const wasm = new URL("zxing-wasm/reader/zxing_reader.wasm", import.meta.url).href;
  setZXingModuleOverrides({ locateFile: (path: string, prefix: string) => (path.endsWith(".wasm") ? wasm : prefix + path) });
  return BarcodeDetector as unknown as DetectorCtor;
}

/**
 * Camera barcode/QR scan. Renders nothing without a camera API — hardware keyboard-wedge scanners and
 * manual entry remain the fallback.
 */
export function BarcodeScanButton({ onScan, label = "Scan" }: { onScan: (code: string) => void; label?: string }) {
  const [supported, setSupported] = useState(false);
  const [open, setOpen] = useState(false);
  const [error, setError] = useState("");
  const videoRef = useRef<HTMLVideoElement>(null);
  // parent re-renders (e.g. 15 s queue polling) must not restart the camera
  const onScanRef = useRef(onScan);
  useEffect(() => { onScanRef.current = onScan; }, [onScan]);

  useEffect(() => setSupported(!!navigator.mediaDevices?.getUserMedia), []);

  useEffect(() => {
    if (!open) return;
    let stream: MediaStream | null = null;
    let stopped = false;
    let detector: Detector | null = null;

    const loop = async () => {
      const video = videoRef.current;
      if (stopped || !video || !detector) return;
      try {
        const codes = video.readyState >= 2 ? await detector.detect(video) : [];
        if (codes[0]?.rawValue) {
          onScanRef.current(codes[0].rawValue.trim());
          setOpen(false);
          return;
        }
      } catch {
        // transient decode failure — keep scanning
      }
      requestAnimationFrame(loop);
    };

    getDetector()
      .then((Ctor) => { detector = new Ctor(); return navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } }); })
      .then((s) => {
        if (stopped) { s.getTracks().forEach((t) => t.stop()); return; } // closed while the decoder or camera was loading
        stream = s;
        if (!videoRef.current) return;
        videoRef.current.srcObject = s;
        return videoRef.current.play().then(loop);
      })
      .catch(() => { if (!stopped) setError(tx("Camera unavailable or permission denied.")); });

    return () => {
      stopped = true;
      stream?.getTracks().forEach((t) => t.stop());
    };
  }, [open]);

  if (!supported) return null;

  return (
    <>
      <button
        type="button"
        onClick={() => { setError(""); setOpen(true); }}
        className="min-h-11 px-3 rounded-lg border border-indigo-600 bg-indigo-600 text-white text-sm font-semibold"
        data-testid="barcode-scan-button"
      >
        {label}
      </button>
      {open && (
        <div role="dialog" aria-modal="true" aria-label={tx("Barcode scanner")} className="fixed inset-0 z-50 flex flex-col items-center justify-center gap-3 bg-black/80 p-4">
          <video ref={videoRef} muted playsInline className="w-full max-w-md rounded-xl bg-black" />
          {error && <p role="alert" className="text-sm text-red-200">{error}</p>}
          <button type="button" onClick={() => setOpen(false)} className="min-h-12 w-full max-w-md rounded-xl bg-white font-semibold text-gray-900">
            {tx("Cancel")}
          </button>
        </div>
      )}
    </>
  );
}

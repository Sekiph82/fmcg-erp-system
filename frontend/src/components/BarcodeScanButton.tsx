"use client";

import { useEffect, useRef, useState } from "react";

type Detector = { detect: (source: HTMLVideoElement) => Promise<{ rawValue: string }[]> };
type DetectorCtor = new (opts?: { formats?: string[] }) => Detector;

function getDetector(): DetectorCtor | null {
  if (typeof window === "undefined") return null;
  return (window as unknown as { BarcodeDetector?: DetectorCtor }).BarcodeDetector ?? null;
}

/**
 * Camera barcode/QR scan via the native BarcodeDetector API (Android Chrome, Edge).
 * Renders nothing where unsupported (iOS Safari) — hardware keyboard-wedge scanners and
 * manual entry remain the fallback. ponytail: add a JS decoder (zxing) when iOS camera scan is required.
 */
export function BarcodeScanButton({ onScan, label = "Scan" }: { onScan: (code: string) => void; label?: string }) {
  const [supported, setSupported] = useState(false);
  const [open, setOpen] = useState(false);
  const [error, setError] = useState("");
  const videoRef = useRef<HTMLVideoElement>(null);
  // parent re-renders (e.g. 15 s queue polling) must not restart the camera
  const onScanRef = useRef(onScan);
  useEffect(() => { onScanRef.current = onScan; }, [onScan]);

  useEffect(() => setSupported(!!getDetector() && !!navigator.mediaDevices?.getUserMedia), []);

  useEffect(() => {
    if (!open) return;
    const Ctor = getDetector();
    if (!Ctor) return;
    let stream: MediaStream | null = null;
    let stopped = false;
    const detector = new Ctor();

    const loop = async () => {
      const video = videoRef.current;
      if (stopped || !video) return;
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

    navigator.mediaDevices
      .getUserMedia({ video: { facingMode: "environment" } })
      .then((s) => {
        stream = s;
        if (stopped || !videoRef.current) return;
        videoRef.current.srcObject = s;
        return videoRef.current.play().then(loop);
      })
      .catch(() => setError("Camera unavailable or permission denied."));

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
        className="min-h-11 px-3 rounded-lg border border-indigo-300 bg-indigo-50 text-indigo-800 text-sm font-semibold"
        data-testid="barcode-scan-button"
      >
        {label}
      </button>
      {open && (
        <div role="dialog" aria-modal="true" aria-label="Barcode scanner" className="fixed inset-0 z-50 flex flex-col items-center justify-center gap-3 bg-black/80 p-4">
          <video ref={videoRef} muted playsInline className="w-full max-w-md rounded-xl bg-black" />
          {error && <p role="alert" className="text-sm text-red-200">{error}</p>}
          <button type="button" onClick={() => setOpen(false)} className="min-h-12 w-full max-w-md rounded-xl bg-white font-semibold text-gray-900">
            Cancel
          </button>
        </div>
      )}
    </>
  );
}

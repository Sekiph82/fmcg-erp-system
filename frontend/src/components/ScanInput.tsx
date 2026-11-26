"use client";

import { useState } from "react";
import { BarcodeScanButton } from "@/components/BarcodeScanButton";
import { tx } from "@/lib/i18n/core";

/**
 * One field for every scanner: hardware keyboard-wedge scanners type the code + Enter,
 * the camera button (where supported) fills it, and people can type it by hand.
 * `onScan` receives the code and the device time of the scan.
 */
export function ScanInput({
  onScan, label = tx("Scan barcode"), placeholder = tx("Scan or type barcode"), disabled = false, id = "scan-input",
}: {
  onScan: (code: string, scannedAt: string) => void;
  label?: string;
  placeholder?: string;
  disabled?: boolean;
  id?: string;
}) {
  const [value, setValue] = useState("");
  const submit = (code: string) => {
    const trimmed = code.trim();
    if (!trimmed || disabled) return;
    onScan(trimmed, new Date().toISOString());
    setValue("");
  };
  return (
    <form onSubmit={(e) => { e.preventDefault(); submit(value); }} className="space-y-1">
      <label htmlFor={id} className="text-xs font-semibold text-gray-700">{label}</label>
      <div className="flex gap-2">
        <input
          id={id}
          data-testid={id}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder={placeholder}
          autoComplete="off"
          autoCapitalize="off"
          enterKeyHint="go"
          disabled={disabled}
          className="min-h-11 flex-1 min-w-0 rounded-lg border border-gray-300 px-3 text-base font-mono"
        />
        <BarcodeScanButton label={tx("Camera")} onScan={submit} />
        <button type="submit" disabled={disabled || !value.trim()} className="min-h-11 rounded-lg bg-indigo-700 px-3 text-sm font-semibold text-white disabled:opacity-40">
          OK
        </button>
      </div>
    </form>
  );
}

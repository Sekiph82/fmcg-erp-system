"use client";

import { useEffect } from "react";
import { clsx } from "clsx";

export type ToastType = "success" | "error" | "warning";

export interface ToastMessage {
  id: string;
  type: ToastType;
  title: string;
  body?: string;
}

const icons = {
  success: (
    <svg className="h-5 w-5 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
    </svg>
  ),
  error: (
    <svg className="h-5 w-5 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
    </svg>
  ),
  warning: (
    <svg className="h-5 w-5 text-yellow-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
    </svg>
  ),
};

const borders: Record<ToastType, string> = {
  success: "border-l-green-500",
  error: "border-l-red-500",
  warning: "border-l-yellow-500",
};

interface ToastItemProps {
  toast: ToastMessage;
  onDismiss: (id: string) => void;
}

function ToastItem({ toast, onDismiss }: ToastItemProps) {
  useEffect(() => {
    const t = setTimeout(() => onDismiss(toast.id), toast.type === "error" ? 7000 : 4000);
    return () => clearTimeout(t);
  }, [toast.id, toast.type, onDismiss]);

  return (
    <div className={clsx("flex items-start gap-3 rounded-lg border border-gray-200 border-l-4 bg-white px-4 py-3 shadow-lg w-80", borders[toast.type])}>
      <div className="mt-0.5 shrink-0">{icons[toast.type]}</div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-gray-900">{toast.title}</p>
        {toast.body && <p className="mt-0.5 text-xs text-gray-500 break-words">{toast.body}</p>}
      </div>
      <button onClick={() => onDismiss(toast.id)} className="shrink-0 text-gray-400 hover:text-gray-600 text-lg leading-none">&times;</button>
    </div>
  );
}

interface ToastContainerProps {
  toasts: ToastMessage[];
  onDismiss: (id: string) => void;
}

export function ToastContainer({ toasts, onDismiss }: ToastContainerProps) {
  return (
    <div className="fixed bottom-5 right-5 z-50 flex flex-col gap-3">
      {toasts.map((t) => <ToastItem key={t.id} toast={t} onDismiss={onDismiss} />)}
    </div>
  );
}

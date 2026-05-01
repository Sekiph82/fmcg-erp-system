"use client";

import { createContext, useContext, useCallback, useState, ReactNode } from "react";
import { ToastContainer, ToastMessage, ToastType } from "@/components/ui/Toast";

interface ToastContextValue {
  toast: (type: ToastType, title: string, body?: string) => void;
  success: (title: string, body?: string) => void;
  error: (title: string, body?: string) => void;
  warning: (title: string, body?: string) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const dismiss = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const toast = useCallback((type: ToastType, title: string, body?: string) => {
    const id = Math.random().toString(36).slice(2);
    setToasts((prev) => [...prev.slice(-4), { id, type, title, body }]);
  }, []);

  const success = useCallback((title: string, body?: string) => toast("success", title, body), [toast]);
  const error   = useCallback((title: string, body?: string) => toast("error",   title, body), [toast]);
  const warning = useCallback((title: string, body?: string) => toast("warning", title, body), [toast]);

  return (
    <ToastContext.Provider value={{ toast, success, error, warning }}>
      {children}
      <ToastContainer toasts={toasts} onDismiss={dismiss} />
    </ToastContext.Provider>
  );
}

export function useToastContext(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToastContext must be inside ToastProvider");
  return ctx;
}

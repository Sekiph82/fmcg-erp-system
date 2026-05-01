"use client";

import { useState, useEffect, useCallback } from "react";

const STORAGE_KEY = "erp_palette_recent";
const MAX_RECENT = 8;

export interface RecentItem {
  label: string;
  href: string;
  subtitle?: string;
  ts: number;
}

function loadRecent(): RecentItem[] {
  if (typeof window === "undefined") return [];
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "[]");
  } catch {
    return [];
  }
}

function saveRecent(items: RecentItem[]) {
  if (typeof window === "undefined") return;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(items.slice(0, MAX_RECENT)));
}

export function useCommandPalette() {
  const [open, setOpen] = useState(false);
  const [recent, setRecent] = useState<RecentItem[]>([]);

  useEffect(() => {
    setRecent(loadRecent());
  }, [open]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "k") {
        e.preventDefault();
        setOpen((v) => !v);
      }
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  const openPalette = useCallback(() => setOpen(true), []);
  const closePalette = useCallback(() => setOpen(false), []);

  const recordVisit = useCallback((item: Omit<RecentItem, "ts">) => {
    const next: RecentItem[] = [
      { ...item, ts: Date.now() },
      ...loadRecent().filter((r) => r.href !== item.href),
    ].slice(0, MAX_RECENT);
    saveRecent(next);
    setRecent(next);
  }, []);

  const clearRecent = useCallback(() => {
    saveRecent([]);
    setRecent([]);
  }, []);

  return { open, openPalette, closePalette, recent, recordVisit, clearRecent };
}

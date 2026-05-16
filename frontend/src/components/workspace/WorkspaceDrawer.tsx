"use client";

import { useRouter, usePathname, useSearchParams } from "next/navigation";
import { useCallback, useEffect } from "react";

interface WorkspaceDrawerProps {
  /** Which drawer= value triggers this drawer */
  drawerKey: string;
  title: string;
  children: React.ReactNode;
  width?: "sm" | "md" | "lg" | "xl";
}

const widthClass = {
  sm: "w-full max-w-md",
  md: "w-full max-w-xl",
  lg: "w-full max-w-2xl",
  xl: "w-full max-w-4xl",
};

export function WorkspaceDrawer({
  drawerKey,
  title,
  children,
  width = "lg",
}: WorkspaceDrawerProps) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const isOpen = searchParams.get("drawer") === drawerKey;

  const close = useCallback(() => {
    const params = new URLSearchParams(searchParams.toString());
    params.delete("drawer");
    params.delete("id");
    router.replace(`${pathname}?${params.toString()}`);
  }, [router, pathname, searchParams]);

  // Close on Escape
  useEffect(() => {
    if (!isOpen) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") close();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [isOpen, close]);

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/60 backdrop-blur-[2px] z-40 transition-opacity"
        onClick={close}
      />

      {/* Drawer panel — glass-modal */}
      <div
        className={`fixed right-0 top-0 bottom-0 ${widthClass[width]} glass-modal z-50 flex flex-col border-l border-cyan-500/25`}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-cyan-500/20 shrink-0">
          <h2 className="text-base font-semibold text-slate-100">{title}</h2>
          <button
            onClick={close}
            className="rounded-lg p-1.5 text-slate-400 hover:text-slate-200 hover:bg-white/[0.06] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500/50"
            aria-label="Close drawer"
          >
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {children}
        </div>
      </div>
    </>
  );
}

/** Hook: open a drawer by key */
export function useDrawer() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const open = useCallback(
    (key: string, id?: string) => {
      const params = new URLSearchParams(searchParams.toString());
      params.set("drawer", key);
      if (id) params.set("id", id);
      else params.delete("id");
      router.push(`${pathname}?${params.toString()}`);
    },
    [router, pathname, searchParams]
  );

  const close = useCallback(() => {
    const params = new URLSearchParams(searchParams.toString());
    params.delete("drawer");
    params.delete("id");
    router.replace(`${pathname}?${params.toString()}`);
  }, [router, pathname, searchParams]);

  const currentDrawer = searchParams.get("drawer");
  const currentId = searchParams.get("id");

  return { open, close, currentDrawer, currentId };
}

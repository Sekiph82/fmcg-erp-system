"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { Sidebar } from "./Sidebar";
import { useUnsavedChangesContext } from "@/context/UnsavedChangesContext";

interface DashboardShellProps {
  children: React.ReactNode;
}

export function DashboardShell({ children }: DashboardShellProps) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const { isDirty, confirmLeave } = useUnsavedChangesContext();
  const router = useRouter();
  const originalPushRef = useRef<typeof window.history.pushState | null>(null);

  const openMobile = useCallback(() => setMobileOpen(true), []);
  const closeMobile = useCallback(() => setMobileOpen(false), []);

  // ── Browser close / refresh / tab close ─────────────────────────────────────
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (!isDirty) return;
      e.preventDefault();
      e.returnValue = ""; // triggers browser's native "Leave site?" dialog
    };
    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, [isDirty]);

  // ── In-app navigation (Next.js SPA route changes) ────────────────────────────
  useEffect(() => {
    if (!isDirty) {
      // Restore original pushState if we patched it
      if (originalPushRef.current) {
        window.history.pushState = originalPushRef.current;
        originalPushRef.current = null;
      }
      return;
    }

    const original = window.history.pushState.bind(window.history);
    originalPushRef.current = original;

    window.history.pushState = async function (state, title, url) {
      const ok = await confirmLeave();
      if (ok) original(state, title, url);
    };

    return () => {
      if (originalPushRef.current) {
        window.history.pushState = originalPushRef.current;
        originalPushRef.current = null;
      }
    };
  }, [isDirty, confirmLeave]);

  return (
    <div className="flex h-screen bg-[#f1f3f6] overflow-hidden">
      {/* Mobile overlay backdrop */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-[1px] lg:hidden"
          onClick={closeMobile}
        />
      )}

      <Sidebar mobileOpen={mobileOpen} onMobileClose={closeMobile} />

      {/* Right column: mobile top bar + main content */}
      <div className="flex flex-1 flex-col overflow-hidden min-w-0">
        {/* Mobile top bar — only visible on small screens */}
        <header className="flex h-[52px] shrink-0 items-center gap-3 border-b border-gray-200/80 bg-white px-4 lg:hidden">
          <button
            onClick={openMobile}
            className="flex h-8 w-8 items-center justify-center rounded-lg text-gray-500 hover:bg-gray-100 transition-colors"
            aria-label="Open navigation"
          >
            <svg className="h-[18px] w-[18px]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          <div className="flex items-center gap-2">
            <div className="flex h-6 w-6 items-center justify-center rounded-md bg-indigo-600 text-[9px] font-bold text-white">
              ERP
            </div>
            <span className="text-[13px] font-semibold text-gray-800 tracking-tight">
              FMCG ERP
            </span>
          </div>
        </header>

        {/* Main scrollable content */}
        <main className="flex-1 overflow-y-auto">
          <div className="p-6 lg:p-8">{children}</div>
        </main>
      </div>
    </div>
  );
}

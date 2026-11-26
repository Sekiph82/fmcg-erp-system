"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import Image from "next/image";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Sidebar } from "./Sidebar";
import { CommandPalette } from "./CommandPalette";
import { NotificationBell } from "./NotificationBell";
import { AIModeBanner } from "./ai/AIModeBanner";
import { HelpButton } from "./help/HelpButton";
import { HelpDrawer } from "./help/HelpDrawer";
import { getHelpForRoute } from "@/lib/help/get-help-for-route";
import { useCommandPalette } from "@/hooks/useCommandPalette";
import { useUnsavedChangesContext } from "@/context/UnsavedChangesContext";
import { PostingRulesFirstLogin } from "./PostingRulesFirstLogin";
import LanguageSwitcher from "./LanguageSwitcher";
import { useI18n, enableTx } from "@/lib/i18n";

interface DashboardShellProps {
  children: React.ReactNode;
}

export function DashboardShell({ children }: DashboardShellProps) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);
  const { t, locale } = useI18n();
  // M51.S01.T008: tx() stays English until hydration so server and first client render agree; after that the whole
  // dashboard tree is keyed by locale, so a locale change re-renders every tx() literal. English users never remount.
  const [txReady, setTxReady] = useState(false);
  useEffect(() => { enableTx(); setTxReady(true); }, []);
  const contentKey = txReady ? locale : "en";
  const { isDirty, confirmLeave } = useUnsavedChangesContext();
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const originalPushRef = useRef<typeof window.history.pushState | null>(null);
  const { open, openPalette, closePalette, recent, recordVisit } = useCommandPalette();
  const showModuleAIBanner = pathname.includes("/ai") && !pathname.startsWith("/dashboard/ai");

  const currentTab = searchParams.get("tab");
  const helpEntry = getHelpForRoute(pathname, currentTab);
  const openHelp = useCallback(() => setHelpOpen(true), []);
  const closeHelp = useCallback(() => setHelpOpen(false), []);

  const openMobile = useCallback(() => setMobileOpen(true), []);
  const closeMobile = useCallback(() => setMobileOpen(false), []);

  // ── Browser close / refresh / tab close ─────────────────────────────────────
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (!isDirty) return;
      e.preventDefault();
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, [isDirty]);

  // ── In-app navigation (Next.js SPA route changes) ────────────────────────────
  useEffect(() => {
    if (!isDirty) {
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
    <div key={contentKey} className="flex h-screen h-dvh bg-[#030d1a] overflow-hidden" data-testid="dashboard-shell">
      {/* Mobile overlay backdrop */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-[1px] lg:hidden"
          onClick={closeMobile}
        />
      )}

      <PostingRulesFirstLogin />
      <Sidebar mobileOpen={mobileOpen} onMobileClose={closeMobile} onOpenSearch={openPalette} />

      {/* Right column: mobile top bar + main content */}
      <div className="flex flex-1 flex-col overflow-hidden min-w-0" data-theme="dark">
        {/* Mobile top bar */}
        <header className="flex h-[52px] shrink-0 items-center gap-3 border-b border-cyan-500/[0.15] bg-[#020c18] px-4 lg:hidden" style={{boxShadow: '0 1px 0 rgba(0,212,255,0.08)' }}>
          <button
            onClick={openMobile}
            className="flex h-8 w-8 items-center justify-center rounded-lg text-slate-400 hover:bg-white/10 transition-colors"
            aria-label={t("staff.shell.openNavigation")}
          >
            <svg className="h-[18px] w-[18px]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          <div className="flex items-center gap-2 flex-1 min-w-0">
            <div className="relative h-6 w-6 rounded-md overflow-hidden shrink-0">
              <Image src="/icons/povu-icon-192.png" alt="POVU" fill sizes="24px" className="object-contain" />
            </div>
            <span className="text-[13px] font-semibold text-white tracking-tight truncate">POVU ERP</span>
          </div>
          <LanguageSwitcher className="shrink-0" />
          {/* Mobile notification bell */}
          <NotificationBell />
          {/* Mobile help button */}
          <HelpButton onClick={openHelp} />
          {/* Mobile search button */}
          <button
            onClick={openPalette}
            className="flex h-8 w-8 items-center justify-center rounded-lg text-slate-400 hover:bg-white/10 transition-colors"
            aria-label={t("staff.shell.openSearch")}
          >
            <svg className="h-[18px] w-[18px]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </button>
        </header>

        {/* Main scrollable content */}
        <main className="min-w-0 flex-1 overflow-y-auto" data-testid="dashboard-main">
          {showModuleAIBanner && <AIModeBanner />}
          <div className="p-6 lg:p-8">{children}</div>
        </main>
      </div>

      {/* Global Command Palette */}
      <CommandPalette
        open={open}
        onClose={closePalette}
        onVisit={recordVisit}
        recent={recent}
      />

      {/* Floating help button — desktop only */}
      <div className="fixed bottom-6 right-6 z-30 hidden lg:block">
        <HelpButton onClick={openHelp} className="h-10 w-10 shadow-lg shadow-cyan-500/10" />
      </div>

      {/* Global help drawer */}
      <HelpDrawer open={helpOpen} onClose={closeHelp} entry={helpEntry} />
    </div>
  );
}

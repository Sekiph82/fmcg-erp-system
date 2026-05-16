"use client";

import { useRouter, usePathname, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { useAuth } from "@/context/AuthContext";

export interface WorkspaceTab {
  key: string;
  label: string;
  permission?: string;
  content: React.ReactNode;
}

interface WorkspaceTabsProps {
  tabs: WorkspaceTab[];
  defaultTab?: string;
}

export function WorkspaceTabs({ tabs, defaultTab }: WorkspaceTabsProps) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const { hasPermission } = useAuth();
  const [overflowOpen, setOverflowOpen] = useState(false);
  const tabBarRef = useRef<HTMLDivElement>(null);

  const visibleTabs = tabs.filter(
    (t) => !t.permission || hasPermission(t.permission)
  );

  const activeKey =
    searchParams.get("tab") ??
    defaultTab ??
    visibleTabs[0]?.key ??
    "";

  const activeTab = visibleTabs.find((t) => t.key === activeKey) ?? visibleTabs[0];

  const navigate = useCallback(
    (key: string) => {
      const params = new URLSearchParams(searchParams.toString());
      params.set("tab", key);
      // Clear drawer/id when switching tabs
      params.delete("drawer");
      params.delete("id");
      router.replace(`${pathname}?${params.toString()}`);
      setOverflowOpen(false);
    },
    [router, pathname, searchParams]
  );

  // Close overflow on outside click
  useEffect(() => {
    if (!overflowOpen) return;
    const handler = (e: MouseEvent) => {
      if (tabBarRef.current && !tabBarRef.current.contains(e.target as Node)) {
        setOverflowOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [overflowOpen]);

  if (visibleTabs.length === 0) return null;

  return (
    <div className="flex flex-col flex-1 min-h-0">
      {/* Tab bar — neon liquid glass */}
      <div
        ref={tabBarRef}
        className="relative flex items-center border-b border-cyan-500/20 bg-[rgba(15,23,42,0.65)] backdrop-blur-xl overflow-x-auto scrollbar-hide"
      >
        <div className="flex items-center gap-0 min-w-0 flex-1">
          {visibleTabs.map((tab) => {
            const active = tab.key === (activeTab?.key ?? "");
            return (
              <button
                key={tab.key}
                onClick={() => navigate(tab.key)}
                className={
                  active
                    ? "relative flex items-center whitespace-nowrap px-4 py-3 text-sm font-medium transition-colors duration-150 shrink-0 text-cyan-300 after:absolute after:bottom-0 after:left-0 after:right-0 after:h-[2px] after:bg-gradient-to-r after:from-cyan-500 after:to-blue-500"
                    : "relative flex items-center whitespace-nowrap px-4 py-3 text-sm font-medium transition-colors duration-150 shrink-0 text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]"
                }
              >
                {tab.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Active tab content */}
      <div className="flex-1 min-h-0 overflow-auto">
        {activeTab ? activeTab.content : null}
      </div>
    </div>
  );
}

"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import {
  NAV_CONFIG,
  NavSection,
  NavStandaloneLink,
  NavClusterHeader,
  isItemActive,
  getSectionIdForPath,
} from "./nav-config";

// ── Storage keys ──────────────────────────────────────────────────────────────

const STORAGE_COLLAPSED = "erp_sidebar_collapsed";
const STORAGE_EXPANDED  = "erp_sidebar_expanded";

// ── Chevron ───────────────────────────────────────────────────────────────────

function Chevron({ open }: { open: boolean }) {
  return (
    <svg
      className="h-3 w-3 shrink-0 transition-transform duration-200"
      style={{ transform: open ? "rotate(90deg)" : "rotate(0deg)" }}
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
    >
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M9 5l7 7-7 7" />
    </svg>
  );
}

// ── Tooltip ───────────────────────────────────────────────────────────────────

function Tooltip({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="group/tip relative flex items-center w-full">
      {children}
      <div className="pointer-events-none absolute left-full z-[9999] ml-3.5 whitespace-nowrap rounded-md bg-[#1e2d45] border border-white/[0.1] px-2.5 py-1.5 text-[12px] font-medium text-slate-200 shadow-xl opacity-0 group-hover/tip:opacity-100 transition-opacity duration-100">
        {label}
        <span className="absolute top-1/2 -left-1.5 -translate-y-1/2 border-[5px] border-transparent border-r-[#1e2d45]" />
      </div>
    </div>
  );
}

// ── Avatar ────────────────────────────────────────────────────────────────────

function Avatar({ name }: { name: string }) {
  const initials = name
    .split(" ")
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase() ?? "")
    .join("");
  return (
    <div className="h-7 w-7 shrink-0 rounded-full bg-indigo-600/25 ring-1 ring-indigo-500/30 flex items-center justify-center text-[11px] font-bold text-indigo-300 select-none">
      {initials || "?"}
    </div>
  );
}

// ── Cluster header (expanded only) ────────────────────────────────────────────

function ClusterLabel({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-2.5 px-3 pt-[18px] pb-[5px]">
      <span className="text-[9.5px] font-semibold tracking-[0.14em] text-slate-600 uppercase select-none whitespace-nowrap">
        {label}
      </span>
      <div className="flex-1 h-px bg-white/[0.055]" />
    </div>
  );
}

// ── Section group ─────────────────────────────────────────────────────────────

interface SectionProps {
  section: NavSection;
  collapsed: boolean;
  pathname: string;
  isExpanded: boolean;
  onToggle: () => void;
  onExpandSidebar: () => void;
  onNavigate: () => void;
  hasPermission: (code: string) => boolean;
}

function SectionGroup({
  section,
  collapsed,
  pathname,
  isExpanded,
  onToggle,
  onExpandSidebar,
  onNavigate,
  hasPermission,
}: SectionProps) {
  const visibleItems = section.items.filter(
    (item) => !item.permission || hasPermission(item.permission)
  );
  if (visibleItems.length === 0) return null;

  const hasActiveChild = visibleItems.some((item) => isItemActive(item.href, pathname));

  // ── Collapsed icon rail ──────────────────────────────────────────────────────
  if (collapsed) {
    return (
      <Tooltip label={section.label}>
        <button
          onClick={() => {
            onExpandSidebar();
            if (!isExpanded) onToggle();
          }}
          className={[
            "flex h-9 w-9 items-center justify-center rounded-lg transition-all duration-200",
            hasActiveChild
              ? "bg-cyan-500/[0.14] text-cyan-300 border border-cyan-500/[0.30]"
              : "text-slate-500 hover:bg-white/[0.06] hover:text-slate-300 border border-transparent",
          ].join(" ")}
          style={hasActiveChild ? { boxShadow: "0 0 12px rgba(0,180,255,0.30)" } : undefined}
        >
          {section.icon}
        </button>
      </Tooltip>
    );
  }

  // ── Expanded section ─────────────────────────────────────────────────────────
  return (
    <div>
      {/* Section header button */}
      <button
        onClick={onToggle}
        className={[
          "group/hdr flex w-full items-center gap-2.5 rounded-lg px-2.5 py-[8px] text-left transition-all duration-150",
          hasActiveChild
            ? "text-slate-200 hover:bg-white/[0.04]"
            : "text-slate-500 hover:bg-white/[0.04] hover:text-slate-300",
        ].join(" ")}
      >
        {/* Icon */}
        <span
          className={[
            "shrink-0 transition-colors",
            hasActiveChild
              ? "text-indigo-400"
              : "text-slate-600 group-hover/hdr:text-slate-400",
          ].join(" ")}
        >
          {section.icon}
        </span>

        {/* Label */}
        <span className="flex-1 text-[12.5px] font-medium leading-none truncate">
          {section.label}
        </span>

        {/* Active-but-collapsed indicator dot */}
        {hasActiveChild && !isExpanded && (
          <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-indigo-400" />
        )}

        {/* Chevron */}
        <span
          className={[
            "shrink-0 transition-colors",
            hasActiveChild ? "text-slate-400" : "text-slate-700 group-hover/hdr:text-slate-500",
          ].join(" ")}
        >
          <Chevron open={isExpanded} />
        </span>
      </button>

      {/* Animated item list — grid-template-rows trick for smooth auto-height */}
      <div
        style={{
          display: "grid",
          gridTemplateRows: isExpanded ? "1fr" : "0fr",
          transition: "grid-template-rows 0.22s ease",
        }}
      >
        <div style={{ overflow: "hidden" }}>
          <div className="pb-1 pt-0.5">
            {visibleItems.map((item) => {
              const active = isItemActive(item.href, pathname);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={onNavigate}
                  className={[
                    "relative flex items-center border-l-[2px] py-[6px] pl-[28px] pr-2.5",
                    "text-[12.5px] leading-snug rounded-r-lg transition-all duration-150",
                    active
                      ? "border-cyan-400 bg-cyan-500/[0.10] text-cyan-100 font-medium"
                      : "border-transparent text-slate-500 hover:bg-white/[0.045] hover:text-slate-300",
                  ].join(" ")}
                  style={active ? {
                    boxShadow: "inset 3px 0 10px rgba(0,180,255,0.15), -1px 0 12px rgba(0,180,255,0.25)",
                    textShadow: "0 0 8px rgba(0,200,255,0.35)",
                  } : undefined}
                >
                  {item.label}
                </Link>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Standalone link ───────────────────────────────────────────────────────────

function StandaloneLink({
  entry,
  collapsed,
  pathname,
  hasPermission,
  onNavigate,
}: {
  entry: NavStandaloneLink;
  collapsed: boolean;
  pathname: string;
  hasPermission: (code: string) => boolean;
  onNavigate: () => void;
}) {
  if (entry.permission && !hasPermission(entry.permission)) return null;
  const active = isItemActive(entry.href, pathname);

  if (collapsed) {
    return (
      <Tooltip label={entry.label}>
        <Link
          href={entry.href}
          onClick={onNavigate}
          className={[
            "flex h-9 w-9 items-center justify-center rounded-lg transition-all duration-200",
            active
              ? "bg-cyan-500/[0.15] text-cyan-300 border border-cyan-500/[0.35]"
              : "text-slate-500 hover:bg-white/[0.06] hover:text-slate-300 border border-transparent",
          ].join(" ")}
          style={active ? { boxShadow: "0 0 14px rgba(0,180,255,0.35)" } : undefined}
        >
          {entry.icon}
        </Link>
      </Tooltip>
    );
  }

  return (
    <Link
      href={entry.href}
      onClick={onNavigate}
      className={[
        "flex items-center gap-2.5 rounded-lg px-2.5 py-[9px]",
        "text-[12.5px] font-medium transition-all duration-200",
        active
          ? "bg-cyan-500/[0.12] text-cyan-100 border border-cyan-500/[0.30]"
          : "text-slate-400 hover:bg-white/[0.045] hover:text-slate-200 border border-transparent",
      ].join(" ")}
      style={active ? {
        boxShadow: "0 0 14px rgba(0,180,255,0.30), inset 0 1px 0 rgba(0,200,255,0.10)",
        textShadow: "0 0 8px rgba(0,200,255,0.35)",
      } : undefined}
    >
      <span className={active ? "text-cyan-300" : "text-slate-500"}>{entry.icon}</span>
      {entry.label}
    </Link>
  );
}

// ── Collapsed cluster divider ─────────────────────────────────────────────────

function CollapsedClusterDivider() {
  return <div className="my-2 mx-auto h-px w-5 bg-white/[0.07]" />;
}

// ── Collapse toggle ───────────────────────────────────────────────────────────

function CollapseToggle({ collapsed, onToggle }: { collapsed: boolean; onToggle: () => void }) {
  return (
    <button
      onClick={onToggle}
      title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
      className="flex h-7 w-7 items-center justify-center rounded-md text-slate-600 hover:bg-white/[0.07] hover:text-slate-300 transition-colors"
    >
      <svg className="h-[15px] w-[15px]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        {collapsed ? (
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M13 5l7 7-7 7M5 5l7 7-7 7" />
        ) : (
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
        )}
      </svg>
    </button>
  );
}

// ── Main Sidebar ──────────────────────────────────────────────────────────────

interface SidebarProps {
  mobileOpen: boolean;
  onMobileClose: () => void;
  onOpenSearch?: () => void;
}

export function Sidebar({ mobileOpen, onMobileClose, onOpenSearch }: SidebarProps) {
  const pathname = usePathname();
  const { user, logout, hasPermission } = useAuth();

  const [collapsed, setCollapsed] = useState(false);
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set());
  const [mounted, setMounted] = useState(false);

  // Hydrate from localStorage after mount
  useEffect(() => {
    const savedCollapsed = localStorage.getItem(STORAGE_COLLAPSED);
    if (savedCollapsed !== null) setCollapsed(savedCollapsed === "true");

    const savedExpanded = localStorage.getItem(STORAGE_EXPANDED);
    const base: Set<string> = savedExpanded
      ? new Set<string>(JSON.parse(savedExpanded))
      : new Set<string>();

    const activeSection = getSectionIdForPath(pathname);
    if (activeSection) base.add(activeSection);

    setExpandedSections(base);
    setMounted(true);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Auto-expand active section on route change
  useEffect(() => {
    if (!mounted) return;
    const activeSection = getSectionIdForPath(pathname);
    if (activeSection) {
      setExpandedSections((prev) => {
        if (prev.has(activeSection)) return prev;
        const next = new Set(prev);
        next.add(activeSection);
        localStorage.setItem(STORAGE_EXPANDED, JSON.stringify(Array.from(next)));
        return next;
      });
    }
  }, [pathname, mounted]);

  const toggleCollapsed = useCallback(() => {
    setCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem(STORAGE_COLLAPSED, String(next));
      return next;
    });
  }, []);

  const expandSidebar = useCallback(() => {
    setCollapsed(false);
    localStorage.setItem(STORAGE_COLLAPSED, "false");
  }, []);

  const toggleSection = useCallback((id: string) => {
    setExpandedSections((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      localStorage.setItem(STORAGE_EXPANDED, JSON.stringify(Array.from(next)));
      return next;
    });
  }, []);

  // Close mobile on navigation
  const handleNavigate = useCallback(() => {
    onMobileClose();
  }, [onMobileClose]);

  const can = (permission?: string) => !permission || hasPermission(permission);

  // ── Render ────────────────────────────────────────────────────────────────────

  return (
    <aside
      className={[
        // Base
        "flex h-screen flex-col",
        "bg-[#0b1120]",
        "border-r border-white/[0.065]",
        "transition-[width,transform] duration-200 ease-in-out",
        // Desktop: static sidebar that shrinks/expands
        "relative",
        // Desktop width
        collapsed ? "w-[52px]" : "w-[228px]",
        // Mobile: fixed overlay controlled by mobileOpen
        "max-lg:fixed max-lg:inset-y-0 max-lg:left-0 max-lg:z-50 max-lg:w-[228px]",
        mobileOpen ? "max-lg:translate-x-0" : "max-lg:-translate-x-full",
      ]
        .join(" ")}
      style={{ flexShrink: 0 }}
    >
      {/* ── Logo / Header ──────────────────────────────────────────────────────── */}
      <div
        className={[
          "flex h-[52px] shrink-0 items-center border-b border-white/[0.065]",
          collapsed ? "justify-center px-0" : "justify-between px-3.5",
        ].join(" ")}
      >
        {collapsed ? (
          <button
            onClick={expandSidebar}
            title="Expand sidebar"
            className="group flex items-center justify-center"
          >
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-[10px] font-bold text-white tracking-tight shadow-lg shadow-indigo-900/50 group-hover:bg-indigo-500 transition-colors">
              ERP
            </div>
          </button>
        ) : (
          <>
            <div className="flex items-center gap-2.5 min-w-0">
              <div className="flex h-[28px] w-[28px] shrink-0 items-center justify-center rounded-[7px] bg-indigo-600 text-[9.5px] font-bold text-white shadow-md shadow-indigo-900/40">
                ERP
              </div>
              <div className="min-w-0 leading-none">
                <p className="text-[13px] font-semibold text-white tracking-tight truncate">
                  FMCG ERP
                </p>
                <p className="text-[10px] text-slate-500 tracking-wide mt-[3px] truncate">
                  Enterprise Suite
                </p>
              </div>
            </div>
            <CollapseToggle collapsed={collapsed} onToggle={toggleCollapsed} />
          </>
        )}
      </div>

      {/* ── Search trigger ─────────────────────────────────────────────────────── */}
      {onOpenSearch && !collapsed && (
        <div className="px-2 pt-2 pb-1 shrink-0">
          <button
            onClick={onOpenSearch}
            className="w-full flex items-center gap-2 rounded-lg px-2.5 py-2 text-slate-500 hover:text-slate-300 hover:bg-white/[0.05] border border-white/[0.06] transition-all text-[12px] group"
          >
            <svg className="h-3.5 w-3.5 shrink-0 text-slate-600 group-hover:text-slate-400 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <span className="flex-1 text-left truncate">Search…</span>
            <kbd className="text-[9px] font-mono bg-white/[0.04] border border-white/[0.07] rounded px-1 py-0.5 text-slate-600 shrink-0">⌘K</kbd>
          </button>
        </div>
      )}
      {onOpenSearch && collapsed && (
        <div className="px-[7px] pt-1.5 pb-0.5 shrink-0 flex justify-center">
          <Tooltip label="Search (Ctrl+K)">
            <button
              onClick={onOpenSearch}
              className="flex h-9 w-9 items-center justify-center rounded-lg text-slate-600 hover:bg-white/[0.06] hover:text-slate-300 border border-transparent transition-all"
            >
              <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </button>
          </Tooltip>
        </div>
      )}

      {/* ── Navigation ─────────────────────────────────────────────────────────── */}
      <nav
        className={[
          "flex-1 overflow-y-auto overflow-x-hidden py-2",
          collapsed
            ? "px-[7px] flex flex-col items-center gap-0.5"
            : "px-2 space-y-[1px]",
        ].join(" ")}
        style={{ scrollbarWidth: "none" }}
      >
        {NAV_CONFIG.map((entry) => {
          const key = entry.id;

          // ── Cluster header ────────────────────────────────────────────────────
          if (entry.type === "cluster-header") {
            if (collapsed) {
              return <CollapsedClusterDivider key={key} />;
            }
            return (
              <ClusterLabel key={key} label={(entry as NavClusterHeader).label} />
            );
          }

          // ── Standalone link ───────────────────────────────────────────────────
          if (entry.type === "link") {
            return (
              <StandaloneLink
                key={key}
                entry={entry as NavStandaloneLink}
                collapsed={collapsed}
                pathname={pathname}
                hasPermission={can}
                onNavigate={handleNavigate}
              />
            );
          }

          // ── Section group ─────────────────────────────────────────────────────
          const section = entry as NavSection;
          if (section.permission && !can(section.permission)) {
            const anyVisible = section.items.some((i) => !i.permission || can(i.permission));
            if (!anyVisible) return null;
          }

          return (
            <SectionGroup
              key={key}
              section={section}
              collapsed={collapsed}
              pathname={pathname}
              isExpanded={expandedSections.has(section.id)}
              onToggle={() => toggleSection(section.id)}
              onExpandSidebar={expandSidebar}
              onNavigate={handleNavigate}
              hasPermission={can}
            />
          );
        })}

        {/* Bottom padding */}
        <div className="h-3" />
      </nav>

      {/* ── User footer ────────────────────────────────────────────────────────── */}
      <div
        className={[
          "shrink-0 border-t border-white/[0.065] bg-[#080f1b]",
          collapsed
            ? "flex flex-col items-center gap-2 py-3 px-[7px]"
            : "px-3 py-3",
        ].join(" ")}
      >
        {collapsed ? (
          <>
            <Tooltip label={user?.full_name ?? "User"}>
              <div className="cursor-default">
                <Avatar name={user?.full_name ?? "?"} />
              </div>
            </Tooltip>
            <Tooltip label="Sign out">
              <button
                onClick={logout}
                className="flex h-7 w-7 items-center justify-center rounded-md text-slate-600 hover:bg-white/[0.06] hover:text-red-400 transition-colors"
              >
                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8}
                    d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                </svg>
              </button>
            </Tooltip>
          </>
        ) : (
          <div className="flex items-center gap-2.5">
            <Avatar name={user?.full_name ?? "?"} />
            <div className="min-w-0 flex-1 leading-none">
              <p className="text-[12px] font-semibold text-slate-300 truncate">
                {user?.full_name ?? "—"}
              </p>
              <p className="text-[11px] text-slate-600 mt-[3px] truncate">
                {user?.email ?? ""}
              </p>
            </div>
            <button
              onClick={logout}
              title="Sign out"
              className="shrink-0 rounded-md p-[5px] text-slate-600 hover:bg-white/[0.07] hover:text-red-400 transition-colors"
            >
              <svg className="h-[14px] w-[14px]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8}
                  d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
              </svg>
            </button>
          </div>
        )}
      </div>
    </aside>
  );
}

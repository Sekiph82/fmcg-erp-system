"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import {
  NAV_CONFIG,
  NavSection,
  NavStandaloneLink,
  NavClusterHeader,
  isItemActive,
} from "./nav-config";

// ── Storage keys ──────────────────────────────────────────────────────────────

const STORAGE_COLLAPSED = "erp_sidebar_collapsed";
const STORAGE_CLUSTER   = "erp_sidebar_cluster_v1";  // which of the 14 clusters is open
const STORAGE_SECTION   = "erp_sidebar_section_v1";  // which section inside that cluster is open

// ── Pre-process NAV_CONFIG into grouped structure (runs once at module level) ─

interface ClusterData {
  clusterId: string;
  label: string;
  sections: NavSection[];
}

type Group =
  | { kind: "standalone"; entry: NavStandaloneLink }
  | { kind: "cluster";    data: ClusterData };

const GROUPS: Group[] = (() => {
  const result: Group[] = [];
  let cur: ClusterData | null = null;

  for (const entry of NAV_CONFIG) {
    if (entry.type === "link") {
      cur = null;
      result.push({ kind: "standalone", entry: entry as NavStandaloneLink });
    } else if (entry.type === "cluster-header") {
      const ch = entry as NavClusterHeader;
      cur = { clusterId: ch.id, label: ch.label, sections: [] };
      result.push({ kind: "cluster", data: cur });
    } else if (entry.type === "section" && cur) {
      cur.sections.push(entry as NavSection);
    }
  }

  return result;
})();

// Return the cluster + section IDs that contain the active path
function findActive(pathname: string): { clusterId: string | null; sectionId: string | null } {
  for (const group of GROUPS) {
    if (group.kind !== "cluster") continue;
    for (const section of group.data.sections) {
      if (section.items.some((item) => isItemActive(item.href, pathname))) {
        return { clusterId: group.data.clusterId, sectionId: section.id };
      }
    }
  }
  return { clusterId: null, sectionId: null };
}

// ── Chevron ───────────────────────────────────────────────────────────────────

function Chevron({ open }: { open: boolean }) {
  return (
    <svg
      className="h-3 w-3 shrink-0 transition-transform duration-200"
      style={{ transform: open ? "rotate(90deg)" : "rotate(0deg)" }}
      fill="none" stroke="currentColor" viewBox="0 0 24 24"
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
  const initials = name.split(" ").slice(0, 2).map((w) => w[0]?.toUpperCase() ?? "").join("");
  return (
    <div className="h-7 w-7 shrink-0 rounded-full bg-indigo-600/25 ring-1 ring-indigo-500/30 flex items-center justify-center text-[11px] font-bold text-indigo-300 select-none">
      {initials || "?"}
    </div>
  );
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
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 5l7 7-7 7M5 5l7 7-7 7" />
        ) : (
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
        )}
      </svg>
    </button>
  );
}

// ── Standalone link (Dashboard) ───────────────────────────────────────────────

function StandaloneLink({
  entry, collapsed, pathname, hasPermission, onNavigate,
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
        "flex items-center gap-2.5 rounded-lg px-2.5 py-[8px] text-[12.5px] font-medium transition-all duration-200",
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

// ── Section accordion (second level, within an open cluster) ─────────────────

function SectionAccordion({
  section, pathname, isExpanded, onToggle, hasPermission, onNavigate,
}: {
  section: NavSection;
  pathname: string;
  isExpanded: boolean;
  onToggle: () => void;
  hasPermission: (code: string) => boolean;
  onNavigate: () => void;
}) {
  const visibleItems = section.items.filter(
    (item) => !item.permission || hasPermission(item.permission)
  );
  if (visibleItems.length === 0) return null;

  const hasActiveChild = visibleItems.some((item) => isItemActive(item.href, pathname));

  return (
    <div>
      {/* Section header — second accordion level */}
      <button
        onClick={onToggle}
        aria-expanded={isExpanded}
        className={[
          "group/sec flex w-full items-center gap-2 rounded-lg px-2.5 py-[6px] pl-[14px] text-left transition-all duration-150",
          hasActiveChild
            ? "text-slate-300 hover:bg-white/[0.03]"
            : "text-slate-500 hover:bg-white/[0.03] hover:text-slate-400",
        ].join(" ")}
      >
        <span
          className={[
            "shrink-0 transition-colors",
            hasActiveChild ? "text-indigo-400" : "text-slate-600 group-hover/sec:text-slate-500",
          ].join(" ")}
        >
          {section.icon}
        </span>
        <span className="flex-1 text-[12px] font-medium leading-none truncate">
          {section.label}
        </span>
        {hasActiveChild && !isExpanded && (
          <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-indigo-400" />
        )}
        <span
          className={[
            "shrink-0 transition-colors",
            hasActiveChild ? "text-slate-400" : "text-slate-700 group-hover/sec:text-slate-600",
          ].join(" ")}
        >
          <Chevron open={isExpanded} />
        </span>
      </button>

      {/* Section items — animated */}
      <div
        style={{
          display: "grid",
          gridTemplateRows: isExpanded ? "1fr" : "0fr",
          transition: "grid-template-rows 0.18s ease",
        }}
      >
        <div style={{ overflow: "hidden" }}>
          <div className="pb-0.5 pt-0.5">
            {visibleItems.map((item) => {
              const active = isItemActive(item.href, pathname);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={onNavigate}
                  className={[
                    "relative flex items-center border-l-[2px] py-[5px] pl-[34px] pr-2.5",
                    "text-[11.5px] leading-snug rounded-r-lg transition-all duration-150",
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

// ── Cluster accordion (first level — the 14 main categories) ─────────────────

interface ClusterAccordionProps {
  data: ClusterData;
  isExpanded: boolean;
  expandedSection: string | null;
  onToggleCluster: () => void;
  onToggleSection: (id: string) => void;
  collapsed: boolean;
  pathname: string;
  hasPermission: (code: string) => boolean;
  onExpandSidebar: () => void;
  onNavigate: () => void;
}

function ClusterAccordion({
  data, isExpanded, expandedSection, onToggleCluster, onToggleSection,
  collapsed, pathname, hasPermission, onExpandSidebar, onNavigate,
}: ClusterAccordionProps) {
  const visibleSections = data.sections.filter((sec) =>
    sec.items.some((item) => !item.permission || hasPermission(item.permission))
  );
  if (visibleSections.length === 0) return null;

  const hasActiveChild = visibleSections.some((sec) =>
    sec.items.some(
      (item) => (!item.permission || hasPermission(item.permission)) && isItemActive(item.href, pathname)
    )
  );

  // Use the first section's icon as representative cluster icon
  const clusterIcon = visibleSections[0]?.icon;

  // ── Collapsed icon rail (sidebar fully collapsed) ─────────────────────────
  if (collapsed) {
    return (
      <Tooltip label={data.label}>
        <button
          onClick={() => {
            onExpandSidebar();
            if (!isExpanded) onToggleCluster();
          }}
          className={[
            "flex h-9 w-9 items-center justify-center rounded-lg transition-all duration-200",
            hasActiveChild
              ? "bg-cyan-500/[0.14] text-cyan-300 border border-cyan-500/[0.30]"
              : "text-slate-500 hover:bg-white/[0.06] hover:text-slate-300 border border-transparent",
          ].join(" ")}
          style={hasActiveChild ? { boxShadow: "0 0 12px rgba(0,180,255,0.30)" } : undefined}
        >
          {clusterIcon}
        </button>
      </Tooltip>
    );
  }

  // ── Expanded sidebar ──────────────────────────────────────────────────────
  return (
    <div>
      {/* Cluster header button — this IS one of the 14 main categories */}
      <button
        onClick={onToggleCluster}
        aria-expanded={isExpanded}
        className={[
          "group/cl flex w-full items-center gap-2.5 rounded-lg px-2.5 py-[7px] text-left transition-all duration-150",
          hasActiveChild
            ? "text-slate-200 hover:bg-white/[0.04]"
            : "text-slate-500 hover:bg-white/[0.04] hover:text-slate-300",
        ].join(" ")}
      >
        {/* Cluster icon */}
        <span
          className={[
            "shrink-0 transition-colors",
            hasActiveChild ? "text-indigo-400" : "text-slate-600 group-hover/cl:text-slate-400",
          ].join(" ")}
        >
          {clusterIcon}
        </span>

        {/* Cluster label */}
        <span className="flex-1 text-[12.5px] font-semibold leading-none truncate">
          {data.label}
        </span>

        {/* Active indicator dot — shows when cluster is closed but has active child */}
        {hasActiveChild && !isExpanded && (
          <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-indigo-400" />
        )}

        {/* Chevron */}
        <span
          className={[
            "shrink-0 transition-colors",
            hasActiveChild ? "text-slate-400" : "text-slate-700 group-hover/cl:text-slate-500",
          ].join(" ")}
        >
          <Chevron open={isExpanded} />
        </span>
      </button>

      {/* Animated content: sections within this cluster */}
      <div
        style={{
          display: "grid",
          gridTemplateRows: isExpanded ? "1fr" : "0fr",
          transition: "grid-template-rows 0.20s ease",
        }}
      >
        <div style={{ overflow: "hidden" }}>
          <div className="pb-1 pt-0.5 ml-[3px] border-l border-white/[0.06]">
            {visibleSections.map((section) => (
              <SectionAccordion
                key={section.id}
                section={section}
                pathname={pathname}
                isExpanded={expandedSection === section.id}
                onToggle={() => onToggleSection(section.id)}
                hasPermission={hasPermission}
                onNavigate={onNavigate}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
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

  const [collapsed,       setCollapsed]       = useState(false);
  const [expandedCluster, setExpandedCluster] = useState<string | null>(null);
  const [expandedSection, setExpandedSection] = useState<string | null>(null);
  const [mounted,         setMounted]         = useState(false);

  // ── Hydrate from localStorage + auto-expand based on current route ────────────
  useEffect(() => {
    const savedCollapsed = localStorage.getItem(STORAGE_COLLAPSED);
    if (savedCollapsed !== null) setCollapsed(savedCollapsed === "true");

    const { clusterId, sectionId } = findActive(pathname);
    if (clusterId) {
      // Route wins: expand the cluster + section the user is currently in
      setExpandedCluster(clusterId);
      setExpandedSection(sectionId);
    } else {
      // No active route in any section — restore the last manually opened state
      setExpandedCluster(localStorage.getItem(STORAGE_CLUSTER) ?? null);
      setExpandedSection(localStorage.getItem(STORAGE_SECTION) ?? null);
    }

    setMounted(true);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Auto-expand when route changes ────────────────────────────────────────────
  useEffect(() => {
    if (!mounted) return;
    const { clusterId, sectionId } = findActive(pathname);
    if (clusterId) {
      setExpandedCluster(clusterId);
      setExpandedSection(sectionId);
      localStorage.setItem(STORAGE_CLUSTER, clusterId);
      if (sectionId) localStorage.setItem(STORAGE_SECTION, sectionId);
      else localStorage.removeItem(STORAGE_SECTION);
    }
  // expandedCluster / expandedSection intentionally omitted — react only to route changes
  // eslint-disable-next-line react-hooks/exhaustive-deps
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

  // Open clicked cluster; close it if already open. Reset section when switching clusters.
  const toggleCluster = useCallback((id: string) => {
    setExpandedCluster((prev) => {
      const next = prev === id ? null : id;
      if (next) localStorage.setItem(STORAGE_CLUSTER, next);
      else localStorage.removeItem(STORAGE_CLUSTER);
      // Clear section selection when closing or switching clusters
      if (next !== prev) {
        setExpandedSection(null);
        localStorage.removeItem(STORAGE_SECTION);
      }
      return next;
    });
  }, []);

  // Toggle section within the currently open cluster
  const toggleSection = useCallback((id: string) => {
    setExpandedSection((prev) => {
      const next = prev === id ? null : id;
      if (next) localStorage.setItem(STORAGE_SECTION, next);
      else localStorage.removeItem(STORAGE_SECTION);
      return next;
    });
  }, []);

  const handleNavigate = useCallback(() => {
    onMobileClose();
  }, [onMobileClose]);

  const can = (permission?: string) => !permission || hasPermission(permission);

  // ── Render ────────────────────────────────────────────────────────────────────

  return (
    <aside
      className={[
        "flex h-screen flex-col bg-[#0b1120] border-r border-white/[0.065]",
        "transition-[width,transform] duration-200 ease-in-out relative",
        collapsed ? "w-[52px]" : "w-[228px]",
        "max-lg:fixed max-lg:inset-y-0 max-lg:left-0 max-lg:z-50 max-lg:w-[228px]",
        mobileOpen ? "max-lg:translate-x-0" : "max-lg:-translate-x-full",
      ].join(" ")}
      style={{ flexShrink: 0 }}
    >
      {/* ── Logo / Header ─────────────────────────────────────────────────────── */}
      <div
        className={[
          "flex h-[52px] shrink-0 items-center border-b border-white/[0.065]",
          collapsed ? "justify-center px-0" : "justify-between px-3.5",
        ].join(" ")}
      >
        {collapsed ? (
          <button onClick={expandSidebar} title="Expand sidebar" className="group flex items-center justify-center">
            {/* POVU logo icon — circular crop in collapsed mode */}
            <div className="h-8 w-8 rounded-lg overflow-hidden shadow-lg group-hover:opacity-90 transition-opacity">
              <img
                src="/povu-logo.jpg"
                alt="POVU"
                className="h-full w-full object-cover"
              />
            </div>
          </button>
        ) : (
          <>
            <div className="flex items-center gap-2.5 min-w-0">
              {/* POVU logo — replaces the purple ERP square */}
              <div className="h-[28px] w-[28px] shrink-0 rounded-[7px] overflow-hidden shadow-md">
                <img
                  src="/povu-logo.jpg"
                  alt="POVU"
                  className="h-full w-full object-cover"
                />
              </div>
              <div className="min-w-0 leading-none">
                <p className="text-[13px] font-semibold text-white tracking-tight truncate">POVU ERP</p>
                <p className="text-[10px] text-slate-500 tracking-wide mt-[3px] truncate">Enterprise Suite</p>
              </div>
            </div>
            <CollapseToggle collapsed={collapsed} onToggle={toggleCollapsed} />
          </>
        )}
      </div>

      {/* ── Search trigger ────────────────────────────────────────────────────── */}
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

      {/* ── Navigation ───────────────────────────────────────────────────────── */}
      <nav
        className={[
          "flex-1 overflow-y-auto overflow-x-hidden py-2",
          collapsed
            ? "px-[7px] flex flex-col items-center gap-0.5"
            : "px-2 space-y-[1px]",
        ].join(" ")}
        style={{ scrollbarWidth: "none" }}
      >
        {GROUPS.map((group) => {
          if (group.kind === "standalone") {
            return (
              <StandaloneLink
                key={group.entry.id}
                entry={group.entry}
                collapsed={collapsed}
                pathname={pathname}
                hasPermission={can}
                onNavigate={handleNavigate}
              />
            );
          }

          // cluster
          return (
            <ClusterAccordion
              key={group.data.clusterId}
              data={group.data}
              isExpanded={expandedCluster === group.data.clusterId}
              expandedSection={
                expandedCluster === group.data.clusterId ? expandedSection : null
              }
              onToggleCluster={() => toggleCluster(group.data.clusterId)}
              onToggleSection={toggleSection}
              collapsed={collapsed}
              pathname={pathname}
              hasPermission={can}
              onExpandSidebar={expandSidebar}
              onNavigate={handleNavigate}
            />
          );
        })}

        <div className="h-3" />
      </nav>

      {/* ── User footer ──────────────────────────────────────────────────────── */}
      <div
        className={[
          "shrink-0 border-t border-white/[0.065] bg-[#080f1b]",
          collapsed ? "flex flex-col items-center gap-2 py-3 px-[7px]" : "px-3 py-3",
        ].join(" ")}
      >
        {collapsed ? (
          <>
            <Tooltip label={user?.full_name ?? "User"}>
              <div className="cursor-default"><Avatar name={user?.full_name ?? "?"} /></div>
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
              <p className="text-[12px] font-semibold text-slate-300 truncate">{user?.full_name ?? "—"}</p>
              <p className="text-[11px] text-slate-600 mt-[3px] truncate">{user?.email ?? ""}</p>
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

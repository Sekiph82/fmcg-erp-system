"use client";

import React from "react";

interface SectionCardProps {
  title: string;
  icon?: string;
  children: React.ReactNode;
  badge?: React.ReactNode;
  className?: string;
}

export function SectionCard({ title, icon, children, badge, className = "" }: SectionCardProps) {
  return (
    <div className={`rounded-2xl bg-white border border-gray-100 shadow-sm overflow-hidden ${className}`}>
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-50">
        <div className="flex items-center gap-2">
          {icon && <span className="text-base">{icon}</span>}
          <h3 className="text-sm font-bold text-gray-800 uppercase tracking-wide">{title}</h3>
        </div>
        {badge && <div>{badge}</div>}
      </div>
      <div className="p-4">{children}</div>
    </div>
  );
}

export function StatusPill({
  value,
  label,
  status,
}: {
  value: string | number;
  label: string;
  status: "ok" | "warning" | "critical" | "neutral";
}) {
  const colors = {
    ok: "text-emerald-700 bg-emerald-50",
    warning: "text-amber-700 bg-amber-50",
    critical: "text-red-700 bg-red-50",
    neutral: "text-gray-700 bg-gray-50",
  };
  return (
    <div className={`flex flex-col items-center rounded-lg p-2 ${colors[status]}`}>
      <span className="text-lg font-bold leading-none">{value}</span>
      <span className="text-[11px] font-medium mt-0.5 text-center leading-tight">{label}</span>
    </div>
  );
}

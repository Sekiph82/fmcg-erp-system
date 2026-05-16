"use client";

import { useAuth } from "@/context/AuthContext";

interface ActionDef {
  label: string;
  onClick: () => void;
  permission?: string;
  variant?: "primary" | "secondary";
}

interface WorkspaceHeaderProps {
  title: string;
  description?: string;
  actions?: ActionDef[];
  badge?: string;
}

export function WorkspaceHeader({ title, description, actions = [], badge }: WorkspaceHeaderProps) {
  const { hasPermission } = useAuth();

  const visibleActions = actions.filter(
    (a) => !a.permission || hasPermission(a.permission)
  );

  return (
    <div className="flex items-center justify-between px-6 py-4 shrink-0 border-b border-cyan-500/20 bg-[rgba(15,23,42,0.70)] backdrop-blur-xl">
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <h1 className="text-lg font-semibold text-slate-100 truncate">{title}</h1>
          {badge && (
            <span className="inline-flex items-center rounded-full border border-blue-500/30 bg-blue-500/10 px-2 py-0.5 text-xs font-medium text-blue-300">
              {badge}
            </span>
          )}
        </div>
        {description && (
          <p className="mt-0.5 text-sm text-slate-400 truncate">{description}</p>
        )}
      </div>

      {visibleActions.length > 0 && (
        <div className="flex items-center gap-2 ml-4 shrink-0">
          {visibleActions.map((action, i) => (
            <button
              key={i}
              onClick={action.onClick}
              className={
                action.variant === "secondary"
                  ? "glow-button-secondary text-sm"
                  : "glow-button text-sm"
              }
            >
              {action.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

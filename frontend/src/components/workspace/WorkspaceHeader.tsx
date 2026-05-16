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
    <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 bg-white shrink-0">
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <h1 className="text-lg font-semibold text-gray-900 truncate">{title}</h1>
          {badge && (
            <span className="inline-flex items-center rounded-full bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700">
              {badge}
            </span>
          )}
        </div>
        {description && (
          <p className="mt-0.5 text-sm text-gray-500 truncate">{description}</p>
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

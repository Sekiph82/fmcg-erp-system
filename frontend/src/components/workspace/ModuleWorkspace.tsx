"use client";

import { useAuth } from "@/context/AuthContext";
import { WorkspaceHeader } from "./WorkspaceHeader";
import { WorkspaceTabs, WorkspaceTab } from "./WorkspaceTabs";

interface ActionDef {
  label: string;
  onClick: () => void;
  permission?: string;
  variant?: "primary" | "secondary";
}

interface ModuleWorkspaceProps {
  title: string;
  description?: string;
  permission?: string;
  badge?: string;
  actions?: ActionDef[];
  tabs: WorkspaceTab[];
  defaultTab?: string;
}

export function ModuleWorkspace({
  title,
  description,
  permission,
  badge,
  actions,
  tabs,
  defaultTab,
}: ModuleWorkspaceProps) {
  const { hasPermission } = useAuth();

  if (permission && !hasPermission(permission)) {
    return (
      <div className="flex flex-col items-center justify-center h-full py-24 text-gray-400">
        <svg className="h-12 w-12 mb-3 opacity-40" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
        </svg>
        <p className="text-sm font-medium">Access restricted</p>
        <p className="text-xs mt-1">You do not have permission to view this module.</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full min-h-0">
      <WorkspaceHeader
        title={title}
        description={description}
        actions={actions}
        badge={badge}
      />
      <WorkspaceTabs tabs={tabs} defaultTab={defaultTab} />
    </div>
  );
}

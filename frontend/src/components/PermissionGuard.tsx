"use client";

import { useAuth } from "@/context/AuthContext";

interface Props {
  permission: string;
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

/**
 * Renders children only when the current user has the given permission code.
 * Superusers always pass through. Renders fallback (default: null) otherwise.
 */
export function PermissionGuard({ permission, children, fallback = null }: Props) {
  const { hasPermission } = useAuth();
  return hasPermission(permission) ? <>{children}</> : <>{fallback}</>;
}

/**
 * Full-page 403 guard. Use in page components to block entire pages.
 * Renders a 403 message instead of the page content when permission is missing.
 */
export function RequirePermission({ permission, children }: { permission: string; children: React.ReactNode }) {
  const { hasPermission, loading } = useAuth();

  if (loading) return null;

  if (!hasPermission(permission)) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-3 text-center" data-testid="access-denied">
        <div className="h-12 w-12 rounded-full bg-red-100 flex items-center justify-center">
          <svg className="h-6 w-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
          </svg>
        </div>
        <h2 className="text-lg font-semibold text-gray-800">Access Denied</h2>
        <p className="text-sm text-gray-500">
          You don&apos;t have permission to view this page.<br />
          Required: <code className="bg-gray-100 px-1 rounded text-xs">{permission}</code>
        </p>
      </div>
    );
  }

  return <>{children}</>;
}

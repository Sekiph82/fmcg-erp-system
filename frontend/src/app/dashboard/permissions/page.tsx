"use client";

import { useQuery } from "@tanstack/react-query";
import { rolesApi, groupByModule, STANDARD_ACTIONS } from "@/lib/roles";
import { getPermissionCoverage } from "@/lib/modules";

const MODULE_ORDER = [
  "users", "roles", "audit",
  "inventory", "products", "materials", "warehouses", "wms",
  "procurement", "sales", "finance", "mpesa",
  "production", "quality", "maintenance",
  "logistics", "tax", "integrations",
];

const ACTION_DISPLAY: Record<string, string> = {
  view: "View",
  create: "Create",
  edit: "Edit",
  delete: "Delete",
  approve: "Approve",
  export: "Export",
  initiate_payment: "Initiate",
  view_transactions: "View Txns",
  retry_transaction: "Retry",
  cancel_payment: "Cancel",
  reconcile_payment: "Reconcile",
  view_payment_logs: "Logs",
};

export default function PermissionsPage() {
  const { data: allPerms = [], isLoading: permsLoading } = useQuery({
    queryKey: ["permissions"],
    queryFn: () => rolesApi.listPermissions(),
  });

  const { data: roles = [], isLoading: rolesLoading } = useQuery({
    queryKey: ["roles"],
    queryFn: () => rolesApi.list(),
  });

  const { data: coverage, isLoading: coverageLoading } = useQuery({
    queryKey: ["permission-coverage"],
    queryFn: getPermissionCoverage,
  });

  const grouped = groupByModule(allPerms);

  // Sort modules by MODULE_ORDER, then alphabetically for any extras
  const sortedModules = [
    ...MODULE_ORDER.filter((m) => grouped[m]),
    ...Object.keys(grouped).filter((m) => !MODULE_ORDER.includes(m)).sort(),
  ];

  if (permsLoading || rolesLoading) {
    return (
      <div className="flex justify-center py-20">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" />
      </div>
    );
  }

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Permission Matrix</h1>
        <p className="text-sm text-gray-500 mt-1">
          {allPerms.length} permissions · {roles.length} roles
        </p>
      </div>

      {coverage && (
        <div className="mb-6 rounded-xl border border-gray-100 bg-white p-5 shadow-sm">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-sm font-semibold text-gray-800">Registry Coverage</h2>
              <p className="mt-1 text-xs text-gray-500">
                Backend registry permissions compared with database permissions.
              </p>
            </div>
            {coverage.missing_registry_permissions.length === 0 ? (
              <span className="rounded-full bg-green-50 px-3 py-1 text-xs font-semibold text-green-700">
                In sync
              </span>
            ) : (
              <span className="rounded-full bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-700">
                Review needed
              </span>
            )}
          </div>

          <div className="grid gap-3 md:grid-cols-4">
            <div className="rounded-lg border border-gray-100 bg-gray-50 p-3">
              <div className="text-xs font-medium text-gray-500">Registry</div>
              <div className="mt-1 text-xl font-semibold text-gray-900">
                {coverage.registry_permission_count}
              </div>
            </div>
            <div className="rounded-lg border border-gray-100 bg-gray-50 p-3">
              <div className="text-xs font-medium text-gray-500">Database</div>
              <div className="mt-1 text-xl font-semibold text-gray-900">
                {coverage.database_permission_count}
              </div>
            </div>
            <div className="rounded-lg border border-gray-100 bg-gray-50 p-3">
              <div className="text-xs font-medium text-gray-500">Covered</div>
              <div className="mt-1 text-xl font-semibold text-green-700">
                {coverage.covered_registry_permissions.length}
              </div>
            </div>
            <div className="rounded-lg border border-gray-100 bg-gray-50 p-3">
              <div className="text-xs font-medium text-gray-500">Missing</div>
              <div className="mt-1 text-xl font-semibold text-amber-700">
                {coverage.missing_registry_permissions.length}
              </div>
            </div>
          </div>

          {(coverage.missing_registry_permissions.length > 0 ||
            coverage.database_only_permissions.length > 0) && (
            <div className="mt-4 grid gap-4 lg:grid-cols-2">
              <div>
                <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
                  Missing Registry Permissions
                </h3>
                <div className="flex max-h-36 flex-wrap gap-1.5 overflow-auto rounded-lg border border-gray-100 bg-gray-50 p-3">
                  {coverage.missing_registry_permissions.slice(0, 24).map((code) => (
                    <span key={code} className="rounded bg-amber-100 px-2 py-0.5 font-mono text-xs text-amber-800">
                      {code}
                    </span>
                  ))}
                  {coverage.missing_registry_permissions.length === 0 && (
                    <span className="text-xs text-gray-400">None</span>
                  )}
                </div>
              </div>
              <div>
                <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
                  Database-Only Permissions
                </h3>
                <div className="flex max-h-36 flex-wrap gap-1.5 overflow-auto rounded-lg border border-gray-100 bg-gray-50 p-3">
                  {coverage.database_only_permissions.slice(0, 24).map((code) => (
                    <span key={code} className="rounded bg-blue-100 px-2 py-0.5 font-mono text-xs text-blue-800">
                      {code}
                    </span>
                  ))}
                  {coverage.database_only_permissions.length === 0 && (
                    <span className="text-xs text-gray-400">None</span>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {coverageLoading && (
        <div className="mb-6 rounded-xl border border-gray-100 bg-white p-5 text-sm text-gray-500 shadow-sm">
          Loading permission coverage...
        </div>
      )}

      {/* Per-module breakdown */}
      <div className="space-y-8">
        {sortedModules.map((module) => {
          const perms = grouped[module] ?? [];
          const actions = perms.map((p) => p.action);

          return (
            <div key={module} className="rounded-xl border border-gray-100 bg-white shadow-sm overflow-hidden">
              {/* Module header */}
              <div className="flex items-center gap-3 bg-gray-50 px-5 py-3 border-b border-gray-100">
                <h2 className="text-sm font-bold text-gray-800 uppercase tracking-wide flex-1">
                  {module}
                </h2>
                <span className="text-xs text-gray-400">{perms.length} permissions</span>
              </div>

              <div className="overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-50">
                      <th className="px-5 py-2.5 text-left text-xs font-semibold text-gray-500 w-40">
                        Role
                      </th>
                      {actions.map((action) => (
                        <th
                          key={action}
                          className="px-3 py-2.5 text-center text-xs font-semibold text-gray-500 whitespace-nowrap"
                        >
                          {ACTION_DISPLAY[action] ?? action}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {roles.map((role, ri) => {
                      const rolePermCodes = new Set(role.permissions.map((p) => p.code));
                      return (
                        <tr
                          key={role.id}
                          className={ri % 2 === 0 ? "bg-white" : "bg-gray-50/50"}
                        >
                          <td className="px-5 py-2 font-medium text-gray-700 whitespace-nowrap">
                            <span>{role.name}</span>
                            {!role.is_active && (
                              <span className="ml-2 text-xs text-gray-400">(inactive)</span>
                            )}
                          </td>
                          {perms.map((perm) => {
                            const has = rolePermCodes.has(perm.code);
                            return (
                              <td key={perm.id} className="px-3 py-2 text-center">
                                {has ? (
                                  <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-green-100 text-green-600">
                                    <svg className="h-3 w-3" fill="currentColor" viewBox="0 0 20 20">
                                      <path
                                        fillRule="evenodd"
                                        d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                                        clipRule="evenodd"
                                      />
                                    </svg>
                                  </span>
                                ) : (
                                  <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-gray-100 text-gray-300">
                                    <svg className="h-3 w-3" fill="currentColor" viewBox="0 0 20 20">
                                      <path
                                        fillRule="evenodd"
                                        d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                                        clipRule="evenodd"
                                      />
                                    </svg>
                                  </span>
                                )}
                              </td>
                            );
                          })}
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          );
        })}
      </div>

      {/* Mobile visibility legend */}
      <div className="mt-8 rounded-xl border border-gray-100 bg-white p-5 shadow-sm">
        <h2 className="mb-3 text-sm font-semibold text-gray-700">Mobile-Visible Permissions</h2>
        <p className="text-xs text-gray-500 mb-3">
          Permissions marked as mobile-visible are surfaced in the mobile executive dashboard.
        </p>
        <div className="flex flex-wrap gap-1.5">
          {allPerms
            .filter((p) => p.is_mobile_visible)
            .map((p) => (
              <span
                key={p.id}
                className="inline-block rounded bg-blue-50 px-2 py-0.5 text-xs font-mono text-blue-700"
              >
                {p.code}
              </span>
            ))}
        </div>
      </div>
    </div>
  );
}

"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import { AccessScopeAssign, usersApi } from "@/lib/users";
import { rolesApi } from "@/lib/roles";
import { auditApi, EVENT_LABELS, eventBadgeColor } from "@/lib/audit";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Input } from "@/components/ui/Input";

export default function UserDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const qc = useQueryClient();

  const [resetOpen, setResetOpen] = useState(false);
  const [rolesOpen, setRolesOpen] = useState(false);
  const [scopesOpen, setScopesOpen] = useState(false);
  const [newPassword, setNewPassword] = useState("");
  const [selectedRoleIds, setSelectedRoleIds] = useState<string[]>([]);
  const [scopeJson, setScopeJson] = useState("[]");
  const [scopeError, setScopeError] = useState<string | null>(null);

  const { data: user, isLoading } = useQuery({
    queryKey: ["user", id],
    queryFn: () => usersApi.get(id),
    enabled: !!id,
  });

  const { data: allRoles = [] } = useQuery({
    queryKey: ["roles"],
    queryFn: () => rolesApi.list(),
  });

  const { data: auditLogs = [] } = useQuery({
    queryKey: ["audit-user", id],
    queryFn: () => auditApi.userHistory(id, { limit: 30 }),
    enabled: !!id,
  });

  const { data: userScopes = [] } = useQuery({
    queryKey: ["user-scopes", id],
    queryFn: () => usersApi.listScopes(id),
    enabled: !!id,
  });

  const invalidate = () => qc.invalidateQueries({ queryKey: ["user", id] });

  const activateMutation = useMutation({
    mutationFn: () => usersApi.activate(id),
    onSuccess: invalidate,
  });

  const deactivateMutation = useMutation({
    mutationFn: () => usersApi.deactivate(id),
    onSuccess: invalidate,
  });

  const resetMutation = useMutation({
    mutationFn: () => usersApi.resetPassword(id, { new_password: newPassword }),
    onSuccess: () => {
      setResetOpen(false);
      setNewPassword("");
    },
  });

  const assignRolesMutation = useMutation({
    mutationFn: () => usersApi.assignRoles(id, selectedRoleIds),
    onSuccess: () => {
      invalidate();
      setRolesOpen(false);
    },
  });

  const assignScopesMutation = useMutation({
    mutationFn: (scopes: AccessScopeAssign[]) => usersApi.assignScopes(id, scopes),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["user-scopes", id] });
      setScopesOpen(false);
      setScopeError(null);
    },
  });

  const openRolesModal = () => {
    setSelectedRoleIds(user?.roles.map((r) => r.id) ?? []);
    setRolesOpen(true);
  };

  const openScopesModal = () => {
    const editableScopes = userScopes.map(({ id: _id, user_id: _userId, role_id: _roleId, ...scope }) => scope);
    setScopeJson(JSON.stringify(editableScopes, null, 2));
    setScopeError(null);
    setScopesOpen(true);
  };

  const toggleRole = (roleId: string) => {
    setSelectedRoleIds((prev) =>
      prev.includes(roleId) ? prev.filter((id) => id !== roleId) : [...prev, roleId],
    );
  };

  const saveScopes = () => {
    try {
      const parsed = JSON.parse(scopeJson) as AccessScopeAssign[];
      if (!Array.isArray(parsed)) {
        setScopeError("Scope payload must be a JSON array.");
        return;
      }
      assignScopesMutation.mutate(parsed);
    } catch {
      setScopeError("Scope payload is not valid JSON.");
    }
  };

  if (isLoading) {
    return (
      <div className="flex justify-center py-20">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" />
      </div>
    );
  }

  if (!user) {
    return <p className="text-gray-500">User not found.</p>;
  }

  return (
    <div className="max-w-3xl space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <button
            onClick={() => router.back()}
            className="mb-2 text-xs text-gray-400 hover:text-indigo-600"
          >
            ← Back
          </button>
          <h1 className="text-2xl font-bold text-gray-900">{user.full_name}</h1>
          <p className="text-sm text-gray-500">@{user.username} · {user.email}</p>
        </div>
        <div className="flex gap-2">
          <Badge
            label={user.is_active ? "Active" : "Inactive"}
            variant={user.is_active ? "green" : "red"}
          />
          {user.is_superuser && <Badge label="Superuser" variant="blue" />}
        </div>
      </div>

      {/* Actions */}
      <div className="flex flex-wrap gap-2">
        {user.is_active ? (
          <Button
            variant="danger"
            onClick={() => deactivateMutation.mutate()}
            loading={deactivateMutation.isPending}
          >
            Deactivate
          </Button>
        ) : (
          <Button
            onClick={() => activateMutation.mutate()}
            loading={activateMutation.isPending}
          >
            Activate
          </Button>
        )}
        <Button variant="secondary" onClick={() => setResetOpen(true)}>
          Reset Password
        </Button>
        <Button variant="secondary" onClick={openRolesModal}>
          Assign Roles
        </Button>
        <Button variant="secondary" onClick={openScopesModal}>
          Assign Scopes
        </Button>
      </div>

      {/* Roles */}
      <section className="rounded-xl border border-gray-100 bg-white p-5 shadow-sm">
        <h2 className="mb-3 text-sm font-semibold text-gray-700">Assigned Roles</h2>
        {user.roles.length === 0 ? (
          <p className="text-sm text-gray-400">No roles assigned.</p>
        ) : (
          <div className="space-y-2">
            {user.roles.map((role) => (
              <div
                key={role.id}
                className="flex items-center justify-between rounded-lg bg-gray-50 px-3 py-2"
              >
                <div>
                  <p className="text-sm font-medium text-gray-800">{role.name}</p>
                  {role.description && (
                    <p className="text-xs text-gray-400">{role.description}</p>
                  )}
                </div>
                <Badge
                  label={role.is_active ? "Active" : "Inactive"}
                  variant={role.is_active ? "green" : "red"}
                />
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Access Scopes */}
      <section className="rounded-xl border border-gray-100 bg-white p-5 shadow-sm">
        <div className="mb-3 flex items-center justify-between gap-3">
          <h2 className="text-sm font-semibold text-gray-700">User-Specific Scopes</h2>
          <Button variant="secondary" onClick={openScopesModal}>
            Manage Scopes
          </Button>
        </div>
        {userScopes.length === 0 ? (
          <p className="text-sm text-gray-400">No user-specific scopes assigned.</p>
        ) : (
          <div className="space-y-2">
            {userScopes.map((scope) => {
              const actions = [
                ["View", scope.can_view],
                ["Create", scope.can_create],
                ["Edit", scope.can_edit],
                ["Delete", scope.can_delete],
                ["Approve", scope.can_approve],
                ["Post", scope.can_post],
                ["Release", scope.can_release],
                ["Cancel", scope.can_cancel],
                ["Transfer", scope.can_transfer],
                ["Adjust", scope.can_adjust],
                ["Receive", scope.can_receive],
                ["Dispatch", scope.can_dispatch],
              ].filter(([, enabled]) => enabled);
              return (
                <div key={scope.id} className="rounded-lg bg-gray-50 px-3 py-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-sm font-medium text-gray-800">{scope.scope_type}</span>
                    <span className="font-mono text-xs text-gray-500">{scope.scope_id}</span>
                    {scope.scope_name && <span className="text-xs text-gray-400">{scope.scope_name}</span>}
                    <Badge label={scope.is_active ? "Active" : "Inactive"} variant={scope.is_active ? "green" : "red"} />
                  </div>
                  <div className="mt-2 flex flex-wrap gap-1">
                    {actions.length === 0 ? (
                      <span className="text-xs text-gray-400">No actions</span>
                    ) : (
                      actions.map(([label]) => (
                        <span key={String(label)} className="rounded bg-indigo-50 px-2 py-0.5 text-xs text-indigo-700">
                          {label}
                        </span>
                      ))
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>

      {/* Permissions Summary */}
      <section className="rounded-xl border border-gray-100 bg-white p-5 shadow-sm">
        <h2 className="mb-3 text-sm font-semibold text-gray-700">Effective Permissions</h2>
        {user.is_superuser ? (
          <p className="text-sm text-indigo-600 font-medium">
            Superuser — full access to all modules
          </p>
        ) : (
          <div className="flex flex-wrap gap-1.5">
            {user.roles
              .filter((r) => r.is_active)
              .flatMap((r) => r.permissions)
              .filter((p, i, arr) => arr.findIndex((x) => x.code === p.code) === i)
              .sort((a, b) => a.code.localeCompare(b.code))
              .map((perm) => (
                <span
                  key={perm.code}
                  className="inline-block rounded bg-indigo-50 px-2 py-0.5 text-xs font-mono text-indigo-700"
                >
                  {perm.code}
                </span>
              ))}
            {user.roles.filter((r) => r.is_active).flatMap((r) => r.permissions).length === 0 && (
              <p className="text-sm text-gray-400">No permissions via active roles.</p>
            )}
          </div>
        )}
      </section>

      {/* Audit History */}
      <section className="rounded-xl border border-gray-100 bg-white p-5 shadow-sm">
        <h2 className="mb-3 text-sm font-semibold text-gray-700">Activity History</h2>
        {auditLogs.length === 0 ? (
          <p className="text-sm text-gray-400">No activity recorded.</p>
        ) : (
          <div className="space-y-2">
            {auditLogs.map((log) => (
              <div key={log.id} className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2">
                  <span
                    className={`inline-block rounded px-2 py-0.5 text-xs font-medium ${eventBadgeColor(log.event_type)}`}
                  >
                    {EVENT_LABELS[log.event_type] ?? log.event_type}
                  </span>
                  {log.ip_address && (
                    <span className="text-xs text-gray-400">{log.ip_address}</span>
                  )}
                </div>
                <span className="text-xs text-gray-400">
                  {new Date(log.created_at).toLocaleString()}
                </span>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Reset Password Modal */}
      <Modal open={resetOpen} onClose={() => setResetOpen(false)} title="Reset Password">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            resetMutation.mutate();
          }}
          className="space-y-4"
        >
          <Input
            label="New Password *"
            type="password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            required
          />
          {resetMutation.error && (
            <p className="text-sm text-red-600">Failed to reset password.</p>
          )}
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={() => setResetOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" loading={resetMutation.isPending}>
              Reset
            </Button>
          </div>
        </form>
      </Modal>

      {/* Assign Roles Modal */}
      <Modal open={rolesOpen} onClose={() => setRolesOpen(false)} title="Assign Roles">
        <div className="space-y-4">
          <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
            {allRoles.map((role) => (
              <label
                key={role.id}
                className="flex items-center gap-3 rounded-lg border border-gray-100 p-3 cursor-pointer hover:bg-gray-50"
              >
                <input
                  type="checkbox"
                  checked={selectedRoleIds.includes(role.id)}
                  onChange={() => toggleRole(role.id)}
                  className="rounded"
                />
                <div className="flex-1">
                  <p className="text-sm font-medium text-gray-800">{role.name}</p>
                  {role.description && (
                    <p className="text-xs text-gray-400">{role.description}</p>
                  )}
                </div>
                <Badge
                  label={role.is_active ? "Active" : "Inactive"}
                  variant={role.is_active ? "green" : "red"}
                />
              </label>
            ))}
          </div>
          {assignRolesMutation.error && (
            <p className="text-sm text-red-600">Failed to assign roles.</p>
          )}
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={() => setRolesOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => assignRolesMutation.mutate()}
              loading={assignRolesMutation.isPending}
            >
              Save Roles
            </Button>
          </div>
        </div>
      </Modal>

      {/* Assign Scopes Modal */}
      <Modal open={scopesOpen} onClose={() => setScopesOpen(false)} title="Assign User Scopes">
        <div className="space-y-4">
          <textarea
            value={scopeJson}
            onChange={(e) => setScopeJson(e.target.value)}
            rows={14}
            className="w-full rounded-lg border border-gray-200 px-3 py-2 font-mono text-xs focus:outline-none focus:ring-2 focus:ring-indigo-500"
            spellCheck={false}
          />
          {scopeError && <p className="text-sm text-red-600">{scopeError}</p>}
          {assignScopesMutation.error && (
            <p className="text-sm text-red-600">Failed to save scopes.</p>
          )}
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={() => setScopesOpen(false)}>
              Cancel
            </Button>
            <Button onClick={saveScopes} loading={assignScopesMutation.isPending}>
              Save Scopes
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}

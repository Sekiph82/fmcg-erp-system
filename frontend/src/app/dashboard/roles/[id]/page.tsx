"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import { rolesApi, groupByModule, STANDARD_ACTIONS } from "@/lib/roles";
import { auditApi, EVENT_LABELS, eventBadgeColor } from "@/lib/audit";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Input } from "@/components/ui/Input";

export default function RoleDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const qc = useQueryClient();

  const [editOpen, setEditOpen] = useState(false);
  const [editName, setEditName] = useState("");
  const [editDesc, setEditDesc] = useState("");
  const [permOpen, setPermOpen] = useState(false);
  const [selectedPermIds, setSelectedPermIds] = useState<string[]>([]);

  const { data: role, isLoading } = useQuery({
    queryKey: ["role", id],
    queryFn: () => rolesApi.get(id),
    enabled: !!id,
  });

  const { data: allPerms = [] } = useQuery({
    queryKey: ["permissions"],
    queryFn: () => rolesApi.listPermissions(),
  });

  const { data: auditLogs = [] } = useQuery({
    queryKey: ["audit-role", id],
    queryFn: () =>
      auditApi.list({ target_type: "role", target_id: id, limit: 30 }),
    enabled: !!id,
  });

  const invalidate = () => qc.invalidateQueries({ queryKey: ["role", id] });

  const activateMutation = useMutation({
    mutationFn: () => rolesApi.activate(id),
    onSuccess: invalidate,
  });
  const deactivateMutation = useMutation({
    mutationFn: () => rolesApi.deactivate(id),
    onSuccess: invalidate,
  });
  const editMutation = useMutation({
    mutationFn: () => rolesApi.update(id, { name: editName, description: editDesc }),
    onSuccess: () => { invalidate(); setEditOpen(false); },
  });
  const assignPermsMutation = useMutation({
    mutationFn: () => rolesApi.assignPermissions(id, selectedPermIds),
    onSuccess: () => { invalidate(); setPermOpen(false); },
  });

  const openEdit = () => {
    setEditName(role?.name ?? "");
    setEditDesc(role?.description ?? "");
    setEditOpen(true);
  };

  const openPerms = () => {
    setSelectedPermIds(role?.permissions.map((p) => p.id) ?? []);
    setPermOpen(true);
  };

  const togglePerm = (pid: string) =>
    setSelectedPermIds((prev) =>
      prev.includes(pid) ? prev.filter((x) => x !== pid) : [...prev, pid],
    );

  const grouped = groupByModule(allPerms);

  if (isLoading) {
    return (
      <div className="flex justify-center py-20">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" />
      </div>
    );
  }

  if (!role) return <p className="text-gray-500">Role not found.</p>;

  const rolePermIds = new Set(role.permissions.map((p) => p.id));

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
          <h1 className="text-2xl font-bold text-gray-900">{role.name}</h1>
          {role.description && (
            <p className="text-sm text-gray-500 mt-0.5">{role.description}</p>
          )}
        </div>
        <Badge
          label={role.is_active ? "Active" : "Inactive"}
          variant={role.is_active ? "green" : "red"}
        />
      </div>

      {/* Actions */}
      <div className="flex flex-wrap gap-2">
        <Button variant="secondary" onClick={openEdit}>Edit Role</Button>
        <Button variant="secondary" onClick={openPerms}>Manage Permissions</Button>
        {role.is_active ? (
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
      </div>

      {/* Permissions by module */}
      <section className="rounded-xl border border-gray-100 bg-white p-5 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-gray-700">
            Permissions ({role.permissions.length})
          </h2>
          <button
            onClick={openPerms}
            className="text-xs text-indigo-500 hover:underline"
          >
            Edit
          </button>
        </div>
        {role.permissions.length === 0 ? (
          <p className="text-sm text-gray-400">No permissions assigned.</p>
        ) : (
          <div className="space-y-3">
            {Object.entries(groupByModule(role.permissions))
              .sort(([a], [b]) => a.localeCompare(b))
              .map(([module, perms]) => (
                <div key={module}>
                  <p className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-1.5">
                    {module}
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {perms.map((p) => (
                      <span
                        key={p.id}
                        className="inline-block rounded bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-700"
                      >
                        {p.action}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
          </div>
        )}
      </section>

      {/* Audit trail */}
      <section className="rounded-xl border border-gray-100 bg-white p-5 shadow-sm">
        <h2 className="mb-3 text-sm font-semibold text-gray-700">Change History</h2>
        {auditLogs.length === 0 ? (
          <p className="text-sm text-gray-400">No changes recorded.</p>
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
                  {log.actor_email && (
                    <span className="text-xs text-gray-500">by {log.actor_email}</span>
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

      {/* Edit Modal */}
      <Modal open={editOpen} onClose={() => setEditOpen(false)} title="Edit Role">
        <form
          onSubmit={(e) => { e.preventDefault(); editMutation.mutate(); }}
          className="space-y-4"
        >
          <Input
            label="Role Name *"
            value={editName}
            onChange={(e) => setEditName(e.target.value)}
            required
          />
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
            <textarea
              value={editDesc}
              onChange={(e) => setEditDesc(e.target.value)}
              rows={3}
              className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          {editMutation.error && (
            <p className="text-sm text-red-600">Failed to update role.</p>
          )}
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={() => setEditOpen(false)}>Cancel</Button>
            <Button type="submit" loading={editMutation.isPending}>Save</Button>
          </div>
        </form>
      </Modal>

      {/* Permissions Modal */}
      <Modal open={permOpen} onClose={() => setPermOpen(false)} title="Manage Permissions">
        <div className="space-y-4">
          <div className="max-h-96 overflow-y-auto space-y-4 pr-1">
            {Object.entries(grouped)
              .sort(([a], [b]) => a.localeCompare(b))
              .map(([module, perms]) => (
                <div key={module}>
                  <p className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">
                    {module}
                  </p>
                  <div className="grid grid-cols-2 gap-1.5 sm:grid-cols-3">
                    {perms.map((p) => (
                      <label
                        key={p.id}
                        className="flex items-center gap-2 cursor-pointer text-sm"
                      >
                        <input
                          type="checkbox"
                          checked={selectedPermIds.includes(p.id)}
                          onChange={() => togglePerm(p.id)}
                          className="rounded"
                        />
                        <span className="text-gray-700">{p.action}</span>
                      </label>
                    ))}
                  </div>
                </div>
              ))}
          </div>
          {assignPermsMutation.error && (
            <p className="text-sm text-red-600">Failed to assign permissions.</p>
          )}
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={() => setPermOpen(false)}>Cancel</Button>
            <Button
              onClick={() => assignPermsMutation.mutate()}
              loading={assignPermsMutation.isPending}
            >
              Save Permissions
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}

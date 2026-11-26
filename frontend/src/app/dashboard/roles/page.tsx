"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { rolesApi, RoleCreate } from "@/lib/roles";
import { Table } from "@/components/ui/Table";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Input } from "@/components/ui/Input";
import { tx } from "@/lib/i18n/core";

const emptyForm: RoleCreate = { name: "", description: "" };

export default function RolesPage() {
  const qc = useQueryClient();
  const [filterActive, setFilterActive] = useState<string>("all");
  const [createOpen, setCreateOpen] = useState(false);
  const [form, setForm] = useState<RoleCreate>(emptyForm);

  const is_active =
    filterActive === "active" ? true : filterActive === "inactive" ? false : undefined;

  const { data: roles = [], isLoading } = useQuery({
    queryKey: ["roles", is_active],
    queryFn: () => rolesApi.list({ is_active }),
  });

  const createMutation = useMutation({
    mutationFn: rolesApi.create,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["roles"] });
      setCreateOpen(false);
      setForm(emptyForm);
    },
  });

  const set = (k: keyof RoleCreate, v: string) =>
    setForm((f) => ({ ...f, [k]: v }));

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{tx("Roles")}</h1>
          <p className="text-sm text-gray-500 mt-1">{roles.length} {tx("total")}</p>
        </div>
        <Button onClick={() => setCreateOpen(true)}>{tx("+ Add Role")}</Button>
      </div>

      <div className="mb-4 flex gap-3">
        <select
          value={filterActive}
          onChange={(e) => setFilterActive(e.target.value)}
          className="rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          <option value="all">{tx("All Status")}</option>
          <option value="active">{tx("Active")}</option>
          <option value="inactive">{tx("Inactive")}</option>
        </select>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-16">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" />
        </div>
      ) : (
        <Table
          keyField="id"
          data={roles}
          columns={[
            {
              header: tx("Role"),
              accessor: (r) => (
                <Link
                  href={`/dashboard/roles/${r.id}`}
                  className="font-medium text-indigo-600 hover:underline"
                >
                  {r.name}
                </Link>
              ),
            },
            { header: tx("Description"), accessor: (r) => r.description ?? "—" },
            {
              header: tx("Permissions"),
              accessor: (r) => (
                <span className="text-sm text-gray-600">{r.permissions.length} {tx("assigned")}</span>
              ),
            },
            {
              header: tx("Status"),
              accessor: (r) => (
                <Badge
                  label={r.is_active ? tx("Active") : tx("Inactive")}
                  variant={r.is_active ? "green" : "red"}
                />
              ),
            },
            {
              header: "",
              accessor: (r) => (
                <Link
                  href={`/dashboard/roles/${r.id}`}
                  className="text-xs text-indigo-500 hover:underline"
                >
                  {tx("Manage →")}
                </Link>
              ),
            },
          ]}
        />
      )}

      <Modal open={createOpen} onClose={() => setCreateOpen(false)} title={tx("Create Role")}>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            createMutation.mutate(form);
          }}
          className="space-y-4"
        >
          <Input
            label={tx("Role Name *")}
            value={form.name}
            onChange={(e) => set("name", e.target.value)}
            required
          />
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{tx("Description")}</label>
            <textarea
              value={form.description ?? ""}
              onChange={(e) => set("description", e.target.value)}
              rows={3}
              className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          {createMutation.error && (
            <p className="text-sm text-red-600">{tx("Failed to create role. Name may already exist.")}</p>
          )}
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={() => setCreateOpen(false)}>
              {tx("Cancel")}
            </Button>
            <Button type="submit" loading={createMutation.isPending}>
              {tx("Create")}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}

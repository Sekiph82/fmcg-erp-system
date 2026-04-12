"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { usersApi, UserCreate } from "@/lib/users";
import { rolesApi } from "@/lib/roles";
import { Table } from "@/components/ui/Table";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Input } from "@/components/ui/Input";

const emptyForm: UserCreate = {
  email: "",
  username: "",
  full_name: "",
  password: "",
  is_active: true,
  is_superuser: false,
};

export default function UsersPage() {
  const qc = useQueryClient();
  const [search, setSearch] = useState("");
  const [filterActive, setFilterActive] = useState<string>("all");
  const [createOpen, setCreateOpen] = useState(false);
  const [form, setForm] = useState<UserCreate>(emptyForm);

  const is_active =
    filterActive === "active" ? true : filterActive === "inactive" ? false : undefined;

  const { data, isLoading } = useQuery({
    queryKey: ["users", search, is_active],
    queryFn: () => usersApi.list({ search: search || undefined, is_active }),
    staleTime: 30_000,
  });

  const { data: roles = [] } = useQuery({
    queryKey: ["roles"],
    queryFn: () => rolesApi.list({ is_active: true }),
  });

  const createMutation = useMutation({
    mutationFn: usersApi.create,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["users"] });
      setCreateOpen(false);
      setForm(emptyForm);
    },
  });

  const set = (k: keyof UserCreate, v: unknown) =>
    setForm((f) => ({ ...f, [k]: v }));

  const users = data?.items ?? [];
  const total = data?.total ?? 0;

  return (
    <div>
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Users</h1>
          <p className="text-sm text-gray-500 mt-1">{total} total</p>
        </div>
        <Button onClick={() => setCreateOpen(true)}>+ Add User</Button>
      </div>

      {/* Filters */}
      <div className="mb-4 flex flex-wrap gap-3">
        <Input
          placeholder="Search name, email, username…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-72"
        />
        <select
          value={filterActive}
          onChange={(e) => setFilterActive(e.target.value)}
          className="rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          <option value="all">All Status</option>
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
        </select>
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="flex justify-center py-16">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" />
        </div>
      ) : (
        <Table
          keyField="id"
          data={users}
          columns={[
            {
              header: "Name",
              accessor: (r) => (
                <Link
                  href={`/dashboard/users/${r.id}`}
                  className="font-medium text-indigo-600 hover:underline"
                >
                  {r.full_name}
                </Link>
              ),
            },
            { header: "Username", accessor: "username", className: "font-mono text-xs" },
            { header: "Email", accessor: "email" },
            {
              header: "Roles",
              accessor: (r) => (
                <div className="flex flex-wrap gap-1">
                  {r.roles.length === 0 ? (
                    <span className="text-xs text-gray-400">—</span>
                  ) : (
                    r.roles.map((role) => (
                      <span
                        key={role.id}
                        className="inline-block rounded bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-700"
                      >
                        {role.name}
                      </span>
                    ))
                  )}
                </div>
              ),
            },
            {
              header: "Type",
              accessor: (r) =>
                r.is_superuser ? (
                  <Badge label="Superuser" variant="blue" />
                ) : (
                  <Badge label="User" variant="gray" />
                ),
            },
            {
              header: "Status",
              accessor: (r) => (
                <Badge
                  label={r.is_active ? "Active" : "Inactive"}
                  variant={r.is_active ? "green" : "red"}
                />
              ),
            },
            {
              header: "",
              accessor: (r) => (
                <Link
                  href={`/dashboard/users/${r.id}`}
                  className="text-xs text-indigo-500 hover:underline"
                >
                  Details →
                </Link>
              ),
            },
          ]}
        />
      )}

      {/* Create Modal */}
      <Modal open={createOpen} onClose={() => setCreateOpen(false)} title="Create User">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            createMutation.mutate(form);
          }}
          className="space-y-4"
        >
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Full Name *"
              value={form.full_name}
              onChange={(e) => set("full_name", e.target.value)}
              required
            />
            <Input
              label="Username *"
              value={form.username}
              onChange={(e) => set("username", e.target.value)}
              required
            />
          </div>
          <Input
            label="Email *"
            type="email"
            value={form.email}
            onChange={(e) => set("email", e.target.value)}
            required
          />
          <Input
            label="Password *"
            type="password"
            value={form.password}
            onChange={(e) => set("password", e.target.value)}
            required
          />
          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2 text-sm text-gray-700">
              <input
                type="checkbox"
                checked={form.is_superuser}
                onChange={(e) => set("is_superuser", e.target.checked)}
                className="rounded"
              />
              Superuser
            </label>
            <label className="flex items-center gap-2 text-sm text-gray-700">
              <input
                type="checkbox"
                checked={form.is_active}
                onChange={(e) => set("is_active", e.target.checked)}
                className="rounded"
              />
              Active
            </label>
          </div>
          {createMutation.error && (
            <p className="text-sm text-red-600">Failed to create user. Check inputs and try again.</p>
          )}
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={() => setCreateOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" loading={createMutation.isPending}>
              Create
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}

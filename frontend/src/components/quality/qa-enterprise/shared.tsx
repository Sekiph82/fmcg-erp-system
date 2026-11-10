"use client";

import { ReactNode } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/context/AuthContext";
import { apiErrorMessage } from "@/lib/qa-enterprise";

export type Notify = (message: string, type?: "success" | "error") => void;

export function useQualityPermissions() {
  const { hasAnyPermission } = useAuth();
  return {
    canView: hasAnyPermission(["quality.view", "quality.view_all"]),
    canCreate: hasAnyPermission(["quality.create", "quality.create_all"]),
    canEdit: hasAnyPermission(["quality.edit", "quality.edit_all"]),
    canApprove: hasAnyPermission(["quality.approve", "quality.approve_all"]),
  };
}

/** Mutation that toasts success/failure (server rule messages are shown verbatim) and refreshes queries. */
export function useAction<TArgs, TResult>(
  fn: (args: TArgs) => Promise<TResult>,
  notify: Notify,
  success: string | ((result: TResult) => string),
  invalidate: string[],
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: (result) => {
      notify(typeof success === "function" ? success(result) : success, "success");
      invalidate.forEach((key) => queryClient.invalidateQueries({ queryKey: [key] }));
    },
    onError: (error) => notify(apiErrorMessage(error), "error"),
  });
}

export function Section({ title, description, actions, children }: {
  title: string; description?: string; actions?: ReactNode; children: ReactNode;
}) {
  return (
    <section className="rounded-xl border border-gray-200 bg-white p-4 space-y-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-base font-semibold text-gray-900">{title}</h3>
          {description && <p className="text-sm text-gray-500">{description}</p>}
        </div>
        {actions}
      </div>
      {children}
    </section>
  );
}

export function TextArea({ id, label, value, onChange, rows = 2 }: {
  id: string; label: string; value: string; onChange: (value: string) => void; rows?: number;
}) {
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-sm font-medium text-gray-700">{label}</label>
      <textarea id={id} rows={rows} value={value} onChange={(e) => onChange(e.target.value)}
        className="block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm neon-focus" />
    </div>
  );
}

export function ReadOnlyNotice({ children }: { children: ReactNode }) {
  return <p role="status" className="rounded-lg bg-gray-50 px-3 py-2 text-sm text-gray-600">{children}</p>;
}

export function LoadError({ error }: { error: unknown }) {
  return <p role="alert" className="text-sm text-red-600">{apiErrorMessage(error)}</p>;
}

export const statusVariant = (status: string): "green" | "red" | "yellow" | "blue" | "gray" => {
  if (["APPROVED", "ACTIVE", "ACCEPT", "STORED", "CLOSED", "IMPLEMENTED", "VERIFIED", "SATISFIED"].includes(status)) return "green";
  if (["REJECTED", "REVOKED", "REJECT", "FAILED", "DISPOSED", "CANCELLED"].includes(status)) return "red";
  if (["PENDING", "SUBMITTED", "DRAFT", "SECOND_SAMPLE", "IN_PROGRESS", "INCOMPLETE"].includes(status)) return "yellow";
  if (["SUPERSEDED", "RETIRED", "DEPLETED", "NOT_STARTED"].includes(status)) return "gray";
  return "blue";
};

export const shortId = (id: string | null | undefined) => (id ? id.slice(0, 8) : "—");

export function todayIso(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}

export function addDaysIso(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() + days);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

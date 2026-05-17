"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { RequirePermission } from "@/components/PermissionGuard";
import { useAuth } from "@/context/AuthContext";

function PayrollRunDetail({ id }: { id: string }) {
  const router = useRouter();
  const { hasPermission } = useAuth();

  useEffect(() => {
    router.replace(`/dashboard/hr?tab=payroll&id=${encodeURIComponent(id)}&drawer=detail`);
  }, [id, router]);

  if (hasPermission("payroll_ke.approve")) {
    return null;
  }
  return null;
}

export default function Page({ params }: { params: { id: string } }) {
  return (
    <RequirePermission permission="payroll_ke.view">
      <PayrollRunDetail id={params.id} />
    </RequirePermission>
  );
}

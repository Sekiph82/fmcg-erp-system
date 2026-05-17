"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { RequirePermission } from "@/components/PermissionGuard";
import { useAuth } from "@/context/AuthContext";

function PayrollRunRedirect({ id }: { id: string }) {
  const router = useRouter();
  const { hasPermission } = useAuth();

  useEffect(() => {
    const target = `/dashboard/hr?tab=payroll&id=${encodeURIComponent(id)}&drawer=detail`;
    if (hasPermission("payroll_ke.approve")) {
      router.replace(target + "&mode=approve");
    } else {
      router.replace(target);
    }
  }, [id, router, hasPermission]);

  return null;
}

export default function Page({ params }: { params: { id: string } }) {
  return (
    <RequirePermission permission="payroll_ke.view">
      <PayrollRunRedirect id={params.id} />
    </RequirePermission>
  );
}

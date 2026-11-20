"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";

// finance people who approve the accounting rule set (owner 2026-11-20); the CEO/owner are not sent there
const FINANCE_ROLES = new Set(["cfo", "finance_manager", "scoped_finance_manager"]);
const SEEN = "posting-rules-shown";

/** Until finance approves the rule set, a finance approver lands on Finance → Posting Rules once per sign-in session. */
export function PostingRulesFirstLogin() {
  const { user, hasExactPermission } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const eligible = !!user && !user.must_change_password && hasExactPermission("finance.approve")
    && user.roles.some((r) => FINANCE_ROLES.has(r.name));
  const { data } = useQuery<{ mandatory: boolean; rules: { status: string }[] }>({
    queryKey: ["posting-rules-catalog"],
    queryFn: async () => (await apiClient.get("/api/v1/finance/accounting/posting-rules/catalog")).data,
    enabled: eligible,
    staleTime: 300_000,
  });
  const pending = !!data && !data.mandatory && data.rules.some((r) => r.status === "proposed" || r.status === "missing");

  useEffect(() => {
    if (!pending || pathname !== "/dashboard") return; // only on landing, never away from work in progress
    try {
      if (sessionStorage.getItem(SEEN)) return;
      sessionStorage.setItem(SEEN, "1");
    } catch { /* storage blocked: still show it once now */ }
    router.push("/dashboard/finance?tab=posting-rules");
  }, [pending, router, pathname]);
  return null;
}

"use client";

import { createContext, useContext, useEffect, useState, useCallback, useMemo } from "react";
import { useRouter } from "next/navigation";
import { getMe, login as apiLogin, logout as apiLogout, User } from "@/lib/auth";
import { setAppRouter } from "@/lib/api";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  hasPermission: (code: string) => boolean;
  hasAnyPermission: (codes: string[]) => boolean;
  hasModule: (moduleKey: string) => boolean;
  canPerformInScope: (scopeType: string, scopeId: string, action: string) => boolean;
  canViewScope: (scopeType: string, scopeId: string) => boolean;
  canEditScope: (scopeType: string, scopeId: string) => boolean;
  canViewRecord: (record: Record<string, unknown>) => boolean;
  canEditRecord: (record: Record<string, unknown>) => boolean;
  getFirstAllowedRoute: () => string;
  completeTwoFA: (accessToken?: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  const loadUser = useCallback(async () => {
    try {
      const me = await getMe();
      setUser(me);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadUser(); }, [loadUser]);
  useEffect(() => { setAppRouter(router); }, [router]);

  const login = async (username: string, password: string) => {
    const res = await apiLogin(username, password);
    if (res.two_fa_required && res.session_token) {
      sessionStorage.setItem("2fa_session_token", res.session_token);
      sessionStorage.setItem("2fa_method", res.method || "totp");
      router.push("/auth/2fa");
      return;
    }
    const me = await getMe();
    setUser(me);
    router.push(res.must_change_password || me.must_change_password ? "/auth/change-password" : "/dashboard");
  };

  const completeTwoFA = async (_accessToken?: string) => {
    sessionStorage.removeItem("2fa_session_token");
    sessionStorage.removeItem("2fa_method");
    const me = await getMe();
    setUser(me);
    router.push(me.must_change_password ? "/auth/change-password" : "/dashboard");
  };

  const logout = async () => {
    try {
      await apiLogout();
    } catch {
      // Local cleanup still matters if the server session is already gone.
    }
    setUser(null);
    router.push("/login");
  };

  const permissionSet = useMemo(
    () => new Set(user?.permission_codes ?? []),
    [user?.permission_codes]
  );

  const hasPermission = (code: string): boolean => {
    if (!user) return false;
    if (user.is_superuser) return true;
    if (permissionSet.has(code)) return true;

    const [moduleKey, action] = code.split(".", 2);
    if (!moduleKey || !action) return false;

    const scopedAliases = [
      `${moduleKey}.${action}_all`,
      `${moduleKey}.${action}_own_scope`,
      `${moduleKey}.${action}_own_region`,
      `${moduleKey}.${action}_own_company`,
      `${moduleKey}.${action}_own_branch`,
      `${moduleKey}.${action}_own_warehouse`,
      `${moduleKey}.${action}_own_factory`,
      `${moduleKey}.${action}_own_line`,
      `${moduleKey}.${action}_own_department`,
      `${moduleKey}.${action}_own_category`,
    ];
    return scopedAliases.some((permission) => permissionSet.has(permission));
  };

  const hasAnyPermission = (codes: string[]): boolean => codes.some((code) => hasPermission(code));

  const hasModule = (moduleKey: string): boolean => {
    if (!user) return false;
    if (user.is_superuser) return true;
    return user.modules.includes(moduleKey) || user.permission_codes.some((code) => code.startsWith(`${moduleKey}.`));
  };

  const canPerformInScope = (scopeType: string, scopeId: string, action: string): boolean => {
    if (!user) return false;
    if (user.is_superuser) return true;
    const actionFieldByAction: Record<string, keyof NonNullable<User["scopes"][number]>> = {
      view: "can_view",
      view_all: "can_view",
      view_own_scope: "can_view",
      create: "can_create",
      edit: "can_edit",
      update: "can_edit",
      delete: "can_delete",
      approve: "can_approve",
      post: "can_post",
      release: "can_release",
      close: "can_release",
      cancel: "can_cancel",
      export: "can_export",
      import: "can_import",
      transfer: "can_transfer",
      adjust: "can_adjust",
      receive: "can_receive",
      dispatch: "can_dispatch",
    };
    const field = actionFieldByAction[action] ?? (`can_${action}` as keyof NonNullable<User["scopes"][number]>);
    const exact = user.scopes.find((scope) =>
      scope.is_active && scope.scope_type === scopeType && scope.scope_id === String(scopeId)
    );
    if (exact) return Boolean(exact[field]);
    const global = user.scopes.find((scope) =>
      scope.is_active && scope.scope_type === scopeType && scope.scope_id === "ALL"
    );
    return global ? Boolean(global[field]) : false;
  };

  const canViewScope = (scopeType: string, scopeId: string): boolean =>
    canPerformInScope(scopeType, scopeId, "view");

  const canEditScope = (scopeType: string, scopeId: string): boolean =>
    canPerformInScope(scopeType, scopeId, "edit");

  const resolveRecordScopes = (record: Record<string, unknown>): Array<[string, string]> => {
    const fields: Record<string, string> = {
      company_id: "company",
      branch_id: "branch",
      warehouse_id: "warehouse",
      source_warehouse_id: "warehouse",
      destination_warehouse_id: "warehouse",
      target_warehouse_id: "warehouse",
      from_warehouse_id: "warehouse",
      to_warehouse_id: "warehouse",
      factory_id: "factory",
      production_line_id: "production_line",
      sales_region_id: "sales_region",
      region: "sales_region",
      sales_team_id: "sales_team",
      customer_group_id: "customer_group",
      supplier_category_id: "supplier_category",
      product_category_id: "product_category",
      cost_center_id: "cost_center",
      department_id: "department",
      department: "department",
      employee_department_id: "employee_department",
      project_id: "project",
      machine_id: "machine",
      utility_area_id: "utility_area",
    };
    return Object.entries(fields)
      .filter(([field]) => record[field] !== undefined && record[field] !== null)
      .map(([field, scopeType]) => [scopeType, String(record[field])] as [string, string]);
  };

  const canViewRecord = (record: Record<string, unknown>): boolean => {
    if (!user) return false;
    if (user.is_superuser) return true;
    return resolveRecordScopes(record).some(([scopeType, scopeId]) => canViewScope(scopeType, scopeId));
  };

  const canEditRecord = (record: Record<string, unknown>): boolean => {
    if (!user) return false;
    if (user.is_superuser) return true;
    return resolveRecordScopes(record).some(([scopeType, scopeId]) => canEditScope(scopeType, scopeId));
  };

  const getFirstAllowedRoute = (): string => {
    if (!user) return "/login";
    if (hasModule("dashboard") || user.is_superuser) return "/dashboard";
    const routeByModule: Record<string, string> = {
      inventory: "/dashboard/inventory",
      procurement: "/dashboard/procurement",
      production: "/dashboard/production",
      quality: "/dashboard/quality",
      sales: "/dashboard/sales",
      finance: "/dashboard/finance",
      hr: "/dashboard/hr",
      payroll_ke: "/dashboard/payroll",
      maintenance: "/dashboard/maintenance",
      utilities: "/dashboard/utilities",
      reports: "/dashboard/reports",
      ai: "/dashboard/ai",
      users: "/dashboard/users",
      roles: "/dashboard/roles",
    };
    const firstModule = user.modules.find((moduleKey) => routeByModule[moduleKey]);
    return firstModule ? routeByModule[firstModule] : "/dashboard";
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        login,
        logout,
        hasPermission,
        hasAnyPermission,
        hasModule,
        canPerformInScope,
        canViewScope,
        canEditScope,
        canViewRecord,
        canEditRecord,
        getFirstAllowedRoute,
        completeTwoFA,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}

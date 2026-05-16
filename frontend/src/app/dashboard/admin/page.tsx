"use client";

import dynamic from "next/dynamic";
import { ModuleWorkspace } from "@/components/workspace";

const UsersPage        = dynamic(() => import("@/app/dashboard/users/page"),          { ssr: false });
const RolesPage        = dynamic(() => import("@/app/dashboard/roles/page"),          { ssr: false });
const PermPage         = dynamic(() => import("@/app/dashboard/permissions/page"),    { ssr: false });
const CompaniesPage    = dynamic(() => import("@/app/dashboard/companies/page"),      { ssr: false });
const SecurityPage     = dynamic(() => import("@/app/dashboard/security/page"),       { ssr: false });
const ApprovalsPage    = dynamic(() => import("@/app/dashboard/approvals/page"),      { ssr: false });
const CustomFieldsPage = dynamic(() => import("@/app/dashboard/custom-fields/page"), { ssr: false });
const UtilitiesPage    = dynamic(() => import("@/app/dashboard/utilities/page"),      { ssr: false });
const MobilePage       = dynamic(() => import("@/app/dashboard/mobile/page"),         { ssr: false });
const LogsPage         = dynamic(() => import("@/app/dashboard/logs/page"),           { ssr: false });
const ImportHistPage   = dynamic(() => import("@/app/dashboard/import-history/page"),{ ssr: false });

export default function AdminPage() {
  const tabs = [
    { key: "users",          label: "Users",         permission: "users.view",       content: <UsersPage /> },
    { key: "roles",          label: "Roles",         permission: "roles.view",       content: <RolesPage /> },
    { key: "permissions",    label: "Permissions",   permission: "roles.view",       content: <PermPage /> },
    { key: "companies",      label: "Companies",     permission: "users.view",       content: <CompaniesPage /> },
    { key: "security",       label: "Security",      permission: "users.view",       content: <SecurityPage /> },
    { key: "approvals",      label: "Approvals",     permission: "finance.view",     content: <ApprovalsPage /> },
    { key: "custom-fields",  label: "Custom Fields", permission: "hr.view",          content: <CustomFieldsPage /> },
    { key: "system-config",  label: "System Config", permission: "utilities.view",   content: <UtilitiesPage /> },
    { key: "mobile",         label: "Mobile Apps",   permission: "hr.view",          content: <MobilePage /> },
    { key: "logs",           label: "System Logs",   permission: "audit.view",       content: <LogsPage /> },
    { key: "import-history", label: "Import History",permission: "audit.view",       content: <ImportHistPage /> },
  ];

  return (
    <ModuleWorkspace
      title="Administration"
      description="Users, roles, security, system configuration"
      permission="users.view"
      tabs={tabs}
      defaultTab="users"
    />
  );
}

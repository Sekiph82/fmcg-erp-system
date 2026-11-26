"use client";

import dynamic from "next/dynamic";
import { ModuleWorkspace } from "@/components/workspace";
import { tx } from "@/lib/i18n/core";

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
    { key: "users",          label: tx("Users"),         permission: "users.view",       content: <UsersPage /> },
    { key: "roles",          label: tx("Roles"),         permission: "roles.view",       content: <RolesPage /> },
    { key: "permissions",    label: tx("Permissions"),   permission: "roles.view",       content: <PermPage /> },
    { key: "companies",      label: tx("Companies"),     permission: "company.view",       content: <CompaniesPage /> },
    { key: "security",       label: tx("Security"),      permission: "users.view",       content: <SecurityPage /> },
    { key: "approvals",      label: tx("Approvals"),     permission: "self.superuser",     content: <ApprovalsPage /> },
    { key: "custom-fields",  label: tx("Custom Fields"), permission: "hr.view",          content: <CustomFieldsPage /> },
    { key: "system-config",  label: tx("System Config"), permission: "utilities.view",   content: <UtilitiesPage /> },
    { key: "mobile",         label: tx("Mobile Apps"),   permission: "users.edit|company.edit|integrations.edit",          content: <MobilePage /> },
    { key: "logs",           label: tx("System Logs"),   permission: "audit.view",       content: <LogsPage /> },
    { key: "import-history", label: tx("Import History"),permission: "audit.view",       content: <ImportHistPage /> },
  ];

  return (
    <ModuleWorkspace
      title={tx("Administration")}
      description="Users, roles, security, system configuration"
      permission="users.view"
      tabs={tabs}
      defaultTab="users"
    />
  );
}

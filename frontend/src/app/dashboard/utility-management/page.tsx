"use client";

import dynamic from "next/dynamic";
import { ModuleWorkspace } from "@/components/workspace";

const AssetsPage           = dynamic(() => import("@/app/dashboard/utility-management/assets/page"),            { ssr: false });
const ElectricityPage      = dynamic(() => import("@/app/dashboard/utility-management/electricity/page"),       { ssr: false });
const WaterPage            = dynamic(() => import("@/app/dashboard/utility-management/water/page"),             { ssr: false });
const SolarPage            = dynamic(() => import("@/app/dashboard/utility-management/solar/page"),             { ssr: false });
const SteamPage            = dynamic(() => import("@/app/dashboard/utility-management/steam/page"),             { ssr: false });
const WastewaterPage       = dynamic(() => import("@/app/dashboard/utility-management/wastewater/page"),        { ssr: false });
const SoftWaterPage        = dynamic(() => import("@/app/dashboard/utility-management/soft-water/page"),        { ssr: false });
const CompressorPage       = dynamic(() => import("@/app/dashboard/utility-management/compressor/page"),        { ssr: false });
const ChemTreatPage        = dynamic(() => import("@/app/dashboard/utility-management/chemical-treatment/page"),{ ssr: false });
const MachineUtilityPage   = dynamic(() => import("@/app/dashboard/utility-management/machine-utility/page"),  { ssr: false });
const ReadingsPage         = dynamic(() => import("@/app/dashboard/utility-management/readings/page"),          { ssr: false });
const DevicesPage          = dynamic(() => import("@/app/dashboard/utility-management/devices/page"),           { ssr: false });
const KPICenterPage        = dynamic(() => import("@/app/dashboard/utility-management/kpi-center/page"),        { ssr: false });
const AlarmCenterPage      = dynamic(() => import("@/app/dashboard/utility-management/alarm-center/page"),      { ssr: false });
const AlarmRulesPage       = dynamic(() => import("@/app/dashboard/utility-management/alarm-rules/page"),       { ssr: false });
const BillingPage          = dynamic(() => import("@/app/dashboard/utility-management/billing/page"),           { ssr: false });
const TransactionsPage     = dynamic(() => import("@/app/dashboard/utility-management/transactions/page"),      { ssr: false });
const UtilReportsPage      = dynamic(() => import("@/app/dashboard/utility-management/reports/page"),           { ssr: false });
const UtilIntegrationPage  = dynamic(() => import("@/app/dashboard/utility-management/integration/page"),      { ssr: false });
const IoTPage              = dynamic(() => import("@/app/dashboard/iot/page"),                                  { ssr: false });
const ESGPage              = dynamic(() => import("@/app/dashboard/esg/page"),                                  { ssr: false });

export default function UtilityManagementPage() {
  const tabs = [
    { key: "assets",             label: "Assets",             permission: "utilities.view", content: <AssetsPage /> },
    { key: "electricity",        label: "Electricity",        permission: "utilities.view", content: <ElectricityPage /> },
    { key: "water",              label: "Water",              permission: "utilities.view", content: <WaterPage /> },
    { key: "solar",              label: "Solar",              permission: "utilities.view", content: <SolarPage /> },
    { key: "steam",              label: "Steam",              permission: "utilities.view", content: <SteamPage /> },
    { key: "wastewater",         label: "Wastewater",         permission: "utilities.view", content: <WastewaterPage /> },
    { key: "soft-water",         label: "Soft Water",         permission: "utilities.view", content: <SoftWaterPage /> },
    { key: "compressor",         label: "Compressor",         permission: "utilities.view", content: <CompressorPage /> },
    { key: "chemical-treatment", label: "Chemical Treatment", permission: "utilities.view", content: <ChemTreatPage /> },
    { key: "machine-utility",    label: "Machine Utility",    permission: "utilities.view", content: <MachineUtilityPage /> },
    { key: "readings",           label: "Readings",           permission: "utilities.view", content: <ReadingsPage /> },
    { key: "devices",            label: "Devices",            permission: "utilities.view", content: <DevicesPage /> },
    { key: "kpi-center",         label: "KPI Center",         permission: "utilities.view", content: <KPICenterPage /> },
    { key: "alarm-center",       label: "Alarm Center",       permission: "utilities.view", content: <AlarmCenterPage /> },
    { key: "alarm-rules",        label: "Alarm Rules",        permission: "utilities.view", content: <AlarmRulesPage /> },
    { key: "billing",            label: "Billing",            permission: "utilities.view", content: <BillingPage /> },
    { key: "transactions",       label: "Transactions",       permission: "utilities.view", content: <TransactionsPage /> },
    { key: "reports",            label: "Reports",            permission: "utilities.view", content: <UtilReportsPage /> },
    { key: "integration",        label: "Integration",        permission: "utilities.view", content: <UtilIntegrationPage /> },
    { key: "iot",                label: "IoT",                permission: "utilities.view", content: <IoTPage /> },
    { key: "esg",                label: "ESG",                permission: "utilities.view", content: <ESGPage /> },
  ];
  return (
    <ModuleWorkspace
      title="Utility Management"
      description="Electricity, water, solar, steam, IoT sensors, ESG, alarms, KPIs"
      permission="utilities.view"
      tabs={tabs}
      defaultTab="assets"
    />
  );
}

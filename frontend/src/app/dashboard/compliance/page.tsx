"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { ModuleWorkspace } from "@/components/workspace";
import { useDrawer } from "@/components/workspace/WorkspaceDrawer";

// ── Lazy tab content from existing pages ──────────────────────────────────────
// Each tab embeds the existing page component directly.
// When Phase 2 conversion lands, swap these for inline content.

import dynamic from "next/dynamic";

const GS1Page       = dynamic(() => import("@/app/dashboard/gs1/page"),       { ssr: false });
const QualityCerts  = dynamic(() => import("@/app/dashboard/quality/certificates/page"), { ssr: false });

export default function CompliancePage() {
  const { open } = useDrawer();
  const searchParams = useSearchParams();

  const tabs = [
    {
      key: "gs1",
      label: "GS1 & Labels",
      permission: "gs1.view",
      content: <GS1Page />,
    },
    {
      key: "regulatory-certs",
      label: "Regulatory Certs",
      permission: "quality.view",
      content: <QualityCerts />,
    },
  ];

  return (
    <ModuleWorkspace
      title="Compliance"
      description="GS1 labels, barcodes, regulatory certificates"
      permission="gs1.view"
      tabs={tabs}
      defaultTab="gs1"
    />
  );
}

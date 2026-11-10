"use client";

import { useCallback, useState } from "react";
import { ToastContainer } from "@/components/ui/Toast";
import { useToast } from "@/hooks/useToast";
import { AqlSpcPanel } from "./AqlSpcPanel";
import { CapaLinksPanel } from "./CapaLinksPanel";
import { ConcessionsCostsPanel } from "./ConcessionsCostsPanel";
import { LabPanel } from "./LabPanel";
import { PlansPanel } from "./PlansPanel";
import { SpecsPanel } from "./SpecsPanel";
import { ReadOnlyNotice, useQualityPermissions } from "./shared";

const SECTIONS = [
  { key: "specs", label: "Specifications & change", Panel: SpecsPanel },
  { key: "plans", label: "QC plans", Panel: PlansPanel },
  { key: "aql-spc", label: "AQL & SPC", Panel: AqlSpcPanel },
  { key: "concessions", label: "Concessions & cost", Panel: ConcessionsCostsPanel },
  { key: "lab", label: "Retain samples & methods", Panel: LabPanel },
  { key: "capa", label: "CAPA links", Panel: CapaLinksPanel },
] as const;

export function QAEnterpriseWorkspace() {
  const { canView } = useQualityPermissions();
  const { toasts, toast, dismiss } = useToast();
  const notify = useCallback((message: string, type: "success" | "error" = "success") => toast(type, message), [toast]);
  const [active, setActive] = useState<(typeof SECTIONS)[number]["key"]>("specs");
  const current = SECTIONS.find((s) => s.key === active) ?? SECTIONS[0];

  return (
    <div data-testid="qa-enterprise-workspace" className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold text-gray-900">QA governance</h2>
        <p className="text-sm text-gray-500">Specifications, QC plans, sampling and SPC, concessions, quality cost, laboratory evidence and CAPA links.</p>
      </div>
      {!canView ? (
        <ReadOnlyNotice>QA governance requires quality.view.</ReadOnlyNotice>
      ) : (
        <>
          <div role="tablist" aria-label="QA governance sections" className="flex flex-wrap gap-2 border-b border-gray-200 pb-2">
            {SECTIONS.map((s) => (
              <button key={s.key} type="button" role="tab" aria-selected={active === s.key} onClick={() => setActive(s.key)}
                className={`rounded-lg px-3 py-1.5 text-sm font-medium ${active === s.key ? "bg-indigo-600 text-white" : "text-gray-600 hover:bg-gray-100"}`}>
                {s.label}
              </button>
            ))}
          </div>
          <div role="tabpanel" aria-label={current.label}>
            <current.Panel notify={notify} />
          </div>
        </>
      )}
      <ToastContainer toasts={toasts} onDismiss={dismiss} />
    </div>
  );
}

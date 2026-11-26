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
import { SupplierAuditsPanel } from "./SupplierAuditsPanel";
import { ReadOnlyNotice, useQualityPermissions } from "./shared";
import { tx, lx } from "@/lib/i18n/core";

const SECTIONS = lx(() => [
  { key: "specs", label: tx("Specifications & change"), Panel: SpecsPanel },
  { key: "plans", label: tx("QC plans"), Panel: PlansPanel },
  { key: "aql-spc", label: tx("AQL & SPC"), Panel: AqlSpcPanel },
  { key: "concessions", label: tx("Concessions & cost"), Panel: ConcessionsCostsPanel },
  { key: "lab", label: tx("Retain samples & methods"), Panel: LabPanel },
  { key: "suppliers", label: tx("Supplier audits"), Panel: SupplierAuditsPanel },
  { key: "capa", label: tx("CAPA links"), Panel: CapaLinksPanel },
] as const);

export function QAEnterpriseWorkspace() {
  const { canView } = useQualityPermissions();
  const { toasts, toast, dismiss } = useToast();
  const notify = useCallback((message: string, type: "success" | "error" = "success") => toast(type, message), [toast]);
  const [active, setActive] = useState<(typeof SECTIONS)[number]["key"]>("specs");
  const current = SECTIONS.find((s) => s.key === active) ?? SECTIONS[0];

  return (
    <div data-testid="qa-enterprise-workspace" className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold text-gray-900">{tx("QA governance")}</h2>
        <p className="text-sm text-gray-500">{tx("Specifications, QC plans, sampling and SPC, concessions, quality cost, laboratory evidence, supplier audits and CAPA links.")}</p>
      </div>
      {!canView ? (
        <ReadOnlyNotice>{tx("QA governance requires quality.view.")}</ReadOnlyNotice>
      ) : (
        <>
          <div role="tablist" aria-label={tx("QA governance sections")} className="flex flex-wrap gap-2 border-b border-gray-200 pb-2">
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

#!/usr/bin/env node
const { execSync } = require("child_process");
const fs = require("fs");
const path = require("path");

const routes = [
  ["/dashboard/custom-fields/ai", "674b6c5", "frontend/src/app/dashboard/custom-fields/ai/page.tsx"],
  ["/dashboard/reports/inventory", "674b6c5", "frontend/src/app/dashboard/reports/inventory/page.tsx"],
  ["/dashboard/reports/production", "674b6c5", "frontend/src/app/dashboard/reports/production/page.tsx"],
  ["/dashboard/reports/procurement", "674b6c5", "frontend/src/app/dashboard/reports/procurement/page.tsx"],
  ["/dashboard/reports/sales", "674b6c5", "frontend/src/app/dashboard/reports/sales/page.tsx"],
  ["/dashboard/reports/finance", "674b6c5", "frontend/src/app/dashboard/reports/finance/page.tsx"],
  ["/dashboard/reports/payments", "674b6c5", "frontend/src/app/dashboard/reports/payments/page.tsx"],
  ["/dashboard/reports/marketing", "674b6c5", "frontend/src/app/dashboard/reports/marketing/page.tsx"],
  ["/dashboard/report-builder/ai", "674b6c5", "frontend/src/app/dashboard/report-builder/ai/page.tsx"],
  ["/dashboard/chatter/reports", "674b6c5", "frontend/src/app/dashboard/chatter/reports/page.tsx"],
  ["/dashboard/chatter/ai", "674b6c5", "frontend/src/app/dashboard/chatter/ai/page.tsx"],
  ["/dashboard/notification-center/reports", "674b6c5", "frontend/src/app/dashboard/notification-center/reports/page.tsx"],
  ["/dashboard/notification-center/ai", "674b6c5", "frontend/src/app/dashboard/notification-center/ai/page.tsx"],
  ["/dashboard/bank-reconciliation/ai", "674b6c5", "frontend/src/app/dashboard/bank-reconciliation/ai/page.tsx"],
  ["/dashboard/invoice-match/ai", "674b6c5", "frontend/src/app/dashboard/invoice-match/ai/page.tsx"],
  ["/dashboard/fixed-assets/ai", "674b6c5", "frontend/src/app/dashboard/fixed-assets/ai/page.tsx"],
  ["/dashboard/dimensions/ai", "674b6c5", "frontend/src/app/dashboard/dimensions/ai/page.tsx"],
  ["/dashboard/tax/reports", "674b6c5", "frontend/src/app/dashboard/tax/reports/page.tsx"],
  ["/dashboard/expenses/reports", "674b6c5", "frontend/src/app/dashboard/expenses/reports/page.tsx"],
  ["/dashboard/expenses/ai", "674b6c5", "frontend/src/app/dashboard/expenses/ai/page.tsx"],
  ["/dashboard/recruitment/reports", "674b6c5", "frontend/src/app/dashboard/recruitment/reports/page.tsx"],
  ["/dashboard/recruitment/ai", "674b6c5", "frontend/src/app/dashboard/recruitment/ai/page.tsx"],
  ["/dashboard/ess/ai", "674b6c5", "frontend/src/app/dashboard/ess/ai/page.tsx"],
  ["/dashboard/appraisals/reports", "674b6c5", "frontend/src/app/dashboard/appraisals/reports/page.tsx"],
  ["/dashboard/appraisals/ai", "674b6c5", "frontend/src/app/dashboard/appraisals/ai/page.tsx"],
  ["/dashboard/training/reports", "674b6c5", "frontend/src/app/dashboard/training/reports/page.tsx"],
  ["/dashboard/training/ai", "674b6c5", "frontend/src/app/dashboard/training/ai/page.tsx"],
  ["/dashboard/timesheets/reports", "674b6c5", "frontend/src/app/dashboard/timesheets/reports/page.tsx"],
  ["/dashboard/timesheets/ai", "674b6c5", "frontend/src/app/dashboard/timesheets/ai/page.tsx"],
  ["/dashboard/webhooks/reports", "674b6c5", "frontend/src/app/dashboard/webhooks/reports/page.tsx"],
  ["/dashboard/fleet/reports", "674b6c5", "frontend/src/app/dashboard/fleet/reports/page.tsx"],
  ["/dashboard/tpm/ai", "674b6c5", "frontend/src/app/dashboard/tpm/ai/page.tsx"],
  ["/dashboard/kanban/reports", "674b6c5", "frontend/src/app/dashboard/kanban/reports/page.tsx"],
  ["/dashboard/kanban/ai", "674b6c5", "frontend/src/app/dashboard/kanban/ai/page.tsx"],
  ["/dashboard/procurement-suggestion/ai", "674b6c5", "frontend/src/app/dashboard/procurement-suggestion/ai/page.tsx"],
  ["/dashboard/subcontracting/ai", "674b6c5", "frontend/src/app/dashboard/subcontracting/ai/page.tsx"],
  ["/dashboard/landed-cost/ai", "674b6c5", "frontend/src/app/dashboard/landed-cost/ai/page.tsx"],
  ["/dashboard/qms/reports", "674b6c5", "frontend/src/app/dashboard/qms/reports/page.tsx"],
  ["/dashboard/qms/ai", "674b6c5", "frontend/src/app/dashboard/qms/ai/page.tsx"],
  ["/dashboard/contracts/ai", "674b6c5", "frontend/src/app/dashboard/contracts/ai/page.tsx"],
  ["/dashboard/recurring-orders/reports", "674b6c5", "frontend/src/app/dashboard/recurring-orders/reports/page.tsx"],
  ["/dashboard/recurring-orders/ai", "674b6c5", "frontend/src/app/dashboard/recurring-orders/ai/page.tsx"],
  ["/dashboard/commissions/ai", "674b6c5", "frontend/src/app/dashboard/commissions/ai/page.tsx"],
  ["/dashboard/van-sales/ai", "674b6c5", "frontend/src/app/dashboard/van-sales/ai/page.tsx"],
  ["/dashboard/portal/ai", "674b6c5", "frontend/src/app/dashboard/portal/ai/page.tsx"],
  ["/dashboard/portal/reports", "674b6c5", "frontend/src/app/dashboard/portal/reports/page.tsx"],
  ["/dashboard/utility-management/reports/daily-consumption", "674b6c5", "frontend/src/app/dashboard/utility-management/reports/daily-consumption/page.tsx"],
  ["/dashboard/utility-management/reports/equipment-efficiency", "674b6c5", "frontend/src/app/dashboard/utility-management/reports/equipment-efficiency/page.tsx"],
  ["/dashboard/utility-management/reports/treatment", "674b6c5", "frontend/src/app/dashboard/utility-management/reports/treatment/page.tsx"],
  ["/dashboard/utility-management/reports/cost-allocation", "674b6c5", "frontend/src/app/dashboard/utility-management/reports/cost-allocation/page.tsx"],
  ["/dashboard/utility-management/reports/load-analysis", "674b6c5", "frontend/src/app/dashboard/utility-management/reports/load-analysis/page.tsx"],
  ["/dashboard/utility-management/reports/anomalies", "674b6c5", "frontend/src/app/dashboard/utility-management/reports/anomalies/page.tsx"],
  ["/dashboard/utility-management/reports/sustainability", "674b6c5", "frontend/src/app/dashboard/utility-management/reports/sustainability/page.tsx"],
  ["/dashboard/esg/reports", "27ebada", "frontend/src/app/dashboard/esg/reports/page.tsx"],
];

let restored = 0, failed = 0;
for (const [route, commit, gitPath] of routes) {
  try {
    const content = execSync(`git show ${commit}:${gitPath}`, { encoding: "utf8" });
    const dir = path.dirname(gitPath);
    fs.mkdirSync(dir, { recursive: true });
    fs.writeFileSync(gitPath, content);
    restored++;
    console.log("OK:", route);
  } catch (e) {
    console.log("FAIL:", route, String(e.message).slice(0, 100));
    failed++;
  }
}
console.log("\nRestored:", restored, "| Failed:", failed);

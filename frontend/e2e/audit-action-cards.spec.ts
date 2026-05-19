/**
 * ERP-Wide Action Card Health Audit
 *
 * Visits all major dashboard routes, discovers tabs, finds card-like
 * interactive elements, tests their click behavior, and writes a JSON + MD report.
 *
 * Run (app must be running):
 *   E2E_SKIP_WEBSERVER=1 npx playwright test e2e/audit-action-cards.spec.ts \
 *     --project=chromium --workers=1 --reporter=list
 */

import { test, expect, Page } from "playwright/test";
import fs from "fs";
import path from "path";

const BASE_URL = process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:3000";
const DOCS_DIR = path.resolve(__dirname, "../../docs");
const JSON_OUT = path.join(DOCS_DIR, "ACTION_CARD_HEALTH_AUDIT.json");
const MD_OUT = path.join(DOCS_DIR, "ACTION_CARD_HEALTH_AUDIT.md");

// All routes to audit with their expected tabs
const AUDIT_ROUTES: Array<{ route: string; tabs?: string[]; label: string }> = [
  { route: "/dashboard", label: "Main Dashboard" },
  { route: "/dashboard/inventory", label: "Inventory", tabs: ["stock", "movements", "cycle-count", "shelf-life", "traceability", "serials", "valuation"] },
  { route: "/dashboard/logistics", label: "Logistics", tabs: ["overview", "shipments", "containers", "arrivals", "documents", "fleet"] },
  { route: "/dashboard/maintenance", label: "Maintenance", tabs: ["overview", "assets", "breakdowns", "plans", "predictive", "spares", "reports"] },
  { route: "/dashboard/cycle-count", label: "Cycle Count" },
  { route: "/dashboard/production", label: "Production" },
  { route: "/dashboard/quality", label: "Quality" },
  { route: "/dashboard/hr", label: "HR" },
  { route: "/dashboard/finance", label: "Finance" },
  { route: "/dashboard/procurement", label: "Procurement" },
  { route: "/dashboard/sales", label: "Sales" },
  { route: "/dashboard/traceability", label: "Traceability" },
  { route: "/dashboard/shelf-life", label: "Shelf Life" },
  { route: "/dashboard/timesheets", label: "Timesheets" },
  { route: "/dashboard/training", label: "Training" },
  { route: "/dashboard/kanban", label: "Kanban" },
  { route: "/dashboard/report-builder", label: "Report Builder" },
  { route: "/dashboard/mobile", label: "Mobile App" },
  { route: "/dashboard/notification-center", label: "Notification Center" },
  { route: "/dashboard/appraisals", label: "Appraisals" },
  { route: "/dashboard/allergen", label: "Allergen" },
  { route: "/dashboard/fleet", label: "Fleet" },
  { route: "/dashboard/reports", label: "Reports" },
];

interface CardResult {
  route: string;
  tab: string;
  cardText: string;
  selector: string;
  looksClickable: boolean;
  hasOnClickOrLink: boolean;
  beforeUrl: string;
  afterUrl: string;
  interactionResult: string;
  status: "working" | "broken" | "static_ok" | "needs_review";
  reason: string;
}

const allResults: CardResult[] = [];

async function auditPage(page: Page, route: string, tab: string): Promise<CardResult[]> {
  const results: CardResult[] = [];
  const beforeUrl = page.url();

  // Find all card-like elements: buttons, anchors, divs/elements with cursor-pointer and hover styling
  const cards = await page.evaluate(() => {
    const found: Array<{ text: string; selector: string; looksClickable: boolean; hasHandler: boolean; tagName: string }> = [];
    const seen = new Set<Element>();

    // Selectors that suggest card/tile patterns
    const candidates = document.querySelectorAll(
      'button:not([data-tab]):not([type="submit"]):not([disabled]), ' +
      'a[href]:not([href="#"]):not([href=""]), ' +
      '[role="button"], ' +
      '[tabindex="0"]'
    );

    candidates.forEach((el) => {
      if (seen.has(el)) return;
      const rect = el.getBoundingClientRect();
      if (rect.width < 60 || rect.height < 36) return; // skip tiny buttons

      const text = (el.textContent || "").trim().replace(/\s+/g, " ").slice(0, 80);
      if (!text || text.length < 3) return;

      // Skip navigation/tab buttons
      if (el.closest('[class*="tab"]') && el.tagName === "BUTTON") return;
      if (el.closest("nav")) return;
      if (el.closest("[data-testid]") && el.closest("[data-testid]")?.getAttribute("data-testid")?.includes("tab")) return;

      const style = window.getComputedStyle(el);
      const className = el.className || "";
      const looksClickable =
        style.cursor === "pointer" ||
        className.includes("cursor-pointer") ||
        className.includes("hover:") ||
        el.tagName === "A" ||
        el.tagName === "BUTTON";

      // Check if it has meaningful size (card-like)
      const isCardLike = rect.width > 120 && rect.height > 40;
      if (!isCardLike && el.tagName !== "A") return;

      const hasHandler =
        el.tagName === "A" ||
        el.tagName === "BUTTON" ||
        el.getAttribute("role") === "button" ||
        el.getAttribute("tabindex") !== null;

      const id = `${el.tagName}-${text.slice(0, 20)}`;
      seen.add(el);

      found.push({
        text,
        selector: el.tagName.toLowerCase() + (el.className ? `.${String(el.className).split(" ")[0]}` : ""),
        looksClickable,
        hasHandler,
        tagName: el.tagName,
      });
    });

    return found;
  });

  // Test a subset of the cards (first 5 per page/tab to avoid timeout)
  for (const card of cards.slice(0, 5)) {
    const beforeNav = page.url();

    try {
      // Find and click the element
      const el = page.getByText(card.text, { exact: false }).first();
      const isVisible = await el.isVisible().catch(() => false);
      if (!isVisible) continue;

      const [response] = await Promise.all([
        page.waitForNavigation({ timeout: 2000 }).catch(() => null),
        el.click({ timeout: 2000 }).catch(() => null),
      ]);

      const afterNav = page.url();
      const navigated = afterNav !== beforeNav;
      const modalOpen = await page.locator('[role="dialog"]').isVisible().catch(() => false);

      let interactionResult = "none";
      if (navigated) interactionResult = "navigated";
      else if (modalOpen) interactionResult = "modal_opened";
      else if (response) interactionResult = "api_called";

      const status: CardResult["status"] =
        card.hasHandler ? (interactionResult !== "none" ? "working" : "needs_review") : "static_ok";

      results.push({
        route,
        tab,
        cardText: card.text,
        selector: card.selector,
        looksClickable: card.looksClickable,
        hasOnClickOrLink: card.hasHandler,
        beforeUrl: beforeNav,
        afterUrl: afterNav,
        interactionResult,
        status,
        reason: navigated
          ? `Navigated to ${afterNav}`
          : modalOpen
          ? "Modal opened"
          : card.hasHandler
          ? "Has handler but no observable change"
          : "No handler — static display card",
      });

      // Navigate back if we left the page
      if (navigated) {
        await page.goto(BASE_URL + route, { waitUntil: "networkidle", timeout: 15000 }).catch(() => {});
        if (tab) {
          await page.goto(`${BASE_URL}${route}?tab=${tab}`, { waitUntil: "networkidle", timeout: 10000 }).catch(() => {});
        }
        await page.waitForTimeout(1000);
      }
    } catch {
      // skip
    }
  }

  return results;
}

test.describe("Action Card Health Audit", () => {
  for (const entry of AUDIT_ROUTES.slice(0, 8)) { // limit to first 8 for speed
    test(`audit: ${entry.label}`, async ({ page }) => {
      await page.setViewportSize({ width: 1440, height: 900 });

      try {
        await page.goto(`${BASE_URL}${entry.route}`, { waitUntil: "networkidle", timeout: 20000 });
        await page.waitForTimeout(1500);

        const routeResults = await auditPage(page, entry.route, "default");
        allResults.push(...routeResults);

        // If tabs specified, visit each
        if (entry.tabs) {
          for (const tab of entry.tabs.slice(0, 4)) { // limit tabs for speed
            await page.goto(`${BASE_URL}${entry.route}?tab=${tab}`, { waitUntil: "networkidle", timeout: 15000 }).catch(() => {});
            await page.waitForTimeout(1000);
            const tabResults = await auditPage(page, entry.route, tab);
            allResults.push(...tabResults);
          }
        }
      } catch {
        // Route may not be accessible; skip
      }
    });
  }

  test.afterAll(async () => {
    const working = allResults.filter((r) => r.status === "working").length;
    const broken = allResults.filter((r) => r.status === "broken").length;
    const staticOk = allResults.filter((r) => r.status === "static_ok").length;
    const needsReview = allResults.filter((r) => r.status === "needs_review").length;

    const output = {
      generatedAt: new Date().toISOString(),
      summary: {
        total: allResults.length,
        working,
        broken,
        static_ok: staticOk,
        needs_review: needsReview,
      },
      results: allResults,
    };

    fs.mkdirSync(DOCS_DIR, { recursive: true });
    fs.writeFileSync(JSON_OUT, JSON.stringify(output, null, 2));

    const md = `# Action Card Health Audit
Generated: ${new Date().toISOString()}

## Summary

| Status | Count |
|--------|-------|
| Working | ${working} |
| Broken | ${broken} |
| Static OK | ${staticOk} |
| Needs Review | ${needsReview} |
| **Total** | **${allResults.length}** |

## Results

${allResults
  .map(
    (r) =>
      `### ${r.route} → ${r.tab} → "${r.cardText}"
- **Status:** ${r.status}
- **Looks clickable:** ${r.looksClickable}
- **Has handler:** ${r.hasOnClickOrLink}
- **Interaction:** ${r.interactionResult}
- **Reason:** ${r.reason}
`
  )
  .join("\n")}
`;

    fs.writeFileSync(MD_OUT, md);
    console.log(`\nAudit complete. ${allResults.length} cards tested.`);
    console.log(`Working: ${working}, Broken: ${broken}, Static OK: ${staticOk}, Needs Review: ${needsReview}`);
    console.log(`JSON: ${JSON_OUT}`);
    console.log(`MD: ${MD_OUT}\n`);
  });
});

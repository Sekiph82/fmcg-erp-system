import { expect, test, type Route } from "playwright/test";

const downtimeId = "11111111-1111-4111-8111-111111111111";
const machineId = "22222222-2222-4222-8222-222222222222";
const workOrderId = "33333333-3333-4333-8333-333333333333";
const runtimeId = "44444444-4444-4444-8444-444444444444";
const baselineId = "55555555-5555-4555-8555-555555555555";

async function fulfillJson(route: Route, body: unknown) {
  await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
}

test.use({ storageState: { cookies: [], origins: [] } });

test("shows evidence-backed handoff destinations without creating or assigning actions", async ({ page }) => {
  const baseUrl = new URL(process.env.E2E_BASE_URL || "http://localhost:3000");
  await page.context().addCookies([{
    name: "erp_access_token",
    value: "synthetic-m26-handoff-token",
    url: baseUrl.origin,
    httpOnly: true,
    sameSite: "Lax",
  }]);
  await page.route("**/api/v1/**", async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname.endsWith("/auth/me")) {
      return fulfillJson(route, {
        id: "synthetic-m26-user",
        email: "m26@example.invalid",
        username: "synthetic-m26-user",
        full_name: "Synthetic M26 User",
        is_active: true,
        is_superuser: true,
        must_change_password: false,
        roles: [],
        permission_codes: [],
        modules: ["production", "maintenance", "training"],
        scopes: [],
        feature_flags: {},
      });
    }
    if (url.pathname.endsWith("/modules/manifest")) {
      return fulfillJson(route, { permission_codes: [], visible_permission_codes: [] });
    }
    if (url.pathname.endsWith("/performance/anomalies")) {
      return fulfillJson(route, {
        period_start: "2026-11-08",
        period_end: "2026-11-08",
        baseline_start: "2026-10-09",
        anomalies: [],
        insufficient_baseline_machine_ids: [],
        unavailable_runtime_log_ids: [],
        overlapping_runtime_log_ids: [],
        data_notes: [],
      });
    }
    if (url.pathname.endsWith("/performance/downtime-correlations")) {
      return fulfillJson(route, {
        period_start: "2026-11-08",
        period_end: "2026-11-08",
        events: [{
          downtime_id: downtimeId,
          machine_id: machineId,
          machine_code: "SYN-M-01",
          machine_name: "Synthetic Mixer",
          work_order_id: workOrderId,
          downtime_class: "mechanical_breakdown",
          start_time: "2026-11-08T08:00:00Z",
          end_time: "2026-11-08T09:00:00Z",
          duration_minutes: 60,
          observed_operator_ids: [],
          runtime_log_ids: [runtimeId],
          labor_logs: [],
          quality_inspections: [],
          waste_records: [],
          correlation_basis: ["same_machine_time_overlap"],
        }],
        follow_up_handoffs: [{
          handoff_id: `maintenance:${downtimeId}`,
          destination: "maintenance",
          destination_path: "/dashboard/maintenance?tab=breakdowns",
          title: "Review machine downtime anomaly",
          rationale: "A recorded runtime interval exceeded the machine-specific historical rule.",
          machine_id: machineId,
          machine_code: "SYN-M-01",
          downtime_id: downtimeId,
          work_order_id: workOrderId,
          source_ids: [downtimeId, runtimeId, baselineId],
          attribution_note: "Review suggestion only. No maintenance, training, or production plan record was created or changed; correlation does not establish cause or operator responsibility.",
        }],
        data_notes: ["Synthetic mocked evidence; no records were created."],
      });
    }
    if (url.pathname.endsWith("/machines") || url.pathname.endsWith("/performance")) {
      return fulfillJson(route, []);
    }
    return fulfillJson(route, {});
  });

  await page.goto("/dashboard/machine-ops/performance", { waitUntil: "domcontentloaded" });
  const correlations = page.getByLabel("Downtime production correlations");
  await expect(correlations).toBeVisible({ timeout: 30_000 });
  const handoff = correlations.getByLabel("Evidence-backed follow-up handoffs");
  await expect(handoff.getByText("Review machine downtime anomaly")).toBeVisible();
  await expect(handoff.getByRole("link", { name: "Open maintenance module" })).toHaveAttribute("href", "/dashboard/maintenance?tab=breakdowns");
  await handoff.getByText("Evidence IDs and scope").click();
  await expect(handoff.getByText(new RegExp(`${downtimeId}.*${runtimeId}.*${baselineId}`))).toBeVisible();
  await expect(handoff.getByText(/No maintenance, training, or production plan record was created or changed/i)).toBeVisible();
  await expect(handoff.getByText(/does not establish cause or operator responsibility/i)).toBeVisible();
});

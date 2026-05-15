import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { moduleParityEntries } from "./api-parity-manifest.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "..");
const dashboardRoot = path.join(root, "src", "app", "dashboard");
const strict = process.argv.includes("--strict");

function walk(dir) {
  return readdirSync(dir).flatMap((entry) => {
    const fullPath = path.join(dir, entry);
    const stats = statSync(fullPath);
    if (stats.isDirectory()) return walk(fullPath);
    if (entry.endsWith(".tsx")) return [fullPath];
    return [];
  });
}

function toPosix(value) {
  return value.split(path.sep).join("/");
}

function pageRoute(filePath) {
  const relative = toPosix(path.relative(path.join(root, "src", "app"), filePath));
  return `/${relative.replace(/\/page\.tsx$/, "")}`;
}

function routeMatches(route, entryRoute) {
  return route === entryRoute || route.startsWith(`${entryRoute}/`);
}

const files = walk(dashboardRoot);
const rawApiFiles = files.filter((file) => readFileSync(file, "utf8").includes("/api/v1/"));
const manifestErrors = [];

for (const entry of moduleParityEntries) {
  const routePath = path.join(root, entry.frontendRoute.replace(/^\/dashboard/, "src/app/dashboard"), "page.tsx");
  if (!existsSync(routePath)) {
    manifestErrors.push(`${entry.key}: missing frontend route ${entry.frontendRoute}`);
  }
  if (entry.frontendClient) {
    const clientPath = path.join(root, entry.frontendClient);
    if (!existsSync(clientPath)) {
      manifestErrors.push(`${entry.key}: missing frontend client ${entry.frontendClient}`);
    }
  }
}

const uncoveredRawApiFiles = rawApiFiles.filter((file) => {
  const route = pageRoute(file);
  return !moduleParityEntries.some((entry) => entry.allowRawApiPath && routeMatches(route, entry.frontendRoute));
});

const summary = {
  manifest_entries: moduleParityEntries.length,
  dashboard_pages_scanned: files.length,
  raw_api_pages: rawApiFiles.length,
  uncovered_raw_api_pages: uncoveredRawApiFiles.length,
  strict,
};

console.log(JSON.stringify(summary, null, 2));

if (uncoveredRawApiFiles.length > 0) {
  console.log("\nUncovered raw /api/v1 dashboard pages:");
  for (const file of uncoveredRawApiFiles) {
    console.log(`- ${toPosix(path.relative(root, file))}`);
  }
}

if (manifestErrors.length > 0) {
  console.log("\nManifest errors:");
  for (const error of manifestErrors) {
    console.log(`- ${error}`);
  }
}

if (manifestErrors.length > 0 || (strict && uncoveredRawApiFiles.length > 0)) {
  process.exitCode = 1;
}

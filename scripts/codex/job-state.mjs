import { createHash } from "node:crypto";
import { lstat, readFile, rename, unlink, writeFile } from "node:fs/promises";
import { isAbsolute, relative, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

const stages = ["SPEC", "BUILD", "REVIEW", "APPROVE", "MERGED", "ESCALATED"];
const lenses = ["rules", "code", "tests"];

function assertReviewPasses(job, required) {
  const failed = required.filter((lens) => job.reviews?.[lens] !== "pass");
  if (failed.length) throw new Error(`Cannot enter ${job.stage}: missing PASS evidence for ${failed.join(", " )}.`);
}

export function validateJobState(job) {
  if (!job || typeof job !== "object" || Array.isArray(job)) throw new Error("Job metadata must be an object.");
  if (!/^[A-Z][A-Z0-9]*(?:[.-][A-Z0-9]+)+$/.test(job.id ?? "")) throw new Error("Job ID must match the canonical task ID.");
  if (typeof job.task !== "string" || !job.task.trim()) throw new Error("Job task title is required.");
  if (!stages.includes(job.stage)) throw new Error("Job stage is invalid.");
  if (!Number.isInteger(job.round) || job.round < 1) throw new Error("Review round must be a positive integer.");
  for (const lens of lenses) {
    if (!["pending", "pass", "changes"].includes(job.reviews?.[lens])) throw new Error(`Review ${lens} must be pending, pass, or changes.`);
    if (job.reviews[lens] === "pass") {
      const reference = job.reviewEvidence?.[lens];
      if (!reference || typeof reference.path !== "string" || !reference.path.trim() || !/^[0-9a-f]{64}$/i.test(reference.sha256 ?? "")) {
        throw new Error(`Review ${lens} PASS requires a repository evidence path and SHA-256.`);
      }
      if (isAbsolute(reference.path) || reference.path.split(/[\\/]/).some((part) => part === ".." || part === ".")) {
        throw new Error(`Review ${lens} evidence path must stay inside the repository.`);
      }
    }
  }
  if (["BUILD", "REVIEW", "APPROVE", "MERGED"].includes(job.stage)) assertReviewPasses(job, ["rules"]);
  if (["REVIEW", "APPROVE", "MERGED"].includes(job.stage)) assertReviewPasses(job, lenses);
  if (job.stage === "MERGED" && (job.accepted !== true || !/^[0-9a-f]{40}$/i.test(job.publishedCommit ?? ""))) {
    throw new Error("MERGED requires accepted evidence and the published target commit SHA.");
  }
  if (job.stage === "ESCALATED" && job.blockedTaskId !== job.id) throw new Error("ESCALATED requires this exact task to be blocked.");
  if (typeof job.updatedAt !== "string" || Number.isNaN(Date.parse(job.updatedAt))) throw new Error("updatedAt must be a valid timestamp.");
  return job;
}

export function isPathWithin(parent, candidate) {
  const relativePath = relative(resolve(parent), resolve(candidate));
  return relativePath !== "" && relativePath !== ".." && !relativePath.startsWith(`..${sep}`) && !isAbsolute(relativePath);
}

export function transitionJob(job, stage, evidence = {}, now = new Date()) {
  validateJobState(job);
  if (!stages.includes(stage)) throw new Error(`Unknown job stage ${stage}.`);
  const order = { SPEC: 0, BUILD: 1, REVIEW: 2, APPROVE: 3, MERGED: 4 };
  if (stage === "ESCALATED") {
    if (evidence.blockedTaskId !== job.id) throw new Error("ESCALATED is allowed only while this exact task is blocked.");
  } else if (job.stage === "ESCALATED") {
    throw new Error("An escalated task must be explicitly returned to READY before work can resume.");
  } else if (order[stage] !== order[job.stage] + 1) {
    throw new Error(`Job stage must advance one step at a time from ${job.stage}.`);
  }
  const next = { ...job, ...evidence, stage, updatedAt: now.toISOString() };
  validateJobState(next);
  return next;
}

export function updateJobReview(job, lens, result, evidence = null, now = new Date()) {
  validateJobState(job);
  if (!lenses.includes(lens) || !["pending", "pass", "changes"].includes(result)) throw new Error("Review result is invalid.");
  if (result === "pass" && (!evidence || typeof evidence.path !== "string" || !/^[0-9a-f]{64}$/i.test(evidence.sha256 ?? ""))) {
    throw new Error(`Review ${lens} PASS requires a repository evidence path and SHA-256.`);
  }
  const reviewEvidence = { ...job.reviewEvidence };
  if (result === "pass") reviewEvidence[lens] = evidence;
  else delete reviewEvidence[lens];
  const next = { ...job, reviews: { ...job.reviews, [lens]: result }, reviewEvidence, updatedAt: now.toISOString() };
  validateJobState(next);
  return next;
}

async function run() {
  const args = process.argv.slice(2);
  const value = (name) => {
    const index = args.indexOf(name);
    return index >= 0 ? args[index + 1] : null;
  };
  const taskId = value("--task");
  if (!taskId || !/^[A-Z][A-Z0-9]*(?:[.-][A-Z0-9]+)+$/.test(taskId)) throw new Error("Provide a valid --task ID.");
  const root = resolve(fileURLToPath(new URL("../..", import.meta.url)));
  const jobsRoot = resolve(root, "project-control/codex/jobs");
  const jobDirectory = resolve(jobsRoot, taskId);
  if (!isPathWithin(jobsRoot, jobDirectory)) throw new Error("Job path escapes the project jobs directory.");
  const directoryInfo = await lstat(jobDirectory);
  if (directoryInfo.isSymbolicLink() || !directoryInfo.isDirectory()) throw new Error("Job directory must be a real directory inside project jobs.");
  const path = resolve(jobDirectory, "job.json");
  if (!isPathWithin(jobDirectory, path)) throw new Error("Job metadata path escapes its task directory.");
  const info = await lstat(path);
  if (info.isSymbolicLink() || !info.isFile()) throw new Error("Job metadata must be a regular file.");
  const job = JSON.parse(await readFile(path, "utf8"));
  let updated;
  if (value("--stage")) {
    const evidence = {};
    if (value("--blocked-task-id")) evidence.blockedTaskId = value("--blocked-task-id");
    if (args.includes("--accepted")) evidence.accepted = true;
    if (value("--published-commit")) evidence.publishedCommit = value("--published-commit");
    updated = transitionJob(job, value("--stage"), evidence);
  } else if (value("--review")) {
    const [lens, result] = value("--review").split("=");
    let evidence = null;
    if (result === "pass") {
      const evidencePath = value("--evidence");
      if (!evidencePath || isAbsolute(evidencePath)) throw new Error("PASS requires --evidence with a repository-relative file path.");
      const absoluteEvidencePath = resolve(root, evidencePath);
      const relativeEvidencePath = relative(root, absoluteEvidencePath);
      if (!relativeEvidencePath || relativeEvidencePath.startsWith(`..${sep}`) || relativeEvidencePath === "..") throw new Error("Review evidence must stay inside the repository.");
      const evidenceInfo = await lstat(absoluteEvidencePath);
      if (evidenceInfo.isSymbolicLink() || !evidenceInfo.isFile()) throw new Error("Review evidence must be a regular repository file.");
      const bytes = await readFile(absoluteEvidencePath);
      evidence = { path: relativeEvidencePath.split(sep).join("/"), sha256: createHash("sha256").update(bytes).digest("hex") };
    }
    updated = updateJobReview(job, lens, result, evidence);
  } else {
    throw new Error("Use --stage STAGE or --review LENS=RESULT.");
  }
  const temporary = `${path}.tmp`;
  await writeFile(temporary, `${JSON.stringify(updated, null, 2)}\n`, { encoding: "utf8", flag: "wx" });
  try { await rename(temporary, path); }
  catch (error) { await unlink(temporary).catch(() => {}); throw error; }
  console.log(`Updated ${taskId}: ${updated.stage} (${updated.updatedAt}).`);
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try { await run(); }
  catch (error) { console.error(`Job metadata update refused: ${error.message}`); process.exitCode = 1; }
}

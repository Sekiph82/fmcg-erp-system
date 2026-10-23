import test from "node:test";
import assert from "node:assert/strict";
import { isPathWithin, transitionJob, updateJobReview, validateJobState } from "./job-state.mjs";

const initial = {
  id: "M20.S01.T003",
  task: "Identify exact missing state/data invariants",
  stage: "SPEC",
  round: 1,
  reviews: { rules: "pending", code: "pending", tests: "pending" },
  updatedAt: "2026-10-22T00:00:00.000Z",
};

test("job path containment is portable and rejects sibling and parent paths", () => {
  assert.equal(isPathWithin("C:/repo/jobs", "C:/repo/jobs/M20.S01.T003/job.json"), true);
  assert.equal(isPathWithin("C:/repo/jobs", "C:/repo/jobs-elsewhere/M20.S01.T003/job.json"), false);
  assert.equal(isPathWithin("C:/repo/jobs", "C:/repo/job.json"), false);
  assert.equal(isPathWithin("/repo/jobs", "/repo/jobs/M20.S01.T003/job.json"), true);
  assert.equal(isPathWithin("/repo/jobs", "/repo/jobs-elsewhere/job.json"), false);
});

test("stage transitions require actual review evidence and advance timestamps", () => {
  assert.throws(() => updateJobReview(initial, "rules", "pass"), /requires a repository evidence path/);
  const spec = updateJobReview(initial, "rules", "pass", { path: "coordination/rules.md", sha256: "b".repeat(64) }, new Date("2026-10-22T01:00:00Z"));
  const build = transitionJob(spec, "BUILD", {}, new Date("2026-10-22T02:00:00Z"));
  assert.equal(build.stage, "BUILD");
  assert.equal(build.updatedAt, "2026-10-22T02:00:00.000Z");
  assert.throws(() => transitionJob(build, "REVIEW"), /code/);
});

test("APPROVE and MERGED require passed reviews, acceptance, and published SHA", () => {
  const reviewEvidence = Object.fromEntries(["rules", "code", "tests"].map((lens) => [lens, { path: `coordination/${lens}.md`, sha256: "c".repeat(64) }]));
  const reviewed = { ...initial, stage: "REVIEW", reviews: { rules: "pass", code: "pass", tests: "pass" }, reviewEvidence };
  assert.throws(() => transitionJob({ ...reviewed, stage: "SPEC" }, "MERGED", { accepted: true, publishedCommit: "a".repeat(40) }), /one step at a time/);
  const approved = transitionJob(reviewed, "APPROVE");
  assert.throws(() => transitionJob(approved, "MERGED", { accepted: true }), /published target commit SHA/);
  const merged = transitionJob(approved, "MERGED", { accepted: true, publishedCommit: "a".repeat(40) });
  assert.equal(validateJobState(merged).stage, "MERGED");
});

test("ESCALATED is task-specific and cannot be used to hide unblocked work", () => {
  assert.throws(() => transitionJob(initial, "ESCALATED", { blockedTaskId: "M20.S01.T004" }), /exact task is blocked/);
  const blocked = transitionJob(initial, "ESCALATED", { blockedTaskId: initial.id });
  assert.throws(() => transitionJob(blocked, "BUILD", {}), /explicitly returned to READY/);
});

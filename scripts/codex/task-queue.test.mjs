import test from "node:test";
import assert from "node:assert/strict";
import { mkdir, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { applyOwnerAnswers, claimCurrentTask, completeCurrentTask, writeTracker } from "./task-queue.mjs";
import { parseTaskState } from "./task-state.mjs";

const tracker = `# Tracker

- Current Milestone: M20 — Master Production Scheduling
- Current Sprint: M20.S01 — MPS Domain Reconciliation
- Current Task: M20.S01.T003 — Identify exact missing state/data invariants
- Current Task Status: IN_PROGRESS
- Next Task/Action: M20.S01.T003 — Identify exact missing state/data invariants
- Required Actor: CODEX

## Tasks
- [x] M20.S01.T002 — Preserve existing capabilities
- [~] M20.S01.T003 — Identify exact missing state/data invariants
- [ ] M20.S01.T004 — Define acceptance dataset

## Questions for Şekip
- Q-M20-NEXT | Confirm the explicit task after T003 | TASK: M20.S01.T004

## Owner Decisions

`;

test("validates only the explicit current task and never infers checkbox order", () => {
  const state = parseTaskState(tracker);
  assert.equal(state.currentTask.id, "M20.S01.T003");
  assert.equal(state.nextTaskSelectionRequired, true);
  assert.equal(state.completedTasks, 1);
  assert.equal(state.totalTasks, 3);
});

test("records a completed current task while requiring an explicit successor", () => {
  const completed = tracker
    .replace("- Current Task Status: IN_PROGRESS", "- Current Task Status: COMPLETE")
    .replace("- Next Task/Action: M20.S01.T003 — Identify exact missing state/data invariants", "- Next Task/Action: Select the next task explicitly")
    .replace("- [~] M20.S01.T003 — Identify exact missing state/data invariants", "- [x] M20.S01.T003 — Identify exact missing state/data invariants");
  const state = parseTaskState(completed);
  assert.equal(state.currentTask.id, "M20.S01.T003");
  assert.equal(state.currentTaskStatus, "COMPLETE");
  assert.equal(state.nextTaskSelectionRequired, true);
  assert.equal(state.completedTasks, 2);
});

test("does not require a successor after the whole tracker is complete", () => {
  const complete = tracker
    .replace("- Current Task: M20.S01.T003 — Identify exact missing state/data invariants", "- Current Task: None")
    .replace("- Current Task Status: IN_PROGRESS", "- Current Task Status: COMPLETE")
    .replace("- Next Task/Action: M20.S01.T003 — Identify exact missing state/data invariants", "- Next Task/Action: None")
    .replace("- [~] M20.S01.T003 — Identify exact missing state/data invariants", "- [x] M20.S01.T003 — Identify exact missing state/data invariants")
    .replace("- [ ] M20.S01.T004 — Define acceptance dataset", "- [x] M20.S01.T004 — Define acceptance dataset");
  const state = parseTaskState(complete);
  assert.equal(state.currentTask, null);
  assert.equal(state.currentTaskStatus, "COMPLETE");
  assert.equal(state.nextTaskSelectionRequired, false);
});

test("rejects an empty tracker instead of treating it as complete", () => {
  const empty = tracker
    .replace("- Current Task: M20.S01.T003 — Identify exact missing state/data invariants", "- Current Task: None")
    .replace("- Current Task Status: IN_PROGRESS", "- Current Task Status: COMPLETE")
    .replace("- Next Task/Action: M20.S01.T003 — Identify exact missing state/data invariants", "- Next Task/Action: None")
    .replace(/^- \[[ x~!]\] M20\.S01\.T00[2-4].*\r?\n/gm, "");
  assert.throws(() => parseTaskState(empty), /at least one canonical task row/);
});

test("rejects an in-progress row that is not the explicit active task", () => {
  const invalid = tracker
    .replace("- Current Task Status: IN_PROGRESS", "- Current Task Status: COMPLETE")
    .replace("- [~] M20.S01.T003 — Identify exact missing state/data invariants", "- [x] M20.S01.T003 — Identify exact missing state/data invariants")
    .replace("- [ ] M20.S01.T004 — Define acceptance dataset", "- [~] M20.S01.T004 — Define acceptance dataset");
  assert.throws(() => parseTaskState(invalid), /must be the explicit current task/);
});

test("claims the explicit READY task without changing other rows", () => {
  const ready = tracker
    .replace("- Current Task Status: IN_PROGRESS", "- Current Task Status: READY")
    .replace("- [~] M20.S01.T003", "- [ ] M20.S01.T003");
  const result = claimCurrentTask(ready);
  assert.equal(result.changed, true);
  assert.match(result.source, /- Current Task Status: IN_PROGRESS/);
  assert.match(result.source, /- \[~\] M20\.S01\.T003/);
  assert.match(result.source, /- \[ \] M20\.S01\.T004/);
});

test("resumes an already in-progress current task idempotently", () => {
  const result = claimCurrentTask(tracker);
  assert.equal(result.changed, false);
  assert.equal(result.id, "M20.S01.T003");
});

test("completes only the active task with evidence and an exact READY successor", () => {
  const result = completeCurrentTask(tracker, {
    nextTaskId: "M20.S01.T004",
    evidence: "Focused database and UI checks passed; independent review found no blocker.",
  });
  const state = parseTaskState(result.source);
  assert.equal(state.currentTaskStatus, "COMPLETE");
  assert.equal(state.tasks.find((task) => task.id === "M20.S01.T003").marker, "x");
  assert.equal(state.nextTaskId, "M20.S01.T004");
  assert.match(result.source, /Evidence: Focused database and UI checks passed/);
  assert.throws(() => completeCurrentTask(tracker, { nextTaskId: "M20.S01.T003", evidence: "done" }), /exact canonical READY/);
  assert.throws(() => completeCurrentTask(tracker, { nextTaskId: "M20.S01.T004", evidence: "  " }), /non-empty single line/);
});

test("claim advances only to the exact selected READY successor after completion", () => {
  const completed = completeCurrentTask(tracker, {
    nextTaskId: "M20.S01.T004",
    evidence: "Focused checks passed.",
  }).source;
  const result = claimCurrentTask(completed);
  const state = parseTaskState(result.source);
  assert.equal(result.advanced, true);
  assert.equal(state.currentTask.id, "M20.S01.T004");
  assert.equal(state.currentTaskStatus, "IN_PROGRESS");
  assert.equal(state.tasks.find((task) => task.id === "M20.S01.T004").marker, "~");
  assert.equal(state.nextTaskSelectionRequired, true);
});

test("cannot complete the active task without selecting a READY successor", () => {
  assert.throws(() => completeCurrentTask(tracker, { nextTaskId: "M20.S01.T099", evidence: "done" }), /exact canonical READY/);
});

test("refuses to claim a blocked task", () => {
  const blocked = tracker
    .replace("- Current Task Status: IN_PROGRESS", "- Current Task Status: BLOCKED")
    .replace("- [~] M20.S01.T003", "- [!] M20.S01.T003");
  assert.throws(() => claimCurrentTask(blocked), /cannot be claimed/);
});

test("applies a matching Q-ID once and only unblocks its tagged task", () => {
  const blocked = tracker
    .replace("- Current Task: M20.S01.T003 — Identify exact missing state/data invariants", "- Current Task: M20.S01.T004 — Define acceptance dataset")
    .replace("- Current Task Status: IN_PROGRESS", "- Current Task Status: BLOCKED")
    .replace("- Next Task/Action: M20.S01.T003 — Identify exact missing state/data invariants", "- Next Task/Action: M20.S01.T004 — Define acceptance dataset")
    .replace("- [~] M20.S01.T003 — Identify exact missing state/data invariants", "- [x] M20.S01.T003 — Identify exact missing state/data invariants")
    .replace("- [ ] M20.S01.T004 — Define acceptance dataset", "- [!] M20.S01.T004 — Define acceptance dataset");
  const answer = { questionId: "Q-M20-NEXT", taskId: "M20.S01.T004", answer: "Proceed with T004." };
  const first = applyOwnerAnswers(blocked, [answer]);
  assert.deepEqual(first.applied, [{ questionId: answer.questionId, taskId: answer.taskId }]);
  assert.match(first.source, /- \[ \] M20\.S01\.T004 — Define acceptance dataset/);
  assert.match(first.source, /Q-M20-NEXT \| TASK: M20\.S01\.T004 \| ANSWER: Proceed with T004\./);
  assert.equal(parseTaskState(first.source).questions.length, 0);
  const second = applyOwnerAnswers(first.source, [answer]);
  assert.deepEqual(second.applied, []);
  assert.equal(second.source, first.source);
});

test("rejects duplicate authority fields and inconsistent task markers", () => {
  assert.throws(() => parseTaskState(`${tracker}\n- Current Task Status: READY\n`), /exactly once/);
  assert.throws(() => parseTaskState(tracker.replace("- [~] M20.S01.T003", "- [ ] M20.S01.T003")), /does not match/);
});

test("refuses to overwrite TASKS.md when its source changed after processing", async () => {
  const root = await mkdtemp(join(tmpdir(), "fmcg-task-queue-"));
  try {
    await writeFile(join(root, "TASKS.md"), "newer owner edit\n", "utf8");
    await assert.rejects(writeTracker(root, "old tracker\n", "queue rewrite\n"), /changed during queue processing/);
    assert.equal(await readFile(join(root, "TASKS.md"), "utf8"), "newer owner edit\n");
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});

test("refuses a second queue writer while TASKS.md is locked", async () => {
  const root = await mkdtemp(join(tmpdir(), "fmcg-task-queue-"));
  try {
    const original = "current tracker\n";
    await writeFile(join(root, "TASKS.md"), original, "utf8");
    await mkdir(join(root, "TASKS.md.codex-queue.lock"));
    await assert.rejects(writeTracker(root, original, "competing rewrite\n"), /Another task queue update holds/);
    assert.equal(await readFile(join(root, "TASKS.md"), "utf8"), original);
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});

test("rejects duplicate owner question IDs before applying an inbox answer", () => {
  const duplicateQuestions = tracker.replace("## Owner Decisions", "- Q-M20-NEXT | Duplicate ID? | TASK: M20.S01.T004\n\n## Owner Decisions");
  assert.throws(() => applyOwnerAnswers(duplicateQuestions, [{ questionId: "Q-M20-NEXT", taskId: "M20.S01.T004", answer: "Proceed." }]), /must be unique/);
});

test("rejects a matching blank owner answer without consuming the question", () => {
  assert.throws(() => applyOwnerAnswers(tracker, [{ questionId: "Q-M20-NEXT", taskId: "M20.S01.T004", answer: "   " }]), /is blank/);
});

test("rejects owner questions that point to a missing canonical task", () => {
  const unknownTask = tracker.replace("TASK: M20.S01.T004", "TASK: M20.S01.T099");
  assert.throws(() => parseTaskState(unknownTask), /references unknown task M20.S01.T099/);
});

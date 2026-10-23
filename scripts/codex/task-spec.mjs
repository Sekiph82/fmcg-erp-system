const canonicalRoot = String.raw`C:\Users\sekip\Desktop\fmcg-erp-system`;

function promptFor(task) {
  return [
    `TASK: ${task.id} — ${task.title}`,
    "",
    "SPEC: FMCG ERP autonomous implementation handoff",
    `Workspace: ${canonicalRoot}`,
    "",
    "Use this exact task as the only implementation scope. Treat the root TASKS.md row as the authority. On completion, select the next dependency-ready task using canonical acceptance criteria and dependencies, then write its exact ID/title to TASKS.md; do not choose solely by checkbox order or dashboard selection.",
    "Before editing, read this task's linked acceptance material and the latest applicable audit. If those materials do not define a required business decision, record the precise blocker for the owner instead of inventing a value.",
    "At the task boundary, run `node scripts/codex/task-queue.mjs --apply-answers` and apply only exact Q-ID/task-ID matches once. Preserve owner data and existing local changes. Never inspect `.hiveai`, Codex private databases, or AppData. Do not modify FormuLab or create another Desktop checkout.",
    "Use one implementation executor and one independent read-only reviewer. Report only checks and approvals supported by evidence. Respect owner-data, security, authentication, approval, and publication gates; do not fabricate data or approval.",
    "The owner authorizes synchronizing the canonical local checkout with origin/main before each task, including committing and pushing completed task work when required and safe after local checks and independent review. Fetch and inspect differences; preserve owner work. Never reset, clean, force-push, overwrite newer work, or rebase. Do not run GitHub Actions for M20 through 2026-10-30.",
    "When this task is complete or blocked, update its authorized task records, apply matching owner answers at the boundary, choose the next dependency-ready task from TASKS.md, then generate the next handoff from that exact canonical successor. If a business decision blocks progress, report it in plain Turkish and continue independent eligible work.",
  ].join("\n");
}

export function createNextTaskSpec(state) {
  if (!state.currentTask) {
    return { status: "QUEUE_COMPLETE", taskId: null, title: null, prompt: null };
  }
  if (state.currentTaskStatus !== "COMPLETE") {
    return { status: "CURRENT_TASK_NOT_COMPLETE", taskId: null, title: null, prompt: null };
  }
  if (!state.nextTaskId) {
    return { status: "EXPLICIT_TASK_SELECTION_REQUIRED", taskId: null, title: null, prompt: null };
  }

  const task = state.tasks.find((item) => item.id === state.nextTaskId);
  if (!task) throw new Error(`Explicit successor ${state.nextTaskId} is missing from the canonical task rows.`);
  if (task.marker !== " ") {
    return { status: "SUCCESSOR_NOT_READY", taskId: task.id, title: task.title, prompt: null };
  }

  return {
    status: "SPEC_READY",
    taskId: task.id,
    title: task.title,
    prompt: promptFor(task),
  };
}

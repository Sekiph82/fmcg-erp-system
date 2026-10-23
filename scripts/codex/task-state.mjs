import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

const taskRowPattern = /^- \[([ x~!])\] ([A-Z][A-Z0-9]*(?:[.-][A-Z0-9]+)+) — (.+)$/;
const taskReferencePattern = /^([A-Z][A-Z0-9]*(?:[.-][A-Z0-9]+)+) — (.+)$/;

export function readField(source, name) {
  const matches = [...source.matchAll(new RegExp(`^- ${name}:\\s*(.+)$`, "gm"))];
  if (matches.length !== 1) throw new Error(`${name} must appear exactly once in TASKS.md.`);
  return matches[0][1].trim();
}

export function parseTaskState(source) {
  const lines = source.split(/\r?\n/);
  const tasks = lines.flatMap((line, index) => {
    const match = line.match(taskRowPattern);
    return match ? [{ marker: match[1], id: match[2], title: match[3].trim(), lineIndex: index }] : [];
  });
  if (!tasks.length) throw new Error("TASKS.md must contain at least one canonical task row.");
  const currentValue = readField(source, "Current Task");
  const current = currentValue === "None" ? null : currentValue.match(taskReferencePattern);
  if (currentValue !== "None" && !current) throw new Error("Current Task must explicitly identify one task ID and title, or None.");
  const status = readField(source, "Current Task Status");
  const requiredActor = readField(source, "Required Actor");
  const milestone = readField(source, "Current Milestone");
  const sprint = readField(source, "Current Sprint");
  const nextTask = readField(source, "Next Task/Action");
  if (requiredActor !== "CODEX") throw new Error(`Required Actor must be CODEX; found ${requiredActor}.`);
  if (!milestone || !sprint || !nextTask) throw new Error("Current Milestone, Current Sprint, and Next Task/Action must be explicit.");
  const inProgress = tasks.filter((task) => task.marker === "~");
  if (inProgress.length > 1) throw new Error(`Only one task may be in progress; found ${inProgress.map((task) => task.id).join(", ")}.`);
  if (current) {
    const matches = tasks.filter((task) => task.id === current[1] && task.title === current[2]);
    if (matches.length !== 1) throw new Error(`Current Task ${current[1]} must match exactly one canonical task row.`);
    const markerForStatus = { READY: " ", IN_PROGRESS: "~", BLOCKED: "!", COMPLETE: "x" }[status];
    if (!markerForStatus) throw new Error(`Unsupported Current Task Status: ${status}.`);
    if (matches[0].marker !== markerForStatus) throw new Error(`Current Task Status ${status} does not match [${matches[0].marker}] for ${current[1]}.`);
    if (inProgress.length && (status !== "IN_PROGRESS" || !current || inProgress[0].id !== current[1])) {
      throw new Error("Any in-progress task must be the explicit current task with status IN_PROGRESS.");
    }
    if (status === "IN_PROGRESS" && (inProgress.length !== 1 || inProgress[0].id !== current[1])) {
      throw new Error("The explicit current task must be the only in-progress task.");
    }
  } else if (inProgress.length) {
    throw new Error("An in-progress task requires an explicit current task.");
  }
  if (currentValue === "None" && (status !== "COMPLETE" || nextTask !== "None" || tasks.some((task) => task.marker !== "x"))) {
    throw new Error("Current Task may be None only when every canonical task is complete and Next Task/Action is None.");
  }
  const nextReference = nextTask.match(taskReferencePattern);
  if (nextReference && !tasks.some((task) => task.id === nextReference[1] && task.title === nextReference[2])) {
    throw new Error(`Next Task/Action references unknown task ${nextReference[1]}.`);
  }
  const questions = parseQuestions(source, tasks);
  return {
    currentTask: current ? { id: current[1], title: current[2] } : null,
    currentTaskStatus: status,
    requiredActor,
    milestone,
    sprint,
    nextTask,
    nextTaskId: nextReference?.[1] === current?.[1] ? null : nextReference?.[1] ?? null,
    nextTaskTitle: nextReference?.[1] === current?.[1] ? null : nextReference?.[2] ?? null,
    nextTaskSelectionRequired: current ? (!nextReference || nextReference[1] === current[1]) : false,
    tasks,
    questions,
    completedTasks: tasks.filter((task) => task.marker === "x").length,
    totalTasks: tasks.length,
  };
}

export function parseQuestions(source, taskRows) {
  const headings = [...source.matchAll(/^## Questions for Şekip\s*$/gm)];
  if (headings.length > 1) throw new Error("TASKS.md may contain only one Questions for Şekip section.");
  if (!headings.length) return [];
  const start = headings[0].index + headings[0][0].length;
  const after = source.slice(start);
  const end = after.search(/^## /m);
  const section = end < 0 ? after : after.slice(0, end);
  const questions = section.split(/\r?\n/).flatMap((line) => {
    const match = line.match(/^\s*[-*]\s+(Q-[A-Z0-9.-]+)\s*\|\s*(.+?)\s*\|\s*TASK:\s*([A-Z][A-Z0-9]*(?:[.-][A-Z0-9]+)+)\s*$/);
    return match ? [{ id: match[1], question: match[2].slice(0, 1_000), taskId: match[3] }] : [];
  });
  const ids = new Set();
  const canonicalTasks = new Set((taskRows ?? source.split(/\r?\n/).flatMap((line) => {
    const task = line.match(taskRowPattern);
    return task ? [{ id: task[2] }] : [];
  })).map((task) => task.id));
  for (const question of questions) {
    if (ids.has(question.id)) throw new Error(`Question ID ${question.id} must be unique.`);
    ids.add(question.id);
    if (!canonicalTasks.has(question.taskId)) throw new Error(`Question ${question.id} references unknown task ${question.taskId}.`);
  }
  return questions;
}

export async function readProjectTaskState(root) {
  const trackerPath = resolve(root, "TASKS.md");
  const source = await readFile(trackerPath, "utf8");
  return { source, state: parseTaskState(source), trackerPath };
}

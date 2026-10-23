import { existsSync } from "node:fs";
import { lstat, mkdir, readFile, rename, rmdir, unlink, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { parseQuestions, parseTaskState, readProjectTaskState } from "./task-state.mjs";
import { createNextTaskSpec } from "./task-spec.mjs";

export function claimCurrentTask(source) {
  const state = parseTaskState(source);
  if (!state.currentTask) return { source, changed: false, complete: true, id: null, title: null };
  if (state.currentTaskStatus === "IN_PROGRESS") return { source, changed: false, ...state.currentTask };
  if (state.currentTaskStatus !== "READY") throw new Error(`The explicit current task is ${state.currentTaskStatus}; it cannot be claimed.`);
  const row = state.tasks.find((task) => task.id === state.currentTask.id && task.title === state.currentTask.title);
  const lines = source.split(/\r?\n/);
  lines[row.lineIndex] = lines[row.lineIndex].replace("- [ ]", "- [~]");
  const updated = lines.join("\n").replace(/^- Current Task Status: READY$/m, "- Current Task Status: IN_PROGRESS");
  if (updated === source) throw new Error(`Could not claim explicit current task ${row.id}.`);
  return { source: updated, changed: true, id: row.id, title: row.title };
}

export function applyOwnerAnswers(source, answers) {
  let updated = source;
  const applied = [];
  for (const answer of answers) {
    if (!answer || typeof answer.questionId !== "string" || typeof answer.answer !== "string") continue;
    if (!answer.answer.trim()) throw new Error(`Owner answer ${answer.questionId} is blank; refusing to consume it.`);
    const question = parseQuestions(updated).find((item) => item.id === answer.questionId);
    if (!question || answer.taskId !== question.taskId) continue;
    const duplicate = new RegExp(`^\\s*[-*]\\s+${escapeRegExp(question.id)}\\s*\\|`, "m").test(ownerDecisionSection(updated));
    if (duplicate) continue;
    updated = appendOwnerDecision(updated, question, answer.answer);
    updated = removeOpenQuestion(updated, question.id);
    const state = parseTaskState(updated);
    const task = state.tasks.find((item) => item.id === question.taskId);
    if (task?.marker === "!") {
      const lines = updated.split(/\r?\n/);
      lines[task.lineIndex] = lines[task.lineIndex].replace("- [!]", "- [ ]");
      updated = lines.join("\n");
      if (state.currentTask?.id === task.id && state.currentTaskStatus === "BLOCKED") {
        updated = updated.replace(/^- Current Task Status: BLOCKED$/m, "- Current Task Status: READY");
      }
    }
    applied.push({ questionId: question.id, taskId: question.taskId });
  }
  return { source: updated, applied };
}

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function ownerDecisionSection(source) {
  const marker = /^## Owner Decisions\s*$/m;
  const match = marker.exec(source);
  if (!match) return "";
  const rest = source.slice(match.index + match[0].length);
  const end = rest.search(/^## /m);
  return end < 0 ? rest : rest.slice(0, end);
}

function appendOwnerDecision(source, question, rawAnswer) {
  const answer = rawAnswer.replace(/[\r\n]+/g, " ").trim().slice(0, 4_000);
  if (!answer) return source;
  const line = `- ${question.id} | TASK: ${question.taskId} | ANSWER: ${answer}`;
  if (/^## Owner Decisions\s*$/m.test(source)) {
    const heading = /^## Owner Decisions\s*$/m.exec(source);
    const insertAt = heading.index + heading[0].length;
    return `${source.slice(0, insertAt)}\n${line}${source.slice(insertAt)}`;
  }
  return `${source.trimEnd()}\n\n## Owner Decisions\n\n${line}\n`;
}

function removeOpenQuestion(source, questionId) {
  const heading = /^## Questions for Şekip\s*$/m.exec(source);
  if (!heading) return source;
  const afterHeading = heading.index + heading[0].length;
  const rest = source.slice(afterHeading);
  const nextHeading = rest.search(/^## /m);
  const sectionEnd = nextHeading < 0 ? source.length : afterHeading + nextHeading;
  const section = source.slice(afterHeading, sectionEnd);
  const escaped = escapeRegExp(questionId);
  const nextSection = section.replace(new RegExp(`^\\s*[-*]\\s+${escaped}\\s*\\|[^\\n]*(?:\\n|$)`, "m"), "");
  return `${source.slice(0, afterHeading)}${nextSection}${source.slice(sectionEnd)}`;
}

async function readAnswerInbox(root) {
  const path = resolve(root, "project-control/codex/owner-answers.jsonl");
  try {
    const info = await lstat(path);
    if (info.isSymbolicLink() || !info.isFile()) throw new Error("Owner answer inbox must be a regular file.");
    return (await readFile(path, "utf8")).split(/\r?\n/).flatMap((line, index) => {
      if (!line) return [];
      if (line.length > 8_500) throw new Error(`Owner answer inbox line ${index + 1} exceeds the size limit.`);
      let answer;
      try { answer = JSON.parse(line); } catch { throw new Error(`Owner answer inbox line ${index + 1} is malformed JSON.`); }
      if (!answer || typeof answer.questionId !== "string" || typeof answer.taskId !== "string" || typeof answer.answer !== "string" || !answer.answer.trim()) {
        throw new Error(`Owner answer inbox line ${index + 1} is incomplete or blank.`);
      }
      return [answer];
    });
  } catch (error) {
    if (error?.code === "ENOENT") return [];
    throw error;
  }
}

export async function writeTracker(root, expectedSource, source) {
  const path = resolve(root, "TASKS.md");
  const temporaryPath = resolve(root, "TASKS.md.codex-queue.tmp");
  const lockPath = resolve(root, "TASKS.md.codex-queue.lock");
  let locked = false;
  try {
    await mkdir(lockPath);
    locked = true;
  } catch (error) {
    if (error?.code === "EEXIST") throw new Error("Another task queue update holds the TASKS.md lock; retry later.");
    throw error;
  }
  try {
    if (existsSync(temporaryPath)) throw new Error("TASKS.md.codex-queue.tmp already exists; refusing to overwrite it.");
    const info = await lstat(path);
    if (info.isSymbolicLink() || !info.isFile()) throw new Error("TASKS.md must be a regular file.");
    if (await readFile(path, "utf8") !== expectedSource) throw new Error("TASKS.md changed during queue processing; refusing to overwrite the newer tracker.");
    await writeFile(temporaryPath, source, { encoding: "utf8", flag: "wx" });
    try {
      if (await readFile(path, "utf8") !== expectedSource) throw new Error("TASKS.md changed before queue commit; refusing to overwrite the newer tracker.");
      await rename(temporaryPath, path);
    } catch (error) {
      await unlink(temporaryPath).catch(() => {});
      throw error;
    }
  } finally {
    if (locked) await rmdir(lockPath).catch(() => {});
  }
}

async function run() {
  const root = resolve(fileURLToPath(new URL("../..", import.meta.url)));
  const args = new Set(process.argv.slice(2));
  if (!["--check", "--claim", "--apply-answers", "--spec"].some((arg) => args.has(arg))) {
    throw new Error("Use --check, --claim, --apply-answers, or --spec.");
  }
  const { source, state } = await readProjectTaskState(root);
  if (args.has("--apply-answers")) {
    const result = applyOwnerAnswers(source, await readAnswerInbox(root));
    if (result.applied.length) {
      parseTaskState(result.source);
      await writeTracker(root, source, result.source);
      for (const item of result.applied) console.log(`Applied owner answer ${item.questionId} to ${item.taskId}.`);
    } else console.log("No unanswered matching owner decisions in the inbox.");
    return;
  }
  if (args.has("--claim")) {
    const result = claimCurrentTask(source);
    if (result.changed) {
      parseTaskState(result.source);
      await writeTracker(root, source, result.source);
      console.log(`Claimed explicit task ${result.id}: ${result.title}`);
    } else if (result.complete) console.log("Autonomous queue complete: no current task remains.");
    else console.log(`Resuming explicit task ${result.id}: ${result.title}`);
    return;
  }
  const nextTaskSpec = createNextTaskSpec(state);
  if (args.has("--spec")) {
    console.log(JSON.stringify(nextTaskSpec, null, 2));
    return;
  }
  console.log(JSON.stringify({
    currentTask: state.currentTask,
    currentTaskStatus: state.currentTaskStatus,
    requiredActor: state.requiredActor,
    milestone: state.milestone,
    sprint: state.sprint,
    nextTask: state.nextTask,
    explicitNextTaskId: state.nextTaskId,
    nextTaskSelectionRequired: state.nextTaskSelectionRequired,
    nextTaskSpec,
    openQuestions: state.questions.length,
    completedTasks: state.completedTasks,
    totalTasks: state.totalTasks,
  }, null, 2));
}

const invokedPath = process.argv[1] ? resolve(process.argv[1]) : "";
if (invokedPath === fileURLToPath(import.meta.url)) {
  try { await run(); }
  catch (error) { console.error(`Autonomous queue stopped: ${error.message}`); process.exitCode = 1; }
}

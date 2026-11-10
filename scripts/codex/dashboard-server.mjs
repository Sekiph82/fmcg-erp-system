import { createReadStream } from "node:fs";
import { appendFile, lstat, mkdir, readFile, readdir, realpath } from "node:fs/promises";
import { createServer } from "node:http";
import { dirname, isAbsolute, join, relative, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";
import { CodexAppServerClient } from "./app-server-client.mjs";

const scriptDirectory = dirname(fileURLToPath(import.meta.url));
const defaultRoot = resolve(scriptDirectory, "../..");
const cacheDurationMs = 1_000;
const workflowStages = ["SPEC", "BUILD", "REVIEW", "APPROVE", "MERGED", "ESCALATED"];
const reviewLenses = ["rules", "code", "tests"];
let answerWriteChain = Promise.resolve();
const projectCatalog = [
  { id: "packlab", name: "PackLab", kind: "Codex", names: ["PackLab"], pathSegments: ["PackLab"], localRoot: "C:\\Users\\sekip\\Desktop\\PackLab" },
  { id: "formulab", name: "Formulab", kind: "Codex", names: ["Formulab", "FormuLab"], pathSegments: ["FormuLab"], localRoot: "C:\\Users\\sekip\\Desktop\\FormuLab" },
  { id: "fmcg-erp-system", name: "FMCG ERP", kind: "Codex", names: ["fmcg-erp-system", "fmcg-erp-system-main"], pathSegments: ["fmcg-erp-system", "fmcg-erp-system-main"], localRoot: "C:\\Users\\sekip\\Desktop\\fmcg-erp-system" },
  { id: "match3-visual-ui-factory", name: "MATCH3-Visual-UI-Factory", kind: "Codex", names: ["MATCH3-Visual-UI-Factory"], pathSegments: ["MATCH3-Visual-UI-Factory"], localRoot: "C:\\Users\\sekip\\Desktop\\GAMES\\MATCH3 GAMES\\MATCH3-Visual-UI-Factory" },
  { id: "match3-level-factory", name: "Match3-Level-Factory", kind: "Codex", names: ["Match3-Level-Factory"], pathSegments: ["Match3-Level-Factory"], localRoot: "C:\\Users\\sekip\\Desktop\\GAMES\\MATCH3 GAMES\\Match3-Level-Factory" },
  { id: "scrubbots-level-factory", name: "ScrubBots Level Factory", kind: "Codex", names: ["ScrubBots Level Factory"], pathSegments: ["Scrubbots - Pixel Art Generator"], localRoot: "C:\\Users\\sekip\\Desktop\\Scrubbots - Pixel Art Generator" },
  { id: "match3-engine", name: "MATCH3_ENGINE", kind: "Codex", names: ["MATCH3_ENGINE"], pathSegments: ["MATCH3_ENGINE"], localRoot: "C:\\Users\\sekip\\Desktop\\GAMES\\MATCH3 GAMES\\MATCH3_ENGINE" },
  { id: "wonder-pop", name: "Wonder_Pop", kind: "GitHub", repositoryUrl: "https://github.com/Sekiph82/Wonder_Pop", names: ["Wonder_Pop"], pathSegments: ["Wonder_Pop"], localRoot: "C:\\Users\\sekip\\Desktop\\GAMES\\MATCH3 GAMES\\Wonder_Pop" },
  { id: "the-fractured-realms", name: "The_Fractured_Realms", kind: "GitHub", repositoryUrl: "https://github.com/Sekiph82/The_Fractured_Realms", names: ["The_Fractured_Realms"], pathSegments: ["The_Fractured_Realms"], localRoot: "C:\\Users\\sekip\\Desktop\\GAMES\\MATCH3 GAMES\\The_Fractured_Realms" },
  { id: "dino-islands", name: "Dino_Islands", kind: "GitHub", repositoryUrl: "https://github.com/Sekiph82/Dino_Islands", names: ["Dino_Islands"], pathSegments: ["Dino_Islands"], localRoot: "C:\\Users\\sekip\\Desktop\\GAMES\\MATCH3 GAMES\\Dino_Islands" },
  { id: "garage-legends", name: "Garage_Legends", kind: "GitHub", repositoryUrl: "https://github.com/Sekiph82/Garage_Legends", names: ["Garage_Legends"], pathSegments: ["Garage_Legends"], localRoot: "C:\\Users\\sekip\\Desktop\\GAMES\\MATCH3 GAMES\\Garage_Legends" },
  { id: "coral-rescue", name: "Coral_Rescue", kind: "GitHub", repositoryUrl: "https://github.com/Sekiph82/Coral_Rescue", names: ["Coral_Rescue"], pathSegments: ["Coral_Rescue"], localRoot: "C:\\Users\\sekip\\Desktop\\GAMES\\MATCH3 GAMES\\Coral_Rescue" },
];

function trackerSummary(source) {
  const get = (name) => source.match(new RegExp(`^- ${name}:\\s*(.+)$`, "m"))?.[1]?.trim() ?? null;
  const task = get("Current Task")?.match(/^([A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*-\d+(?:\.\d+)?|[A-Z][A-Z0-9]*(?:[.-][A-Z0-9]+)+) — (.+)$/);
  const tasks = [...source.matchAll(/^- \[([^\]])\] ([A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*-\d+(?:\.\d+)?|[A-Z][A-Z0-9]*(?:[.-][A-Z0-9]+)+) — (.+)$/gm)];
  const completed = tasks.filter((match) => match[1] === "x").length;
  return {
    milestone: get("Current Milestone"),
    sprint: get("Current Sprint"),
    currentTask: task ? { id: task[1], title: task[2] } : null,
    currentTaskStatus: get("Current Task Status"),
    nextTask: get("Next Task") ?? get("Next Task/Action"),
    requiredActor: get("Required Actor"),
    completion: tasks.length ? `${Math.round((completed / tasks.length) * 1000) / 10}%` : "—",
    completedTasks: completed,
    totalTasks: tasks.length,
  };
}

function trackerQuestions(source) {
  const questionSection = source.split(/^## /m).find((candidate) => /^(?:Questions(?: for .+)?|Owner Questions)$/i.test(candidate.split(/\r?\n/, 1)[0]?.trim() ?? ""));
  const section = questionSection?.slice(questionSection.indexOf("\n") + 1) ?? "";
  const canonicalTasks = new Set([...source.matchAll(/^- \[[^\]]\] ([A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*-\d+(?:\.\d+)?|[A-Z][A-Z0-9]*(?:[.-][A-Z0-9]+)+) — /gm)].map((match) => match[1]));
  return section.split(/\r?\n/).flatMap((line) => {
    const match = line.match(/^\s*[-*]\s+(Q-[A-Z0-9.-]+)\s*\|\s*(.+?)\s*\|\s*TASK:\s*([A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*-\d+(?:\.\d+)?|[A-Z][A-Z0-9]*(?:[.-][A-Z0-9]+)+)\s*$/);
    return match && canonicalTasks.has(match[3]) ? [{ id: match[1], question: match[2].slice(0, 1_000), taskId: match[3] }] : [];
  });
}

async function ownerInboxPath(root, create = false) {
  const canonicalRoot = await realpath(root);
  let current = canonicalRoot;
  for (const segment of ["project-control", "codex"]) {
    current = resolve(current, segment);
    try {
      await lstat(current);
    } catch (error) {
      if (!create || error?.code !== "ENOENT") throw error;
      await mkdir(current);
    }
    const info = await lstat(current);
    const canonical = await realpath(current);
    if (info.isSymbolicLink() || !info.isDirectory() || !isWithinDirectory(canonicalRoot, canonical)) {
      throw new Error("Owner answer inbox directories must be regular directories inside the project root.");
    }
    current = canonical;
  }
  return resolve(current, "owner-answers.jsonl");
}

async function readOwnerAnswers(root) {
  let path;
  try {
    path = await ownerInboxPath(root);
  } catch (error) {
    if (["ENOENT", "ENOTDIR", "ELOOP"].includes(error?.code)) return [];
    throw error;
  }
  try {
    const info = await lstat(path);
    if (info.isSymbolicLink() || !info.isFile()) return [];
    const source = await readFile(path, "utf8");
    return source.split(/\r?\n/).flatMap((line) => {
      if (!line || line.length > 8_500) return [];
      try {
        const answer = JSON.parse(line);
        return typeof answer?.questionId === "string" && typeof answer?.taskId === "string" && typeof answer?.answer === "string" && typeof answer?.submittedAt === "string"
          ? [{ questionId: answer.questionId, taskId: answer.taskId, answer: answer.answer.slice(0, 4_000), submittedAt: answer.submittedAt }]
          : [];
      } catch {
        return [];
      }
    });
  } catch (error) {
    if (error?.code === "ENOENT") return [];
    throw error;
  }
}

function saveOwnerAnswer(root, questionId, answer, source, taskId) {
  const result = answerWriteChain.then(() => saveOwnerAnswerExclusive(root, questionId, answer, source, taskId));
  answerWriteChain = result.catch(() => {});
  return result;
}

async function saveOwnerAnswerExclusive(root, questionId, answer, source, taskId) {
  const questions = trackerQuestions(source);
  const question = questions.find((item) => item.id === questionId);
  if (!question) return { status: 404, error: "That question is no longer open." };
  if (question.taskId !== taskId) return { status: 409, error: "The task ID does not match this question." };
  if ((await readOwnerAnswers(root)).some((entry) => entry.questionId === questionId)) {
    return { status: 409, error: "An answer has already been submitted for this question." };
  }
  const entry = { questionId, taskId, answer, submittedAt: new Date().toISOString() };
  const path = await ownerInboxPath(root, true);
  try {
    const info = await lstat(path);
    if (info.isSymbolicLink() || !info.isFile()) return { status: 400, error: "The answer inbox is not a regular file." };
  } catch (error) {
    if (error?.code !== "ENOENT") throw error;
  }
  await appendFile(path, `${JSON.stringify(entry)}\n`, { encoding: "utf8", flag: "a" });
  return { status: 201, entry };
}

async function readJsonBody(request, maximumBytes = 8_192) {
  const chunks = [];
  let size = 0;
  for await (const chunk of request) {
    size += chunk.length;
    if (size > maximumBytes) throw Object.assign(new Error("Request body is too large."), { status: 413 });
    chunks.push(chunk);
  }
  try {
    return JSON.parse(Buffer.concat(chunks).toString("utf8"));
  } catch {
    throw Object.assign(new Error("Request body must be valid JSON."), { status: 400 });
  }
}

function isWithinDirectory(parent, candidate) {
  const pathFromParent = relative(parent, candidate);
  return pathFromParent === "" || (!pathFromParent.startsWith(`..${sep}`) && pathFromParent !== ".." && !isAbsolute(pathFromParent));
}

export async function readWorkflowJobs(root) {
  const jobsDirectory = resolve(root, "project-control/codex/jobs");
  let entries;
  try {
    entries = await readdir(jobsDirectory, { withFileTypes: true });
  } catch (error) {
    if (error?.code === "ENOENT") return [];
    throw error;
  }
  const canonicalRoot = await realpath(root);
  const canonicalJobsDirectory = await realpath(jobsDirectory);
  if (!isWithinDirectory(canonicalRoot, canonicalJobsDirectory)) return [];
  const jobs = [];
  for (const entry of entries) {
    if (!entry.isDirectory()) continue;
    try {
      const jobDirectory = join(canonicalJobsDirectory, entry.name);
      const canonicalJobDirectory = await realpath(jobDirectory);
      if (!isWithinDirectory(canonicalJobsDirectory, canonicalJobDirectory)) continue;
      const jobPath = join(jobDirectory, "job.json");
      const canonicalJobPath = await realpath(jobPath);
      if (!isWithinDirectory(canonicalJobDirectory, canonicalJobPath)) continue;
      const fileInfo = await lstat(jobPath);
      if (fileInfo.isSymbolicLink() || !fileInfo.isFile()) continue;
      const value = JSON.parse(await readFile(canonicalJobPath, "utf8"));
      if (!value || typeof value !== "object" || Array.isArray(value) ||
           !/^[A-Z][A-Z0-9]*(?:[.-][A-Z0-9]+)+$/.test(value.id ?? "") ||
           typeof value.task !== "string" || !value.task.trim() ||
          !workflowStages.includes(value.stage) ||
          !Number.isInteger(value.round) || value.round < 1 ||
           !value.reviews || typeof value.reviews !== "object" || Array.isArray(value.reviews)) continue;
      if (["APPROVE", "MERGED"].includes(value.stage) && reviewLenses.some((lens) => value.reviews[lens] !== "pass")) continue;
      if (value.stage === "MERGED" && (value.accepted !== true || !/^[0-9a-f]{40}$/i.test(value.publishedCommit ?? ""))) continue;
      if (value.stage === "ESCALATED" && value.blockedTaskId !== value.id) continue;
      const reviews = Object.fromEntries(reviewLenses.map((lens) => [
        lens,
        ["pending", "pass", "changes"].includes(value.reviews[lens]) ? value.reviews[lens] : "pending",
      ]));
      jobs.push({
        id: value.id,
        task: value.task.slice(0, 240),
        stage: value.stage,
        round: value.round,
        reviews,
        accepted: value.accepted === true,
        publishedCommit: typeof value.publishedCommit === "string" ? value.publishedCommit : null,
        updatedAt: typeof value.updatedAt === "string" ? value.updatedAt : null,
      });
    } catch (error) {
      if (error?.code !== "ENOENT" && error?.code !== "ELOOP" && !(error instanceof SyntaxError)) throw error;
    }
  }
  return jobs.sort((left, right) => (right.updatedAt ?? "").localeCompare(left.updatedAt ?? ""));
}

function normalizePath(value) {
  return typeof value === "string" ? value.replaceAll("\\", "/").replace(/\/$/, "").toLowerCase() : "";
}

function pathHasSegment(path, segments) {
  const pathSegments = normalizePath(path).split("/");
  return segments.some((segment) => pathSegments.includes(segment.toLowerCase()));
}

function getRoots(project) {
  const roots = Array.isArray(project?.roots) ? project.roots : [];
  return roots.map((root) => typeof root === "string" ? root : root?.path).filter((root) => typeof root === "string");
}

function threadStatus(thread) {
  const status = thread?.status;
  if (typeof status === "string") return status;
  if (status && typeof status.type === "string") return status.type;
  return thread?.archived ? "archived" : "idle";
}

function threadUpdatedAt(thread) {
  const value = thread?.updatedAt ?? thread?.updated_at ?? thread?.recencyAt ?? thread?.recency_at ?? null;
  if (typeof value === "number") return new Date(value < 10_000_000_000 ? value * 1000 : value).toISOString();
  return typeof value === "string" ? value : null;
}

function sanitizeThread(thread) {
  const title = typeof thread?.title === "string" && thread.title.trim()
    ? thread.title
    : typeof thread?.preview === "string" && thread.preview.trim()
      ? thread.preview
      : "Untitled Codex task";
  return {
    id: typeof thread?.id === "string" ? thread.id : "",
    title: title.slice(0, 180),
    cwd: typeof thread?.cwd === "string" ? thread.cwd : "",
    status: threadStatus(thread),
    updatedAt: threadUpdatedAt(thread),
    source: typeof thread?.sourceKind === "string" ? thread.sourceKind : "Codex",
    projectId: typeof thread?.projectId === "string" ? thread.projectId : null,
  };
}

function projectMatches(project, definition) {
  const projectName = String(project?.name ?? "").trim().toLowerCase();
  if (projectName) {
    const knownName = projectCatalog.some((item) => item.names.some((name) => name.toLowerCase() === projectName));
    if (knownName) return definition.names.some((name) => name.toLowerCase() === projectName);
  }
  const roots = getRoots(project);
  return roots.some((root) => pathHasSegment(root, definition.pathSegments)) ||
    (definition.localRoot && roots.some((root) => normalizePath(root) === normalizePath(definition.localRoot)));
}

function groupThreads(projects, threads) {
  const safeThreads = threads.map(sanitizeThread);
  const matchedProjectIds = new Set();
  const grouped = projectCatalog.map((definition) => {
    const source = projects.find((project) => projectMatches(project, definition));
    const sourceId = typeof source?.id === "string" ? source.id : null;
    if (sourceId) matchedProjectIds.add(sourceId);
    const roots = getRoots(source);
    const localRoot = definition.localRoot ?? null;
    const matchingThreads = safeThreads.filter((thread) =>
      (sourceId && thread.projectId === sourceId) ||
      roots.some((root) => normalizePath(root) === normalizePath(thread.cwd)) ||
      (localRoot && normalizePath(localRoot) === normalizePath(thread.cwd)) ||
      pathHasSegment(thread.cwd, definition.pathSegments)
    ).map((thread) => ({
      ...thread,
      workspaceMismatch: Boolean(definition.canonicalRoot && normalizePath(thread.cwd) !== normalizePath(definition.canonicalRoot)),
    }));
    const threadRoots = matchingThreads.map((thread) => thread.cwd).filter(Boolean);
    return {
      id: definition.id,
      name: definition.name,
      kind: definition.kind,
      repositoryUrl: definition.repositoryUrl ?? null,
      roots: localRoot ? [localRoot] : roots.length ? roots : [...new Set(threadRoots)],
      updatedAt: threadUpdatedAt({ updatedAt: source?.updatedAt ?? source?.updated_at ?? source?.recencyAt }),
      threads: matchingThreads,
    };
  });
  for (const source of projects) {
    if (typeof source?.id !== "string" || matchedProjectIds.has(source.id)) continue;
    const roots = getRoots(source);
    const matchingThreads = safeThreads.filter((thread) =>
      thread.projectId === source.id || roots.some((root) => normalizePath(root) === normalizePath(thread.cwd))
    );
    grouped.push({
      id: source.id,
      name: typeof source.name === "string" && source.name.trim() ? source.name.trim() : "Unnamed project",
      kind: typeof source.kind === "string" ? source.kind : "Codex",
      repositoryUrl: typeof source.repositoryUrl === "string" ? source.repositoryUrl : null,
      roots: roots.length ? roots : [...new Set(matchingThreads.map((thread) => thread.cwd).filter(Boolean))],
      updatedAt: threadUpdatedAt({ updatedAt: source.updatedAt ?? source.updated_at ?? source.recencyAt }),
      threads: matchingThreads,
    });
  }
  return grouped;
}

async function readProjectWorkflow(root) {
  if (!isAbsolute(root)) return null;
  let canonicalRoot;
  try {
    const rootInfo = await lstat(root);
    if (rootInfo.isSymbolicLink() || !rootInfo.isDirectory()) return null;
    canonicalRoot = await realpath(root);
  } catch (error) {
    if (["ENOENT", "ENOTDIR", "ELOOP"].includes(error?.code)) return null;
    throw error;
  }

  const trackerPath = resolve(canonicalRoot, "TASKS.md");
  let trackerSource;
  try {
    const trackerInfo = await lstat(trackerPath);
    if (trackerInfo.isSymbolicLink() || !trackerInfo.isFile()) return { root: canonicalRoot, task: null, questions: [], jobs: [], workflowState: "tracker-unavailable" };
    const canonicalTrackerPath = await realpath(trackerPath);
    if (!isWithinDirectory(canonicalRoot, canonicalTrackerPath)) return { root: canonicalRoot, task: null, questions: [], jobs: [], workflowState: "tracker-unavailable" };
    trackerSource = await readFile(canonicalTrackerPath, "utf8");
  } catch (error) {
    if (["ENOENT", "ENOTDIR", "ELOOP"].includes(error?.code)) return { root: canonicalRoot, task: null, questions: [], jobs: [], workflowState: "tracker-unavailable" };
    throw error;
  }

  const answers = await readOwnerAnswers(canonicalRoot);
  const questions = trackerQuestions(trackerSource).map((question) => ({
    ...question,
    answer: answers.filter((answer) => answer.questionId === question.id && answer.taskId === question.taskId).at(-1) ?? null,
  }));
  return {
    root: canonicalRoot,
    task: trackerSummary(trackerSource),
    questions,
    jobs: await readWorkflowJobs(canonicalRoot),
    workflowState: "available",
    trackerSource,
  };
}

function statusCodeFor(error) {
  if (error?.code === -32601 || /method not found|unknown method/i.test(error?.message ?? "")) return 501;
  return 503;
}

function safeMessage(error) {
  if (error?.code === -32601 || /method not found|unknown method/i.test(error?.message ?? "")) {
    return "This Codex App Server does not support the required read-only listing method.";
  }
  if (/timed out/i.test(error?.message ?? "")) return "Codex App Server did not respond in time.";
  return "Codex App Server data is temporarily unavailable.";
}

export function createDashboardServer({
  root = defaultRoot,
  host = "127.0.0.1",
  port = 9000,
  clientFactory = () => new CodexAppServerClient(),
} = {}) {
  let client;
  let initialized = false;
  let cache;
  let loading;
  let workflowRoots = new Map();

  async function snapshot() {
    if (cache && Date.now() - cache.loadedAt < cacheDurationMs) return cache.value;
    if (loading) return loading;
    loading = (async () => {
      try {
        client ??= clientFactory();
        if (!initialized) {
          await client.initialize();
          initialized = true;
        }

        let projectListing;
        let projectListState = "available";
        try {
          projectListing = await client.listProjects();
        } catch (error) {
          if (statusCodeFor(error) !== 501) throw error;
          projectListState = "unsupported";
          projectListing = { rows: [], truncated: false };
        }

        const threadListing = await client.listThreads();
        const groupedProjects = groupThreads(projectListing.rows, threadListing.rows);
        const nextWorkflowRoots = new Map();
        const projects = await Promise.all(groupedProjects.map(async (project) => {
          let workflow = null;
          const candidates = project.id === "fmcg-erp-system" ? [root] : project.roots;
          for (const candidate of candidates) {
            try {
              workflow = await readProjectWorkflow(candidate);
            } catch {
              workflow = null;
            }
            if (workflow) break;
          }
          if (workflow?.root) nextWorkflowRoots.set(project.id, workflow.root);
          const { root: _root, trackerSource: _trackerSource, ...publicWorkflow } = workflow ?? {
            task: null,
            questions: [],
            jobs: [],
            workflowState: project.roots.length ? "tracker-unavailable" : "no-local-root",
          };
          return { ...project, ...publicWorkflow };
        }));
        workflowRoots = nextWorkflowRoots;
        const value = {
          generatedAt: new Date().toISOString(),
          source: "Codex App Server and each project's local TASKS.md",
          projectListState,
          projects,
          projectCount: projects.length,
          activeThreadCount: projects.reduce((count, project) => count + project.threads.length, 0),
          truncated: Boolean(projectListing.truncated || threadListing.truncated),
        };
        cache = { loadedAt: Date.now(), value };
        return value;
      } finally {
        loading = null;
      }
    })();
    return loading;
  }

  const server = createServer(async (request, response) => {
    response.setHeader("X-Content-Type-Options", "nosniff");
    response.setHeader("Referrer-Policy", "no-referrer");
    response.setHeader("X-Frame-Options", "DENY");
    response.setHeader("Cache-Control", "no-store");
    response.setHeader("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; base-uri 'none'; frame-ancestors 'none'");

    const hostHeader = request.headers.host;
    const boundPort = server.address()?.port ?? port;
    if (hostHeader && hostHeader !== `${host}:${boundPort}` && hostHeader !== `localhost:${boundPort}`) {
      response.writeHead(403).end("Forbidden");
      return;
    }
    const pathname = new URL(request.url ?? "/", `http://${host}:${port}`).pathname;
    if (request.method === "POST" && pathname === "/api/owner-answers") {
      const allowedOrigin = `http://${hostHeader}`;
      if (request.headers.origin && request.headers.origin !== allowedOrigin) {
        response.writeHead(403).end("Forbidden");
        return;
      }
      if (!String(request.headers["content-type"] ?? "").toLowerCase().startsWith("application/json")) {
        response.writeHead(415).end("Content-Type must be application/json.");
        return;
      }
      try {
        const payload = await readJsonBody(request);
        const projectId = typeof payload?.projectId === "string" ? payload.projectId.trim() : "";
        const questionId = typeof payload?.questionId === "string" ? payload.questionId.trim() : "";
        const taskId = typeof payload?.taskId === "string" ? payload.taskId.trim() : "";
        const answer = typeof payload?.answer === "string" ? payload.answer.trim() : "";
        if (!/^[a-z0-9-]+$/.test(projectId) || !/^Q-[A-Z0-9.-]+$/.test(questionId) || !/^[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*-\d+(?:\.\d+)?$|^[A-Z][A-Z0-9]*(?:[.-][A-Z0-9]+)+$/.test(taskId) || !answer || answer.length > 4_000) {
          response.writeHead(400, { "Content-Type": "application/json; charset=utf-8" }).end(JSON.stringify({ error: "Provide a local project, matching open question and task IDs, and an answer of 1 to 4000 characters." }));
          return;
        }
        const project = (await snapshot()).projects.find((entry) => entry.id === projectId);
        const projectRoot = workflowRoots.get(projectId);
        if (!project || !projectRoot) {
          response.writeHead(404, { "Content-Type": "application/json; charset=utf-8" }).end(JSON.stringify({ error: "That project has no validated local task root." }));
          return;
        }
        const workflow = await readProjectWorkflow(projectRoot);
        if (!workflow?.trackerSource) {
          response.writeHead(404, { "Content-Type": "application/json; charset=utf-8" }).end(JSON.stringify({ error: "That project task file is unavailable." }));
          return;
        }
        const result = await saveOwnerAnswer(projectRoot, questionId, answer, workflow.trackerSource, taskId);
        if (result.status !== 201) {
          response.writeHead(result.status, { "Content-Type": "application/json; charset=utf-8" }).end(JSON.stringify({ error: result.error }));
          return;
        }
        cache = undefined;
        response.writeHead(201, { "Content-Type": "application/json; charset=utf-8" }).end(JSON.stringify({ submittedAt: result.entry.submittedAt }));
      } catch (error) {
        response.writeHead(error?.status ?? 500, { "Content-Type": "application/json; charset=utf-8" }).end(JSON.stringify({ error: error?.status ? error.message : "The answer could not be saved." }));
      }
      return;
    }
    if (request.method !== "GET") {
      response.writeHead(405, { Allow: "GET, POST" }).end("Method not allowed");
      return;
    }
    if (pathname === "/health") {
      response.writeHead(200, { "Content-Type": "application/json; charset=utf-8" }).end(JSON.stringify({ ok: true }));
      return;
    }
    if (pathname === "/api/overview") {
      try {
        const value = await snapshot();
        response.writeHead(200, { "Content-Type": "application/json; charset=utf-8" }).end(JSON.stringify(value));
      } catch (error) {
        response.writeHead(statusCodeFor(error), { "Content-Type": "application/json; charset=utf-8" }).end(JSON.stringify({
          error: safeMessage(error),
          detail: error?.code === -32601 ? "unsupported" : "unavailable",
          generatedAt: new Date().toISOString(),
        }));
        const failedClient = client;
        client = undefined;
        initialized = false;
        try {
          await failedClient?.close();
        } catch {
          // A failed connection must not prevent the next refresh from reconnecting.
        }
      }
      return;
    }
    const assets = {
      "/": ["index.html", "text/html; charset=utf-8"],
      "/dashboard.js": ["dashboard.js", "text/javascript; charset=utf-8"],
      "/dashboard.css": ["dashboard.css", "text/css; charset=utf-8"],
    };
    const asset = assets[pathname];
    if (!asset) {
      response.writeHead(404).end("Not found");
      return;
    }
    response.writeHead(200, { "Content-Type": asset[1] });
    createReadStream(resolve(scriptDirectory, "dashboard", asset[0])).pipe(response);
  });

  return {
    server,
    async listen() {
      await new Promise((resolveListen, reject) => {
        server.once("error", reject);
        server.listen(port, host, resolveListen);
      });
    },
    async close() {
      await new Promise((resolveClose) => server.close(() => resolveClose()));
      await client?.close();
    },
  };
}

const invokedPath = process.argv[1] ? resolve(process.argv[1]) : "";
if (invokedPath === fileURLToPath(import.meta.url)) {
  const app = createDashboardServer();
  app.server.on("error", (error) => {
    console.error(`Dashboard could not start: ${error.message}`);
    process.exitCode = 1;
  });
  await app.listen();
  console.log("Codex project dashboard: http://127.0.0.1:9000");
  const shutdown = async () => {
    await app.close();
    process.exit(0);
  };
  process.once("SIGINT", shutdown);
  process.once("SIGTERM", shutdown);
}

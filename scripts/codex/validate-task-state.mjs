import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { parseTaskState, readProjectTaskState } from "./task-state.mjs";

export { parseTaskState };

const root = resolve(fileURLToPath(new URL("../..", import.meta.url)));
if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    const { state } = await readProjectTaskState(root);
    console.log(`TASKS.md valid: ${state.currentTask?.id ?? "no current task"} (${state.currentTaskStatus}); ${state.completedTasks}/${state.totalTasks} tasks complete.`);
    if (state.nextTaskSelectionRequired) console.log("Next task selection is not an explicit task row; the queue will not infer a checkbox-order successor.");
  } catch (error) {
    console.error(`TASKS.md validation failed: ${error.message}`);
    process.exitCode = 1;
  }
}

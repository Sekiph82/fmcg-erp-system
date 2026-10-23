import assert from "node:assert/strict";
import test from "node:test";
import { createNextTaskSpec } from "./task-spec.mjs";

test("successor prompt uses the exact selected non-M20 task row", () => {
  const spec = createNextTaskSpec({
    currentTask: { id: "M02.S03.T001", title: "Refresh rotation" },
    currentTaskStatus: "COMPLETE",
    nextTaskId: "M02.S03.T002",
    tasks: [{
      id: "M02.S03.T002",
      title: "Implement inactivity/session-expiry policy",
      marker: " ",
    }],
  });

  assert.equal(spec.status, "SPEC_READY");
  assert.equal(spec.taskId, "M02.S03.T002");
  assert.equal(spec.title, "Implement inactivity/session-expiry policy");
  assert.match(spec.prompt, /TASK: M02\.S03\.T002/);
  assert.doesNotMatch(spec.prompt, /M20 task/);
});

test("successor prompt is withheld when the canonical row is not READY", () => {
  const spec = createNextTaskSpec({
    currentTask: { id: "M02.S03.T001", title: "Refresh rotation" },
    currentTaskStatus: "COMPLETE",
    nextTaskId: "M02.S03.T002",
    tasks: [{ id: "M02.S03.T002", title: "Expiry policy", marker: "!" }],
  });

  assert.equal(spec.status, "SUCCESSOR_NOT_READY");
  assert.equal(spec.prompt, null);
});

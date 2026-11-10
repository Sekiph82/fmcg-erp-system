import test from "node:test";
import assert from "node:assert/strict";
import { EventEmitter } from "node:events";
import { PassThrough, Writable } from "node:stream";
import { CodexAppServerClient } from "./app-server-client.mjs";

test("project and thread listing use only the Codex state database", async () => {
  const requests = [];
  const client = new CodexAppServerClient({
    spawnProcess: () => {
      const child = new EventEmitter();
      child.stdout = new PassThrough();
      child.exitCode = null;
      child.stdin = new Writable({
        write(chunk, encoding, callback) {
          const message = JSON.parse(chunk.toString("utf8"));
          if (message.id === undefined) return callback();
          requests.push(message);
          const result = message.method === "initialize" ? {} : { data: [] };
          child.stdout.write(`${JSON.stringify({ jsonrpc: "2.0", id: message.id, result })}\n`);
          callback();
        },
      });
      child.kill = () => {
        child.exitCode = 0;
        child.emit("close", 0);
      };
      return child;
    },
  });
  await client.initialize();
  await client.listProjects();
  await client.listThreads();
  await client.close();
  assert.equal(requests.find((request) => request.method === "project/list").params.useStateDbOnly, true);
  assert.equal(requests.find((request) => request.method === "thread/list").params.useStateDbOnly, true);
});

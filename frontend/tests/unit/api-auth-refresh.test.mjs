import assert from "node:assert/strict";
import { after, before, test } from "node:test";
import http from "node:http";

let server;
let baseURL;
let protectedCalls = 0;
let refreshCalls = 0;
let navigation = [];
let apiClient;
let setAppRouter;

before(async () => {
  server = http.createServer((request, response) => {
    if (request.url === "/api/v1/auth/refresh") {
      refreshCalls += 1;
      response.writeHead(200, { "content-type": "application/json" });
      response.end(JSON.stringify({ access_token: null }));
      return;
    }

    if (request.url === "/api/v1/auth/2fa/settings") {
      protectedCalls += 1;
      response.writeHead(protectedCalls === 1 ? 401 : 200, { "content-type": "application/json" });
      response.end(JSON.stringify(protectedCalls === 1 ? { detail: "expired" } : { enabled: true }));
      return;
    }

    if (request.url === "/api/v1/auth/2fa/login-verify") {
      response.writeHead(401, { "content-type": "application/json" });
      response.end(JSON.stringify({ detail: "invalid challenge" }));
      return;
    }

    response.writeHead(404);
    response.end();
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  baseURL = `http://127.0.0.1:${server.address().port}`;
  process.env.NEXT_PUBLIC_API_URL = baseURL;
  ({ apiClient, setAppRouter } = await import("../../src/lib/api.ts"));
  setAppRouter({ push: (path) => navigation.push(path) });
});

after(async () => {
  await new Promise((resolve, reject) => server.close((error) => error ? reject(error) : resolve()));
});

test("authenticated 2FA settings refresh after an expired access token", async () => {
  protectedCalls = 0;
  refreshCalls = 0;
  navigation = [];

  const response = await apiClient.get("/api/v1/auth/2fa/settings");

  assert.deepEqual(response.data, { enabled: true });
  assert.equal(protectedCalls, 2);
  assert.equal(refreshCalls, 1);
  assert.deepEqual(navigation, []);
});

test("2FA login challenge failures do not attempt refresh or redirect", async () => {
  refreshCalls = 0;
  navigation = [];

  await assert.rejects(apiClient.post("/api/v1/auth/2fa/login-verify", {}), (error) => error.response?.status === 401);

  assert.equal(refreshCalls, 0);
  assert.deepEqual(navigation, []);
});

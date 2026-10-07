import assert from "node:assert/strict";
import { after, beforeEach, test } from "node:test";
import { mkdtemp, unlink, rmdir } from "node:fs/promises";
import { fileURLToPath, pathToFileURL } from "node:url";
import path from "node:path";
import { build } from "esbuild";
import axios, { AxiosError } from "axios";

const storage = new Map([["accessToken", "old-access"], ["refreshToken", "old-refresh"]]);
globalThis.localStorage = {
  getItem: (key) => storage.get(key) ?? null,
  setItem: (key, value) => storage.set(key, value),
  removeItem: (key) => storage.delete(key),
};
let lockQueue = Promise.resolve();
Object.defineProperty(globalThis, "navigator", { configurable: true, value: {
  locks: { request: (_, callback) => {
    const next = lockQueue.then(callback);
    lockQueue = next.catch(() => {});
    return next;
  } },
} });
globalThis.window = { location: { origin: "https://frontend.test" } };

let handler;
const calls = [];
axios.defaults.adapter = async (config) => {
  calls.push(config);
  const result = await handler(config);
  if (config.url.endsWith("csrf/")) result.data = { has_refresh_cookie: true, ...result.data };
  const response = { status: result.status || 200, data: result.data || {}, headers: {}, config, statusText: "" };
  if (response.status >= 400) throw new AxiosError("Request failed", "ERR_BAD_RESPONSE", config, {}, response);
  return response;
};

const frontend = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const tempDir = await mkdtemp(path.join(frontend, "tests", ".auth-harness-"));
const bundle = path.join(tempDir, "harness.mjs");
await build({
  stdin: { contents: `export { default as api, refreshAccessToken, getWebSocketUrl } from './src/shared/services/api.js';
    export { store } from './src/shared/store/index.jsx';
    export { initializeAuth, loginSuccess, logout, logoutUser } from './src/shared/store/authSlice.jsx';
    export { AuthChangedError } from './src/shared/services/authSession.js';`, resolveDir: frontend },
  bundle: true, platform: "node", format: "esm", external: ["axios"], outfile: bundle,
  define: { "import.meta.env.VITE_REACT_APP_API_URL": JSON.stringify("https://auth.test/api/v1/") },
});
const { api, store, initializeAuth, loginSuccess, logout, logoutUser, refreshAccessToken, getWebSocketUrl, AuthChangedError } = await import(pathToFileURL(bundle));
after(async () => { await unlink(bundle); await rmdir(tempDir); });
beforeEach(() => {
  store.dispatch(logout());
  calls.length = 0;
  handler = async (config) => config.url.endsWith("csrf/") ? { data: { csrf_token: "csrf" } } : { data: {} };
});
const signIn = () => store.dispatch(loginSuccess({ access: "initial-access", user: { id: 1 } }));
const deferred = () => {
  let resolve;
  const promise = new Promise((done) => { resolve = done; });
  return { promise, resolve };
};

test("access and refresh tokens are never persisted in localStorage", () => {
  signIn();
  assert.equal(storage.has("accessToken"), false);
  assert.equal(storage.has("refreshToken"), false);
  assert.equal(storage.has("isAuthenticated"), false);
});

test("a signed-out page skips refresh instead of generating an expected 401", async () => {
  handler = async () => ({ data: { csrf_token: "csrf", has_refresh_cookie: false } });
  await store.dispatch(initializeAuth()).unwrap();
  assert.equal(store.getState().auth.initialized, true);
  assert.equal(store.getState().auth.isAuthenticated, false);
  assert.equal(store.getState().auth.error, null);
  assert.equal(calls.filter((call) => call.url.endsWith("token/refresh/")).length, 0);
});

test("a page reload restores authentication from the cookie without persisted tokens", async () => {
  handler = async (config) => {
    if (config.url.endsWith("csrf/")) return { data: { csrf_token: "csrf", has_refresh_cookie: true } };
    if (config.url.endsWith("token/refresh/")) return { data: { access: "restored-access" } };
    assert.equal(config.headers.Authorization, "Bearer restored-access");
    return { data: { id: 1, avatar: "https://auth.test/media/avatars/user.png" } };
  };
  await store.dispatch(initializeAuth()).unwrap();
  assert.equal(store.getState().auth.isAuthenticated, true);
  assert.equal(store.getState().auth.user.avatar, "https://auth.test/media/avatars/user.png");
  assert.equal(calls.filter((call) => call.url.endsWith("token/refresh/")).length, 1);
  assert.equal(storage.has("accessToken"), false);
});

test("concurrent 401 responses share one refresh and retry with the new bearer", async () => {
  signIn();
  handler = async (config) => {
    if (config.url.endsWith("csrf/")) return { data: { csrf_token: "csrf" } };
    if (config.url.endsWith("token/refresh/")) {
      assert.equal(config.headers["X-CSRFToken"], "csrf");
      assert.equal(config.data, "{}");
      assert.equal(config.withCredentials, true);
      return { data: { access: "fresh-access" } };
    }
    return config.headers.Authorization === "Bearer fresh-access" ? { data: { id: 1 } } : { status: 401 };
  };
  const results = await Promise.all([api.get("/users/profile/"), api.get("/users/profile/")]);
  assert.equal(results.length, 2);
  assert.equal(calls.filter((call) => call.url.endsWith("token/refresh/")).length, 1);
  assert.equal(store.getState().auth.accessToken, "fresh-access");
});

test("a temporary refresh network failure preserves the signed-in session", async () => {
  signIn();
  handler = async (config) => {
    if (config.url.endsWith("csrf/")) return { data: { csrf_token: "csrf" } };
    throw new AxiosError("Network unavailable", "ERR_NETWORK", config);
  };
  await assert.rejects(refreshAccessToken());
  assert.equal(store.getState().auth.isAuthenticated, true);
  assert.equal(store.getState().auth.accessToken, "initial-access");
});

test("an expired password-change request retries without nesting browser locks", { timeout: 5000 }, async () => {
  signIn();
  handler = async (config) => {
    if (config.url.endsWith("csrf/")) return { data: { csrf_token: "csrf" } };
    if (config.url.endsWith("token/refresh/")) return { data: { access: "fresh-access" } };
    return config.headers.Authorization === "Bearer fresh-access" ? { data: { access: "changed-access", user: { id: 1 } } } : { status: 401 };
  };
  const response = await api.post("/users/auth/password/change/", { old_password: "old" });
  assert.equal(response.status, 200);
  assert.equal(calls.filter((call) => call.url.endsWith("token/refresh/")).length, 1);
});

test("a delayed 401 reuses credentials already refreshed by another request", async () => {
  signIn();
  const delayed = deferred(), pending = deferred();
  handler = async (config) => {
    if (config.url.endsWith("csrf/")) return { data: { csrf_token: "csrf" } };
    if (config.url.endsWith("token/refresh/")) return { data: { access: "fresh-access" } };
    if (config.headers.Authorization === "Bearer fresh-access") return { data: { id: 1 } };
    if (config.url.endsWith("delayed/")) { pending.resolve(); await delayed.promise; }
    return { status: 401 };
  };
  const second = api.get("/delayed/");
  await pending.promise;
  await api.get("/immediate/");
  delayed.resolve();
  await second;
  assert.equal(calls.filter((call) => call.url.endsWith("token/refresh/")).length, 1);
});

test("an invalid refresh response clears authentication", async () => {
  signIn();
  handler = async (config) => config.url.endsWith("csrf/") ? { data: { csrf_token: "csrf" } } : { status: 401 };
  await assert.rejects(refreshAccessToken());
  assert.equal(store.getState().auth.isAuthenticated, false);
  assert.equal(store.getState().auth.accessToken, null);
});

test("logout prevents an in-flight refresh from restoring authentication", async () => {
  signIn();
  const started = deferred(), finished = deferred();
  handler = async (config) => {
    if (config.url.endsWith("csrf/")) return { data: { csrf_token: "csrf" } };
    started.resolve();
    await finished.promise;
    return { data: { access: "obsolete-access" } };
  };
  const refreshing = refreshAccessToken();
  await started.promise;
  store.dispatch(logout());
  finished.resolve();
  await assert.rejects(refreshing, AuthChangedError);
  assert.equal(store.getState().auth.accessToken, null);
});

test("a new login cannot be overwritten by an old bootstrap response", async () => {
  const started = deferred(), finished = deferred();
  handler = async (config) => {
    if (config.url.endsWith("csrf/")) return { data: { csrf_token: "csrf" } };
    started.resolve();
    await finished.promise;
    return { data: { access: "obsolete-access" } };
  };
  const boot = store.dispatch(initializeAuth());
  await started.promise;
  store.dispatch(loginSuccess({ access: "new-access", user: { id: 2 } }));
  finished.resolve();
  await boot;
  assert.equal(store.getState().auth.user.id, 2);
  assert.equal(store.getState().auth.accessToken, "new-access");
  assert.equal(store.getState().auth.isInitializing, false);
});

test("a forced tab bootstrap waits for an obsolete rotation and loads the new user", async () => {
  const started = deferred(), finished = deferred();
  let rotations = 0;
  handler = async (config) => {
    if (config.url.endsWith("csrf/")) return { data: { csrf_token: "csrf" } };
    if (config.url.endsWith("token/refresh/")) {
      rotations += 1;
      if (rotations === 1) { started.resolve(); await finished.promise; }
      return { data: { access: rotations === 1 ? "obsolete-access" : "current-access" } };
    }
    return { data: { id: 2 } };
  };
  const first = store.dispatch(initializeAuth());
  await started.promise;
  store.dispatch(loginSuccess({ access: "new-access", user: { id: 2 } }));
  const second = store.dispatch(initializeAuth({ force: true }));
  finished.resolve();
  await Promise.all([first, second]);
  assert.equal(rotations, 2);
  assert.equal(store.getState().auth.accessToken, "current-access");
  assert.equal(store.getState().auth.user.id, 2);
});

test("failed logout keeps authentication so the user can retry", async () => {
  signIn();
  handler = async (config) => {
    if (config.url.endsWith("csrf/")) return { data: { csrf_token: "csrf" } };
    throw new AxiosError("Network unavailable", "ERR_NETWORK", config);
  };
  await assert.rejects(store.dispatch(logoutUser()).unwrap());
  assert.equal(store.getState().auth.isAuthenticated, true);
});

test("auth requests send CSRF and refresh cookies without a bearer", async () => {
  signIn();
  handler = async (config) => {
    if (config.url.endsWith("csrf/")) return { data: { csrf_token: "csrf" } };
    assert.equal(config.headers.Authorization, undefined);
    assert.equal(config.headers["X-CSRFToken"], "csrf");
    assert.equal(config.withCredentials, true);
    return { data: { access: "login-access", user: { id: 1 } } };
  };
  await api.post("/users/auth/login/", { username: "user", password: "password" });
});

test("websocket URLs use the API host and contain no token", () => {
  assert.equal(getWebSocketUrl("/ws/live/"), "wss://auth.test/ws/live/");
});

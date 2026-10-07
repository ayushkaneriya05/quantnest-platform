/* eslint-env node */
import assert from "node:assert/strict";
import { after, test } from "node:test";
import { existsSync } from "node:fs";
import { mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { spawnSync } from "node:child_process";
import { build } from "esbuild";

const frontend = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const chrome = [process.env.CHROME_PATH, "C:/Program Files/Google/Chrome/Application/chrome.exe",
  "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe", "/usr/bin/google-chrome", "/usr/bin/chromium"]
  .find((candidate) => candidate && existsSync(candidate));
const temporary = await mkdtemp(path.join(frontend, "tests", ".ui-harness-"));
after(async () => {
  // Browser profiles contain nested files; verify the target before cleanup.
  assert.ok(path.resolve(temporary).startsWith(path.join(frontend, "tests") + path.sep));
  await rm(temporary, { recursive: true, force: true });
});

const entry = `
import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { MemoryRouter, Routes, Route, Outlet, useNavigate } from 'react-router-dom';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import authReducer from './src/shared/store/authSlice.jsx';
import notificationReducer from './src/shared/store/notificationSlice.jsx';
import { PageActionsProvider } from './src/shared/context/PageActionsContext.jsx';
import { usePageActions, usePageActionState } from './src/shared/context/pageActions.js';
import { useSetPageActions } from './src/shared/hooks/useSetPageActions.js';
import ProfileTab from './src/features/dashboard/components/profile-settings/profile-tab.jsx';
import GoogleCallbackPage from './src/features/auth/pages/GoogleCallbackPage.jsx';
import GoogleLoginButton from './src/features/auth/components/GoogleLoginButton.jsx';

window.regressionErrors = [];
window.addEventListener('error', (event) => window.regressionErrors.push(event.message));
const previousError = console.error;
console.error = (...args) => { window.regressionErrors.push(args.map(String).join(' ')); previousError(...args); };
const wait = () => new Promise((resolve) => setTimeout(resolve, 100));
const check = (value, message) => { if (!value) throw new Error(message); };
const waitFor = async (predicate) => { for (let attempt = 0; attempt < 40; attempt++) { if (predicate()) return; await wait(); } throw new Error('UI did not settle'); };
const finish = (value) => { document.querySelector('#result').textContent = JSON.stringify(value); };
let renders = 0, navigate;

function Layout() {
  const { actions, headerContent } = usePageActionState();
  return <><header>{headerContent}{actions}</header><Outlet /></>;
}
function Page() {
  if (++renders > 20) throw new Error('Header publication caused a render loop');
  const [count, setCount] = useState(0);
  const { setPageHeader, clearPageHeader } = usePageActions();
  navigate = useNavigate();
  useEffect(() => { setPageHeader(<span id="custom-header">Header {count}</span>); return clearPageHeader; }, [count, setPageHeader, clearPageHeader]);
  useSetPageActions(<button id="action" onClick={() => setCount((current) => current + 1)}>Count {count}</button>);
  return <main>Page</main>;
}
const root = createRoot(document.querySelector('#root'));
const mode = new URLSearchParams(location.search).get('case');
async function run() {
  if (mode === 'header') {
    root.render(<MemoryRouter initialEntries={['/page']} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <PageActionsProvider><Routes><Route element={<Layout />}>
        <Route path="page" element={<Page />} /><Route path="other" element={<main>Other</main>} />
      </Route></Routes></PageActionsProvider></MemoryRouter>);
    await wait();
    check(document.querySelector('#action')?.textContent === 'Count 0', 'Initial action missing');
    document.querySelector('#action').click();
    await wait();
    check(document.querySelector('#action')?.textContent === 'Count 1', 'Action callback is stale');
    check(document.querySelector('#custom-header')?.textContent === 'Header 1', 'Custom header is stale');
    navigate('/other');
    await wait();
    check(document.querySelector('header').textContent === '', 'Header was not cleared on navigation');
    check(renders < 10, 'Excessive page rerenders');
  } else if (mode === 'google-back') {
    root.render(<MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <GoogleLoginButton onError={(message) => window.regressionErrors.push(message)} />
    </MemoryRouter>);
    await wait();
    const button = document.querySelector('button');
    button.click();
    await wait();
    check(button.disabled && button.textContent.includes('Authenticating'), 'Google start did not set the busy state');
    window.dispatchEvent(new PageTransitionEvent('pageshow', { persisted: false }));
    await wait();
    check(button.disabled, 'An ordinary page event cleared an active Google request');
    window.dispatchEvent(new PageTransitionEvent('pageshow', { persisted: true }));
    await wait();
    check(!button.disabled && button.textContent.includes('Continue with Google'), 'Returning from Google kept the button busy');
    button.click();
    await wait();
    check(window.googleRequests.filter((url) => url.includes('/start/')).length === 2, 'Google sign-in could not be restarted after Back');
  } else if (mode.startsWith('google-')) {
    const store = configureStore({ reducer: { auth: authReducer, notification: notificationReducer } });
    root.render(<Provider store={store}><MemoryRouter initialEntries={['/google-callback']} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Routes><Route path="/google-callback" element={<GoogleCallbackPage />} />
        <Route path="/dashboard" element={<main id="signed-in">Dashboard</main>} />
        <Route path="/login" element={<main>Login</main>} /></Routes>
    </MemoryRouter></Provider>);
    await wait();
    check(window.googleRequests.filter((url) => url.includes('/complete/')).length === 1, 'Google result was consumed more than once');
    if (mode === 'google-success') {
      check(document.querySelector('#signed-in'), 'Google login did not navigate to dashboard');
      check(store.getState().auth.isAuthenticated, 'Google login did not update authentication');
    } else if (mode === 'google-2fa') {
      check(!store.getState().auth.isAuthenticated, 'Google bypassed two-factor authentication');
      await waitFor(() => document.getElementById('2fa-token'));
      const input = document.getElementById('2fa-token');
      const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
      setter.call(input, '123456');
      input.dispatchEvent(new Event('input', { bubbles: true }));
      await wait();
      input.closest('form').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
      await wait();
      check(document.querySelector('#signed-in'), 'Google two-factor verification did not finish login');
      check(store.getState().auth.isAuthenticated, 'Verified Google login did not update authentication');
    } else {
      await waitFor(() => document.querySelector('[role="alert"]'));
      check(document.querySelector('[role="alert"]')?.textContent.includes('cancelled'), 'Backend Google failure was not shown');
      check(!store.getState().auth.isAuthenticated, 'Failed Google login authenticated a user');
    }
  } else {
    const store = configureStore({ reducer: { auth: authReducer }, preloadedState: {
      auth: { user: window.fixtureUser, accessToken: 'fixture-access', isAuthenticated: true },
    } });
    root.render(<Provider store={store}><ProfileTab /></Provider>);
    await waitFor(() => document.querySelector('img[alt="Profile picture"]')?.naturalWidth > 0);
    check(document.querySelector('img[alt="Profile picture"]')?.naturalWidth > 0, 'Avatar did not load');
    const save = async () => { document.querySelector('form').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true })); await wait(); };
    await save();
    check(!window.profileRequests[0].has('avatar'), 'Saving text submitted the existing avatar URL');
    check(!window.profileRequests[0].has('newAvatar'), 'Unknown newAvatar field was submitted');
    check(document.querySelector('img[alt="Profile picture"]')?.naturalWidth > 0, 'Saving text removed the avatar');
    const fileInput = document.querySelector('#avatar-upload');
    const transfer = new DataTransfer();
    const canvas = document.createElement('canvas');
    canvas.width = canvas.height = 2;
    const image = await new Promise((resolve) => canvas.toBlob(resolve, 'image/png'));
    transfer.items.add(new File([image], 'avatar.png', { type: 'image/png' }));
    fileInput.files = transfer.files;
    fileInput.dispatchEvent(new Event('change', { bubbles: true }));
    await wait();
    check(document.querySelector('img[alt="Profile picture"]')?.naturalWidth === 2, 'New avatar preview did not load');
    await save();
    check(window.profileRequests[1].get('avatar') instanceof File, 'New avatar was not submitted as a file');
    [...document.querySelectorAll('button')].find((button) => button.textContent.includes('Remove Profile Picture')).click();
    await wait();
    check(!document.querySelector('img[alt="Profile picture"]'), 'Removed avatar still displayed');
    await save();
    check(window.profileRequests[2].get('avatar') === '', 'Avatar removal was not included in the save');
    check(store.getState().auth.user.avatar === null, 'Removed avatar remained in shared profile data');
  }
  check(window.regressionErrors.length === 0, window.regressionErrors.join('\\n'));
  finish({ ok: true, renders });
}
run().catch((error) => finish({ ok: false, error: error.message, errors: window.regressionErrors }));
`;

await build({
  stdin: { contents: entry, resolveDir: frontend, loader: "jsx" },
  outfile: path.join(temporary, "harness.js"), bundle: true, format: "iife", jsx: "automatic",
  alias: { "@": path.join(frontend, "src") },
  define: { "process.env.NODE_ENV": '"development"' },
  plugins: [{ name: "isolated-profile-api", setup(builder) {
    builder.onResolve({ filter: /services\/api(?:\.js)?$/ }, () => ({ path: "api", namespace: "fixture" }));
    builder.onLoad({ filter: /.*/, namespace: "fixture" }, () => ({ contents: `
      window.fixtureUser = { id: 1, username: 'fixture', first_name: 'Test', last_name: 'User', email: 'test@example.com', bio: 'Profile fixture biography', avatar: 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="2" height="2"%3E%3Crect width="2" height="2" fill="blue"/%3E%3C/svg%3E' };
      window.profileRequests = [];
      window.googleRequests = [];
      export const isAuthFailure = () => false;
      export const refreshAccessToken = async () => 'fixture-access';
      export default { post: async (url, payload) => {
        window.googleRequests.push(url);
        if (url.includes('/start/')) return new Promise(() => {});
        const mode = new URLSearchParams(location.search).get('case');
        if (mode === 'google-error') throw { response: { data: { message: 'Google sign-in was cancelled.' } } };
        if (mode === 'google-2fa' && url.includes('/complete/')) return { data: { is_2fa_required: true, login_token: 'challenge', next: '/dashboard' } };
        if (url.includes('/verify-2fa/') && (payload.login_token !== 'challenge' || payload.otp_token !== '123456')) throw new Error('Invalid two-factor payload');
        return { data: { access: 'fixture-access', user: window.fixtureUser, next: '/dashboard' } };
      }, patch: async (_, payload) => {
        window.profileRequests.push(new Map(payload.entries()));
        const user = { ...window.fixtureUser, bio: payload.get('bio') };
        if (payload.get('avatar') === '') user.avatar = null;
        return { data: user };
      } };
    ` }));
  } }],
});
const script = await readFile(path.join(temporary, "harness.js"), "utf8");
const html = path.join(temporary, "harness.html");
await writeFile(html, `<div id="root"></div><pre id="result"></pre><script>${script.replaceAll("</script>", "<\\/script>")}</script>`);

for (const scenario of ["header", "profile", "google-success", "google-2fa", "google-error", "google-back"]) {
  test(`${scenario} UI regression in headless Chrome`, { skip: !chrome }, () => {
    const url = pathToFileURL(html);
    url.searchParams.set("case", scenario);
    const result = spawnSync(chrome, ["--headless", "--disable-gpu", "--no-first-run", "--disable-background-networking",
      "--disable-extensions", `--user-data-dir=${path.join(temporary, scenario)}`, "--dump-dom", "--virtual-time-budget=8000", url.toString()],
      { encoding: "utf8", windowsHide: true, timeout: 30000, maxBuffer: 10 * 1024 * 1024 });
    assert.equal(result.status, 0, result.error?.message || result.stderr.slice(-2000));
    const output = result.stdout.match(/<pre id="result"[^>]*>(.*?)<\/pre>/s)?.[1];
    assert.ok(output, "Browser regression did not finish: " + result.stdout.slice(-5000));
    const report = JSON.parse(output.replaceAll("&quot;", '"').replaceAll("&amp;", "&").replaceAll("&lt;", "<").replaceAll("&gt;", ">"));
    assert.equal(report.ok, true, JSON.stringify(report));
  });
}

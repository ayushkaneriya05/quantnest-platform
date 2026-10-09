/* eslint-env node */
import assert from "node:assert/strict";
import { after, test } from "node:test";
import { existsSync } from "node:fs";
import { mkdtemp, readFile, readdir, rm, writeFile } from "node:fs/promises";
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
import ThemeProvider from './src/shared/context/ThemeProvider.jsx';
import { usePageActions, usePageActionState } from './src/shared/context/pageActions.js';
import { useSetPageActions } from './src/shared/hooks/useSetPageActions.js';
import ProfileTab from './src/features/settings/components/profile-tab.jsx';
import GoogleCallbackPage from './src/features/auth/pages/GoogleCallbackPage.jsx';
import GoogleLoginButton from './src/features/auth/components/GoogleLoginButton.jsx';
import TwoFASetupModal from './src/features/settings/components/two-fa-setup-modal.jsx';
import LoginPage from './src/features/auth/pages/LoginPage.jsx';
import RegisterPage from './src/features/auth/pages/RegisterPage.jsx';
import PasswordResetRequestPage from './src/features/auth/pages/PasswordResetRequestPage.jsx';
import PasswordResetConfirmPage from './src/features/auth/pages/PasswordResetConfirmPage.jsx';

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
const browserRoot = createRoot(document.querySelector('#root'));
const root = { render: (content) => browserRoot.render(<ThemeProvider>{content}</ThemeProvider>) };
const mode = new URLSearchParams(location.search).get('case');
async function run() {
  if (mode === 'twofa-setup') {
    root.render(<><p>Background page content</p><TwoFASetupModal isOpen onClose={() => {}} onSetupComplete={() => {}} /></>);
    await waitFor(() => document.querySelector('#secret-key')?.value === 'TESTSETUPSECRET');
    const checkSurface = () => {
      const dialog = document.querySelector('[role="dialog"]');
      const sample = document.createElement('div');
      sample.style.backgroundColor = 'hsl(var(--card))';
      document.body.appendChild(sample);
      check(getComputedStyle(dialog).backgroundColor === getComputedStyle(sample).backgroundColor, 'Setup modal must use the solid themed card surface');
      check(getComputedStyle(dialog).opacity === '1', 'Setup modal remains translucent');
      sample.remove();
    };
    await wait(); await wait(); checkSurface();
    check(getComputedStyle(document.querySelector('img[alt="QR Code for 2FA"]')).backgroundColor === 'rgb(255, 255, 255)', 'QR code needs a white scanning surface');
    [...document.querySelectorAll('button')].find(button => button.textContent.trim() === 'Next').click();
    await waitFor(() => document.getElementById('2fa-code-verify'));
    checkSurface();
    const code = document.getElementById('2fa-code-verify');
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(code, '123456');
    code.dispatchEvent(new Event('input', { bubbles: true }));
    await wait();
    [...document.querySelectorAll('button')].find(button => button.textContent.includes('Verify & Enable')).click();
    await waitFor(() => document.body.textContent.includes('TEST-BACKUP-CODE'));
    checkSurface();
  } else if (mode.startsWith('auth-')) {
    const store = configureStore({ reducer: { auth: authReducer, notification: notificationReducer } });
    const Page = { 'auth-login': LoginPage, 'auth-register': RegisterPage, 'auth-reset': PasswordResetRequestPage, 'auth-confirm': PasswordResetConfirmPage }[mode];
    root.render(<Provider store={store}><MemoryRouter initialEntries={['/password-reset/confirm/example/token']} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}><Routes><Route path='/password-reset/confirm/:uid/:token' element={<Page />} /></Routes></MemoryRouter></Provider>);
    await waitFor(() => document.querySelector('form'));
    check(document.documentElement.scrollWidth <= window.innerWidth + 1, 'Authentication page overflows horizontally');
    for (const input of document.querySelectorAll('form input:not([type=checkbox])')) {
      const box = input.getBoundingClientRect();
      check(box.width > 100 && box.left >= 0 && box.right <= window.innerWidth, 'Form input is clipped');
    }
    const rgb = value => { const n=value.match(/[0-9.]+/g).map(Number); return [...n.slice(0,3),n[3] ?? 1]; };
    const blend = (a,b) => [...a.slice(0,3).map((v,i)=>v*a[3]+b[i]*(1-a[3])),1];
    const lum = c => c.slice(0,3).map(v=>v/255).map(v=>v<=0.04045?v/12.92:((v+0.055)/1.055)**2.4).reduce((s,v,i)=>s+v*[0.2126,0.7152,0.0722][i],0);
    for (const node of document.querySelectorAll('label, button, a, h1, h2, h3, p')) {
      if (!node.textContent.trim() || node.closest('[disabled]') || !node.getClientRects().length) continue;
      const chain=[]; for(let parent=node;parent;parent=parent.parentElement)chain.unshift(parent);
      let background=[255,255,255,1];
      for(const parent of chain)background=blend(rgb(getComputedStyle(parent).backgroundColor),background);
      const foreground=blend(rgb(getComputedStyle(node).color),background);
      const ratio=(Math.max(lum(foreground),lum(background))+0.05)/(Math.min(lum(foreground),lum(background))+0.05);
      check(ratio>=4.5, 'Low contrast ('+ratio.toFixed(2)+'): '+node.textContent.trim().slice(0,60));
    }
  } else if (mode === 'header') {
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
        <Route path="/overview" element={<main id="signed-in">Dashboard</main>} />
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
        if (url === '/users/2fa/create/') return { data: { secret_key: 'TESTSETUPSECRET', qr_code: '<svg xmlns="http://www.w3.org/2000/svg" width="2" height="2"><rect width="2" height="2" /></svg>' } };
        if (url === '/users/2fa/verify/') return { data: { backup_codes: ['TEST-BACKUP-CODE'] } };
        window.googleRequests.push(url);
        if (url.includes('/start/')) return new Promise(() => {});
        const mode = new URLSearchParams(location.search).get('case');
        if (mode === 'google-error') throw { response: { data: { message: 'Google sign-in was cancelled.' } } };
        if (mode === 'google-2fa' && url.includes('/complete/')) return { data: { is_2fa_required: true, login_token: 'challenge', next: '/overview' } };
        if (url.includes('/verify-2fa/') && (payload.login_token !== 'challenge' || payload.otp_token !== '123456')) throw new Error('Invalid two-factor payload');
        return { data: { access: 'fixture-access', user: window.fixtureUser, next: '/overview' } };
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
const assets = path.join(frontend, "dist", "assets");
const stylesheet = (await readdir(assets)).find(name => name.endsWith(".css"));
assert.ok(stylesheet, "Build the frontend before running UI regressions.");
const themeBootstrap = `const theme = new URLSearchParams(location.search).get('theme'); document.documentElement.classList.toggle('dark', theme === 'dark'); document.documentElement.dataset.themePreference = theme;`;
await writeFile(html, `<style>${await readFile(path.join(assets, stylesheet), "utf8")}</style><script>${themeBootstrap}</script><div id="root"></div><pre id="result" style="display:none"></pre><script>${script.replaceAll("</script>", "<\\/script>")}</script>`);

for (const theme of ["light", "dark"])
for (const scenario of ["twofa-setup", "auth-login", "auth-register", "auth-reset", "auth-confirm", "header", "profile", "google-success", "google-2fa", "google-error", "google-back"]) {
  test(`${scenario} ${theme} UI regression in headless Chrome`, { skip: !chrome }, () => {
    const url = pathToFileURL(html);
    url.searchParams.set("case", scenario);
    url.searchParams.set("theme", theme);
    const result = spawnSync(chrome, ["--headless", "--disable-gpu", "--no-first-run", "--disable-background-networking",
      "--disable-extensions", `--window-size=${scenario.startsWith('auth-') ? '390,844' : '1440,1000'}`, `--user-data-dir=${path.join(temporary, theme + '-' + scenario)}`, "--dump-dom", "--virtual-time-budget=8000", url.toString()],
      { encoding: "utf8", windowsHide: true, timeout: 30000, maxBuffer: 10 * 1024 * 1024 });
    assert.equal(result.status, 0, result.error?.message || result.stderr.slice(-2000));
    const output = result.stdout.match(/<pre id="result"[^>]*>(.*?)<\/pre>/s)?.[1];
    assert.ok(output, "Browser regression did not finish: " + result.stdout.slice(-5000));
    const report = JSON.parse(output.replaceAll("&quot;", '"').replaceAll("&amp;", "&").replaceAll("&lt;", "<").replaceAll("&gt;", ">"));
    assert.equal(report.ok, true, JSON.stringify(report));
  });
}

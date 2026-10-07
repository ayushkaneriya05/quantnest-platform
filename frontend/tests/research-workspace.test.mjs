/* eslint-env node */
import assert from "node:assert/strict";
import { after, test } from "node:test";
import { existsSync } from "node:fs";
import { mkdtemp, readFile, readdir, rm, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { spawnSync } from "node:child_process";
import { build } from "esbuild";
import { mergeResearchRuns } from "../src/features/dashboard/pages/analysis/hooks/researchState.js";

test("delayed research updates cannot replace a newer revision or erase history", () => {
  const original = [{ id: 1, revision: 4, status: "COMPLETED", result: { answer: "Validated" } }];
  assert.deepEqual(mergeResearchRuns(original, [{ id: 1, revision: 2, status: "RUNNING" }], false), original);
  const updated = mergeResearchRuns(original, [{ id: 1, revision: 5, progress_message: "Updated" }], false);
  assert.equal(updated[0].result.answer, "Validated");
  const history = mergeResearchRuns(updated, [{ id: 2, revision: 1 }, { id: 3, revision: 1 }]);
  assert.deepEqual(history.map((item) => item.id), [1, 2, 3]);
});

const frontend = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const chrome = [process.env.CHROME_PATH, "C:/Program Files/Google/Chrome/Application/chrome.exe", "/usr/bin/chromium"].find((candidate) => candidate && existsSync(candidate));
const temporary = await mkdtemp(path.join(frontend, "tests", ".research-harness-"));
after(async () => { assert.ok(path.resolve(temporary).startsWith(path.join(frontend, "tests") + path.sep)); await rm(temporary, { recursive: true, force: true }); });
const entry = `
import React from 'react';
import { createRoot } from 'react-dom/client';
import { MemoryRouter } from 'react-router-dom';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import notificationReducer from './src/shared/store/notificationSlice.jsx';
import { PageActionsProvider } from './src/shared/context/PageActionsContext.jsx';
import { usePageActionState } from './src/shared/context/pageActions.js';
import AIResearchAssistant from './src/features/dashboard/pages/analysis/AIResearchAssistant.jsx';
import MarketScreener from './src/features/dashboard/pages/analysis/MarketScreener.jsx';
window.regressionErrors = [];
window.addEventListener('error', (event) => window.regressionErrors.push(event.message));
console.error = (...args) => window.regressionErrors.push(args.map(String).join(' '));
const wait = () => new Promise((resolve) => setTimeout(resolve, 100));
const check = (value, message) => { if (!value) throw new Error(message); };
const waitFor = async (predicate, label = 'UI did not settle') => { for (let attempt = 0; attempt < 40; attempt++) { if (predicate()) return; await wait(); } throw new Error(label + '; dialogs: ' + [...document.querySelectorAll('[role="dialog"]')].map((item) => item.textContent).join(' | ')); };
const button = (label) => [...document.querySelectorAll('button')].find((item) => item.textContent.trim() === label);
const mode = new URLSearchParams(location.search).get('case');
const store = configureStore({ reducer: { notification: notificationReducer } });
const freshConversation = ['welcome', 'message-race'].includes(mode);
function WorkspaceLayout() {
  const { actions } = usePageActionState();
  return <div className="flex h-screen flex-col"><header className="flex h-16 shrink-0 items-center justify-between px-4">Dashboard navigation<div>{actions}</div></header><main className="flex min-h-0 flex-1 flex-col">{mode === 'screener' ? <MarketScreener /> : <AIResearchAssistant />}</main></div>;
}
createRoot(document.querySelector('#root')).render(<Provider store={store}><MemoryRouter initialEntries={[freshConversation ? '/' : '/?session=1']} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}><PageActionsProvider><WorkspaceLayout /></PageActionsProvider></MemoryRouter></Provider>);
async function run() {
  await waitFor(() => freshConversation ? button('Analyze a stock') : document.querySelector('article') || mode === 'screener' && document.querySelector('[aria-label="Select RELIANCE"]'));
  if (mode === 'welcome') {
    check(document.body.textContent.includes('Explore the market') && document.body.textContent.includes('Develop a strategy'), 'Starter groups missing');
    button('Analyze a stock').click(); await wait();
    const input = document.querySelector('textarea');
    check(input.value.includes('RELIANCE'), 'Starter did not populate composer');
    check(window.researchRequests.length === 0, 'Starter submitted automatically');
    input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', shiftKey: true, bubbles: true })); await wait();
    check(window.researchRequests.length === 0, 'Shift Enter submitted');
    input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true })); await wait();
    input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true })); await wait();
    check(window.researchRequests.filter((item) => item.url === '/research/runs/').length === 1, 'Duplicate submission was allowed');
  } else if (mode === 'message-race') {
    button('Analyze a stock').click(); await wait();
    document.querySelector('textarea').dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
    await waitFor(() => document.querySelector('article[data-run-id="2"] [role="status"]')?.textContent.includes('Loading candles'), 'Compact progress was not hydrated after new-chat navigation');
    await waitFor(() => document.querySelector('article[data-run-id="2"]')?.textContent.includes('General research'), 'Frozen request context was not restored');
    check(document.querySelector('[aria-label="Research timeframe"]').textContent.includes('1D'), 'Full REST context was not restored after compact progress');
    check(window.researchRequests.length === 1, 'Research was submitted more than once');
  } else if (mode === 'conversation' || mode === 'mobile') {
    check(document.querySelector('h2')?.textContent.includes('Market observations'), 'Markdown heading was not rendered');
    document.querySelector('[aria-label="Open E1 evidence"]').click(); await wait();
    check(document.querySelector('[role="dialog"]')?.textContent.includes('100.25'), 'Citation opened incorrect evidence');
    document.querySelector('[role="dialog"]').dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true })); await waitFor(() => !document.querySelector('[role="dialog"][data-state="open"]'));
    button('Compare volatility').click(); await wait();
    check(document.querySelector('textarea').value === 'Compare volatility', 'Followup did not retain the conversation');
    const messages = document.querySelector('[data-testid="research-messages"]');
    for (let index = 0; index < 30; index++) { const clone = messages.querySelector('article').cloneNode(true); messages.firstElementChild.append(clone); }
    messages.scrollTop = messages.scrollHeight;
    const composer = document.querySelector('[data-testid="research-composer"]').getBoundingClientRect();
    check(composer.bottom <= innerHeight + 2 && composer.top > 0, 'Composer scrolled out of the viewport');
    check(composer.height <= 150, 'Composer takes excessive conversation space');
    check(messages.clientHeight >= innerHeight - 220, 'Conversation does not use available vertical space');
    check(getComputedStyle(messages).scrollbarWidth === 'thin', 'Conversation scrollbar is not themed');
    check(document.documentElement.scrollWidth <= innerWidth + 2, 'Workspace overflows horizontally');
    if (mode === 'conversation') {
      check(messages.clientWidth > 1000, 'Conversation width is unnecessarily constrained');
      document.querySelector('[aria-label="Toggle conversation sidebar"]').click(); await wait();
      check(messages.getBoundingClientRect().width === document.documentElement.clientWidth, 'Collapsed sidebar did not release conversation space');
    }
    if (mode === 'mobile') { document.querySelector('[aria-label="Open conversations"]').click(); await waitFor(() => [...document.querySelectorAll('[role="dialog"]')].some((item) => item.textContent.includes('Momentum study'))); }
  } else if (mode === 'attachments' || mode === 'mobile-attachments') {
    await waitFor(() => document.querySelector('[aria-label="Remove RELIANCE"]'), 'Saved attachments did not finish loading');
    document.querySelector('[aria-label="Remove RELIANCE"]').click(); await wait();
    check(!document.querySelector('[data-testid="research-composer"] [aria-label="Remove RELIANCE"]'), 'Stock attachment was not removed');
    button('Attach context').click(); await waitFor(() => document.querySelector('[role="dialog"][data-state="open"] [role="combobox"]'));
    const dialog = document.querySelector('[role="dialog"][data-state="open"]');
    dialog.querySelector('[role="combobox"]').click(); await waitFor(() => [...document.querySelectorAll('[role="option"]')].some((item) => item.textContent.includes('Crossover idea')));
    [...document.querySelectorAll('[role="option"]')].find((item) => item.textContent.includes('Crossover idea')).click(); await wait();
    check(document.querySelector('[aria-label="Research timeframe"]').textContent.includes('5m'), 'Attached strategy timeframe was not selected');
    for (let index = 0; index < 3; index++) { dialog.querySelectorAll('[role="checkbox"]')[index].click(); await wait(); }
    check(dialog.querySelectorAll('[role="checkbox"]')[3].disabled, 'More than three backtests can be attached');
    check(dialog.querySelector('[role="checkbox"]').getAttribute('aria-checked') === 'true', 'Themed checkbox did not retain selection');
    check(getComputedStyle(dialog.querySelector('[role="checkbox"]')).backgroundColor === 'rgb(79, 70, 229)', 'Checkbox does not match the theme');
    check([...dialog.querySelectorAll('.overflow-y-auto')].every((item) => getComputedStyle(item).scrollbarWidth === 'thin'), 'Attachment scrollbars are not themed');
    const bounds = dialog.getBoundingClientRect();
    check(bounds.left >= 0 && bounds.right <= innerWidth && bounds.top >= 0 && bounds.bottom <= innerHeight, 'Attachment dialog exceeds the viewport');
    const footer = button('Done').getBoundingClientRect();
    check(footer.bottom <= bounds.bottom, 'Attachment confirmation is outside the dialog');
    check(!window.researchRequests.length, 'Attachments submitted the question automatically');
    button('Done').click(); await wait();
    button('Compare volatility').click(); await wait();
    document.querySelector('textarea').dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true })); await wait();
    const request = window.researchRequests.find((item) => item.url === '/research/runs/').payload;
    check(request.timeframe === '5m' && request.strategy_id === 7 && request.backtest_ids.length === 3, 'Resolved attachments were not sent correctly');
  } else if (mode === 'progress') {
    check(document.body.textContent.includes('Loading candles'), 'Backend stage was not displayed');
    const socket = window.fixtureSockets[0];
    socket.onmessage({ data: JSON.stringify({ type: 'research.update', run: { id: 1, session: 1, revision: 4, status: 'RUNNING', progress_message: 'Evaluating conditions' } }) });
    socket.onmessage({ data: JSON.stringify({ type: 'research.update', run: { id: 1, session: 1, revision: 3, status: 'RUNNING', progress_message: 'Older stage' } }) }); await wait();
    const progress = document.querySelector('[data-testid="research-messages"]').textContent;
    check(progress.includes('Evaluating conditions') && !progress.includes('Older stage'), 'Stale websocket replaced a newer stage: ' + progress);
    button('Cancel').click(); await wait();
    await waitFor(() => document.querySelector('[data-testid="research-messages"]').textContent.includes('Research was cancelled'));
    socket.onmessage({ data: JSON.stringify({ type: 'research.update', run: { id: 1, session: 1, revision: 4, status: 'RUNNING', progress_message: 'Delayed stage' } }) }); await wait();
    check(!button('Retry this question').disabled, 'Delayed active update locked the composer after cancellation');
    socket.onmessage({ data: JSON.stringify({ type: 'research.update', run: { id: 99, session: 99, revision: 1, status: 'RUNNING', progress_message: 'Other conversation' } }) }); await wait();
    check(!document.querySelector('article[data-run-id="99"]'), 'Other conversation was added to this chat');
  } else if (mode === 'confirmation') {
    document.querySelector('[aria-label="Select RELIANCE"]').click(); await wait();
    button('Preview watchlist additions').click(); await wait();
    check(document.querySelector('[role="dialog"]')?.textContent.includes('RELIANCE'), 'Action preview missing instruments');
    check(!window.researchRequests.some((item) => item.url.includes('/confirm/')), 'Preview executed before confirmation');
    button('Confirm action').click(); await wait();
    check(window.researchRequests.filter((item) => item.url.includes('/confirm/')).length === 1, 'Confirmation did not execute once');
    check(document.querySelector('[role="dialog"]')?.textContent.includes('Action completed'), 'Confirmation outcome was not displayed');
  } else if (mode === 'screener') {
    check(document.body.textContent.includes('Trend setup'), 'Backend screen preset missing');
    const selector = document.querySelector('header [aria-label="Saved screens"]');
    check(selector && !document.querySelector('main [aria-label="Saved screens"]'), 'Screen selector is not in the header');
    selector.click(); await waitFor(() => document.activeElement?.type === 'search');
    await waitFor(() => document.querySelectorAll('[role="option"]').length === 21);
    check(!document.querySelector('[role="option"][data-value="1"]'), 'Older screen appeared in the latest 20');
    let search = document.activeElement;
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(search, 'Momentum study');
    search.dispatchEvent(new Event('input', { bubbles: true }));
    await waitFor(() => document.querySelector('[role="option"][data-value="1"]'));
    search.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowDown', bubbles: true }));
    search.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
    await waitFor(() => !document.querySelector('[role="listbox"]'));
    const timeframe = [...document.querySelectorAll('main [role="combobox"]')].find((item) => item.textContent === '1D');
    timeframe.click(); await waitFor(() => document.activeElement?.type === 'search');
    check(document.querySelectorAll('[role="option"]').length === 2, 'Finite choices were truncated');
    search = document.activeElement;
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(search, '5m');
    search.dispatchEvent(new Event('input', { bubbles: true })); await wait();
    check(document.querySelectorAll('[role="option"]').length === 1, 'Finite option search did not filter');
    search.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true })); await wait();
    check(timeframe.textContent === '5m', 'Keyboard selection did not update the timeframe');
    document.querySelector('[aria-label="Select RELIANCE"]').click(); await wait();
    check(!button('Ask AI about selected results').disabled, 'Selected screening results cannot be researched');
    document.querySelector('[aria-label="Sort by Close"]').click(); await wait();
    button('Reload saved result').click(); await wait();
    check(!window.researchRequests.length, 'Reloading saved result started a new observation');
  }
  check(!window.regressionErrors.length, window.regressionErrors.join('\\n'));
  document.querySelector('#result').textContent = JSON.stringify({ ok: true });
}
run().catch((error) => document.querySelector('#result').textContent = JSON.stringify({ ok: false, error: error.message, errors: window.regressionErrors }));
`;
await build({ stdin: { contents: entry, resolveDir: frontend, loader: "jsx" }, outfile: path.join(temporary, "harness.js"), bundle: true, format: "iife", jsx: "automatic", alias: { "@": path.join(frontend, "src") }, define: { "process.env.NODE_ENV": '"development"' }, plugins: [{ name: "research-fixtures", setup(builder) {
  builder.onResolve({ filter: /(?:services\/api|\.\/api)(?:\.js)?$/ }, () => ({ path: path.join(frontend, "tests/research-api-fixture.js") }));
  builder.onResolve({ filter: /EnumsContext(?:\.jsx)?$/ }, () => ({ path: "enums", namespace: "fixture" }));
  builder.onLoad({ filter: /.*/, namespace: "fixture" }, () => ({ contents: "export const useEnums = () => ({ enums: window.fixtureSchema.enums, loading: false });" }));
} }] });
const assets = path.join(frontend, "dist", "assets");
const stylesheet = existsSync(assets) ? (await readdir(assets)).find((name) => name.endsWith(".css")) : null;
assert.ok(stylesheet, "Build the frontend before running geometry regressions.");
const html = path.join(temporary, "harness.html");
await writeFile(html, `<style>${await readFile(path.join(assets, stylesheet), "utf8")}</style><div id="root"></div><pre id="result" style="display:none"></pre><script>${(await readFile(path.join(temporary, "harness.js"), "utf8")).replaceAll("</script>", "<\\/script>")}</script>`);
for (const scenario of ["welcome", "message-race", "conversation", "mobile", "attachments", "mobile-attachments", "progress", "confirmation", "screener"]) {
  test(`research ${scenario} in headless Chrome`, { skip: !chrome }, () => {
    const url = pathToFileURL(html); url.searchParams.set("case", scenario);
    const result = spawnSync(chrome, ["--headless", "--disable-gpu", "--no-first-run", "--disable-background-networking", "--disable-extensions", `--window-size=${scenario.startsWith("mobile") ? "390,844" : "1440,1000"}`, `--user-data-dir=${path.join(temporary, scenario)}`, "--dump-dom", "--virtual-time-budget=8000", url.toString()], { encoding: "utf8", windowsHide: true, timeout: 30000, maxBuffer: 10 * 1024 * 1024 });
    assert.equal(result.status, 0, result.error?.message || result.stderr.slice(-1500));
    const output = result.stdout.match(/<pre id="result"[^>]*>(.*?)<\/pre>/s)?.[1];
    assert.ok(output, result.stdout.slice(-4000));
    const report = JSON.parse(output.replaceAll("&quot;", '"').replaceAll("&amp;", "&").replaceAll("&lt;", "<").replaceAll("&gt;", ">"));
    assert.equal(report.ok, true, JSON.stringify(report));
  });
}

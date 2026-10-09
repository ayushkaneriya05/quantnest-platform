/* eslint-env node */
import assert from 'node:assert/strict';
import { test, after } from 'node:test';
import { readFile, writeFile, mkdtemp, rm, readdir } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { spawnSync } from 'node:child_process';
import { parse } from 'espree';
import { build } from 'esbuild';
import postcss from 'postcss';
import tailwind from 'tailwindcss';
import config from '../tailwind.config.js';

const frontend = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const chrome = [process.env.CHROME_PATH, 'C:/Program Files/Google/Chrome/Application/chrome.exe', 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', '/usr/bin/chromium'].find(p => p && existsSync(p));
const temporary = await mkdtemp(path.join(frontend, 'tests', '.theme-check-'));
after(async () => {
  assert.ok(path.resolve(temporary).startsWith(path.join(frontend, 'tests') + path.sep));
  await rm(temporary, { recursive: true, force: true });
});

// Render actual static text/control class combinations from every page and shared
// component. Dynamic data, inherited parent styling, and overlays need separate UI checks.
const specimens = [];
const textElements = new Set(['p', 'span', 'a', 'button', 'label', 'h1', 'h2', 'h3', 'h4', 'td', 'th', 'small', 'summary', 'Button', 'Badge', 'Link', 'Label', 'CardTitle', 'CardDescription', 'DialogTitle', 'DialogDescription', 'TableCell', 'TabsTrigger']);
let scanned = 0;
function classOptions(node) {
  if (!node) return [''];
  if (node.type === 'Literal') return [typeof node.value === 'string' ? node.value : ''];
  if (node.type === 'JSXExpressionContainer') return classOptions(node.expression);
  if (node.type === 'ConditionalExpression') return [...classOptions(node.consequent), ...classOptions(node.alternate)];
  if (node.type === 'LogicalExpression') return [...classOptions(node.left), ...classOptions(node.right)];
  const combine = (parts) => parts.reduce((rows, part) => rows.flatMap(row => part.map(value => row + value)).slice(0, 32), ['']);
  if (node.type === 'TemplateLiteral') return combine(node.quasis.flatMap((q, i) => [[q.value.cooked], ...(node.expressions[i] ? [classOptions(node.expressions[i])] : [])]));
  if (node.type === 'CallExpression' && ['cn', 'clsx'].includes(node.callee?.name)) return combine(node.arguments.map(arg => classOptions(arg).map(value => value + ' ')));
  return ['']; // Runtime API values are covered by the fixture UI tests.
}
async function scan(directory) {
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const file = path.join(directory, entry.name);
    if (entry.isDirectory()) { await scan(file); continue; }
    if (!file.endsWith('.jsx')) continue;
    scanned++;
    const source = await readFile(file, 'utf8');
    const ast = parse(source, { ecmaVersion: 'latest', sourceType: 'module', ecmaFeatures: { jsx: true }, loc: true });
    const visit = (node) => {
      if (!node || typeof node !== 'object') return;
      if (node.type === 'JSXOpeningElement' && !node.selfClosing && textElements.has(node.name?.name)) {
        const attributes = Object.fromEntries(node.attributes.filter(a => a.type === 'JSXAttribute').map(a => [a.name.name, a.value]));
        // Conditional variants and colors can share a condition; combining their
        // alternatives independently would invent states the UI cannot render.
        if (attributes.variant && attributes.variant.type !== 'Literal') return;
        const variants = classOptions(attributes.variant);
        for (const classes of classOptions(attributes.className)) {
        if (/(?:text-(?:foreground|muted|brand|success|loss|warning|destructive|\w+-\d)|bg-\w+-\d)/.test(classes)) {
          const colors = classes.split(/\s+/).filter(c => /^(?:(?:dark|hover|focus):)*(?:bg-|text-)/.test(c));
          for (const state of ['normal', 'hover', 'focus']) {
            const active = colors.filter(c => !/(hover|focus):/.test(c) || c.includes(`${state}:`)).map(c => c.replace(`${state}:`, '')).join(' ');
            for (const variant of variants) specimens.push({ source: path.relative(frontend, file) + ':' + node.loc.start.line, component: node.name.name, variant: variant || undefined, state, classes: active });
          }
        }
        }
      }
      for (const value of Object.values(node)) {
        if (Array.isArray(value)) value.forEach(visit);
        else if (value && typeof value === 'object') visit(value);
      }
    };
    visit(ast);
  }
}
await scan(path.join(frontend, 'src'));
const js = `
import { buttonVariants } from './src/shared/components/ui/button.jsx';
import { badgeVariants } from './src/shared/components/ui/badge.jsx';
import { cn } from './src/shared/lib/utils.js';
const samples = ${JSON.stringify(specimens)};
const host = document.querySelector('#samples');
for (const sample of samples) {
  const node = document.createElement('span');
  const base = sample.component === 'Button' ? buttonVariants({variant:sample.variant}) : sample.component === 'Badge' ? badgeVariants({variant:sample.variant}) : '';
  node.className = cn(base, sample.classes);
  node.textContent = 'Readable text'; host.appendChild(node);
}
const rgb = (value) => { const n=value.match(/[0-9.]+/g).map(Number); return [...n.slice(0,3), n[3] ?? 1]; };
const blend = (front,back) => front.slice(0,3).map((v,i)=> v*front[3]+back[i]*(1-front[3]));
const lum = c => c.map(v=>v/255).map(v=>v<=0.04045?v/12.92:((v+0.055)/1.055)**2.4).reduce((sum,v,i)=>sum+v*[0.2126,0.7152,0.0722][i],0);
const issues=[];
for (const theme of ['light','dark']) {
  document.documentElement.classList.toggle('dark',theme==='dark');
  const surface=rgb(getComputedStyle(host).backgroundColor);
  [...host.children].forEach((node,index)=>{
    const style=getComputedStyle(node), bg=blend(rgb(style.backgroundColor),surface), fg=blend(rgb(style.color),bg);
    const ratio=(Math.max(lum(fg),lum(bg))+0.05)/(Math.min(lum(fg),lum(bg))+0.05);
    if(ratio < 4.5) issues.push({...samples[index],theme,ratio:Number(ratio.toFixed(2))});
  });
}
document.querySelector('#result').textContent=JSON.stringify({scanned:${scanned},samples:samples.length,issues});
`;
const bundled = await build({ stdin: { contents: js, resolveDir: frontend, loader: 'jsx' }, bundle: true, write: false, format: 'iife', jsx: 'automatic', alias: { '@': path.join(frontend, 'src') }, define: { 'process.env.NODE_ENV': '"production"' } });
const raw = 'dark ' + specimens.map(s => s.classes).join(' ');
const css = await postcss([tailwind({ ...config, content: [{ raw }, { raw: await readFile(path.join(frontend, 'src/shared/components/ui/button.jsx'), 'utf8') }, { raw: await readFile(path.join(frontend, 'src/shared/components/ui/badge.jsx'), 'utf8') }] })]).process(await readFile(path.join(frontend, 'src/index.css'), 'utf8'), { from: path.join(frontend, 'src/index.css') });
const html = path.join(temporary, 'index.html');
await writeFile(html, `<style>${css.css}\n*{transition:none!important;animation:none!important}</style><div id="samples" style="background:hsl(var(--card));color:hsl(var(--foreground))"></div><pre id="result"></pre><script>${bundled.outputFiles[0].text.replaceAll('</script>', '<\\/script>')}</script>`);
test('text and control styles across all frontend pages have readable theme pairs', { skip: !chrome }, () => {
  const result = spawnSync(chrome, ['--headless', '--disable-gpu', '--no-first-run', '--disable-background-networking', '--disable-extensions', '--no-proxy-server', `--user-data-dir=${path.join(temporary, 'profile')}`, '--dump-dom', '--virtual-time-budget=4000', pathToFileURL(html).toString()], { windowsHide: true, encoding: 'utf8', timeout: 30000, maxBuffer: 12 * 1024 * 1024 });
  assert.equal(result.status, 0, result.error?.message || result.stderr.slice(-1000));
  const output = result.stdout.match(/<pre id="result">(.*?)<\/pre>/s)?.[1];
  assert.ok(output, result.stdout.slice(-1000));
  const report = JSON.parse(output.replaceAll('&quot;', '"').replaceAll('&amp;', '&').replaceAll('&lt;', '<').replaceAll('&gt;', '>'));
  console.log(`${report.scanned} source files; ${report.samples} text/control states per theme`);
  // Collapse duplicate state findings so a failure remains readable.
  const issues = [...new Map(report.issues.map(i => [i.source + i.theme + i.classes, i])).values()];
  assert.equal(issues.length, 0, issues.map(i => `${i.source} ${i.theme}/${i.state} ${i.ratio}: ${i.classes}`).join('\n'));
});

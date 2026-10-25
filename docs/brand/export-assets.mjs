// Run from any directory: node docs/brand/export-assets.mjs
import { mkdir, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { join } from 'node:path';
await import('./brand.js');
const directory = fileURLToPath(new URL('./assets/', import.meta.url));
await mkdir(directory, { recursive: true });
const brand = globalThis.QuantNestBrand;
for (const concept of brand.concepts) {
  await writeFile(join(directory, `${concept.id}-symbol.svg`), brand.symbolSvg(concept.id));
  await writeFile(join(directory, `${concept.id}-logo.svg`), brand.lockupSvg(concept.id));
  await writeFile(join(directory, `${concept.id}-animated.svg`), brand.lockupSvg(concept.id, { animated: true, prefix: 'quantnest' }));
  if (concept.wordmark) {
    for (const theme of ['light', 'dark']) {
      await writeFile(join(directory, `${concept.id}-colour-${theme}.svg`), brand.lockupSvg(concept.id, { theme, accent: true }));
      await writeFile(join(directory, `${concept.id}-wordmark-${theme}.svg`), brand.wordmarkSvg({ conceptId: concept.id, theme, accent: true }));
    }
  }
}
await writeFile(join(directory, 'quantnest-wordmark.svg'), brand.wordmarkSvg());
console.log(`Exported ${brand.concepts.length} symbol/logo/animation sets and the custom wordmark.`);

// Explicit opt-in: exploring another concept must not silently change the application brand.
if (process.argv.includes('--platform')) {
  const platformDirectory = fileURLToPath(new URL('../../frontend/public/brand/', import.meta.url));
  await mkdir(platformDirectory, { recursive: true });
  for (const theme of ['light', 'dark']) {
    for (const animated of [false, true]) {
      await writeFile(join(platformDirectory, `quantnest-${theme}${animated ? '-animated' : ''}.svg`),
        brand.lockupSvg('woven-core', { theme, accent: true, animated, prefix: 'quantnest' }));
    }
  }
  const symbol = brand.symbolSvg('woven-core', { theme: 'dark', accent: true });
  const icon = `<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64"><title>QuantNest</title><rect width="64" height="64" rx="14" fill="#0b1421"/>${symbol.replace('<svg ', '<svg x="2" y="2" width="60" height="60" ')}</svg>`;
  await writeFile(join(platformDirectory, 'favicon.svg'), icon);
  const logo = brand.lockupSvg('woven-core', { theme: 'dark', accent: true });
  const social = `<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630"><title>QuantNest</title><rect width="1200" height="630" fill="#0b1421"/><rect x="40" y="40" width="1120" height="550" rx="24" fill="none" stroke="#283343"/>${logo.replace('<svg ', '<svg x="180" y="239" width="840" height="151.2" ')}</svg>`;
  await writeFile(join(platformDirectory, 'social.svg'), social);
  console.log('Exported approved Woven Core platform SVGs. Regenerate the PNG icons and social image when geometry changes.');
}

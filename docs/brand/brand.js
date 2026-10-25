/* Geometry and export builders shared by the preview and the generated SVGs. */
(() => {
  const shell = 'M20 5H43C51.284 5 58 11.716 58 20V39C58 44.6 55.8 49.6 52.2 52.8L61 61H49L42.8 55H20C11.716 55 5 48.284 5 40V20C5 11.716 11.716 5 20 5Z';
  const counter = 'M18 42V18H24.5L39.5 32.5V18H46V42H39.5L24.5 27.5V42Z';
  const woven = 'M6 59V5H21L44 43V5H58V59H43L20 21V59Z';
  const seam = 'M25.4474 30L33.1053 25L34.9211 28L27.2632 33ZM38.2 51L47 45L49 48L40 54Z';
  const folds = [
    'M32 4L59 20L47 27L32 18L17 27L5 20Z',
    'M5 27L17 34V41L32 50L47 41V34L59 27V47L32 63L5 47Z',
    'M22 31L32 25L42 31V40L32 46L22 40Z',
  ];

  // An asymmetric ribbon and separate seed, drawn for a softer fourth direction.
  const currentRibbon = 'M57 17C52 8 43 4 33 4C16 4 4 17 4 33C4 48 16 59 31 59C41 59 49 55 54 48L61 55V40L44 27L35 33L45 41C42 46 37 49 31 49C21 49 14 42 14 33C14 22 22 14 33 14C41 14 48 18 52 25Z';
  const currentSeed = 'M26 23C28 22 30 23 31 25L34 29L29 33C27 35 24 35 22 32C20 29 23 25 26 23Z';
  // This broad centreline reveals the filled ribbon without changing its contour.
  const currentTrace = 'M54 20C49 10 41 9 33 9C19 9 9 20 9 33C9 45 19 54 31 54C40 54 47 49 50 42L40 32L58 47';

  // One rounded band, repeated by a half-turn. The diagonal gap stays open at small sizes.
  const unionBand = 'M5 38V21C5 12 12 5 21 5H43C52 5 59 12 59 21H47C47 19 45 17 42 17H22C19 17 17 19 17 22V27H31L20 38Z';

  // Two woven sweeps surround a diamond seed. This emblem is independent of the Q.
  const signatureWing = 'M32 3L56 24Q59 27 59 30H46L32 17L18 30H5Q5 27 8 24Z';
  const signatureSeed = 'M32 23L41 32L32 41L23 32Z';
  const signatureMark = (animated = false) => `<g${animated ? ' class="piece piece-one"' : ''}><path d="${signatureWing}"/></g><g transform="rotate(180 32 32)"><g${animated ? ' class="piece piece-one"' : ''}><path d="${signatureWing}"/></g></g><path${animated ? ' class="piece piece-three"' : ''} d="${signatureSeed}"/>`;

  // Two broad bands shelter a small seed, with clear space between all three shapes.
  // Small diagonal breaks stay on the perimeter; no stroke crosses the inner space.
  const coreRibbons = [
    'M23 11C27 5 32 3 37 4L29 18L13 44C11 48 13 50 17 50H27L21 59H17C6 59 1 49 6 39Z',
    'M42 6C43 7 44 8 45 10L60 39C65 49 59 59 48 59H28L34 50H48C52 50 54 47 52 43L36 15Z',
  ];
  // Optical centre of the triangular opening, two units below the original seed.
  const coreSeed = 'M27 42C26 34 31 30 39 30C40 38 35 43 27 42Z';
  const coreMark = (animated = false) => `<g transform="translate(32 32) rotate(18) scale(.94) translate(-32 -32)">${coreRibbons.map((path, index) => `<path${animated ? ` class="core-ribbon core-ribbon-${index}"` : ''} d="${path}"/>`).join('')}<path${animated ? ' class="piece piece-three"' : ''} d="${coreSeed}"/></g>`;

  // A separate, wider mixed-case alphabet. Short square terminals contrast with soft bowls.
  const signatureGlyphs = [
    [9, 'M31 24V36C31 46 26 51 17 51S3 46 3 36V24C3 14 8 9 17 9S31 14 31 24Z'],
    [52, 'M0 23V40Q0 51 11 51Q23 51 23 39V23M23 23V51'],
    [87, 'M24 37Q24 23 12 23Q0 23 0 37Q0 51 12 51Q24 51 24 37ZM24 23V51'],
    [124, 'M0 51V23M0 36Q0 23 12 23Q24 23 24 36V51'],
    [161, 'M6 13V42Q6 51 15 51H19M0 24H19'],
    [192, 'M0 51V10L29 51V10'],
    [233, 'M24 46Q19 51 12 51Q0 51 0 37Q0 23 12 23Q24 23 24 36H0'],
    [269, 'M23 26Q18 22 11 23Q1 23 1 30Q1 35 12 37Q24 39 24 45Q24 52 12 51Q5 51 0 48'],
    [304, 'M6 13V42Q6 51 15 51H19M0 24H19'],
  ];

  function signatureWordmark({ theme, accent, prefix }) {
    const stops = theme === 'dark' ? ['#eed38b', '#d6b15e'] : ['#9a7128', '#805a1b'];
    const gold = accent ? `url(#${prefix}-gold)` : 'currentColor';
    // One gentle colour transition across the entire word, not a metallic stripe per letter.
    const gradient = accent ? `<defs><linearGradient id="${prefix}-gold" gradientUnits="userSpaceOnUse" x1="192" y1="10" x2="323" y2="51">${stops.map((color, index) => `<stop offset="${index * 100}%" stop-color="${color}"/>`).join('')}</linearGradient></defs>` : '';
    const strokes = (entries) => entries.map(([x, path]) => `<path d="${path}" transform="translate(${x} 0)"/>`).join('');
    const outline = (entries, color) => `<g fill="none" stroke="${color}" stroke-width="6.8" stroke-linejoin="round">${strokes(entries)}</g>`;
    // A single masked rectangle gives all four translated letters the same colour progression.
    const nest = accent
      ? `<defs><mask id="${prefix}-nest" maskUnits="userSpaceOnUse" x="188" y="6" width="141" height="51">${outline(signatureGlyphs.slice(5), 'white')}</mask></defs><rect x="188" y="6" width="141" height="51" fill="${gold}" mask="url(#${prefix}-nest)"/>`
      : outline(signatureGlyphs.slice(5), 'currentColor');
    const glyphs = outline(signatureGlyphs.slice(0, 5), 'currentColor') + nest;
    const tail = '<path fill="currentColor" d="M27 41H34L45 55H38Z"/>';
    return `${gradient}<g class="signature-letters">${glyphs}${tail}</g>`;
  }

  // Original single-line lettering. No installed or downloaded font is needed.
  const letters = [
    'M34.5 26V38C34.5 48 29 54 20.25 54S6 48 6 38V26C6 16 11.5 10 20.25 10S34.5 16 34.5 26ZM23.25 42L37.5 57',
    'M45.75 26V43C45.75 50 49.5 54 54.75 54S64.5 50 64.5 42V26M64.5 26V54',
    'M92.25 40C92.25 48 88.5 54 83.25 54S73.5 48 73.5 40S77.25 26 83.25 26S92.25 32 92.25 40ZM92.25 27V54',
    'M102.75 54V27M102.75 39C102.75 31 106.5 26 111.75 26S122.25 32 122.25 40V54',
    'M135 15V45Q135 54 141.75 54H145.5M129.75 27H144.75',
    'M156 54V11L180 54V11',
    'M209.5 48C205.5 54 197.25 56 192.75 50C186.75 42 189.75 28 197.25 26C204.75 24 210.75 30 210.75 40H190.5',
    'M239.25 30C234 24 222.75 25 222.75 34C222.75 43 240 38 240 47C240 56 228 56 222 50',
    'M255 15V45Q255 54 261.75 54H265.5M249.75 27H264.75',
  ];

  const concepts = [
    { id: 'nested-q', number: '01', name: 'Nested Q', tag: 'Monogram',
      line: 'Precision finds a home.',
      summary: 'An N carved into a Q. A compact signature built from the name itself.',
      description: 'The outer Q creates an enclosure; the open space inside forms an N. A deliberate diagonal tail gives the mark its signature. It connects the discipline of “Quant” with the idea of a workspace in “Nest”.',
      motion: 'The enclosure arrives, the N opens within it, then the wordmark settles into place.',
      static: `<path fill-rule="evenodd" d="${shell}${counter}"/>`,
      animated: (prefix) => `<defs><mask id="${prefix}-cut" maskUnits="userSpaceOnUse" x="0" y="0" width="64" height="64"><rect width="64" height="64" fill="white"/><path class="counter" d="${counter}" fill="black"/></mask></defs><g class="piece piece-one"><path d="${shell}" mask="url(#${prefix}-cut)"/></g>`,
    },
    { id: 'woven-n', number: '02', name: 'Woven N', tag: 'Connected',
      line: 'Your process, connected.',
      summary: 'A strong N with two precise seams suggesting interlocking bands.',
      description: 'A freestanding N connects two upright anchors with a continuous diagonal. Small seams introduce the impression of a fold: separate stages brought into one coherent trading process.',
      motion: 'Two clipped sections meet along the diagonal, followed by the complete wordmark.',
      static: `<path fill-rule="evenodd" d="${woven}${seam}"/>`,
      animated: (prefix) => `<defs><clipPath id="${prefix}-left"><path d="M0 0H64V4L0 47Z"/></clipPath><clipPath id="${prefix}-right"><path d="M0 47L64 4V68H0Z"/></clipPath></defs><g class="piece piece-one" clip-path="url(#${prefix}-left)"><path fill-rule="evenodd" d="${woven}${seam}"/></g><g class="piece piece-two" clip-path="url(#${prefix}-right)"><path fill-rule="evenodd" d="${woven}${seam}"/></g>`,
    },
    { id: 'folded-nest', number: '03', name: 'Folded Nest', tag: 'Evolution',
      line: 'An idea, held together.',
      summary: 'Three flat facets shelter a central core, evolving the existing folds.',
      description: 'A folded canopy and an open enclosure surround a small core. This direction carries the faceted character of the current logo into a simpler silhouette with a clearer sense of nesting.',
      motion: 'The enclosure and canopy assemble around the core, then the wordmark appears.',
      static: folds.map((path) => `<path d="${path}"/>`).join(''),
      animated: () => folds.map((path, index) => `<path class="piece piece-${['two', 'one', 'three'][index]}" d="${path}"/>`).join(''),
    },
    { id: 'nest-current', number: '04', name: 'Nest Current', tag: 'Fluid',
      line: 'An idea finds its flow.',
      summary: 'A fluid ribbon shelters a small seed, then opens into a sweeping Q.',
      description: 'A hand-drawn, asymmetric curve wraps around an off-centre seed. Its open mouth and outward sweep suggest a Q without constructing another letter monogram. The seed is the idea; the surrounding current is the process that develops it.',
      motion: 'The ribbon draws around the seed in one continuous gesture, then rests beside the wordmark.',
      static: `<path d="${currentRibbon}"/><path d="${currentSeed}"/>`,
      animated: (prefix) => `<defs><mask id="${prefix}-current" maskUnits="userSpaceOnUse" x="0" y="0" width="64" height="64"><path class="current-trace" d="${currentTrace}" pathLength="1" fill="none" stroke="white" stroke-width="24" stroke-linecap="round" stroke-linejoin="round"/></mask></defs><path d="${currentRibbon}" mask="url(#${prefix}-current)"/><path class="piece piece-three" d="${currentSeed}"/>`,
    },
    { id: 'nest-union', number: '05', name: 'Nest Union', tag: 'Balanced',
      line: 'Independent ideas. One whole.',
      summary: 'Two rounded bands interlock around an open diagonal passage.',
      description: 'One custom shape repeats through a half-turn to create a compact, balanced emblem. Rounded outer corners contrast with precise inner cuts; the open space between the bands hints at an N. It expresses the QuantNest idea of separate tools forming one considered workspace, without relying on a literal trading symbol.',
      motion: 'The two bands approach from opposite corners and settle together. The open diagonal remains visible throughout.',
      static: `<path d="${unionBand}" transform="rotate(90 32 32)"/><path d="${unionBand}" transform="rotate(270 32 32)"/>`,
      // Keep the fixed half-turn outside the animated group so the two motions mirror exactly.
      animated: () => [90, 270].map((angle) => `<g transform="rotate(${angle} 32 32)"><g class="union-band"><path d="${unionBand}"/></g></g>`).join(''),
    },
    { id: 'quantnest-signature', number: '06', name: 'QuantNest Signature', tag: 'Recommended',
      line: 'A signature, woven together.',
      summary: 'A woven seed emblem paired with broad custom lettering and a gold Nest.',
      description: 'Two folded sweeps surround a diamond seed to create an independent favicon. The mixed-case lettering balances soft bowls with crisp terminals. A short, integrated Q tail keeps the first letter clear, while a gentle gold transition across Nest gives the name its signature. Tighter spacing joins the two halves into one word.',
      motion: 'The woven sweeps assemble around the seed while the complete wordmark settles into place. The finished logo stays still.',
      letteringNote: 'Custom vector lettering with its own proportions, broader strokes and two-tone colour. The woven emblem is a separate favicon, not a Q. Turn off Gold accent to inspect the one-colour version.',
      static: signatureMark(),
      animated: () => signatureMark(true),
      wordmark: signatureWordmark,
    },
    { id: 'woven-core', number: '07', name: 'The Woven Core', tag: 'New direction',
      line: 'A place for your next idea.',
      summary: 'A small seed sheltered by a rounded triangle with two precise edge breaks.',
      description: 'Two broad bands form a rounded triangle, tilted slightly off-axis. A small, curved seed sits inside with generous clear space around it: an idea held within a nest. The independent seed adds a focal point without reconnecting the removed centre line. Concept 06’s refined lettering completes the identity.',
      motion: 'The two ribbons approach from opposite diagonals while the seed softly appears inside. The lettering settles alongside them, then everything stays still.',
      letteringNote: 'Uses the refined custom lettering from concept 06, including its integrated Q tail and gentle gold Nest. The independent ribbon-and-seed emblem is also the favicon. The same three filled paths work at every size.',
      static: coreMark(),
      animated: () => coreMark(true),
      wordmark: signatureWordmark,
    },
  ];

  const motionCss = `
    .motion .piece,.motion .lettering{transform-box:fill-box;transform-origin:center;animation:qn-enter 640ms cubic-bezier(.2,.8,.2,1) both}
    .motion .piece-two{animation-name:qn-return;animation-delay:100ms}.motion .piece-three{animation-name:qn-core;animation-delay:220ms}
    .motion .lettering{animation-delay:230ms;animation-duration:540ms}
    .motion .counter{animation:qn-cut 540ms ease-out 140ms both}
    .motion .current-trace{stroke-dasharray:1;animation:qn-draw 780ms cubic-bezier(.35,0,.2,1) both}
    .motion .union-band{animation:qn-union 720ms cubic-bezier(.2,.8,.2,1) both}
    .motion .signature-letters{animation:qn-enter 540ms ease-out both}
    .motion .core-ribbon{animation:qn-weave 720ms cubic-bezier(.2,.8,.2,1) both}
    .motion .core-ribbon-0{--weave-x:-4px;--weave-y:4px}
    .motion .core-ribbon-1{--weave-x:4px;--weave-y:-4px;animation-delay:80ms}
    @keyframes qn-enter{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
    @keyframes qn-return{from{opacity:0;transform:translateY(-6px)}to{opacity:1;transform:translateY(0)}}
    @keyframes qn-core{from{opacity:0;transform:scale(.85)}to{opacity:1;transform:scale(1)}}
    @keyframes qn-cut{from{opacity:0;transform:translateY(5px)}to{opacity:1;transform:translateY(0)}}
    @keyframes qn-draw{from{stroke-dashoffset:1}to{stroke-dashoffset:0}}
    @keyframes qn-union{from{opacity:0;transform:translate(-5px,-5px)}to{opacity:1;transform:translate(0,0)}}
    @keyframes qn-weave{from{opacity:0;transform:translate(var(--weave-x),var(--weave-y))}to{opacity:1;transform:translate(0,0)}}
    @media(prefers-reduced-motion:reduce){.motion .piece,.motion .lettering,.motion .counter,.motion .current-trace,.motion .union-band,.motion .signature-letters,.motion .core-ribbon{animation:none!important}}
  `;
  const wordmark = () => `<g fill="none" stroke="currentColor" stroke-width="5.2" stroke-linecap="round" stroke-linejoin="round">${letters.map((path) => `<path d="${path}"/>`).join('')}</g>`;
  const svg = (body, box, title, color, animated) => `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${box}" role="img" aria-label="${title}"${animated ? ' class="motion"' : ''} style="color:${color}"><title>${title}</title>${animated ? `<style>${motionCss}</style>` : ''}${body}</svg>`;
  const palette = (theme = 'light', accent = false) => ({ ink: theme === 'dark' ? '#f7f7f2' : '#121820', mark: accent ? theme === 'dark' ? '#e4c66b' : '#947023' : 'currentColor' });

  function symbolSvg(id, { theme = 'light', accent = false, animated = false, prefix = id } = {}) {
    const concept = concepts.find((item) => item.id === id);
    const colors = palette(theme, accent);
    return svg(`<g fill="${colors.mark}">${animated ? concept.animated(prefix) : concept.static}</g>`, '0 0 64 64', `QuantNest ${concept.name} symbol`, colors.ink, animated);
  }
  function lockupSvg(id, { theme = 'light', accent = false, animated = false, prefix = id } = {}) {
    const concept = concepts.find((item) => item.id === id);
    const colors = palette(theme, accent);
    const mark = animated ? concept.animated(prefix) : concept.static;
    if (concept.wordmark) {
      const lettering = concept.wordmark({ theme, accent, animated, prefix });
      return svg(`<g transform="translate(4 8) scale(.88)" fill="${colors.mark}">${mark}</g><g transform="translate(68 5)">${lettering}</g>`, '0 0 400 72', `QuantNest ${concept.name} logo`, colors.ink, animated);
    }
    return svg(`<g transform="translate(0 4)" fill="${colors.mark}">${mark}</g><g transform="translate(78 4)"><g class="lettering">${wordmark()}</g></g>`, '0 0 354 72', `QuantNest ${concept.name} logo`, colors.ink, animated);
  }
  function wordmarkSvg({ theme = 'light', accent = false, conceptId, prefix = conceptId } = {}) {
    const concept = concepts.find((item) => item.id === conceptId);
    if (concept?.wordmark) return svg(concept.wordmark({ theme, accent, prefix }), '0 0 333 66', `QuantNest ${concept.name} wordmark`, palette(theme).ink, false);
    return svg(wordmark(), '0 0 274 66', 'QuantNest custom wordmark', palette(theme).ink, false);
  }

  globalThis.QuantNestBrand = { concepts, symbolSvg, lockupSvg, wordmarkSvg };
})();

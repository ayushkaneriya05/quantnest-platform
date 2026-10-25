(() => {
  const brand = globalThis.QuantNestBrand;
  const state = { concept: 'woven-core', theme: 'dark', accent: true };
  const find = (selector) => document.querySelector(selector);
  const motionPreference = window.matchMedia('(prefers-reduced-motion: reduce)');

  find('#concepts').innerHTML = brand.concepts.map((concept) => `<label class="concept"><input type="radio" name="concept" value="${concept.id}" aria-label="${concept.name}" ${concept.id === state.concept ? 'checked' : ''}><span class="concept-meta"><span>${concept.number}</span><span class="concept-tag">${concept.tag}</span></span><span class="concept-symbol">${brand.symbolSvg(concept.id)}</span><span class="concept-signature">${brand.wordmarkSvg({ conceptId: concept.id, accent: true, prefix: `card-${concept.id}` })}</span><span class="concept-title">${concept.name}<span class="selection-dot" aria-hidden="true"></span></span><span class="concept-description">${concept.summary}</span></label>`).join('');

  function replay() {
    find('#motion-logo').innerHTML = brand.lockupSvg(state.concept, { ...state, animated: true, prefix: 'motion' });
    find('#motion-status').textContent = motionPreference.matches ? 'Static version · reduced motion enabled.' : 'One short introduction. Then still.';
    find('#replay').disabled = motionPreference.matches;
  }

  function render() {
    const concept = brand.concepts.find((item) => item.id === state.concept);
    find('#selected-label').textContent = `${concept.number} / ${concept.name.toUpperCase()}`;
    find('#detail-name').textContent = concept.name;
    find('#detail-title').textContent = concept.line;
    find('#detail-description').textContent = concept.description;
    find('#detail-motion').textContent = concept.motion;
    find('#lettering-note').textContent = concept.letteringNote ?? 'The wordmark is drawn as vector paths. The Q tail and open, rounded lettering give the name a shared visual signature.';
    find('#stage').dataset.theme = state.theme;
    document.querySelectorAll('[data-theme][aria-pressed]').forEach((button) => button.setAttribute('aria-pressed', String(button.dataset.theme === state.theme)));
    find('#header-logo').innerHTML = brand.lockupSvg(state.concept, { accent: state.accent, prefix: 'header' });
    find('#sidebar-logo').innerHTML = brand.lockupSvg(state.concept, { accent: state.accent, prefix: 'sidebar' });
    find('#mono-light').innerHTML = brand.lockupSvg(state.concept);
    find('#mono-dark').innerHTML = brand.lockupSvg(state.concept, { theme: 'dark' });
    find('#sizes').innerHTML = [16, 24, 32, 48].map((size) => `<div class="size-item"><div class="size-tile" style="width:${size}px">${brand.symbolSvg(state.concept)}</div><span>${size} px</span></div>`).join('');
    document.querySelectorAll('.size-tile svg').forEach((svg) => { svg.style.width = svg.parentElement.style.width; svg.style.height = svg.parentElement.style.width; });
    replay();
  }

  find('#concepts').addEventListener('change', (event) => { state.concept = event.target.value; render(); });
  document.querySelectorAll('[data-theme][aria-pressed]').forEach((button) => button.addEventListener('click', () => { state.theme = button.dataset.theme; render(); }));
  find('#accent').addEventListener('change', (event) => { state.accent = event.target.checked; render(); });
  find('#replay').addEventListener('click', replay);
  motionPreference.addEventListener('change', replay);

  document.querySelectorAll('[data-download]').forEach((button) => button.addEventListener('click', () => {
    const kind = button.dataset.download;
    const options = { ...state, animated: kind === 'animated', prefix: 'quantnest' };
    const source = kind === 'symbol' ? brand.symbolSvg(state.concept, options) : brand.lockupSvg(state.concept, options);
    const link = document.createElement('a');
    const url = URL.createObjectURL(new Blob([source], { type: 'image/svg+xml;charset=utf-8' }));
    link.href = url;
    link.download = `quantnest-${state.concept}-${kind}-${state.theme}${state.accent ? '-gold' : '-mono'}.svg`;
    document.body.append(link); link.click(); link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }));
  render();
})();

/* ============================================================
   HANZI PERSONAL TRAINER
   ------------------------------------------------------------
   Organizado en capas, de arriba a abajo:

     1. API CLIENT          -> hablar con el backend (FastAPI + SQLite)
     2. ESTADO EN MEMORIA
     3. UTILIDADES
     4. NAVEGACIÓN
     5. INICIO               -> estadísticas + nivel HSK objetivo
     6. AÑADIR                -> buscar por texto / extraer de una foto
     7. TARJETAS               -> flashcards, frases, similares
     8. VOCABULARIO HSK         -> rellenar por lotes niveles ya superados
     9. APUNTES SEMANALES        -> foto de apuntes -> revisar -> guardar
    10. LISTA                     -> buscar/filtrar/editar/borrar
    11. AUTENTICACIÓN              -> login/registro, cada cuenta con su vocabulario
    12. INICIO DE LA APP
============================================================ */


/* ============================================================
   1. API CLIENT
============================================================ */

const API_BASE = '/api';

async function apiRequest(path, options = {}) {
  const res = await fetch(API_BASE + path, options);
  if (!res.ok) {
    let detail = `${res.status}`;
    try {
      const data = await res.json();
      detail = data.detail || JSON.stringify(data);
    } catch (e) { /* respuesta sin JSON */ }
    throw new Error(detail);
  }
  if (res.status === 204) return null;
  return res.json();
}

const apiGet = (path) => apiRequest(path);
const apiPost = (path, body) => apiRequest(path, {
  method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body)
});
const apiPut = (path, body) => apiRequest(path, {
  method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body)
});
const apiDelete = (path) => apiRequest(path, { method: 'DELETE' });
const apiPostForm = (path, formData) => apiRequest(path, { method: 'POST', body: formData });


/* ============================================================
   2. ESTADO EN MEMORIA
============================================================ */

let currentCard = null;   // carácter mostrado ahora en Tarjetas
let revealStage = 0;      // 0 = solo hanzi, 1 = +pinyin, 2 = +traducción


/* ============================================================
   3. UTILIDADES
============================================================ */

function qs(selector, root = document) { return root.querySelector(selector); }
function qsa(selector, root = document) { return [...root.querySelectorAll(selector)]; }

function showError(container, err) {
  container.innerHTML = `<div class="error-box">${err.message || err}</div>`;
}

function clear(container) { container.innerHTML = ''; }

function debounce(fn, ms) {
  let timer;
  return (...args) => { clearTimeout(timer); timer = setTimeout(() => fn(...args), ms); };
}

function hskLabel(level) { return level ? `HSK${level}` : '–'; }

// Gato de la suerte animado, para las esperas a la IA (búsqueda, foto, frases, vocabulario HSK).
function loadingCatHtml(message) {
  return `
    <div class="loading-cat">
      <svg viewBox="0 0 100 100" width="68" height="68" aria-hidden="true">
        <rect x="26" y="90" width="48" height="7" rx="3" fill="#d4af37" stroke="#b8902a" stroke-width="1"/>
        <path d="M20 76 Q8 72 13 58" stroke="#c0392b" stroke-width="3" fill="none" stroke-linecap="round"/>
        <ellipse cx="50" cy="68" rx="26" ry="21" fill="#fff" stroke="#c0392b" stroke-width="2.5"/>
        <ellipse cx="29" cy="76" rx="6.5" ry="10" fill="#fff" stroke="#c0392b" stroke-width="2.5"/>
        <path d="M37 54 Q50 82 63 54 Q57 64 50 60 Q43 64 37 54 Z" fill="#3f9e6b"/>
        <path d="M43 56 Q50 70 57 56 Q53 61 50 59 Q47 61 43 56 Z" fill="#59b885"/>
        <path d="M35 53 Q50 60 65 53" stroke="#c0392b" stroke-width="4" fill="none" stroke-linecap="round"/>
        <circle cx="41" cy="55.5" r="1.3" fill="#fff"/>
        <circle cx="50" cy="58" r="1.3" fill="#fff"/>
        <circle cx="59" cy="55.5" r="1.3" fill="#fff"/>
        <circle cx="50" cy="60" r="3.2" fill="#d4af37" stroke="#b8902a" stroke-width="0.8"/>
        <circle cx="50" cy="36" r="20" fill="#fff" stroke="#c0392b" stroke-width="2.5"/>
        <path d="M32 21 L27 6 L43 17 Z" fill="#fff" stroke="#c0392b" stroke-width="2.5" stroke-linejoin="round"/>
        <path d="M68 21 L73 6 L57 17 Z" fill="#fff" stroke="#c0392b" stroke-width="2.5" stroke-linejoin="round"/>
        <path d="M33 17 L30 9 L39 15 Z" fill="#c0392b"/>
        <path d="M67 17 L70 9 L61 15 Z" fill="#c0392b"/>
        <path d="M38 28 Q40 25 43 26" stroke="#2b2b2b" stroke-width="1.3" fill="none" stroke-linecap="round"/>
        <path d="M62 28 Q60 25 57 26" stroke="#2b2b2b" stroke-width="1.3" fill="none" stroke-linecap="round"/>
        <ellipse cx="41.5" cy="33" rx="2.6" ry="3.2" fill="#2b2b2b"/>
        <ellipse cx="58.5" cy="33" rx="2.6" ry="3.2" fill="#2b2b2b"/>
        <circle cx="42.5" cy="31.5" r="0.8" fill="#fff"/>
        <circle cx="59.5" cy="31.5" r="0.8" fill="#fff"/>
        <path d="M47.5 40 L52.5 40 L50 43.5 Z" fill="#d4af37"/>
        <path d="M50 43 L50 46" stroke="#2b2b2b" stroke-width="1.2"/>
        <path d="M50 46 Q46 49.5 42 47" stroke="#2b2b2b" stroke-width="1.3" fill="none" stroke-linecap="round"/>
        <path d="M50 46 Q54 49.5 58 47" stroke="#2b2b2b" stroke-width="1.3" fill="none" stroke-linecap="round"/>
        <path d="M30 37 L18 35" stroke="#2b2b2b" stroke-width="1" stroke-linecap="round"/>
        <path d="M30 41 L18 42" stroke="#2b2b2b" stroke-width="1" stroke-linecap="round"/>
        <path d="M70 37 L82 35" stroke="#2b2b2b" stroke-width="1" stroke-linecap="round"/>
        <path d="M70 41 L82 42" stroke="#2b2b2b" stroke-width="1" stroke-linecap="round"/>
        <g class="loading-cat-paw" style="transform-origin: 70px 60px;">
          <ellipse cx="70" cy="59" rx="6.5" ry="12" fill="#fff" stroke="#c0392b" stroke-width="2.5"/>
        </g>
      </svg>
      <p class="hint">${message}</p>
    </div>
  `;
}


/* ============================================================
   4. NAVEGACIÓN
============================================================ */

// Menú de dos niveles: categorías arriba (en el header) y, si la categoría
// tiene subapartados, una fila de pestañas secundarias debajo. "Resumen"
// tiene contenido propio (section: 'inicio') además de un subapartado;
// "Añadir Vocabulario" no tiene contenido propio, solo sus 3 subapartados.
const NAV_STRUCTURE = [
  { key: 'tarjetas', label: 'Flash cards', section: 'tarjetas', featured: true },
  {
    key: 'anadir-vocab', label: 'Añadir Vocabulario',
    children: [
      { key: 'anadir', label: 'Manualmente', section: 'anadir' },
      { key: 'apuntes', label: 'Por apuntes', section: 'apuntes' },
      { key: 'vocabulario-hsk', label: 'Automáticamente por nivel HSK', section: 'vocabulario-hsk' },
    ],
  },
  {
    key: 'resumen-cat', label: 'Resumen', section: 'inicio',
    children: [
      { key: 'lista', label: 'Lista de vocabulario aprendido', section: 'lista' },
    ],
  },
];

function subTabsFor(category) {
  const own = category.section ? [{ key: category.key, label: category.label, section: category.section }] : [];
  return [...own, ...(category.children || [])];
}

function categoryForSection(sectionName) {
  return NAV_STRUCTURE.find(cat =>
    cat.section === sectionName || (cat.children || []).some(c => c.section === sectionName)
  ) || NAV_STRUCTURE[0];
}

function showSection(name) {
  qsa('.section').forEach(el => el.classList.toggle('active', el.id === `section-${name}`));

  const category = categoryForSection(name);
  qsa('#main-nav .nav-btn').forEach(btn => btn.classList.toggle('active', btn.dataset.category === category.key));

  const tabs = subTabsFor(category);
  const subNav = qs('#sub-nav');
  if (tabs.length > 1) {
    subNav.innerHTML = tabs.map(t => `
      <button class="sub-nav-btn${t.section === name ? ' active' : ''}" data-section="${t.section}">${t.label}</button>
    `).join('');
    qsa('.sub-nav-btn', subNav).forEach(btn => btn.addEventListener('click', () => showSection(btn.dataset.section)));
    subNav.classList.remove('hidden');
  } else {
    subNav.innerHTML = '';
    subNav.classList.add('hidden');
  }

  if (name === 'inicio') loadStats();
  if (name === 'tarjetas' && !currentCard) loadRandomCard();
  if (name === 'lista') loadList();
}

function initNav() {
  const mainNav = qs('#main-nav');
  mainNav.innerHTML = NAV_STRUCTURE.map(cat =>
    `<button class="nav-btn${cat.featured ? ' nav-btn-featured' : ''}" data-category="${cat.key}">${cat.label}</button>`
  ).join('');
  qsa('.nav-btn', mainNav).forEach(btn => btn.addEventListener('click', () => {
    const category = NAV_STRUCTURE.find(c => c.key === btn.dataset.category);
    showSection(category.section || category.children[0].section);
  }));
}


/* ============================================================
   5. INICIO
============================================================ */

async function loadStats() {
  const grid = qs('#stats-grid');
  try {
    const characters = await apiGet('/characters');
    const byLevel = {};
    let noLevel = 0;
    for (const c of characters) {
      if (c.hskLevel) byLevel[c.hskLevel] = (byLevel[c.hskLevel] || 0) + 1;
      else noLevel += 1;
    }
    const tiles = [`<div class="stat-tile"><div class="value">${characters.length}</div><div class="label">Total</div></div>`];
    for (let level = 1; level <= 6; level++) {
      tiles.push(`<div class="stat-tile"><div class="value">${byLevel[level] || 0}</div><div class="label">HSK${level}</div></div>`);
    }
    tiles.push(`<div class="stat-tile"><div class="value">${noLevel}</div><div class="label">Sin nivel</div></div>`);
    grid.innerHTML = tiles.join('');
  } catch (err) {
    showError(grid, err);
  }

  try {
    const settings = await apiGet('/settings');
    qs('#hsk-level-select').value = String(settings.hskLevel);
  } catch (err) { /* si falla, se queda el valor por defecto del select */ }

  renderUsageCard();
}

function renderUsageCard() {
  const card = qs('#usage-card');
  if (!currentUser || currentUser.isAdmin || !currentUser.usage) {
    card.classList.add('hidden');
    return;
  }
  card.classList.remove('hidden');
  const labels = {
    characters: 'Caracteres guardados', lookups: 'Búsquedas por texto', photos: 'Fotos procesadas',
    hskBatches: 'Cargas de vocabulario HSK', sentences: 'Frases generadas',
  };
  qs('#usage-list').innerHTML = Object.entries(currentUser.usage).map(([key, { used, limit }]) => `
    <p>${labels[key] || key}: <strong>${used} / ${limit}</strong></p>
  `).join('');
}

function initSettings() {
  qs('#hsk-level-select').addEventListener('change', async (e) => {
    try {
      await apiPut('/settings', { hskLevel: parseInt(e.target.value, 10) });
    } catch (err) {
      alert('No se pudo guardar el nivel: ' + err.message);
    }
  });
}


/* ============================================================
   6. AÑADIR
============================================================ */

function suggestionToCharacterIn(cardEl, source) {
  const field = (name) => qs(`[data-field="${name}"]`, cardEl).value.trim();
  const hskRaw = field('hskLevel');
  const radicalsRaw = field('radicals');
  return {
    hanzi: field('hanzi'),
    pinyin: field('pinyin'),
    meaningEs: field('meaningEs'),
    meaningEn: field('meaningEn'),
    hskLevel: hskRaw ? parseInt(hskRaw, 10) : null,
    radicals: radicalsRaw ? radicalsRaw.split(',').map(r => r.trim()).filter(Boolean) : [],
    notes: '',
    source,
  };
}

function renderSuggestionCard(suggestion, source) {
  const card = document.createElement('div');
  card.className = 'card suggestion-card';
  card.innerHTML = `
    <div class="suggestion-field"><label>Hanzi</label><input data-field="hanzi"></div>
    <div class="suggestion-field"><label>Pinyin</label><input data-field="pinyin"></div>
    <div class="suggestion-field"><label>Español</label><input data-field="meaningEs"></div>
    <div class="suggestion-field"><label>Inglés</label><input data-field="meaningEn"></div>
    <div class="suggestion-field"><label>Nivel HSK</label><input data-field="hskLevel" type="number" min="1" max="6"></div>
    <div class="suggestion-field"><label>Radicales</label><input data-field="radicals" placeholder="separados por coma"></div>
    <div class="row">
      <button class="btn-save-suggestion">Guardar</button>
      <button class="secondary btn-discard-suggestion">Descartar</button>
    </div>
  `;
  qs('[data-field="hanzi"]', card).value = suggestion.hanzi || '';
  qs('[data-field="pinyin"]', card).value = suggestion.pinyin || '';
  qs('[data-field="meaningEs"]', card).value = suggestion.meaningEs || '';
  qs('[data-field="meaningEn"]', card).value = suggestion.meaningEn || '';
  qs('[data-field="hskLevel"]', card).value = suggestion.hskLevel || '';
  qs('[data-field="radicals"]', card).value = (suggestion.radicals || []).join(', ');

  qs('.btn-discard-suggestion', card).addEventListener('click', () => card.remove());
  qs('.btn-save-suggestion', card).addEventListener('click', async () => {
    const payload = suggestionToCharacterIn(card, source);
    try {
      await apiPost('/characters', payload);
      card.innerHTML = '<p>✅ Guardado.</p>';
      setTimeout(() => card.remove(), 800);
    } catch (err) {
      alert('No se pudo guardar: ' + err.message);
    }
  });
  return card;
}

function initAnadir() {
  const container = qs('#suggestion-container');

  qs('#btn-lookup').addEventListener('click', async () => {
    const query = qs('#lookup-query').value.trim();
    if (!query) return;
    const btn = qs('#btn-lookup');
    btn.disabled = true;
    const loading = document.createElement('div');
    loading.innerHTML = loadingCatHtml('Buscando…');
    container.prepend(loading);
    try {
      const suggestions = await apiPost('/lookup', { query });
      if (suggestions.length === 0) {
        alert('No se ha encontrado ninguna coincidencia.');
      }
      const group = document.createElement('div');
      if (suggestions.length > 1) {
        const note = document.createElement('p');
        note.className = 'hint';
        note.textContent = `${suggestions.length} caracteres distintos encajan con "${query}" — revisa cuál es el tuyo antes de guardar.`;
        group.appendChild(note);
      }
      suggestions.forEach(s => group.appendChild(renderSuggestionCard(s, 'manual')));
      container.prepend(group);
    } catch (err) {
      const box = document.createElement('div');
      showError(box, err);
      container.prepend(box);
    } finally {
      loading.remove();
      btn.disabled = false;
    }
  });

  qs('#btn-photo-single').addEventListener('click', async () => {
    const input = qs('#photo-single-input');
    if (!input.files[0]) return;
    const formData = new FormData();
    formData.append('file', input.files[0]);
    const btn = qs('#btn-photo-single');
    btn.disabled = true;
    const loading = document.createElement('div');
    loading.innerHTML = loadingCatHtml('Leyendo la foto…');
    container.prepend(loading);
    try {
      const suggestions = await apiPostForm('/photo/extract', formData);
      if (suggestions.length === 0) {
        alert('No se detectó ningún carácter en la foto.');
      }
      suggestions.forEach(s => container.prepend(renderSuggestionCard(s, 'photo')));
    } catch (err) {
      const box = document.createElement('div');
      showError(box, err);
      container.prepend(box);
    } finally {
      loading.remove();
      btn.disabled = false;
    }
  });
}


/* ============================================================
   7. TARJETAS
============================================================ */

function renderCard() {
  revealStage = 0;
  qs('#flashcard-hanzi').textContent = currentCard.hanzi;
  qs('#flashcard-pinyin').textContent = currentCard.pinyin;
  qs('#flashcard-meaning').textContent = currentCard.meaningEs;
  qs('#flashcard-pinyin').classList.add('hidden');
  qs('#flashcard-meaning').classList.add('hidden');
  qs('#sentence-result').classList.add('hidden');
  qs('#similar-result').classList.add('hidden');
  qs('#explain-result').classList.add('hidden');
  qs('#flashcard-familiarity').textContent = `Dominio: ${dominioDots(currentCard.familiarity)}`;
}

function speakHanzi(text) {
  if (!window.speechSynthesis) {
    alert('Tu navegador no soporta la lectura en voz alta.');
    return;
  }
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = 'zh-CN';
  window.speechSynthesis.speak(utterance);
}

async function markCard(known) {
  if (!currentCard) return;
  try {
    await apiPost(`/characters/${currentCard.id}/mark`, { known });
  } catch (err) {
    alert('No se pudo guardar la marca: ' + err.message);
    return;
  }
  loadRandomCard();
}

async function loadRandomCard() {
  try {
    currentCard = await apiGet('/characters/random');
    qs('#flashcard-empty').classList.add('hidden');
    qs('#flashcard-wrap').classList.remove('hidden');
    renderCard();
  } catch (err) {
    currentCard = null;
    qs('#flashcard-wrap').classList.add('hidden');
    qs('#flashcard-empty').classList.remove('hidden');
  }
}

function initTarjetas() {
  qs('#flashcard').addEventListener('click', () => {
    if (revealStage === 0) {
      qs('#flashcard-pinyin').classList.remove('hidden');
      revealStage = 1;
    } else if (revealStage === 1) {
      qs('#flashcard-meaning').classList.remove('hidden');
      revealStage = 2;
    }
  });

  qs('#btn-new-card').addEventListener('click', loadRandomCard);
  qs('#btn-mark-hard').addEventListener('click', () => markCard(false));
  qs('#btn-mark-known').addEventListener('click', () => markCard(true));

  qs('#btn-speak').addEventListener('click', (e) => {
    e.stopPropagation();
    if (currentCard) speakHanzi(currentCard.hanzi);
  });

  qs('#btn-explain').addEventListener('click', async () => {
    const box = qs('#explain-result');
    box.classList.remove('hidden');
    if (currentCard.explanation && currentCard.mnemonic) {
      box.innerHTML = `
        <p>${currentCard.explanation}</p>
        <p class="hint">💡 ${currentCard.mnemonic}</p>
      `;
      return;
    }
    box.innerHTML = loadingCatHtml('Pensando una explicación…');
    try {
      const result = await apiPost(`/characters/${currentCard.id}/explain`, {});
      currentCard.explanation = result.explanation;
      currentCard.mnemonic = result.mnemonic;
      box.innerHTML = `
        <p>${result.explanation}</p>
        <p class="hint">💡 ${result.mnemonic}</p>
      `;
    } catch (err) {
      showError(box, err);
    }
  });

  qs('#btn-generate-sentence').addEventListener('click', async () => {
    const box = qs('#sentence-result');
    box.classList.remove('hidden');
    box.innerHTML = loadingCatHtml('Generando frase…');
    try {
      const result = await apiPost('/sentences/generate', { characterId: currentCard.id });
      const chips = (result.wordsUsed || []).map(w => `<span class="chip">${w}</span>`).join('');
      box.innerHTML = `
        <p style="font-size:22px">${result.hanzi}</p>
        <p class="hint">${result.pinyin}</p>
        <p>${result.translationEs}</p>
        <div>${chips}</div>
      `;
    } catch (err) {
      showError(box, err);
    }
  });

  qs('#btn-show-similar').addEventListener('click', async () => {
    const box = qs('#similar-result');
    box.classList.remove('hidden');
    box.innerHTML = loadingCatHtml('Buscando similares…');
    try {
      const result = await apiGet(`/characters/${currentCard.id}/similar`);
      const byId = {};
      result.byRadical.forEach(group => group.characters.forEach(c => { byId[c.id] = c; }));
      result.byPinyin.forEach(c => { byId[c.id] = c; });

      const radicalLabel = (r, meaning) => meaning ? `${r} <span class="radical-meaning">(${meaning})</span>` : r;
      const chipsHtml = (items) => items.map(
        c => `<span class="chip chip-lg" data-id="${c.id}">${c.hanzi} <small>(${c.pinyin})</small></span>`
      ).join('');

      const targetRadicalsHtml = result.targetRadicals.length
        ? `<p class="similar-heading">Radicales de esta palabra: ${
            result.targetRadicals.map(r => radicalLabel(r.radical, r.meaning)).join(', ')
          }</p>`
        : '';

      const byRadicalHtml = result.byRadical.length
        ? result.byRadical.map(group => `
            <p class="similar-subheading">${radicalLabel(group.radical, group.meaning)}</p>
            <div>${chipsHtml(group.characters)}</div>
          `).join('')
        : '<p class="hint similar-heading">Mismo radical: ninguno todavía.</p>';

      const byPinyinHtml = result.byPinyin.length
        ? `<p class="similar-heading">Mismo pinyin</p><div>${chipsHtml(result.byPinyin)}</div>`
        : '<p class="hint similar-heading">Mismo pinyin: ninguno todavía.</p>';

      box.innerHTML = `
        <div class="card similar-card">
          ${targetRadicalsHtml}
          ${byRadicalHtml}
          ${byPinyinHtml}
        </div>
      `;
      qsa('.chip[data-id]', box).forEach(chip => chip.addEventListener('click', () => {
        currentCard = byId[chip.dataset.id];
        if (currentCard) renderCard();
      }));
    } catch (err) {
      showError(box, err);
    }
  });
}


/* ============================================================
   8. VOCABULARIO HSK (por lotes, para rellenar niveles ya superados)
============================================================ */

let hskBatchRows = [];

function renderHskBatchTable() {
  const container = qs('#hsk-batch-result');
  if (hskBatchRows.length === 0) {
    container.innerHTML = '';
    return;
  }
  const rows = hskBatchRows.map((s, idx) => `
    <tr data-idx="${idx}">
      <td><input type="checkbox" class="hsk-check" checked></td>
      <td><input data-field="hanzi" value="${s.hanzi || ''}"></td>
      <td><input data-field="pinyin" value="${s.pinyin || ''}"></td>
      <td><input data-field="meaningEs" value="${s.meaningEs || ''}"></td>
      <td><input data-field="hskLevel" type="number" min="1" max="6" value="${s.hskLevel || ''}"></td>
      <td><input data-field="radicals" value="${(s.radicals || []).join(', ')}"></td>
    </tr>
  `).join('');
  container.innerHTML = `
    <p class="hint">${hskBatchRows.length} palabras cargadas.</p>
    <table>
      <thead><tr><th></th><th>Hanzi</th><th>Pinyin</th><th>Español</th><th>HSK</th><th>Radicales</th></tr></thead>
      <tbody id="hsk-batch-tbody">${rows}</tbody>
    </table>
    <div class="row">
      <button id="btn-hsk-batch-more" class="secondary">Cargar más</button>
      <button id="btn-hsk-batch-save">Guardar seleccionados</button>
    </div>
  `;
  qs('#btn-hsk-batch-more').addEventListener('click', loadHskBatch);
  qs('#btn-hsk-batch-save').addEventListener('click', saveHskBatchSelected);
}

async function loadHskBatch() {
  const level = parseInt(qs('#hsk-batch-level').value, 10);
  const container = qs('#hsk-batch-result');
  const loading = document.createElement('div');
  loading.innerHTML = loadingCatHtml('Cargando vocabulario de la IA…');
  container.appendChild(loading);
  try {
    const existing = await apiGet('/characters');
    const excludeHanzi = [...new Set([...existing.map(c => c.hanzi), ...hskBatchRows.map(r => r.hanzi)])];
    const batch = await apiPost('/hsk/batch', { level, excludeHanzi });
    if (batch.length === 0 && hskBatchRows.length > 0) {
      alert('La IA no ha devuelto más palabras nuevas de este nivel.');
    }
    hskBatchRows.push(...batch);
    renderHskBatchTable();
  } catch (err) {
    showError(container, err);
  }
}

async function saveHskBatchSelected() {
  const container = qs('#hsk-batch-result');
  const toSave = [];
  qsa('#hsk-batch-tbody tr', container).forEach(row => {
    if (!qs('.hsk-check', row).checked) return;
    const field = (name) => qs(`[data-field="${name}"]`, row).value.trim();
    const hskRaw = field('hskLevel');
    const radicalsRaw = field('radicals');
    toSave.push({
      hanzi: field('hanzi'), pinyin: field('pinyin'), meaningEs: field('meaningEs'),
      meaningEn: '', hskLevel: hskRaw ? parseInt(hskRaw, 10) : null,
      radicals: radicalsRaw ? radicalsRaw.split(',').map(r => r.trim()).filter(Boolean) : [],
      notes: '', source: 'manual',
    });
  });
  if (toSave.length === 0) return;
  try {
    const result = await apiPost('/characters/bulk', toSave);
    hskBatchRows = [];
    const limitNote = result.limitReached
      ? '<p class="hint">⚠️ Has alcanzado el límite de caracteres de esta cuenta, no se guardaron todos.</p>' : '';
    container.innerHTML = `<p>✅ Guardados ${result.inserted}. Omitidos por duplicados: ${result.skipped}.</p>${limitNote}`;
  } catch (err) {
    showError(container, err);
  }
}

function initVocabularioHsk() {
  qs('#btn-hsk-batch-load').addEventListener('click', () => {
    hskBatchRows = [];
    loadHskBatch();
  });
}


/* ============================================================
   9. APUNTES SEMANALES
============================================================ */

function renderNotesTable(suggestions) {
  const container = qs('#notes-result');
  if (suggestions.length === 0) {
    container.innerHTML = '<p class="hint">No se detectó ningún carácter en la foto.</p>';
    return;
  }
  const rows = suggestions.map((s, idx) => `
    <tr data-idx="${idx}">
      <td><input type="checkbox" class="notes-check" checked></td>
      <td><input data-field="hanzi" value="${s.hanzi || ''}"></td>
      <td><input data-field="pinyin" value="${s.pinyin || ''}"></td>
      <td><input data-field="meaningEs" value="${s.meaningEs || ''}"></td>
      <td><input data-field="hskLevel" type="number" min="1" max="6" value="${s.hskLevel || ''}"></td>
      <td><input data-field="radicals" value="${(s.radicals || []).join(', ')}"></td>
    </tr>
  `).join('');
  container.innerHTML = `
    <table>
      <thead><tr><th></th><th>Hanzi</th><th>Pinyin</th><th>Español</th><th>HSK</th><th>Radicales</th></tr></thead>
      <tbody id="notes-tbody">${rows}</tbody>
    </table>
    <div class="row">
      <button id="btn-save-notes">Guardar seleccionados</button>
    </div>
  `;

  qsa('.notes-check', container).forEach(chk => chk.addEventListener('change', (e) => {
    e.target.closest('tr').classList.toggle('notes-row-disabled', !e.target.checked);
  }));

  qs('#btn-save-notes').addEventListener('click', async () => {
    const toSave = [];
    qsa('#notes-tbody tr', container).forEach(row => {
      if (!qs('.notes-check', row).checked) return;
      const field = (name) => qs(`[data-field="${name}"]`, row).value.trim();
      const hskRaw = field('hskLevel');
      const radicalsRaw = field('radicals');
      toSave.push({
        hanzi: field('hanzi'), pinyin: field('pinyin'), meaningEs: field('meaningEs'),
        meaningEn: '', hskLevel: hskRaw ? parseInt(hskRaw, 10) : null,
        radicals: radicalsRaw ? radicalsRaw.split(',').map(r => r.trim()).filter(Boolean) : [],
        notes: '', source: 'photo',
      });
    });
    if (toSave.length === 0) return;
    try {
      const result = await apiPost('/characters/bulk', toSave);
      const limitNote = result.limitReached
        ? '<p class="hint">⚠️ Has alcanzado el límite de caracteres de esta cuenta, no se guardaron todos.</p>' : '';
      container.innerHTML = `<p>✅ Guardados ${result.inserted}. Omitidos por duplicados: ${result.skipped}.</p>${limitNote}`;
    } catch (err) {
      showError(container, err);
    }
  });
}

function initApuntes() {
  qs('#btn-photo-notes').addEventListener('click', async () => {
    const input = qs('#photo-notes-input');
    const files = [...input.files];
    if (files.length === 0) return;
    const container = qs('#notes-result');
    container.innerHTML = loadingCatHtml(files.length > 1 ? `Leyendo foto 1 de ${files.length}…` : 'Leyendo la foto…');
    const messageEl = qs('.loading-cat p', container);

    const allSuggestions = [];
    const failedFiles = [];
    for (let i = 0; i < files.length; i++) {
      if (messageEl && files.length > 1) messageEl.textContent = `Leyendo foto ${i + 1} de ${files.length}…`;
      const formData = new FormData();
      formData.append('file', files[i]);
      try {
        const suggestions = await apiPostForm('/photo/extract', formData);
        allSuggestions.push(...suggestions);
      } catch (err) {
        failedFiles.push(files[i].name);
      }
    }

    if (allSuggestions.length === 0 && failedFiles.length === files.length) {
      showError(container, new Error('No se pudo leer ninguna de las fotos.'));
      return;
    }

    renderNotesTable(allSuggestions);
    if (failedFiles.length > 0) {
      const warning = document.createElement('p');
      warning.className = 'hint';
      warning.textContent = `No se pudieron leer ${failedFiles.length} foto(s): ${failedFiles.join(', ')}.`;
      qs('#notes-result').prepend(warning);
    }
  });
}


/* ============================================================
   10. LISTA
============================================================ */

function dominioDots(familiarity) {
  return '●'.repeat(familiarity) + '○'.repeat(5 - familiarity);
}

function characterRowHtml(c) {
  return `
    <tr data-id="${c.id}">
      <td>${c.hanzi}</td>
      <td>${c.pinyin}</td>
      <td>${c.meaningEs}</td>
      <td>${hskLabel(c.hskLevel)}</td>
      <td>${dominioDots(c.familiarity)}</td>
      <td>${(c.radicals || []).join(', ')}</td>
      <td>${c.source}</td>
      <td>
        <button class="secondary btn-edit">Editar</button>
        <button class="secondary btn-delete">Borrar</button>
      </td>
    </tr>
  `;
}

async function loadList() {
  const tbody = qs('#characters-tbody');
  const search = qs('#search-input').value.trim();
  const hskLevel = qs('#hsk-filter').value;
  const params = new URLSearchParams();
  if (search) params.set('search', search);
  if (hskLevel) params.set('hskLevel', hskLevel);
  try {
    const characters = await apiGet('/characters?' + params.toString());
    tbody.innerHTML = characters.map(characterRowHtml).join('') || '<tr><td colspan="8" class="hint">Sin resultados.</td></tr>';
    qsa('.btn-edit', tbody).forEach(btn => btn.addEventListener('click', (e) => {
      const id = e.target.closest('tr').dataset.id;
      const character = characters.find(c => String(c.id) === id);
      openEditModal(character);
    }));
    qsa('.btn-delete', tbody).forEach(btn => btn.addEventListener('click', async (e) => {
      const id = e.target.closest('tr').dataset.id;
      if (!confirm('¿Borrar este carácter?')) return;
      await apiDelete(`/characters/${id}`);
      loadList();
    }));
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="8"><div class="error-box">${err.message}</div></td></tr>`;
  }
}

function openEditModal(character) {
  const overlay = qs('#edit-modal');
  const body = qs('#edit-modal-body');
  body.innerHTML = `
    <div class="suggestion-field"><label>Hanzi</label><input data-field="hanzi" value="${character.hanzi}"></div>
    <div class="suggestion-field"><label>Pinyin</label><input data-field="pinyin" value="${character.pinyin}"></div>
    <div class="suggestion-field"><label>Español</label><input data-field="meaningEs" value="${character.meaningEs}"></div>
    <div class="suggestion-field"><label>Inglés</label><input data-field="meaningEn" value="${character.meaningEn}"></div>
    <div class="suggestion-field"><label>Nivel HSK</label><input data-field="hskLevel" type="number" min="1" max="6" value="${character.hskLevel || ''}"></div>
    <div class="suggestion-field"><label>Radicales</label><input data-field="radicals" value="${(character.radicals || []).join(', ')}"></div>
    <div class="row">
      <button id="btn-save-edit">Guardar</button>
      <button class="secondary" id="btn-cancel-edit">Cancelar</button>
    </div>
  `;
  overlay.classList.remove('hidden');

  qs('#btn-cancel-edit', body).addEventListener('click', () => overlay.classList.add('hidden'));
  qs('#btn-save-edit', body).addEventListener('click', async () => {
    const payload = suggestionToCharacterIn(body, character.source);
    try {
      await apiPut(`/characters/${character.id}`, payload);
      overlay.classList.add('hidden');
      loadList();
    } catch (err) {
      alert('No se pudo guardar: ' + err.message);
    }
  });
}

function initLista() {
  qs('#search-input').addEventListener('input', debounce(loadList, 300));
  qs('#hsk-filter').addEventListener('change', loadList);
  qs('#edit-modal').addEventListener('click', (e) => { if (e.target.id === 'edit-modal') e.target.classList.add('hidden'); });
}


/* ============================================================
   11. AUTENTICACIÓN
   Cuentas simples (usuario+contraseña); cada persona ve solo su
   propio vocabulario. Mientras no haya sesión, se oculta el resto
   de la app y se muestra el formulario de login/registro.
============================================================ */

let currentUser = null;
let authMode = 'login'; // 'login' | 'signup'

function showAuthOverlay() {
  qs('#app-main').classList.add('hidden');
  qs('#main-nav').classList.add('hidden');
  qs('#sub-nav').classList.add('hidden');
  qs('#auth-status').classList.add('hidden');
  qs('#auth-overlay').classList.remove('hidden');
  qs('#auth-error').innerHTML = '';
}

function hideAuthOverlay() {
  qs('#auth-overlay').classList.add('hidden');
  qs('#app-main').classList.remove('hidden');
  qs('#main-nav').classList.remove('hidden');
  qs('#auth-status').classList.remove('hidden');
}

function setAuthMode(mode) {
  authMode = mode;
  qs('#auth-title').textContent = mode === 'login' ? 'Iniciar sesión' : 'Crear cuenta';
  qs('#btn-auth-submit').textContent = mode === 'login' ? 'Entrar' : 'Crear cuenta';
  qs('#btn-auth-toggle').textContent = mode === 'login'
    ? '¿No tienes cuenta? Crear una' : '¿Ya tienes cuenta? Iniciar sesión';
  qs('#auth-invite-field').classList.toggle('hidden', mode === 'login');
}

async function checkAuth() {
  try {
    currentUser = await apiGet('/auth/me');
    qs('#auth-username-label').textContent = `👤 ${currentUser.username}`;
    hideAuthOverlay();
    return true;
  } catch (err) {
    currentUser = null;
    showAuthOverlay();
    return false;
  }
}

function initAuth() {
  setAuthMode('login');

  qs('#btn-auth-toggle').addEventListener('click', (e) => {
    e.preventDefault();
    setAuthMode(authMode === 'login' ? 'signup' : 'login');
  });

  const submitAuth = async () => {
    const username = qs('#auth-username').value.trim();
    const password = qs('#auth-password').value;
    if (!username || !password) return;
    const path = authMode === 'login' ? '/auth/login' : '/auth/signup';
    const body = { username, password };
    if (authMode === 'signup') body.inviteCode = qs('#auth-invite-code').value.trim();
    try {
      currentUser = await apiPost(path, body);
      qs('#auth-password').value = '';
      qs('#auth-username-label').textContent = `👤 ${currentUser.username}`;
      hideAuthOverlay();
      startApp();
    } catch (err) {
      showError(qs('#auth-error'), err);
    }
  };

  qs('#btn-auth-submit').addEventListener('click', submitAuth);
  qs('#auth-password').addEventListener('keydown', (e) => { if (e.key === 'Enter') submitAuth(); });

  qs('#btn-logout').addEventListener('click', async () => {
    try {
      await apiRequest('/auth/logout', { method: 'POST' });
    } catch (err) { /* da igual, mostramos el login de todas formas */ }
    currentUser = null;
    currentCard = null;
    showAuthOverlay();
  });
}


/* ============================================================
   12. INICIO DE LA APP
============================================================ */

function startApp() {
  initNav();
  initSettings();
  initAnadir();
  initTarjetas();
  initVocabularioHsk();
  initApuntes();
  initLista();
  showSection('tarjetas');
}

async function init() {
  initAuth();
  const authed = await checkAuth();
  if (authed) startApp();
}

document.addEventListener('DOMContentLoaded', init);

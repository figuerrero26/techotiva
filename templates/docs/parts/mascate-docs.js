/* ═══ MASCATE DOCS — JS ═══ */

// ── Navegación ──
function nav(el, id) {
  document.querySelectorAll('.sb-link').forEach(l => l.classList.remove('active'));
  el.classList.add('active');
  const target = document.getElementById(id);
  if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// ── Auto-highlight activo en scroll ──
const sections = document.querySelectorAll('.section[id]');
const navLinks  = document.querySelectorAll('.sb-link');

const observer = new IntersectionObserver(entries => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      const id = entry.target.id;
      navLinks.forEach(l => {
        const match = l.getAttribute('onclick')?.includes("'" + id + "'");
        l.classList.toggle('active', !!match);
      });
    }
  });
}, { rootMargin: '-20% 0px -70% 0px' });

sections.forEach(s => observer.observe(s));

// ── Hacer editables las notas fijas ──
document.querySelectorAll('.nota-body').forEach(el => {
  el.contentEditable = 'true';
});

// ── Changelog interactivo ──
function addChangelog() {
  const dateRaw = document.getElementById('clDate').value;
  const type    = document.getElementById('clType').value;
  const text    = document.getElementById('clText').value.trim();

  if (!text) { document.getElementById('clText').focus(); return; }

  const date = dateRaw || new Date().toISOString().slice(0, 7);

  const tagMap = {
    nuevo:     { cls: 'tag-green',  label: 'nuevo' },
    cambio:    { cls: 'tag-yellow', label: 'cambio' },
    fix:       { cls: 'tag-blue',   label: 'fix' },
    deprecado: { cls: 'tag-rust',   label: 'deprecado' },
  };
  const tag = tagMap[type] || tagMap.nuevo;

  const entry = document.createElement('div');
  entry.className = 'changelog-entry changelog-entry-new';
  entry.innerHTML = `
    <div class="cl-date">${date}</div>
    <div class="cl-desc">
      <span class="cl-tag"><span class="${tag.cls}">${tag.label}</span></span>
      <span contenteditable="true">${text}</span>
      <button class="cl-remove-btn" onclick="this.closest('.changelog-entry').remove()" title="Eliminar">×</button>
    </div>`;

  const list = document.getElementById('changelogList');
  list.insertBefore(entry, list.firstChild);

  document.getElementById('clText').value = '';
  document.getElementById('clText').focus();
}

// ── Notas del equipo interactivas ──
function addNota() {
  const titulo = document.getElementById('notaTitulo').value.trim();
  const cuerpo = document.getElementById('notaCuerpo').value.trim();

  if (!titulo && !cuerpo) { document.getElementById('notaTitulo').focus(); return; }

  const card = document.createElement('div');
  card.className = 'info-card nota-card nota-card-new';
  card.style.marginBottom = '0.75rem';
  card.innerHTML = `
    <div style="display:flex;justify-content:space-between;align-items:flex-start">
      <div class="info-card-label" contenteditable="true">${titulo || 'Nueva nota'}</div>
      <button class="cl-remove-btn" onclick="this.closest('.nota-card').remove()" title="Eliminar">×</button>
    </div>
    <div class="nota-body" contenteditable="true" style="margin-top:0.3rem">${cuerpo || 'Escribir aquí...'}</div>
    <div class="nota-editable-hint">✏️ editar directamente</div>`;

  document.getElementById('notasList').appendChild(card);

  document.getElementById('notaTitulo').value = '';
  document.getElementById('notaCuerpo').value = '';
  document.getElementById('notaTitulo').focus();
}

// ── Atajos de teclado ──
document.addEventListener('DOMContentLoaded', () => {
  const clText = document.getElementById('clText');
  if (clText) clText.addEventListener('keydown', e => {
    if (e.key === 'Enter') { e.preventDefault(); addChangelog(); }
  });

  const notaBody = document.getElementById('notaCuerpo');
  if (notaBody) notaBody.addEventListener('keydown', e => {
    if (e.key === 'Enter' && e.ctrlKey) { e.preventDefault(); addNota(); }
  });
});

// ── Estilos inyectados ──
const docStyles = `

  /* ─ Formularios changelog / notas ─ */
  .cl-form {
    background: var(--surface-mid, #052e18);
    border: 1px solid var(--outline-variant);
    border-radius: var(--radius-md, 14px);
    padding: 0.9rem 1rem;
    margin-bottom: 1.1rem;
  }
  .cl-form-row { display:flex; gap:0.5rem; align-items:center; flex-wrap:wrap; }
  .cl-form-col { display:flex; flex-direction:column; gap:0; }
  .cl-input {
    background: var(--surface-high, #0a3d20);
    border: 1px solid var(--outline-variant);
    border-radius: var(--radius-sm, 8px);
    padding: 0.45rem 0.75rem;
    font-family: 'Be Vietnam Pro', sans-serif;
    font-size: 0.82rem;
    color: var(--on-surface, #e8f5ec);
    outline: none;
    transition: border-color 0.15s;
  }
  .cl-input:focus { border-color: var(--primary); }
  .cl-input::placeholder { color: var(--on-bg-muted); opacity: 0.6; }
  .cl-select { cursor:pointer; padding-right:0.5rem; }
  .cl-input-desc { flex:1; min-width:180px; }
  .cl-textarea { flex:1; min-height:72px; resize:vertical; font-family:'Be Vietnam Pro',sans-serif; font-size:0.82rem; line-height:1.5; width:100%; }
  .cl-add-btn {
    background: var(--primary);
    color: var(--on-primary, #3d2c00);
    border: none;
    border-radius: var(--radius-sm, 8px);
    padding: 0.45rem 0.9rem;
    font-family: 'Be Vietnam Pro', sans-serif;
    font-size: 0.8rem; font-weight: 700;
    cursor: pointer; white-space: nowrap; flex-shrink:0;
    transition: opacity 0.15s;
  }
  .cl-add-btn:hover { opacity: 0.85; }
  .cl-remove-btn {
    background: none; border: none;
    color: var(--on-bg-muted);
    font-size: 1.1rem; cursor: pointer;
    padding: 0 0.2rem; line-height:1;
    opacity: 0.4; flex-shrink:0;
    transition: opacity 0.15s, color 0.15s;
  }
  .cl-remove-btn:hover { opacity:1; color:var(--error); }
  .changelog-entry-new .cl-desc { display:flex; align-items:flex-start; gap:0.4rem; }
  .changelog-entry-new .cl-desc span[contenteditable] { flex:1; }

  .tag-blue   { background:rgba(100,160,255,0.12); color:#7eb8ff; border:1px solid rgba(100,160,255,0.2); border-radius:4px; padding:0.1rem 0.4rem; font-size:0.65rem; font-weight:600; }
  .tag-rust   { background:var(--error-dim,rgba(232,93,58,0.1)); color:var(--error,#e85d3a); border:1px solid rgba(232,93,58,0.2); border-radius:4px; padding:0.1rem 0.4rem; font-size:0.65rem; font-weight:600; }

  /* ─ Notas ─ */
  .nota-card { position:relative; }
  .nota-body { font-size:0.84rem; color:var(--on-bg); margin-top:0.3rem; line-height:1.6; }
  .nota-editable-hint { font-size:0.62rem; color:var(--on-bg-muted); opacity:0.4; margin-top:0.5rem; }
  .nota-card-new { animation: fadeUp 0.25s ease both; }

  /* ─ Ecosistema: grupos ─ */
  .grupos-grid {
    display: grid;
    grid-template-columns: 1fr auto 1fr;
    gap: 1rem;
    align-items: start;
    margin: 1.25rem 0;
  }
  .grupos-arrow {
    font-size: 1.4rem; color: var(--on-bg-muted); opacity:0.5;
    align-self: center; text-align:center; padding-top:2.5rem;
  }
  .grupo-card {
    border-radius: var(--radius-md, 14px);
    border: 1px solid var(--outline-variant);
    overflow: hidden;
  }
  .grupo-card.grupo-ours {
    border-color: var(--primary);
    box-shadow: 0 0 0 1px rgba(246,190,57,0.06), 0 8px 32px rgba(0,0,0,0.18);
  }
  .grupo-card.grupo-ext { opacity: 0.82; }

  .grupo-header {
    display: flex; align-items: center; gap: 0.65rem;
    padding: 0.9rem 1rem 0.75rem;
    border-bottom: 1px solid var(--outline-variant);
    background: var(--surface-mid, #052e18);
  }
  .grupo-icon { font-size:1.3rem; flex-shrink:0; }
  .grupo-name { font-family:'Epilogue',sans-serif; font-weight:700; font-size:0.92rem; color:var(--on-surface); line-height:1.2; }
  .grupo-sub  { font-size:0.67rem; color:var(--on-bg-muted); margin-top:0.1rem; }
  .grupo-header .badge { margin-left:auto; flex-shrink:0; }

  .subequipo-list { padding:0.6rem 0; background:var(--surface-low, #001f10); }
  .subequipo {
    display: flex; gap: 0.7rem;
    padding: 0.65rem 1rem;
    border-left: 2px solid transparent;
    transition: background 0.15s;
  }
  .subequipo:hover { background: rgba(149,212,179,0.03); }
  .subequipo-active { border-left-color:var(--primary); background:rgba(246,190,57,0.04); }

  .seq-dot { width:8px; height:8px; border-radius:50%; flex-shrink:0; margin-top:0.35rem; }
  .seq-primary { background:var(--primary); box-shadow:0 0 6px rgba(246,190,57,0.5); }
  .seq-green   { background:var(--secondary, #95d4b3); }
  .seq-purple  { background:var(--tertiary, #d2bbff); }
  .seq-blue    { background:#7eb8ff; }

  .seq-name { font-size:0.82rem; font-weight:600; color:var(--on-surface); margin-bottom:0.2rem; display:flex; align-items:center; gap:0.4rem; }
  .seq-badge {
    font-size:0.6rem; background:var(--primary-dim); color:var(--primary);
    border:1px solid rgba(246,190,57,0.25); border-radius:999px;
    padding:0.1rem 0.5rem; font-weight:700; text-transform:uppercase; letter-spacing:0.05em;
  }
  .seq-desc { font-size:0.76rem; color:var(--on-bg-muted); line-height:1.5; margin-bottom:0.25rem; }
  .seq-link { font-size:0.71rem; color:var(--on-bg-muted); opacity:0.7; }

  .badge-ext {
    background: var(--surface-high, #0a3d20); color: var(--on-bg-muted, #5f9e78);
    border: 1px solid var(--outline-variant);
    font-size:0.6rem; font-weight:700; padding:0.18rem 0.55rem;
    border-radius:999px; text-transform:uppercase; letter-spacing:0.07em;
  }

  @media (max-width: 680px) {
    .grupos-grid { grid-template-columns:1fr; }
    .grupos-arrow { padding-top:0; transform:rotate(90deg); }
    .cl-form-row { flex-direction:column; align-items:stretch; }
    .cl-add-btn { width:100%; }
  }

  @keyframes fadeUp {
    from { opacity:0; transform:translateY(6px); }
    to   { opacity:1; transform:translateY(0); }
  }
`;

const styleEl = document.createElement('style');
styleEl.textContent = docStyles;
document.head.appendChild(styleEl);

// ── Estilos adicionales para la sección de backend ──
const backendStyles = `
  .method.put { background: rgba(100,160,255,0.12); color: #7eb8ff; }
  .method.del { background: var(--error-dim, rgba(232,93,58,0.1)); color: var(--error, #e85d3a); }

  .schemas-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.75rem;
    margin: 0.75rem 0 1.2rem;
  }
  @media (max-width: 640px) {
    .schemas-grid { grid-template-columns: 1fr; }
  }
`;
const bkStyleEl = document.createElement('style');
bkStyleEl.textContent = backendStyles;
document.head.appendChild(bkStyleEl);

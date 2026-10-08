/* ═══ MASCATE — MIS SEGUIMIENTOS JS (rol: prescriptor) ═══ */
const API = window.location.origin;
MASCATE.guardAuth();

let _todos = [];

window.addEventListener('DOMContentLoaded', async () => {
  renderSidebar(MASCATE.nombre, MASCATE.email);

  try {
    _todos = await fetch(API + '/prescriptores/seguimientos', MASCATE.authGet()).then(r => r.json());
  } catch(e) {
    console.error(e);
    _todos = [];
  }

  poblarFiltroPersona();
  renderStats();
  renderLista(_todos);

  document.getElementById('btn-filtrar')?.addEventListener('click', aplicarFiltro);
  document.getElementById('btn-limpiar')?.addEventListener('click', limpiarFiltro);
});

function poblarFiltroPersona() {
  const sel = document.getElementById('filtro-persona');
  if (!sel) return;
  const nombres = [...new Set(_todos.map(s => s.nombre_beneficiario).filter(Boolean))].sort();
  nombres.forEach(n => {
    const opt = document.createElement('option');
    opt.value = n; opt.textContent = n;
    sel.appendChild(opt);
  });
}

function renderStats() {
  const ahora = new Date();
  const mesActual = ahora.getFullYear() + '-' + String(ahora.getMonth() + 1).padStart(2, '0');
  const delMes = _todos.filter(s => s.fecha && s.fecha.startsWith(mesActual));
  const personasDistintas = new Set(_todos.map(s => s.beneficiario_id)).size;

  set('stat-total',   _todos.length);
  set('stat-personas', personasDistintas);
  set('stat-mes',     delMes.length);
}

function aplicarFiltro() {
  const persona = document.getElementById('filtro-persona')?.value || '';
  const tipo    = document.getElementById('filtro-tipo')?.value || '';
  const filtrados = _todos.filter(s =>
    (!persona || s.nombre_beneficiario === persona) &&
    (!tipo    || s.tipo_registro === tipo)
  );
  renderLista(filtrados);
}

function limpiarFiltro() {
  const selP = document.getElementById('filtro-persona');
  const selT = document.getElementById('filtro-tipo');
  if (selP) selP.value = '';
  if (selT) selT.value = '';
  renderLista(_todos);
}

function renderLista(segs) {
  const lista = document.getElementById('lista-seguimientos');
  const countLabel = document.getElementById('count-label');
  if (!lista) return;

  if (countLabel) {
    countLabel.textContent = segs.length;
    countLabel.style.display = segs.length ? 'inline-block' : 'none';
  }

  if (!segs.length) {
    lista.innerHTML = '<div style="color:var(--on-bg-muted);font-size:0.85rem;padding:0.5rem">No hay registros con los filtros seleccionados.</div>';
    return;
  }

  lista.innerHTML = segs.map(s => {
    const fecha = s.fecha ? new Date(s.fecha).toLocaleDateString('es-ES', { day:'2-digit', month:'short', year:'numeric' }) : '—';
    const tipo  = s.tipo_registro || 'Registro';
    return `
      <div style="padding:0.75rem 0;border-bottom:1px solid var(--border)">
        <div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.3rem">
          <span style="font-size:0.85rem;font-weight:600">${campo(s.nombre_beneficiario)}</span>
          <span class="tag mustard" style="font-size:0.7rem">${tipo}</span>
          <span style="font-size:0.75rem;color:var(--on-bg-muted);margin-left:auto">${fecha}</span>
        </div>
        ${s.nombre_prescriptor ? `<div style="font-size:0.78rem;color:var(--on-bg-muted);margin-bottom:0.25rem">👤 Prescriptxr: ${s.nombre_prescriptor}</div>` : ''}
        ${s.observaciones ? `<div style="font-size:0.82rem;color:var(--on-bg-muted);white-space:pre-wrap;word-break:break-word;line-height:1.5">${s.observaciones}</div>` : ''}
      </div>`;
  }).join('');
}

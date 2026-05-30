/* ═══ MASCATE — MAPA JS ═══ */
const API = window.location.origin;
MASCATE.guardAuth();

let todosDisps = [];

window.addEventListener('DOMContentLoaded', async () => {
  renderSidebar(MASCATE.nombre, MASCATE.email);

  try {
    todosDisps = await (await fetch(API + '/dispositivos/')).json();

    const activos = todosDisps.filter(d => d.activo !== false);
    const zonas   = new Set(todosDisps.map(d => d.ubicacion?.split(',')[0]?.trim()).filter(Boolean)).size;
    const benefs  = todosDisps.reduce((s, d) => s + (d.num_beneficiarios ?? 0), 0);

    set('mapa-stat-total',  activos.length || todosDisps.length);
  if (MASCATE.rol !== 'beneficiario') {
    const cardBenefs = document.getElementById('card-benefs');
    if (cardBenefs) cardBenefs.style.display = '';
    set('mapa-stat-benefs', benefs || '—');
  }
    set('mapa-stat-zonas',  zonas || '—');
    if (MASCATE.rol !== 'beneficiario') set('mapa-stat-benefs', benefs || '—');

    renderDisps(todosDisps);
  } catch(e) {
    console.error('Error:', e);
    document.getElementById('mapa-grid').innerHTML =
      '<div style="color:var(--error);padding:1rem">Error al cargar dispositivos.</div>';
  }

  // Filtros
  document.getElementById('mapa-search')?.addEventListener('input', aplicarFiltros);
  document.getElementById('mapa-tipo')?.addEventListener('change', aplicarFiltros);
});

function aplicarFiltros() {
  const q    = (document.getElementById('mapa-search')?.value ?? '').toLowerCase();
  const tipo = document.getElementById('mapa-tipo')?.value ?? '';
  renderDisps(todosDisps.filter(d => {
    const txt  = (d.nombre + d.ubicacion + d.tipo_servicio).toLowerCase();
    const matchQ = txt.includes(q);
    const matchT = !tipo || d.tipo_servicio === tipo;
    return matchQ && matchT;
  }));
}

function renderDisps(lista) {
  const grid = document.getElementById('mapa-grid');
  if (!grid) return;
  if (!lista.length) {
    grid.innerHTML = '<div style="color:var(--on-bg-muted);font-size:0.85rem;padding:1rem">Sin dispositivos encontrados.</div>';
    return;
  }
  grid.innerHTML = lista.map(d => {
    const color = TAG_COLOR[d.tipo_servicio] ?? 'mustard';
    const bg    = BG_DIM[color] ?? 'var(--primary-dim)';
    return `<div class="panel" style="cursor:pointer" onclick="verDetalle(${d.id})">
      <div style="display:flex;align-items:center;gap:1rem;margin-bottom:0.75rem">
        <div class="list-avatar" style="width:3rem;height:3rem;font-size:1.1rem;flex-shrink:0;background:${bg}">
          ${d.tipo_servicio === 'Artístico' ? '🎨'
          : d.tipo_servicio === 'Deportivo' ? '⚽'
          : d.tipo_servicio === 'Cultural'  ? '🎵'
          : d.tipo_servicio === 'Ambiental' ? '🌿'
          : d.tipo_servicio === 'Educativo' ? '📚'
          : d.tipo_servicio === 'Centro de escucha' ? '💬' : '🏘️'}
        </div>
        <div style="flex:1">
          <div style="font-weight:700;font-size:1rem">${campo(d.nombre)}</div>
          ${d.tipo_servicio ? `<span class="tag ${color}" style="font-size:0.7rem">${d.tipo_servicio}</span>` : ''}
        </div>
      </div>
      <div style="display:flex;flex-direction:column;gap:0.3rem;font-size:0.82rem;color:var(--on-bg-muted)">
        ${d.ubicacion ? `<span>📍 ${d.ubicacion}</span>` : ''}
        ${d.dia_actividad ? `<span>🕓 ${d.dia_actividad}${d.hora_actividad?' · '+d.hora_actividad:''}</span>` : ''}
        ${d.telefono ? `<span>📞 ${d.telefono}</span>` : ''}
      </div>
      <div style="margin-top:0.75rem;display:flex;justify-content:flex-end">
        <button class="btn btn-sm btn-outline">Ver detalle →</button>
      </div>
    </div>`;
  }).join('');
}

function verDetalle(id) {
  const d = todosDisps.find(x => x.id === id);
  if (!d) return;
  const color = TAG_COLOR[d.tipo_servicio] ?? 'mustard';
  document.getElementById('modal-disp-content').innerHTML = `
    <div class="panel-head" style="margin-bottom:1rem">
      <span class="panel-title">${campo(d.nombre)}</span>
      ${d.tipo_servicio ? `<span class="tag ${color}">${d.tipo_servicio}</span>` : ''}
    </div>
    <div style="display:flex;flex-direction:column;gap:0.6rem;margin-bottom:1.25rem">
      ${infoRow('Ubicación',    d.ubicacion)}
      ${infoRow('Horario',      d.dia_actividad ? d.dia_actividad + (d.hora_actividad?' · '+d.hora_actividad:'') : null)}
      ${infoRow('Teléfono',     d.telefono)}
      ${infoRow('Redes',        d.redes_sociales)}
      ${infoRow('Lugar',        d.lugar_actividades)}
    </div>
    <button class="btn btn-sm btn-green" style="width:100%"
      onclick="window.location.href='/notificaciones'">✉️ Contactar dispositivo</button>`;
  document.getElementById('modal-disp-detalle').style.display = 'flex';
}

// Cerrar modal al click fuera
document.getElementById('modal-disp-detalle')?.addEventListener('click', e => {
  if (e.target === document.getElementById('modal-disp-detalle'))
    document.getElementById('modal-disp-detalle').style.display = 'none';
});

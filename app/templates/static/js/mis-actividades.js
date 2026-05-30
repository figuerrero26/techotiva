/* ═══ MASCATE — MIS ACTIVIDADES JS ═══ */
const API = window.location.origin;
MASCATE.guardAuth();

window.addEventListener('DOMContentLoaded', async () => {
  renderSidebar(MASCATE.nombre, MASCATE.email);

  try {
    const acts = await (await fetch(API + '/beneficiarios/mis-actividades', MASCATE.authGet())).json();
    const activas = acts.filter(a => a.activa !== false).length;
    const tipos   = new Set(acts.map(a => a.tipo)).size;

    set('stat-total',  acts.length);
    set('stat-activas', activas);
    set('stat-tipos',   tipos);

    const grid = document.getElementById('mis-acts-grid');
    if (!grid) return;
    if (!acts.length) {
      grid.innerHTML = `<div class="panel span-3" style="text-align:center;padding:2rem">
        <div style="font-size:2rem;margin-bottom:0.5rem">📭</div>
        <div style="font-weight:600;margin-bottom:0.25rem">Aún no estás inscritx en actividades</div>
        <div style="color:var(--on-bg-muted);font-size:0.85rem;margin-bottom:1rem">Explora lo que hay disponible en tu territorio</div>
        <button class="btn btn-sm btn-green" onclick="window.location.href='/actividades'">🔍 Buscar actividades</button>
      </div>`;
      return;
    }
    grid.innerHTML = acts.map(a => {
      const color = TAG_COLOR[a.tipo] ?? 'mustard';
      const bg    = BG_DIM[color]    ?? 'var(--primary-dim)';
      return `<div class="panel">
        <div style="height:4rem;background:${bg};border-radius:var(--radius-md);
                    display:flex;align-items:center;justify-content:center;
                    font-size:1.75rem;margin-bottom:1rem">${a.emoji||'📅'}</div>
        <div class="panel-head">
          <span class="panel-title">${campo(a.nombre)}</span>
          <span class="tag ${color}">${campo(a.tipo)}</span>
        </div>
        ${a.descripcion ? `<p style="font-size:0.82rem;color:var(--on-bg-muted);margin:0.4rem 0 0.6rem">${a.descripcion}</p>` : ''}
        <div style="display:flex;flex-direction:column;gap:0.3rem;font-size:0.78rem;color:var(--on-bg-muted);margin-bottom:0.75rem">
          <span>📍 ${campo(a.lugar)}</span>
          <span>🕓 ${campo(a.dia_semana)} · ${campo(a.hora)}</span>
          ${a.cupo_maximo ? `<span>👥 Cupo: ${a.cupo_maximo}</span>` : ''}
          ${a.fecha_inicio ? `<span>🗓 Desde: ${new Date(a.fecha_inicio).toLocaleDateString('es-CO')}</span>` : ''}
        </div>
      </div>`;
    }).join('');
  } catch(e) {
    console.error('Error:', e);
    document.getElementById('mis-acts-grid').innerHTML =
      '<div style="color:var(--error);padding:1rem">Error al cargar actividades.</div>';
  }
});

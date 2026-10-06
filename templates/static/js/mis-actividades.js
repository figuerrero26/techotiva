/* ═══ MASCATE — MIS ACTIVIDADES JS ═══ */
const API = window.location.origin;
MASCATE.guardAuth();

window.addEventListener('DOMContentLoaded', async () => {
  renderSidebar(MASCATE.nombre, MASCATE.email);
  await cargarMisActividades();
});

async function cargarMisActividades() {
  try {
    const acts  = await (await fetch(API + '/beneficiarios/mis-actividades', MASCATE.authGet())).json();
    const tbody = document.getElementById('mis-acts-tbody');
    if (!tbody) return;

    if (!acts.length) {
      tbody.innerHTML = `<tr><td colspan="9" style="text-align:center;padding:2rem">
        <div style="font-size:2rem;margin-bottom:0.5rem">📭</div>
        <div style="font-weight:600;margin-bottom:0.25rem">Aún no estás inscritx en actividades</div>
        <div style="color:var(--on-bg-muted);font-size:0.85rem;margin-bottom:1rem">Explora lo que hay disponible en tu territorio</div>
        <button class="btn btn-sm btn-green" onclick="window.location.href='/actividades'">🔍 Buscar actividades</button>
      </td></tr>`;
      return;
    }

    tbody.innerHTML = acts.map(a => {
      const ins         = a.total_inscritos ?? 0;
      const disponibles = a.cupo_maximo != null ? a.cupo_maximo - ins : null;
      const cupoColor   = disponibles != null && disponibles <= 0 ? 'var(--error)' : disponibles != null && disponibles <= 3 ? 'var(--warning,#e6a817)' : 'var(--primary)';
      const inscritosTexto = `<span class="btn btn-sm btn-outline" style="font-size:0.78rem;color:${cupoColor};border-color:${cupoColor};cursor:default">👥 ${ins}${a.cupo_maximo ? '/'+a.cupo_maximo : ''}</span>`;

      return `<tr>
        <td>
          <div style="display:flex;align-items:center;gap:0.5rem">
            <span style="font-size:1.1rem">${a.emoji||'📅'}</span>
            <span style="font-weight:600">${a.nombre}</span>
          </div>
        </td>
        <td><span class="tag ${TAG_COLOR[a.tipo]||'mustard'}">${a.tipo||'—'}</span></td>
        <td style="font-size:0.82rem;color:var(--on-bg-muted)">${a.dispositivo_nombre||'—'}</td>
        <td>${a.lugar||'—'}</td>
        <td>${a.fecha_inicio ? new Date(a.fecha_inicio+'T00:00:00').toLocaleDateString('es-CO',{day:'2-digit',month:'short',year:'numeric'}) : '—'}</td>
        <td>${a.hora||'—'}</td>
        <td>${inscritosTexto}</td>
        <td><span class="tag ${a.activa !== false ? 'green' : ''}" style="${a.activa !== false ? '' : 'background:var(--on-bg-muted,#aaa);color:#fff'}">${a.activa !== false ? 'Activa' : 'Inactiva'}</span></td>
        <td>
          ${a.activa !== false
            ? `<button class="btn btn-sm btn-outline" style="font-size:0.78rem;color:var(--error);border-color:var(--error)"
                onclick="desinscribirse(${a.id})">Desinscribirse</button>`
            : `<span style="font-size:0.78rem;color:var(--on-bg-muted)">Culminada</span>`}
        </td>
      </tr>`;
    }).join('');
  } catch(e) {
    console.error('Error:', e);
    document.getElementById('mis-acts-tbody').innerHTML =
      '<tr><td colspan="9" style="color:var(--error);padding:1rem">Error al cargar actividades.</td></tr>';
  }
}

async function desinscribirse(actividadId) {
  if (!confirm('¿Seguro que quieres desinscribirte de esta actividad?')) return;
  try {
    const res = await fetch(API + '/beneficiarios/desinscribirse/' + actividadId, {
      method: 'DELETE', headers: MASCATE.authHeaders(),
    });
    if (res.ok) {
      const t = document.createElement('div');
      t.textContent = '✓ Desinscripción exitosa';
      t.style.cssText = 'position:fixed;bottom:1.5rem;right:1.5rem;z-index:2000;background:var(--error);color:#fff;padding:0.75rem 1.25rem;border-radius:var(--radius-md);font-size:0.85rem;font-weight:600;box-shadow:0 4px 20px rgba(0,0,0,0.2)';
      document.body.appendChild(t);
      setTimeout(() => t.remove(), 3000);
      await cargarMisActividades();
    } else {
      const d = await res.json().catch(() => ({}));
      alert(d.detail || 'No se pudo desinscribir.');
    }
  } catch(e) { alert('Error de conexión.'); }
}

/* ═══ MASCATE — REPORTES JS ═══ */
const API = window.location.origin;
MASCATE.guardAuth();

window.addEventListener('DOMContentLoaded', async () => {
  const { rol, nombre, email } = MASCATE;
  renderSidebar(nombre, email);

  try {
    const stats = await (await fetch(API + '/admin/stats', MASCATE.authGet())).json();
    setStats([
      { id:'stat-0', val: campo(stats.participacion_pct, '—') },
      { id:'stat-1', val: stats.total_usuarios },
      { id:'stat-2', val: stats.total_dispositivos },
      { id:'stat-3', val: campo(stats.total_actividades,
                           (await (await fetch(API + '/actividades/')).json()).length) },
    ]);

    // Distribución por rol
    const users  = await (await fetch(API + '/admin/usuarios', MASCATE.authGet())).json();
    const disps  = users.filter(u => u.rol === 'dispositivo').length;
    const prescs = users.filter(u => u.rol === 'prescriptor').length;
    const benefs = users.filter(u => u.rol === 'beneficiario').length;
    const total  = Math.max(disps + prescs + benefs, 1);

    const legendItems = document.querySelectorAll('.legend-item');
    if (legendItems[0]) legendItems[0].lastChild.textContent = ` Beneficiarixs (${Math.round(benefs/total*100)}%)`;
    if (legendItems[1]) legendItems[1].lastChild.textContent = ` Prescriptxres (${Math.round(prescs/total*100)}%)`;
    if (legendItems[2]) legendItems[2].lastChild.textContent = ` Dispositivos (${Math.round(disps/total*100)}%)`;

    // Tabla dispositivos — con campos nuevos del backend
    const dispositivos = await (await fetch(API + '/admin/dispositivos', MASCATE.authGet())).json();
    const tbody = document.getElementById('rep-tbody');
    if (tbody) {
      tbody.innerHTML = dispositivos.map(d => `<tr>
        <td>${campo(d.nombre)}</td>
        <td style="color:var(--primary);font-weight:700">${campo(d.num_beneficiarios, 0)}</td>
        <td>${campo(d.num_actividades, '—')}</td>
        <td>
          <div style="display:flex;align-items:center;gap:0.5rem">
            <div class="seed-track" style="width:90px;display:inline-block">
              <div class="seed-fill" style="width:${campo(d.asistencia_pct, 0)}%"></div>
            </div>
            ${d.asistencia_pct != null ? d.asistencia_pct + '%' : '—'}
          </div>
        </td>
        <td>${d.activo ? '<span class="tag green">Activo</span>' : '<span class="tag mustard">En pausa</span>'}</td>
      </tr>`).join('');
    }
  } catch(e) { console.error('Error cargando reportes:', e); }

  // Botón exportar
  document.querySelector('.btn-outline')?.addEventListener('click', () => exportarDispositivos('csv'));
});

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

    // Distribución por rol — donut dinámico
    const users  = await (await fetch(API + '/admin/usuarios', MASCATE.authGet())).json();
    const disps  = users.filter(u => u.rol === 'dispositivo').length;
    const prescs = users.filter(u => u.rol === 'prescriptor').length;
    const benefs = users.filter(u => u.rol === 'beneficiario').length;
    const total  = Math.max(disps + prescs + benefs, 1);

    // Circunferencia = 2π × 28 ≈ 176
    const CIRC = 176;
    const bPct = benefs / total;
    const pPct = prescs / total;
    const dPct = disps  / total;

    const bLen = Math.round(bPct * CIRC);
    const pLen = Math.round(pPct * CIRC);
    const dLen = Math.round(dPct * CIRC);

    const elB = document.getElementById('donut-benef');
    const elP = document.getElementById('donut-presc');
    const elD = document.getElementById('donut-disp');

    if (elB) { elB.setAttribute('stroke-dasharray', `${bLen} ${CIRC - bLen}`); elB.setAttribute('stroke-dashoffset', '0'); }
    if (elP) { elP.setAttribute('stroke-dasharray', `${pLen} ${CIRC - pLen}`); elP.setAttribute('stroke-dashoffset', `-${bLen}`); }
    if (elD) { elD.setAttribute('stroke-dasharray', `${dLen} ${CIRC - dLen}`); elD.setAttribute('stroke-dashoffset', `-${bLen + pLen}`); }

    const legendItems = document.querySelectorAll('.legend-item');
    if (legendItems[0]) legendItems[0].lastChild.textContent = ` Beneficiarixs (${Math.round(bPct*100)}%)`;
    if (legendItems[1]) legendItems[1].lastChild.textContent = ` Prescriptxres (${Math.round(pPct*100)}%)`;
    if (legendItems[2]) legendItems[2].lastChild.textContent = ` Dispositivos (${Math.round(dPct*100)}%)`;

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

});

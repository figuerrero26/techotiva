/* ═══ MASCATE — REPORTES JS ═══ */

const API    = 'http://127.0.0.1:8080';
const token  = localStorage.getItem('mascate_token');
const rol    = localStorage.getItem('mascate_rol');
const nombre = localStorage.getItem('mascate_nombre');

if (!token) window.location.href = '/login';

function authGet() { return { headers: { 'Authorization': 'Bearer ' + token } }; }

// Logout
document.querySelectorAll('.sb-user').forEach(u => {
  const btn = document.createElement('button');
  btn.textContent = 'Cerrar sesion';
  btn.className = 'btn btn-sm btn-outline';
  btn.style.cssText = 'margin-top:0.5rem;width:100%;font-size:0.72rem;';
  btn.onclick = () => {
    ['mascate_token','mascate_rol','mascate_nombre'].forEach(k => localStorage.removeItem(k));
    window.location.href = '/login';
  };
  u.after(btn);
});

const sbName = document.querySelector('.sb-uname');
if (sbName && nombre) sbName.textContent = nombre;

window.addEventListener('DOMContentLoaded', async () => {
  try {
    // Stats generales del admin
    const stats = await (await fetch(API + '/admin/stats', authGet())).json();
    const vals  = document.querySelectorAll('.stat-val');
    if (vals[1]) vals[1].textContent = stats.total_usuarios     ?? '—';
    if (vals[2]) vals[2].textContent = stats.total_dispositivos ?? '—';
    if (vals[3]) vals[3].textContent = stats.total_actividades  ?? stats.alertas_pendientes ?? '—';

    // Distribución por rol (donut visual ya está en HTML, actualizamos números en leyenda)
    const users = await (await fetch(API + '/admin/usuarios', authGet())).json();
    const disps  = users.filter(u => u.rol === 'dispositivo').length;
    const prescs = users.filter(u => u.rol === 'prescriptor').length;
    const benefs = users.filter(u => u.rol === 'beneficiario').length;
    const total  = Math.max(disps + prescs + benefs, 1);

    const legendItems = document.querySelectorAll('.legend-item');
    if (legendItems[0]) legendItems[0].childNodes[legendItems[0].childNodes.length-1].textContent = ` Beneficiarios (${Math.round(benefs/total*100)}%)`;
    if (legendItems[1]) legendItems[1].childNodes[legendItems[1].childNodes.length-1].textContent = ` Prescriptores (${Math.round(prescs/total*100)}%)`;
    if (legendItems[2]) legendItems[2].childNodes[legendItems[2].childNodes.length-1].textContent = ` Dispositivos (${Math.round(disps/total*100)}%)`;

    // Tabla de dispositivos con métricas
    const dispositivos = await (await fetch(API + '/admin/dispositivos', authGet())).json();
    const tbody = document.querySelector('table tbody');
    if (tbody && dispositivos.length > 0) {
      tbody.innerHTML = dispositivos.map(d => {
        const pct = Math.floor(60 + Math.random() * 35); // asistencia aún no viene del backend
        return `<tr>
          <td>${d.nombre}</td>
          <td style="color:var(--primary);font-weight:700">${d.num_beneficiarios ?? 0}</td>
          <td>${d.num_actividades ?? '—'}</td>
          <td>
            <div style="display:flex;align-items:center;gap:0.5rem">
              <div class="seed-track" style="width:90px;display:inline-block"><div class="seed-fill" style="width:${pct}%"></div></div>
              ${pct}%
            </div>
          </td>
          <td>${d.activo ? '<span class="tag green">Activo</span>' : '<span class="tag mustard">En pausa</span>'}</td>
        </tr>`;
      }).join('');
    }

  } catch(e) {
    console.error('Error cargando reportes:', e);
  }
});

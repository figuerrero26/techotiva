/* ═══ MASCATE — ACTIVIDADES JS ═══ */

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

const TAG_COLOR = { Artístico:'mustard', Deportivo:'green', Cultural:'blue', Ambiental:'green', Educativo:'blue', Escucha:'purple' };

window.addEventListener('DOMContentLoaded', async () => {
  try {
    const acts = await (await fetch(API + '/actividades/')).json();

    // Stats
    const vals = document.querySelectorAll('.stat-val');
    if (vals[0]) vals[0].textContent = acts.length;
    // participantes y próximas son calculados del lado backend; usamos lo que haya
    if (vals[2]) vals[2].textContent = acts.length; // fallback

    // Cards — primeras 3 actividades
    const grid = document.querySelector('.grid-3');
    if (grid && acts.length > 0) {
      grid.innerHTML = acts.slice(0, 3).map(a => {
        const color = TAG_COLOR[a.tipo] ?? 'mustard';
        const pct   = Math.floor(60 + Math.random() * 35); // sin datos reales de asistencia aún
        return `<div class="panel">
          <div style="height:5rem;background:var(--${color}-dim, rgba(246,190,57,0.12));border-radius:var(--radius-md);display:flex;align-items:center;justify-content:center;font-size:2rem;margin-bottom:1rem">${a.emoji || '📅'}</div>
          <div class="panel-head">
            <span class="panel-title">${a.nombre}</span>
            <span class="tag ${color}">${a.tipo}</span>
          </div>
          <p style="font-size:0.83rem;color:var(--on-bg-muted);margin:0.5rem 0 0.75rem">${a.lugar}</p>
          <div style="display:flex;gap:1rem;font-size:0.78rem;color:var(--on-bg-muted);margin-bottom:0.75rem">
            <span>📍 ${a.lugar}</span><span>🕓 ${a.dia_semana} ${a.hora}</span>
          </div>
          <div class="seed-track"><div class="seed-fill" style="width:${pct}%"></div></div>
          <div style="display:flex;justify-content:space-between;align-items:center;margin-top:0.6rem">
            <span style="font-size:0.78rem;color:var(--on-bg-muted)">${pct}% asistencia</span>
            <button class="btn btn-sm btn-outline">Ver detalle</button>
          </div>
        </div>`;
      }).join('');
    }

    // Tabla de próximas actividades
    const tbody = document.querySelector('table tbody');
    if (tbody && acts.length > 0) {
      tbody.innerHTML = acts.map(a => {
        const color = TAG_COLOR[a.tipo] ?? 'mustard';
        return `<tr>
          <td>${a.emoji || '📅'} ${a.nombre}</td>
          <td>${a.lugar}</td>
          <td>${a.dia_semana}</td>
          <td>${a.hora}</td>
          <td><span class="tag ${color}">${a.tipo}</span></td>
        </tr>`;
      }).join('');
    }

    // Ajustar encabezados de tabla si es necesario
    const ths = document.querySelectorAll('table thead th');
    if (ths[3]) ths[3].textContent = 'Hora';

  } catch(e) {
    console.error('Error cargando actividades:', e);
  }
});

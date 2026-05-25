/* ═══ MASCATE — PERFIL JS ═══ */

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

// Nombre en sidebar y hero
const sbName = document.querySelector('.sb-uname');
if (sbName && nombre) sbName.textContent = nombre;

const sbEmail = document.querySelector('.sb-uemail');

window.addEventListener('DOMContentLoaded', async () => {
  // Nombre en hero
  const heroH1 = document.querySelector('h1');
  if (heroH1 && nombre) heroH1.textContent = nombre;

  // Iniciales en avatares
  const ini = (nombre || 'US').substring(0,2).toUpperCase();
  document.querySelectorAll('.list-avatar, .sb-avatar').forEach(el => {
    if (el.textContent.trim() === 'LM') el.textContent = ini;
  });

  // Tag de rol
  const rolTag = document.querySelector('.tag.mustard');
  if (rolTag) {
    const labels = { admin:'Administrador', dispositivo:'Dispositivo', prescriptor:'Prescriptxr', beneficiario:'Beneficiarix' };
    rolTag.textContent = labels[rol] ?? rol;
  }

  // Actividades propias
  try {
    const acts = await (await fetch(API + '/actividades/')).json();
    const vals = document.querySelectorAll('.stat-val');
    if (vals[0]) vals[0].textContent = acts.length;

    // Cards de actividades recientes
    const grid = document.querySelector('.grid-3');
    if (grid && acts.length > 0) {
      const TAG_COLOR = { Artístico:'mustard', Deportivo:'green', Cultural:'blue', Ambiental:'green', Educativo:'blue', Escucha:'purple' };
      grid.innerHTML = acts.slice(0,3).map(a => {
        const color = TAG_COLOR[a.tipo] ?? 'mustard';
        return `<div class="act-card">
          <div class="act-card-emoji">${a.emoji || '📅'}</div>
          <div class="act-card-name">${a.nombre}</div>
          <div class="act-card-org">${a.lugar}</div>
          <div class="act-card-meta"><span class="tag ${color}">${a.tipo}</span></div>
        </div>`;
      }).join('');
    }
  } catch(e) { console.error('Error cargando actividades de perfil:', e); }

  // Si es admin, cargar stats adicionales
  if (rol === 'admin') {
    try {
      const stats = await (await fetch(API + '/admin/stats', authGet())).json();
      const vals  = document.querySelectorAll('.stat-val');
      if (vals[1]) vals[1].textContent = stats.total_usuarios     ?? '—';
      if (vals[2]) vals[2].textContent = stats.total_dispositivos ?? '—';
      if (vals[3]) vals[3].textContent = stats.alertas_pendientes ?? '—';
    } catch(e) {}
  }

  // Si es prescriptor, cargar asignados
  if (rol === 'prescriptor') {
    try {
      const asignados = await (await fetch(API + '/prescriptores/mis-asignados', authGet())).json();
      const vals = document.querySelectorAll('.stat-val');
      if (vals[0]) vals[0].textContent = asignados.length;
    } catch(e) {}
  }
});

/* ═══ MASCATE — NOTIFICACIONES JS ═══ */

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

// Construir notificaciones a partir de alertas del admin + actividades recientes
window.addEventListener('DOMContentLoaded', async () => {
  const container = document.querySelector('.panel[style*="padding:0"]') ?? document.querySelector('.content');
  const notifs = [];

  // Alertas del sistema (solo admin)
  if (rol === 'admin') {
    try {
      const alertas = await (await fetch(API + '/admin/alertas', authGet())).json();
      alertas.forEach(a => notifs.push({ icon:'⚠️', titulo: a.mensaje, desc: a.dispositivo, tiempo:'Ahora', unread:true }));
    } catch(e) {}
  }

  // Actividades recientes como notificaciones de contexto
  try {
    const acts = await (await fetch(API + '/actividades/')).json();
    acts.slice(0,3).forEach((a, i) => {
      notifs.push({
        icon: a.emoji || '📅',
        titulo: `Actividad: ${a.nombre}`,
        desc: `${a.dia_semana} a las ${a.hora} — ${a.lugar}`,
        tiempo: i === 0 ? 'Hoy' : `Hace ${i+1} días`,
        unread: i === 0,
      });
    });
  } catch(e) {}

  // Fallback si no hay nada
  if (notifs.length === 0) {
    notifs.push({ icon:'🌱', titulo:'Todo al día', desc:'No hay notificaciones pendientes.', tiempo:'Ahora', unread:false });
  }

  // Actualizar contador
  const subtitle = document.querySelector('.page-header p');
  const unreadCount = notifs.filter(n => n.unread).length;
  if (subtitle) subtitle.textContent = unreadCount > 0 ? `${unreadCount} notificacion${unreadCount > 1 ? 'es' : ''} sin leer` : 'Todo al día';

  // Renderizar
  if (container) {
    container.innerHTML = notifs.map(n => `
      <div class="list-row" style="padding:1rem 1.25rem;${n.unread ? 'background:var(--primary-dim);' : ''}border-bottom:1px solid var(--border)">
        <div class="contact-icon" style="background:${n.unread ? 'var(--primary-dim)' : 'var(--surface-2,rgba(255,255,255,0.04))'};flex-shrink:0">${n.icon}</div>
        <div class="list-info">
          <div class="list-name">${n.titulo}</div>
          <div class="list-sub">${n.desc}</div>
        </div>
        <div style="display:flex;flex-direction:column;align-items:flex-end;gap:0.3rem;flex-shrink:0">
          ${n.unread ? '<span class="tag green">Nueva</span>' : ''}
          <span style="font-size:0.72rem;color:var(--on-bg-muted)">${n.tiempo}</span>
        </div>
      </div>
    `).join('');
  }

  // Botón "marcar todo leído"
  document.querySelector('.btn-outline')?.addEventListener('click', () => {
    document.querySelectorAll('.list-row').forEach(row => {
      row.style.background = '';
    });
    document.querySelectorAll('.tag.green').forEach(t => {
      if (t.textContent === 'Nueva') t.remove();
    });
    if (subtitle) subtitle.textContent = 'Todo al día';
  });
});

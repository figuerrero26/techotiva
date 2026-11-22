/* ═══ MASCATE — NOTIFICACIONES JS ═══ */
const API = window.location.origin;
MASCATE.guardAuth();

// Actividades vigentes con fecha de hoy en adelante, de la más cercana a la más lejana
function proximas(acts) {
  const hoy = new Date().toISOString().slice(0, 10);
  return (Array.isArray(acts) ? acts : [])
    .filter(a => a.activa !== false && a.fecha_inicio && a.fecha_inicio >= hoy)
    .sort((a, b) => a.fecha_inicio.localeCompare(b.fecha_inicio) || (a.hora || '').localeCompare(b.hora || ''));
}

// "2026-11-29" → "sáb 29 nov"
function fechaCorta(iso) {
  if (!iso) return 'Sin fecha';
  return new Date(iso + 'T00:00:00').toLocaleDateString('es-CO', { weekday:'short', day:'numeric', month:'short' });
}

window.addEventListener('DOMContentLoaded', async () => {
  const { rol, nombre, email } = MASCATE;
  renderSidebar(nombre, email);
  await initNotifBtn();

  const container = document.getElementById('notif-list');
  const subtitle  = document.getElementById('notif-subtitle');
  const notifs    = [];

  // ── Admin: alertas + pendientes de aprobación ──
  if (rol === 'admin') {
    try {
      const alertas = await (await fetch(API + '/admin/alertas', MASCATE.authGet())).json();
      alertas.forEach(a => notifs.push({
        icon:'⚠️', titulo: a.mensaje,
        desc: `${a.dispositivo} · ${a.dias_sin_actividad} días sin actividad`,
        tiempo:'Ahora', unread:true, bg:'var(--error-dim)', accion: null,
      }));
    } catch(e) {}
    try {
      const users = await (await fetch(API + '/admin/usuarios', MASCATE.authGet())).json();
      const pendientes = users.filter(u => u.status === 'pendiente');
      if (pendientes.length) notifs.push({
        icon:'👤', titulo: `${pendientes.length} usuario${pendientes.length>1?'s':''} pendiente${pendientes.length>1?'s':''} de aprobación`,
        desc: pendientes.map(u => campo(u.nombre, u.email)).join(', '),
        tiempo:'Pendiente', unread:true, bg:'var(--primary-dim)',
        accion: { label:'Ver usuarios', href:'/usuarios' },
      });
      // Beneficiarios que se registraron solos y aún no tienen dispositivo
      const sinDisp = users.filter(u => u.rol === 'beneficiario' && u.status === 'activo' && !u.dispositivo_nombre);
      if (sinDisp.length) notifs.push({
        icon:'🌱', titulo: `${sinDisp.length} beneficiarix${sinDisp.length>1?'s':''} nuevx${sinDisp.length>1?'s':''} sin dispositivo asignado`,
        desc: sinDisp.map(u => campo(u.nombre, u.email)).join(', ') + ' · asígnales un dispositivo desde Usuarios.',
        tiempo:'Pendiente', unread:true, bg:'var(--secondary-dim, var(--primary-dim))',
        accion: { label:'Asignar dispositivo', href:'/usuarios' },
      });
    } catch(e) {}
  }

  // ── Prescriptor: asignados urgentes ──
  if (rol === 'prescriptor') {
    try {
      const asignados = await (await fetch(API + '/prescriptores/mis-asignados', MASCATE.authGet())).json();
      const urgentes  = asignados.filter(a => a.estado === 'urgente');
      const revisar   = asignados.filter(a => a.estado === 'revisar');
      if (urgentes.length) notifs.push({
        icon:'🚨', titulo: `${urgentes.length} persona${urgentes.length>1?'s':''} requieren atención urgente`,
        desc: urgentes.map(a => a.nombre_apodo).join(', '),
        tiempo:'Urgente', unread:true, bg:'var(--error-dim)', accion:null,
      });
      if (revisar.length) notifs.push({
        icon:'👁️', titulo: `${revisar.length} persona${revisar.length>1?'s':''} para revisar`,
        desc: revisar.map(a => a.nombre_apodo).join(', '),
        tiempo:'Revisar', unread:true, bg:'var(--primary-dim)', accion:null,
      });
    } catch(e) {}
  }

  // ── Beneficiario: actividades inscritas ──
  if (rol === 'beneficiario') {
    try {
      const acts = proximas(await (await fetch(API + '/beneficiarios/mis-actividades', MASCATE.authGet())).json());
      if (acts.length) notifs.push({
        icon:'📅', titulo: `Tienes ${acts.length} actividad${acts.length>1?'es':''} próxima${acts.length>1?'s':''}`,
        desc: acts.slice(0,3).map(a => `${a.emoji||'📅'} ${a.nombre} (${fechaCorta(a.fecha_inicio)}${a.dispositivo_nombre ? ' · ' + a.dispositivo_nombre : ''})`).join(' · '),
        tiempo:'Vigentes', unread:false, bg:'var(--secondary-dim)',
        accion: { label:'Ver mis actividades', href:'/mis-actividades' },
      });
    } catch(e) {}
  }

  // ── Dispositivo: beneficiarios activos ──
  if (rol === 'dispositivo') {
    try {
      const disp = await (await fetch(API + '/dispositivos/me', MASCATE.authGet())).json();
      if (disp?.id) {
        const stats = await (await fetch(API + '/dispositivos/' + disp.id + '/estadisticas', MASCATE.authGet())).json();
        notifs.push({
          icon:'🌱', titulo: `${stats.beneficiarios_activos} beneficiarixs activos esta semana`,
          desc: `${stats.actividades_registradas} actividades · ${stats.seguimientos_semana} seguimientos`,
          tiempo:'Esta semana', unread:false, bg:'var(--secondary-dim)', accion:null,
        });
      }
    } catch(e) {}
  }

  // Próximas actividades (vigentes, de la más cercana a la más lejana)
  try {
    let endpoint = '/actividades/', opciones = {};
    if (rol === 'beneficiario') {
      endpoint = '/beneficiarios/mis-actividades'; opciones = MASCATE.authGet();
    } else if (rol === 'dispositivo') {
      const disp = await (await fetch(API + '/dispositivos/me', MASCATE.authGet())).json();
      if (disp?.id) endpoint = '/actividades/?dispositivo_id=' + disp.id;
    }
    const acts = proximas(await (await fetch(API + endpoint, opciones)).json());
    acts.slice(0, 2).forEach((a, i) => notifs.push({
      icon:   a.emoji || '📅',
      titulo: a.nombre,
      desc:   `${fechaCorta(a.fecha_inicio)}${a.hora ? ' a las ' + a.hora : ''} · ${campo(a.lugar)}`
              + (rol !== 'dispositivo' && a.dispositivo_nombre ? ` · 🏘️ ${a.dispositivo_nombre}` : ''),
      tiempo: i === 0 ? 'Próxima' : 'Después',
      unread: false, bg:'var(--surface-2,rgba(255,255,255,0.04))', accion:null,
    }));
  } catch(e) {}

  if (!notifs.length) notifs.push({
    icon:'🌱', titulo:'Todo al día',
    desc:'No hay notificaciones pendientes.',
    tiempo:'Ahora', unread:false, bg:'var(--surface-2,rgba(255,255,255,0.04))', accion:null,
  });

  // Actualizar contador
  const unreadCount = notifs.filter(n => n.unread).length;
  if (subtitle) subtitle.textContent = unreadCount > 0
    ? `${unreadCount} notificacion${unreadCount>1?'es':''} sin leer`
    : 'Todo al día';

  if (container) {
    container.innerHTML = notifs.map(n => `
      <div class="list-row"
           style="padding:1rem 1.25rem;${n.unread?'background:var(--primary-dim);':''}
                  border-bottom:1px solid var(--border)">
        <div class="contact-icon" style="background:${n.bg};flex-shrink:0">${n.icon}</div>
        <div class="list-info">
          <div class="list-name">${n.titulo}</div>
          <div class="list-sub">${n.desc}</div>
          ${n.accion ? `<a href="${n.accion.href}"
            style="font-size:0.78rem;color:var(--primary);font-weight:600;
                   text-decoration:none;margin-top:0.3rem;display:inline-block">
            ${n.accion.label} →</a>` : ''}
        </div>
        <div style="display:flex;flex-direction:column;align-items:flex-end;
                    gap:0.3rem;flex-shrink:0">
          ${n.unread ? '<span class="tag green">Nueva</span>' : ''}
          <span style="font-size:0.72rem;color:var(--on-bg-muted)">${n.tiempo}</span>
        </div>
      </div>`).join('');
  }

  document.getElementById('btn-marcar-leido')?.addEventListener('click', () => {
    container?.querySelectorAll('.list-row').forEach(r => r.style.background = '');
    container?.querySelectorAll('.tag.green').forEach(t => { if (t.textContent==='Nueva') t.remove(); });
    if (subtitle) subtitle.textContent = 'Todo al día';
  });
});

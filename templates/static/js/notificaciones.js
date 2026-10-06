/* ═══ MASCATE — NOTIFICACIONES JS ═══ */
const API = window.location.origin;
MASCATE.guardAuth();

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
      const acts = await (await fetch(API + '/beneficiarios/mis-actividades', MASCATE.authGet())).json();
      if (acts.length) notifs.push({
        icon:'📅', titulo: `Tienes ${acts.length} actividad${acts.length>1?'es':''} inscrita${acts.length>1?'s':''}`,
        desc: acts.slice(0,3).map(a => `${a.emoji||'📅'} ${a.nombre}`).join(' · '),
        tiempo:'Activas', unread:false, bg:'var(--secondary-dim)',
        accion: { label:'Ver actividades', href:'/actividades' },
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

  // Actividades recientes como contexto para todos
  try {
    const endpoint = rol === 'beneficiario'
      ? '/beneficiarios/mis-actividades'
      : '/actividades/';
    const acts = await (await fetch(API + endpoint, rol === 'beneficiario' ? MASCATE.authGet() : {})).json();
    acts.slice(0, 2).forEach((a, i) => notifs.push({
      icon:   a.emoji || '📅',
      titulo: a.nombre,
      desc:   `${campo(a.dia_semana)} a las ${campo(a.hora)} · ${campo(a.lugar)}`,
      tiempo: i === 0 ? 'Próxima' : 'Próximamente',
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

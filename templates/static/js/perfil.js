/* ═══ MASCATE — PERFIL JS ═══ */
/* Requiere: /static/js/mascate-utils.js */

const API = window.location.origin;
MASCATE.guardAuth();

window.addEventListener('DOMContentLoaded', async () => {
  const { rol, nombre, email } = MASCATE;

  renderSidebar(nombre, email);

  // ══ BENEFICIARIO ══
  if (rol === 'beneficiario') {
    try {
      const me   = await (await fetch(API + '/beneficiarios/me', MASCATE.authGet())).json();
      const acts = await (await fetch(API + '/beneficiarios/mis-actividades', MASCATE.authGet())).json();

      renderSidebar(me.nombre_apodo, me.email);
      set('hero-avatar',  ini(me.nombre_apodo));
      set('hero-nombre',  me.nombre_apodo);
      set('hero-rol',     ROL_LABELS[rol]);
      set('hero-desc',    campo(me.descripcion, 'Participante del colectivo MASCATE.'));

      setStats([
        { id:'stat-0', val: acts.length,                         lbl:'Actividades',  icon:'📅' },
        { id:'stat-1', val: campo(me.asistencia_pct, '—'),       lbl:'Asistencia',   icon:'✅' },
        { id:'stat-2', val: acts.filter(a=>a.activa).length||'—',lbl:'Activas',      icon:'⭐' },
        { id:'stat-3', val: campo(me.progreso, '—'),             lbl:'Progreso',     icon:'🎯' },
      ]);

      // Info personal — renderInfoGrid muestra solo lo que el back manda
      renderInfoGrid('info-grid', me, rol, rol);

      // Contacto — prescriptor asignado si el back lo manda
      const contactoList = document.getElementById('contacto-list');
      if (contactoList) {
        let html = '';
        if (me.prescriptor_nombre) html += `<div class="list-row">
          <div class="contact-icon" style="background:var(--primary-dim)">👩‍🏫</div>
          <div class="list-info"><div class="list-name">${me.prescriptor_nombre}</div>
          <div class="list-sub">Prescriptxr asignado</div></div></div>`;
        if (me.dispositivo_nombre) html += `<div class="list-row">
          <div class="contact-icon" style="background:var(--secondary-dim)">🏢</div>
          <div class="list-info"><div class="list-name">${me.dispositivo_nombre}</div>
          <div class="list-sub">Organización vinculada</div></div></div>`;
        contactoList.innerHTML = html || '<div style="color:var(--on-bg-muted);font-size:0.85rem;padding:0.5rem">Sin contactos asignados aún.</div>';
      }

      renderActCards('acts-grid', acts);
    } catch(e) { console.error('Error perfil beneficiario:', e); }
  }

  // ══ PRESCRIPTOR ══
  else if (rol === 'prescriptor') {
    try {
      const asignados = await (await fetch(API + '/prescriptores/mis-asignados', MASCATE.authGet())).json();
      const segs      = await (await fetch(API + '/prescriptores/seguimientos',   MASCATE.authGet())).json();
      const acts      = await (await fetch(API + '/actividades/')).json();

      set('hero-avatar', ini(nombre)); set('hero-nombre', nombre);
      set('hero-rol', ROL_LABELS[rol]); set('hero-desc', '');

      setStats([
        { id:'stat-0', val: asignados.length,                                   lbl:'Asignados',    icon:'👥' },
        { id:'stat-1', val: segs.length,                                         lbl:'Seguimientos', icon:'📋' },
        { id:'stat-2', val: asignados.filter(a=>a.estado==='urgente').length,   lbl:'Urgentes',     icon:'⚠️' },
        { id:'stat-3', val: asignados.filter(a=>a.estado==='al_dia').length,    lbl:'Al día',       icon:'✅' },
      ]);

      renderInfoGrid('info-grid', { nombre_completo: nombre, email }, rol, rol);

      // Asignados como contactos
      const contactoList = document.getElementById('contacto-list');
      if (contactoList) {
        contactoList.innerHTML = asignados.slice(0,3).map(a => `
          <div class="list-row">
            <div class="contact-icon" style="background:var(--secondary-dim)">🌱</div>
            <div class="list-info">
              <div class="list-name">${a.nombre_apodo}</div>
              <div class="list-sub">${a.estado === 'urgente' ? '⚠️ Requiere atención' : 'Al día'}</div>
            </div>
            <span class="tag ${a.estado==='urgente'?'rust':a.estado==='revisar'?'mustard':'green'}">${a.estado}</span>
          </div>`).join('') || '<div style="color:var(--on-bg-muted);font-size:0.85rem;padding:0.5rem">Sin asignados.</div>';
      }
      set('contacto-titulo', 'Personas asignadas');
      renderActCards('acts-grid', acts);
    } catch(e) { console.error('Error perfil prescriptor:', e); }
  }

  // ══ DISPOSITIVO ══
  else if (rol === 'dispositivo') {
    try {
      const disps = await (await fetch(API + '/dispositivos/', MASCATE.authGet())).json();
      const d     = disps[0];
      if (!d) return;
      const stats = await (await fetch(API + '/dispositivos/' + d.id + '/estadisticas', MASCATE.authGet())).json();
      const acts  = await (await fetch(API + '/actividades/?dispositivo_id=' + d.id)).json();

      renderSidebar(d.nombre, email);
      set('hero-avatar', ini(d.nombre)); set('hero-nombre', d.nombre);
      set('hero-rol', ROL_LABELS[rol]);
      set('hero-desc', campo(d.descripcion, campo(d.tipo_servicio, '')));

      setStats([
        { id:'stat-0', val: stats.beneficiarios_activos,   lbl:'Beneficiarixs', icon:'🌱' },
        { id:'stat-1', val: stats.actividades_registradas, lbl:'Actividades',   icon:'📅' },
        { id:'stat-2', val: stats.seguimientos_semana,     lbl:'Seguimientos',  icon:'📋' },
        { id:'stat-3', val: campo(d.capacidad, '—'),       lbl:'Capacidad',     icon:'👥' },
      ]);

      renderInfoGrid('info-grid', d, rol, rol);

      const contactoList = document.getElementById('contacto-list');
      if (contactoList) {
        contactoList.innerHTML = `
          <div class="list-row"><div class="contact-icon" style="background:var(--primary-dim)">📍</div>
            <div class="list-info"><div class="list-name">${campo(d.ubicacion)}</div><div class="list-sub">Sede</div></div></div>
          <div class="list-row"><div class="contact-icon" style="background:var(--secondary-dim)">📞</div>
            <div class="list-info"><div class="list-name">${campo(d.telefono)}</div><div class="list-sub">Teléfono</div></div></div>
          ${d.redes_sociales ? `<div class="list-row"><div class="contact-icon" style="background:var(--tertiary-dim,var(--primary-dim))">📱</div>
            <div class="list-info"><div class="list-name">${d.redes_sociales}</div><div class="list-sub">Redes sociales</div></div></div>` : ''}`;
      }
      set('contacto-titulo', 'Información de contacto');
      renderActCards('acts-grid', acts);
    } catch(e) { console.error('Error perfil dispositivo:', e); }
  }

  // ══ ADMIN ══
  else if (rol === 'admin') {
    try {
      const stats = await (await fetch(API + '/admin/stats', MASCATE.authGet())).json();
      const acts  = await (await fetch(API + '/actividades/')).json();

      set('hero-avatar', ini(nombre)); set('hero-nombre', nombre || 'Administrador MASCATE');
      set('hero-rol', ROL_LABELS[rol]); set('hero-desc', 'Administración del sistema MASCATE.');

      setStats([
        { id:'stat-0', val: stats.total_usuarios,      lbl:'Usuarios',      icon:'👥' },
        { id:'stat-1', val: stats.total_dispositivos,  lbl:'Dispositivos',  icon:'🏘️' },
        { id:'stat-2', val: stats.total_prescriptores, lbl:'Prescriptxres', icon:'🎯' },
        { id:'stat-3', val: stats.alertas_pendientes,  lbl:'Alertas',       icon:'⚠️' },
      ]);

      renderInfoGrid('info-grid', { email, rol: 'admin' }, rol, rol);

      const contactoList = document.getElementById('contacto-list');
      if (contactoList) {
        contactoList.innerHTML = `
          <div class="list-row"><div class="contact-icon" style="background:var(--primary-dim)">📊</div>
            <div class="list-info"><div class="list-name">${stats.total_usuarios} usuarios registrados</div><div class="list-sub">Total sistema</div></div></div>
          <div class="list-row"><div class="contact-icon" style="background:var(--error-dim)">⚠️</div>
            <div class="list-info"><div class="list-name">${stats.alertas_pendientes} alertas pendientes</div><div class="list-sub">Requieren atención</div></div></div>`;
      }
      set('contacto-titulo', 'Estado del sistema');
      renderActCards('acts-grid', acts);
    } catch(e) { console.error('Error perfil admin:', e); }
  }
});

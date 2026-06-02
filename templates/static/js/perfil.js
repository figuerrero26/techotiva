/* ═══ MASCATE — PERFIL JS ═══ */
/* Requiere: /static/js/mascate-utils.js */

const API = window.location.origin;
MASCATE.guardAuth();

// ── Modal de detalle de actividad (disponible en todas las vistas) ────────
// verDetalleAct vive en actividades.js pero perfil.js lo necesita también.
// Lo definimos aquí sin botones de editar/eliminar (el prescriptor solo lee).
window.verDetalleAct = function verDetalleAct(act) {
  if (!act) return;

  document.getElementById('det-nombre').textContent      = campo(act.nombre);
  document.getElementById('det-tipo').textContent        = campo(act.tipo);
  document.getElementById('det-tipo').className          = 'tag ' + (TAG_COLOR[act.tipo] ?? 'mustard');
  document.getElementById('det-descripcion').textContent = act.descripcion ?? '';

  const grid = document.getElementById('det-grid');
  if (grid) {
    grid.innerHTML = [
      { lbl: '📍 Lugar', val: act.lugar },
      { lbl: '🕓 Día',   val: act.dia_semana },
      { lbl: '⏰ Hora',  val: act.hora },
      { lbl: '👥 Cupo',  val: act.cupo_maximo ? act.cupo_maximo + ' personas' : null },
      { lbl: '🗓 Desde', val: act.fecha_inicio
          ? new Date(act.fecha_inicio).toLocaleDateString('es-CO') : null },
    ].filter(f => f.val).map(f => `
      <div class="contact-card"><div>
        <div class="contact-lbl">${f.lbl}</div>
        <div class="contact-val">${f.val}</div>
      </div></div>`).join('');
  }

  // Prescriptor: solo lectura, sin acciones de editar/eliminar
  const acciones = document.getElementById('det-acciones');
  if (acciones) acciones.innerHTML = '';

  document.getElementById('modal-det-overlay').style.display = 'flex';
};

document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('modal-det-overlay')?.addEventListener('click', e => {
    if (e.target === document.getElementById('modal-det-overlay'))
      document.getElementById('modal-det-overlay').style.display = 'none';
  });
});

// ─────────────────────────────────────────────────────────────────────────
window.addEventListener('DOMContentLoaded', async () => {
  const { rol, nombre, email } = MASCATE;

  renderSidebar(nombre, email);

  // ══ BENEFICIARIO ══
  if (rol === 'beneficiario') {
    try {
      const me   = await (await fetch(API + '/beneficiarios/me', MASCATE.authGet())).json();
      const acts = await (await fetch(API + '/beneficiarios/mis-actividades', MASCATE.authGet())).json();

      renderSidebar(me.nombre_apodo, me.email);
      set('hero-avatar', ini(me.nombre_apodo));
      set('hero-nombre', me.nombre_apodo);
      set('hero-rol',    ROL_LABELS[rol]);
      set('hero-desc',   campo(me.descripcion, 'Participante del colectivo MASCATE.'));

      setStats([
        { id:'stat-0', val: acts.length,                          lbl:'Actividades', icon:'📅' },
        { id:'stat-1', val: campo(me.asistencia_pct, '—'),        lbl:'Asistencia',  icon:'✅' },
        { id:'stat-2', val: acts.filter(a=>a.activa).length||'—', lbl:'Activas',     icon:'⭐' },
        { id:'stat-3', val: campo(me.progreso, '—'),              lbl:'Progreso',    icon:'🎯' },
      ]);

      renderInfoGrid('info-grid', me, rol, rol);

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

      _perfilActual = me;
      window._actsCache = acts;
      renderActCards('acts-grid', acts);
    } catch(e) { console.error('Error perfil beneficiario:', e); }
  }

  // ══ PRESCRIPTOR ══
  else if (rol === 'prescriptor') {
    try {
      const asignados = await (await fetch(API + '/prescriptores/mis-asignados', MASCATE.authGet())).json();
      const segs      = await (await fetch(API + '/prescriptores/seguimientos',   MASCATE.authGet())).json();

      set('hero-avatar', ini(nombre)); set('hero-nombre', nombre);
      set('hero-rol', ROL_LABELS[rol]); set('hero-desc', '');

      setStats([
        { id:'stat-0', val: asignados.length,                                 lbl:'Asignados',    icon:'👥' },
        { id:'stat-1', val: segs.length,                                       lbl:'Seguimientos', icon:'📋' },
        { id:'stat-2', val: asignados.filter(a=>a.estado==='urgente').length, lbl:'Urgentes',     icon:'⚠️' },
        { id:'stat-3', val: asignados.filter(a=>a.estado==='al_dia').length,  lbl:'Al día',       icon:'✅' },
      ]);

      // Cargar perfil propio para obtener dispositivo_id y filtrar actividades
      let acts = [];
      try {
        const me = await (await fetch(API + '/prescriptores/me', MASCATE.authGet())).json();
        _perfilActual = me;
        renderInfoGrid('info-grid', me, rol, rol);

        const cl = document.getElementById('contacto-list');
        if (cl && me.dispositivo_nombre) {
          cl.innerHTML = `<div class="list-row">
            <div class="contact-icon" style="background:var(--primary-dim)">🏘️</div>
            <div class="list-info">
              <div class="list-name">${me.dispositivo_nombre}</div>
              <div class="list-sub">Dispositivo asignado</div>
            </div></div>`;
        }

        // Solo actividades del dispositivo del prescriptor
        if (me?.dispositivo_id) {
          acts = await (await fetch(API + '/actividades/?dispositivo_id=' + me.dispositivo_id)).json();
        }
      } catch(e) {
        renderInfoGrid('info-grid', { nombre_completo: nombre, email }, rol, rol);
      }

      const contactoList = document.getElementById('contacto-list');
      if (contactoList) {
        contactoList.innerHTML = asignados.slice(0, 3).map(a => `
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

      window._actsCache = acts;
      renderActCards('acts-grid', acts);
    } catch(e) { console.error('Error perfil prescriptor:', e); }
  }

  // ══ DISPOSITIVO ══
  else if (rol === 'dispositivo') {
    try {
      const d = await (await fetch(API + '/dispositivos/me', MASCATE.authGet())).json();
      if (!d || !d.id) return;

      const stats = await (await fetch(API + '/dispositivos/' + d.id + '/estadisticas', MASCATE.authGet())).json();
      const acts  = await (await fetch(API + '/actividades/?dispositivo_id=' + d.id)).json();

      _perfilActual = d;
      _dispositivoId = d.id;
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

      window._actsCache = acts;
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

      window._actsCache = acts;
      renderActCards('acts-grid', acts);
    } catch(e) { console.error('Error perfil admin:', e); }
  }

  // ── Botón Editar perfil ──────────────────────────────────────────────────
  const btnEdit = document.querySelector('.btn-mustard');
  if (btnEdit && MASCATE.rol !== 'admin') {
    btnEdit.addEventListener('click', abrirModalEdit);
  } else if (btnEdit) {
    btnEdit.remove(); // admin no edita perfil desde aquí
  }

  // ── Botón "Ver todas" → vista de actividades ────────────────────────────
  document.querySelector('.panel-action')?.addEventListener('click', () => {
    window.location.href = '/actividades';
  });
});

// ─────────────────────────────────────────────────────────────────────────
// ══ MODAL EDITAR PERFIL ══

const EDIT_FIELDS = {
  beneficiario: [
    { id:'edit-nombre_apodo',     label:'Apodo / Nombre',   type:'text',   full:true  },
    { id:'edit-telefono',         label:'Teléfono',         type:'tel'                },
    { id:'edit-localidad',        label:'Localidad',        type:'text'               },
    { id:'edit-fecha_nacimiento', label:'Fecha nacimiento', type:'date'               },
    { id:'edit-genero',           label:'Género',           type:'select',
      options:['','Masculino','Femenino','No binario','Prefiero no decir'] },
    { id:'edit-descripcion',      label:'Descripción',      type:'textarea', full:true },
  ],
  prescriptor: [
    { id:'edit-nombre_completo',   label:'Nombre completo',   type:'text', full:true },
    { id:'edit-telefono',          label:'Teléfono',          type:'tel'             },
    { id:'edit-perfil_disciplina', label:'Perfil / disciplina', type:'text'          },
  ],
  dispositivo: [
    { id:'edit-nombre',            label:'Nombre',              type:'text', full:true },
    { id:'edit-tipo_servicio',     label:'Tipo de servicio',    type:'select',
      options:['','Artístico','Cultural','Deportivo','Centro de escucha','Psicoterapia','Educativo','Ambiental'] },
    { id:'edit-lugar_actividades', label:'Lugar de actividades', type:'select',
      options:['','Parque','Salón comunal','Sede propia','Espacio de reserva natural','Otro'] },
    { id:'edit-ubicacion',         label:'Ubicación / Dirección', type:'text', full:true },
    { id:'edit-dia_actividad',     label:'Día de actividad',    type:'text'            },
    { id:'edit-hora_actividad',    label:'Hora',                type:'time'            },
    { id:'edit-telefono',          label:'Teléfono',            type:'tel'             },
    { id:'edit-redes_sociales',    label:'Redes sociales',      type:'text'            },
    { id:'edit-descripcion',       label:'Descripción',         type:'textarea', full:true },
    { id:'edit-capacidad',         label:'Capacidad',           type:'number'          },
  ],
};

// Datos actuales del perfil para pre-llenar el modal
let _perfilActual = null;
let _dispositivoId = null;

function abrirModalEdit() {
  const { rol } = MASCATE;
  if (rol === 'admin') return; // admin no edita perfil desde aquí

  const fields = EDIT_FIELDS[rol];
  if (!fields || !_perfilActual) return;

  const container = document.getElementById('edit-fields');
  if (!container) return;

  container.innerHTML = fields.map(f => {
    const span = f.full ? 'grid-column:1/-1' : '';
    let input = '';
    if (f.type === 'select') {
      input = `<select id="${f.id}" style="width:100%">
        ${f.options.map(o => `<option value="${o}"${_perfilActual[f.id.replace('edit-','')] === o ? ' selected' : ''}>${o||'Selecciona...'}</option>`).join('')}
      </select>`;
    } else if (f.type === 'textarea') {
      input = `<textarea id="${f.id}" style="width:100%;min-height:70px;resize:vertical"
        placeholder="">${_perfilActual[f.id.replace('edit-','')] ?? ''}</textarea>`;
    } else {
      input = `<input type="${f.type}" id="${f.id}" style="width:100%"
        value="${_perfilActual[f.id.replace('edit-','')] ?? ''}">`;
    }
    return `<div style="${span}"><label style="font-size:0.78rem;color:var(--on-bg-muted)">${f.label}</label>${input}</div>`;
  }).join('');

  document.getElementById('edit-error').style.display = 'none';
  document.getElementById('modal-edit-overlay').style.display = 'flex';
}

function cerrarModalEdit() {
  document.getElementById('modal-edit-overlay').style.display = 'none';
}

async function guardarPerfil() {
  const { rol } = MASCATE;
  const btn     = document.getElementById('edit-btn-guardar');
  const errorEl = document.getElementById('edit-error');
  errorEl.style.display = 'none';

  // Construir payload solo con los campos del rol
  const fields  = EDIT_FIELDS[rol];
  const payload = {};
  fields.forEach(f => {
    const key = f.id.replace('edit-', '');
    const el  = document.getElementById(f.id);
    if (!el) return;
    const val = el.value.trim();
    payload[key] = val || null;
  });

  btn.textContent = 'Guardando...';
  btn.disabled    = true;

  try {
    let url, method = 'PUT';
    if      (rol === 'beneficiario') url = API + '/beneficiarios/me';
    else if (rol === 'prescriptor')  url = API + '/prescriptores/me';
    else if (rol === 'dispositivo')  url = API + '/dispositivos/' + _dispositivoId;

    const res  = await fetch(url, { method, headers: MASCATE.authHeaders(), body: JSON.stringify(payload) });
    const data = await res.json();

    if (res.ok) {
      cerrarModalEdit();
      // Actualizar datos en memoria y re-renderizar hero
      _perfilActual = { ..._perfilActual, ...payload };
      const nombre = data.nombre_apodo ?? data.nombre_completo ?? data.nombre ?? MASCATE.nombre;
      set('hero-avatar', ini(nombre));
      set('hero-nombre', nombre);
      // Toast
      const t = document.createElement('div');
      t.textContent = '✓ Perfil actualizado — los cambios se verán completamente al volver a iniciar sesión.';
      t.style.cssText = 'position:fixed;bottom:1.5rem;right:1.5rem;z-index:2000;background:var(--primary);color:#fff;padding:0.75rem 1.25rem;border-radius:var(--radius-md);font-size:0.85rem;font-weight:600;box-shadow:0 4px 20px rgba(0,0,0,0.2);max-width:340px;line-height:1.4';
      document.body.appendChild(t);
      setTimeout(() => t.remove(), 3000);
    } else {
      errorEl.textContent   = data.detail || 'Error al guardar.';
      errorEl.style.display = 'block';
    }
  } catch(e) {
    errorEl.textContent   = 'Error de conexión.';
    errorEl.style.display = 'block';
  }

  btn.textContent = 'Guardar cambios';
  btn.disabled    = false;
}

document.getElementById('modal-edit-overlay')?.addEventListener('click', e => {
  if (e.target === document.getElementById('modal-edit-overlay')) cerrarModalEdit();
});

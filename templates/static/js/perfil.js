/* ═══ MASCATE — PERFIL JS ═══ */
/* Requiere: /static/js/mascate-utils.js */

const API = window.location.origin;
MASCATE.guardAuth();

// ── Modal de detalle de actividad (disponible en todas las vistas) ────────
// verDetalleAct vive en actividades.js pero perfil.js lo necesita también.
// Lo definimos aquí sin botones de editar/eliminar (el prescriptor solo lee).
window.verDetalleAct = function verDetalleAct(act) {
  if (!act) return;

  document.getElementById('det-nombre').textContent      = `${act.emoji || '📅'} ${act.nombre}`;
  document.getElementById('det-tipo').textContent        = campo(act.tipo);
  document.getElementById('det-tipo').className          = 'tag ' + (TAG_COLOR[act.tipo] ?? 'mustard');
  document.getElementById('det-descripcion').textContent = act.descripcion || 'Sin descripción.';
  const grid = document.getElementById('det-grid');
  if (grid) grid.innerHTML = '';

  const acciones = document.getElementById('det-acciones');
  if (acciones) {
    acciones.innerHTML = MASCATE.rol === 'beneficiario'
      ? `<button class="btn btn-sm btn-green" onclick="inscribirse(${act.id})">✓ Inscribirme</button>`
      : '';
  }

  document.getElementById('modal-det-overlay').style.display = 'flex';
};

async function inscribirse(actividadId) {
  try {
    const res = await fetch(API + '/beneficiarios/inscribirse', {
      method: 'POST', headers: MASCATE.authHeaders(),
      body: JSON.stringify({ actividad_id: actividadId })
    });
    const data = await res.json();
    document.getElementById('modal-det-overlay').style.display = 'none';
    if (res.ok) {
      const t = document.createElement('div');
      t.textContent = '✓ Inscripción exitosa';
      t.style.cssText = 'position:fixed;bottom:1.5rem;right:1.5rem;z-index:2000;background:var(--primary);color:#fff;padding:0.75rem 1.25rem;border-radius:var(--radius-md);font-size:0.85rem;font-weight:600;box-shadow:0 4px 20px rgba(0,0,0,0.2)';
      document.body.appendChild(t);
      setTimeout(() => t.remove(), 3000);
    } else {
      alert('Error: ' + (data.detail || 'No se pudo inscribir.'));
    }
  } catch(e) { console.error(e); }
}

document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('modal-det-overlay')?.addEventListener('click', e => {
    if (e.target === document.getElementById('modal-det-overlay'))
      document.getElementById('modal-det-overlay').style.display = 'none';
  });
});

function renderTablaActsBenef(tbodyId, acts) {
  const tbody = document.getElementById(tbodyId);
  if (!tbody) return;
  if (!acts?.length) {
    tbody.innerHTML = '<tr><td colspan="9" style="color:var(--on-bg-muted);text-align:center;padding:1rem">Sin actividades disponibles.</td></tr>';
    return;
  }
  tbody.innerHTML = acts.map(a => {
    const actJson   = JSON.stringify(a).replace(/'/g, "\\'");
    const ins       = a.total_inscritos ?? 0;
    const disponibles = a.cupo_maximo != null ? a.cupo_maximo - ins : null;
    const cupoColor = disponibles != null && disponibles <= 0 ? 'var(--error)' : disponibles != null && disponibles <= 3 ? 'var(--warning,#e6a817)' : 'var(--primary)';
    const inscritosTexto = `<span class="btn btn-sm btn-outline" style="font-size:0.78rem;color:${cupoColor};border-color:${cupoColor};cursor:default">👥 ${ins}${a.cupo_maximo ? '/'+a.cupo_maximo : ''}</span>`;
    return `<tr>
      <td>
        <div style="display:flex;align-items:center;gap:0.5rem">
          <span style="font-size:1.1rem">${a.emoji||'📅'}</span>
          <span style="font-weight:600">${a.nombre}</span>
        </div>
      </td>
      <td><span class="tag ${TAG_COLOR[a.tipo]||'mustard'}">${a.tipo||'—'}</span></td>
      <td style="font-size:0.82rem;color:var(--on-bg-muted)">${a.dispositivo_nombre||'—'}</td>
      <td>${a.lugar||'—'}</td>
      <td>${a.fecha_inicio ? new Date(a.fecha_inicio+'T00:00:00').toLocaleDateString('es-CO',{day:'2-digit',month:'short',year:'numeric'}) : '—'}</td>
      <td>${a.hora||'—'}</td>
      <td>${inscritosTexto}</td>
      <td><span class="tag ${a.activa !== false ? 'green' : ''}" style="${a.activa !== false ? '' : 'background:var(--on-bg-muted,#aaa);color:#fff'}">${a.activa !== false ? 'Activa' : 'Inactiva'}</span></td>
      <td>
        <div style="display:flex;gap:0.35rem;flex-wrap:wrap">
          <button class="btn btn-sm btn-outline" style="font-size:0.78rem" onclick='verDetalleAct(${actJson})'>🔍 Ver detalle</button>
          <button class="btn btn-sm btn-green" style="font-size:0.78rem" onclick="inscribirse(${a.id})">✓ Inscribirme</button>
        </div>
      </td>
    </tr>`;
  }).join('');
}

// ─────────────────────────────────────────────────────────────────────────
window.addEventListener('DOMContentLoaded', async () => {
  const { rol, nombre, email } = MASCATE;

  renderSidebar(nombre, email);

  // ══ BENEFICIARIO ══
  if (rol === 'beneficiario') {
    try {
      const [me, acts, segs] = await Promise.all([
        fetch(API + '/beneficiarios/me', MASCATE.authGet()).then(r => r.json()),
        fetch(API + '/actividades/').then(r => r.json()),
        fetch(API + '/beneficiarios/mis-seguimientos', MASCATE.authGet())
          .then(r => { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
          .catch(e => { console.error('mis-seguimientos error:', e); return []; }),
      ]);

      const ultimoPrescriptor = Array.isArray(segs) && segs.length ? (segs[0].nombre_prescriptor || '—') : '—';

      renderSidebar(me.nombre_apodo, me.email);
      set('hero-avatar', ini(me.nombre_apodo));
      set('hero-nombre', me.nombre_apodo);
      set('hero-rol',    ROL_LABELS[rol]);
      set('hero-desc',   campo(me.descripcion, 'Participante del colectivo MASCATE.'));

      setStats([
        { id:'stat-0', val: acts.length,                             lbl:'Actividades disponibles', icon:'📅' },
        { id:'stat-1', val: acts.filter(a=>a.activa!==false).length, lbl:'Activas',                 icon:'⭐' },
        { id:'stat-2', val: ultimoPrescriptor,                       lbl:'Prescriptxr',             icon:'🎯' },
        { id:'stat-3', val: me.dispositivo_nombre || '—',            lbl:'Dispositivo',             icon:'🏘️' },
      ]);

      // Los stats 2 y 3 contienen texto, no números — reducir fuente para que quepan
      ['stat-2', 'stat-3'].forEach(id => {
        const el = document.getElementById(id);
        if (el) { el.style.fontSize = '0.85rem'; el.style.fontWeight = '600'; el.style.lineHeight = '1.3'; el.style.wordBreak = 'break-word'; }
      });

      renderInfoGrid('info-grid', me, rol, rol);

      const contactoList = document.getElementById('contacto-list');
      if (contactoList) {
        let html = '';
        if (me.dispositivo_nombre) html += `<div class="list-row">
          <div class="contact-icon" style="background:var(--secondary-dim)">🏢</div>
          <div class="list-info"><div class="list-name">${me.dispositivo_nombre}</div>
          <div class="list-sub">Organización vinculada</div></div></div>`;

        try {
          const prescs = await (await fetch(API + '/beneficiarios/mis-prescriptores', MASCATE.authGet())).json();
          if (prescs.length) {
            html += `<div style="font-size:0.78rem;font-weight:600;color:var(--on-bg-muted);margin:0.75rem 0 0.35rem">🎯 Prescriptorxs</div>`;
            html += prescs.map(p => `
              <div class="list-row" style="padding:0.5rem 0;border-bottom:1px solid var(--border)">
                <div class="list-avatar green" style="font-size:0.75rem;flex-shrink:0">${ini(p.nombre_completo)}</div>
                <div class="list-info">
                  <div class="list-name">${p.nombre_completo}</div>
                  ${p.perfil_disciplina ? `<div class="list-sub">${p.perfil_disciplina}</div>` : ''}
                  ${p.telefono ? `<div style="font-size:0.76rem;color:var(--on-bg-muted)">📞 ${p.telefono}</div>` : ''}
                  ${p.email ? `<div style="font-size:0.76rem;color:var(--on-bg-muted)">✉️ ${p.email}</div>` : ''}
                </div>
              </div>`).join('');
          }
        } catch(e) { console.error('Error cargando prescriptores:', e); }

        contactoList.innerHTML = html || '<div style="color:var(--on-bg-muted);font-size:0.85rem;padding:0.5rem">Sin contactos asignados aún.</div>';
      }

      _perfilActual = me;
      window._actsCache = acts;
      document.getElementById('panel-actividades')?.remove();
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

      // Cargar perfil propio
      let me = null;
      try {
        me = await (await fetch(API + '/prescriptores/me', MASCATE.authGet())).json();
        _perfilActual = me;
        renderInfoGrid('info-grid', me, rol, rol);
      } catch(e) {
        renderInfoGrid('info-grid', { nombre_completo: nombre, email }, rol, rol);
      }

      // Panel lateral: dispositivo arriba + asignados abajo
      const contactoList = document.getElementById('contacto-list');
      if (contactoList) {
        let html = '';
        if (me?.dispositivo_nombre) {
          html += `<div class="list-row">
            <div class="contact-icon" style="background:var(--primary-dim)">🏘️</div>
            <div class="list-info">
              <div class="list-name">${me.dispositivo_nombre}</div>
              <div class="list-sub">Dispositivo asignado</div>
            </div>
            <span class="tag green" style="font-size:0.72rem">Activo</span>
          </div>`;
        } else {
          html += `<div class="list-row">
            <div class="contact-icon" style="background:var(--on-bg-dim,#eee)">🏘️</div>
            <div class="list-info">
              <div class="list-name" style="color:var(--on-bg-muted)">Sin dispositivo asignado</div>
            </div>
          </div>`;
        }
        contactoList.innerHTML = html || '<div style="color:var(--on-bg-muted);font-size:0.85rem;padding:0.5rem">Sin información.</div>';
      }
      set('contacto-titulo', 'Dispositivo asignado');

      document.getElementById('panel-actividades')?.remove();
      document.getElementById('panel-presc-benef')?.remove();
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

      document.querySelector('.stats-row')?.remove();

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

      document.getElementById('panel-actividades')?.remove();
      window._actsCache = acts;
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
// ══ TABLA ACTIVIDADES DISPOSITIVO ══

function renderTablaActsDisp(tbodyId, acts) {
  const tbody = document.getElementById(tbodyId);
  if (!tbody) return;
  if (!acts?.length) {
    tbody.innerHTML = '<tr><td colspan="8" style="color:var(--on-bg-muted);text-align:center;padding:1rem">Sin actividades creadas aún.</td></tr>';
    return;
  }
  tbody.innerHTML = acts.map(a => {
    const ins         = a.total_inscritos ?? 0;
    const disponibles = a.cupo_maximo != null ? a.cupo_maximo - ins : null;
    const cupoColor   = disponibles != null && disponibles <= 0 ? 'var(--error)' : disponibles != null && disponibles <= 3 ? 'var(--warning,#e6a817)' : 'var(--primary)';
    const actJson     = JSON.stringify(a).replace(/'/g, "\\'");
    return `<tr>
      <td>
        <div style="display:flex;align-items:center;gap:0.5rem">
          <span style="font-size:1.1rem">${a.emoji||'📅'}</span>
          <span style="font-weight:600">${a.nombre}</span>
        </div>
      </td>
      <td><span class="tag ${TAG_COLOR[a.tipo]||'mustard'}">${a.tipo||'—'}</span></td>
      <td>${a.lugar||'—'}</td>
      <td>${a.fecha_inicio ? new Date(a.fecha_inicio+'T00:00:00').toLocaleDateString('es-CO',{day:'2-digit',month:'short',year:'numeric'}) : '—'}</td>
      <td>${a.hora||'—'}</td>
      <td><button class="btn btn-sm btn-outline" style="font-size:0.78rem;color:${cupoColor};border-color:${cupoColor}" onclick="verInscritosDisp(${a.id},'${a.nombre.replace(/'/g,"\\'")}')">👥 ${ins}${a.cupo_maximo ? '/'+a.cupo_maximo : ''}</button></td>
      <td><span class="tag ${a.activa !== false ? 'green' : ''}" style="${a.activa !== false ? '' : 'background:var(--on-bg-muted,#aaa);color:#fff'}">${a.activa !== false ? 'Activa' : 'Inactiva'}</span></td>
      <td>
        <div style="display:flex;gap:0.35rem;flex-wrap:wrap">
          <button class="btn btn-sm btn-outline" style="font-size:0.78rem" onclick='verDetalleAct(${actJson})'>🔍 Ver detalle</button>
          <button class="btn btn-sm btn-outline" style="font-size:0.78rem" onclick='abrirModalActDisp(${actJson})'>✏️ Editar</button>
        </div>
      </td>
    </tr>`;
  }).join('');
}

// ── Inscritos modal ──
async function verInscritosDisp(actividadId, nombre) {
  document.getElementById('ins-disp-titulo').textContent = nombre;
  document.getElementById('ins-disp-count').textContent  = '...';
  document.getElementById('ins-disp-list').innerHTML     = '<div style="color:var(--on-bg-muted);font-size:0.85rem">Cargando...</div>';
  document.getElementById('modal-ins-disp-overlay').style.display = 'flex';
  try {
    const res  = await fetch(API + '/actividades/' + actividadId + '/inscritos', MASCATE.authGet());
    const data = await res.json();
    document.getElementById('ins-disp-count').textContent = data.total + ' inscritos';
    document.getElementById('ins-disp-list').innerHTML = data.inscritos?.length
      ? data.inscritos.map(b => `<div class="list-row">
          <div class="list-avatar">${(b.nombre_apodo||'?')[0].toUpperCase()}</div>
          <div class="list-info">
            <div class="list-name">${b.nombre_apodo}</div>
            <div class="list-sub">${b.localidad||''} ${b.telefono ? '· '+b.telefono : ''}</div>
          </div></div>`).join('')
      : '<div style="color:var(--on-bg-muted);font-size:0.85rem;padding:0.5rem">Nadie inscrito aún.</div>';
  } catch(e) { document.getElementById('ins-disp-list').innerHTML = '<div style="color:var(--error)">Error al cargar.</div>'; }
}

// ── Modal editar/crear actividad ──
let _actEditandoDisp = null;

function abrirModalActDisp(act = null) {
  _actEditandoDisp = act || null;
  const esEditar = !!act;
  document.getElementById('modal-act-disp-titulo').textContent = esEditar ? 'Editar actividad' : 'Nueva actividad';
  document.getElementById('dact-btn-guardar').textContent      = esEditar ? 'Guardar cambios'  : 'Crear actividad';
  document.getElementById('dact-nombre').value      = act?.nombre       ?? '';
  document.getElementById('dact-tipo').value        = act?.tipo         ?? '';
  document.getElementById('dact-emoji').value       = act?.emoji        ?? '';
  document.getElementById('dact-lugar').value       = act?.lugar        ?? '';
  document.getElementById('dact-fecha').value       = act?.fecha_inicio ?? '';
  document.getElementById('dact-hora').value        = act?.hora         ?? '';
  document.getElementById('dact-cupo').value        = act?.cupo_maximo  ?? '';
  document.getElementById('dact-descripcion').value = act?.descripcion  ?? '';
  document.getElementById('dact-error').style.display = 'none';
  document.getElementById('modal-act-disp-overlay').style.display = 'flex';
}

function cerrarModalActDisp() {
  document.getElementById('modal-act-disp-overlay').style.display = 'none';
  _actEditandoDisp = null;
}

async function guardarActividadDisp() {
  const errorEl = document.getElementById('dact-error');
  const btn     = document.getElementById('dact-btn-guardar');
  errorEl.style.display = 'none';

  const nombre = document.getElementById('dact-nombre').value.trim();
  const tipo   = document.getElementById('dact-tipo').value;
  const lugar  = document.getElementById('dact-lugar').value.trim();
  const fecha  = document.getElementById('dact-fecha').value;
  const hora   = document.getElementById('dact-hora').value;
  if (!nombre || !tipo || !lugar || !fecha || !hora) {
    errorEl.textContent = 'Nombre, Tipo, Lugar, Fecha y Hora son obligatorios.';
    errorEl.style.display = 'block';
    return;
  }

  const payload = {
    nombre, tipo, lugar, hora,
    emoji:       document.getElementById('dact-emoji').value       || '📋',
    fecha_inicio: fecha || null,
    cupo_maximo: document.getElementById('dact-cupo').value ? parseInt(document.getElementById('dact-cupo').value) : null,
    descripcion: document.getElementById('dact-descripcion').value || null,
    dia_semana:  null,
  };

  btn.disabled = true; btn.textContent = 'Guardando...';
  try {
    let res;
    if (_actEditandoDisp) {
      res = await fetch(API + '/actividades/' + _actEditandoDisp.id, { method:'PUT', headers: MASCATE.authHeaders(), body: JSON.stringify(payload) });
    } else {
      res = await fetch(API + '/actividades/', { method:'POST', headers: MASCATE.authHeaders(), body: JSON.stringify(payload) });
    }
    const data = await res.json();
    if (res.ok) {
      cerrarModalActDisp();
      const acts = await (await fetch(API + '/actividades/?dispositivo_id=' + _dispositivoId, MASCATE.authGet())).json();
      window._actsCache = acts;
      renderTablaActsDisp('disp-acts-tbody', acts);
    } else {
      errorEl.textContent = data.detail || 'Error al guardar.';
      errorEl.style.display = 'block';
    }
  } catch(e) { errorEl.textContent = 'Error de conexión.'; errorEl.style.display = 'block'; }
  btn.disabled = false; btn.textContent = _actEditandoDisp ? 'Guardar cambios' : 'Crear actividad';
}

document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('modal-act-disp-overlay')?.addEventListener('click', e => {
    if (e.target === document.getElementById('modal-act-disp-overlay')) cerrarModalActDisp();
  });
  document.getElementById('modal-ins-disp-overlay')?.addEventListener('click', e => {
    if (e.target === document.getElementById('modal-ins-disp-overlay'))
      document.getElementById('modal-ins-disp-overlay').style.display = 'none';
  });
});

// ─────────────────────────────────────────────────────────────────────────
// ══ MODAL EDITAR PERFIL ══

const EDIT_FIELDS = {
  beneficiario: [
    // ── Básicos ──
    { id:'edit-nombre_apodo',     label:'Apodo / Nombre',   type:'text',   full:true  },
    { id:'edit-telefono',         label:'Teléfono',         type:'tel'                },
    { id:'edit-localidad',        label:'Localidad',        type:'text'               },
    { id:'edit-fecha_nacimiento', label:'Fecha de nacimiento', type:'date'            },
    { id:'edit-genero',           label:'Género',           type:'select',
      options:['','Masculino','Femenino','No binario','Otro','Prefiero no decir'] },
    { id:'edit-descripcion',      label:'Notas adicionales', type:'textarea', full:true },
    // ── Sociodemográfico ──
    { id:'edit-section-socio',    label:'── Perfil sociodemográfico ──', type:'section', full:true },
    { id:'edit-estado_civil',     label:'Estado civil',     type:'select',
      options:['','Soltero/a','Casado/a','Unión libre','Separado/a','Divorciado/a','Viudo/a'] },
    { id:'edit-num_hijos',        label:'Número de hijos',  type:'number'             },
    { id:'edit-etnia',            label:'Etnia / identidad étnica', type:'text'       },
    { id:'edit-con_quien_vive',   label:'¿Con quién vive?', type:'text'               },
    { id:'edit-direccion',        label:'Dirección',        type:'text',  full:true   },
    { id:'edit-escolaridad',      label:'Escolaridad',      type:'select',
      options:['','Sin escolaridad','Primaria incompleta','Primaria completa','Secundaria incompleta','Secundaria completa','Técnico/Tecnólogo','Universitario','Posgrado'] },
    { id:'edit-ocupacion',        label:'Ocupación',        type:'text'               },
    { id:'edit-sabe_leer_escribir',   label:'¿Sabe leer y escribir?', type:'select',
      options:['','true','false'], labels:{'true':'Sí','false':'No','':'—'} },
    { id:'edit-sabe_usar_computador', label:'¿Sabe usar computador?', type:'select',
      options:['','true','false'], labels:{'true':'Sí','false':'No','':'—'} },
    { id:'edit-practica_deporte', label:'¿Practica deporte?', type:'select',
      options:['','true','false'], labels:{'true':'Sí','false':'No','':'—'} },
    // ── Red de apoyo ──
    { id:'edit-section-apoyo',    label:'── Red de apoyo ──', type:'section', full:true },
    { id:'edit-nombre_persona_apoyo',   label:'Nombre persona de apoyo',   type:'text'  },
    { id:'edit-telefono_persona_apoyo', label:'Teléfono persona de apoyo', type:'tel'   },
    { id:'edit-vinculo_persona_apoyo',  label:'Vínculo con la persona',    type:'select',
      options:['','Familiar','Amigo/a','Vecino/a','Institución','Otro'] },
    { id:'edit-apoyo_familiar',      label:'Apoyo familiar',      type:'select',
      options:['','true','false'], labels:{'true':'Sí','false':'No','':'—'} },
    { id:'edit-apoyo_comunitario',   label:'Apoyo comunitario',   type:'select',
      options:['','true','false'], labels:{'true':'Sí','false':'No','':'—'} },
    { id:'edit-apoyo_institucional', label:'Apoyo institucional', type:'select',
      options:['','true','false'], labels:{'true':'Sí','false':'No','':'—'} },
    { id:'edit-apoyo_actor_social',  label:'Actor social de apoyo', type:'text', full:true },
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
    const key  = f.id.replace('edit-', '');
    const val  = _perfilActual[key];

    if (f.type === 'section') {
      return `<div style="${span};padding:0.5rem 0 0.1rem;font-size:0.78rem;font-weight:600;color:var(--on-bg-muted);border-bottom:1px solid var(--border)">${f.label}</div>`;
    }
    let input = '';
    if (f.type === 'select') {
      const strVal = val === true ? 'true' : val === false ? 'false' : (val ?? '');
      input = `<select id="${f.id}" style="width:100%">
        ${f.options.map(o => {
          const lbl = f.labels ? (f.labels[o] || o || 'Selecciona...') : (o || 'Selecciona...');
          return `<option value="${o}"${strVal === o ? ' selected' : ''}>${lbl}</option>`;
        }).join('')}
      </select>`;
    } else if (f.type === 'textarea') {
      input = `<textarea id="${f.id}" style="width:100%;min-height:70px;resize:vertical"
        placeholder="">${val ?? ''}</textarea>`;
    } else {
      input = `<input type="${f.type}" id="${f.id}" style="width:100%"
        value="${val ?? ''}">`;
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
  const BOOL_FIELDS = new Set(['sabe_leer_escribir','sabe_usar_computador','practica_deporte','apoyo_familiar','apoyo_comunitario','apoyo_institucional']);
  const payload = {};
  fields.forEach(f => {
    if (f.type === 'section') return;
    const key = f.id.replace('edit-', '');
    const el  = document.getElementById(f.id);
    if (!el) return;
    const raw = el.value.trim();
    if (!raw) { payload[key] = null; return; }
    if (BOOL_FIELDS.has(key)) {
      payload[key] = raw === 'true';
    } else if (f.type === 'number') {
      payload[key] = parseInt(raw) || null;
    } else {
      payload[key] = raw;
    }
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

// ═══════════════════════════════════════════════════════════════
// TABLA BENEFICIARIOS (prescriptor)
// ═══════════════════════════════════════════════════════════════
const ESTADO_SEG = {
  al_dia:     { label:'Al día',           cls:'green' },
  revisar:    { label:'Revisar',          cls:'mustard' },
  urgente:    { label:'Urgente',          cls:'rust' },
  finalizado: { label:'Proceso finalizado', cls:'blue' },
  desvinculado: { label:'Desvinculado',   cls:'' },
};

function renderTablaBenefPresc(tbodyId, asignados) {
  const tbody = document.getElementById(tbodyId);
  if (!tbody) return;
  if (!asignados.length) {
    tbody.innerHTML = `<tr><td colspan="5" style="text-align:center;padding:2rem;color:var(--on-bg-muted)">Sin beneficiarixs asignados aún.</td></tr>`;
    return;
  }
  tbody.innerHTML = asignados.map(b => {
    const est = ESTADO_SEG[b.estado] || { label: b.estado, cls: '' };
    const ultimaSesion = b.ultima_sesion
      ? new Date(b.ultima_sesion).toLocaleDateString('es-CO', { day:'2-digit', month:'short', year:'numeric' })
      : '—';
    const diasLabel = b.dias_sin_sesion != null ? `${b.dias_sin_sesion} días` : '—';
    return `<tr>
      <td style="font-weight:600">${b.nombre_apodo}</td>
      <td style="font-size:0.85rem;color:var(--on-bg-muted)">${ultimaSesion}</td>
      <td style="font-size:0.85rem">${diasLabel}</td>
      <td><span class="tag ${est.cls}">${est.label}</span></td>
      <td style="display:flex;gap:0.5rem;flex-wrap:wrap">
        ${b.estado !== 'finalizado' ? `<button class="btn btn-sm btn-green" style="font-size:0.78rem"
          onclick="abrirModalSeg(${b.id}, '${b.nombre_apodo.replace(/'/g,"\\'")}')">+ Seguimiento</button>` : ''}
        <button class="btn btn-sm btn-outline" style="font-size:0.78rem"
          onclick="verSeguimientosBenef(${b.id}, '${b.nombre_apodo.replace(/'/g,"\\'")}')">Ficha</button>
      </td>
    </tr>`;
  }).join('');
}

function abrirModalSeg(benefId, nombre) {
  document.getElementById('seg-benef-id').value  = benefId;
  document.getElementById('seg-benef-nombre').textContent = nombre;
  document.getElementById('seg-tipo').value = '';
  document.getElementById('seg-observaciones').value = '';
  document.getElementById('seg-error').style.display = 'none';
  document.getElementById('modal-seg-overlay').style.display = 'flex';
}

async function guardarSeguimiento() {
  const tipo   = document.getElementById('seg-tipo').value.trim();
  const obs    = document.getElementById('seg-observaciones').value.trim();
  const benefId = parseInt(document.getElementById('seg-benef-id').value);
  const errEl   = document.getElementById('seg-error');
  errEl.style.display = 'none';

  if (!tipo) { errEl.textContent = 'Selecciona el tipo de registro.'; errEl.style.display = 'block'; return; }

  try {
    const res = await fetch(API + '/prescriptores/seguimientos', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...MASCATE.authHeaders() },
      body: JSON.stringify({ beneficiario_id: benefId, tipo_registro: tipo, observaciones: obs || null }),
    });
    const data = await res.json();
    if (res.ok) {
      document.getElementById('modal-seg-overlay').style.display = 'none';
      const t = document.createElement('div');
      t.textContent = '✓ Seguimiento guardado';
      t.style.cssText = 'position:fixed;bottom:1.5rem;right:1.5rem;z-index:2000;background:var(--primary);color:#fff;padding:0.75rem 1.25rem;border-radius:var(--radius-md);font-size:0.85rem;font-weight:600;box-shadow:0 4px 20px rgba(0,0,0,0.2)';
      document.body.appendChild(t);
      setTimeout(() => t.remove(), 3000);
      // Refresca días sin sesión en tabla
      const asignados = await (await fetch(API + '/prescriptores/mis-asignados', MASCATE.authGet())).json();
      renderTablaBenefPresc('presc-benef-tbody', asignados);
    } else {
      errEl.textContent = data.detail || 'Error al guardar.';
      errEl.style.display = 'block';
    }
  } catch(e) { errEl.textContent = 'Error de conexión.'; errEl.style.display = 'block'; }
}

async function verSeguimientosBenef(benefId, nombre) {
  document.getElementById('segs-benef-titulo').textContent = nombre;
  document.getElementById('segs-benef-count').textContent  = '...';
  document.getElementById('segs-benef-list').innerHTML     = '<div style="color:var(--on-bg-muted);font-size:0.85rem">Cargando...</div>';
  document.getElementById('modal-segs-benef-overlay').style.display = 'flex';
  try {
    const data = await (await fetch(API + '/prescriptores/seguimientos?beneficiario_id=' + benefId, MASCATE.authGet())).json();
    document.getElementById('segs-benef-count').textContent = data.length;
    if (!data.length) {
      document.getElementById('segs-benef-list').innerHTML = '<div style="color:var(--on-bg-muted);font-size:0.85rem;padding:0.5rem">Sin seguimientos registrados.</div>';
      return;
    }
    document.getElementById('segs-benef-list').innerHTML = data.map(s => {
      const fecha = new Date(s.fecha).toLocaleDateString('es-CO', { day:'2-digit', month:'short', year:'numeric', hour:'2-digit', minute:'2-digit' });
      return `<div style="border:1px solid var(--border);border-radius:var(--radius-sm);padding:0.75rem">
        <div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.35rem">
          <span class="tag mustard" style="font-size:0.72rem">${s.tipo_registro || '—'}</span>
          <span style="font-size:0.78rem;color:var(--on-bg-muted)">${fecha}</span>
        </div>
        ${s.observaciones ? `<div style="font-size:0.85rem">${s.observaciones}</div>` : '<div style="font-size:0.82rem;color:var(--on-bg-muted)">Sin observaciones.</div>'}
      </div>`;
    }).join('');
  } catch(e) {
    document.getElementById('segs-benef-list').innerHTML = '<div style="color:var(--error);font-size:0.85rem">Error al cargar.</div>';
  }
}

// ═══════════════════════════════════════════════════════════════
// TABLA SEGUIMIENTOS (beneficiario)
// ═══════════════════════════════════════════════════════════════
function renderTablaSegsbenef(tbodyId, segs) {
  const tbody = document.getElementById(tbodyId);
  if (!tbody) return;
  if (!segs.length) {
    tbody.innerHTML = `<tr><td colspan="4" style="text-align:center;padding:2rem;color:var(--on-bg-muted)">Aún no tienes seguimientos registrados.</td></tr>`;
    return;
  }
  tbody.innerHTML = segs.map(s => {
    const fecha = new Date(s.fecha).toLocaleDateString('es-CO', { day:'2-digit', month:'short', year:'numeric' });
    return `<tr>
      <td style="font-size:0.85rem;color:var(--on-bg-muted)">${fecha}</td>
      <td><span class="tag mustard" style="font-size:0.72rem">${s.tipo_registro || '—'}</span></td>
      <td style="font-size:0.85rem">${s.nombre_beneficiario || '—'}</td>
      <td style="font-size:0.85rem;color:var(--on-bg-muted)">${s.observaciones || '—'}</td>
    </tr>`;
  }).join('');
}

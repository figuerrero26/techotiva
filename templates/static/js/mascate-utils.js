/* ═══ MASCATE — UTILS COMPARTIDOS ═══
   Importar antes que cualquier JS de vista:
   <script src="/static/js/mascate-utils.js"></script>
*/

// ── Auth ──────────────────────────────────────────────────────────────────
const MASCATE = {
  token:  localStorage.getItem('mascate_token'),
  rol:    localStorage.getItem('mascate_rol'),
  nombre: localStorage.getItem('mascate_nombre'),
  email:  localStorage.getItem('mascate_email'),

  authGet()     { return { headers: { 'Authorization': 'Bearer ' + this.token } }; },
  authHeaders() { return { 'Authorization': 'Bearer ' + this.token, 'Content-Type': 'application/json' }; },

  logout() {
    ['mascate_token','mascate_rol','mascate_nombre','mascate_email'].forEach(k => localStorage.removeItem(k));
    window.location.href = '/login';
  },

  guardAuth() {
    if (!this.token) window.location.href = '/login';
  },

  async cambiarPassword(passwordActual, passwordNueva) {
    const res = await fetch(window.location.origin + '/auth/cambiar-password', {
      method: 'POST',
      headers: this.authHeaders(),
      body: JSON.stringify({ password_actual: passwordActual, password_nueva: passwordNueva })
    });
    return { ok: res.ok, data: await res.json() };
  },

  async cambiarRol(usuarioId, nuevoRol) {
    const res = await fetch(window.location.origin + '/admin/usuarios/' + usuarioId + '/rol', {
      method: 'PUT',
      headers: this.authHeaders(),
      body: JSON.stringify({ rol: nuevoRol })
    });
    return { ok: res.ok, data: await res.json() };
  },
};

// ── Labels ────────────────────────────────────────────────────────────────
const ROL_LABELS = {
  admin:        'Administrador',
  dispositivo:  'Dispositivo CBC',
  prescriptor:  'Prescriptxr',
  beneficiario: 'Beneficiarix',
};

const TAG_COLOR = {
  Artístico: 'mustard',
  Deportivo:  'green',
  Cultural:   'blue',
  Ambiental:  'green',
  Educativo:  'blue',
  Escucha:    'purple',
};

const BG_DIM = {
  mustard: 'var(--primary-dim)',
  green:   'var(--secondary-dim)',
  blue:    'rgba(100,160,255,0.12)',
  purple:  'rgba(210,187,255,0.15)',
  rust:    'var(--error-dim)',
};

// ── DOM helpers ───────────────────────────────────────────────────────────

/** Setea textContent por id, solo si el elemento existe y val no es nulo */
function set(id, val) {
  const el = document.getElementById(id);
  if (el && val != null) el.textContent = val;
}

/** Iniciales de dos letras */
function ini(str) { return (str || '??').substring(0, 2).toUpperCase(); }

/**
 * Renderiza una fila de info solo si val existe (viene del back).
 * Cuando el back agregue el campo, aparece automáticamente.
 */
function infoRow(lbl, val, opts = {}) {
  if (val === null || val === undefined || val === '') return '';
  const extra = opts.full ? 'grid-column:1/-1' : '';
  return `<div class="contact-card" style="${extra}"><div>
    <div class="contact-lbl">${lbl}</div>
    <div class="contact-val">${val}</div>
  </div></div>`;
}

/**
 * Devuelve val si existe, fallback si no.
 * Usar para campos que el back todavía no manda.
 */
function campo(val, fallback = '—') {
  return (val !== null && val !== undefined && val !== '') ? val : fallback;
}

/**
 * Renderiza el sidebar con datos del usuario logueado.
 * @param {string} nombreVal  - nombre a mostrar
 * @param {string} emailVal   - email a mostrar
 */
function setSidebar(nombreVal, emailVal) {
  set('sb-role-tag', ROL_LABELS[MASCATE.rol] ?? MASCATE.rol);
  set('sb-uname',    nombreVal || '—');
  set('sb-uemail',   emailVal  || '—');
  set('sb-avatar',   ini(nombreVal));
}

/** Agrega botón de logout al .sb-user de cada vista */
function initLogout() {
  document.querySelectorAll('.sb-user').forEach(u => {
    const btn = document.createElement('button');
    btn.textContent = 'Cerrar sesion';
    btn.className   = 'btn btn-sm btn-outline';
    btn.style.cssText = 'margin-top:0.5rem;width:100%;font-size:0.72rem;';
    btn.onclick = () => MASCATE.logout();
    u.after(btn);
  });
}

/**
 * Renderiza stats en las tarjetas de la vista.
 * @param {Array<{id, val, lbl?, icon?}>} items
 */
function setStats(items) {
  items.forEach(s => {
    set(s.id, s.val ?? '—');
    if (s.lbl)  set(s.id + '-lbl',  s.lbl);
    if (s.icon) set(s.id + '-icon', s.icon);
  });
}

/**
 * Renderiza cards de actividades en un contenedor.
 * @param {string}   containerId  - id del elemento contenedor
 * @param {Array}    acts         - array de actividades
 * @param {number}   max          - máximo de cards (default 3)
 */
function renderActCards(containerId, acts, max = 3) {
  const grid = document.getElementById(containerId);
  if (!grid) return;
  if (!acts?.length) {
    grid.innerHTML = '<div style="color:var(--on-bg-muted);font-size:0.85rem;padding:1rem">Sin actividades registradas.</div>';
    return;
  }
  grid.innerHTML = acts.slice(0, max).map(a => {
    const color = TAG_COLOR[a.tipo] ?? 'mustard';
    const bg    = BG_DIM[color]    ?? 'var(--primary-dim)';
    return `<div class="panel">
      <div style="height:5rem;background:${bg};border-radius:var(--radius-md);
                  display:flex;align-items:center;justify-content:center;
                  font-size:2rem;margin-bottom:1rem">${a.emoji || '📅'}</div>
      <div class="panel-head">
        <span class="panel-title">${campo(a.nombre)}</span>
        <span class="tag ${color}">${campo(a.tipo)}</span>
      </div>
      ${a.descripcion ? `<p style="font-size:0.83rem;color:var(--on-bg-muted);margin:0.5rem 0 0.75rem">${a.descripcion}</p>` : ''}
      <div style="display:flex;gap:1rem;font-size:0.78rem;color:var(--on-bg-muted);margin-bottom:0.75rem">
        <span>📍 ${campo(a.lugar)}</span>
        <span>🕓 ${campo(a.dia_semana)} ${campo(a.hora)}</span>
        ${a.cupo_maximo ? `<span>👥 Cupo: ${a.cupo_maximo}</span>` : ''}
      </div>
      ${a.fecha_inicio ? `<div style="font-size:0.78rem;color:var(--on-bg-muted);margin-bottom:0.5rem">🗓 Desde: ${a.fecha_inicio}</div>` : ''}
      <div style="display:flex;justify-content:space-between;align-items:center;margin-top:0.6rem">
        <span style="font-size:0.78rem;color:var(--on-bg-muted)">${campo(a.dia_semana)} · ${campo(a.hora)}</span>
        <button class="btn btn-sm btn-outline" onclick="window.verDetalleAct&&window.verDetalleAct(window._actsCache?.find(x=>x.id===${a.id}))">Ver detalle</button>
      </div>
    </div>`;
  }).join('');
}

/**
 * Renderiza filas de tabla de actividades.
 * @param {string} tbodyId
 * @param {Array}  acts
 */
function renderActTabla(tbodyId, acts) {
  const tbody = document.getElementById(tbodyId);
  if (!tbody) return;
  if (!acts?.length) {
    tbody.innerHTML = '<tr><td colspan="6" style="color:var(--on-bg-muted)">Sin actividades.</td></tr>';
    return;
  }
  tbody.innerHTML = acts.map(a => {
    const color = TAG_COLOR[a.tipo] ?? 'mustard';
    return `<tr>
      <td>${a.emoji || '📅'} ${campo(a.nombre)}</td>
      <td><span class="tag ${color}">${campo(a.tipo)}</span></td>
      <td>${campo(a.lugar)}</td>
      <td>${campo(a.dia_semana)}</td>
      <td>${campo(a.hora)}</td>
      ${a.cupo_maximo != null ? `<td>${a.cupo_maximo}</td>` : ''}
    </tr>`;
  }).join('');
}

/**
 * Renderiza panel de información personal con infoRow condicional.
 * Muestra solo los campos que el back efectivamente manda.
 * Cuando el back agregue campos nuevos, aparecen solos.
 *
 * @param {string} gridId   - id del contenedor
 * @param {object} data     - objeto con los datos del usuario/perfil
 * @param {string} userRol  - rol del USUARIO VISTO (no necesariamente el logueado)
 * @param {string} viewerRol - rol del usuario logueado (quién está mirando)
 */
function renderInfoGrid(gridId, data, userRol, viewerRol) {
  const grid = document.getElementById(gridId);
  if (!grid) return;

  // Campos visibles según quién mira a quién
  const esUnoMismo  = viewerRol === userRol || viewerRol === 'admin';
  const puedeVerEmail = viewerRol === 'admin' || viewerRol === userRol;

  let html = '';

  // Campos básicos — siempre visibles si existen
  html += infoRow('Nombre',      data.nombre_apodo ?? data.nombre_completo ?? data.nombre);
  html += infoRow('Rol',         ROL_LABELS[userRol] ?? userRol);

  // Email — solo el propio usuario o admin
  if (puedeVerEmail) {
    html += infoRow('Correo', data.email);
  }

  // Campos que el back todavía no manda — aparecerán solos cuando lleguen
  html += infoRow('Teléfono',         data.telefono);
  html += infoRow('Localidad',        data.localidad);
  html += infoRow('Fecha nacimiento', data.fecha_nacimiento
    ? new Date(data.fecha_nacimiento).toLocaleDateString('es-CO') : null);
  html += infoRow('Género',           data.genero);
  html += infoRow('Disciplina',       data.perfil_disciplina);  // prescriptor
  html += infoRow('Ubicación',        data.ubicacion);          // dispositivo
  html += infoRow('Horario',          data.dia_actividad
    ? `${data.dia_actividad} ${data.hora_actividad ?? ''}`.trim() : null);
  html += infoRow('Redes sociales',   data.redes_sociales);
  html += infoRow('Desde',            data.fecha_registro
    ? new Date(data.fecha_registro).toLocaleDateString('es-CO') : null);
  html += infoRow('Descripción',      data.descripcion, { full: true });

  grid.innerHTML = html || '<div style="color:var(--on-bg-muted);font-size:0.85rem">Sin información adicional.</div>';
}

// ── Sidebars por rol ──────────────────────────────────────────────────────
const SIDEBARS = {
  admin: {
    logo: '🔐', sections: [
      { label: 'Sistema', items: [
        { href:'/dashboard',     ic:'📊', txt:'Panel central' },
        { href:'/dispositivos-admin', ic:'🏘️', txt:'Dispositivos' },
        { href:'/usuarios',      ic:'👥', txt:'Usuarios' },
        { href:'/reportar-info',   ic:'📋', txt:'Formularios' },
      ]},
      { label: 'Config', items: [
        { href:'/configuracion', ic:'🔧', txt:'Configuración' },
        { href:'/reportes',      ic:'📄', txt:'Reportes' },
        { href:'/roles',         ic:'🛡️', txt:'Roles y permisos' },
      ]},
    ],
  },
  dispositivo: {
    logo: '🏘️', sections: [
      { label: 'Principal', items: [
        { href:'/dashboard',   ic:'📊', txt:'Panel general' },
        { href:'/perfil',      ic:'👤', txt:'Mi perfil' },
        { href:'/actividades', ic:'📋', txt:'Actividades' },
        { href:'/usuarios',    ic:'👥', txt:'Beneficiarixs' },
        { href:'/mis-prescriptores', ic:'🎯', txt:'Prescriptorxs' },
        { href:'/formularios', ic:'🤝', txt:'Hoja de primer contacto' },
      ]},
      { label: 'Reportes', items: [
        { href:'/reportar-info', ic:'📄', txt:'Reportar info' },
      ]},
      { label: 'Configuracion', items: [
        { href:'/configuracion',  ic:'⚙️',  txt:'Configuración' },
      ]},
    ],
  },
  prescriptor: {
    logo: '🎯', sections: [
      { label: 'Principal', items: [
        { href:'/dashboard',     ic:'🏠', txt:'Inicio' },
        { href:'/perfil',        ic:'👤', txt:'Mi perfil' },
        { href:'/actividades',   ic:'📋', txt:'Mis seguimientos' },
        { href:'/usuarios',      ic:'👥', txt:'Asignados a mí' },
      ]},
      { label: 'Gestión', items: [
        { href:'/reportar-info', ic:'📝', txt:'Ingresar información' },
        { href:'/notificaciones',ic:'🔔', txt:'Notificaciones' },
      ]},
      { label: 'Configuracion', items: [
        { href:'/configuracion',  ic:'⚙️',  txt:'Configuración' },
      ]},
    ],
  },
  beneficiario: {
    logo: '🌱', sections: [
      { label: 'Explorar', items: [
        { href:'/dashboard',   ic:'🏠', txt:'Inicio' },
        { href:'/actividades', ic:'🔍', txt:'Buscar actividades' },
        { href:'/mapa',        ic:'🗺️', txt:'Mapa de dispositivos' },
      ]},
      { label: 'Mi espacio', items: [
        { href:'/mis-actividades', ic:'📌', txt:'Mis actividades' },
        { href:'/perfil',        ic:'👤', txt:'Mi perfil' },
        { href:'/notificaciones',ic:'🔔', txt:'Notificaciones' },
        { href:'/configuracion',  ic:'⚙️',  txt:'Configuración' },
      ]},
    ],
  },
};

/**
 * Inyecta el sidebar correcto según el rol en el elemento <nav class="sidebar">.
 * Marca como activo el item cuyo href coincide con la página actual.
 * @param {string} nombreVal
 * @param {string} emailVal
 */
function renderSidebar(nombreVal, emailVal) {
  const nav = document.querySelector('nav.sidebar');
  if (!nav) return;

  const rolData  = SIDEBARS[MASCATE.rol] ?? SIDEBARS['admin'];
  const current  = window.location.pathname;

  let sectionsHtml = '';
  rolData.sections.forEach(sec => {
    sectionsHtml += `<span class="sb-section">${sec.label}</span>`;
    sec.items.forEach(item => {
      const active = item.href === current ? ' active' : '';
      sectionsHtml += `<a class="sb-item${active}" href="${item.href}"><span class="ic">${item.ic}</span> ${item.txt}</a>`;
    });
  });

  const i = ini(nombreVal);
  nav.innerHTML = `
    <div class="sb-brand">
      <div class="sb-logo">${rolData.logo}</div>
      <div>
        <div class="sb-name" id="sb-uname">${nombreVal || '—'}</div>
        <div class="sb-role-tag" id="sb-role-tag">${ROL_LABELS[MASCATE.rol] ?? MASCATE.rol}</div>
      </div>
    </div>
    ${sectionsHtml}
    <div class="sb-spacer"></div>
    <div class="sb-user">
      <div class="sb-avatar" id="sb-avatar">${i}</div>
      <div>
        <div class="sb-uname" id="sb-uname">${nombreVal || '—'}</div>
        <div class="sb-uemail" id="sb-uemail">${emailVal || '—'}</div>
      </div>
    </div>`;

  // Agregar logout
  const sbUser = nav.querySelector('.sb-user');
  if (sbUser) {
    const btn = document.createElement('button');
    btn.textContent = 'Cerrar sesion';
    btn.className   = 'btn btn-sm btn-outline';
    btn.style.cssText = 'margin-top:0.5rem;width:100%;font-size:0.72rem;';
    btn.onclick = () => MASCATE.logout();
    sbUser.after(btn);
  }
}

// ── Export helper ─────────────────────────────────────────────────────────
/**
 * Descarga la lista de dispositivos como CSV o JSON.
 * Llama a GET /admin/dispositivos/exportar?formato=csv
 */
async function exportarDispositivos(formato = 'csv') {
  try {
    const res = await fetch(
      window.location.origin + '/admin/dispositivos/exportar?formato=' + formato,
      MASCATE.authGet()
    );
    if (!res.ok) { alert('Error al exportar'); return; }
    const blob = await res.blob();
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href     = url;
    a.download = 'dispositivos-mascate.' + formato;
    a.click();
    URL.revokeObjectURL(url);
  } catch(e) { console.error('Error exportando:', e); }
}

// ── Campanita de notificaciones ───────────────────────────────────────────
/**
 * Inicializa la campanita de notificaciones con badge si hay pendientes.
 * Llama a esta función en cada vista después de renderSidebar.
 */
async function initNotifBtn() {
  const btn = document.querySelector('.notif-btn');
  const dot = document.querySelector('.notif-dot');
  if (!btn || !dot) return;

  btn.style.cursor = 'pointer';
  btn.onclick = () => { window.location.href = '/notificaciones'; };

  // Mostrar dot si hay alertas o pendientes
  try {
    let hayPendientes = false;

    if (MASCATE.rol === 'admin') {
      const [alertas, users] = await Promise.all([
        fetch(window.location.origin + '/admin/alertas', MASCATE.authGet()).then(r => r.json()),
        fetch(window.location.origin + '/admin/usuarios', MASCATE.authGet()).then(r => r.json()),
      ]);
      hayPendientes = alertas.length > 0 || users.some(u => u.status === 'pendiente');
    } else if (MASCATE.rol === 'prescriptor') {
      const asignados = await fetch(window.location.origin + '/prescriptores/mis-asignados', MASCATE.authGet()).then(r => r.json());
      hayPendientes = asignados.some(a => a.estado === 'urgente' || a.estado === 'revisar');
    }

    dot.style.display = hayPendientes ? 'block' : 'none';
  } catch(e) {
    dot.style.display = 'none';
  }
}

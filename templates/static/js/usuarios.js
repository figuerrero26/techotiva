/* ═══ MASCATE — USUARIOS JS ═══ */
const API = window.location.origin;
MASCATE.guardAuth();

let todosLosUsuarios  = [];
let usuarioEditando   = null;
let _dispositivosLista = [];   // cache de dispositivos para el modal
let _miDispId          = null; // id del dispositivo del usuario logueado (rol=dispositivo)

window.addEventListener('DOMContentLoaded', async () => {
  const { rol, nombre, email } = MASCATE;
  renderSidebar(nombre, email);

  if (rol === 'prescriptor') {
    await cargarAsignados();
    initFiltros();
    return;
  }

  if (rol === 'dispositivo') {
    await cargarBeneficiariosDispositivo();
    initFiltros();
    return;
  }

  // admin
  await cargarUsuarios();
  await cargarPendientes();
  await cargarSolicitudesPrescriptor();
  initFiltros();
});

// ── Cargar usuarios (admin) ──────────────────────────────────────────────
async function cargarUsuarios() {
  try {
    todosLosUsuarios = await (await fetch(API + '/admin/usuarios', MASCATE.authGet())).json();

    const beneficiarios = todosLosUsuarios.filter(u => u.rol === 'beneficiario');
    const prescriptores = todosLosUsuarios.filter(u => u.rol === 'prescriptor');
    const dispositivos  = todosLosUsuarios.filter(u => u.rol === 'dispositivo');

    setStats([
      { id:'stat-0', val: todosLosUsuarios.length },
      { id:'stat-1', val: beneficiarios.length },
      { id:'stat-2', val: prescriptores.length },
      { id:'stat-3', val: dispositivos.length },
    ]);

    renderTabla(todosLosUsuarios);
  } catch(e) { console.error('Error cargando usuarios:', e); }
}

// ── Cargar beneficiarios del dispositivo ────────────────────────────────
async function cargarBeneficiariosDispositivo() {
  try {
    const me = await fetch(API + '/dispositivos/me', MASCATE.authGet()).then(r => r.json());
    const dispositivoId = me.id;
    _miDispId = dispositivoId;

    const beneficiarios = await fetch(
      API + '/dispositivos/' + dispositivoId + '/beneficiarios-detalle',
      MASCATE.authGet()
    ).then(r => r.json());

    todosLosUsuarios = Array.isArray(beneficiarios) ? beneficiarios : [];

    const h1 = document.querySelector('h1');
    if (h1) h1.textContent = 'Beneficiarixs del dispositivo';
    const p = document.querySelector('.page-header p');
    if (p) p.textContent = 'Personas registradas y vinculadas a este dispositivo.';

    document.querySelectorAll('.stat-card')[2]?.remove();
    document.querySelectorAll('.stat-card')[2]?.remove();

    const urgentes = todosLosUsuarios.filter(a => a.estado === 'urgente').length;
    setStats([
      { id:'stat-0', val: todosLosUsuarios.length },
      { id:'stat-1', val: todosLosUsuarios.length },
      { id:'stat-2', val: urgentes },
    ]);

    const labels = document.querySelectorAll('.stat-label');
    if (labels[0]) labels[0].textContent = 'Total';
    if (labels[1]) labels[1].textContent = 'Beneficiarixs';
    if (labels[2]) labels[2].textContent = 'Urgentes';

    document.getElementById('panel-pendientes')?.remove();

    const thead = document.getElementById('users-thead');
    if (thead) thead.innerHTML = `<tr>
      <th>Beneficiarix</th><th>Correo</th><th>Teléfono</th><th>Última sesión</th><th>Días sin sesión</th><th>Estado</th><th>Acciones</th>
    </tr>`;

    renderTablaAsignados(todosLosUsuarios);
  } catch(e) { console.error('Error cargando beneficiarios del dispositivo:', e); }
}

// ── Cargar solicitudes de prescriptores (admin) ──────────────────────────
async function cargarSolicitudesPrescriptor() {
  if (MASCATE.rol !== 'admin') return;
  try {
    const sol = await fetch(API + '/admin/solicitudes-prescriptor', MASCATE.authGet()).then(r => r.json());
    window._solicitudesPrescriptor = Array.isArray(sol) ? sol : [];
    const panel = document.getElementById('panel-solicitudes-presc');
    const lista  = document.getElementById('solicitudes-list');
    const count  = document.getElementById('solicitudes-count');

    if (!Array.isArray(sol) || !sol.length) {
      if (panel) panel.style.display = 'none';
      return;
    }

    if (panel) panel.style.display = 'block';
    if (count) count.textContent = sol.length;

    if (lista) {
      lista.innerHTML = sol.map(s => `
        <div class="list-row" style="padding:0.65rem 0;border-bottom:1px solid var(--border)">
          <div class="list-avatar" style="background:var(--violet-dim);color:var(--violet);flex-shrink:0">
            ${(s.nombre_completo||'??').substring(0,2).toUpperCase()}
          </div>
          <div class="list-info">
            <div class="list-name">${campo(s.nombre_completo, s.email)}</div>
            <div class="list-sub">
              Quiere unirse a: <strong>${campo(s.solicitud_nombre)}</strong>
              ${s.dispositivo_nombre_actual ? ' · Actual: ' + s.dispositivo_nombre_actual : ''}
            </div>
          </div>
          <div style="display:flex;gap:0.4rem;flex-shrink:0">
            <button class="btn btn-sm btn-green"
              onclick="adminAprobarSolicitud(${s.prescriptor_id})">✓ Aprobar</button>
            <button class="btn btn-sm btn-outline"
              style="color:var(--error);border-color:var(--error)"
              onclick="adminRechazarSolicitud(${s.prescriptor_id})">✕ Rechazar</button>
          </div>
        </div>`).join('');
    }
  } catch(e) { console.error('Error solicitudes prescriptor:', e); }
}

async function adminAprobarSolicitud(prescriptorId) {
  try {
    const res = await fetch(API + '/admin/prescriptores/' + prescriptorId + '/aprobar-solicitud',
      { method: 'POST', headers: MASCATE.authHeaders() });
    if (res.ok) {
      await cargarUsuarios();
      await cargarSolicitudesPrescriptor();
    } else {
      const d = await res.json().catch(() => ({}));
      alert('Error: ' + (d.detail || 'No se pudo aprobar.'));
    }
  } catch(e) { console.error(e); }
}

async function adminRechazarSolicitud(prescriptorId) {
  if (!confirm('¿Rechazar esta solicitud?')) return;
  try {
    const res = await fetch(API + '/admin/prescriptores/' + prescriptorId + '/rechazar-solicitud',
      { method: 'POST', headers: MASCATE.authHeaders() });
    if (res.ok) {
      await cargarSolicitudesPrescriptor();
    } else {
      const d = await res.json().catch(() => ({}));
      alert('Error: ' + (d.detail || 'No se pudo rechazar.'));
    }
  } catch(e) { console.error(e); }
}

// ── Cargar pendientes de aprobación ──────────────────────────────────────
async function cargarPendientes() {
  const pendientes = todosLosUsuarios.filter(u => u.status === 'pendiente');
  const panel      = document.getElementById('panel-pendientes');
  const lista      = document.getElementById('pendientes-list');
  const count      = document.getElementById('pendientes-count');
  const dot        = document.getElementById('notif-dot');

  if (!pendientes.length) {
    if (panel) panel.style.display = 'none';
    if (dot)   dot.style.display   = 'none';
    return;
  }

  if (panel) panel.style.display = 'block';
  if (dot)   dot.style.display   = 'block';
  if (count) count.textContent   = pendientes.length;

  if (lista) {
    lista.innerHTML = pendientes.map(u => `
      <div class="list-row" style="padding:0.75rem 0;border-bottom:1px solid var(--border)">
        <div class="list-avatar" style="flex-shrink:0">${ini(u.nombre||u.email)}</div>
        <div class="list-info">
          <div class="list-name">${campo(u.nombre, u.email)}</div>
          <div class="list-sub">${ROL_LABELS[u.rol] ?? u.rol} · ${u.email}</div>
        </div>
        <div style="display:flex;gap:0.5rem;flex-shrink:0">
          <button class="btn btn-sm btn-green"
            onclick="aprobarUsuario(${u.id})">✓ Aprobar</button>
          <button class="btn btn-sm btn-outline"
            style="color:var(--error);border-color:var(--error)"
            onclick="rechazarUsuario(${u.id})">✕ Rechazar</button>
        </div>
      </div>`).join('');
  }
}

// ── Aprobar / Rechazar ───────────────────────────────────────────────────
async function aprobarUsuario(id) {
  try {
    const res = await fetch(API + '/admin/usuarios/' + id + '/aprobar',
      { method: 'POST', headers: MASCATE.authHeaders() });
    if (res.ok) { await cargarUsuarios(); await cargarPendientes(); }
    else {
      const d = await res.json();
      alert('Error: ' + (d.detail || 'No se pudo aprobar.'));
    }
  } catch(e) { console.error(e); }
}

async function rechazarUsuario(id) {
  if (!confirm('¿Desactivar este usuario?')) return;
  try {
    const res = await fetch(API + '/admin/usuarios/' + id + '/estado',
      { method: 'PUT', headers: MASCATE.authHeaders(),
        body: JSON.stringify({ status: 'inactivo' }) });
    if (res.ok) { await cargarUsuarios(); await cargarPendientes(); }
    else {
      const d = await res.json();
      alert('Error: ' + (d.detail || 'No se pudo rechazar.'));
    }
  } catch(e) { console.error(e); }
}

// ── Render tabla ─────────────────────────────────────────────────────────
function renderTabla(lista) {
  const tbody = document.getElementById('users-tbody');
  if (!tbody) return;

  if (!lista.length) {
    const cols = MASCATE.rol === 'dispositivo' ? 5 : 8;
    tbody.innerHTML = `<tr><td colspan="${cols}" style="color:var(--on-bg-muted);text-align:center;padding:1rem">Sin usuarios.</td></tr>`;
    return;
  }

  tbody.innerHTML = lista.map(u => {
    const rolColor = u.rol === 'beneficiario' ? 'mustard'
                   : u.rol === 'prescriptor'  ? 'blue'
                   : u.rol === 'dispositivo'  ? 'purple' : 'green';
    const stColor  = u.status === 'activo'    ? 'green'
                   : u.status === 'pendiente' ? 'mustard' : 'rust';
    const fecha    = u.fecha_registro
                   ? new Date(u.fecha_registro).toLocaleDateString('es-CO') : '—';
    let contexto = '—';
    if (u.dispositivo_nombre) {
      contexto = `<div style="font-size:0.8rem">${u.dispositivo_nombre}</div>`;
      if (u.prescriptor_nombre) {
        contexto += `<div style="font-size:0.75rem;color:var(--on-bg-muted)">${u.prescriptor_nombre}</div>`;
      }
    } else if (u.prescriptor_nombre) {
      contexto = `<div style="font-size:0.8rem;color:var(--on-bg-muted)">${u.prescriptor_nombre}</div>`;
    }
    return `<tr>
      <td>
        <div style="display:flex;align-items:center;gap:0.6rem">
          <div class="list-avatar" style="width:1.8rem;height:1.8rem;font-size:0.7rem;flex-shrink:0">
            ${ini(u.nombre||u.email)}
          </div>
          <span style="font-weight:600">${campo(u.nombre, u.email)}</span>
        </div>
      </td>
      <td><span class="tag ${rolColor}">${ROL_LABELS[u.rol] ?? u.rol}</span></td>
      <td style="font-size:0.82rem;color:var(--on-bg-muted)">${campo(u.email)}</td>
      <td style="font-size:0.82rem">${campo(u.telefono)}</td>
      <td><span class="tag ${stColor}">${u.status}</span></td>
      ${MASCATE.rol !== 'dispositivo' ? `<td>${contexto}</td>` : ''}
      ${MASCATE.rol !== 'dispositivo' ? `<td style="font-size:0.82rem;color:var(--on-bg-muted)">${fecha}</td>` : ''}
      <td style="display:flex;gap:0.4rem;flex-wrap:wrap">
        ${MASCATE.rol !== 'prescriptor' ? `<button class="btn btn-sm btn-outline" onclick="abrirModal(${u.id})">Editar</button>` : ''}
        ${u.rol === 'beneficiario' && u.beneficiario_id ? `<button class="btn btn-sm btn-outline" style="color:var(--primary);border-color:var(--primary)" onclick="abrirFicha(${u.beneficiario_id})">Ficha</button>` : ''}
        ${u.rol === 'prescriptor' && MASCATE.rol === 'admin' ? `<button class="btn btn-sm btn-outline" style="color:var(--primary);border-color:var(--primary)" onclick="abrirFichaPresc(${u.id})">Ficha</button>` : ''}
        ${MASCATE.rol === 'prescriptor' && u.rol === 'beneficiario' && u.beneficiario_id ? `<button class="btn btn-sm btn-green" style="font-size:0.78rem" onclick="irASeguimiento(${u.beneficiario_id},'${(u.nombre||u.email).replace(/'/g,"\\'")}')">+ Seguimiento</button>` : ''}
        ${MASCATE.rol === 'admin' && u.rol === 'beneficiario' && u.beneficiario_id ? `<button class="btn btn-sm btn-outline" style="font-size:0.78rem" onclick="verSeguimientosUsu(${u.beneficiario_id}, '${(u.nombre||u.email).replace(/'/g,"\\'")}')">Seguimientos</button>` : ''}
      </td>
    </tr>`;
  }).join('');
}

// ── Filtros ──────────────────────────────────────────────────────────────
function initFiltros() {
  const searchInput  = document.getElementById('search-input');
  const roleSelect   = document.getElementById('role-select');
  const statusSelect = document.getElementById('status-select');
  const rol          = MASCATE.rol;

  // Para prescriptor y dispositivo el rol es siempre beneficiario → ocultar filtro rol
  if (rol === 'prescriptor' || rol === 'dispositivo') {
    roleSelect?.closest('div')?.remove();
  }

  function filtrar() {
    const q  = (searchInput?.value  ?? '').toLowerCase();
    const r  = roleSelect?.value    ?? 'todos';
    const st = statusSelect?.value  ?? 'todos';

    const filtrados = todosLosUsuarios.filter(u => {
      const txt    = (u.nombre || u.email || '').toLowerCase();
      const matchQ = txt.includes(q);
      const matchR = r  === 'todos' || u.rol    === r;
      const matchS = st === 'todos' || u.status === st;
      return matchQ && matchR && matchS;
    });

    if (rol === 'prescriptor') {
      renderTablaAsignados(filtrados);
    } else {
      renderTabla(filtrados);
    }
  }

  searchInput?.addEventListener('input', filtrar);
  document.getElementById('btn-filtrar')?.addEventListener('click', filtrar);
  roleSelect?.addEventListener('change', filtrar);
  statusSelect?.addEventListener('change', filtrar);
}

// ── Modal editar ─────────────────────────────────────────────────────────
async function abrirModal(id) {
  usuarioEditando = todosLosUsuarios.find(u => u.id === id);
  if (!usuarioEditando) return;

  const u = usuarioEditando;
  set('modal-titulo', 'Editar usuario');
  set('modal-avatar', ini(u.nombre || u.email));
  set('modal-nombre', campo(u.nombre, u.email));
  set('modal-email',  u.email);

  const modalRol    = document.getElementById('modal-rol');
  const modalEstado = document.getElementById('modal-estado');
  if (modalRol)    modalRol.value    = u.rol;
  if (modalEstado) modalEstado.value = u.status;

  // Bloque dispositivo: solo para prescriptores
  const dispWrap = document.getElementById('modal-dispositivo-wrap');
  const dispSel  = document.getElementById('modal-dispositivo');
  const solInfo  = document.getElementById('modal-solicitud-info');

  // Cargar lista de dispositivos si no está cargada (usada por prescriptores y beneficiarios)
  if (!_dispositivosLista.length) {
    try {
      const res = await fetch(API + '/admin/dispositivos', MASCATE.authGet());
      if (res.ok) _dispositivosLista = await res.json();
    } catch(e) { console.error(e); }
  }

  // Bloque dispositivo para PRESCRIPTORES
  if (u.rol === 'prescriptor' && dispWrap) {
    dispWrap.style.display = 'block';
    if (dispSel) {
      dispSel.innerHTML = '<option value="">— Sin dispositivo —</option>' +
        _dispositivosLista.map(d => `<option value="${d.id}">${d.nombre}</option>`).join('');
      if (u.dispositivo_id) dispSel.value = String(u.dispositivo_id);
      else if (u.dispositivo_nombre) {
        const match = _dispositivosLista.find(d => d.nombre === u.dispositivo_nombre);
        if (match) dispSel.value = String(match.id);
      }
    }
    if (solInfo) {
      const solData = (window._solicitudesPrescriptor || []).find(s => s.prescriptor_id === u.prescriptor_id);
      solInfo.innerHTML = solData?.solicitud_nombre
        ? `⏳ Solicitud pendiente en <strong>${solData.solicitud_nombre}</strong>` : '';
    }
  } else if (dispWrap) {
    dispWrap.style.display = 'none';
    if (solInfo) solInfo.textContent = '';
  }

  // Bloque dispositivo para BENEFICIARIOS
  const dispBenefWrap = document.getElementById('modal-disp-benef-wrap');
  const dispBenefSel  = document.getElementById('modal-disp-benef');
  if (u.rol === 'beneficiario' && MASCATE.rol === 'admin' && dispBenefWrap) {
    dispBenefWrap.style.display = 'block';
    if (dispBenefSel) {
      dispBenefSel.innerHTML = '<option value="">— Sin dispositivo —</option>' +
        _dispositivosLista.map(d => `<option value="${d.id}">${d.nombre}</option>`).join('');
      if (u.dispositivo_id) dispBenefSel.value = String(u.dispositivo_id);
    }
  } else if (dispBenefWrap) {
    dispBenefWrap.style.display = 'none';
  }

  // Ocultar bloque entidad dispositivo siempre
  const dispEntityWrap = document.getElementById('modal-disp-entity-wrap');
  if (dispEntityWrap) dispEntityWrap.style.display = 'none';

  // Ocultar campo rol si el usuario logueado es dispositivo O si el usuario editado es dispositivo
  const rolWrap = document.getElementById('modal-rol-wrap');
  if (rolWrap) rolWrap.style.display = (MASCATE.rol === 'dispositivo' || u.rol === 'dispositivo') ? 'none' : '';
  const btnEliminar = document.getElementById('modal-btn-eliminar');
  if (btnEliminar) btnEliminar.style.display = MASCATE.rol === 'dispositivo' ? 'none' : '';

  // Política de privacidad
  const privWrap = document.getElementById('modal-privacidad-wrap');
  const privTxt  = document.getElementById('modal-privacidad-txt');
  if (privWrap && privTxt) {
    if (u.politica_privacidad_at) {
      const fecha = new Date(u.politica_privacidad_at).toLocaleDateString('es-CO', { day:'2-digit', month:'long', year:'numeric' });
      privTxt.innerHTML = `✅ Aceptó tratamiento de datos el <strong>${fecha}</strong>`;
      privWrap.style.cssText = 'display:block;margin-bottom:1rem;padding:0.6rem 0.75rem;border-radius:var(--radius-sm);font-size:0.8rem;background:var(--primary-dim,#e8f5e9);color:var(--on-bg)';
    } else {
      privTxt.innerHTML = '⚠️ No ha aceptado la política de tratamiento de datos';
      privWrap.style.cssText = 'display:block;margin-bottom:1rem;padding:0.6rem 0.75rem;border-radius:var(--radius-sm);font-size:0.8rem;font-weight:600;background:#fdecea;color:#c0392b';
    }
  }

  const overlay = document.getElementById('modal-overlay');
  if (overlay) { overlay.style.display = 'flex'; }
}

function cerrarModal() {
  const overlay = document.getElementById('modal-overlay');
  if (overlay) overlay.style.display = 'none';
  usuarioEditando = null;
}

async function desasociarDispositivoAdmin() {
  if (!usuarioEditando || usuarioEditando.rol !== 'prescriptor' || !usuarioEditando.prescriptor_id) return;
  if (!confirm('¿Quitar el dispositivo asignado a este prescriptor?')) return;

  try {
    const res = await fetch(
      API + '/admin/prescriptores/' + usuarioEditando.prescriptor_id + '/dispositivo',
      {
        method: 'PUT',
        headers: MASCATE.authHeaders(),
        body: JSON.stringify({ dispositivo_id: null }),
      }
    );
    if (res.ok) {
      const dispSel = document.getElementById('modal-dispositivo');
      if (dispSel) dispSel.value = '';
      const solInfo = document.getElementById('modal-solicitud-info');
      if (solInfo) solInfo.textContent = '';
      usuarioEditando.dispositivo_nombre = null;
    } else {
      const d = await res.json();
      alert('Error: ' + (d.detail || 'No se pudo quitar el dispositivo.'));
    }
  } catch(e) { console.error(e); alert('Error de conexión.'); }
}

async function guardarCambiosUsuario() {
  if (!usuarioEditando) return;

  const nuevoRol    = document.getElementById('modal-rol')?.value;
  const nuevoEstado = document.getElementById('modal-estado')?.value;
  const btn         = document.getElementById('modal-btn-guardar');

  btn.textContent = 'Guardando...';
  btn.disabled    = true;

  let hayError = false;

  // Cambiar rol si cambió
  if (nuevoRol !== usuarioEditando.rol) {
    const { ok, data } = await MASCATE.cambiarRol(usuarioEditando.id, nuevoRol);
    if (!ok) {
      alert('Error al cambiar rol: ' + (data.detail || 'Error desconocido.'));
      hayError = true;
    }
  }

  // Cambiar estado si cambió
  if (!hayError && nuevoEstado !== usuarioEditando.status) {
    try {
      const res = await fetch(
        API + '/admin/usuarios/' + usuarioEditando.id + '/estado',
        { method: 'PUT', headers: MASCATE.authHeaders(),
          body: JSON.stringify({ status: nuevoEstado }) }
      );
      if (!res.ok) {
        const d = await res.json();
        alert('Error al cambiar estado: ' + (d.detail || 'Error desconocido.'));
        hayError = true;
      }
    } catch(e) { console.error(e); hayError = true; }
  }

  // Guardar dispositivo si el usuario es prescriptor
  if (!hayError && usuarioEditando.rol === 'prescriptor' && usuarioEditando.prescriptor_id) {
    const dispSel = document.getElementById('modal-dispositivo');
    const nuevoDispId = dispSel?.value ? parseInt(dispSel.value) : null;
    const dispActualNombre = usuarioEditando.dispositivo_nombre || null;
    const dispActual = dispActualNombre
      ? (_dispositivosLista.find(d => d.nombre === dispActualNombre) || null)
      : null;
    const dispActualId = dispActual ? dispActual.id : null;

    if (nuevoDispId !== dispActualId) {
      try {
        const res = await fetch(
          API + '/admin/prescriptores/' + usuarioEditando.prescriptor_id + '/dispositivo',
          {
            method: 'PUT',
            headers: MASCATE.authHeaders(),
            body: JSON.stringify({ dispositivo_id: nuevoDispId }),
          }
        );
        if (!res.ok) {
          const d = await res.json();
          alert('Error al asignar dispositivo: ' + (d.detail || 'Error desconocido.'));
          hayError = true;
        }
      } catch(e) { console.error(e); hayError = true; }
    }
  }

  // Guardar dispositivo si el usuario es beneficiario
  if (!hayError && usuarioEditando.rol === 'beneficiario' && usuarioEditando.beneficiario_id) {
    const dispBenefSel = document.getElementById('modal-disp-benef');
    const nuevoDispId  = dispBenefSel?.value ? parseInt(dispBenefSel.value) : null;
    const dispActualId = usuarioEditando.dispositivo_id || null;

    if (nuevoDispId !== dispActualId) {
      try {
        const res = await fetch(
          API + '/admin/beneficiarios/' + usuarioEditando.beneficiario_id + '/dispositivo',
          { method: 'PUT', headers: MASCATE.authHeaders(),
            body: JSON.stringify({ dispositivo_id: nuevoDispId }) }
        );
        if (!res.ok) {
          const d = await res.json();
          alert('Error al asignar dispositivo: ' + (d.detail || 'Error desconocido.'));
          hayError = true;
        }
      } catch(e) { console.error(e); hayError = true; }
    }
  }

  btn.textContent = 'Guardar cambios';
  btn.disabled    = false;

  if (!hayError) {
    cerrarModal();
    await cargarUsuarios();
    await cargarPendientes();
  }
}

async function crearPerfilDispositivo(userId) {
  try {
    const res = await fetch(API + '/admin/usuarios/' + userId + '/crear-dispositivo', {
      method: 'POST', headers: MASCATE.authHeaders()
    });
    const data = await res.json();
    if (res.ok) {
      // Actualizar caché y reabrir modal
      const idx = todosLosUsuarios.findIndex(u => u.id === userId);
      if (idx !== -1) todosLosUsuarios[idx] = data;
      usuarioEditando = data;
      abrirModal(userId);
    } else {
      alert('Error: ' + (data.detail || 'No se pudo crear el perfil.'));
    }
  } catch(e) {
    alert('Error de conexión.');
  }
}

async function eliminarUsuario() {
  if (!usuarioEditando) return;
  const nombre = usuarioEditando.nombre || usuarioEditando.email;
  if (!confirm(`¿Eliminar permanentemente a "${nombre}"?\nEsta acción no se puede deshacer.`)) return;

  const btn = document.getElementById('modal-btn-eliminar');
  btn.textContent = 'Eliminando...'; btn.disabled = true;
  try {
    const res = await fetch(API + '/admin/usuarios/' + usuarioEditando.id, {
      method: 'DELETE', headers: MASCATE.authHeaders(),
    });
    if (res.ok || res.status === 204) {
      cerrarModal();
      await cargarUsuarios();
      await cargarPendientes();
    } else {
      const d = await res.json().catch(() => ({}));
      alert('Error: ' + (d.detail || 'No se pudo eliminar.'));
    }
  } catch(e) { console.error(e); alert('Error de conexión.'); }
  btn.textContent = 'Eliminar'; btn.disabled = false;
}

async function restablecerPassword() {
  if (!usuarioEditando) return;
  const nombre = usuarioEditando.nombre || usuarioEditando.email;
  if (!confirm(`¿Enviar correo de restablecimiento de contraseña a "${nombre}" (${usuarioEditando.email})?`)) return;

  const btn = document.getElementById('modal-btn-reset');
  btn.textContent = 'Enviando...'; btn.disabled = true;
  try {
    const res = await fetch(API + '/admin/usuarios/' + usuarioEditando.id + '/restablecer-password', {
      method: 'POST', headers: MASCATE.authHeaders(),
    });
    const d = await res.json().catch(() => ({}));
    if (res.ok) {
      cerrarModal();
      const toast = document.createElement('div');
      toast.textContent = '✓ ' + (d.message || 'Correo enviado');
      toast.style.cssText = 'position:fixed;bottom:1.5rem;right:1.5rem;z-index:2000;background:var(--primary);color:#fff;padding:0.75rem 1.25rem;border-radius:var(--radius-md);font-size:0.85rem;font-weight:600;box-shadow:0 4px 20px rgba(0,0,0,0.2)';
      document.body.appendChild(toast);
      setTimeout(() => toast.remove(), 4000);
    } else {
      alert('Error: ' + (d.detail || 'No se pudo enviar el correo.'));
    }
  } catch(e) { console.error(e); alert('Error de conexión.'); }
  btn.textContent = 'Restablecer contraseña'; btn.disabled = false;
}

// Cerrar modal al click fuera
document.getElementById('modal-overlay')?.addEventListener('click', e => {
  if (e.target === document.getElementById('modal-overlay')) cerrarModal();
});

async function cargarAsignados() {
  try {
    const asignados = await (await fetch(API + '/prescriptores/mis-asignados', MASCATE.authGet())).json();

    todosLosUsuarios = Array.isArray(asignados) ? asignados : [];

    // Adaptar encabezado de tabla
    const thead = document.getElementById('users-thead');
    if (thead) thead.innerHTML = `<tr>
      <th>Beneficiarix</th><th>Correo</th><th>Teléfono</th><th>Última sesión</th><th>Días sin sesión</th><th>Estado</th><th>Acciones</th>
    </tr>`;

    const h1 = document.querySelector('h1');
    if (h1) h1.textContent = 'Mis beneficiarixs';
    const p = document.querySelector('.page-header p');
    if (p) p.textContent = 'Personas a tu cargo y estado de seguimiento.';

    document.querySelectorAll('.stat-card')[2]?.remove();
    document.querySelectorAll('.stat-card')[2]?.remove();

    const urgentes = todosLosUsuarios.filter(a => a.estado === 'urgente').length;
    setStats([
      { id:'stat-0', val: todosLosUsuarios.length },
      { id:'stat-1', val: todosLosUsuarios.length },
      { id:'stat-2', val: urgentes },
    ]);

    const labels = document.querySelectorAll('.stat-label');
    if (labels[0]) labels[0].textContent = 'Total';
    if (labels[1]) labels[1].textContent = 'Beneficiarixs';
    if (labels[2]) labels[2].textContent = 'Urgentes';

    document.getElementById('panel-pendientes')?.remove();

    renderTablaAsignados(todosLosUsuarios);
  } catch(e) { console.error('Error cargando asignados:', e); }
}

const ESTADO_PRESC = {
  al_dia:       { label: 'Al día',       cls: 'green'  },
  revisar:      { label: 'Revisar',      cls: 'mustard' },
  urgente:      { label: 'Urgente',      cls: 'rust'    },
  desvinculado: { label: 'Desvinculado', cls: 'gray'    },
};

function renderTablaAsignados(lista) {
  const tbody = document.getElementById('users-tbody');
  if (!tbody) return;
  if (!lista.length) {
    tbody.innerHTML = '<tr><td colspan="7" style="color:var(--on-bg-muted);text-align:center;padding:1rem">Sin beneficiarixs asignados aún.</td></tr>';
    return;
  }
  tbody.innerHTML = lista.map(a => {
    const est      = ESTADO_PRESC[a.estado] || { label: a.estado, cls: '' };
    const ultima   = a.ultima_sesion
      ? new Date(a.ultima_sesion).toLocaleDateString('es-CO', { day:'2-digit', month:'short', year:'numeric' })
      : '—';
    const diasLabel = a.dias_sin_sesion != null ? `${a.dias_sin_sesion} días` : '—';
    const nomEsc   = (a.nombre_apodo || '').replace(/'/g, "\\'");
    return `<tr>
      <td><div style="display:flex;align-items:center;gap:0.6rem">
        <div class="list-avatar" style="width:1.8rem;height:1.8rem;font-size:0.7rem;flex-shrink:0">${ini(a.nombre_apodo)}</div>
        <span style="font-weight:600">${campo(a.nombre_apodo)}</span>
      </div></td>
      <td style="font-size:0.82rem;color:var(--on-bg-muted)">${campo(a.email)}</td>
      <td style="font-size:0.82rem">${campo(a.telefono)}</td>
      <td style="font-size:0.85rem;color:var(--on-bg-muted)">${ultima}</td>
      <td style="font-size:0.85rem">${diasLabel}</td>
      <td><span class="tag ${est.cls}">${est.label}</span></td>
      <td style="display:flex;gap:0.4rem;flex-wrap:wrap">
        <button class="btn btn-sm btn-green" style="font-size:0.78rem"
          onclick="irASeguimiento(${a.id},'${nomEsc}')">+ Seguimiento</button>
        <button class="btn btn-sm btn-outline" style="font-size:0.78rem"
          onclick="verSeguimientosUsu(${a.id}, '${nomEsc}')">Seguimientos</button>
        <button class="btn btn-sm btn-outline" style="color:var(--primary);border-color:var(--primary);font-size:0.78rem"
          onclick="abrirFicha(${a.id})">Ficha</button>
      </td>
    </tr>`;
  }).join('');
}

// ── Ficha primer contacto ─────────────────────────────────────────────────
let _fichaPcId = null;
let _fichaBenefId = null;

async function abrirFicha(beneficiarioId) {
  _fichaBenefId = beneficiarioId;
  _fichaPcId = null;

  const benef = todosLosUsuarios.find(u => u.id === beneficiarioId);
  const nombre = benef?.nombre || benef?.nombre_apodo || benef?.email || 'Beneficiarix';
  set('ficha-titulo', nombre);

  // Ocultar form, mostrar overlay en modo vista
  document.getElementById('ficha-form').style.display = 'none';
  document.getElementById('ficha-view').style.display = 'block';
  document.getElementById('ficha-btn-editar').style.display = 'none';
  document.getElementById('ficha-btn-guardar').style.display = 'none';
  document.getElementById('ficha-btn-cancelar').style.display = 'none';
  document.getElementById('ficha-view').innerHTML = '<div style="color:var(--on-bg-muted);font-size:0.85rem;padding:0.5rem">Cargando...</div>';

  const overlay = document.getElementById('ficha-overlay');
  if (overlay) overlay.style.display = 'flex';

  try {
    const pcs = await fetch(
      API + '/primer-contacto/?beneficiario_id=' + beneficiarioId,
      MASCATE.authGet()
    ).then(r => r.json());

    if (!Array.isArray(pcs) || !pcs.length) {
      document.getElementById('ficha-view').innerHTML =
        '<div style="color:var(--on-bg-muted);font-size:0.85rem;padding:0.5rem">Esta persona no tiene hoja de primer contacto registrada aún.</div>';
      return;
    }

    const pc = pcs[0];
    _fichaPcId = pc.id;
    renderFichaView(pc);
    document.getElementById('ficha-btn-editar').style.display = 'inline-flex';
  } catch(e) {
    console.error(e);
    document.getElementById('ficha-view').innerHTML =
      '<div style="color:var(--error);padding:0.5rem">Error al cargar la ficha.</div>';
  }
}

function renderFichaView(pc) {
  const fecha = pc.fecha_contacto
    ? new Date(pc.fecha_contacto + 'T00:00:00').toLocaleDateString('es-CO', { day:'2-digit', month:'long', year:'numeric' })
    : '—';
  const marcaTemporal = pc.created_at
    ? new Date(pc.created_at).toLocaleString('es-CO', { day:'2-digit', month:'short', year:'numeric', hour:'2-digit', minute:'2-digit' })
    : null;
  const fnac = pc.fecha_nacimiento
    ? new Date(pc.fecha_nacimiento + 'T00:00:00').toLocaleDateString('es-CO', { day:'2-digit', month:'long', year:'numeric' })
    : '—';
  const edad = pc.fecha_nacimiento ? calcEdad(pc.fecha_nacimiento) + ' años' : null;

  const f = (l, v) => (v != null && v !== '' && v !== false)
    ? `<div><div style="font-size:0.73rem;color:var(--on-bg-muted)">${l}</div><div style="font-size:0.86rem;font-weight:500">${v === true ? 'Sí' : v === false ? 'No' : v}</div></div>`
    : '';
  const sec = (titulo) => `<div style="font-size:0.75rem;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;color:var(--on-bg-muted);margin:1rem 0 0.5rem;border-top:1px solid var(--border);padding-top:0.75rem">${titulo}</div>`;
  const grid = (...items) => `<div style="display:grid;grid-template-columns:1fr 1fr;gap:0.5rem 1.25rem">${items.join('')}</div>`;
  const bloque = (l, v) => v ? `<div style="margin-top:0.6rem"><div style="font-size:0.73rem;color:var(--on-bg-muted);margin-bottom:0.2rem">${l}</div><div style="font-size:0.85rem;line-height:1.5;white-space:pre-wrap">${v}</div></div>` : '';

  const dir = [pc.clase_via, pc.numero_via_principal, pc.letra_via_principal, '#', pc.numero_via_generadora, pc.letra_via_generadora, '-', pc.numero_predio]
    .filter(Boolean).join(' ').replace('# -', '#').trim();

  document.getElementById('ficha-view').innerHTML = `
    ${sec('Datos personales')}
    ${grid(
      f('Fecha de nacimiento', fnac),
      f('Edad', edad),
      f('Género', pc.genero),
      f('Teléfono', pc.telefono),
      f('Localidad', pc.localidad),
      f('Estado civil', pc.estado_civil),
      f('N.º hijos', pc.num_hijos),
      f('Pertenencia étnica', pc.pertenencia_etnica),
      f('Etnia', pc.etnia),
      f('Religión', pc.religion),
    )}

    ${sec('Evento de contacto · ' + fecha)}
    ${marcaTemporal ? `<div style="font-size:0.78rem;color:var(--on-bg-muted);margin-bottom:0.4rem">🕐 Registrado el ${marcaTemporal}</div>` : ''}
    ${grid(
      f('Hora', pc.hora_contacto),
      f('UPZ', pc.upz),
      f('Barrio', pc.barrio),
      f('Forma de contacto', pc.forma_contacto),
    )}
    ${dir ? `<div style="margin-top:0.5rem">${f('Dirección', dir)}</div>` : ''}
    ${f('Con quién vive', pc.con_quien_vive)}

    ${sec('Convenio y DBC')}
    ${grid(
      f('Convenio 515', pc.convenio_515),
      f('DBC', pc.tipo_dbc),
      f('Número de caso', pc.numero_caso),
      f('Procesos previos', pc.procesos_previos),
    )}

    ${sec('Fuente de información')}
    ${grid(
      f('Fuente', pc.nombre_fuente),
      f('Teléfono fuente', pc.telefono_fuente),
      f('Género fuente', pc.genero_fuente),
      f('Vínculo fuente', pc.vinculo_fuente),
    )}

    ${sec('Educación y trabajo')}
    ${grid(
      f('Sabe leer/escribir', pc.sabe_leer_escribir),
      f('Usa computador', pc.sabe_usar_computador),
      f('Escolaridad', pc.escolaridad),
      f('Ocupación', pc.ocupacion),
    )}

    ${sec('Redes de apoyo')}
    ${grid(
      f('Apoyo familiar', pc.apoyo_familiar),
      f('Apoyo comunitario', pc.apoyo_comunitario),
      f('Apoyo institucional', pc.apoyo_institucional),
      f('Otro actor social', pc.apoyo_otro_actor),
      f('¿Cuál actor?', pc.cual_actor_social),
    )}

    ${(pc.tiene_persona_apoyo) ? `
    ${sec('Persona de apoyo')}
    ${grid(
      f('Nombre', pc.nombre_persona_apoyo),
      f('Teléfono', pc.telefono_persona_apoyo),
      f('Vínculo', pc.vinculo_persona_apoyo),
      f('Código vínculo', pc.tipo_vinculo_codigo),
      f('Género', pc.genero_apoyo),
    )}` : ''}

    ${sec('Recreación y participación')}
    ${grid(
      f('Practica deporte', pc.practica_deporte),
      f('Tiene tiempo rec.', pc.tiene_tiempo_recreacion),
      f('Cuánto tiempo', pc.cuanto_tiempo_recreacion),
      f('Conoce espacios', pc.conoce_espacios),
      f('Ha participado', pc.ha_participado),
    )}

    ${pc.situaciones_presentes ? `
    ${sec('Situaciones presentes')}
    <div style="font-size:0.85rem;line-height:1.7">${pc.situaciones_presentes.split(' | ').map(s => `<span style="display:inline-block;background:var(--primary-dim);color:var(--primary);border-radius:4px;padding:0.15rem 0.45rem;margin:0.1rem;font-size:0.78rem">${s}</span>`).join('')}</div>` : ''}

    ${bloque('Peticiones', pc.peticiones)}
    ${bloque('Descripción del caso', pc.descripcion_caso)}

    ${sec('Registrador')}
    ${grid(
      f('Rol', pc.rol_registrador),
      f('Nombre', pc.nombre_registrador),
      f('Teléfono', pc.telefono_registrador),
    )}

    ${_fichaBenefId && (() => {
      const u = todosLosUsuarios.find(x => x.id === _fichaBenefId);
      if (!u?.politica_privacidad_at) return '';
      const fechaPriv = new Date(u.politica_privacidad_at).toLocaleDateString('es-CO', { day:'2-digit', month:'long', year:'numeric' });
      return sec('Política de privacidad') +
        `<div style="font-size:0.85rem;color:var(--success,#2e7d32);font-weight:500">✓ Aceptada el ${fechaPriv}</div>`;
    })()}
  `;
}

function calcEdad(fnac) {
  const hoy = new Date(), nac = new Date(fnac + 'T00:00:00');
  let edad = hoy.getFullYear() - nac.getFullYear();
  const m = hoy.getMonth() - nac.getMonth();
  if (m < 0 || (m === 0 && hoy.getDate() < nac.getDate())) edad--;
  return edad;
}

function toggleEditarFicha() {
  // Cargar los datos actuales en el form
  const pcs = [];  // Recuperar del _fichaPcId si es necesario
  document.getElementById('ficha-view').style.display = 'none';
  document.getElementById('ficha-form').style.display = 'block';
  document.getElementById('ficha-btn-editar').style.display = 'none';
  document.getElementById('ficha-btn-guardar').style.display = 'inline-flex';
  document.getElementById('ficha-btn-cancelar').style.display = 'inline-flex';

  // Rellenar form con datos actuales del view (re-fetch para tener datos frescos)
  fetch(API + '/primer-contacto/' + _fichaPcId, MASCATE.authGet())
    .then(r => r.json())
    .then(pc => {
      v('fe-fnac',       pc.fecha_nacimiento || '');
      v('fe-genero',     pc.genero || '');
      v('fe-telefono',   pc.telefono || '');
      v('fe-localidad',  pc.localidad || '');
      v('fe-fecha',      pc.fecha_contacto || '');
      v('fe-hora',       pc.hora_contacto || '');
      v('fe-upz',        pc.upz || '');
      v('fe-barrio',     pc.barrio || '');
      v('fe-forma',      pc.forma_contacto || '');
      v('fe-fuente',     pc.nombre_fuente || '');
      v('fe-vinculo',    pc.vinculo_fuente || '');
      v('fe-procesos',   pc.procesos_previos ?? '');
      v('fe-situaciones',pc.situaciones_presentes || '');
      v('fe-peticiones', pc.peticiones || '');
      v('fe-descripcion',pc.descripcion_caso || '');
    })
    .catch(console.error);
}

function v(id, val) {
  const el = document.getElementById(id);
  if (el) el.value = val;
}

function cancelarEditarFicha() {
  document.getElementById('ficha-form').style.display = 'none';
  document.getElementById('ficha-view').style.display = 'block';
  document.getElementById('ficha-btn-editar').style.display = 'inline-flex';
  document.getElementById('ficha-btn-guardar').style.display = 'none';
  document.getElementById('ficha-btn-cancelar').style.display = 'none';
}

async function guardarFicha() {
  if (!_fichaPcId) return;
  const btn = document.getElementById('ficha-btn-guardar');
  btn.textContent = 'Guardando...'; btn.disabled = true;

  const payload = {
    fecha_nacimiento:      g('fe-fnac')        || null,
    genero:                g('fe-genero')       || null,
    telefono:              g('fe-telefono')     || null,
    localidad:             g('fe-localidad')    || null,
    fecha_contacto:        g('fe-fecha')        || null,
    hora_contacto:         g('fe-hora')         || null,
    upz:                   g('fe-upz')          || null,
    barrio:                g('fe-barrio')       || null,
    forma_contacto:        g('fe-forma')        || null,
    nombre_fuente:         g('fe-fuente')       || null,
    vinculo_fuente:        g('fe-vinculo')      || null,
    procesos_previos:      g('fe-procesos') ? parseInt(g('fe-procesos')) : null,
    situaciones_presentes: g('fe-situaciones')  || null,
    peticiones:            g('fe-peticiones')   || null,
    descripcion_caso:      g('fe-descripcion')  || null,
  };

  try {
    const res = await fetch(API + '/primer-contacto/' + _fichaPcId, {
      method: 'PUT',
      headers: MASCATE.authHeaders(),
      body: JSON.stringify(payload),
    });
    if (res.ok) {
      const pc = await res.json();
      cancelarEditarFicha();
      renderFichaView(pc);
    } else {
      const d = await res.json().catch(() => ({}));
      alert('Error: ' + (d.detail || 'No se pudo guardar.'));
    }
  } catch(e) { console.error(e); alert('Error de conexión.'); }

  btn.textContent = 'Guardar'; btn.disabled = false;
}

function g(id) {
  return document.getElementById(id)?.value || '';
}

function cerrarFicha() {
  document.getElementById('ficha-overlay').style.display = 'none';
  _fichaPcId = null;
  _fichaBenefId = null;
  document.getElementById('ficha-form').style.display = 'none';
  document.getElementById('ficha-view').style.display = 'block';
  document.getElementById('ficha-btn-editar').style.display = 'none';
  document.getElementById('ficha-btn-guardar').style.display = 'none';
  document.getElementById('ficha-btn-cancelar').style.display = 'none';
}

// ── Ficha prescriptor ────────────────────────────────────────────────────
function abrirFichaPresc(usuarioId) {
  const u = todosLosUsuarios.find(x => x.id === usuarioId);
  if (!u) return;

  set('ficha-titulo', u.nombre || u.email);
  document.getElementById('ficha-form').style.display = 'none';
  document.getElementById('ficha-view').style.display = 'block';
  document.getElementById('ficha-btn-editar').style.display = 'none';
  document.getElementById('ficha-btn-guardar').style.display = 'none';
  document.getElementById('ficha-btn-cancelar').style.display = 'none';
  renderFichaPrescView(u);
  document.getElementById('ficha-overlay').style.display = 'flex';
}

function renderFichaPrescView(u) {
  const f = (l, v) => (v != null && v !== '')
    ? `<div><div style="font-size:0.73rem;color:var(--on-bg-muted)">${l}</div><div style="font-size:0.86rem;font-weight:500">${v}</div></div>`
    : '';
  const sec = t => `<div style="font-size:0.75rem;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;color:var(--on-bg-muted);margin:1rem 0 0.5rem;border-top:1px solid var(--border);padding-top:0.75rem">${t}</div>`;
  const grid = (...items) => `<div style="display:grid;grid-template-columns:1fr 1fr;gap:0.5rem 1.25rem">${items.join('')}</div>`;

  const fecha = u.fecha_registro
    ? new Date(u.fecha_registro).toLocaleDateString('es-CO', { day:'2-digit', month:'long', year:'numeric' })
    : '—';
  const stColor = u.status === 'activo' ? 'var(--success,#2e7d32)' : u.status === 'pendiente' ? 'var(--warning,#f57f17)' : 'var(--error)';

  document.getElementById('ficha-view').innerHTML = `
    ${sec('Datos personales')}
    ${grid(
      f('Nombre completo', u.nombre),
      f('Correo electrónico', u.email),
      f('Teléfono', u.telefono),
      f('Perfil / disciplina', u.perfil_disciplina),
    )}

    ${sec('Vinculación')}
    ${grid(
      f('Dispositivo asignado', u.dispositivo_nombre),
      f('Fecha de registro', fecha),
    )}
    <div style="margin-top:0.5rem">
      ${f('Estado', `<span style="font-weight:600;color:${stColor}">${u.status}</span>`)}
    </div>

    ${u.politica_privacidad_at ? (() => {
      const fechaPriv = new Date(u.politica_privacidad_at).toLocaleDateString('es-CO', { day:'2-digit', month:'long', year:'numeric' });
      return sec('Política de privacidad') +
        `<div style="font-size:0.85rem;color:var(--success,#2e7d32);font-weight:500">✓ Aceptada el ${fechaPriv}</div>`;
    })() : ''}
  `;
}

document.getElementById('ficha-overlay')?.addEventListener('click', e => {
  if (e.target === document.getElementById('ficha-overlay')) cerrarFicha();
});

function toast(msg) {
  const t = document.createElement('div');
  t.textContent = msg;
  t.style.cssText = 'position:fixed;bottom:1.5rem;right:1.5rem;z-index:2000;background:var(--primary);color:#fff;padding:0.75rem 1.25rem;border-radius:var(--radius-md);font-size:0.85rem;font-weight:600;box-shadow:0 4px 20px rgba(0,0,0,0.2)';
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 3500);
}

function irASeguimiento(benefId, nombre) {
  window.location.href = '/reportar-info?tab=seguimiento&bid=' + benefId + '&bnombre=' + encodeURIComponent(nombre);
}

// ═══════════════════════════════════════════════════════════════
// SEGUIMIENTO DESDE TABLA DE USUARIOS (prescriptor)
// ═══════════════════════════════════════════════════════════════
function abrirModalSegUsu(benefId, nombre) {
  document.getElementById('seg-usu-benef-id').value = benefId;
  document.getElementById('seg-usu-nombre').textContent = nombre;
  document.getElementById('seg-usu-tipo').value = '';
  document.getElementById('seg-usu-observaciones').value = '';
  document.getElementById('seg-usu-error').style.display = 'none';
  document.getElementById('modal-seg-usu-overlay').style.display = 'flex';
}

async function verSeguimientosUsu(benefId, nombre) {
  document.getElementById('ver-segs-titulo').textContent = nombre;
  document.getElementById('ver-segs-count').textContent  = '...';
  document.getElementById('ver-segs-list').innerHTML     = '<div style="color:var(--on-bg-muted);font-size:0.85rem">Cargando...</div>';
  document.getElementById('modal-ver-segs-overlay').style.display = 'flex';
  try {
    const data = await (await fetch(API + '/prescriptores/seguimientos?beneficiario_id=' + benefId, MASCATE.authGet())).json();
    document.getElementById('ver-segs-count').textContent = data.length;
    if (!data.length) {
      document.getElementById('ver-segs-list').innerHTML = '<div style="color:var(--on-bg-muted);font-size:0.85rem;padding:0.5rem">Sin seguimientos registrados aún.</div>';
      return;
    }
    document.getElementById('ver-segs-list').innerHTML = data.map(s => {
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
    document.getElementById('ver-segs-list').innerHTML = '<div style="color:var(--error);font-size:0.85rem">Error al cargar.</div>';
  }
}

async function guardarSeguimientoUsu() {
  const tipo    = document.getElementById('seg-usu-tipo').value.trim();
  const obs     = document.getElementById('seg-usu-observaciones').value.trim();
  const benefId = parseInt(document.getElementById('seg-usu-benef-id').value);
  const errEl   = document.getElementById('seg-usu-error');
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
      document.getElementById('modal-seg-usu-overlay').style.display = 'none';
      const t = document.createElement('div');
      t.textContent = '✓ Seguimiento guardado';
      t.style.cssText = 'position:fixed;bottom:1.5rem;right:1.5rem;z-index:2000;background:var(--primary);color:#fff;padding:0.75rem 1.25rem;border-radius:var(--radius-md);font-size:0.85rem;font-weight:600;box-shadow:0 4px 20px rgba(0,0,0,0.2)';
      document.body.appendChild(t);
      setTimeout(() => t.remove(), 3000);
    } else {
      errEl.textContent = data.detail || 'Error al guardar.';
      errEl.style.display = 'block';
    }
  } catch(e) { errEl.textContent = 'Error de conexión.'; errEl.style.display = 'block'; }
}

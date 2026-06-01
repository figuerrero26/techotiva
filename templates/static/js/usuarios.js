/* ═══ MASCATE — USUARIOS JS ═══ */
const API = window.location.origin;
MASCATE.guardAuth();

let todosLosUsuarios = [];
let usuarioEditando  = null;

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
    // Obtener el dispositivo_id del perfil propio
    const reMe = await fetch(API + '/dispositivos/me', MASCATE.authGet());
    console.log('[dispositivo] GET /dispositivos/me →', reMe.status);
    const me = await reMe.json();
    console.log('[dispositivo] /dispositivos/me payload:', me);
    const dispositivoId = me.id;

    // Traer beneficiarios del dispositivo
    const reBen = await fetch(API + '/dispositivos/' + dispositivoId + '/beneficiarios', MASCATE.authGet());
    console.log('[dispositivo] GET /dispositivos/' + dispositivoId + '/beneficiarios →', reBen.status);
    const beneficiarios = await reBen.json();
    console.log('[dispositivo] beneficiarios payload:', beneficiarios);

    todosLosUsuarios = beneficiarios;

    // Adaptar encabezado
    const h1 = document.querySelector('h1');
    if (h1) h1.textContent = 'Beneficiarixs del dispositivo';
    const p = document.querySelector('.page-header p');
    if (p) p.textContent = 'Personas registradas y vinculadas a este dispositivo.';

    // Ocultar stats de prescriptores y dispositivos — no aplica
    document.querySelectorAll('.stat-card')[2]?.remove();
    document.querySelectorAll('.stat-card')[2]?.remove(); // el 3ro pasa a ser [2] tras el primero

    const urgentes = beneficiarios.filter(u => u.estado === 'urgente').length;
    setStats([
      { id:'stat-0', val: beneficiarios.length },
      { id:'stat-1', val: beneficiarios.length },
      { id:'stat-2', val: urgentes },
    ]);

    const labels = document.querySelectorAll('.stat-label');
    if (labels[0]) labels[0].textContent = 'Total';
    if (labels[1]) labels[1].textContent = 'Beneficiarixs';
    if (labels[2]) labels[2].textContent = 'Urgentes';

    // Ocultar panel pendientes y botón nuevo usuario — dispositivo no los gestiona
    document.getElementById('panel-pendientes')?.remove();
    document.querySelector('.btn-mustard')?.remove();

    renderTabla(todosLosUsuarios);
  } catch(e) { console.error('Error cargando beneficiarios del dispositivo:', e); }
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
    tbody.innerHTML = '<tr><td colspan="8" style="color:var(--on-bg-muted);text-align:center;padding:1rem">Sin usuarios.</td></tr>';
    return;
  }

  tbody.innerHTML = lista.map(u => {
    const rolColor = u.rol === 'beneficiario' ? 'mustard'
                   : u.rol === 'prescriptor'  ? 'blue'
                   : u.rol === 'dispositivo'  ? 'purple' : 'green';
    const stColor  = u.status === 'activo'    ? 'green'
                   : u.status === 'pendiente' ? 'mustard' : 'rust';
    return `<tr>
      <td>
        <div style="display:flex;align-items:center;gap:0.6rem">
          <div class="list-avatar"
               style="width:1.8rem;height:1.8rem;font-size:0.7rem;flex-shrink:0">
            ${ini(u.nombre||u.email)}
          </div>
          ${campo(u.nombre, u.email)}
        </div>
      </td>
      <td><span class="tag ${rolColor}">${ROL_LABELS[u.rol] ?? u.rol}</span></td>
      <td>${campo(u.fecha_nacimiento
            ? new Date(u.fecha_nacimiento).toLocaleDateString('es-CO') : null)}</td>
      <td>${campo(u.localidad)}</td>
      <td>${campo(u.genero)}</td>
      <td><span class="tag ${stColor}">${u.status}</span></td>
      <td>${campo(u.telefono)}</td>
      <td>
        <button class="btn btn-sm btn-outline"
          onclick="abrirModal(${u.id})">Editar</button>
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
function abrirModal(id) {
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

  const overlay = document.getElementById('modal-overlay');
  if (overlay) { overlay.style.display = 'flex'; }
}

function cerrarModal() {
  const overlay = document.getElementById('modal-overlay');
  if (overlay) overlay.style.display = 'none';
  usuarioEditando = null;
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

  btn.textContent = 'Guardar cambios';
  btn.disabled    = false;

  if (!hayError) {
    cerrarModal();
    await cargarUsuarios();
    await cargarPendientes();
  }
}

// Cerrar modal al click fuera
document.getElementById('modal-overlay')?.addEventListener('click', e => {
  if (e.target === document.getElementById('modal-overlay')) cerrarModal();
});

async function cargarAsignados() {
  try {
    const reAs = await fetch(API + '/prescriptores/mis-asignados', MASCATE.authGet());
    console.log('[prescriptor] GET /prescriptores/mis-asignados →', reAs.status);
    const asignados = await reAs.json();
    console.log('[prescriptor] mis-asignados payload:', asignados);

    // Normalizar para que initFiltros y renderTabla funcionen igual
    // El endpoint devuelve nombre_apodo en vez de nombre; aplanamos aquí
    todosLosUsuarios = asignados.map(a => ({
      ...a,
      nombre: a.nombre_apodo ?? a.nombre,
      rol:    'beneficiario',
      status: a.status ?? 'activo',   // puede que el endpoint devuelva 'estado' en vez de 'status'
      _dias:  a.dias_sin_sesion,
      _estado_seguimiento: a.estado,  // 'urgente' | 'revisar' | 'al_dia'
    }));

    // Adaptar encabezado
    const h1 = document.querySelector('h1');
    if (h1) h1.textContent = 'Mis personas asignadas';
    const p = document.querySelector('.page-header p');
    if (p) p.textContent = 'Personas bajo tu seguimiento y acompañamiento.';

    // Ocultar stats de prescriptores y dispositivos — no aplica
    document.querySelectorAll('.stat-card')[2]?.remove();
    document.querySelectorAll('.stat-card')[2]?.remove();

    setStats([
      { id:'stat-0', val: asignados.length },
      { id:'stat-1', val: asignados.length },
      { id:'stat-2', val: asignados.filter(a => a.estado === 'urgente').length },
    ]);

    const labels = document.querySelectorAll('.stat-label');
    if (labels[0]) labels[0].textContent = 'Asignados';
    if (labels[1]) labels[1].textContent = 'Total';
    if (labels[2]) labels[2].textContent = 'Urgentes';

    // Ocultar panel pendientes y botón nuevo usuario
    document.getElementById('panel-pendientes')?.remove();
    document.querySelector('.btn-mustard')?.remove();

    renderTablaAsignados(todosLosUsuarios);
  } catch(e) { console.error('Error cargando asignados:', e); }
}

function renderTablaAsignados(lista) {
  const tbody = document.getElementById('users-tbody');
  if (!tbody) return;
  if (!lista.length) {
    tbody.innerHTML = '<tr><td colspan="8" style="color:var(--on-bg-muted);text-align:center;padding:1rem">Sin personas asignadas aún.</td></tr>';
    return;
  }
  tbody.innerHTML = lista.map(a => {
    const est      = a._estado_seguimiento;
    const tagClass = est === 'urgente' ? 'rust' : est === 'revisar' ? 'mustard' : 'green';
    const label    = est === 'urgente' ? 'Urgente' : est === 'revisar' ? 'Revisar' : 'Al día';
    const dias     = a._dias != null ? 'Hace ' + a._dias + ' días' : '—';
    return `<tr>
      <td><div style="display:flex;align-items:center;gap:0.6rem">
        <div class="list-avatar" style="width:1.8rem;height:1.8rem;font-size:0.7rem;flex-shrink:0">${ini(a.nombre)}</div>
        ${campo(a.nombre)}
      </div></td>
      <td><span class="tag mustard">Beneficiarix</span></td>
      <td>${campo(a.fecha_nacimiento ? new Date(a.fecha_nacimiento).toLocaleDateString('es-CO') : null)}</td>
      <td>${campo(a.localidad)}</td>
      <td>${campo(a.genero)}</td>
      <td><span class="tag ${tagClass}">${label}</span></td>
      <td>${dias}</td>
      <td><button class="btn btn-sm btn-green" onclick="window.location.href='/reportar-info'">+ Registro</button></td>
    </tr>`;
  }).join('');
}

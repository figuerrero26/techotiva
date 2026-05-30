/* ═══ MASCATE — ROLES JS ═══ */
const API = window.location.origin;
MASCATE.guardAuth();

let todosLosUsuarios = [];

window.addEventListener('DOMContentLoaded', async () => {
  renderSidebar(MASCATE.nombre, MASCATE.email);
  await cargarUsuarios();
  initFiltros();
});

async function cargarUsuarios() {
  try {
    todosLosUsuarios = await (await fetch(API + '/admin/usuarios', MASCATE.authGet())).json();

    const benefs = todosLosUsuarios.filter(u => u.rol === 'beneficiario').length;
    const prescs = todosLosUsuarios.filter(u => u.rol === 'prescriptor').length;
    const disps  = todosLosUsuarios.filter(u => u.rol === 'dispositivo').length;
    const admins = todosLosUsuarios.filter(u => u.rol === 'admin').length;

    set('stat-benef', benefs); set('stat-presc', prescs);
    set('stat-disp',  disps);  set('stat-admin', admins);

    renderPendientes(todosLosUsuarios.filter(u => u.status === 'pendiente'));
    renderTabla(todosLosUsuarios);
  } catch(e) { console.error('Error:', e); }
}

function renderPendientes(pendientes) {
  const lista = document.getElementById('pendientes-list');
  const count = document.getElementById('pendientes-count');
  if (!lista) return;
  if (!pendientes.length) {
    lista.innerHTML = '<div style="color:var(--on-bg-muted);font-size:0.85rem;padding:0.5rem">Sin pendientes.</div>';
    if (count) count.style.display = 'none';
    return;
  }
  if (count) { count.textContent = pendientes.length; count.style.display = 'inline'; }
  lista.innerHTML = pendientes.map(u => `
    <div class="list-row" style="padding:0.6rem 0;border-bottom:1px solid var(--border)">
      <div class="list-avatar" style="flex-shrink:0">${ini(u.nombre||u.email)}</div>
      <div class="list-info">
        <div class="list-name">${campo(u.nombre, u.email)}</div>
        <div class="list-sub">${ROL_LABELS[u.rol]??u.rol}</div>
      </div>
      <div style="display:flex;gap:0.4rem;flex-shrink:0">
        <button class="btn btn-sm btn-green" onclick="aprobar(${u.id})">✓</button>
        <button class="btn btn-sm btn-outline" style="color:var(--error);border-color:var(--error)"
          onclick="rechazar(${u.id})">✕</button>
      </div>
    </div>`).join('');
}

function renderTabla(lista) {
  const tbody = document.getElementById('roles-tbody');
  if (!tbody) return;
  if (!lista.length) {
    tbody.innerHTML = '<tr><td colspan="6" style="color:var(--on-bg-muted);text-align:center;padding:1rem">Sin usuarios.</td></tr>';
    return;
  }
  tbody.innerHTML = lista.map(u => {
    const rolColor = u.rol==='beneficiario'?'mustard':u.rol==='prescriptor'?'blue':u.rol==='dispositivo'?'purple':'rust';
    const stColor  = u.status==='activo'?'green':u.status==='pendiente'?'mustard':'rust';
    const fecha    = u.fecha_registro ? new Date(u.fecha_registro).toLocaleDateString('es-CO') : '—';
    return `<tr>
      <td><div style="display:flex;align-items:center;gap:0.5rem">
        <div class="list-avatar" style="width:1.6rem;height:1.6rem;font-size:0.65rem;flex-shrink:0">${ini(u.nombre||u.email)}</div>
        ${campo(u.nombre, '—')}
      </div></td>
      <td style="font-size:0.82rem;color:var(--on-bg-muted)">${u.email}</td>
      <td><span class="tag ${rolColor}">${ROL_LABELS[u.rol]??u.rol}</span></td>
      <td><span class="tag ${stColor}">${u.status}</span></td>
      <td style="font-size:0.82rem">${fecha}</td>
      <td>
        <select onchange="cambiarRolDirecto(${u.id}, this.value, this)"
                style="font-size:0.78rem;padding:0.2rem 0.4rem">
          <option value="beneficiario" ${u.rol==='beneficiario'?'selected':''}>Beneficiarix</option>
          <option value="prescriptor"  ${u.rol==='prescriptor' ?'selected':''}>Prescriptxr</option>
          <option value="dispositivo"  ${u.rol==='dispositivo' ?'selected':''}>Dispositivo</option>
          <option value="admin"        ${u.rol==='admin'       ?'selected':''}>Admin</option>
        </select>
      </td>
    </tr>`;
  }).join('');
}

function initFiltros() {
  const search = document.getElementById('search-input');
  const rolSel = document.getElementById('role-select');
  function filtrar() {
    const q = (search?.value??'').toLowerCase();
    const r = rolSel?.value ?? 'todos';
    renderTabla(todosLosUsuarios.filter(u => {
      const txt = (u.nombre||u.email||'').toLowerCase();
      return txt.includes(q) && (r==='todos'||u.rol===r);
    }));
  }
  search?.addEventListener('input', filtrar);
  rolSel?.addEventListener('change', filtrar);
}

async function cambiarRolDirecto(id, nuevoRol, selectEl) {
  const original = todosLosUsuarios.find(u => u.id === id)?.rol;
  if (nuevoRol === original) return;
  if (!confirm(`¿Cambiar rol a "${ROL_LABELS[nuevoRol]}"?`)) {
    selectEl.value = original; return;
  }
  const { ok, data } = await MASCATE.cambiarRol(id, nuevoRol);
  if (ok) { mostrarToast('✓ Rol actualizado'); await cargarUsuarios(); }
  else { alert('Error: ' + (data.detail||'No se pudo cambiar.')); selectEl.value = original; }
}

async function aprobar(id) {
  const res = await fetch(API + '/admin/usuarios/' + id + '/aprobar',
    { method: 'POST', headers: MASCATE.authHeaders() });
  if (res.ok) { mostrarToast('✓ Usuario aprobado'); await cargarUsuarios(); }
  else { const d = await res.json(); alert('Error: ' + (d.detail||'No se pudo aprobar.')); }
}

async function rechazar(id) {
  if (!confirm('¿Desactivar este usuario?')) return;
  const res = await fetch(API + '/admin/usuarios/' + id + '/estado',
    { method: 'PUT', headers: MASCATE.authHeaders(), body: JSON.stringify({ status: 'inactivo' }) });
  if (res.ok) { mostrarToast('Usuario desactivado'); await cargarUsuarios(); }
  else { const d = await res.json(); alert('Error: ' + (d.detail||'No se pudo rechazar.')); }
}

function mostrarToast(msg) {
  const t = document.createElement('div');
  t.textContent = msg;
  t.style.cssText = `position:fixed;bottom:1.5rem;right:1.5rem;z-index:2000;
    background:var(--primary);color:#fff;padding:0.75rem 1.25rem;
    border-radius:var(--radius-md);font-size:0.85rem;font-weight:600;
    box-shadow:0 4px 20px rgba(0,0,0,0.2)`;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 3000);
}

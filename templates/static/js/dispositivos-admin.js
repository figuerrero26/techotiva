/* ═══ MASCATE — DISPOSITIVOS ADMIN JS ═══ */
const API = window.location.origin;
MASCATE.guardAuth();

let todosLosDisps = [];
let dispEditando  = null;

window.addEventListener('DOMContentLoaded', async () => {
  const { nombre, email } = MASCATE;
  renderSidebar(nombre, email);
  await cargarDispositivos();
  initFiltros();

  document.getElementById('btn-nuevo')?.addEventListener('click', () => abrirModal());
  document.getElementById('btn-exportar')?.addEventListener('click', () => exportarDispositivos('csv'));
  document.getElementById('modal-disp-overlay')?.addEventListener('click', e => {
    if (e.target === document.getElementById('modal-disp-overlay')) cerrarModal();
  });
});

async function cargarDispositivos() {
  try {
    todosLosDisps = await (await fetch(API + '/admin/dispositivos', MASCATE.authGet())).json();
    const activos = todosLosDisps.filter(d => d.activo).length;
    const benefs  = todosLosDisps.reduce((s, d) => s + (d.num_beneficiarios ?? 0), 0);
    const acts    = todosLosDisps.reduce((s, d) => s + (d.num_actividades   ?? 0), 0);
    setStats([
      { id:'stat-0', val: todosLosDisps.length },
      { id:'stat-1', val: activos },
      { id:'stat-2', val: benefs },
      { id:'stat-3', val: acts },
    ]);
    renderTabla(todosLosDisps);
  } catch(e) { console.error('Error cargando dispositivos:', e); }
}

function renderTabla(lista) {
  const tbody = document.getElementById('disp-tbody');
  if (!tbody) return;
  if (!lista.length) {
    tbody.innerHTML = '<tr><td colspan="7" style="color:var(--on-bg-muted);text-align:center;padding:1rem">Sin dispositivos.</td></tr>';
    return;
  }
  tbody.innerHTML = lista.map(d => `<tr>
    <td><div style="display:flex;align-items:center;gap:0.6rem">
      <div class="list-avatar" style="width:1.8rem;height:1.8rem;font-size:0.7rem;flex-shrink:0">${ini(d.nombre)}</div>
      <div>
        <div style="font-weight:600">${campo(d.nombre)}</div>
        ${d.email ? `<div style="font-size:0.75rem;color:var(--on-bg-muted)">${d.email}</div>` : ''}
      </div>
    </div></td>
    <td>${d.tipo_servicio ? `<span class="tag ${TAG_COLOR[d.tipo_servicio]??'mustard'}">${d.tipo_servicio}</span>` : '—'}</td>
    <td style="color:var(--primary);font-weight:700">${campo(d.num_beneficiarios, 0)}</td>
    <td>${campo(d.num_actividades, '—')}</td>
    <td>${renderPrescriptores(d)}</td>
    <td>${d.activo ? '<span class="tag green">Activo</span>' : '<span class="tag rust">Inactivo</span>'}</td>
    <td><button class="btn btn-sm btn-outline" onclick="abrirModal(${d.id})">Editar</button></td>
  </tr>`).join('');
}

function initFiltros() {
  const search = document.getElementById('search-input');
  const tipo   = document.getElementById('tipo-select');
  function filtrar() {
    const q = (search?.value ?? '').toLowerCase();
    const t = tipo?.value ?? 'todos';
    renderTabla(todosLosDisps.filter(d => {
      const matchQ = (d.nombre || '').toLowerCase().includes(q);
      const matchT = t === 'todos' || d.tipo_servicio === t;
      return matchQ && matchT;
    }));
  }
  search?.addEventListener('input', filtrar);
  document.getElementById('btn-filtrar')?.addEventListener('click', filtrar);
  tipo?.addEventListener('change', filtrar);
}

function abrirModal(id = null) {
  dispEditando = id ? todosLosDisps.find(d => d.id === id) : null;
  const d = dispEditando;
  set('modal-titulo', d ? 'Editar dispositivo' : 'Nuevo dispositivo');
  set('modal-btn-guardar', d ? 'Guardar cambios' : 'Crear dispositivo');
  document.getElementById('m-email').value     = d?.email        ?? '';
  document.getElementById('m-nombre').value    = d?.nombre       ?? '';
  document.getElementById('m-tipo').value      = d?.tipo_servicio?? '';
  document.getElementById('m-lugar').value     = d?.lugar_actividades ?? '';
  document.getElementById('m-ubicacion').value = d?.ubicacion    ?? '';
  document.getElementById('m-dia').value       = d?.dia_actividad?? '';
  document.getElementById('m-hora').value      = d?.hora_actividad?? '';
  document.getElementById('m-telefono').value  = d?.telefono     ?? '';
  document.getElementById('m-redes').value     = d?.redes_sociales ?? '';
  document.getElementById('m-email').disabled  = !!d; // no editar email en edición
  document.getElementById('modal-error').style.display = 'none';
  document.getElementById('modal-disp-overlay').style.display = 'flex';
}

function cerrarModal() {
  document.getElementById('modal-disp-overlay').style.display = 'none';
  dispEditando = null;
}

async function guardarDispositivo() {
  const errorEl = document.getElementById('modal-error');
  const btn     = document.getElementById('modal-btn-guardar');
  errorEl.style.display = 'none';

  const email     = document.getElementById('m-email').value.trim();
  const nombre    = document.getElementById('m-nombre').value.trim();
  if (!nombre) { errorEl.textContent = 'El nombre es obligatorio.'; errorEl.style.display = 'block'; return; }
  if (!dispEditando && !email) { errorEl.textContent = 'El email es obligatorio.'; errorEl.style.display = 'block'; return; }

  const payload = {
    email,
    nombre,
    tipo_servicio:     document.getElementById('m-tipo').value      || null,
    lugar_actividades: document.getElementById('m-lugar').value     || null,
    ubicacion:         document.getElementById('m-ubicacion').value || null,
    dia_actividad:     document.getElementById('m-dia').value       || null,
    hora_actividad:    document.getElementById('m-hora').value      || null,
    telefono:          document.getElementById('m-telefono').value  || null,
    redes_sociales:    document.getElementById('m-redes').value     || null,
  };

  btn.textContent = 'Guardando...'; btn.disabled = true;

  try {
    let res;
    if (dispEditando) {
      res = await fetch(API + '/dispositivos/' + dispEditando.id,
        { method: 'PUT', headers: MASCATE.authHeaders(), body: JSON.stringify(payload) });
    } else {
      res = await fetch(API + '/admin/dispositivos',
        { method: 'POST', headers: MASCATE.authHeaders(), body: JSON.stringify(payload) });
    }
    const data = await res.json();
    if (res.ok) {
      cerrarModal();
      await cargarDispositivos();
      mostrarToast(dispEditando ? '✓ Dispositivo actualizado' : '✓ Dispositivo creado');
    } else {
      errorEl.textContent = data.detail || 'Error al guardar.';
      errorEl.style.display = 'block';
    }
  } catch(e) {
    errorEl.textContent = 'Error de conexión.';
    errorEl.style.display = 'block';
  }
  btn.textContent = dispEditando ? 'Guardar cambios' : 'Crear dispositivo';
  btn.disabled = false;
}


function renderPrescriptores(d) {
  // Soporta tanto array (nuevo backend) como string único (legacy)
  const lista = Array.isArray(d.prescriptores) ? d.prescriptores
              : d.prescriptor                  ? [d.prescriptor]
              : [];
  if (!lista.length) return '<span style="color:var(--on-bg-muted)">—</span>';
  if (lista.length === 1) return lista[0];
  return lista.map(p =>
    `<span class="tag blue" style="margin:0.1rem;font-size:0.72rem">${p}</span>`
  ).join('');
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

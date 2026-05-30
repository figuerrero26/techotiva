/* ═══ MASCATE — ACTIVIDADES JS ═══ */
const API = window.location.origin;
MASCATE.guardAuth();

window.addEventListener('DOMContentLoaded', async () => {
  const { rol, nombre, email } = MASCATE;
  renderSidebar(nombre, email);
  await initNotifBtn();

  // Ocultar btn nueva actividad si no tiene permiso
  await cargarMiDispositivo();
  const btnNueva = document.getElementById('btn-nueva');
  if (rol === 'beneficiario') {
    btnNueva?.remove();
  } else {
    btnNueva?.addEventListener('click', () => abrirModalAct());
  }

  // "Ver todas →" en tabla
  document.querySelector('.panel-action')?.addEventListener('click', () => {
    // scroll a la tabla
    document.querySelector('table')?.scrollIntoView({ behavior:'smooth' });
  });

  try {
    let acts = [];
    if (rol === 'beneficiario') {
      acts = await (await fetch(API + '/beneficiarios/mis-actividades', MASCATE.authGet())).json();
    } else if (rol === 'dispositivo') {
      const disps = await (await fetch(API + '/dispositivos/', MASCATE.authGet())).json();
      if (disps.length) acts = await (await fetch(API + '/actividades/?dispositivo_id=' + disps[0].id)).json();
    } else {
      acts = await (await fetch(API + '/actividades/')).json();
    }

    const tipos   = new Set(acts.map(a => a.tipo)).size;
    const lugares = new Set(acts.map(a => a.lugar)).size;
    set('stat-total',   acts.length);
    set('stat-tipos',   tipos);
    set('stat-lugares', lugares);

    if (rol === 'admin') {
      try {
        const disps = await (await fetch(API + '/admin/dispositivos', MASCATE.authGet())).json();
        set('stat-dispositivos', disps.length);
      } catch(e) {}
    } else {
      set('stat-dispositivos', '—');
    }

    renderActCards('acts-cards', acts);
    renderActTabla('acts-tbody', acts);

  } catch(e) {
    console.error('Error cargando actividades:', e);
    const g = document.getElementById('acts-cards');
    if (g) g.innerHTML = '<div style="color:var(--error);padding:1rem">Error al cargar actividades.</div>';
  }
});

// ── Modal actividad ──────────────────────────────────────────────────────
let actEditando = null;
let miDispositivo = null;

// Cargar dispositivo propio al inicio (solo para dispositivo/admin)
async function cargarMiDispositivo() {
  if (MASCATE.rol === 'dispositivo') {
    try {
      miDispositivo = await (await fetch(API + '/dispositivos/me', MASCATE.authGet())).json();
    } catch(e) {}
  }
}

function abrirModalAct(act = null) {
  actEditando = act;
  const titulo = document.getElementById('modal-act-titulo');
  const btn    = document.getElementById('act-btn-guardar');
  if (titulo) titulo.textContent = act ? 'Editar actividad' : 'Nueva actividad';
  if (btn)    btn.textContent    = act ? 'Guardar cambios'  : 'Crear actividad';

  document.getElementById('act-nombre').value      = act?.nombre      ?? '';
  document.getElementById('act-tipo').value        = act?.tipo        ?? '';
  document.getElementById('act-emoji').value       = act?.emoji       ?? '';
  document.getElementById('act-lugar').value       = act?.lugar       ?? '';
  document.getElementById('act-dia').value         = act?.dia_semana  ?? '';
  document.getElementById('act-hora').value        = act?.hora        ?? '';
  document.getElementById('act-cupo').value        = act?.cupo_maximo ?? '';
  document.getElementById('act-fecha').value       = act?.fecha_inicio ?? '';
  document.getElementById('act-descripcion').value = act?.descripcion  ?? '';
  document.getElementById('act-error').style.display = 'none';
  document.getElementById('modal-act-overlay').style.display = 'flex';
}

function cerrarModalAct() {
  document.getElementById('modal-act-overlay').style.display = 'none';
  actEditando = null;
}

async function guardarActividad() {
  const errorEl = document.getElementById('act-error');
  const btn     = document.getElementById('act-btn-guardar');
  errorEl.style.display = 'none';

  const nombre = document.getElementById('act-nombre').value.trim();
  if (!nombre) {
    errorEl.textContent = 'El nombre es obligatorio.';
    errorEl.style.display = 'block'; return;
  }

  const payload = {
    nombre,
    tipo:         document.getElementById('act-tipo').value        || null,
    emoji:        document.getElementById('act-emoji').value       || '📋',
    lugar:        document.getElementById('act-lugar').value       || null,
    dia_semana:   document.getElementById('act-dia').value         || null,
    hora:         document.getElementById('act-hora').value        || null,
    cupo_maximo:  document.getElementById('act-cupo').value        ? parseInt(document.getElementById('act-cupo').value) : null,
    fecha_inicio: document.getElementById('act-fecha').value       || null,
    descripcion:  document.getElementById('act-descripcion').value || null,
  };

  // Para dispositivo, agregar dispositivo_id
  if (MASCATE.rol === 'dispositivo' && miDispositivo?.id) {
    payload.dispositivo_id = miDispositivo.id;
  }

  btn.textContent = 'Guardando...'; btn.disabled = true;

  try {
    let res;
    if (actEditando) {
      res = await fetch(API + '/actividades/' + actEditando.id,
        { method: 'PUT', headers: MASCATE.authHeaders(), body: JSON.stringify(payload) });
    } else {
      res = await fetch(API + '/actividades/',
        { method: 'POST', headers: MASCATE.authHeaders(), body: JSON.stringify(payload) });
    }
    const data = await res.json();
    if (res.ok) {
      cerrarModalAct();
      window.location.reload();
    } else {
      errorEl.textContent = data.detail || 'Error al guardar.';
      errorEl.style.display = 'block';
    }
  } catch(e) {
    errorEl.textContent = 'Error de conexión.';
    errorEl.style.display = 'block';
  }
  btn.textContent = actEditando ? 'Guardar cambios' : 'Crear actividad';
  btn.disabled = false;
}

document.getElementById('modal-act-overlay')?.addEventListener('click', e => {
  if (e.target === document.getElementById('modal-act-overlay')) cerrarModalAct();
});

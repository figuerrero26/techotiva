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
  if (rol === 'beneficiario' || rol === 'prescriptor') {
    btnNueva?.remove();
  } else {
    btnNueva?.addEventListener('click', () => abrirModalAct());
  }

  // "Ver todas →" en tabla
  document.querySelector('.panel-action')?.addEventListener('click', () => {
    document.querySelector('table')?.scrollIntoView({ behavior: 'smooth' });
  });

  try {
    let acts = [];
    if (rol === 'beneficiario') {
      // Beneficiario ve TODAS las actividades disponibles para inscribirse
      acts = await (await fetch(API + '/actividades/')).json();
    } else if (rol === 'dispositivo') {
      const me = await (await fetch(API + '/dispositivos/me', MASCATE.authGet())).json();
      if (me?.id) acts = await (await fetch(API + '/actividades/?dispositivo_id=' + me.id)).json();
    } else if (rol === 'prescriptor') {
      // Prescriptor ve solo actividades de su dispositivo, sin poder modificarlas
      const me = await (await fetch(API + '/prescriptores/me', MASCATE.authGet())).json();
      if (me?.dispositivo_id) {
        acts = await (await fetch(API + '/actividades/?dispositivo_id=' + me.dispositivo_id)).json();
      }
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
      } catch (e) {}
    } else {
      // Ocultar stat dispositivos para roles no admin
      const cardDisp = document.getElementById('stat-dispositivos')?.closest('.stat-card');
      if (cardDisp) cardDisp.style.display = 'none';
    }

    window._actsCache = acts;
    renderActCards('acts-cards', acts);
    renderActTabla('acts-tbody', acts);

  } catch (e) {
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
    } catch (e) {}
  }
}

function abrirModalAct(act = null) {
  actEditando = act;
  const titulo = document.getElementById('modal-act-titulo');
  const btn    = document.getElementById('act-btn-guardar');
  if (titulo) titulo.textContent = act ? 'Editar actividad' : 'Nueva actividad';
  if (btn)    btn.textContent    = act ? 'Guardar cambios'  : 'Crear actividad';

  document.getElementById('act-nombre').value      = act?.nombre       ?? '';
  document.getElementById('act-tipo').value        = act?.tipo         ?? '';
  document.getElementById('act-emoji').value       = act?.emoji        ?? '';
  document.getElementById('act-lugar').value       = act?.lugar        ?? '';
  document.getElementById('act-dia').value         = act?.dia_semana   ?? '';
  document.getElementById('act-hora').value        = act?.hora         ?? '';
  document.getElementById('act-cupo').value        = act?.cupo_maximo  ?? '';
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
    errorEl.style.display = 'block';
    return;
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

  btn.textContent = 'Guardando...';
  btn.disabled = true;

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
  } catch (e) {
    errorEl.textContent = 'Error de conexión.';
    errorEl.style.display = 'block';
  }

  btn.textContent = actEditando ? 'Guardar cambios' : 'Crear actividad';
  btn.disabled = false;
}

document.getElementById('modal-act-overlay')?.addEventListener('click', e => {
  if (e.target === document.getElementById('modal-act-overlay')) cerrarModalAct();
});

// ── Detalle de actividad ─────────────────────────────────────────────────
// CORRECCIÓN: bloque if/else if mal anidado, if duplicado, faltaba
//             asignar acciones.innerHTML y cerrar llaves correctamente.
window.verDetalleAct = function verDetalleAct(act) {
  const TAG_COLOR = {
    Artístico: 'mustard', Deportivo: 'green', Cultural: 'blue',
    Ambiental: 'green',   Educativo: 'blue',  Escucha:  'purple'
  };

  document.getElementById('det-nombre').textContent      = campo(act.nombre);
  document.getElementById('det-tipo').textContent        = campo(act.tipo);
  document.getElementById('det-tipo').className          = 'tag ' + (TAG_COLOR[act.tipo] ?? 'mustard');
  document.getElementById('det-descripcion').textContent = act.descripcion ?? '';

  const grid = document.getElementById('det-grid');
  grid.innerHTML = [
    { lbl: '📍 Lugar', val: act.lugar },
    { lbl: '🕓 Día',   val: act.dia_semana },
    { lbl: '⏰ Hora',  val: act.hora },
    { lbl: '👥 Cupo',  val: act.cupo_maximo ? act.cupo_maximo + ' personas' : null },
    { lbl: '🗓 Desde', val: act.fecha_inicio ? new Date(act.fecha_inicio).toLocaleDateString('es-CO') : null },
  ].filter(f => f.val).map(f => `
    <div class="contact-card"><div>
      <div class="contact-lbl">${f.lbl}</div>
      <div class="contact-val">${f.val}</div>
    </div></div>`).join('');

  // Acciones según rol
  const acciones = document.getElementById('det-acciones');
  const { rol } = MASCATE;
  let btns = '';

  if (rol === 'beneficiario') {
    btns = `<button class="btn btn-sm btn-green" onclick="inscribirse(${act.id})">✓ Inscribirme</button>`;
  } else if (rol === 'dispositivo' || rol === 'admin') {
    btns = `
      <button class="btn btn-sm btn-outline"
        onclick="document.getElementById('modal-det-overlay').style.display='none';
                 abrirModalAct(window._actsCache?.find(x=>x.id===${act.id}))">
        ✏️ Editar
      </button>
      <button class="btn btn-sm btn-outline"
        style="color:var(--error);border-color:var(--error)"
        onclick="eliminarAct(${act.id})">
        🗑 Eliminar
      </button>`;
  }

  // CORRECCIÓN: asignar los botones al contenedor
  if (acciones) acciones.innerHTML = btns;

  document.getElementById('modal-det-overlay').style.display = 'flex';
};

// ── Inscripción ──────────────────────────────────────────────────────────
async function inscribirse(actividadId) {
  try {
    const res = await fetch(API + '/beneficiarios/inscribirse', {
      method: 'POST',
      headers: MASCATE.authHeaders(),
      body: JSON.stringify({ actividad_id: actividadId })
    });
    const data = await res.json();
    if (res.ok) {
      document.getElementById('modal-det-overlay').style.display = 'none';
      const t = document.createElement('div');
      t.textContent = '✓ Inscripción exitosa';
      t.style.cssText = 'position:fixed;bottom:1.5rem;right:1.5rem;z-index:2000;background:var(--primary);color:#fff;padding:0.75rem 1.25rem;border-radius:var(--radius-md);font-size:0.85rem;font-weight:600;box-shadow:0 4px 20px rgba(0,0,0,0.2)';
      document.body.appendChild(t);
      setTimeout(() => t.remove(), 3000);
    } else {
      alert('Error: ' + (data.detail || 'No se pudo inscribir.'));
    }
  } catch (e) {
    console.error(e);
  }
}

document.getElementById('modal-det-overlay')?.addEventListener('click', e => {
  if (e.target === document.getElementById('modal-det-overlay'))
    document.getElementById('modal-det-overlay').style.display = 'none';
});

// ── Eliminar actividad ───────────────────────────────────────────────────
async function eliminarAct(actId) {
  if (!confirm('¿Eliminar esta actividad? Esta acción no se puede deshacer.')) return;
  try {
    const res = await fetch(API + '/actividades/' + actId, {
      method: 'DELETE',
      headers: MASCATE.authHeaders()
    });
    if (res.ok) {
      document.getElementById('modal-det-overlay').style.display = 'none';
      window.location.reload();
    } else {
      const d = await res.json();
      alert('Error: ' + (d.detail || 'No se pudo eliminar.'));
    }
  } catch (e) {
    console.error(e);
  }
}

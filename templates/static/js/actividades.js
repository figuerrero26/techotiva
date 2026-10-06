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
    window._inscritosIds = new Set();
    if (rol === 'beneficiario') {
      const [todas, misActs] = await Promise.all([
        fetch(API + '/actividades/').then(r => r.json()),
        fetch(API + '/beneficiarios/mis-actividades', MASCATE.authGet()).then(r => r.json()).catch(() => []),
      ]);
      acts = todas;
      window._inscritosIds = new Set(misActs.map(a => a.id));
    } else if (rol === 'dispositivo') {
      const me = await (await fetch(API + '/dispositivos/me', MASCATE.authGet())).json();
      if (me?.id) acts = await (await fetch(API + '/actividades/?dispositivo_id=' + me.id)).json();
    } else if (rol === 'prescriptor') {
      acts = await (await fetch(API + '/actividades/')).json();
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

    if (rol !== 'dispositivo') {
      const thDisp = document.getElementById('th-disp-act');
      if (thDisp) thDisp.style.display = '';
    }
    if (rol === 'dispositivo' || rol === 'admin') {
      const thIns = document.getElementById('th-inscritos-act');
      if (thIns) thIns.style.display = '';
    }

    window._actsCache = acts;
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
  const tipo   = document.getElementById('act-tipo').value;
  const lugar  = document.getElementById('act-lugar').value.trim();
  const fecha  = document.getElementById('act-fecha').value;
  const hora   = document.getElementById('act-hora').value;

  if (!nombre || !tipo || !lugar || !fecha || !hora) {
    errorEl.textContent = 'Los campos Nombre, Tipo, Lugar, Fecha de inicio y Hora son obligatorios.';
    errorEl.style.display = 'block';
    return;
  }

  const payload = {
    nombre,
    tipo:         document.getElementById('act-tipo').value        || null,
    emoji:        document.getElementById('act-emoji').value       || '📋',
    lugar:        document.getElementById('act-lugar').value       || null,
    dia_semana:   null,
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

  document.getElementById('det-nombre').textContent      = `${act.emoji || '📅'} ${act.nombre}`;
  document.getElementById('det-tipo').textContent        = campo(act.tipo);
  document.getElementById('det-tipo').className          = 'tag ' + (TAG_COLOR[act.tipo] ?? 'mustard');
  document.getElementById('det-descripcion').textContent = act.descripcion || 'Sin descripción.';
  document.getElementById('det-grid').innerHTML          = '';

  // Acciones según rol
  const acciones = document.getElementById('det-acciones');
  const { rol } = MASCATE;
  let btns = '';

  if (rol === 'beneficiario') {
    btns = `<button class="btn btn-sm btn-green" onclick="inscribirse(${act.id})">✓ Inscribirme</button>`;
  } else if (rol === 'dispositivo' || rol === 'admin') {
    btns = `
      <button class="btn btn-sm btn-outline" style="color:var(--primary);border-color:var(--primary)"
        onclick="document.getElementById('modal-det-overlay').style.display='none';verInscritos(${act.id},'${act.nombre.replace(/'/g,"\\'")}')">
        👥 Ver inscritos${act.total_inscritos ? ' (' + act.total_inscritos + ')' : ''}
      </button>
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
      window._inscritosIds?.add(actividadId);
      renderActTabla('acts-tbody', window._actsCache || []);
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

// ── Render tabla con acción según rol ────────────────────────────────────
function renderActTabla(tbodyId, acts) {
  const tbody = document.getElementById(tbodyId);
  if (!tbody) return;
  const esBenef     = MASCATE.rol === 'beneficiario';
  const esDisp      = MASCATE.rol === 'dispositivo' || MASCATE.rol === 'admin';
  const mostrarDisp = MASCATE.rol !== 'dispositivo';

  // Columna Inscritos para beneficiario y columna Acciones siempre
  const thead = tbody.closest('table')?.querySelector('thead tr');
  if (thead) {
    if (esBenef && !thead.querySelector('th[data-inscritos]')) {
      const th = document.createElement('th');
      th.setAttribute('data-inscritos', '1');
      th.textContent = 'Inscritos';
      thead.insertBefore(th, thead.querySelector('th[data-acciones]') || null);
    }
    if (!thead.querySelector('th[data-acciones]')) {
      const th = document.createElement('th');
      th.setAttribute('data-acciones', '1');
      th.textContent = 'Acciones';
      thead.appendChild(th);
    }
  }

  const cols = mostrarDisp ? 8 : 7;
  if (!acts.length) {
    tbody.innerHTML = `<tr><td colspan="${cols}" style="color:var(--on-bg-muted);text-align:center;padding:1rem">Sin actividades.</td></tr>`;
    return;
  }

  const TAG_COLOR = {
    Artístico: 'mustard', Deportivo: 'green', Cultural: 'blue',
    Ambiental: 'green',   Educativo: 'blue',  Escucha:  'purple'
  };

  tbody.innerHTML = acts.map(a => {
    const ins         = a.total_inscritos ?? 0;
    const disponibles = a.cupo_maximo != null ? a.cupo_maximo - ins : null;
    const cupoColor   = disponibles != null && disponibles <= 0 ? 'var(--error)' : disponibles != null && disponibles <= 3 ? 'var(--warning,#e6a817)' : 'var(--primary)';
    const actJson     = JSON.stringify(a).replace(/'/g, "\\'");

    const inscritosCell = esBenef
      ? `<td><span class="btn btn-sm btn-outline" style="font-size:0.78rem;color:${cupoColor};border-color:${cupoColor};cursor:default">👥 ${ins}${a.cupo_maximo ? '/'+a.cupo_maximo : ''}</span></td>`
      : '';

    const yaInscrito     = esBenef && window._inscritosIds?.has(a.id);
    const btnDetalle     = `<button class="btn btn-sm btn-outline" style="font-size:0.78rem" onclick='verDetalleAct(${actJson})'>🔍 Ver detalle</button>`;
    const btnEditar      = esDisp ? `<button class="btn btn-sm btn-outline" style="font-size:0.78rem" onclick="abrirModalAct(window._actsCache?.find(x=>x.id===${a.id}))">✏️ Editar</button>` : '';
    const btnInscribirse = esBenef
      ? (yaInscrito
          ? `<span class="tag green" style="font-size:0.75rem">✓ Inscrito</span>`
          : `<button class="btn btn-sm btn-green" style="font-size:0.78rem" onclick="inscribirse(${a.id})">✓ Inscribirme</button>`)
      : '';

    const inscritosDispCell = esDisp
      ? `<td><button class="btn btn-sm btn-outline" style="font-size:0.78rem;color:${cupoColor};border-color:${cupoColor}" onclick="verInscritos(${a.id},'${a.nombre.replace(/'/g,"\\'")}')">👥 ${ins}${a.cupo_maximo ? '/'+a.cupo_maximo : ''}</button></td>`
      : '';

    return `<tr>
      <td>
        <div style="display:flex;align-items:center;gap:0.5rem">
          <span style="font-size:1.1rem">${a.emoji||'📅'}</span>
          <span style="font-weight:600">${a.nombre}</span>
        </div>
      </td>
      <td><span class="tag ${TAG_COLOR[a.tipo]||'mustard'}">${a.tipo||'—'}</span></td>
      ${mostrarDisp ? `<td style="font-size:0.82rem;color:var(--on-bg-muted)">${a.dispositivo_nombre||'—'}</td>` : ''}
      <td>${a.lugar||'—'}</td>
      <td>${a.fecha_inicio ? new Date(a.fecha_inicio+'T00:00:00').toLocaleDateString('es-CO',{day:'2-digit',month:'short',year:'numeric'}) : '—'}</td>
      <td>${a.hora||'—'}</td>
      ${inscritosDispCell}
      <td><span class="tag ${a.activa !== false ? 'green' : ''}" style="${a.activa !== false ? '' : 'background:var(--on-bg-muted,#aaa);color:#fff'}">${a.activa !== false ? 'Activa' : 'Inactiva'}</span></td>
      ${inscritosCell}
      <td style="white-space:nowrap">
        <div style="display:flex;gap:0.35rem;flex-wrap:wrap">
          ${btnDetalle}${btnEditar}${btnInscribirse}
        </div>
      </td>
    </tr>`;
  }).join('');
}

// ── Ver inscritos ────────────────────────────────────────────────────────
async function verInscritos(actividadId, nombreAct) {
  document.getElementById('inscritos-titulo').textContent = nombreAct || 'Inscritos';
  document.getElementById('inscritos-count').textContent = '...';
  document.getElementById('inscritos-list').innerHTML = '<div style="color:var(--on-bg-muted);font-size:0.85rem">Cargando...</div>';
  document.getElementById('modal-inscritos-overlay').style.display = 'flex';

  try {
    const res  = await fetch(API + '/actividades/' + actividadId + '/inscritos', MASCATE.authGet());
    const data = await res.json();
    document.getElementById('inscritos-count').textContent = data.total + ' inscritos';

    if (!data.inscritos?.length) {
      document.getElementById('inscritos-list').innerHTML =
        '<div style="color:var(--on-bg-muted);font-size:0.85rem;padding:0.5rem">Nadie inscrito aún.</div>';
      return;
    }

    document.getElementById('inscritos-list').innerHTML = data.inscritos.map(b => `
      <div class="list-row">
        <div class="contact-icon" style="background:var(--secondary-dim)">${b.nombre_apodo?.[0]?.toUpperCase()||'?'}</div>
        <div class="list-info">
          <div class="list-name">${b.nombre_apodo}</div>
          <div class="list-sub">${[b.localidad, b.telefono].filter(Boolean).join(' · ') || 'Sin datos de contacto'}</div>
        </div>
        <div style="font-size:0.72rem;color:var(--on-bg-muted);white-space:nowrap">
          ${b.fecha_inscripcion ? new Date(b.fecha_inscripcion).toLocaleDateString('es-CO') : ''}
        </div>
      </div>`).join('');
  } catch(e) {
    document.getElementById('inscritos-list').innerHTML =
      '<div style="color:var(--error);font-size:0.85rem">Error al cargar inscritos.</div>';
  }
}

document.getElementById('modal-inscritos-overlay')?.addEventListener('click', e => {
  if (e.target === document.getElementById('modal-inscritos-overlay'))
    document.getElementById('modal-inscritos-overlay').style.display = 'none';
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

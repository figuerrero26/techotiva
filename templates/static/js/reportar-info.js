/* ═══ MASCATE — REPORTAR INFO (Seguimiento + Primer Contacto) ═══ */
const API = window.location.origin;
MASCATE.guardAuth();

let asignadosData          = [];
let _delSegId              = null;
let _delPcId               = null;
let _miDispositivoId       = null;
let _prescriptorDispositId = null;  // dispositivo_id del prescriptor logueado

// ── Inicialización ─────────────────────────────────────────────────────────
window.addEventListener('DOMContentLoaded', async () => {
  renderSidebar(MASCATE.nombre, MASCATE.email);
  await initNotifBtn();

  // Ocultar tab de seguimiento para dispositivo de inmediato (evita el flash)
  if (MASCATE.rol === 'dispositivo') {
    const btnSeg = document.querySelector('[data-tab="seguimiento"]');
    if (btnSeg) btnSeg.style.display = 'none';
    document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.getElementById('tab-primer-contacto')?.classList.add('active');
    document.querySelector('[data-tab="primer-contacto"]')?.classList.add('active');
  }

  // Fecha de hoy en el picker de primer contacto
  const pcFecha = document.getElementById('pc-fecha');
  if (pcFecha) pcFecha.value = new Date().toISOString().split('T')[0];

  // Tabs: usar addEventListener en lugar de onclick inline
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const tab = btn.dataset.tab;
      document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      const pane = document.getElementById('tab-' + tab);
      if (pane) pane.classList.add('active');
      btn.classList.add('active');
    });
  });

  await cargarBeneficiarios();
  await cargarSeguimientos();
  await cargarPrimeroContactos();
  await initPCDbc();

  // Pre-selección desde query params (redireccionado desde "Usuarios")
  const qp = new URLSearchParams(window.location.search);
  const qTab = qp.get('tab');
  const qBid = qp.get('bid');
  const qNom = qp.get('bnombre');
  if (qTab === 'seguimiento' && MASCATE.rol !== 'dispositivo') {
    document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.getElementById('tab-seguimiento')?.classList.add('active');
    document.querySelector('[data-tab="seguimiento"]')?.classList.add('active');
    if (qBid && qNom) seleccionarPersonaSeg(parseInt(qBid), decodeURIComponent(qNom));
  }
});

async function initPCDbc() {
  const wrap = document.getElementById('pc-dbc-wrap');
  if (!wrap) return;

  if (MASCATE.rol === 'dispositivo') {
    try {
      const me = await fetch(API + '/dispositivos/me', MASCATE.authGet()).then(r => r.json());
      _miDispositivoId = me.id;
      wrap.innerHTML = `<input type="text" id="pc-dbc" value="${me.nombre}" readonly
        style="width:100%;background:var(--bg-alt,#f5f5f5);color:var(--on-bg);cursor:default">`;
    } catch(e) {
      wrap.innerHTML = `<input type="text" id="pc-dbc" placeholder="No se pudo cargar" readonly style="width:100%">`;
    }
  } else if (MASCATE.rol === 'admin') {
    try {
      const disps = await fetch(API + '/dispositivos/', MASCATE.authGet()).then(r => r.json());
      if (Array.isArray(disps) && disps.length) {
        const opts = disps.map(d =>
          `<option value="${d.id}" data-nombre="${d.nombre}">${d.nombre}</option>`
        ).join('');
        wrap.innerHTML = `<select id="pc-dbc" style="width:100%">
          <option value="">-- Seleccionar DBC --</option>${opts}</select>`;
      }
    } catch(e) {}
  } else if (MASCATE.rol === 'prescriptor') {
    try {
      const me = await fetch(API + '/prescriptores/me', MASCATE.authGet()).then(r => r.json());
      if (me.dispositivo_id && me.dispositivo_nombre) {
        _miDispositivoId = me.dispositivo_id;
        wrap.innerHTML = `<input type="text" id="pc-dbc" value="${me.dispositivo_nombre}" readonly
          style="width:100%;background:var(--bg-alt,#f5f5f5);color:var(--on-bg);cursor:default">`;
      } else {
        wrap.innerHTML = `<input type="text" id="pc-dbc" placeholder="Sin dispositivo asignado" readonly
          style="width:100%;background:var(--bg-alt,#f5f5f5);color:var(--on-bg-muted);cursor:default">`;
      }
    } catch(e) {
      wrap.innerHTML = `<input type="text" id="pc-dbc" placeholder="No se pudo cargar" readonly style="width:100%">`;
    }
  }
}

// ── Carga de beneficiarios según rol ──────────────────────────────────────
async function cargarBeneficiarios() {
  let lista = [];

  try {
    if (MASCATE.rol === 'prescriptor') {
      const raw = await fetch(API + '/prescriptores/mis-asignados', MASCATE.authGet()).then(r => r.json());
      if (Array.isArray(raw)) {
        lista = raw.map(a => ({ id: a.id, nombre_apodo: a.nombre_apodo }));
      }
    } else if (MASCATE.rol === 'dispositivo') {
      const me = await fetch(API + '/dispositivos/me', MASCATE.authGet()).then(r => r.json());
      if (me?.id) {
        _miDispositivoId = me.id;
        const raw = await fetch(API + '/dispositivos/' + me.id + '/beneficiarios', MASCATE.authGet()).then(r => r.json());
        if (Array.isArray(raw)) {
          lista = raw.map(b => ({ id: b.id, nombre_apodo: b.nombre_apodo }));
        }
      }
    } else if (MASCATE.rol === 'admin') {
      const raw = await fetch(API + '/admin/beneficiarios', MASCATE.authGet()).then(r => r.json());
      if (Array.isArray(raw)) {
        lista = raw.map(b => ({ id: b.id, nombre_apodo: b.nombre_apodo }));
      }
    }
  } catch(e) {
    console.error('Error cargando beneficiarios:', e);
  }

  asignadosData = lista;

  // Poblar pc-modo con beneficiarios que aún no tienen primer contacto
  const pcModo = document.getElementById('pc-modo');
  if (pcModo && lista.length) {
    try {
      const pcs = await fetch(API + '/primer-contacto/', MASCATE.authGet()).then(r => r.json());
      const idsConPC = new Set(Array.isArray(pcs) ? pcs.map(p => p.beneficiario_id) : []);
      const sinPC = lista.filter(b => !idsConPC.has(b.id));
      if (sinPC.length) {
        const opts = sinPC.map(b => `<option value="${b.id}">${b.nombre_apodo}</option>`).join('');
        pcModo.innerHTML = `<option value="nueva">+ Nueva persona</option>${opts}`;
      }
    } catch(e) {}
  }

  // seg-persona es ahora un input hidden + buscador (no select)

  // Para prescriptor: cargar también la tabla de estado de seguimiento
  if (MASCATE.rol === 'prescriptor') {
    try {
      const raw = await fetch(API + '/prescriptores/mis-asignados', MASCATE.authGet()).then(r => r.json());
      const tabla = document.getElementById('tabla-asignados');
      if (tabla) {
        if (!Array.isArray(raw) || !raw.length) {
          tabla.innerHTML = '<div style="color:var(--on-bg-muted);font-size:0.85rem;padding:0.5rem">Sin personas asignadas.</div>';
        } else {
          tabla.innerHTML = `<div style="overflow-x:auto"><table>
            <thead><tr><th>Persona</th><th>Último seguimiento</th><th>Días sin sesión</th><th>Estado</th></tr></thead>
            <tbody>${raw.map(a => {
              const tagClass = a.estado === 'urgente' ? 'rust' : a.estado === 'revisar' ? 'mustard' : 'green';
              const label    = a.estado === 'urgente' ? 'Urgente' : a.estado === 'revisar' ? 'Revisar' : 'Al día';
              const ultima   = a.ultima_sesion ? new Date(a.ultima_sesion).toLocaleDateString('es-CO') : '—';
              return `<tr>
                <td><div style="display:flex;align-items:center;gap:0.5rem">
                  <div class="list-avatar" style="width:1.6rem;height:1.6rem;font-size:0.65rem;flex-shrink:0">${a.nombre_apodo.substring(0,2).toUpperCase()}</div>
                  ${a.nombre_apodo}
                </div></td>
                <td style="font-size:0.82rem">${ultima}</td>
                <td style="font-size:0.82rem">${a.dias_sin_sesion != null ? a.dias_sin_sesion + ' días' : '—'}</td>
                <td><span class="tag ${tagClass}">${label}</span></td>
              </tr>`;
            }).join('')}</tbody>
          </table></div>`;
        }
      }
    } catch(e) {}
  } else {
    // Para otros roles, ocultar la tabla de estado
    const tabla = document.getElementById('tabla-asignados');
    if (tabla) tabla.closest('.panel') && (tabla.closest('.panel').style.display = 'none');
  }
}

// ══════════════════════════════════════════════════════════════════════════
// SEGUIMIENTO
// ══════════════════════════════════════════════════════════════════════════

async function cargarSeguimientos() {
  if (MASCATE.rol === 'dispositivo') {
    // Los dispositivos no crean seguimientos, ocultar la pestaña
    const btnSeg = document.querySelector('[data-tab="seguimiento"]');
    if (btnSeg) btnSeg.style.display = 'none';
    // Activar pestaña de primer contacto por defecto
    document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.getElementById('tab-primer-contacto')?.classList.add('active');
    document.querySelector('[data-tab="primer-contacto"]')?.classList.add('active');
    return;
  }

  try {
    const segs = await fetch(API + '/prescriptores/seguimientos', MASCATE.authGet()).then(r => r.json());
    if (!Array.isArray(segs)) {
      set('count-seg', 0);
      document.getElementById('lista-seg').innerHTML = '<div style="color:var(--on-bg-muted);font-size:0.85rem;padding:0.5rem">Sin registros aún.</div>';
      return;
    }
    set('count-seg', segs.length);
    const lista = document.getElementById('lista-seg');
    if (!lista) return;
    if (!segs.length) {
      lista.innerHTML = '<div style="color:var(--on-bg-muted);font-size:0.85rem;padding:0.5rem">Sin registros aún.</div>';
      return;
    }
    lista.innerHTML = segs.slice(0, 8).map(s => {
      const fecha = new Date(s.fecha).toLocaleDateString('es-CO', { day:'2-digit', month:'short', year:'numeric' });
      return `<div style="border:1px solid var(--outline-variant);border-radius:var(--radius-sm);padding:0.75rem;margin-bottom:0.5rem">
        <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:0.5rem;margin-bottom:0.35rem">
          <div>
            <span style="font-size:0.85rem;font-weight:600">${campo(s.nombre_beneficiario, '—')}</span>
            <span class="tag mustard" style="font-size:0.7rem;margin-left:0.4rem">${s.tipo_registro || '—'}</span>
          </div>
          <div style="display:flex;align-items:center;gap:0.4rem;flex-shrink:0">
            <span style="font-size:0.75rem;color:var(--on-bg-muted)">${fecha}</span>
            <button class="btn btn-sm btn-outline" style="padding:0.2rem 0.5rem;color:var(--error);border-color:var(--error)" onclick="pedirDelSeg(${s.id})">🗑</button>
          </div>
        </div>
        ${s.observaciones ? `<div style="font-size:0.82rem;color:var(--on-bg-muted);white-space:pre-wrap;word-break:break-word;line-height:1.5">${s.observaciones}</div>` : ''}
      </div>`;
    }).join('');
  } catch(e) {
    console.error('Error cargando seguimientos:', e);
  }
}

async function guardarSeguimiento() {
  const errorEl = document.getElementById('seg-error');
  const btn     = document.getElementById('btn-guardar-seg');
  if (errorEl) errorEl.style.display = 'none';

  const personaId     = document.getElementById('seg-persona')?.value;
  const tipoRegistro  = document.getElementById('seg-tipo')?.value;
  const observaciones = document.getElementById('seg-observaciones')?.value.trim();

  if (!personaId || isNaN(parseInt(personaId))) {
    if (errorEl) { errorEl.textContent = 'Selecciona una persona de la lista.'; errorEl.style.display = 'block'; }
    return;
  }

  if (btn) { btn.textContent = 'Guardando...'; btn.disabled = true; }
  try {
    const res = await fetch(API + '/prescriptores/seguimientos', {
      method: 'POST',
      headers: MASCATE.authHeaders(),
      body: JSON.stringify({ beneficiario_id: parseInt(personaId), tipo_registro: tipoRegistro, observaciones: observaciones || null }),
    });
    const data = await res.json();
    if (res.ok) {
      limpiarSeg();
      await cargarSeguimientos();
      toast('✓ Registro guardado');
    } else {
      if (errorEl) { errorEl.textContent = data.detail || 'Error al guardar.'; errorEl.style.display = 'block'; }
    }
  } catch(e) {
    if (errorEl) { errorEl.textContent = 'Error de conexión.'; errorEl.style.display = 'block'; }
  }
  if (btn) { btn.textContent = 'Guardar registro'; btn.disabled = false; }
}

function limpiarSeg() {
  document.getElementById('seg-persona-txt').value  = '';
  document.getElementById('seg-persona').value      = '';
  const lista = document.getElementById('seg-personas-lista');
  if (lista) lista.style.display = 'none';
  // Cerrar formulario nueva persona si estaba abierto
  const wrap = document.getElementById('seg-nueva-persona-wrap');
  if (wrap) wrap.style.display = 'none';
  ['seg-nuevo-nombre','seg-nuevo-email','seg-nuevo-fnac','seg-nuevo-telefono','seg-nuevo-localidad'].forEach(id => {
    const el = document.getElementById(id); if (el) el.value = '';
  });
  const gnEl = document.getElementById('seg-nuevo-genero');
  if (gnEl) gnEl.value = '';
  const obs = document.getElementById('seg-observaciones');
  if (obs) obs.value = '';
  const err = document.getElementById('seg-error');
  if (err) err.style.display = 'none';
}

function pedirDelSeg(id) {
  _delSegId = id;
  const m = document.getElementById('modal-del-seg');
  if (m) m.style.display = 'flex';
}

async function confirmarDelSeg() {
  if (!_delSegId) return;
  const btn = document.getElementById('btn-del-seg');
  if (btn) { btn.textContent = 'Eliminando...'; btn.disabled = true; }
  try {
    const res = await fetch(API + '/prescriptores/seguimientos/' + _delSegId, {
      method: 'DELETE', headers: MASCATE.authHeaders(),
    });
    if (res.ok || res.status === 204) {
      cerrarModales();
      await cargarSeguimientos();
      toast('✓ Registro eliminado', 'error');
    } else {
      const d = await res.json().catch(() => ({}));
      cerrarModales();
      const el = document.getElementById('seg-error');
      if (el) { el.textContent = d.detail || 'No se pudo eliminar.'; el.style.display = 'block'; }
    }
  } catch(e) { console.error(e); cerrarModales(); }
  if (btn) { btn.textContent = 'Sí, eliminar'; btn.disabled = false; }
}

// ══════════════════════════════════════════════════════════════════════════
// PRIMER CONTACTO
// ══════════════════════════════════════════════════════════════════════════

async function cargarPrimeroContactos() {
  try {
    const pcs = await fetch(API + '/primer-contacto/', MASCATE.authGet()).then(r => r.json());
    set('count-pc', Array.isArray(pcs) ? pcs.length : 0);
    const lista = document.getElementById('lista-pc');
    if (!lista) return;
    if (!Array.isArray(pcs) || !pcs.length) {
      lista.innerHTML = '<div style="color:var(--on-bg-muted);font-size:0.85rem;padding:0.5rem">Sin registros de primer contacto aún.</div>';
      return;
    }
    lista.innerHTML = pcs.slice(0, 10).map(pc => {
      const fecha = pc.fecha_contacto
        ? new Date(pc.fecha_contacto + 'T00:00:00').toLocaleDateString('es-CO', { day:'2-digit', month:'short', year:'numeric' }) : '—';
      return `<div class="list-row" style="padding:0.6rem 0;border-bottom:1px solid var(--border)">
        <div class="list-avatar" style="flex-shrink:0;font-size:0.75rem">${(pc.nombre_beneficiario||'??').substring(0,2).toUpperCase()}</div>
        <div class="list-info">
          <div class="list-name" style="font-size:0.85rem">${campo(pc.nombre_beneficiario, '—')}</div>
          <div class="list-sub">${fecha}</div>
        </div>
      </div>`;
    }).join('');
  } catch(e) {
    console.error('Error cargando primer contacto:', e);
  }
}

function _siNo(id) {
  const v = document.getElementById(id)?.value;
  if (v === 'Sí') return true;
  if (v === 'No') return false;
  return null;
}
function _val(id)  { return document.getElementById(id)?.value?.trim() || null; }
function _sel(id)  { return document.getElementById(id)?.value || null; }
function _num(id)  { const v = parseInt(document.getElementById(id)?.value); return isNaN(v) ? null : v; }

function calcularEdadPC(fechaStr) {
  const el = document.getElementById('pc-edad');
  if (!el) return;
  if (!fechaStr) { el.value = ''; return; }
  const hoy = new Date();
  const nac = new Date(fechaStr + 'T00:00:00');
  let edad = hoy.getFullYear() - nac.getFullYear();
  const m = hoy.getMonth() - nac.getMonth();
  if (m < 0 || (m === 0 && hoy.getDate() < nac.getDate())) edad--;
  el.value = edad >= 0 ? edad : '';
}

function togglePCModo(val) {
  const wrap = document.getElementById('pc-nuevo-nombre-wrap');
  if (wrap) wrap.style.display = val === 'nueva' ? 'block' : 'none';
}

function toggleApoyoWrap(val) {
  const w = document.getElementById('pc-apoyo-detalle-wrap');
  if (w) w.style.display = val === 'Sí' ? 'block' : 'none';
}
function toggleCualActor(val) {
  const w = document.getElementById('pc-cual-actor-wrap');
  if (w) w.style.display = val === 'Sí' ? 'block' : 'none';
}
function toggleCualEtnico(val) {
  const w = document.getElementById('pc-cual-etnico-wrap');
  if (w) w.style.display = val === 'Sí' ? 'flex' : 'none';
}

async function guardarPrimerContacto() {
  const errorEl = document.getElementById('pc-error');
  const btn     = document.getElementById('btn-guardar-pc');
  if (errorEl) errorEl.style.display = 'none';

  const fecha    = document.getElementById('pc-fecha')?.value;
  const pcModoV  = document.getElementById('pc-modo')?.value ?? 'nueva';
  const esNueva  = pcModoV === 'nueva';

  if (esNueva && !_val('pc-nuevo-nombre')) {
    if (errorEl) { errorEl.textContent = 'Ingresa el nombre y apellidos de la persona.'; errorEl.style.display = 'block'; }
    return;
  }
  if (!fecha) {
    if (errorEl) { errorEl.textContent = 'Ingresa la fecha del contacto.'; errorEl.style.display = 'block'; }
    return;
  }


  let dispositivoId = _miDispositivoId;
  let dbcNombre     = null;

  if (MASCATE.rol === 'admin') {
    const dbcEl = document.getElementById('pc-dbc');
    if (dbcEl && dbcEl.tagName === 'SELECT') {
      const opt = dbcEl.options[dbcEl.selectedIndex];
      dispositivoId = opt ? parseInt(opt.value) : null;
      dbcNombre     = opt ? opt.dataset.nombre || opt.text : null;
    }
    if (!dispositivoId) {
      if (errorEl) { errorEl.textContent = 'Selecciona el DBC al que pertenece este contacto.'; errorEl.style.display = 'block'; }
      return;
    }
  } else if (!dispositivoId) {
    try {
      if (MASCATE.rol === 'prescriptor') {
        const me = await fetch(API + '/prescriptores/me', MASCATE.authGet()).then(r => r.json());
        dispositivoId = me.dispositivo_id;
      } else if (MASCATE.rol === 'dispositivo') {
        const me = await fetch(API + '/dispositivos/me', MASCATE.authGet()).then(r => r.json());
        dispositivoId = me.id;
        _miDispositivoId = me.id;
        dbcNombre = me.nombre;
      }
    } catch(e) {}
  } else {
    dbcNombre = document.getElementById('pc-dbc')?.value || null;
  }

  if (!dispositivoId) {
    if (errorEl) { errorEl.textContent = 'No se pudo determinar el dispositivo. Asegúrate de estar asignado a uno.'; errorEl.style.display = 'block'; }
    return;
  }

  const contactoBase = {
    dispositivo_id:        dispositivoId,
    // § 2 Convenio
    convenio_515:          _sel('pc-convenio515'),
    tipo_dbc:              dbcNombre || _val('pc-dbc'),
    numero_caso:           _val('pc-num-caso'),
    politica_privacidad:   document.getElementById('pc-politica-privacidad')?.checked ? 'Sí' : 'No',
    // § 2 Evento
    fecha_contacto:        fecha,
    hora_contacto:         _sel('pc-hora'),
    upz:                   _sel('pc-upz'),
    barrio:                _val('pc-barrio'),
    forma_contacto:        _sel('pc-forma'),
    // § 3 Fuente
    nombre_fuente:         _val('pc-fuente'),
    telefono_fuente:       _val('pc-tel-fuente'),
    genero_fuente:         _sel('pc-genero-fuente'),
    vinculo_fuente:        _sel('pc-vinculo'),
    // § 4 Beneficiario — datos compartidos
    genero:                _sel('pc-nuevo-genero'),
    telefono:              _val('pc-nuevo-telefono'),
    localidad:             _val('pc-nuevo-localidad'),
    fecha_nacimiento:      _val('pc-nuevo-fnac'),
    edad_benef:            _num('pc-edad'),
    estado_civil:          _sel('pc-estado-civil'),
    num_hijos:             _num('pc-num-hijos'),
    procesos_previos:      _num('pc-procesos') ?? 0,
    // § 5 Identidad y cultura
    pertenencia_etnica:    _sel('pc-grupo-etnico') || null,
    etnia:                 _val('pc-cual-etnico'),
    religion:              _sel('pc-religion'),
    // § 6 Persona de apoyo
    tiene_persona_apoyo:   _siNo('pc-persona-apoyo'),
    nombre_persona_apoyo:  _val('pc-nombre-apoyo'),
    telefono_persona_apoyo:_val('pc-tel-apoyo'),
    vinculo_persona_apoyo: _val('pc-tipo-vinculo-txt'),
    tipo_vinculo_codigo:   _sel('pc-tipo-vinculo-cod'),
    genero_apoyo:          _sel('pc-genero-apoyo'),
    // § 7 Condiciones de vida
    con_quien_vive:        _sel('pc-con-quien-vive'),
    clase_via:             _sel('pc-clase-via'),
    numero_via_principal:  _val('pc-num-via-ppal'),
    letra_via_principal:   _val('pc-letra-via-ppal'),
    identificador_sector:  _val('pc-id-sector'),
    numero_via_generadora: _val('pc-num-via-gen'),
    letra_via_generadora:  _val('pc-letra-via-gen'),
    numero_predio:         _val('pc-num-predio'),
    otras_caracteristicas_dir: _val('pc-otras-caract'),
    // § 8 Educación y trabajo
    sabe_leer_escribir:    _siNo('pc-sabe-leer'),
    sabe_usar_computador:  _siNo('pc-sabe-pc'),
    escolaridad:           _sel('pc-escolaridad'),
    ocupacion:             _sel('pc-ocupacion'),
    // § 9 Redes de apoyo
    apoyo_familiar:        _siNo('pc-apoyo-fam'),
    apoyo_comunitario:     _siNo('pc-apoyo-com'),
    apoyo_institucional:   _siNo('pc-apoyo-inst'),
    apoyo_otro_actor:      _siNo('pc-apoyo-actor'),
    cual_actor_social:     _val('pc-cual-actor'),
    // § 10 Recreación y participación
    practica_deporte:      _siNo('pc-practica-deporte'),
    tiene_tiempo_recreacion: _siNo('pc-tiene-tiempo-rec'),
    cuanto_tiempo_recreacion: _val('pc-cuanto-tiempo'),
    conoce_espacios:       _sel('pc-conoce-espacios'),
    ha_participado:        _sel('pc-ha-participado'),
    // § 11 Situación actual
    situaciones_presentes: (() => {
      const checks = [...document.querySelectorAll('#pc-situaciones-checks input[type="checkbox"]:checked')]
        .map(c => c.value);
      const extra = _val('pc-situaciones');
      return [...checks, ...(extra ? [extra] : [])].join(' | ') || null;
    })(),
    peticiones:            _val('pc-peticiones'),
    descripcion_caso:      _val('pc-descripcion'),
    // § 12 Registrador
    rol_registrador:       _val('pc-rol-registrador'),
    nombre_registrador:    _val('pc-nombre-registrador'),
    telefono_registrador:  _val('pc-tel-registrador'),
  };

  const endpoint = esNueva
    ? API + '/primer-contacto/sin-cuenta'
    : API + '/primer-contacto/';
  const payload = esNueva
    ? { ...contactoBase, nombre_apodo: _val('pc-nuevo-nombre'), email: _val('pc-nuevo-email') }
    : { ...contactoBase, beneficiario_id: parseInt(pcModoV) };

  if (btn) { btn.textContent = 'Guardando...'; btn.disabled = true; }
  try {
    const res = await fetch(endpoint, {
      method: 'POST', headers: MASCATE.authHeaders(), body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (res.ok) {
      limpiarPC();
      await cargarPrimeroContactos();
      toast('✓ Primer contacto registrado');
    } else {
      if (errorEl) { errorEl.textContent = data.detail || 'Error al guardar.'; errorEl.style.display = 'block'; }
    }
  } catch(e) {
    if (errorEl) { errorEl.textContent = 'Error de conexión.'; errorEl.style.display = 'block'; }
  }
  if (btn) { btn.textContent = 'Guardar primer contacto'; btn.disabled = false; }
}

function limpiarPC() {
  // DBC: reset según tipo de control (select para admin, input para otros)
  const dbcEl = document.getElementById('pc-dbc');
  if (dbcEl) dbcEl.value = '';

  const textIds = [
    'pc-barrio','pc-fuente','pc-tel-fuente','pc-num-caso',
    'pc-situaciones','pc-peticiones','pc-descripcion',
    'pc-nuevo-nombre','pc-nuevo-email','pc-nuevo-telefono','pc-nuevo-fnac',
    'pc-nombre-apoyo','pc-tel-apoyo','pc-tipo-vinculo-txt',
    'pc-num-via-ppal','pc-letra-via-ppal','pc-id-sector',
    'pc-num-via-gen','pc-letra-via-gen','pc-num-predio','pc-otras-caract',
    'pc-cual-etnico','pc-cual-actor','pc-cuanto-tiempo',
    'pc-rol-registrador','pc-nombre-registrador','pc-tel-registrador',
  ];
  textIds.forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });

  const selIds = [
    'pc-hora','pc-forma','pc-vinculo','pc-convenio515',
    'pc-upz','pc-nuevo-genero','pc-genero-fuente','pc-nuevo-localidad',
    'pc-estado-civil','pc-grupo-etnico','pc-religion',
    'pc-persona-apoyo','pc-tipo-vinculo-cod','pc-genero-apoyo',
    'pc-con-quien-vive','pc-clase-via',
    'pc-sabe-leer','pc-sabe-pc','pc-escolaridad','pc-ocupacion',
    'pc-apoyo-fam','pc-apoyo-com','pc-apoyo-inst','pc-apoyo-actor',
    'pc-practica-deporte','pc-tiene-tiempo-rec','pc-conoce-espacios','pc-ha-participado',
  ];
  selIds.forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });

  const proc = document.getElementById('pc-procesos');
  if (proc) proc.value = '0';
  const edad = document.getElementById('pc-edad');
  if (edad) edad.value = '';
  const numH = document.getElementById('pc-num-hijos');
  if (numH) numH.value = '';

  document.querySelectorAll('#pc-situaciones-checks input[type="checkbox"]')
    .forEach(c => c.checked = false);
  const polCheck = document.getElementById('pc-politica-privacidad');
  if (polCheck) polCheck.checked = false;

  const modo = document.getElementById('pc-modo');
  if (modo) { modo.value = 'nueva'; }
  const nWrap = document.getElementById('pc-nuevo-nombre-wrap');
  if (nWrap) nWrap.style.display = 'block';
  const aWrap = document.getElementById('pc-apoyo-detalle-wrap');
  if (aWrap) aWrap.style.display = 'none';
  const cWrap = document.getElementById('pc-cual-actor-wrap');
  if (cWrap) cWrap.style.display = 'none';
  const eWrap = document.getElementById('pc-cual-etnico-wrap');
  if (eWrap) eWrap.style.display = 'none';

  const err = document.getElementById('pc-error');
  if (err) err.style.display = 'none';
}

function pedirDelPC(id) {
  _delPcId = id;
  const m = document.getElementById('modal-del-pc');
  if (m) m.style.display = 'flex';
}

async function confirmarDelPC() {
  if (!_delPcId) return;
  const btn = document.getElementById('btn-del-pc');
  if (btn) { btn.textContent = 'Eliminando...'; btn.disabled = true; }
  try {
    const res = await fetch(API + '/primer-contacto/' + _delPcId, {
      method: 'DELETE', headers: MASCATE.authHeaders(),
    });
    if (res.ok || res.status === 204) {
      cerrarModales();
      await cargarPrimeroContactos();
      toast('✓ Registro eliminado', 'error');
    } else {
      cerrarModales();
    }
  } catch(e) { console.error(e); cerrarModales(); }
  if (btn) { btn.textContent = 'Sí, eliminar'; btn.disabled = false; }
}

// ── Buscador de persona en seguimiento ────────────────────────────────────

function _itemDropdownSeg(label, isHeader) {
  const base = 'padding:0.5rem 0.75rem;font-size:0.85rem;cursor:pointer;border-bottom:1px solid var(--border);transition:background .1s';
  return isHeader
    ? `style="${base};font-weight:700;color:var(--primary)"`
    : `style="${base}"`;
}

function _renderDropdownSeg(txt) {
  const lista = document.getElementById('seg-personas-lista');
  if (!lista) return;

  const filtrados = txt
    ? asignadosData.filter(a => a.nombre_apodo.toLowerCase().includes(txt.toLowerCase()))
    : asignadosData;

  const itemStyle = 'padding:0.5rem 0.75rem;font-size:0.85rem;cursor:pointer;border-bottom:1px solid var(--border);transition:background .1s';
  const agregar   = `<div
      style="${itemStyle};font-weight:700;color:var(--primary)"
      onmouseover="this.style.background='var(--primary-dim)'" onmouseout="this.style.background=''"
      onmousedown="abrirFormNuevoSeg()">+ Agregar persona</div>`;

  const personas = filtrados.length
    ? filtrados.map(a =>
        `<div style="${itemStyle}"
          onmouseover="this.style.background='var(--primary-dim)'" onmouseout="this.style.background=''"
          onmousedown="seleccionarPersonaSeg(${a.id},'${a.nombre_apodo.replace(/'/g,"\\'")}')">
          ${a.nombre_apodo}</div>`
      ).join('')
    : `<div style="padding:0.5rem 0.75rem;font-size:0.85rem;color:var(--on-bg-muted)">Sin resultados</div>`;

  lista.innerHTML = agregar + personas;
  lista.style.display = 'block';
}

function mostrarTodasPersonasSeg() {
  document.getElementById('seg-persona').value = '';   // limpiar selección al reabrir
  _renderDropdownSeg('');
}

function filtrarPersonasSeg(q) {
  document.getElementById('seg-persona').value = '';   // limpiar selección al escribir
  _renderDropdownSeg(q.trim());
}

function seleccionarPersonaSeg(id, nombre) {
  document.getElementById('seg-persona').value     = id;
  document.getElementById('seg-persona-txt').value = nombre;
  const lista = document.getElementById('seg-personas-lista');
  if (lista) lista.style.display = 'none';
  // Ocultar formulario de nueva persona si estaba abierto
  document.getElementById('seg-nueva-persona-wrap').style.display = 'none';
}

// ── Formulario inline "Nueva persona" en seguimiento ─────────────────────

function abrirFormNuevoSeg() {
  const lista = document.getElementById('seg-personas-lista');
  const wrap  = document.getElementById('seg-nueva-persona-wrap');
  if (lista) lista.style.display = 'none';
  if (wrap)  { wrap.style.display = 'block'; }
  document.getElementById('seg-persona').value     = '';
  document.getElementById('seg-persona-txt').value = '';
  document.getElementById('seg-nuevo-nombre')?.focus();
}

function cerrarFormNuevoSeg() {
  document.getElementById('seg-nueva-persona-wrap').style.display = 'none';
  ['seg-nuevo-nombre','seg-nuevo-email','seg-nuevo-fnac','seg-nuevo-telefono','seg-nuevo-localidad'].forEach(id => {
    const el = document.getElementById(id); if (el) el.value = '';
  });
  const gnEl = document.getElementById('seg-nuevo-genero');
  if (gnEl) gnEl.value = '';
  document.getElementById('seg-persona').value     = '';
  document.getElementById('seg-persona-txt').value = '';
}

async function crearPersonaSeg() {
  const nombre  = document.getElementById('seg-nuevo-nombre')?.value.trim();
  const email   = document.getElementById('seg-nuevo-email')?.value.trim();
  const errorEl = document.getElementById('seg-error');

  if (!nombre) {
    if (errorEl) { errorEl.textContent = 'Ingresa el nombre y apellidos de la persona.'; errorEl.style.display = 'block'; }
    return;
  }
  if (!email) {
    if (errorEl) { errorEl.textContent = 'El correo electrónico es obligatorio.'; errorEl.style.display = 'block'; }
    return;
  }

  // Obtener dispositivo_id si no lo tenemos aún
  if (!_prescriptorDispositId) {
    try {
      if (MASCATE.rol === 'prescriptor') {
        const me = await fetch(API + '/prescriptores/me', MASCATE.authGet()).then(r => r.json());
        _prescriptorDispositId = me.dispositivo_id;
      } else if (MASCATE.rol === 'dispositivo') {
        _prescriptorDispositId = _miDispositivoId;
      }
    } catch(e) {}
  }

  const dispId = _prescriptorDispositId || _miDispositivoId;
  if (!dispId) {
    if (errorEl) { errorEl.textContent = 'No se pudo determinar el dispositivo asociado.'; errorEl.style.display = 'block'; }
    return;
  }

  const btn = document.getElementById('btn-crear-persona-seg');
  if (btn) { btn.textContent = 'Creando...'; btn.disabled = true; }

  try {
    const res = await fetch(API + '/primer-contacto/sin-cuenta', {
      method: 'POST',
      headers: MASCATE.authHeaders(),
      body: JSON.stringify({
        nombre_apodo:    nombre,
        email:           email,
        dispositivo_id:  dispId,
        fecha_nacimiento: document.getElementById('seg-nuevo-fnac')?.value || null,
        genero:           document.getElementById('seg-nuevo-genero')?.value || null,
        telefono:         document.getElementById('seg-nuevo-telefono')?.value.trim() || null,
        localidad:        document.getElementById('seg-nuevo-localidad')?.value.trim() || null,
      }),
    });
    const data = await res.json();
    if (res.ok) {
      // Agregar a la lista en memoria y seleccionar
      const nuevaPersona = { id: data.beneficiario_id, nombre_apodo: nombre };
      asignadosData.unshift(nuevaPersona);  // al principio para que aparezca de primero
      seleccionarPersonaSeg(data.beneficiario_id, nombre);
      cerrarFormNuevoSeg();
      toast(email ? '✓ Persona creada. Se envió correo para configurar contraseña.' : '✓ Persona creada y seleccionada.');
    } else {
      if (errorEl) { errorEl.textContent = data.detail || 'Error al crear persona.'; errorEl.style.display = 'block'; }
    }
  } catch(e) {
    if (errorEl) { errorEl.textContent = 'Error de conexión.'; errorEl.style.display = 'block'; }
  }

  if (btn) { btn.textContent = 'Crear y seleccionar'; btn.disabled = false; }
}

// ── Modales y helpers ──────────────────────────────────────────────────────
function cerrarModales() {
  _delSegId = null; _delPcId = null;
  ['modal-del-seg','modal-del-pc'].forEach(id => {
    const m = document.getElementById(id);
    if (m) m.style.display = 'none';
  });
}

function toast(msg, type) {
  const t = document.createElement('div');
  t.textContent = msg;
  const bg = type === 'error' ? 'var(--error)' : 'var(--primary)';
  t.style.cssText = 'position:fixed;bottom:1.5rem;right:1.5rem;z-index:2000;background:' + bg + ';color:#fff;padding:0.75rem 1.25rem;border-radius:var(--radius-md);font-size:0.85rem;font-weight:600;box-shadow:0 4px 20px rgba(0,0,0,0.2)';
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 3000);
}

// ── Event listeners para botones (evitar onclick inline) ──────────────────
document.addEventListener('DOMContentLoaded', () => {
  // Botones de formulario seguimiento
  document.getElementById('btn-limpiar-seg')?.addEventListener('click', limpiarSeg);
  document.getElementById('btn-guardar-seg')?.addEventListener('click', guardarSeguimiento);

  // Botones de formulario primer contacto
  document.getElementById('btn-limpiar-pc')?.addEventListener('click', limpiarPC);
  document.getElementById('btn-guardar-pc')?.addEventListener('click', guardarPrimerContacto);

  // Modales seguimiento
  document.getElementById('btn-cancel-seg')?.addEventListener('click', cerrarModales);
  document.getElementById('btn-del-seg')?.addEventListener('click', confirmarDelSeg);

  // Modales primer contacto
  document.getElementById('btn-cancel-pc')?.addEventListener('click', cerrarModales);
  document.getElementById('btn-del-pc')?.addEventListener('click', confirmarDelPC);

  // Cerrar modal al hacer clic fuera
  ['modal-del-seg','modal-del-pc'].forEach(id => {
    const m = document.getElementById(id);
    if (m) m.addEventListener('click', e => { if (e.target === m) cerrarModales(); });
  });
});

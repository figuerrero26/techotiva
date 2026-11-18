/* ═══ MASCATE — DASHBOARD JS ═══ */

const API    = window.location.origin;
const token  = localStorage.getItem('mascate_token');
const rol    = localStorage.getItem('mascate_rol');
const nombre = localStorage.getItem('mascate_nombre');
const email  = localStorage.getItem('mascate_email');

if (!token || !rol) { window.location.href = '/login'; }

function authHeaders() { return { 'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json' }; }
function authGet()     { return { headers: { 'Authorization': 'Bearer ' + token } }; }

// ── Logout ──
function doLogout() {
  // Avisar al servidor para que deje de aparecer en "sesiones activas"
  if (token) {
    try { fetch(API + '/auth/logout', { method: 'POST', ...authGet(), keepalive: true }).catch(() => {}); } catch(e) {}
  }
  ['mascate_token','mascate_rol','mascate_nombre','mascate_email'].forEach(k => localStorage.removeItem(k));
  window.location.href = '/login';
}

// Pulso de actividad (sesiones activas): cada 2 min mientras la pestaña esté visible
if (token) {
  setInterval(() => {
    if (document.visibilityState !== 'visible') return;
    fetch(API + '/auth/ping', { method: 'POST', ...authGet() }).catch(() => {});
  }, 120000);
}

document.querySelectorAll('.sb-user').forEach(u => {
  const btn = document.createElement('button');
  btn.textContent = 'Cerrar sesion';
  btn.className   = 'btn btn-sm btn-outline';
  btn.style.cssText = 'margin-top:0.5rem;width:100%;font-size:0.72rem;';
  btn.onclick = doLogout;
  u.after(btn);
});

// ── Navegación ──
function showScreen(role) {
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  document.getElementById('screen-' + role)?.classList.add('active');
}

// ── Helpers UI ──
function setStatVal(screen, index, value) {
  const cards = document.querySelectorAll(`#screen-${screen} .stats-row:not(.ind-row) .stat-val`);
  if (cards[index] != null) cards[index].textContent = value;
}
function setHTML(el, html) { if (el) el.innerHTML = html; }
function setText(id, val)  { const el = document.getElementById(id); if (el && val != null) el.textContent = val; }

// ── Init ──
window.addEventListener('DOMContentLoaded', async () => {
  showScreen(rol);

  // Notif badge
  try {
    let hay = false;
    if (rol === 'admin') {
      const [alertas, users] = await Promise.all([
        fetch(API + '/admin/alertas',  authGet()).then(r => r.json()),
        fetch(API + '/admin/usuarios', authGet()).then(r => r.json()),
      ]);
      hay = alertas.length > 0 || users.some(u => u.status === 'pendiente');
    } else if (rol === 'prescriptor') {
      const asignados = await fetch(API + '/prescriptores/mis-asignados', authGet()).then(r => r.json());
      hay = asignados.some(a => a.estado === 'urgente' || a.estado === 'revisar');
    } else if (rol === 'dispositivo') {
        const me = await fetch(API + '/dispositivos/me', authGet()).then(r => r.json());
        if (me && me.id) {
          const pend = await fetch(API + '/dispositivos/' + me.id + '/prescriptores/pendientes', authGet()).then(r => r.json());
          hay = pend.length > 0;
        }
    }
    if (hay) document.querySelectorAll('.notif-dot').forEach(d => d.style.display = 'block');
  } catch(e) {}

  try {
    if      (rol === 'dispositivo')  await loadDispositivo();
    else if (rol === 'prescriptor')  await loadPrescriptor();
    else if (rol === 'beneficiario') await loadBeneficiario();
    else if (rol === 'admin')        await loadAdmin();
  } catch(e) { console.error('Error cargando datos:', e); }
});

// ═══ DISPOSITIVO ═══
async function loadDispositivo() {
  setText('dispo-sb-name', nombre);
  setText('dispo-sb-uname', nombre);
  setText('dispo-sb-uemail', email || '');
  const bAvatar = document.getElementById('dispo-sb-avatar');
  if (bAvatar && nombre) bAvatar.textContent = nombre.substring(0,2).toUpperCase();

  const d = await fetch(API + '/dispositivos/me', authGet()).then(r => r.json());
  if (!d || !d.id) return;

  try {
    const stats = await fetch(API + '/dispositivos/' + d.id + '/estadisticas', authGet()).then(r => r.json());
    setStatVal('dispositivo', 0, stats.beneficiarios_activos);
    setStatVal('dispositivo', 1, stats.actividades_registradas);
    setStatVal('dispositivo', 2, stats.seguimientos_semana);

    const h1 = document.querySelector('#screen-dispositivo .page-header h1');
    if (h1) h1.textContent = 'Bienvenidx, ' + nombre + ' 👋';
    const sbName = document.querySelector('#screen-dispositivo .sb-uname');
    if (sbName) sbName.textContent = nombre;

    // Botón registrar actividad → /actividades
    const btnAct = document.querySelector('#screen-dispositivo .topbar-right .btn-green');
    if (btnAct) btnAct.onclick = () => window.location.href = '/actividades';

    // Prescriptores pendientes de aprobación
    try {
      const pendientes = await fetch(API + '/dispositivos/' + d.id + '/prescriptores/pendientes', authGet()).then(r => r.json());
      const panelPend  = document.getElementById('disp-panel-pendientes');
      const listaPend  = document.getElementById('disp-pendientes-list');
      if (panelPend) panelPend.style.display = pendientes.length > 0 ? 'block' : 'none';
      if (listaPend && pendientes.length > 0) {
        listaPend.innerHTML = pendientes.map(p => `
          <div class="list-row" style="padding:0.6rem 0;border-bottom:1px solid var(--border)">
            <div class="list-avatar" style="flex-shrink:0">${(p.nombre_completo||'??').substring(0,2).toUpperCase()}</div>
            <div class="list-info"><div class="list-name">${p.nombre_completo||'—'}</div><div class="list-sub">${p.perfil_disciplina||'—'}</div></div>
            <div style="display:flex;gap:0.4rem;flex-shrink:0">
              <button class="btn btn-sm btn-green" onclick="window.aprobarPrescriptor(${d.id},${p.id})">✓ Aprobar</button>
              <button class="btn btn-sm btn-outline" style="color:var(--error);border-color:var(--error)" onclick="window.rechazarPrescriptor(${d.id},${p.id})">✕ Rechazar</button>
            </div>
          </div>`).join('');
      }
    } catch(e) {}

    // Beneficiarios
    const benefs = await fetch(API + '/dispositivos/' + d.id + '/beneficiarios', authGet()).then(r => r.json());
    const listPanel = document.getElementById('disp-panel-beneficiarios');
    if (listPanel && benefs.length > 0) {
      let html = '<div class="panel-head"><span class="panel-title">Beneficiarixs recientes</span><button class="panel-action" onclick="window.location.href=\'/usuarios\'">Ver todos →</button></div>';
      benefs.forEach(b => {
        const i = b.nombre_apodo.substring(0,2).toUpperCase();
        html += `<div class="list-row"><div class="list-avatar">${i}</div><div class="list-info"><div class="list-name">${b.nombre_apodo}</div></div><span class="tag green">Activo</span></div>`;
      });
      setHTML(listPanel, html);
    }

    // Actividades
    const acts = await fetch(API + '/actividades/?dispositivo_id=' + d.id).then(r => r.json());
    const actPanel = document.getElementById('disp-panel-actividades');
    if (actPanel && acts.length > 0) {
      let html = '<div class="panel-head"><span class="panel-title">Actividades</span><button class="panel-action" onclick="window.location.href=\'/actividades\'">+ Nueva</button></div>';
      acts.forEach(a => {
        html += `<div class="list-row"><div class="list-avatar" style="background:var(--primary-dim);font-size:1.1rem">${a.emoji||'📅'}</div><div class="list-info"><div class="list-name">${a.nombre}</div><div class="list-sub">${a.dia_semana} - ${a.hora} - ${a.lugar}</div></div><span class="tag green">${a.tipo}</span></div>`;
      });
      setHTML(actPanel, html);
    }

  } catch(e) { console.error('Error cargando dispositivo:', e); }
}

// ═══ PRESCRIPTOR ═══
async function loadPrescriptor() {
  setText('presc-sb-name', nombre);
  setText('presc-sb-uname', nombre);
  setText('presc-sb-uemail', email || '');
  const bAvatar = document.getElementById('sb-avatar');
  if (bAvatar && nombre) bAvatar.textContent = nombre.substring(0,2).toUpperCase();

  const h1 = document.querySelector('#screen-prescriptor .page-header h1');
  if (h1) h1.textContent = 'Hola, ' + nombre + ' 🎯';

  // Botón + Ingresar info → /reportar-info
  const btnInfo = document.getElementById('presc-btn-info');
  if (btnInfo) btnInfo.onclick = () => window.location.href = '/reportar-info';

  // Ver todas → /usuarios (asignados)
  const btnVerTodas = document.querySelector('#screen-prescriptor .panel-action');
  if (btnVerTodas) btnVerTodas.onclick = () => window.location.href = '/usuarios';

  // Tarjeta dispositivo
  try {
    const me = await fetch(API + '/prescriptores/me', authGet()).then(r => r.json());
    const tag = document.getElementById('presc-disp-tag');
    if (tag) tag.style.visibility = 'visible';
    if (me.dispositivo_id && me.dispositivo_nombre) {
      document.getElementById('presc-disp-nombre').textContent = me.dispositivo_nombre;
      document.getElementById('presc-disp-sub').textContent = 'Dispositivo asignado';
      if (tag) { tag.textContent = 'Activo'; tag.className = 'tag green'; }
    } else {
      document.getElementById('presc-disp-nombre').textContent = 'Sin dispositivo asignado';
      document.getElementById('presc-disp-sub').textContent = 'El administrador debe asignarte un dispositivo';
      if (tag) { tag.textContent = 'Sin asignar'; tag.className = 'tag rust'; }
    }
  } catch(e) {
    document.getElementById('presc-disp-nombre').textContent = 'No se pudo cargar';
    console.error('Error cargando dispositivo prescriptor:', e);
  }

  try {
    const asignados = await fetch(API + '/prescriptores/mis-asignados', authGet()).then(r => r.json());
    setStatVal('prescriptor', 0, asignados.length);
    setStatVal('prescriptor', 2, asignados.filter(a => a.estado === 'urgente').length);

    // Sub header
    setText('presc-sub', 'Prescriptxr · ' + asignados.length + ' personas asignadas');

    // Panel asignados — 2 columnas
    const grid = document.getElementById('presc-asignados-grid');
    if (grid && asignados.length > 0) {
      const mitad = Math.ceil(asignados.length / 2);
      const col1  = asignados.slice(0, mitad);
      const col2  = asignados.slice(mitad);
      const renderCol = arr => arr.map(a => {
        const tagClass = a.estado==='urgente'?'rust':a.estado==='revisar'?'mustard':a.estado==='finalizado'?'blue':a.estado==='desvinculado'?'':'green';
        const label    = a.estado==='urgente'?'Urgente':a.estado==='revisar'?'Revisar':a.estado==='finalizado'?'Proceso finalizado':a.estado==='desvinculado'?'Desvinculado':'Al día';
        const dias     = a.dias_sin_sesion != null ? 'Hace ' + a.dias_sin_sesion + ' días' : 'Sin sesiones';
        return `<div class="list-row"><div class="list-avatar ${tagClass}">${a.nombre_apodo.substring(0,2).toUpperCase()}</div><div class="list-info"><div class="list-name">${a.nombre_apodo}</div><div class="list-sub">${dias}${a.localidad?' · '+a.localidad:''}</div></div><span class="tag ${tagClass}">${label}</span></div>`;
      }).join('');
      grid.innerHTML = `<div>${renderCol(col1)}</div><div>${renderCol(col2)}</div>`;
    } else if (grid) {
      grid.innerHTML = '<div style="color:var(--on-bg-muted);font-size:0.85rem;padding:0.5rem">Sin personas asignadas aún.</div>';
    }

    // Select personas en formulario
    const sel = document.getElementById('presc-select-persona');
    if (sel && asignados.length > 0) {
      const activos = asignados.filter(a => a.estado !== 'finalizado');
      sel.innerHTML = activos.length
        ? activos.map(a => `<option value="${a.id}">${a.nombre_apodo}</option>`).join('')
        : '<option value="" disabled>Sin personas activas</option>';
    }

    // Botón guardar registro
    const btn = document.querySelector('#screen-prescriptor .btn-green:last-of-type');
    if (btn && btn.textContent.includes('Guardar')) {
      btn.onclick = async () => {
        const selects = document.querySelectorAll('#screen-prescriptor .frow select');
        const textarea = document.querySelector('#screen-prescriptor textarea');
        const payload = {
          beneficiario_id: parseInt(selects[0]?.value),
          tipo_registro:   selects[1]?.value ?? 'Sesion grupal',
          observaciones:   textarea?.value ?? '',
        };
        if (!payload.beneficiario_id) { alert('Selecciona una persona.'); return; }
        try {
          const res = await fetch(API + '/prescriptores/seguimientos',
            { method: 'POST', headers: authHeaders(), body: JSON.stringify(payload) });
          if (res.ok) {
            btn.textContent = '¡Guardado!';
            if (textarea) textarea.value = '';
            setTimeout(() => { btn.textContent = 'Guardar registro'; loadPrescriptor(); }, 1500);
          }
        } catch(e) { console.error(e); }
      };
    }
  } catch(e) { console.error('Error cargando asignados:', e); }

  try {
    const segs = await fetch(API + '/prescriptores/seguimientos', authGet()).then(r => r.json());
    setStatVal('prescriptor', 1, segs.length);
  } catch(e) {}

}

// ═══ BENEFICIARIO ═══
async function loadBeneficiario() {
  setText('benef-sb-name', nombre);
  setText('benef-sb-uname', nombre);
  setText('benef-sb-uemail', email || '');
  const bAvatar = document.getElementById('benef-sb-avatar');
  if (bAvatar && nombre) bAvatar.textContent = nombre.substring(0,2).toUpperCase();

  // Chips de filtro
  document.querySelectorAll('#screen-beneficiario .chip').forEach(chip => {
    chip.style.cursor = 'pointer';
    chip.onclick = () => {
      document.querySelectorAll('#screen-beneficiario .chip').forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      const tipo = chip.textContent.trim();
      filtrarActsBenef(tipo === 'Todos' ? null : tipo.split(' ').slice(1).join(' '));
    };
  });

  // Buscador
  const searchInput = document.querySelector('#screen-beneficiario .search-bar input');
  if (searchInput) {
    searchInput.oninput = () => filtrarActsBenef(null, searchInput.value);
  }

  try {
    // Solo actividades a las que el beneficiario está inscrito
    const misActs = await fetch(API + '/beneficiarios/mis-actividades', authGet()).then(r => r.json());
    window._benef_acts = misActs;
    renderActsBenef(misActs);

    // Panel dispositivo: derivar los dispositivos únicos de sus actividades
    const dispPanel = document.getElementById('benef-disp-panel');
    if (!misActs.length) {
      // Sin inscripciones — ocultar panel dispositivo y mostrar CTA
      if (dispPanel) {
        dispPanel.innerHTML = `
          <div class="panel-head"><span class="panel-title">Sin actividades inscritas</span></div>
          <div style="color:var(--on-bg-muted);font-size:0.85rem;padding:0.5rem 0 0.25rem">
            Aún no estás inscritx en ninguna actividad.
          </div>
          <div style="margin-top:0.85rem">
            <button class="btn btn-md btn-green" style="width:100%"
              onclick="window.location.href='/actividades'">🔍 Explorar actividades</button>
          </div>`;
      }
      return;
    }

    // Obtener dispositivos únicos de las actividades inscritas
    const dispIds = [...new Set(misActs.map(a => a.dispositivo_id).filter(Boolean))];
    if (!dispIds.length || !dispPanel) return;

    // Cargar datos del primer dispositivo y listar los demás como chips
    const dispsData = await Promise.all(
      dispIds.map(id => fetch(API + '/dispositivos/' + id).then(r => r.json()).catch(() => null))
    ).then(res => res.filter(Boolean));

    if (!dispsData.length) return;

    // Renderizar selector si hay más de un dispositivo
    let dispActual = dispsData[0];

    function renderDispPanel(d) {
      const horario = d.dia_actividad
        ? d.dia_actividad + (d.hora_actividad ? ' · ' + d.hora_actividad : '')
        : '—';
      dispPanel.innerHTML = `
        <div class="panel-head">
          <span class="panel-title">Detalle del dispositivo</span>
          <button class="panel-action" onclick="window.location.href='/mapa'">Ver en mapa →</button>
        </div>
        ${dispsData.length > 1 ? `
        <div style="display:flex;gap:0.5rem;flex-wrap:wrap;margin-bottom:0.85rem">
          ${dispsData.map(dd => `
            <span class="chip${dd.id === d.id ? ' active' : ''}"
              style="cursor:pointer"
              onclick="renderDispPanel_${d.id}(window._benef_disps.find(x=>x.id===${dd.id}))">
              ${dd.nombre}
            </span>`).join('')}
        </div>` : ''}
        <div class="detail-hero">
          <h2>${d.nombre}</h2>
          <p>${d.ubicacion ? '📍 ' + d.ubicacion : '—'}</p>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.75rem">
          <div class="contact-card"><div class="contact-icon" style="background:var(--secondary-dim)">📞</div><div><div class="contact-val">${d.telefono||'—'}</div><div class="contact-lbl">Teléfono</div></div></div>
          <div class="contact-card"><div class="contact-icon" style="background:var(--tertiary-dim)">📱</div><div><div class="contact-val">${d.redes_sociales||'—'}</div><div class="contact-lbl">Instagram</div></div></div>
          <div class="contact-card"><div class="contact-icon" style="background:var(--primary-dim)">🕐</div><div><div class="contact-val">${horario}</div><div class="contact-lbl">Horario</div></div></div>
          <div class="contact-card"><div class="contact-icon" style="background:var(--error-dim)">👤</div><div><div class="contact-val" id="benef-facilitadora">—</div><div class="contact-lbl">Facilitadxra</div></div></div>
        </div>
        `;
    }

    // Exponer para los chips dinámicos
    window._benef_disps = dispsData;
    window[`renderDispPanel_${dispsData[0].id}`] = renderDispPanel;
    dispsData.forEach(d => { window[`renderDispPanel_${d.id}`] = renderDispPanel; });

    renderDispPanel(dispActual);

  } catch(e) { console.error('Error beneficiario:', e); }
}

function renderActsBenef(acts) {
  const grid = document.getElementById('benef-acts-grid');
  if (!grid) return;
  if (!acts.length) {
    grid.innerHTML = '<div style="color:var(--on-bg-muted);font-size:0.85rem;padding:0.5rem">No estás inscritx en ninguna actividad aún. <a href="/actividades" style="color:var(--primary);font-weight:600">Explorar →</a></div>';
    return;
  }
  const TAG_COLOR = { Artístico:'green', Deportivo:'mustard', Cultural:'rust', Ambiental:'green', Educativo:'purple', Escucha:'blue' };
  grid.innerHTML = acts.map(a => `
    <div class="act-card">
      <div class="act-card-emoji">${a.emoji||'📅'}</div>
      <div class="act-card-name">${a.nombre}</div>
      <div class="act-card-org">${a.lugar||'—'}</div>
      <div class="act-card-meta">
        <span class="tag ${TAG_COLOR[a.tipo]||'mustard'}">${a.tipo||''}</span>
        <span style="font-size:0.72rem;color:var(--on-bg-muted)">${a.dia_semana||''} · ${a.hora||''}</span>
      </div>
    </div>`).join('');
}

function filtrarActsBenef(tipo, q) {
  let acts = window._benef_acts || [];
  if (tipo) acts = acts.filter(a => a.tipo === tipo);
  if (q)    acts = acts.filter(a => (a.nombre+a.lugar+a.tipo).toLowerCase().includes(q.toLowerCase()));
  renderActsBenef(acts);
}

// ═══ ADMIN ═══
async function loadAdmin() {
  setText('admin-sb-name', nombre);
  setText('admin-sb-uname', nombre);
  setText('admin-sb-uemail', email || '');

  const adminAvatar = document.querySelector('#screen-admin #admin-sb-avatar');
  if (adminAvatar && nombre) {
    adminAvatar.textContent = nombre.substring(0,2).toUpperCase();
    adminAvatar.style.background = 'var(--primary-dim)';
    adminAvatar.style.color = 'var(--primary)';
  }
  // Botones topbar
  document.querySelector('#screen-admin .topbar-right .btn-mustard')?.addEventListener('click', () => {
    window.location.href = '/dispositivos-admin';
  });

  // Gestionar →
  document.querySelector('#screen-admin .panel-action')?.addEventListener('click', () => {
    window.location.href = '/usuarios';
  });

  const dbcSel = document.getElementById('ind-dbc');
  if (dbcSel && !dbcSel.dataset.bound) {
    dbcSel.dataset.bound = '1';
    dbcSel.addEventListener('change', () => loadIndicadores(dbcSel.value));
  }
  loadIndicadores(dbcSel?.value || '');

  try {
    const stats = await fetch(API + '/admin/stats', authGet()).then(r => r.json());
    setStatVal('admin', 0, stats.total_dispositivos);
    setStatVal('admin', 1, stats.total_usuarios);
    setStatVal('admin', 2, stats.total_prescriptores);
    setStatVal('admin', 3, stats.alertas_pendientes);
  } catch(e) { console.error(e); }

  try {
    const alertas    = await fetch(API + '/admin/alertas', authGet()).then(r => r.json());
    const alertPanel = document.getElementById('admin-alertas-panel');
    if (alertPanel) {
      let html = '<div class="panel-head"><span class="panel-title">Alertas del sistema</span><button class="panel-action" onclick="window.location.href=\'/notificaciones\'">Ver todas →</button></div>';
      if (alertas.length) {
        alertas.forEach(a => {
          html += `<div class="list-row"><div class="list-avatar rust" style="border-radius:8px;font-size:1rem">⚠️</div><div class="list-info"><div class="list-name">${a.mensaje}</div><div class="list-sub">${a.dispositivo}</div></div><span class="tag rust">Urgente</span></div>`;
        });
      } else {
        html += '<div style="color:var(--on-bg-muted);font-size:0.85rem;padding:0.5rem">Sin alertas activas.</div>';
      }

      // Mostrar también dispositivos pendientes de aprobación
      try {
        const users = await fetch(API + '/admin/usuarios', authGet()).then(r => r.json());
        const pendDisps = users.filter(u => u.rol === 'dispositivo' && u.status === 'pendiente');
        if (pendDisps.length) {
          html += `<div style="margin-top:0.75rem;padding-top:0.75rem;border-top:1px solid var(--border)"><div style="font-size:0.78rem;color:var(--on-bg-muted);margin-bottom:0.5rem">Dispositivos pendientes de aprobación</div>`;
          pendDisps.forEach(u => {
            html += `<div class="list-row"><div class="list-avatar mustard" style="font-size:1rem">🏘️</div><div class="list-info"><div class="list-name">${u.nombre||u.email}</div><div class="list-sub">${u.email}</div></div><button class="btn btn-sm btn-green" onclick="aprobarDisp(${u.id})">✓ Aprobar</button></div>`;
          });
          html += '</div>';
        }
      } catch(e) {}

      setHTML(alertPanel, html);
    }
  } catch(e) {}

  try {
    const disps = await fetch(API + '/admin/dispositivos', authGet()).then(r => r.json());
    const tbody = document.getElementById('admin-disp-tbody');
    if (tbody) {
      tbody.innerHTML = disps.length
        ? disps.map(d => `<tr>
            <td>${d.nombre}</td>
            <td>${d.tipo_servicio ? `<span class="tag green">${d.tipo_servicio}</span>` : '—'}</td>
            <td style="color:var(--primary);font-weight:700">${d.num_beneficiarios}</td>
            <td>${d.prescriptor||'—'}</td>
            <td>${d.activo?'<span class="tag green">Activo</span>':'<span class="tag rust">Inactivo</span>'}</td>
            <td><button class="btn btn-sm btn-outline" onclick="window.location.href='/dispositivos-admin'">Editar</button></td>
          </tr>`).join('')
        : '<tr><td colspan="6" style="color:var(--on-bg-muted);text-align:center">Sin dispositivos.</td></tr>';
    }
  } catch(e) {}

  try {
    const users    = await fetch(API + '/admin/usuarios', authGet()).then(r => r.json());
    // Distribución por rol — donut (circunferencia = 2π × 28 ≈ 176)
    if (document.getElementById('rol-donut')) {
      const be = users.filter(u => u.rol==='beneficiario').length;
      const pr = users.filter(u => u.rol==='prescriptor').length;
      const d2 = users.filter(u => u.rol==='dispositivo').length;
      const tot  = Math.max(be + pr + d2, 1);
      const CIRC = 176;
      const bLen = Math.round(be / tot * CIRC);
      const pLen = Math.round(pr / tot * CIRC);
      const dLen = Math.round(d2 / tot * CIRC);
      const arc = (id, len, offset) => {
        const el = document.getElementById(id);
        if (el) { el.setAttribute('stroke-dasharray', `${len} ${CIRC - len}`); el.setAttribute('stroke-dashoffset', `-${offset}`); }
      };
      arc('donut-benef', bLen, 0);
      arc('donut-presc', pLen, bLen);
      arc('donut-disp',  dLen, bLen + pLen);
      const pct = n => Math.round(n / tot * 100);
      setText('lg-benef', `Beneficiarixs · ${be} (${pct(be)}%)`);
      setText('lg-presc', `Prescriptxres · ${pr} (${pct(pr)}%)`);
      setText('lg-disp',  `Dispositivos · ${d2} (${pct(d2)}%)`);
    }
  } catch(e) {}
}

// ── Indicadores de la población (panel central admin) ──
function _indBars(obj, total) {
  const entries = Object.entries(obj || {});
  if (!entries.length) return '<div class="ind-empty">Sin datos aún.</div>';
  const max = Math.max(total || 0, ...entries.map(([, v]) => v), 1);
  return entries.map(([k, v]) => `<div class="ind-bar">
      <span>${k}</span>
      <div class="seed-track"><div class="seed-fill" style="width:${Math.round(v / max * 100)}%"></div></div>
      <b>${v}</b>
    </div>`).join('');
}

async function loadIndicadores(dispositivoId) {
  let d;
  try {
    const qs = dispositivoId ? '?dispositivo_id=' + dispositivoId : '';
    const res = await fetch(API + '/admin/indicadores' + qs, authGet());
    if (!res.ok) return;
    d = await res.json();
  } catch(e) { console.error(e); return; }

  const sel = document.getElementById('ind-dbc');
  if (sel && sel.options.length <= 1) {
    d.dispositivos.forEach(x => sel.insertAdjacentHTML('beforeend', `<option value="${x.id}">${x.nombre}</option>`));
  }

  const total = d.total_beneficiarios;
  const base  = d.con_primer_contacto;
  setText('ind-benef', total);
  setText('ind-spa', d.spa.total);
  // SPA cuenta solo personas en proceso activo (para priorizar)
  const baseSpa = d.spa.base || 0;
  setText('ind-spa-lbl', `Usuarios de SPA${baseSpa ? ' · ' + Math.round(d.spa.total / baseSpa * 100) + '%' : ''}`);

  const emo = d.emociones;
  const balEl = document.getElementById('ind-balance');
  if (balEl) {
    if (!emo.personas) {
      balEl.textContent = 'Sin datos';
    } else {
      const pos = emo.positivas, neg = emo.negativas;
      balEl.textContent = pos > neg ? 'Positivo' : neg > pos ? 'Negativo' : 'Neutro';
      balEl.style.color = pos > neg ? 'var(--secondary)' : neg > pos ? 'var(--error)' : 'var(--on-bg-muted)';
    }
  }
  setText('ind-balance-lbl', `Balance emocional · 😊 ${emo.positivas} / 😟 ${emo.negativas}`);
  setText('ind-emo-n', `${emo.personas} persona${emo.personas === 1 ? '' : 's'}`);

  // Cada emoción principal con su barra; al hacer clic se despliegan sus niveles de intensidad
  const maxEmo = Math.max(1, ...Object.values(emo.conteo));
  const emoGrupo = nombres => nombres.map(n => {
    const v = emo.conteo[n] || 0;
    const niveles = Object.entries((emo.niveles || {})[n] || {});
    const maxNiv = Math.max(1, ...niveles.map(([, c]) => c));
    const detalle = niveles.map(([k, c]) => `<div class="ind-bar" style="font-size:0.76rem;padding:0.15rem 0">
        <span style="padding-left:1.1rem;color:var(--on-bg-muted)">${k}</span>
        <div class="seed-track" style="height:5px"><div class="seed-fill" style="width:${Math.round(c / maxNiv * 100)}%;opacity:0.7"></div></div>
        <b style="font-weight:600">${c}</b>
      </div>`).join('');
    return `<div class="ind-bar ind-emo" ${v ? 'onclick="this.classList.toggle(\'open\');this.nextElementSibling.hidden=!this.nextElementSibling.hidden"' : ''}
        title="${v ? 'Clic para ver los niveles de intensidad' : ''}" style="${v ? 'cursor:pointer' : ''}">
        <span>${v ? '<span class="ind-caret">▸</span>' : '<span class="ind-caret" style="visibility:hidden">▸</span>'} ${n}</span>
        <div class="seed-track"><div class="seed-fill" style="width:${Math.round(v / maxEmo * 100)}%"></div></div>
        <b>${v}</b>
      </div>
      <div hidden>${detalle}</div>`;
  }).join('');

  setHTML(document.getElementById('ind-emociones'),
    emo.personas
      ? `<div class="ind-sub">Positivas</div>${emoGrupo(['Alegría', 'Confianza', 'Anticipación'])}
         <div class="ind-sub">Neutra</div>${emoGrupo(['Sorpresa'])}
         <div class="ind-sub">Negativas</div>${emoGrupo(['Miedo', 'Tristeza', 'Disgusto', 'Ira'])}
         <div class="ind-empty" style="font-size:0.72rem">Haz clic en una emoción para ver sus niveles de intensidad (leve · media · intensa).</div>`
      : '<div class="ind-empty">Aún no hay primeros contactos con la rueda de emociones diligenciada.</div>');

  // Barras de SPA clicables: cada una abre la lista de personas de ese tipo
  const maxSpa = Math.max(baseSpa, 1);
  const barrasSpa = Object.entries(d.spa.tipos).map(([k, v]) => `<div class="ind-bar ind-spa-bar"
      onclick="verUsuariosSpa('${k}')" title="Clic para ver quiénes son">
      <span>${k}</span>
      <div class="seed-track"><div class="seed-fill" style="width:${Math.round(v / maxSpa * 100)}%"></div></div>
      <b>${v}</b>
    </div>`).join('');

  setHTML(document.getElementById('ind-caract'), `
    <div class="ind-sub">Usuarios de SPA</div>${barrasSpa}
    <div class="ind-sub">Género</div>${_indBars(d.genero, total)}
    <div class="ind-sub">Edad</div>${_indBars(d.edades, total)}
    ${Object.keys(d.poblaciones).length ? `<div class="ind-sub">Poblaciones de especial interés</div>${_indBars(d.poblaciones, base)}` : ''}`);

  setHTML(document.getElementById('ind-cobertura'),
    _indBars(Object.fromEntries(d.cobertura.map(c => [c.nombre, c.beneficiarios]))));

  setHTML(document.getElementById('ind-categorias'),
    _indBars(d.categorias, base) +
    `<div class="ind-empty" style="font-size:0.75rem">Personas con al menos una situación de cada categoría (según su último primer contacto).</div>`);
}

// ── Lista de personas con consumo de SPA (clic en la tarjeta o en una barra) ──
function _escHtml(v) {
  return String(v ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

async function verUsuariosSpa(tipo) {
  const dbc = document.getElementById('ind-dbc');
  const params = new URLSearchParams();
  if (dbc?.value) params.set('dispositivo_id', dbc.value);
  if (tipo) params.set('tipo', tipo);

  const modal = document.getElementById('modal-spa');
  const tbody = document.getElementById('modal-spa-tbody');
  document.getElementById('modal-spa-titulo').textContent = '💊 ' + (tipo ? 'Consumo: ' + tipo : 'Usuarios de SPA');
  const nombreDbc = dbc?.value ? dbc.options[dbc.selectedIndex].text : 'Todos los DBC';
  document.getElementById('modal-spa-sub').textContent =
    `${nombreDbc} · solo personas en proceso activo, según su último primer contacto.`;
  tbody.innerHTML = '<tr><td colspan="4" style="color:var(--on-bg-muted);text-align:center">Cargando...</td></tr>';
  modal.style.display = 'flex';

  try {
    const res = await fetch(API + '/admin/indicadores/spa?' + params.toString(), authGet());
    const lista = res.ok ? await res.json() : [];
    document.getElementById('modal-spa-count').textContent = lista.length;
    if (!lista.length) {
      tbody.innerHTML = '<tr><td colspan="4" style="color:var(--on-bg-muted);text-align:center">No hay personas en esta situación.</td></tr>';
      return;
    }
    tbody.innerHTML = lista.map(p => {
      const fecha = p.fecha_contacto
        ? new Date(p.fecha_contacto + 'T00:00:00').toLocaleDateString('es-CO', { day:'2-digit', month:'short', year:'numeric' })
        : '—';
      const tipos = p.tipos.map(t => `<span class="tag rust" style="font-size:0.7rem;margin:0.1rem">${_escHtml(t)}</span>`).join('');
      return `<tr>
        <td style="font-weight:600">${_escHtml(p.nombre)}</td>
        <td style="font-size:0.82rem">${_escHtml(p.dispositivo)}</td>
        <td>${tipos}</td>
        <td style="font-size:0.82rem;color:var(--on-bg-muted)">${fecha}</td>
      </tr>`;
    }).join('');
  } catch(e) {
    tbody.innerHTML = '<tr><td colspan="4" style="color:var(--error);text-align:center">Error al cargar.</td></tr>';
  }
}

function cerrarModalSpa() {
  document.getElementById('modal-spa').style.display = 'none';
}

async function aprobarDisp(usuarioId) {
  try {
    const res = await fetch(API + '/admin/usuarios/' + usuarioId + '/aprobar',
      { method: 'POST', headers: authHeaders() });
    if (res.ok) { loadAdmin(); }
    else { const d = await res.json(); alert('Error: ' + (d.detail||'No se pudo aprobar.')); }
  } catch(e) { console.error(e); }
}

async function aprobarPrescriptor(dispId, prescId) {
  try {
    const res = await fetch(API + '/dispositivos/' + dispId + '/prescriptores/' + prescId + '/aprobar',
      { method: 'POST', headers: authHeaders() });
    if (res.ok) { loadDispositivo(); }
    else { const d = await res.json(); alert('Error: ' + (d.detail||'No se pudo aprobar.')); }
  } catch(e) { console.error(e); }
}

window.rechazarPrescriptor = async function(dispId, prescId) {
  if (!confirm('¿Rechazar esta solicitud? La cuenta se eliminará y la persona podrá volver a registrarse con ese correo.')) return;
  try {
    const res = await fetch(API + '/dispositivos/' + dispId + '/prescriptores/' + prescId + '/rechazar',
      { method: 'PUT', headers: authHeaders() });
    if (res.ok) { loadDispositivo(); }
    else { const d = await res.json(); alert('Error: ' + (d.detail||'No se pudo rechazar.')); }
  } catch(e) { console.error(e); }
};


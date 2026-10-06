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
  ['mascate_token','mascate_rol','mascate_nombre','mascate_email'].forEach(k => localStorage.removeItem(k));
  window.location.href = '/login';
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
  const cards = document.querySelectorAll(`#screen-${screen} .stat-val`);
  if (cards[index] != null) cards[index].textContent = value;
}
function setHTML(el, html) { if (el) el.innerHTML = html; }
function setText(id, val)  { const el = document.getElementById(id); if (el && val != null) el.textContent = val; }

// ── Init ──
window.addEventListener('DOMContentLoaded', async () => {
  showScreen(rol);
  if (rol !== 'admin') document.querySelector('.demo-bar')?.remove();

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
    setStatVal('dispositivo', 3, '—');

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
    } else if (me.solicitud_dispositivo_id && me.solicitud_dispositivo_nombre) {
      document.getElementById('presc-disp-nombre').textContent = me.solicitud_dispositivo_nombre;
      document.getElementById('presc-disp-sub').textContent = 'Solicitud pendiente de aprobación';
      if (tag) { tag.textContent = 'Pendiente'; tag.className = 'tag mustard'; }
    } else {
      document.getElementById('presc-disp-nombre').textContent = 'Sin dispositivo asignado';
      document.getElementById('presc-disp-sub').textContent = 'Solicita unirte a un dispositivo';
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
        const tagClass = a.estado==='urgente'?'rust':a.estado==='revisar'?'mustard':'green';
        const label    = a.estado==='urgente'?'Urgente':a.estado==='revisar'?'Revisar':'Al día';
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
      sel.innerHTML = asignados.map(a => `<option value="${a.id}">${a.nombre_apodo}</option>`).join('');
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
    const dispPanel = document.querySelector('#screen-beneficiario .panel');
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

  try {
    const stats = await fetch(API + '/admin/stats', authGet()).then(r => r.json());
    setStatVal('admin', 0, stats.total_dispositivos);
    setStatVal('admin', 1, stats.total_usuarios);
    setStatVal('admin', 2, stats.total_prescriptores);
    setStatVal('admin', 3, stats.alertas_pendientes);
  } catch(e) { console.error(e); }

  try {
    const alertas    = await fetch(API + '/admin/alertas', authGet()).then(r => r.json());
    const alertPanel = document.querySelectorAll('#screen-admin .grid-2 .panel')[1];
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
    const tbody = document.querySelector('#screen-admin table tbody');
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
    const rolPanel = document.querySelectorAll('#screen-admin .grid-2 .panel')[0];
    if (rolPanel) {
      const d2 = users.filter(u => u.rol==='dispositivo').length;
      const pr = users.filter(u => u.rol==='prescriptor').length;
      const be = users.filter(u => u.rol==='beneficiario').length;
      const tot = Math.max(d2, pr, be, 1);
      const fills = rolPanel.querySelectorAll('.seed-fill');
      const nums  = rolPanel.querySelectorAll('div[style*="font-weight:700"]');
      if (fills[0]) fills[0].style.width = Math.round(d2/tot*100)+'%';
      if (fills[1]) fills[1].style.width = Math.round(pr/tot*100)+'%';
      if (fills[2]) fills[2].style.width = Math.round(be/tot*100)+'%';
      if (nums[0])  nums[0].textContent  = d2;
      if (nums[1])  nums[1].textContent  = pr;
      if (nums[2])  nums[2].textContent  = be;
    }
  } catch(e) {}
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
  if (!confirm('¿Rechazar este prescriptxr?')) return;
  try {
    const res = await fetch(API + '/dispositivos/' + dispId + '/prescriptores/' + prescId + '/rechazar',
      { method: 'PUT', headers: authHeaders() });
    if (res.ok) { loadDispositivo(); }
    else { const d = await res.json(); alert('Error: ' + (d.detail||'No se pudo rechazar.')); }
  } catch(e) { console.error(e); }
};

window.rechazarDisp = async function(usuarioId) {
  if (!confirm('¿Rechazar este dispositivo?')) return;
  try {
    const res = await fetch(API + '/admin/usuarios/' + usuarioId + '/estado',
      { method: 'PUT', headers: authHeaders(),
        body: JSON.stringify({ status: 'rechazado' }) });
    if (res.ok) { loadAdmin(); }
    else { const d = await res.json(); alert('Error: ' + (d.detail||'No se pudo rechazar.')); }
  } catch(e) { console.error(e); }
};

async function inscribirseDesdeDB(actividadId) {
  try {
    const res = await fetch(API + '/beneficiarios/inscribirse', {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({ actividad_id: actividadId })
    });
    const data = await res.json();
    if (res.ok) {
      const t = document.createElement('div');
      t.textContent = '✓ Inscripción exitosa';
      t.style.cssText = 'position:fixed;bottom:1.5rem;right:1.5rem;z-index:2000;background:var(--primary);color:#fff;padding:0.75rem 1.25rem;border-radius:var(--radius-md);font-size:0.85rem;font-weight:600;box-shadow:0 4px 20px rgba(0,0,0,0.2)';
      document.body.appendChild(t);
      setTimeout(() => { t.remove(); loadBeneficiario(); }, 2000);
    } else {
      alert('Error: ' + (data.detail || 'No se pudo inscribir.'));
    }
  } catch(e) { console.error(e); }
}

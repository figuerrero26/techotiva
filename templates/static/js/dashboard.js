/* ═══ MASCATE — DASHBOARD JS ═══ */

const API    = 'http://127.0.0.1:8080';
const token  = localStorage.getItem('mascate_token');
const rol    = localStorage.getItem('mascate_rol');
const nombre = localStorage.getItem('mascate_nombre');

if (!token || !rol) { window.location.href = '/login'; }

// ── Helpers de autenticación ──
function authHeaders() { return { 'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json' }; }
function authGet()     { return { headers: { 'Authorization': 'Bearer ' + token } }; }

// ── Navegación entre pantallas ──
function showScreen(role) {
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.demo-btn').forEach(b => {
    b.classList.toggle('active', b.textContent.toLowerCase().includes(role));
  });
  document.getElementById('screen-' + role)?.classList.add('active');
}

// ── Logout ──
function doLogout() {
  ['mascate_token', 'mascate_rol', 'mascate_nombre'].forEach(k => localStorage.removeItem(k));
  window.location.href = '/login';
}

// Agregar botón logout a cada sidebar
document.querySelectorAll('.sb-user').forEach(u => {
  const btn = document.createElement('button');
  btn.textContent = 'Cerrar sesion';
  btn.className = 'btn btn-sm btn-outline';
  btn.style.cssText = 'margin-top:0.5rem;width:100%;font-size:0.72rem;';
  btn.onclick = doLogout;
  u.after(btn);
});

// ── Init ──
window.addEventListener('DOMContentLoaded', async () => {
  showScreen(rol);
  if (rol !== 'admin') document.querySelector('.demo-bar')?.remove();
  try {
    if      (rol === 'dispositivo') await loadDispositivo();
    else if (rol === 'prescriptor') await loadPrescriptor();
    else if (rol === 'beneficiario') await loadBeneficiario();
    else if (rol === 'admin')       await loadAdmin();
  } catch(e) { console.error('Error cargando datos:', e); }
});

// ── Helpers de UI ──
function setStatVal(screen, index, value) {
  const cards = document.querySelectorAll(`#screen-${screen} .stat-val`);
  if (cards[index] != null) cards[index].textContent = value;
}

function setInnerHTML(el, html) { if (el) el.innerHTML = html; }

// ═══ DISPOSITIVO ═══
async function loadDispositivo() {
  const disps = await (await fetch(API + '/dispositivos/', authGet())).json();
  for (const d of disps) {
    try {
      const stats = await (await fetch(API + '/dispositivos/' + d.id + '/estadisticas', authGet())).json();
      setStatVal('dispositivo', 0, stats.beneficiarios_activos);
      setStatVal('dispositivo', 1, stats.actividades_registradas);
      setStatVal('dispositivo', 2, stats.valoracion_promedio ?? '—');
      setStatVal('dispositivo', 3, stats.seguimientos_semana);

      // Header
      const h1 = document.querySelector('#screen-dispositivo .page-header h1');
      if (h1) h1.textContent = 'Bienvenidx, ' + nombre + ' 👋';

      // Sidebar user
      const sbName = document.querySelector('#screen-dispositivo .sb-uname');
      if (sbName) sbName.textContent = nombre;

      // Beneficiarios
      const benefs = await (await fetch(API + '/dispositivos/' + d.id + '/beneficiarios', authGet())).json();
      const listPanel = document.querySelectorAll('#screen-dispositivo .panel')[2];
      if (listPanel && benefs.length > 0) {
        let html = '<div class="panel-head"><span class="panel-title">Beneficiarixs</span></div>';
        benefs.forEach(b => {
          const ini = b.nombre_apodo.substring(0, 2).toUpperCase();
          html += `<div class="list-row"><div class="list-avatar">${ini}</div><div class="list-info"><div class="list-name">${b.nombre_apodo}</div></div><span class="tag green">Activo</span></div>`;
        });
        setInnerHTML(listPanel, html);
      }

      // Actividades
      const acts = await (await fetch(API + '/actividades/?dispositivo_id=' + d.id)).json();
      const actPanel = document.querySelectorAll('#screen-dispositivo .panel')[3];
      if (actPanel && acts.length > 0) {
        let html = '<div class="panel-head"><span class="panel-title">Actividades</span></div>';
        acts.forEach(a => {
          html += `<div class="list-row"><div class="list-avatar" style="background:var(--primary-dim);font-size:1.1rem">${a.emoji}</div><div class="list-info"><div class="list-name">${a.nombre}</div><div class="list-sub">${a.dia_semana} - ${a.hora} - ${a.lugar}</div></div><span class="tag green">${a.tipo}</span></div>`;
        });
        setInnerHTML(actPanel, html);
      }
      break;
    } catch(e) { continue; }
  }
}

// ═══ PRESCRIPTOR ═══
async function loadPrescriptor() {
  const h1 = document.querySelector('#screen-prescriptor .page-header h1');
  if (h1) h1.textContent = 'Hola, ' + nombre + ' 🎯';
  const sbName = document.querySelector('#screen-prescriptor .sb-uname');
  if (sbName) sbName.textContent = nombre;

  try {
    const asignados = await (await fetch(API + '/prescriptores/mis-asignados', authGet())).json();
    setStatVal('prescriptor', 0, asignados.length);
    setStatVal('prescriptor', 2, asignados.filter(a => a.estado === 'urgente').length);

    // Panel de asignados
    const panel = document.querySelector('#screen-prescriptor .panel.span-2');
    if (panel && asignados.length > 0) {
      let html = '<div class="panel-head"><span class="panel-title">Personas asignadas</span></div><div>';
      asignados.forEach(a => {
        const ini      = a.nombre_apodo.substring(0, 2).toUpperCase();
        const tagClass = a.estado === 'urgente' ? 'rust' : (a.estado === 'revisar' ? 'mustard' : 'green');
        const label    = a.estado === 'urgente' ? 'Urgente' : (a.estado === 'revisar' ? 'Revisar' : 'Al dia');
        const dias     = a.dias_sin_sesion != null ? 'Hace ' + a.dias_sin_sesion + ' dias' : 'Sin sesiones';
        html += `<div class="list-row"><div class="list-avatar ${tagClass}">${ini}</div><div class="list-info"><div class="list-name">${a.nombre_apodo}</div><div class="list-sub">${dias}</div></div><span class="tag ${tagClass}">${label}</span></div>`;
      });
      html += '</div>';
      setInnerHTML(panel, html);
    }

    // Formulario de seguimiento: poblar select y conectar botón
    const formPanels = document.querySelectorAll('#screen-prescriptor .panel:not(.span-2)');
    const fp = formPanels[formPanels.length - 1];
    if (fp) {
      const selects = fp.querySelectorAll('select');
      if (selects[0] && asignados.length > 0) {
        selects[0].innerHTML = asignados.map(a => `<option value="${a.id}">${a.nombre_apodo}</option>`).join('');
      }
      const btn = fp.querySelector('.btn');
      if (btn) {
        btn.onclick = async () => {
          const payload = {
            beneficiario_id: parseInt(selects[0].value),
            tipo_registro:   selects[1]?.value ?? 'Sesion grupal',
            observaciones:   fp.querySelector('textarea')?.value ?? '',
          };
          try {
            const res = await fetch(API + '/prescriptores/seguimientos', { method: 'POST', headers: authHeaders(), body: JSON.stringify(payload) });
            if (res.ok) {
              btn.textContent = 'Guardado!';
              if (fp.querySelector('textarea')) fp.querySelector('textarea').value = '';
              setTimeout(() => { btn.textContent = 'Guardar registro'; loadPrescriptor(); }, 1500);
            }
          } catch(e) { console.error(e); }
        };
      }
    }
  } catch(e) { console.error('Error cargando asignados:', e); }

  try {
    const segs = await (await fetch(API + '/prescriptores/seguimientos', authGet())).json();
    setStatVal('prescriptor', 1, segs.length);
  } catch(e) {}
}

// ═══ BENEFICIARIO ═══
async function loadBeneficiario() {
  const sbName = document.querySelector('#screen-beneficiario .sb-uname');
  if (sbName) sbName.textContent = nombre;

  try {
    const acts = await (await fetch(API + '/actividades/')).json();
    const grid = document.querySelector('#screen-beneficiario .grid-3');
    if (grid && acts.length > 0) {
      grid.innerHTML = acts.map(a =>
        `<div class="act-card"><div class="act-card-emoji">${a.emoji || ''}</div><div class="act-card-name">${a.nombre}</div><div class="act-card-org">${a.lugar}</div><div class="act-card-meta"><span class="tag green">${a.tipo || ''}</span><span style="font-size:0.72rem;color:var(--on-bg-muted)">${a.dia_semana || ''} - ${a.hora || ''}</span></div></div>`
      ).join('');
    }
  } catch(e) {}

  try {
    const disps = await (await fetch(API + '/dispositivos/')).json();
    if (disps.length > 0) {
      const d    = disps[0];
      const hero = document.querySelector('#screen-beneficiario .detail-hero');
      if (hero) {
        hero.querySelector('h2').textContent = d.nombre;
        hero.querySelector('p').textContent  = '📍 ' + (d.ubicacion || '');
      }
    }
  } catch(e) {}
}

// ═══ ADMIN ═══
async function loadAdmin() {
  try {
    const stats = await (await fetch(API + '/admin/stats', authGet())).json();
    setStatVal('admin', 0, stats.total_dispositivos);
    setStatVal('admin', 1, stats.total_usuarios);
    setStatVal('admin', 2, stats.total_prescriptores);
    setStatVal('admin', 3, stats.alertas_pendientes);
  } catch(e) { console.error(e); }

  try {
    const alertas   = await (await fetch(API + '/admin/alertas', authGet())).json();
    const alertPanel = document.querySelectorAll('#screen-admin .grid-2 .panel')[1];
    if (alertPanel && alertas.length > 0) {
      let html = '<div class="panel-head"><span class="panel-title">Alertas del sistema</span></div>';
      alertas.forEach(a => {
        html += `<div class="list-row"><div class="list-avatar rust" style="border-radius:8px;font-size:1rem">⚠️</div><div class="list-info"><div class="list-name">${a.mensaje}</div><div class="list-sub">${a.dispositivo}</div></div><span class="tag rust">Urgente</span></div>`;
      });
      setInnerHTML(alertPanel, html);
    }
  } catch(e) {}

  try {
    const disps = await (await fetch(API + '/admin/dispositivos', authGet())).json();
    const tbody = document.querySelector('#screen-admin table tbody');
    if (tbody) {
      tbody.innerHTML = disps.map(d => {
        const estado = d.activo ? '<span class="tag green">Activo</span>' : '<span class="tag rust">Inactivo</span>';
        return `<tr><td>${d.nombre}</td><td><span class="tag green">${d.tipo_servicio || '-'}</span></td><td style="color:var(--primary);font-weight:700">${d.num_beneficiarios}</td><td>${d.prescriptor || '-'}</td><td>${estado}</td><td><button class="btn btn-sm btn-outline">Editar</button></td></tr>`;
      }).join('');
    }
  } catch(e) {}

  try {
    const users  = await (await fetch(API + '/admin/usuarios', authGet())).json();
    const rolPanel = document.querySelectorAll('#screen-admin .grid-2 .panel')[0];
    if (rolPanel) {
      const disps2 = users.filter(u => u.rol === 'dispositivo').length;
      const prescs = users.filter(u => u.rol === 'prescriptor').length;
      const benefs = users.filter(u => u.rol === 'beneficiario').length;
      const total  = Math.max(disps2, prescs, benefs, 1);
      const fills  = rolPanel.querySelectorAll('.seed-fill');
      const nums   = rolPanel.querySelectorAll('div[style*="font-weight:700"]');
      if (fills[0]) fills[0].style.width = Math.round(disps2 / total * 100) + '%';
      if (fills[1]) fills[1].style.width = Math.round(prescs  / total * 100) + '%';
      if (fills[2]) fills[2].style.width = Math.round(benefs  / total * 100) + '%';
      if (nums[0])  nums[0].textContent  = disps2;
      if (nums[1])  nums[1].textContent  = prescs;
      if (nums[2])  nums[2].textContent  = benefs;
    }
  } catch(e) {}
}

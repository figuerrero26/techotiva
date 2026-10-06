/* ═══ MASCATE — CONFIGURACIÓN JS ═══ */
const API = window.location.origin;
MASCATE.guardAuth();

window.addEventListener('DOMContentLoaded', async () => {
  const { rol, nombre, email } = MASCATE;
  renderSidebar(nombre, email);

  set('cfg-avatar', ini(nombre));
  set('cfg-nombre', nombre || '—');
  set('cfg-sub',    ROL_LABELS[rol] ?? rol);
  set('cfg-email',  email || '—');
  set('cfg-acceso', new Date().toLocaleString('es-CO', { dateStyle:'short', timeStyle:'short' }));

  // Datos reales según rol
  if (rol === 'beneficiario') {
    try {
      const me = await (await fetch(API + '/beneficiarios/me', MASCATE.authGet())).json();
      set('cfg-nombre', me.nombre_apodo); set('cfg-avatar', ini(me.nombre_apodo));
      set('cfg-email',  me.email);
    } catch(e) {}
  } else if (rol === 'dispositivo') {
    try {
      const d = await (await fetch(API + '/dispositivos/me', MASCATE.authGet())).json();
      if (d) {
        set('cfg-nombre', d.nombre); set('cfg-avatar', ini(d.nombre));
        set('cfg-sub', campo(d.tipo_servicio, ROL_LABELS[rol]));
      }
    } catch(e) {}
  }

  // Estado sistema solo para admin
  if (rol !== "admin") {
    document.querySelector(".panel.span-2:last-of-type")?.remove();
  }

  // Apariencia oculta hasta implementar modo oscuro y compacto
  document.querySelectorAll(".panel").forEach(p => {
    if (p.querySelector(".panel-title")?.textContent.trim() === "Apariencia") {
      p.style.display = "none";
    }
  });

  // Health check — consume GET /health (endpoint público, sin auth)
  const elDb  = document.getElementById('status-db');
  const elSrv = document.getElementById('status-srv');
  try {
    const res    = await fetch(API + '/health');
    const health = await res.json();

    // API / servidor — soporta {api:'ok'} y {api:{status:'ok'}}
    if (elSrv) {
      const apiOk = (health.api === 'ok') || (health.api?.status === 'ok');
      elSrv.className   = 'tag ' + (apiOk ? 'green' : 'rust');
      elSrv.textContent = apiOk ? 'Estable' : 'Error';
    }

    // Base de datos — soporta {db:'ok'} y {database:{status:'ok'}}
    if (elDb) {
      const dbOk = (health.db === 'ok') || (health.database?.status === 'ok');
      elDb.className   = 'tag ' + (dbOk ? 'green' : 'rust');
      elDb.textContent = dbOk ? 'Activa' : 'Error';
    }
  } catch(e) {
    // Si el fetch falla del todo, el servidor no responde
    if (elSrv) { elSrv.className = 'tag rust'; elSrv.textContent = 'Sin respuesta'; }
    if (elDb)  { elDb.className  = 'tag rust'; elDb.textContent  = 'Desconocido'; }
  }

  // Cargar preferencias guardadas
  const prefs = JSON.parse(localStorage.getItem('mascate_prefs') || '{}');
  if (prefs.tema === 'oscuro') {
    document.getElementById('theme-oscuro').style.border = '2px solid var(--primary)';
    document.getElementById('theme-claro').style.border  = '2px solid var(--border)';
  }
  if (prefs.compacto) {
    document.body.classList.add('compact');
    const chk = document.getElementById('chk-compacto');
    if (chk) { chk.checked = true; if (chk.nextSibling) chk.nextSibling.textContent = ' On'; }
  }

  // Tema
  document.getElementById('theme-claro')?.addEventListener('click', () => {
    document.getElementById('theme-claro').style.border  = '2px solid var(--primary)';
    document.getElementById('theme-oscuro').style.border = '2px solid var(--border)';
    const p = JSON.parse(localStorage.getItem('mascate_prefs') || '{}');
    p.tema = 'claro'; localStorage.setItem('mascate_prefs', JSON.stringify(p));
  });
  document.getElementById('theme-oscuro')?.addEventListener('click', () => {
    document.getElementById('theme-oscuro').style.border = '2px solid var(--primary)';
    document.getElementById('theme-claro').style.border  = '2px solid var(--border)';
    const p = JSON.parse(localStorage.getItem('mascate_prefs') || '{}');
    p.tema = 'oscuro'; localStorage.setItem('mascate_prefs', JSON.stringify(p));
  });

  // Modo compacto
  document.getElementById('chk-compacto')?.addEventListener('change', e => {
    document.body.classList.toggle('compact', e.target.checked);
    e.target.nextSibling.textContent = e.target.checked ? ' On' : ' Off';
    const p = JSON.parse(localStorage.getItem('mascate_prefs') || '{}');
    p.compacto = e.target.checked; localStorage.setItem('mascate_prefs', JSON.stringify(p));
  });

  // Abrir modal contraseña
  document.getElementById('btn-pw')?.addEventListener('click', abrirModalPw);

  // Guardar preferencias
  document.getElementById('btn-guardar')?.addEventListener('click', () => {
    const btn = document.getElementById('btn-guardar');
    btn.textContent = '✓ Guardado';
    setTimeout(() => { btn.textContent = 'Guardar cambios'; }, 2000);
  });
});

// ── Modal contraseña ─────────────────────────────────────────────────────
function abrirModalPw() {
  const overlay = document.getElementById('modal-pw-overlay');
  if (overlay) { overlay.style.display = 'flex'; }
  document.getElementById('pw-actual')?.focus();
  document.getElementById('pw-error').style.display = 'none';
  ['pw-actual','pw-nueva','pw-confirmar'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = '';
  });
}

function cerrarModalPw() {
  const overlay = document.getElementById('modal-pw-overlay');
  if (overlay) overlay.style.display = 'none';
}

async function guardarPassword() {
  const actual     = document.getElementById('pw-actual')?.value;
  const nueva      = document.getElementById('pw-nueva')?.value;
  const confirmar  = document.getElementById('pw-confirmar')?.value;
  const errorEl    = document.getElementById('pw-error');
  const btn        = document.getElementById('btn-pw-guardar');

  function mostrarError(msg) {
    errorEl.textContent   = msg;
    errorEl.style.display = 'block';
  }

  errorEl.style.display = 'none';

  if (!actual || !nueva || !confirmar) {
    mostrarError('Por favor completa todos los campos.');
    return;
  }
  if (nueva.length < 8) {
    mostrarError('La nueva contraseña debe tener al menos 8 caracteres.');
    return;
  }
  if (!/[A-Z]/.test(nueva)) {
    mostrarError('La nueva contraseña debe tener al menos una letra mayúscula.');
    return;
  }
  if (!/[0-9]/.test(nueva)) {
    mostrarError('La nueva contraseña debe tener al menos un número.');
    return;
  }
  if (nueva !== confirmar) {
    mostrarError('Las contraseñas nuevas no coinciden.');
    return;
  }

  btn.textContent = 'Cambiando...';
  btn.disabled    = true;

  const { ok, data } = await MASCATE.cambiarPassword(actual, nueva);

  btn.textContent = 'Cambiar contraseña';
  btn.disabled    = false;

  if (ok) {
    cerrarModalPw();
    const toast = document.createElement('div');
    toast.textContent = '✓ Contraseña actualizada correctamente';
    toast.style.cssText = `position:fixed;bottom:1.5rem;right:1.5rem;z-index:2000;
      background:var(--primary);color:#fff;padding:0.75rem 1.25rem;
      border-radius:var(--radius-md);font-size:0.85rem;font-weight:600;
      box-shadow:0 4px 20px rgba(0,0,0,0.2)`;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
  } else {
    mostrarError(data.detail || 'Contraseña actual incorrecta.');
  }
}

// Cerrar modal al click fuera
document.getElementById('modal-pw-overlay')?.addEventListener('click', e => {
  if (e.target === document.getElementById('modal-pw-overlay')) cerrarModalPw();
});

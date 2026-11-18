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

  // Exportar toda la información (admin)
  document.getElementById('btn-exportar-todo')?.addEventListener('click', exportarTodo);

  // Verificación en dos pasos: solo admin
  if (rol === 'admin') cargar2FA();

  // Sesiones activas solo para admin
  if (rol === 'admin') {
    document.getElementById('row-sesiones').style.display = '';
    document.getElementById('btn-sesiones')?.addEventListener('click', abrirModalSesiones);
    cargarSesiones();
    setInterval(cargarSesiones, 30000);
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

// ── Exportar todo a Excel (admin) ────────────────────────────────────────
async function exportarTodo() {
  const btn = document.getElementById('btn-exportar-todo');
  const txt = btn.textContent;
  btn.textContent = 'Generando...'; btn.disabled = true;
  try {
    const res = await fetch(API + '/admin/exportar-todo', MASCATE.authGet());
    if (!res.ok) { alert('No se pudo generar la exportación.'); return; }
    const blob = await res.blob();
    const nombre = (res.headers.get('Content-Disposition') || '').match(/filename=([^;]+)/)?.[1]
      || 'cuidatutecho_export.xlsx';
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = nombre;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  } catch(e) {
    alert('Error de conexión al exportar.');
  } finally {
    btn.textContent = txt; btn.disabled = false;
  }
}

// ── Verificación en dos pasos (admin) ────────────────────────────────────
function pintar2FA(activo, habilitadoServidor) {
  const chk = document.getElementById('chk-2fa');
  chk.checked = activo;
  document.getElementById('lbl-2fa').textContent = activo ? 'Activada' : 'Desactivada';
  const sub = document.getElementById('sub-2fa');
  if (!habilitadoServidor) {
    chk.disabled = true;
    sub.textContent = 'Apagada en el servidor (ADMIN_2FA=false en el .env).';
  } else {
    sub.textContent = activo
      ? 'Al iniciar sesión se pide un código enviado a tu correo.'
      : 'Tu cuenta solo pide contraseña. Actívala para mayor seguridad.';
  }
}

async function cargar2FA() {
  try {
    const res = await fetch(API + '/auth/2fa', MASCATE.authGet());
    if (!res.ok) return;
    const d = await res.json();
    document.getElementById('row-2fa').style.display = '';
    pintar2FA(d.activo, d.habilitado_servidor);
    document.getElementById('chk-2fa').addEventListener('change', async e => {
      if (e.target.checked) {
        await guardar2FA(true);
      } else {
        e.target.checked = true;          // no se apaga hasta confirmar la contraseña
        document.getElementById('pw-2fa').value = '';
        document.getElementById('error-2fa').style.display = 'none';
        document.getElementById('modal-2fa-overlay').style.display = 'flex';
        document.getElementById('pw-2fa').focus();
      }
    });
  } catch(e) {}
}

async function guardar2FA(activo, password) {
  const res = await fetch(API + '/auth/2fa', {
    method: 'PUT', headers: MASCATE.authHeaders(),
    body: JSON.stringify({ activo, password: password || null }),
  });
  const d = await res.json().catch(() => ({}));
  if (res.ok) pintar2FA(d.activo, true);
  return { ok: res.ok, detail: d.detail };
}

async function confirmarDesactivar2FA() {
  const pw  = document.getElementById('pw-2fa').value;
  const err = document.getElementById('error-2fa');
  if (!pw) { err.textContent = 'Escribe tu contraseña.'; err.style.display = 'block'; return; }
  const r = await guardar2FA(false, pw);
  if (r.ok) cerrarModal2FA();
  else { err.textContent = r.detail || 'No se pudo desactivar.'; err.style.display = 'block'; }
}

function cerrarModal2FA() {
  document.getElementById('modal-2fa-overlay').style.display = 'none';
}

// ── Sesiones activas (admin) ─────────────────────────────────────────────
async function cargarSesiones() {
  let lista;
  try {
    const res = await fetch(API + '/admin/sesiones-activas', MASCATE.authGet());
    if (!res.ok) return;
    lista = await res.json();
  } catch(e) { return; }

  set('sesiones-count', lista.length);
  const cont = document.getElementById('sesiones-list');
  if (!cont) return;
  if (!lista.length) {
    cont.innerHTML = '<div style="color:var(--on-bg-muted);font-size:0.85rem">No hay nadie conectado en este momento.</div>';
    return;
  }
  const hace = s => s < 60 ? 'Activo ahora' : `Hace ${Math.floor(s / 60)} min`;
  cont.innerHTML = lista.map(u => `<div class="list-row">
      <div class="list-avatar" style="font-size:0.75rem">${ini(u.nombre)}</div>
      <div class="list-info">
        <div class="list-name">${u.nombre}${u.email === MASCATE.email ? ' <span style="font-weight:400;color:var(--on-bg-muted)">(tú)</span>' : ''}</div>
        <div class="list-sub">${ROL_LABELS[u.rol] ?? u.rol} · ${u.email}</div>
      </div>
      <span class="tag ${u.hace_segundos < 60 ? 'green' : 'mustard'}">${hace(u.hace_segundos)}</span>
    </div>`).join('');
}

function abrirModalSesiones() {
  const overlay = document.getElementById('modal-sesiones-overlay');
  if (overlay) overlay.style.display = 'flex';
  cargarSesiones();
}

function cerrarModalSesiones() {
  const overlay = document.getElementById('modal-sesiones-overlay');
  if (overlay) overlay.style.display = 'none';
}

// Cerrar modal al click fuera
document.getElementById('modal-pw-overlay')?.addEventListener('click', e => {
  if (e.target === document.getElementById('modal-pw-overlay')) cerrarModalPw();
});
document.getElementById('modal-sesiones-overlay')?.addEventListener('click', e => {
  if (e.target === document.getElementById('modal-sesiones-overlay')) cerrarModalSesiones();
});

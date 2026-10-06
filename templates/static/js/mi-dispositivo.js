/* ═══ MASCATE — MI DISPOSITIVO JS (rol: prescriptor) ═══ */
const API = window.location.origin;
MASCATE.guardAuth();

let _miPrescId   = null;
let _solId       = null;
let _miDispActual = null;

window.addEventListener('DOMContentLoaded', async () => {
  renderSidebar(MASCATE.nombre, MASCATE.email);

  try {
    const [me, disps] = await Promise.all([
      fetch(API + '/prescriptores/me', MASCATE.authGet()).then(r => r.json()),
      fetch(API + '/prescriptores/dispositivos-disponibles', MASCATE.authGet()).then(r => r.json()),
    ]);

    _miPrescId    = me.id;
    _solId        = me.solicitud_dispositivo_id;
    _miDispActual = me.dispositivo_id ?? null;

    renderEstado(me);
    renderAviso(me);
    renderDispositivos(disps, me);


  } catch(e) {
    console.error('Error:', e);
    document.getElementById('estado-contenido').innerHTML =
      '<div style="color:var(--error);padding:0.5rem">Error al cargar información.</div>';
  }
});

function renderEstado(me) {
  const el = document.getElementById('estado-contenido');
  if (!el) return;

  if (me.dispositivo_id && me.dispositivo_nombre) {
    el.innerHTML = `
      <div style="display:flex;align-items:center;gap:1rem;flex-wrap:wrap">
        <div class="list-avatar" style="background:var(--primary-dim);color:var(--primary);width:3rem;height:3rem;font-size:1.2rem;flex-shrink:0">🏘️</div>
        <div>
          <div style="font-weight:700;font-size:1rem">${me.dispositivo_nombre}</div>
          <div style="font-size:0.82rem;color:var(--on-bg-muted)">Eres parte activa de este dispositivo</div>
        </div>
        <span class="tag green" style="margin-left:auto">Activo</span>
      </div>
      ${me.solicitud_dispositivo_id ? `
        <div style="margin-top:0.75rem;padding:0.65rem 0.9rem;background:var(--secondary-dim);border-radius:var(--radius-sm);font-size:0.85rem">
          ⏳ También tienes una solicitud pendiente en <strong>${me.solicitud_dispositivo_nombre || 'otro dispositivo'}</strong>.
          <button class="btn btn-sm btn-outline" style="margin-left:0.75rem;color:var(--error);border-color:var(--error)" onclick="cancelarSolicitud()">Cancelar solicitud</button>
        </div>` : ''}`;
  } else if (me.solicitud_dispositivo_id && me.solicitud_dispositivo_nombre) {
    el.innerHTML = `
      <div style="padding:0.75rem;background:var(--secondary-dim);border-radius:var(--radius-sm)">
        <div style="font-weight:700;margin-bottom:0.25rem">⏳ Solicitud pendiente</div>
        <div style="font-size:0.85rem;color:var(--on-bg-muted)">Esperando aprobación de <strong>${me.solicitud_dispositivo_nombre}</strong>.</div>
        <div style="margin-top:0.65rem">
          <button class="btn btn-sm btn-outline" style="color:var(--error);border-color:var(--error)" onclick="cancelarSolicitud()">Cancelar solicitud</button>
        </div>
      </div>`;
  } else {
    el.innerHTML = `
      <div style="padding:0.75rem;background:var(--error-dim);border-radius:var(--radius-sm)">
        <div style="font-weight:700;color:var(--error);margin-bottom:0.25rem">Sin dispositivo asignado</div>
        <div style="font-size:0.85rem;color:var(--on-bg-muted)">Envía una solicitud a un dispositivo para empezar a trabajar.</div>
      </div>`;
  }
}

function renderAviso(me) {
  const aviso = document.getElementById('aviso-restriccion');
  const texto = document.getElementById('aviso-restriccion-texto');
  if (!aviso || !texto) return;

  if (me.dispositivo_id) {
    texto.innerHTML = `Actualmente perteneces a <strong>${me.dispositivo_nombre}</strong>. Si solicitas unirte a otro dispositivo y eres aprobadx, <strong>perderás el acceso a los beneficiarixs que tienes asignadxs actualmente</strong> en ese dispositivo.`;
  } else {
    texto.textContent = 'Si te unes a un dispositivo y luego solicitas cambiarte a otro, perderás el acceso a los beneficiarixs que tengas asignadxs en el dispositivo actual.';
  }
  aviso.style.display = 'block';
}

function renderDispositivos(disps, me) {
  const lista = document.getElementById('lista-dispositivos');
  if (!lista) return;
  set('count-disps', disps.length);

  if (!disps.length) {
    lista.innerHTML = '<div style="color:var(--on-bg-muted);font-size:0.85rem;padding:0.5rem">No hay dispositivos activos disponibles.</div>';
    return;
  }

  lista.innerHTML = disps.map(d => {
    const esActual    = d.id === me.dispositivo_id;
    const esSolicitud = d.id === me.solicitud_dispositivo_id;
    let accion = '';
    if (esActual) {
      accion = '<span class="tag green">Tu dispositivo actual</span>';
    } else if (esSolicitud) {
      accion = `<span class="tag mustard">Solicitud enviada</span>
        <button class="btn btn-sm btn-outline" style="color:var(--error);border-color:var(--error)" onclick="cancelarSolicitud()">Cancelar</button>`;
    } else {
      accion = `<button class="btn btn-sm btn-outline" onclick="solicitar(${d.id}, '${(d.nombre||'').replace(/'/g,"\\'")}')">Solicitar unirme</button>`;
    }

    return `<div class="list-row" style="padding:0.75rem 0;border-bottom:1px solid var(--border)">
      <div class="list-avatar" style="background:var(--primary-dim);color:var(--primary);flex-shrink:0">🏘️</div>
      <div class="list-info">
        <div class="list-name">${campo(d.nombre)}</div>
        <div class="list-sub">${campo(d.tipo_servicio)} · ${campo(d.ubicacion)}</div>
      </div>
      <div style="display:flex;align-items:center;gap:0.5rem;flex-shrink:0">${accion}</div>
    </div>`;
  }).join('');
}

async function solicitar(dispId, nombre) {
  const advertencia = _miDispActual
    ? `\n\nRecuerda: solo puedes estar asociadx a un dispositivo a la vez.`
    : '';
  if (!confirm(`¿Enviar solicitud de unión a "${nombre}"?${advertencia}`)) return;
  try {
    const res = await fetch(API + '/prescriptores/solicitar-dispositivo/' + dispId, {
      method: 'POST', headers: MASCATE.authHeaders(),
    });
    const d = await res.json();
    if (res.ok) {
      _solId = dispId;
      window.location.reload();
    } else {
      alert('Error: ' + (d.detail || 'No se pudo enviar la solicitud.'));
    }
  } catch(e) { console.error(e); alert('Error de conexión.'); }
}

async function cancelarSolicitud() {
  if (!confirm('¿Cancelar la solicitud pendiente?')) return;
  try {
    const res = await fetch(API + '/prescriptores/cancelar-solicitud', {
      method: 'DELETE', headers: MASCATE.authHeaders(),
    });
    if (res.ok) { window.location.reload(); }
    else { const d = await res.json(); alert('Error: ' + (d.detail||'No se pudo cancelar.')); }
  } catch(e) { console.error(e); alert('Error de conexión.'); }
}

/* ═══ MASCATE — REPORTAR INFO JS ═══ */
const API = window.location.origin;
MASCATE.guardAuth();

let asignadosData = [];

window.addEventListener('DOMContentLoaded', async () => {
  renderSidebar(MASCATE.nombre, MASCATE.email);
  await cargarDatos();
});

async function cargarDatos() {
  try {
    // Asignados
    asignadosData = await (await fetch(API + '/prescriptores/mis-asignados', MASCATE.authGet())).json();
    const sel = document.getElementById('form-persona');
    if (sel) {
      sel.innerHTML = asignadosData.length
        ? asignadosData.map(a => `<option value="${a.id}">${a.nombre_apodo}</option>`).join('')
        : '<option value="">Sin personas asignadas</option>';
    }

    // Tabla de estado
    const tabla = document.getElementById('tabla-asignados');
    if (tabla) {
      if (!asignadosData.length) {
        tabla.innerHTML = '<div style="color:var(--on-bg-muted);font-size:0.85rem;padding:0.5rem">Sin personas asignadas.</div>';
      } else {
        tabla.innerHTML = `<div style="overflow-x:auto"><table>
          <thead><tr><th>Persona</th><th>Último seguimiento</th><th>Días sin sesión</th><th>Estado</th></tr></thead>
          <tbody>${asignadosData.map(a => {
            const tagClass = a.estado==='urgente'?'rust':a.estado==='revisar'?'mustard':'green';
            const label    = a.estado==='urgente'?'Urgente':a.estado==='revisar'?'Revisar':'Al día';
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
  } catch(e) { console.error('Error cargando asignados:', e); }

  try {
    // Registros recientes
    const segs = await (await fetch(API + '/prescriptores/seguimientos', MASCATE.authGet())).json();
    set('count-registros', segs.length);
    const lista = document.getElementById('lista-registros');
    if (lista) {
      if (!segs.length) {
        lista.innerHTML = '<div style="color:var(--on-bg-muted);font-size:0.85rem;padding:0.5rem">Sin registros aún.</div>';
      } else {
        lista.innerHTML = segs.slice(0, 8).map(s => {
          const fecha = new Date(s.fecha).toLocaleDateString('es-CO');
          return `<div class="list-row" style="padding:0.6rem 0;border-bottom:1px solid var(--border)">
            <div class="list-avatar" style="flex-shrink:0;font-size:0.75rem">${(s.nombre_beneficiario||'??').substring(0,2).toUpperCase()}</div>
            <div class="list-info">
              <div class="list-name" style="font-size:0.85rem">${campo(s.nombre_beneficiario, '—')}</div>
              <div class="list-sub">${campo(s.tipo_registro)} · ${fecha}</div>
              ${s.observaciones ? `<div style="font-size:0.78rem;color:var(--on-bg-muted);margin-top:0.2rem">${s.observaciones.substring(0,80)}${s.observaciones.length>80?'…':''}</div>` : ''}
            </div>
            <button class="btn btn-sm btn-outline"
              style="flex-shrink:0;color:var(--error);border-color:var(--error)"
              onclick="eliminarRegistro(${s.id})">🗑</button>
          </div>`;
        }).join('');
      }
    }
  } catch(e) {}
}

async function guardarRegistro() {
  const errorEl = document.getElementById('form-error');
  const btn     = document.getElementById('btn-guardar-registro');
  errorEl.style.display = 'none';

  const personaId    = document.getElementById('form-persona')?.value;
  const tipoRegistro = document.getElementById('form-tipo')?.value;
  const observaciones = document.getElementById('form-observaciones')?.value.trim();

  if (!personaId) {
    errorEl.textContent = 'Selecciona una persona.';
    errorEl.style.display = 'block'; return;
  }

  btn.textContent = 'Guardando...'; btn.disabled = true;

  try {
    const res = await fetch(API + '/prescriptores/seguimientos', {
      method: 'POST',
      headers: MASCATE.authHeaders(),
      body: JSON.stringify({
        beneficiario_id: parseInt(personaId),
        tipo_registro:   tipoRegistro,
        observaciones:   observaciones || null,
      }),
    });
    const data = await res.json();
    if (res.ok) {
      limpiarFormulario();
      await cargarDatos();
      // Toast
      const t = document.createElement('div');
      t.textContent = '✓ Registro guardado correctamente';
      t.style.cssText = `position:fixed;bottom:1.5rem;right:1.5rem;z-index:2000;
        background:var(--primary);color:#fff;padding:0.75rem 1.25rem;
        border-radius:var(--radius-md);font-size:0.85rem;font-weight:600;
        box-shadow:0 4px 20px rgba(0,0,0,0.2)`;
      document.body.appendChild(t);
      setTimeout(() => t.remove(), 3000);
    } else {
      errorEl.textContent = data.detail || 'Error al guardar.';
      errorEl.style.display = 'block';
    }
  } catch(e) {
    errorEl.textContent = 'Error de conexión.';
    errorEl.style.display = 'block';
  }
  btn.textContent = 'Guardar registro'; btn.disabled = false;
}

function limpiarFormulario() {
  const obs = document.getElementById('form-observaciones');
  if (obs) obs.value = '';
  document.getElementById('form-error').style.display = 'none';
}

// ── Eliminar registro ────────────────────────────────────────────────────
let _delId = null;

function eliminarRegistro(id) {
  _delId = id;
  document.getElementById('modal-del-overlay').style.display = 'flex';
}

function cerrarModalDel() {
  _delId = null;
  document.getElementById('modal-del-overlay').style.display = 'none';
}

async function confirmarEliminar() {
  if (!_delId) return;
  const btn = document.getElementById('btn-confirmar-del');
  btn.textContent = 'Eliminando...';
  btn.disabled = true;

  try {
    const res = await fetch(API + '/prescriptores/seguimientos/' + _delId, {
      method: 'DELETE',
      headers: MASCATE.authHeaders(),
    });
    if (res.ok || res.status === 204) {
      cerrarModalDel();
      await cargarDatos();
      const t = document.createElement('div');
      t.textContent = '✓ Registro eliminado';
      t.style.cssText = 'position:fixed;bottom:1.5rem;right:1.5rem;z-index:2000;background:var(--error);color:#fff;padding:0.75rem 1.25rem;border-radius:var(--radius-md);font-size:0.85rem;font-weight:600;box-shadow:0 4px 20px rgba(0,0,0,0.2)';
      document.body.appendChild(t);
      setTimeout(() => t.remove(), 3000);
    } else {
      const d = await res.json().catch(() => ({}));
      cerrarModalDel();
      // Mostrar error en el form-error
      const errorEl = document.getElementById('form-error');
      errorEl.textContent = d.detail || 'No se pudo eliminar.';
      errorEl.style.display = 'block';
    }
  } catch(e) {
    console.error(e);
    cerrarModalDel();
  }

  btn.textContent = 'Sí, eliminar';
  btn.disabled = false;
}

document.getElementById('modal-del-overlay')?.addEventListener('click', e => {
  if (e.target === document.getElementById('modal-del-overlay')) cerrarModalDel();
});

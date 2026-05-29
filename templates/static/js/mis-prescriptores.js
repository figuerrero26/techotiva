/* ═══ MASCATE — MIS PRESCRIPTORES JS ═══ */
const API = window.location.origin;
MASCATE.guardAuth();

let dispId = null;

window.addEventListener('DOMContentLoaded', async () => {
  renderSidebar(MASCATE.nombre, MASCATE.email);

  try {
    // Obtener el dispositivo propio
    const disp = await (await fetch(API + '/dispositivos/me', MASCATE.authGet())).json();
    if (!disp || !disp.id) {
      document.getElementById('lista-prescriptores').innerHTML =
        '<div style="color:var(--error);padding:0.5rem">No se encontró el dispositivo.</div>';
      return;
    }
    dispId = disp.id;

    // Cargar pendientes y activos en paralelo
    const [pendientes, beneficiarios] = await Promise.all([
      fetch(API + '/dispositivos/' + dispId + '/prescriptores/pendientes', MASCATE.authGet()).then(r => r.json()),
      fetch(API + '/dispositivos/' + dispId + '/beneficiarios', MASCATE.authGet()).then(r => r.json()),
    ]);

    // Para prescriptores activos usamos el endpoint de admin/usuarios filtrando
    // por ahora usamos los que no están en pendientes
    const todosUsers = await (await fetch(API + '/admin/usuarios', MASCATE.authGet())).json()
      .catch(() => []);
    const prescActivos = todosUsers.filter(u =>
      u.rol === 'prescriptor' && u.status === 'activo'
    );

    set('stat-total',     prescActivos.length + pendientes.length);
    set('stat-activos',   prescActivos.length);
    set('stat-pendientes', pendientes.length);

    // Panel pendientes
    if (pendientes.length > 0) {
      document.getElementById('panel-pendientes').style.display = 'block';
      set('count-pendientes', pendientes.length);
      document.getElementById('lista-pendientes').innerHTML = pendientes.map(p => `
        <div class="list-row" style="padding:0.6rem 0;border-bottom:1px solid var(--border)">
          <div class="list-avatar" style="flex-shrink:0">${(p.nombre_completo||'??').substring(0,2).toUpperCase()}</div>
          <div class="list-info">
            <div class="list-name">${campo(p.nombre_completo)}</div>
            <div class="list-sub">${campo(p.perfil_disciplina)}</div>
          </div>
          <div style="display:flex;gap:0.4rem;flex-shrink:0">
            <button class="btn btn-sm btn-green" onclick="aprobar(${p.id})">✓ Aprobar</button>
          </div>
        </div>`).join('');
    }

    // Lista prescriptores activos
    const lista = document.getElementById('lista-prescriptores');
    if (!prescActivos.length) {
      lista.innerHTML = '<div style="color:var(--on-bg-muted);font-size:0.85rem;padding:0.5rem">Sin prescriptxres activos aún.</div>';
      return;
    }
    lista.innerHTML = prescActivos.map(u => `
      <div class="list-row">
        <div class="list-avatar" style="background:var(--primary-dim);color:var(--primary);flex-shrink:0">
          ${(u.nombre||u.email).substring(0,2).toUpperCase()}
        </div>
        <div class="list-info">
          <div class="list-name">${campo(u.nombre, u.email)}</div>
          <div class="list-sub">${u.email}</div>
        </div>
        <span class="tag green">Activo</span>
      </div>`).join('');

  } catch(e) {
    console.error('Error:', e);
    document.getElementById('lista-prescriptores').innerHTML =
      '<div style="color:var(--error);padding:0.5rem">Error al cargar prescriptxres.</div>';
  }
});

async function aprobar(prescId) {
  if (!dispId) return;
  try {
    const res = await fetch(
      API + '/dispositivos/' + dispId + '/prescriptores/' + prescId + '/aprobar',
      { method: 'POST', headers: MASCATE.authHeaders() }
    );
    if (res.ok) {
      window.location.reload();
    } else {
      const d = await res.json();
      alert('Error: ' + (d.detail || 'No se pudo aprobar.'));
    }
  } catch(e) { console.error(e); }
}

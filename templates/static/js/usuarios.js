/* ═══ MASCATE — USUARIOS JS ═══ */

const API    = 'http://127.0.0.1:8080';
const token  = localStorage.getItem('mascate_token');
const rol    = localStorage.getItem('mascate_rol');
const nombre = localStorage.getItem('mascate_nombre');

if (!token) window.location.href = '/login';

function authGet() { return { headers: { 'Authorization': 'Bearer ' + token } }; }
function authHeaders() { return { 'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json' }; }

// Logout
document.querySelectorAll('.sb-user').forEach(u => {
  const btn = document.createElement('button');
  btn.textContent = 'Cerrar sesion';
  btn.className = 'btn btn-sm btn-outline';
  btn.style.cssText = 'margin-top:0.5rem;width:100%;font-size:0.72rem;';
  btn.onclick = () => {
    ['mascate_token','mascate_rol','mascate_nombre'].forEach(k => localStorage.removeItem(k));
    window.location.href = '/login';
  };
  u.after(btn);
});

// Nombre en sidebar
const sbName = document.querySelector('.sb-uname');
if (sbName && nombre) sbName.textContent = nombre;

window.addEventListener('DOMContentLoaded', async () => {
  try {
    const users = await (await fetch(API + '/admin/usuarios', authGet())).json();

    const dispositivos  = users.filter(u => u.rol === 'dispositivo');
    const prescriptores = users.filter(u => u.rol === 'prescriptor');
    const beneficiarios = users.filter(u => u.rol === 'beneficiario');

    // Stats
    const vals = document.querySelectorAll('.stat-val');
    if (vals[0]) vals[0].textContent = users.length;
    if (vals[1]) vals[1].textContent = beneficiarios.length;
    if (vals[2]) vals[2].textContent = prescriptores.length;
    if (vals[3]) vals[3].textContent = dispositivos.length;

    // Tabla
    const tbody = document.querySelector('table tbody');
    if (tbody) {
      tbody.innerHTML = users.map(u => {
        const rolTag = u.rol === 'beneficiario'
          ? '<span class="tag mustard">Beneficiario</span>'
          : u.rol === 'prescriptor'
          ? '<span class="tag blue">Prescriptor</span>'
          : '<span class="tag purple">Dispositivo</span>';
        const ini = (u.nombre || u.email || '??').substring(0,2).toUpperCase();
        return `<tr>
          <td><div style="display:flex;align-items:center;gap:0.6rem">
            <div class="list-avatar" style="width:1.8rem;height:1.8rem;font-size:0.7rem;flex-shrink:0">${ini}</div>
            ${u.nombre || u.email}
          </div></td>
          <td>${rolTag}</td>
          <td>${u.edad ?? '—'}</td>
          <td>${u.localidad ?? '—'}</td>
          <td><span class="tag green">Activo</span></td>
          <td>${u.actividad ?? '—'}</td>
          <td>${u.telefono ?? '—'}</td>
          <td><button class="btn btn-sm btn-outline">Editar</button></td>
        </tr>`;
      }).join('');
    }

    // Filtro por búsqueda
    const searchInput = document.querySelector('input[type="text"]');
    const roleSelect  = document.querySelector('select');
    function filtrar() {
      const q    = searchInput?.value.toLowerCase() ?? '';
      const rFil = roleSelect?.value ?? 'Todos';
      const rows = tbody.querySelectorAll('tr');
      rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        const matchQ = text.includes(q);
        const matchR = rFil === 'Todos' || text.includes(rFil.toLowerCase().slice(0,-1)); // quita la 's' final
        row.style.display = matchQ && matchR ? '' : 'none';
      });
    }
    searchInput?.addEventListener('input', filtrar);
    document.querySelector('.btn-outline')?.addEventListener('click', filtrar);

  } catch(e) {
    console.error('Error cargando usuarios:', e);
  }
});

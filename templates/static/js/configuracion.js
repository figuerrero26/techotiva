/* ═══ MASCATE — CONFIGURACIÓN JS ═══ */

const API    = 'http://127.0.0.1:8080';
const token  = localStorage.getItem('mascate_token');
const rol    = localStorage.getItem('mascate_rol');
const nombre = localStorage.getItem('mascate_nombre');

if (!token) window.location.href = '/login';

function authGet() { return { headers: { 'Authorization': 'Bearer ' + token } }; }

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

window.addEventListener('DOMContentLoaded', async () => {
  // Nombre en sidebar y perfil
  const sbName  = document.querySelector('.sb-uname');
  const sbEmail = document.querySelector('.sb-uemail');
  if (sbName && nombre) sbName.textContent = nombre;

  // Iniciales en avatares
  const ini = (nombre || 'AD').substring(0,2).toUpperCase();
  document.querySelectorAll('.list-avatar, .sb-avatar').forEach(el => {
    if (['LA','LM','AD'].includes(el.textContent.trim())) el.textContent = ini;
  });

  // Nombre en la card de perfil
  const heroH2 = document.querySelector('h2');
  if (heroH2 && nombre) heroH2.textContent = nombre;

  // Rol label
  const labels = { admin:'Administrador principal', dispositivo:'Dispositivo CBC', prescriptor:'Prescriptxr', beneficiario:'Beneficiarix' };
  const rolSpan = document.querySelector('h2 + span');
  if (rolSpan) rolSpan.textContent = labels[rol] ?? rol;

  // Estado del sistema: intentar ping a /admin/stats
  if (rol === 'admin') {
    try {
      await fetch(API + '/admin/stats', authGet());
      // Si llega aquí, el servidor responde
      const statusItems = document.querySelectorAll('.contact-val');
      // Los valores de estado ya están en el HTML como Activa/Estable/Pendiente
    } catch(e) {
      // Servidor no responde, marcar en rojo
      const items = document.querySelectorAll('.tag.green');
      items.forEach(t => { t.className = 'tag rust'; t.textContent = 'Error'; });
    }
  }

  // Toggle de tema (claro / oscuro) — solo UI local
  const themeBoxes = document.querySelectorAll('[style*="border:2px solid"]');
  themeBoxes.forEach((box, i) => {
    box.style.cursor = 'pointer';
    box.addEventListener('click', () => {
      themeBoxes.forEach(b => b.style.border = '2px solid var(--border)');
      box.style.border = '2px solid var(--primary)';
      // aquí podrías aplicar data-theme al <html> si tienes modo oscuro implementado
    });
  });

  // Modo compacto toggle
  const compactoCheck = document.querySelector('input[type="checkbox"]:last-of-type');
  if (compactoCheck) {
    compactoCheck.addEventListener('change', () => {
      document.body.classList.toggle('compact', compactoCheck.checked);
    });
  }

  // Botón guardar — por ahora solo feedback visual
  const saveBtn = document.querySelector('.btn-green');
  if (saveBtn) {
    saveBtn.addEventListener('click', () => {
      saveBtn.textContent = '✓ Guardado';
      setTimeout(() => { saveBtn.textContent = 'Guardar cambios'; }, 2000);
    });
  }
});

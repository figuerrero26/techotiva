/* ═══ MASCATE — ACTIVIDADES JS ═══ */
const API = window.location.origin;
MASCATE.guardAuth();

window.addEventListener('DOMContentLoaded', async () => {
  const { rol, nombre, email } = MASCATE;
  renderSidebar(nombre, email);
  await initNotifBtn();

  // Ocultar btn nueva actividad si no tiene permiso
  const btnNueva = document.getElementById('btn-nueva');
  if (rol === 'beneficiario') {
    btnNueva?.remove();
  } else {
    btnNueva?.addEventListener('click', () => {
      // Por ahora redirige al dashboard donde está el form
      // Cuando exista modal propio se actualiza aquí
      window.location.href = '/dashboard';
    });
  }

  // "Ver todas →" en tabla
  document.querySelector('.panel-action')?.addEventListener('click', () => {
    // scroll a la tabla
    document.querySelector('table')?.scrollIntoView({ behavior:'smooth' });
  });

  try {
    let acts = [];
    if (rol === 'beneficiario') {
      acts = await (await fetch(API + '/beneficiarios/mis-actividades', MASCATE.authGet())).json();
    } else if (rol === 'dispositivo') {
      const disps = await (await fetch(API + '/dispositivos/', MASCATE.authGet())).json();
      if (disps.length) acts = await (await fetch(API + '/actividades/?dispositivo_id=' + disps[0].id)).json();
    } else {
      acts = await (await fetch(API + '/actividades/')).json();
    }

    const tipos   = new Set(acts.map(a => a.tipo)).size;
    const lugares = new Set(acts.map(a => a.lugar)).size;
    set('stat-total',   acts.length);
    set('stat-tipos',   tipos);
    set('stat-lugares', lugares);

    if (rol === 'admin') {
      try {
        const disps = await (await fetch(API + '/admin/dispositivos', MASCATE.authGet())).json();
        set('stat-dispositivos', disps.length);
      } catch(e) {}
    } else {
      set('stat-dispositivos', '—');
    }

    renderActCards('acts-cards', acts);
    renderActTabla('acts-tbody', acts);

  } catch(e) {
    console.error('Error cargando actividades:', e);
    const g = document.getElementById('acts-cards');
    if (g) g.innerHTML = '<div style="color:var(--error);padding:1rem">Error al cargar actividades.</div>';
  }
});

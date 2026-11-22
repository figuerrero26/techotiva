/* ═══ MASCATE — Adaptación a celulares y tabletas ═══
   - Agrega el botón ☰ que abre y cierra el menú lateral en pantallas pequeñas.
   - Pone las tablas dentro de un contenedor con desplazamiento horizontal.
   En escritorio no cambia nada: el botón y el fondo están ocultos por CSS
   y las tablas solo se envuelven en tabletas y celulares (hasta 1024 px).
*/
(function () {
  const PEQUENA = window.matchMedia('(max-width: 768px)');     // menú plegable
  const TABLETA = window.matchMedia('(max-width: 1024px)');    // tablas con desplazamiento

  function cerrar(screen) {
    screen.classList.remove('menu-abierto');
    screen.querySelector('.menu-movil-btn')?.setAttribute('aria-expanded', 'false');
  }

  function prepararMenus() {
    document.querySelectorAll('.screen').forEach(screen => {
      const topbar = screen.querySelector('.topbar');
      const sidebar = screen.querySelector('.sidebar');
      if (!topbar || !sidebar || topbar.querySelector('.menu-movil-btn')) return;

      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'menu-movil-btn';
      btn.setAttribute('aria-label', 'Abrir menú');
      btn.setAttribute('aria-expanded', 'false');
      btn.textContent = '☰';
      topbar.insertBefore(btn, topbar.firstChild);

      const fondo = document.createElement('div');
      fondo.className = 'menu-movil-fondo';
      screen.appendChild(fondo);

      btn.addEventListener('click', () => {
        const abierto = screen.classList.toggle('menu-abierto');
        btn.setAttribute('aria-expanded', abierto ? 'true' : 'false');
      });
      fondo.addEventListener('click', () => cerrar(screen));
      // Al elegir una opción del menú, se cierra
      sidebar.addEventListener('click', e => { if (e.target.closest('a, .sb-item, button')) cerrar(screen); });
    });
  }

  function tieneScrollPropio(el) {
    for (let p = el.parentElement; p && p !== document.body; p = p.parentElement) {
      const ox = getComputedStyle(p).overflowX;
      if (ox === 'auto' || ox === 'scroll') return true;
    }
    return false;
  }

  function envolverTablas() {
    if (!TABLETA.matches) return;
    document.querySelectorAll('table').forEach(t => {
      if (t.parentElement?.classList.contains('tabla-movil')) return;
      const columnas = t.querySelector('tr')?.children.length || 0;
      if (columnas >= 4) t.classList.add('tabla-ancha');
      if (tieneScrollPropio(t)) return;            // ya está dentro de un contenedor con scroll
      const caja = document.createElement('div');
      caja.className = 'tabla-movil';
      t.parentNode.insertBefore(caja, t);
      caja.appendChild(t);
    });
  }

  function iniciar() {
    prepararMenus();
    envolverTablas();
    // Las páginas crean tablas y contenido después de cargar datos
    let pendiente;
    new MutationObserver(() => {
      clearTimeout(pendiente);
      pendiente = setTimeout(() => { prepararMenus(); envolverTablas(); }, 120);
    }).observe(document.body, { childList: true, subtree: true });
    TABLETA.addEventListener?.('change', envolverTablas);
    PEQUENA.addEventListener?.('change', () => {
      if (!PEQUENA.matches) document.querySelectorAll('.screen.menu-abierto').forEach(cerrar);
    });
    document.addEventListener('keydown', e => {
      if (e.key === 'Escape') document.querySelectorAll('.screen.menu-abierto').forEach(cerrar);
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', iniciar);
  else iniciar();
})();

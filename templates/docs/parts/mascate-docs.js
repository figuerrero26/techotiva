/* ═══ MASCATE DOCS — JS ═══ */

// ── Navegación ──
function nav(el, id) {
  document.querySelectorAll('.sb-link').forEach(l => l.classList.remove('active'));
  el.classList.add('active');
  const target = document.getElementById(id);
  if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// ── Auto-highlight activo en scroll ──
const sections = document.querySelectorAll('.section[id]');
const navLinks  = document.querySelectorAll('.sb-link');

const observer = new IntersectionObserver(entries => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      const id = entry.target.id;
      navLinks.forEach(l => {
        const match = l.getAttribute('onclick')?.includes("'" + id + "'");
        l.classList.toggle('active', !!match);
      });
    }
  });
}, { rootMargin: '-20% 0px -70% 0px' });

sections.forEach(s => observer.observe(s));

// ── Estilos para componentes nuevos (ecosistema + backend placeholder) ──
// Se inyectan aquí para que el CSS de la doc no tenga que tocarlos
// y el equipo pueda ajustar colores sin conflicto con sus tokens.
const docStyles = `
  /* ── Ecosistema ── */
  .ecosystem-grid {
    display: grid;
    grid-template-columns: 1fr auto 1fr auto 1fr;
    gap: 0.75rem;
    align-items: center;
    margin: 1.25rem 0;
  }
  .eco-arrow {
    font-size: 1.2rem;
    color: var(--on-bg-muted);
    text-align: center;
    opacity: 0.6;
  }
  .eco-card {
    border-radius: var(--radius-md);
    padding: 1rem 1.1rem;
    border: 1px solid var(--outline-variant);
    background: var(--surface-mid, #052e18);
  }
  .eco-card.eco-ours {
    border-color: var(--primary, #f6be39);
    box-shadow: 0 0 0 1px rgba(246,190,57,0.08), 0 8px 24px rgba(0,0,0,0.15);
  }
  .eco-card.eco-external {
    opacity: 0.75;
  }
  .eco-card.eco-backend {
    opacity: 0.75;
  }
  .eco-header {
    display: flex;
    align-items: flex-start;
    gap: 0.6rem;
    margin-bottom: 0.6rem;
  }
  .eco-icon {
    font-size: 1.3rem;
    flex-shrink: 0;
  }
  .eco-name {
    font-family: 'Epilogue', sans-serif;
    font-weight: 700;
    font-size: 0.88rem;
    color: var(--on-surface, #e8f5ec);
    line-height: 1.2;
  }
  .eco-team {
    font-size: 0.68rem;
    color: var(--on-bg-muted, #5f9e78);
    margin-top: 0.15rem;
  }
  .eco-header .badge {
    margin-left: auto;
    flex-shrink: 0;
  }
  .eco-desc {
    font-size: 0.78rem;
    color: var(--on-bg-muted, #5f9e78);
    line-height: 1.55;
    margin-bottom: 0.65rem;
  }
  .eco-footer {
    border-top: 1px solid var(--outline-variant, rgba(149,212,179,0.1));
    padding-top: 0.55rem;
  }
  .eco-fact {
    font-size: 0.71rem;
    color: var(--on-bg-muted, #5f9e78);
  }
  .badge-ext {
    background: var(--surface-high, #0a3d20);
    color: var(--on-bg-muted, #5f9e78);
    border: 1px solid var(--outline-variant);
    font-size: 0.6rem;
    font-weight: 700;
    padding: 0.18rem 0.55rem;
    border-radius: 999px;
    text-transform: uppercase;
    letter-spacing: 0.07em;
  }
  @media (max-width: 720px) {
    .ecosystem-grid {
      grid-template-columns: 1fr;
    }
    .eco-arrow {
      transform: rotate(90deg);
      justify-self: center;
    }
  }

  /* ── Backend placeholder ── */
  .placeholder-backend {
    border: 2px dashed var(--outline-variant, rgba(149,212,179,0.15));
    border-radius: var(--radius-lg, 20px);
    padding: 2.5rem 2rem;
    text-align: center;
    margin-top: 1.5rem;
    background: var(--surface-low, #001f10);
  }
  .ph-icon {
    font-size: 2.5rem;
    margin-bottom: 0.75rem;
    opacity: 0.5;
  }
  .ph-title {
    font-family: 'Epilogue', sans-serif;
    font-weight: 700;
    font-size: 1rem;
    color: var(--on-surface, #e8f5ec);
    margin-bottom: 0.4rem;
    opacity: 0.6;
  }
  .ph-desc {
    font-size: 0.82rem;
    color: var(--on-bg-muted, #5f9e78);
    max-width: 420px;
    margin: 0 auto;
    line-height: 1.6;
    opacity: 0.7;
  }
`;

const styleEl = document.createElement('style');
styleEl.textContent = docStyles;
document.head.appendChild(styleEl);

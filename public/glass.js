/* Appearance preference is independent of material library data. */
(() => {
  const root = document.documentElement;
  let appearance = 'light';
  try { appearance = localStorage.getItem('surface-glass-appearance') || 'light'; } catch {}
  root.dataset.appearance = appearance === 'dark' ? 'dark' : 'light';
  const button = document.createElement('button');
  button.className = 'icon-button appearance-button';
  button.id = 'appearance-toggle';
  function sync() {
    const dark = root.dataset.appearance === 'dark';
    button.title = dark ? '切换浅色液态玻璃' : '切换深色液态玻璃';
    button.setAttribute('aria-label', button.title);
    button.setAttribute('aria-pressed', String(dark));
    button.innerHTML = dark
      ? '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5"/></svg>'
      : '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 15.2A8.7 8.7 0 0 1 8.8 4 8.7 8.7 0 1 0 20 15.2Z"/></svg>';
  }
  button.onclick = () => {
    root.dataset.appearance = root.dataset.appearance === 'dark' ? 'light' : 'dark';
    try { localStorage.setItem('surface-glass-appearance', root.dataset.appearance); } catch {}
    sync();
  };
  sync();
  document.querySelector('.topbar-right').prepend(button);
  const toolbar = document.querySelector('.toolbar');
  let frame = 0;
  toolbar.addEventListener('pointermove', event => {
    if (matchMedia('(prefers-reduced-motion: reduce)').matches || frame) return;
    frame = requestAnimationFrame(() => {
      const box = toolbar.getBoundingClientRect();
      toolbar.style.setProperty('--shine-x', `${event.clientX - box.left}px`);
      toolbar.style.setProperty('--shine-y', `${event.clientY - box.top}px`);
      frame = 0;
    });
  }, { passive: true });
  toolbar.addEventListener('pointerleave', () => {
    cancelAnimationFrame(frame); frame = 0;
    toolbar.style.removeProperty('--shine-x'); toolbar.style.removeProperty('--shine-y');
  });
})();

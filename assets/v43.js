(() => {
  'use strict';
  const header = document.querySelector('[data-v43-header]');
  if (!header) return;
  const syncHeader = () => header.classList.toggle('scrolled', window.scrollY > 36);
  syncHeader();
  window.addEventListener('scroll', syncHeader, {passive:true});
})();

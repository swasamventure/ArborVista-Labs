(() => {
  'use strict';
  const menu=document.querySelector('.menu');
  const links=document.querySelector('.links');
  if(menu&&links){
    menu.setAttribute('aria-expanded','false');
    menu.addEventListener('click',()=>{
      const open=links.classList.toggle('open');
      menu.setAttribute('aria-expanded',String(open));
    });
    links.querySelectorAll('a').forEach(link=>link.addEventListener('click',()=>{
      links.classList.remove('open');
      menu.setAttribute('aria-expanded','false');
    }));
    document.addEventListener('keydown',event=>{
      if(event.key==='Escape'&&links.classList.contains('open')){
        links.classList.remove('open');
        menu.setAttribute('aria-expanded','false');
        menu.focus();
      }
    });
  }
  document.querySelectorAll('[data-year]').forEach(element=>{element.textContent='2026';});
})();

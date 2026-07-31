(() => {
  'use strict';
  const header = document.querySelector('[data-v43-header]');
  if (header) {
    const syncHeader = () => header.classList.toggle('scrolled', window.scrollY > 36);
    syncHeader();
    window.addEventListener('scroll', syncHeader, {passive:true});
  }

  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const emit = (name, detail={}) => window.dispatchEvent(new CustomEvent('arbor:analytics', {detail:{name,...detail}}));

  document.querySelectorAll('[data-v43-rotator]').forEach((rotator, rotatorIndex) => {
    const slides = [...rotator.querySelectorAll('[data-rotator-slide]')];
    const dots = [...rotator.querySelectorAll('[data-rotator-dot]')];
    if (slides.length < 2) return;
    const delay = Math.max(3000, Number(rotator.dataset.delay) || 3000);
    let index = Math.max(0, slides.findIndex((slide) => slide.classList.contains('is-active')));
    let timer = null;
    let userPaused = reducedMotion;
    let interactionPaused = false;
    let touchStartX = null;

    rotator.setAttribute('role','region');
    rotator.setAttribute('aria-roledescription','carousel');
    const status = document.createElement('span');
    status.className = 'v432-sr-status';
    status.setAttribute('aria-live','polite');
    status.setAttribute('aria-atomic','true');
    rotator.append(status);

    const controls = rotator.querySelector('.v43-rotator-controls') || document.createElement('div');
    controls.classList.add('v43-rotator-controls');
    const prev = document.createElement('button');
    prev.type='button'; prev.className='v432-rotator-arrow'; prev.setAttribute('aria-label','Show previous image'); prev.innerHTML='←';
    const next = document.createElement('button');
    next.type='button'; next.className='v432-rotator-arrow'; next.setAttribute('aria-label','Show next image'); next.innerHTML='→';
    const pause = document.createElement('button');
    pause.type='button'; pause.className='v432-rotator-pause'; pause.setAttribute('aria-pressed', String(userPaused)); pause.textContent=userPaused?'Play':'Pause';
    controls.prepend(prev); controls.append(pause,next);
    if (!controls.parentElement) rotator.append(controls);

    const hydrate = (slide) => {
      const img = slide?.querySelector('img[data-src]');
      if (img && !img.getAttribute('src')) { img.src=img.dataset.src; img.removeAttribute('data-src'); }
    };
    const stop = () => { if (timer) window.clearInterval(timer); timer = null; };
    const start = () => {
      stop();
      if (!reducedMotion && !userPaused && !interactionPaused && !document.hidden) timer = window.setInterval(() => show(index + 1, 'automatic'), delay);
    };
    const show = (nextIndex, source='manual') => {
      index = (nextIndex + slides.length) % slides.length;
      hydrate(slides[index]);
      hydrate(slides[(index+1)%slides.length]);
      slides.forEach((slide, i) => {
        const active = i === index;
        slide.classList.toggle('is-active', active);
        slide.setAttribute('aria-hidden', String(!active));
        if ('inert' in slide) slide.inert = !active;
      });
      dots.forEach((dot, i) => {
        const active = i === index;
        dot.classList.toggle('is-active', active);
        dot.setAttribute('aria-pressed', String(active));
      });
      status.textContent = `Image ${index + 1} of ${slides.length}`;
      if (source !== 'initial') emit('rotator_change',{rotator:rotator.getAttribute('aria-label')||`rotator_${rotatorIndex+1}`,image:index+1,source});
    };
    const setInteractionPause = (value) => { interactionPaused=value; rotator.classList.toggle('is-interaction-paused',value); value?stop():start(); };
    const toggleUserPause = () => {
      userPaused=!userPaused;
      pause.setAttribute('aria-pressed',String(userPaused));
      pause.textContent=userPaused?'Play':'Pause';
      rotator.classList.toggle('is-user-paused',userPaused);
      emit('rotator_pause',{paused:userPaused,rotator:rotator.getAttribute('aria-label')||`rotator_${rotatorIndex+1}`});
      start();
    };

    dots.forEach((dot, i) => dot.addEventListener('click', () => { show(i); start(); }));
    prev.addEventListener('click',()=>{show(index-1);start();});
    next.addEventListener('click',()=>{show(index+1);start();});
    pause.addEventListener('click',toggleUserPause);
    rotator.addEventListener('mouseenter',()=>setInteractionPause(true));
    rotator.addEventListener('mouseleave',()=>setInteractionPause(false));
    rotator.addEventListener('focusin',()=>setInteractionPause(true));
    rotator.addEventListener('focusout',(event)=>{if(!rotator.contains(event.relatedTarget))setInteractionPause(false);});
    rotator.addEventListener('keydown',(event)=>{
      if(event.key==='ArrowLeft'){event.preventDefault();show(index-1);start();}
      if(event.key==='ArrowRight'){event.preventDefault();show(index+1);start();}
      if(event.key==='Home'){event.preventDefault();show(0);start();}
      if(event.key==='End'){event.preventDefault();show(slides.length-1);start();}
      if(event.key===' '){event.preventDefault();toggleUserPause();}
    });
    rotator.addEventListener('touchstart',(event)=>{touchStartX=event.changedTouches[0]?.clientX??null;},{passive:true});
    rotator.addEventListener('touchend',(event)=>{
      if(touchStartX===null)return;
      const dx=(event.changedTouches[0]?.clientX??touchStartX)-touchStartX;
      if(Math.abs(dx)>45){show(index+(dx<0?1:-1),'swipe');start();}
      touchStartX=null;
    },{passive:true});
    document.addEventListener('visibilitychange',start);
    show(index,'initial');
    start();
  });
})();

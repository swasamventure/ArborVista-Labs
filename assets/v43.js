(() => {
  'use strict';

  const cleanupHref='assets/v433-final-cleanup.css?v=4.3.3-final-verified';
  if(!document.querySelector('link[data-v433-final-cleanup]')){
    const link=document.createElement('link');
    link.rel='stylesheet';
    link.href=cleanupHref;
    link.dataset.v433FinalCleanup='';
    document.head.append(link);
  }

  // Belt-and-suspenders protection for any older cached homepage markup.
  document.querySelectorAll('.av-utility,.av-hero-note').forEach(element=>element.remove());
  document.querySelectorAll('.brand-logo-v433').forEach(lockup=>{
    lockup.classList.add('brand-logo-horizontal');
    const img=lockup.querySelector('img');
    if(img){
      img.src='assets/arbor-vista-logo-horizontal-v433.webp?v=4.3.3-final-verified';
      img.width=1200;
      img.height=281;
    }
  });

  const header=document.querySelector('[data-v43-header]');
  if(header){const sync=()=>header.classList.toggle('scrolled',window.scrollY>36);sync();window.addEventListener('scroll',sync,{passive:true});}
  const reduced=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const emit=(name,detail={})=>window.dispatchEvent(new CustomEvent('arbor:analytics',{detail:{name,...detail}}));
  document.querySelectorAll('[data-v43-rotator]').forEach((rotator,rotatorIndex)=>{
    const slides=[...rotator.querySelectorAll('[data-rotator-slide]')];
    const dots=[...rotator.querySelectorAll('[data-rotator-dot]')];
    if(slides.length<2)return;
    const delay=Math.max(3000,Number(rotator.dataset.delay)||3000);
    let index=Math.max(0,slides.findIndex(s=>s.classList.contains('is-active'))),timer=null,interaction=false,touchStartX=null;
    rotator.setAttribute('role','region');rotator.setAttribute('aria-roledescription','carousel');
    const status=document.createElement('span');status.className='v432-sr-status';status.setAttribute('aria-live','polite');status.setAttribute('aria-atomic','true');rotator.append(status);
    const controls=rotator.querySelector('.v43-rotator-controls')||document.createElement('div');controls.classList.add('v43-rotator-controls');
    const prev=document.createElement('button');prev.type='button';prev.className='v432-rotator-arrow';prev.setAttribute('aria-label','Show previous image');prev.innerHTML='←';
    const next=document.createElement('button');next.type='button';next.className='v432-rotator-arrow';next.setAttribute('aria-label','Show next image');next.innerHTML='→';
    controls.prepend(prev);controls.append(next);if(!controls.parentElement)rotator.append(controls);
    const hydrate=slide=>{const img=slide?.querySelector('img[data-src]');if(img&&!img.getAttribute('src')){img.src=img.dataset.src;img.removeAttribute('data-src');}};
    const stop=()=>{if(timer)clearInterval(timer);timer=null;};
    const start=()=>{stop();if(!reduced&&!interaction&&!document.hidden)timer=setInterval(()=>show(index+1,'automatic'),delay);};
    const show=(nextIndex,source='manual')=>{index=(nextIndex+slides.length)%slides.length;hydrate(slides[index]);hydrate(slides[(index+1)%slides.length]);slides.forEach((slide,i)=>{const active=i===index;slide.classList.toggle('is-active',active);slide.setAttribute('aria-hidden',String(!active));if('inert' in slide)slide.inert=!active;});dots.forEach((dot,i)=>{const active=i===index;dot.classList.toggle('is-active',active);dot.setAttribute('aria-pressed',String(active));});status.textContent=`Image ${index+1} of ${slides.length}`;if(source!=='initial')emit('rotator_change',{rotator:rotator.getAttribute('aria-label')||`rotator_${rotatorIndex+1}`,image:index+1,source});};
    const setInteraction=value=>{interaction=value;value?stop():start();};
    dots.forEach((dot,i)=>dot.addEventListener('click',()=>{show(i);start();}));prev.addEventListener('click',()=>{show(index-1);start();});next.addEventListener('click',()=>{show(index+1);start();});
    rotator.addEventListener('mouseenter',()=>setInteraction(true));rotator.addEventListener('mouseleave',()=>setInteraction(false));rotator.addEventListener('focusin',()=>setInteraction(true));rotator.addEventListener('focusout',e=>{if(!rotator.contains(e.relatedTarget))setInteraction(false);});
    rotator.addEventListener('keydown',e=>{if(e.key==='ArrowLeft'){e.preventDefault();show(index-1);start();}if(e.key==='ArrowRight'){e.preventDefault();show(index+1);start();}if(e.key==='Home'){e.preventDefault();show(0);start();}if(e.key==='End'){e.preventDefault();show(slides.length-1);start();}});
    rotator.addEventListener('touchstart',e=>{touchStartX=e.changedTouches[0]?.clientX??null;},{passive:true});rotator.addEventListener('touchend',e=>{if(touchStartX===null)return;const dx=(e.changedTouches[0]?.clientX??touchStartX)-touchStartX;if(Math.abs(dx)>45){show(index+(dx<0?1:-1),'swipe');start();}touchStartX=null;},{passive:true});
    document.addEventListener('visibilitychange',start);show(index,'initial');start();
  });
})();

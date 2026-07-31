(() => {
  'use strict';
  const root=document.querySelector('[data-v432-gallery]');
  const dataNode=document.getElementById('v432GalleryData');
  if(!root||!dataNode)return;
  let all=[];
  try{all=JSON.parse(dataNode.textContent||'[]');}catch(error){console.error('Gallery data could not be read',error);return;}
  const image=root.querySelector('[data-gallery-image]');
  const caption=root.querySelector('[data-gallery-caption]');
  const category=root.querySelector('[data-gallery-category]');
  const counter=root.querySelector('[data-gallery-counter]');
  const pause=root.querySelector('[data-gallery-pause]');
  const reduced=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const delay=Math.max(3000,Number(root.dataset.delay)||3000);
  let filter='all',items=all,index=0,timer=null,userPaused=reduced,interactionPaused=false,touchStart=null;
  const emit=(name,detail={})=>window.dispatchEvent(new CustomEvent('arbor:analytics',{detail:{name,...detail}}));
  const filtered=()=>filter==='all'?all:all.filter(item=>item.category===filter);
  const versioned=(src)=>String(src).startsWith('data:')?src:src+'?v=4.3.2';
  const render=(next,source='manual')=>{
    items=filtered(); if(!items.length)return;
    index=(next+items.length)%items.length;
    const item=items[index];
    image.classList.add('is-changing');
    const load=new Image();
    load.onload=()=>{
      image.src=versioned(item.src); image.alt=item.alt; caption.textContent=item.caption; category.textContent=item.categoryLabel;
      counter.textContent=`${index+1} / ${items.length}`; requestAnimationFrame(()=>image.classList.remove('is-changing'));
    };
    load.src=versioned(item.src);
    if(source!=='initial')emit('gallery_change',{category:filter,image:index+1,source});
  };
  const stop=()=>{if(timer)clearInterval(timer);timer=null;};
  const start=()=>{stop();if(!reduced&&!userPaused&&!interactionPaused&&!document.hidden)timer=setInterval(()=>render(index+1,'automatic'),delay);};
  const toggle=()=>{userPaused=!userPaused;pause.setAttribute('aria-pressed',String(userPaused));pause.textContent=userPaused?'Play':'Pause';emit('gallery_pause',{paused:userPaused});start();};
  root.querySelector('[data-gallery-prev]').addEventListener('click',()=>{render(index-1);start();});
  root.querySelector('[data-gallery-next]').addEventListener('click',()=>{render(index+1);start();});
  pause.addEventListener('click',toggle);
  root.querySelectorAll('[data-gallery-filter]').forEach(button=>button.addEventListener('click',()=>{
    filter=button.dataset.galleryFilter;index=0;
    root.querySelectorAll('[data-gallery-filter]').forEach(b=>{const active=b===button;b.classList.toggle('is-active',active);b.setAttribute('aria-pressed',String(active));});
    render(0,'filter');start();
  }));
  root.addEventListener('mouseenter',()=>{interactionPaused=true;stop();});
  root.addEventListener('mouseleave',()=>{interactionPaused=false;start();});
  root.addEventListener('focusin',()=>{interactionPaused=true;stop();});
  root.addEventListener('focusout',event=>{if(!root.contains(event.relatedTarget)){interactionPaused=false;start();}});
  root.addEventListener('keydown',event=>{
    if(event.key==='ArrowLeft'){event.preventDefault();render(index-1);start();}
    if(event.key==='ArrowRight'){event.preventDefault();render(index+1);start();}
    if(event.key==='Home'){event.preventDefault();render(0);start();}
    if(event.key==='End'){event.preventDefault();render(items.length-1);start();}
    if(event.key===' '){event.preventDefault();toggle();}
  });
  root.addEventListener('touchstart',event=>{touchStart=event.changedTouches[0]?.clientX??null;},{passive:true});
  root.addEventListener('touchend',event=>{if(touchStart===null)return;const dx=(event.changedTouches[0]?.clientX??touchStart)-touchStart;if(Math.abs(dx)>45){render(index+(dx<0?1:-1),'swipe');start();}touchStart=null;},{passive:true});
  document.addEventListener('visibilitychange',start);
  pause.setAttribute('aria-pressed',String(userPaused)); pause.textContent=userPaused?'Play':'Pause';
  render(0,'initial');start();
})();

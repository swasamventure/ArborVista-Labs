(() => {
  'use strict';
  const root=document.querySelector('[data-v432-gallery]'),dataNode=document.getElementById('v432GalleryData');if(!root||!dataNode)return;
  let all=[];try{all=JSON.parse(dataNode.textContent||'[]');}catch(error){console.error('Gallery data could not be read',error);return;}
  const image=root.querySelector('[data-gallery-image]'),caption=root.querySelector('[data-gallery-caption]'),category=root.querySelector('[data-gallery-category]'),counter=root.querySelector('[data-gallery-counter]');
  const reduced=window.matchMedia('(prefers-reduced-motion: reduce)').matches,delay=Math.max(3000,Number(root.dataset.delay)||3000);
  let filter='all',items=all,index=0,timer=null,interaction=false,touchStart=null;
  const emit=(name,detail={})=>window.dispatchEvent(new CustomEvent('arbor:analytics',{detail:{name,...detail}}));
  const filtered=()=>filter==='all'?all:all.filter(item=>item.category===filter),versioned=src=>String(src).startsWith('data:')?src:src+'?v=4.3.3';
  const render=(next,source='manual')=>{items=filtered();if(!items.length)return;index=(next+items.length)%items.length;const item=items[index];image.classList.add('is-changing');const load=new Image();load.onload=()=>{image.src=versioned(item.src);image.alt=item.alt;caption.textContent=item.caption;category.textContent=item.categoryLabel;counter.textContent=`${index+1} / ${items.length}`;requestAnimationFrame(()=>image.classList.remove('is-changing'));};load.src=versioned(item.src);if(source!=='initial')emit('gallery_change',{category:filter,image:index+1,source});};
  const stop=()=>{if(timer)clearInterval(timer);timer=null;},start=()=>{stop();if(!reduced&&!interaction&&!document.hidden)timer=setInterval(()=>render(index+1,'automatic'),delay);};
  root.querySelector('[data-gallery-prev]')?.addEventListener('click',()=>{render(index-1);start();});root.querySelector('[data-gallery-next]')?.addEventListener('click',()=>{render(index+1);start();});
  root.querySelectorAll('[data-gallery-filter]').forEach(button=>button.addEventListener('click',()=>{filter=button.dataset.galleryFilter;index=0;root.querySelectorAll('[data-gallery-filter]').forEach(b=>{const active=b===button;b.classList.toggle('is-active',active);b.setAttribute('aria-pressed',String(active));});render(0,'filter');start();}));
  root.addEventListener('mouseenter',()=>{interaction=true;stop();});root.addEventListener('mouseleave',()=>{interaction=false;start();});root.addEventListener('focusin',()=>{interaction=true;stop();});root.addEventListener('focusout',e=>{if(!root.contains(e.relatedTarget)){interaction=false;start();}});
  root.addEventListener('keydown',e=>{if(e.key==='ArrowLeft'){e.preventDefault();render(index-1);start();}if(e.key==='ArrowRight'){e.preventDefault();render(index+1);start();}if(e.key==='Home'){e.preventDefault();render(0);start();}if(e.key==='End'){e.preventDefault();render(items.length-1);start();}});
  root.addEventListener('touchstart',e=>{touchStart=e.changedTouches[0]?.clientX??null;},{passive:true});root.addEventListener('touchend',e=>{if(touchStart===null)return;const dx=(e.changedTouches[0]?.clientX??touchStart)-touchStart;if(Math.abs(dx)>45){render(index+(dx<0?1:-1),'swipe');start();}touchStart=null;},{passive:true});document.addEventListener('visibilitychange',start);render(0,'initial');start();
})();

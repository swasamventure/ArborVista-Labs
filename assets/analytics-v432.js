(() => {
  'use strict';
  const cfg=window.ARBOR_RUNTIME_CONFIG||{};
  const queue=[];
  const clean=(value,max=120)=>String(value??'').replace(/[\r\n\t]/g,' ').slice(0,max);
  const emit=(name,properties={})=>{
    const event={
      event:clean(name,64),
      property_slug:clean(cfg.propertySlug||'arbor-vista-retreat',80),
      path:location.pathname,
      referrer_host:document.referrer?(()=>{try{return new URL(document.referrer).host}catch(_){return''}})():'',
      timestamp:new Date().toISOString(),
      properties:Object.fromEntries(Object.entries(properties).filter(([key])=>!/(name|email|phone|address|message|signature)/i.test(key)).map(([key,value])=>[clean(key,64),clean(value,160)]))
    };
    queue.push(event);
    window.dispatchEvent(new CustomEvent('arbor:metric',{detail:event}));
    const endpoint=cfg.analyticsEndpoint;
    if(endpoint){
      const body=JSON.stringify(event);
      if(navigator.sendBeacon)navigator.sendBeacon(endpoint,new Blob([body],{type:'application/json'}));
      else fetch(endpoint,{method:'POST',headers:{'Content-Type':'application/json'},body,keepalive:true}).catch(()=>{});
    }
  };
  window.arborAnalytics={track:emit,getQueue:()=>queue.slice()};
  emit('page_view',{title:document.title});
  document.addEventListener('click',event=>{
    const target=event.target.closest('[data-analytics]');
    if(!target)return;
    emit(target.dataset.analytics,{label:target.dataset.analyticsLabel||target.textContent.trim(),location:target.dataset.analyticsLocation||'',href:target.getAttribute('href')||''});
  });
  window.addEventListener('arbor:analytics',event=>emit(event.detail?.name||'ui_event',event.detail||{}));
  const booking=document.getElementById('bookingFlow');
  if(booking){
    booking.addEventListener('change',event=>{
      if(['check_in','check_out','adults','children'].includes(event.target.name))emit('booking_field_progress',{field:event.target.name});
    });
    booking.addEventListener('submit',()=>emit('booking_submit_attempt'));
  }
})();

const menu=document.querySelector('.menu'),links=document.querySelector('.links');if(menu&&links)menu.addEventListener('click',()=>links.classList.toggle('open'));document.querySelectorAll('[data-year]').forEach(x=>x.textContent=new Date().getFullYear());
function showSuccess(form,id){form.addEventListener('submit',e=>{e.preventDefault();const data=Object.fromEntries(new FormData(form));localStorage.setItem(id,JSON.stringify({...data,submittedAt:new Date().toISOString()}));document.querySelector(`[data-success="${id}"]`)?.classList.add('show');form.reset();window.scrollTo({top:document.body.scrollHeight,behavior:'smooth'});});}
document.querySelectorAll('form[data-save]').forEach(f=>showSuccess(f,f.dataset.save));
const arrival=document.querySelector('[data-arrival]');if(arrival){const d=new Date(arrival.dataset.arrival+'T16:00:00');const days=Math.max(0,Math.ceil((d-new Date())/86400000));arrival.textContent=days===0?'Today':`${days} day${days===1?'':'s'}`;}
const portalGate=localStorage.getItem('gate-pass-demo');if(portalGate){document.querySelectorAll('[data-gate-status]').forEach(x=>x.textContent='Information received — processing');document.querySelectorAll('[data-gate-pill]').forEach(x=>x.classList.add('done'));}

// v2.7.2 guided Book Direct flow with clickable steps and 24-hour draft autosave
(()=>{
  const form=document.getElementById('bookingFlow');
  if(!form) return;

  const DRAFT_KEY='arbor-vista-booking-draft-v2';
  const REQUEST_KEY='arbor-vista-booking-request';
  const DRAFT_TTL=24*60*60*1000;
  const panels=[...form.querySelectorAll('[data-booking-step]')];
  const nav=[...document.querySelectorAll('[data-step-nav]')];
  const progress=document.querySelector('[data-progress-bar]');
  let current=1;
  let saveTimer;

  const today=new Date();
  const iso=today.toISOString().split('T')[0];
  const checkIn=form.elements.check_in;
  const checkOut=form.elements.check_out;
  const agreementDate=form.elements.agreement_date;
  if(checkIn) checkIn.min=iso;
  if(checkOut) checkOut.min=iso;

  function formValues(){
    const values={};
    [...form.elements].forEach(el=>{
      if(!el.name) return;
      if(el.type==='checkbox') values[el.name]=el.checked;
      else values[el.name]=el.value;
    });
    return values;
  }

  function saveDraft(immediate=false){
    const write=()=>{
      localStorage.setItem(DRAFT_KEY,JSON.stringify({savedAt:Date.now(),step:Math.min(current,4),values:formValues()}));
    };
    clearTimeout(saveTimer);
    if(immediate) write(); else saveTimer=setTimeout(write,250);
  }

  function clearDraft(){ localStorage.removeItem(DRAFT_KEY); }

  function restoreDraft(){
    let draft;
    try{ draft=JSON.parse(localStorage.getItem(DRAFT_KEY)||'null'); }catch(_){ clearDraft(); return false; }
    if(!draft?.savedAt || Date.now()-draft.savedAt>DRAFT_TTL){ clearDraft(); return false; }
    Object.entries(draft.values||{}).forEach(([name,value])=>{
      const el=form.elements[name];
      if(!el) return;
      if(el.type==='checkbox') el.checked=Boolean(value);
      else el.value=value ?? '';
    });
    current=Math.max(1,Math.min(Number(draft.step)||1,4));
    return true;
  }

  const restored=restoreDraft();
  if(agreementDate && !agreementDate.value) agreementDate.value=iso;

  checkIn?.addEventListener('change',()=>{
    if(!checkIn.value) return;
    const next=new Date(checkIn.value+'T12:00:00'); next.setDate(next.getDate()+1);
    checkOut.min=next.toISOString().split('T')[0];
    if(checkOut.value && checkOut.value<=checkIn.value) checkOut.value='';
    saveDraft();
  });

  form.elements.first_name?.addEventListener('input',syncLegalName);
  form.elements.last_name?.addEventListener('input',syncLegalName);
  function syncLegalName(){
    const name=`${form.elements.first_name.value} ${form.elements.last_name.value}`.trim();
    if(!form.elements.legal_name.dataset.edited) form.elements.legal_name.value=name;
    saveDraft();
  }
  form.elements.legal_name?.addEventListener('input',()=>{
    form.elements.legal_name.dataset.edited='true';
    saveDraft();
  });

  form.addEventListener('input',()=>saveDraft());
  form.addEventListener('change',()=>saveDraft());
  window.addEventListener('pagehide',()=>saveDraft(true));

  function setStep(step,{scroll=true,save=true}={}){
    current=step;
    panels.forEach(p=>p.classList.toggle('active',Number(p.dataset.bookingStep)===step));
    nav.forEach((n,i)=>{
      n.classList.toggle('active',i+1===step);
      n.classList.toggle('complete',i+1<step);
      n.setAttribute('aria-current',i+1===step?'step':'false');
    });
    if(progress) progress.style.width=`${Math.min(step,4)*25}%`;
    if(step===4) renderReview();
    if(save && step<=4) saveDraft(true);
    if(scroll) document.querySelector('.booking-shell')?.scrollIntoView({behavior:'smooth',block:'start'});
  }

  function clearErrors(panel){
    panel?.querySelectorAll('.invalid').forEach(x=>x.classList.remove('invalid'));
    panel?.querySelectorAll('.field-error').forEach(x=>x.remove());
  }
  function validateStep(step){
    const panel=panels.find(p=>Number(p.dataset.bookingStep)===step);
    if(!panel) return true;
    clearErrors(panel);
    const required=[...panel.querySelectorAll('[required]')];
    let firstBad=null;
    required.forEach(el=>{
      const ok=el.type==='checkbox'?el.checked:el.checkValidity();
      if(!ok){
        const field=el.closest('.field'); field?.classList.add('invalid');
        if(field && !field.querySelector('.field-error')) field.insertAdjacentHTML('beforeend','<span class="field-error">Please complete this field.</span>');
        firstBad??=el;
      }
    });
    if(step===1 && checkIn.value && checkOut.value && checkOut.value<=checkIn.value){
      const field=checkOut.closest('.field'); field?.classList.add('invalid');
      if(field && !field.querySelector('.field-error')) field.insertAdjacentHTML('beforeend','<span class="field-error">Check-out must be after check-in.</span>');
      firstBad??=checkOut;
    }
    firstBad?.focus();
    return !firstBad;
  }

  function canOpenStep(target){
    if(target<=current) return true;
    for(let step=1;step<target;step++){
      if(!validateStep(step)){ setStep(step); return false; }
    }
    return true;
  }

  nav.forEach(button=>button.addEventListener('click',()=>{
    const target=Number(button.dataset.stepNav);
    if(target>=1 && target<=4 && canOpenStep(target)) setStep(target);
  }));

  form.querySelectorAll('[data-next]').forEach(btn=>btn.addEventListener('click',()=>{
    if(validateStep(current)) setStep(current+1);
  }));
  form.querySelectorAll('[data-back]').forEach(btn=>btn.addEventListener('click',()=>setStep(Math.max(1,current-1))));

  function prettyDate(value){
    if(!value)return '—';
    return new Date(value+'T12:00:00').toLocaleDateString(undefined,{month:'long',day:'numeric',year:'numeric'});
  }
  function renderReview(){
    const review=document.querySelector('[data-booking-review]');
    if(!review) return;
    const fields=[
      ['Stay',`${prettyDate(checkIn.value)} – ${prettyDate(checkOut.value)}`],
      ['Guests',`${form.elements.adults.value} adult(s) · ${form.elements.children.value} child(ren)`],
      ['Primary guest',`${form.elements.first_name.value} ${form.elements.last_name.value}`],
      ['Contact',`${form.elements.email.value}<br>${form.elements.phone.value}`],
      ['Vehicles',form.elements.vehicles.value],
      ['Electronic signature',form.elements.electronic_signature.value]
    ];
    review.innerHTML=fields.map(([k,v])=>`<div class="review-item"><small>${k}</small><strong>${v}</strong></div>`).join('');
  }

  function slugify(s){return s.toLowerCase().trim().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'');}
  form.addEventListener('submit',e=>{
    e.preventDefault();
    if(!validateStep(3)){setStep(3);return;}
    const data=Object.fromEntries(new FormData(form));
    const random=String(Math.floor(1000+Math.random()*9000));
    const slug=`${slugify(data.first_name+' '+data.last_name)}-${random}`;
    data.guestSlug=slug; data.submittedAt=new Date().toISOString();
    localStorage.setItem(REQUEST_KEY,JSON.stringify(data));
    clearDraft();
    document.querySelector('[data-confirm-name]').textContent=data.first_name;
    const guestLink=document.querySelector('[data-guest-link]');
    if(guestLink){
      const previewUrl=new URL('guest/',document.baseURI);
      previewUrl.searchParams.set('id',slug);
      guestLink.href=previewUrl.href;
      guestLink.textContent=`Open ${data.first_name}'s guest portal preview`;
    }
    setStep(5,{save:false});
  });

  if(restored){
    const shell=document.querySelector('.booking-shell');
    const notice=document.createElement('div');
    notice.className='draft-restored';
    notice.innerHTML='Your saved booking draft was restored. <button type="button">Start over</button>';
    shell?.insertBefore(notice,shell.firstChild);
    notice.querySelector('button')?.addEventListener('click',()=>{
      clearDraft();
      form.reset();
      agreementDate.value=iso;
      form.elements.legal_name.dataset.edited='';
      notice.remove();
      setStep(1);
    });
  }

  setStep(current,{scroll:false,save:false});
})();


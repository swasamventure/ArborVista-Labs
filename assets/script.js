
const m=document.querySelector('.menu'),l=document.querySelector('.links');if(m&&l)m.addEventListener('click',()=>l.classList.toggle('open'));
document.querySelectorAll('[data-year]').forEach(x=>x.textContent=new Date().getFullYear());

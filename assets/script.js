
const m=document.querySelector('.menu'),l=document.querySelector('.links');if(m&&l)m.addEventListener('click',()=>l.classList.toggle('open'));
document.querySelectorAll('[data-year]').forEach(x=>x.textContent=new Date().getFullYear());


const reviewCards=[...document.querySelectorAll('.review-card')];
const reviewDots=[...document.querySelectorAll('.review-dot')];
let reviewIndex=0;
function showReview(i){
  if(!reviewCards.length)return;
  reviewIndex=(i+reviewCards.length)%reviewCards.length;
  reviewCards.forEach((card,n)=>card.classList.toggle('active',n===reviewIndex));
  reviewDots.forEach((dot,n)=>dot.classList.toggle('active',n===reviewIndex));
}
reviewDots.forEach((dot,i)=>dot.addEventListener('click',()=>showReview(i)));
if(reviewCards.length>1)setInterval(()=>showReview(reviewIndex+1),6500);

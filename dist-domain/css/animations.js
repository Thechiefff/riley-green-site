/*!  Riley Green — Bold Animation System  */
(function(){

/* ═══════════════════════════════════════
   1. CUSTOM CURSOR
═══════════════════════════════════════ */
const cur  = document.createElement('div');
const ring = document.createElement('div');
cur.id  = 'rg-cursor';
ring.id = 'rg-ring';
document.body.appendChild(cur);
document.body.appendChild(ring);

let mx=0,my=0,rx=0,ry=0,scale=1;

document.addEventListener('mousemove', e => {
  mx = e.clientX; my = e.clientY;
  cur.style.transform = `translate(${mx}px,${my}px) translate(-50%,-50%)`;
});

(function animRing(){
  rx += (mx - rx) * .09;
  ry += (my - ry) * .09;
  ring.style.transform = `translate(${rx}px,${ry}px) translate(-50%,-50%) scale(${scale})`;
  requestAnimationFrame(animRing);
})();

// Magnetic hover on interactive elements
document.querySelectorAll('a,button,.album-card,.filter-btn,.nav-cta').forEach(el => {
  el.addEventListener('mouseenter', () => {
    cur.classList.add('cursor-hover');
    ring.classList.add('ring-hover');
    scale = 1.6;
  });
  el.addEventListener('mouseleave', () => {
    cur.classList.remove('cursor-hover');
    ring.classList.remove('ring-hover');
    scale = 1;
  });
});

document.addEventListener('mouseleave', () => { cur.style.opacity='0'; ring.style.opacity='0'; });
document.addEventListener('mouseenter', () => { cur.style.opacity='1'; ring.style.opacity='1'; });


/* ═══════════════════════════════════════
   2. SPLIT TEXT — word-by-word entrance
═══════════════════════════════════════ */
function splitWords(el, baseDelay=0){
  const text = el.textContent;
  const words = text.split(' ');
  el.innerHTML = words.map((w,i) =>
    `<span class="rg-word" style="--d:${baseDelay + i*0.08}s">${w}</span>`
  ).join(' ');
}

// Apply to main headings
document.querySelectorAll('h1.hero-title, h1.hero-name, h1.page-title').forEach(el => splitWords(el, 0.2));


/* ═══════════════════════════════════════
   3. BOLD SCROLL REVEAL
   Uses IntersectionObserver — elements
   blast in hard from bottom / sides
═══════════════════════════════════════ */
const revealObs = new IntersectionObserver(entries => {
  entries.forEach(e => {
    if (!e.isIntersecting) return;
    e.target.classList.add('rg-visible');
    revealObs.unobserve(e.target);
  });
}, { threshold: 0.08, rootMargin: '0px 0px -60px 0px' });

document.querySelectorAll(
  '.reveal, .album-card, .step, .benefit, .testimonial, .tour-item, .tour-row, .track-item, .timeline-item, .stat-item, .perk-item, .pledge-row'
).forEach((el, i) => {
  if (!el.classList.contains('rg-triggered')) {
    el.classList.add('rg-reveal');
    el.style.setProperty('--ri', i);
    revealObs.observe(el);
  }
});


/* ═══════════════════════════════════════
   4. PARALLAX on hero images
═══════════════════════════════════════ */
const heroImgs = document.querySelectorAll('.page-hero-img img, .hero-bg, .hero-orb');
function parallax(){
  const sy = window.scrollY;
  heroImgs.forEach(img => {
    img.style.transform = `translateY(${sy * 0.35}px)`;
  });
  // also move hero orbs inversely
  document.querySelectorAll('.hero-orb1').forEach(o => o.style.transform = `translateY(${-sy * 0.12}px)`);
  document.querySelectorAll('.hero-orb2').forEach(o => o.style.transform = `translateY(${sy * 0.08}px)`);
}
window.addEventListener('scroll', parallax, { passive: true });


/* ═══════════════════════════════════════
   5. MAGNETIC BUTTONS — cursor-attract
═══════════════════════════════════════ */
document.querySelectorAll('.btn-dark,.btn-black,.btn-cream,.btn-outline,.nav-cta,.btn-gold,.stream-btn,.filter-btn').forEach(btn => {
  btn.addEventListener('mousemove', e => {
    const r = btn.getBoundingClientRect();
    const dx = e.clientX - (r.left + r.width/2);
    const dy = e.clientY - (r.top + r.height/2);
    btn.style.transform = `translate(${dx * 0.25}px, ${dy * 0.35}px)`;
  });
  btn.addEventListener('mouseleave', () => {
    btn.style.transform = '';
    btn.style.transition = 'transform 0.5s cubic-bezier(0.25,1,0.5,1)';
    setTimeout(() => btn.style.transition = '', 500);
  });
});


/* ═══════════════════════════════════════
   6. COUNTER ANIMATION
═══════════════════════════════════════ */
const countObs = new IntersectionObserver(entries => {
  entries.forEach(e => {
    if (!e.isIntersecting) return;
    const el = e.target;
    const target = parseFloat(el.dataset.target || el.textContent.replace(/[^0-9.]/g,''));
    const suffix = el.dataset.suffix || (el.textContent.includes('%') ? '%' : '');
    const prefix = el.dataset.prefix || (el.textContent.includes('₦') ? '₦' : '');
    if (!target) return;
    const dur = 1800;
    const start = performance.now();
    const isBig = target > 999999;
    function fmt(n){
      if(isBig){
        const b = n/1000000000;
        if(b>=1) return prefix+b.toFixed(1)+'B'+suffix;
        return prefix+(n/1000000).toFixed(0)+'M'+suffix;
      }
      return prefix+Math.floor(n).toLocaleString()+suffix;
    }
    (function tick(now){
      const t = Math.min((now-start)/dur,1);
      const ease = 1 - Math.pow(1-t, 4);
      el.textContent = fmt(target * ease);
      if(t<1) requestAnimationFrame(tick);
      else el.textContent = fmt(target);
    })(performance.now());
    countObs.unobserve(el);
  });
}, {threshold:0.6});

document.querySelectorAll('[data-target], .stat-number, .scarcity-num').forEach(el => {
  if(el.dataset.target || /^[\d,\.₦%BM+]+$/.test(el.textContent.trim())){
    countObs.observe(el);
  }
});


/* ═══════════════════════════════════════
   7. ALBUM CARD RIPPLE — hover one,
      siblings slightly react
═══════════════════════════════════════ */
document.querySelectorAll('.album-grid').forEach(grid => {
  const cards = grid.querySelectorAll('.album-card');
  cards.forEach(card => {
    card.addEventListener('mouseenter', () => {
      cards.forEach(c => {
        if(c !== card) c.style.opacity = '0.65';
      });
    });
    card.addEventListener('mouseleave', () => {
      cards.forEach(c => c.style.opacity = '');
    });
  });
});


/* ═══════════════════════════════════════
   8. MARQUEE PAUSE on hover
═══════════════════════════════════════ */
document.querySelectorAll('.marquee-track').forEach(t => {
  t.addEventListener('mouseenter', () => t.style.animationPlayState = 'paused');
  t.addEventListener('mouseleave', () => t.style.animationPlayState = 'running');
});


/* ═══════════════════════════════════════
   9. NAV — active link bold underline
      that slides between items
═══════════════════════════════════════ */
const navLinks = document.querySelectorAll('.nav-links a');
const indicator = document.createElement('span');
indicator.id = 'nav-indicator';
const navLinksWrap = document.querySelector('.nav-links');
if(navLinksWrap){ navLinksWrap.style.position='relative'; navLinksWrap.appendChild(indicator); }

function moveIndicator(el){
  if(!el || !navLinksWrap) return;
  const pr = navLinksWrap.getBoundingClientRect();
  const er = el.getBoundingClientRect();
  indicator.style.left   = (er.left - pr.left) + 'px';
  indicator.style.width  = er.width + 'px';
  indicator.style.opacity= '1';
}
navLinks.forEach(a => {
  if(a.classList.contains('active')) moveIndicator(a);
  a.addEventListener('mouseenter', () => moveIndicator(a));
});
if(navLinksWrap){
  navLinksWrap.addEventListener('mouseleave', () => {
    const active = navLinksWrap.querySelector('.active');
    active ? moveIndicator(active) : (indicator.style.opacity='0');
  });
}


/* ═══════════════════════════════════════
   10. GOLD LINE draw on section entry
═══════════════════════════════════════ */
const lineObs = new IntersectionObserver(entries => {
  entries.forEach(e => {
    if(e.isIntersecting) e.target.classList.add('line-drawn');
  });
}, {threshold:0.3});
document.querySelectorAll('.section-tag::before, .tag::before, .hero-eyebrow::before').forEach(el => lineObs.observe(el));

// Actually target the parent elements since ::before can't be observed
document.querySelectorAll('.section-tag, .tag, .hero-eyebrow, .page-eyebrow').forEach(el => {
  el.classList.add('rg-line-el');
  lineObs.observe(el);
});


})();

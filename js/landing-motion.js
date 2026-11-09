// 메인 랜딩의 히어로 커서·스크롤 인터랙션과 소개 영상 지연 로드를 담당한다(rAF + CSS 변수, 의존성 없음)
(function () {
  'use strict';

  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)');
  var finePointer = window.matchMedia('(hover: hover) and (pointer: fine)');

  /* ---------- 히어로 ---------- */
  var hero = document.querySelector('[data-hero]');
  var heroVideo = hero && hero.querySelector('.hero-video');

  function setupHero() {
    if (!hero) return;
    if (reduce.matches) {
      if (heroVideo) { heroVideo.removeAttribute('autoplay'); heroVideo.pause(); }
      return;
    }
    hero.classList.add('is-live');

    hero.querySelectorAll('[data-depth]').forEach(function (el) {
      el.style.setProperty('--d', el.getAttribute('data-depth'));
    });

    // 목표값(target)과 현재값(cur)을 lerp 로 따라가며, 거의 같아지면 루프를 멈춘다
    var target = { x: 0.5, y: 0.4, sp: 0 };
    var cur = { x: 0.5, y: 0.4, sp: 0 };
    var running = false;
    var rect = hero.getBoundingClientRect();

    function measure() { rect = hero.getBoundingClientRect(); }

    function readScroll() {
      var h = hero.offsetHeight || 1;
      target.sp = Math.min(1, Math.max(0, window.scrollY / h));
    }

    function frame() {
      var k = 0.12;
      cur.x += (target.x - cur.x) * k;
      cur.y += (target.y - cur.y) * k;
      cur.sp += (target.sp - cur.sp) * 0.2;
      var s = hero.style;
      s.setProperty('--mx', (cur.x * 100).toFixed(2) + '%');
      s.setProperty('--my', (cur.y * 100).toFixed(2) + '%');
      s.setProperty('--tx', ((cur.x - 0.5) * 2).toFixed(4));
      s.setProperty('--ty', ((cur.y - 0.5) * 2).toFixed(4));
      s.setProperty('--sp', cur.sp.toFixed(4));
      var settled = Math.abs(target.x - cur.x) < 0.0005 && Math.abs(target.y - cur.y) < 0.0005 && Math.abs(target.sp - cur.sp) < 0.0005;
      if (settled) { running = false; return; }
      requestAnimationFrame(frame);
    }

    function kick() {
      if (!running) { running = true; requestAnimationFrame(frame); }
    }

    if (finePointer.matches) {
      hero.addEventListener('pointermove', function (e) {
        target.x = (e.clientX - rect.left) / rect.width;
        target.y = (e.clientY - rect.top) / rect.height;
        hero.classList.add('is-pointing');
        kick();
      });
      hero.addEventListener('pointerenter', measure);
      hero.addEventListener('pointerleave', function () {
        target.x = 0.5; target.y = 0.4;
        hero.classList.remove('is-pointing');
        kick();
      });

      // 자석 버튼: 버튼 안에서 커서 쪽으로 살짝 끌려간다
      hero.querySelectorAll('[data-magnetic]').forEach(function (btn) {
        btn.addEventListener('pointermove', function (e) {
          var r = btn.getBoundingClientRect();
          btn.style.setProperty('--bx', ((e.clientX - r.left - r.width / 2) * 0.3).toFixed(1) + 'px');
          btn.style.setProperty('--by', ((e.clientY - r.top - r.height / 2) * 0.4).toFixed(1) + 'px');
        });
        btn.addEventListener('pointerleave', function () {
          btn.style.setProperty('--bx', '0px');
          btn.style.setProperty('--by', '0px');
        });
      });
    }

    window.addEventListener('scroll', function () { readScroll(); measure(); kick(); }, { passive: true });
    window.addEventListener('resize', function () { measure(); readScroll(); kick(); });
    readScroll();
    kick();

    // 히어로가 화면 밖이면 배경 영상을 멈춰 디코딩 비용을 아낀다
    if (heroVideo && 'IntersectionObserver' in window) {
      new IntersectionObserver(function (entries) {
        entries.forEach(function (en) {
          if (en.isIntersecting) { var p = heroVideo.play(); if (p && p.catch) p.catch(function () {}); }
          else heroVideo.pause();
        });
      }).observe(hero);
    }
  }

  /* ---------- 서비스 카드 스포트라이트 ---------- */
  function setupCards() {
    if (reduce.matches || !finePointer.matches) return;
    document.querySelectorAll('[data-spot]').forEach(function (card) {
      card.addEventListener('pointermove', function (e) {
        var r = card.getBoundingClientRect();
        card.style.setProperty('--cx', (e.clientX - r.left) + 'px');
        card.style.setProperty('--cy', (e.clientY - r.top) + 'px');
      });
    });
  }

  /* ---------- 소개 영상 지연 로드 ---------- */
  function setupLazyVideo() {
    var videos = document.querySelectorAll('video.lazy-video');
    if (!videos.length) return;

    function load(v) {
      if (v.dataset.loaded) return;
      v.querySelectorAll('source[data-src]').forEach(function (s) { s.src = s.dataset.src; });
      v.preload = 'metadata';
      v.load();
      v.dataset.loaded = '1';
    }

    if (!('IntersectionObserver' in window)) { videos.forEach(load); return; }

    // 가까워지면 소스를 붙이고, 절반 이상 보이면(모션 허용 시) 자동 재생
    var near = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) { load(en.target); near.unobserve(en.target); }
      });
    }, { rootMargin: '300px 0px' });

    var inView = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        var v = en.target;
        if (en.isIntersecting && !reduce.matches) {
          load(v);
          var p = v.play(); if (p && p.catch) p.catch(function () {});
        } else if (!en.isIntersecting) {
          v.pause();
        }
      });
    }, { threshold: 0.5 });

    videos.forEach(function (v) { near.observe(v); inView.observe(v); });
  }

  setupHero();
  setupCards();
  setupLazyVideo();
})();

/* =====================================================================
   Kern: hulpjes, canvas/toneel, cachelagen en sprites.
   Toneel = 1672 x 941, precies de maat van de template (ref.png),
   zodat we met de O-toets de template eroverheen kunnen leggen.
   ===================================================================== */
(function () {
  'use strict';
  const SK = window.SK = {};
  const TAU = SK.TAU = Math.PI * 2;
  const clamp = SK.clamp = (v, a, b) => (v < a ? a : v > b ? b : v);
  const lerp = SK.lerp = (a, b, t) => a + (b - a) * t;
  SK.smooth = (e0, e1, x) => { const t = clamp((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t); };

  SK.rng = function (seed) {
    return function () {
      seed |= 0; seed = (seed + 0x6D2B79F5) | 0;
      let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  };
  SK.noise1 = function (seed) {
    const r = SK.rng(seed), n = 256, a = new Float32Array(n);
    for (let i = 0; i < n; i++) a[i] = r();
    return function (x) {
      const xi = Math.floor(x), f = x - xi;
      const i0 = ((xi % n) + n) % n, i1 = (i0 + 1) % n;
      const t = f * f * (3 - 2 * f);
      return a[i0] + (a[i1] - a[i0]) * t;
    };
  };
  SK.fbm = function (nf, x, oct) {
    let v = 0, amp = 0.5, fr = 1, norm = 0;
    for (let i = 0; i < (oct || 3); i++) { v += nf(x * fr) * amp; norm += amp; amp *= 0.5; fr *= 2.07; }
    return v / norm;
  };
  const cc = {};
  const rgb = SK.rgb = function (c) {
    if (cc[c]) return cc[c];
    let v;
    if (c.charCodeAt(0) === 35) v = [parseInt(c.slice(1, 3), 16), parseInt(c.slice(3, 5), 16), parseInt(c.slice(5, 7), 16)];
    else { const m = c.match(/-?\d+(\.\d+)?/g); v = [+m[0], +m[1], +m[2]]; }
    cc[c] = v; return v;
  };
  SK.mix = function (a, b, t) {
    const A = rgb(a), C = rgb(b);
    return 'rgb(' + Math.round(lerp(A[0], C[0], t)) + ',' + Math.round(lerp(A[1], C[1], t)) + ',' + Math.round(lerp(A[2], C[2], t)) + ')';
  };
  SK.rgba = function (c, a) { const v = rgb(c); return 'rgba(' + v[0] + ',' + v[1] + ',' + v[2] + ',' + a + ')'; };

  /* ---------------- toneel ---------------- */
  const VW = SK.VW = 1672, VH = SK.VH = 941;
  const canvas = SK.canvas = document.getElementById('stage');
  const mainCtx = canvas.getContext('2d', { alpha: false });
  mainCtx._tag = 'main';
  SK.ctx = mainCtx;
  SK.mainCtx = mainCtx;
  SK.view = { scale: 1, ox: 0, oy: 0, dpr: 1 };
  SK.quality = 1;
  SK.B = { x0: 0, x1: VW, y0: 0, y1: VH };
  const layers = SK.layers = {};

  SK.resize = function () {
    let dpr = Math.min(window.devicePixelRatio || 1, 2);
    const w = window.innerWidth, h = window.innerHeight;
    while (dpr > 1 && w * h * dpr * dpr > 3.3e6) dpr -= 0.25;
    const eff = dpr * SK.quality;
    canvas.width = Math.round(w * eff);
    canvas.height = Math.round(h * eff);
    const cover = Math.max(w / VW, h / VH), fit = Math.min(w / VW, h / VH);
    const scale = Math.min(cover, fit * 1.18);
    const ox = (w - VW * scale) / 2, oy = (h - VH * scale) / 2;
    SK.view = { scale: scale, ox: ox, oy: oy, dpr: eff };
    SK.B = { x0: -ox / scale, x1: (w - ox) / scale, y0: -oy / scale, y1: (h - oy) / scale };
    for (const k in layers) layers[k].key = null;
  };

  SK.setMainTransform = function () {
    const v = SK.view, s = v.scale * v.dpr;
    mainCtx.setTransform(s, 0, 0, s, v.dpr * v.ox, v.dpr * v.oy);
  };

  /* Cachelaag: canvas op schermformaat met dezelfde transform als het
     hoofdcanvas. paint() tekent op SK.ctx (die tijdelijk naar de laag wijst). */
  SK.renderLayer = function (name, key, paint, grade) {
    const w = canvas.width, h = canvas.height;
    let L = layers[name];
    if (!L || L.c.width !== w || L.c.height !== h) {
      const c = document.createElement('canvas');
      c.width = w; c.height = h;
      L = layers[name] = { c: c, g: c.getContext('2d'), key: null };
      L.g._tag = name;
    }
    if (L.key !== key) {
      const v = SK.view, s = v.scale * v.dpr;
      L.g.setTransform(1, 0, 0, 1, 0, 0);
      L.g.clearRect(0, 0, w, h);
      L.g.setTransform(s, 0, 0, s, v.dpr * v.ox, v.dpr * v.oy);
      const prev = SK.ctx;
      SK.ctx = L.g;
      paint(L.g);
      SK.ctx = prev;
      if (grade && 'filter' in L.g) {      // eenmalige kleurcorrectie van de laag
        const tmp = document.createElement('canvas'); tmp.width = w; tmp.height = h;
        tmp.getContext('2d').drawImage(L.c, 0, 0);
        L.g.save(); L.g.setTransform(1, 0, 0, 1, 0, 0); L.g.clearRect(0, 0, w, h);
        L.g.filter = grade; L.g.drawImage(tmp, 0, 0); L.g.restore();
      }
      L.key = key;
    }
    const ctx = SK.ctx;
    ctx.save();
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.drawImage(L.c, 0, 0);
    ctx.restore();
  };

  /* ---------------- tekenhulpjes ---------------- */
  SK.poly = function (ctx, pts, close) {
    ctx.beginPath();
    for (let i = 0; i < pts.length; i++) {
      const p = pts[i];
      if (i) ctx.lineTo(p[0], p[1]); else ctx.moveTo(p[0], p[1]);
    }
    if (close !== false) ctx.closePath();
  };
  // gladde lijn door punten (kwadratisch door middelpunten)
  SK.curve = function (ctx, pts, move) {
    if (move !== false) ctx.moveTo(pts[0][0], pts[0][1]);
    for (let i = 1; i < pts.length - 1; i++) {
      const mx = (pts[i][0] + pts[i + 1][0]) / 2, my = (pts[i][1] + pts[i + 1][1]) / 2;
      ctx.quadraticCurveTo(pts[i][0], pts[i][1], mx, my);
    }
    const l = pts[pts.length - 1];
    ctx.lineTo(l[0], l[1]);
  };
  SK.lin = function (ctx, x0, y0, x1, y1, stops) {
    const g = ctx.createLinearGradient(x0, y0, x1, y1);
    for (const s of stops) g.addColorStop(s[0], s[1]);
    return g;
  };
  SK.rad = function (ctx, x, y, r0, r1, stops, x1, y1) {
    const g = ctx.createRadialGradient(x, y, r0, x1 === undefined ? x : x1, y1 === undefined ? y : y1, r1);
    for (const s of stops) g.addColorStop(s[0], s[1]);
    return g;
  };

  /* ---------------- sprites ---------------- */
  const glowCache = {};
  SK.glow = function (col, soft) {
    const k = col + (soft || 0);
    if (glowCache[k]) return glowCache[k];
    const c = document.createElement('canvas'); c.width = c.height = 128;
    const g = c.getContext('2d');
    const v = rgb(col);
    const gr = g.createRadialGradient(64, 64, 0, 64, 64, 64);
    const e = soft ? 2.2 : 1.4;
    for (let i = 0; i <= 10; i++) {
      const t = i / 10, a = Math.pow(1 - t, e);
      gr.addColorStop(t, 'rgba(' + v[0] + ',' + v[1] + ',' + v[2] + ',' + a.toFixed(3) + ')');
    }
    g.fillStyle = gr; g.fillRect(0, 0, 128, 128);
    glowCache[k] = c; return c;
  };
  SK.drawGlow = function (ctx, spr, x, y, r, a, sy) {
    ctx.globalAlpha = a;
    ctx.drawImage(spr, x - r, y - r * (sy || 1), r * 2, r * 2 * (sy || 1));
  };

  // esdoornblad (5 lobben) — sprites per kleur
  function leafPath(g, s) {
    const pts = [];
    const lobes = [[0, 1.0], [0.62, 0.78], [1.15, 0.86], [1.62, 0.42], [2.1, 0.5]];
    g.beginPath();
    g.moveTo(0, s * 0.18);
    const side = (dir) => {
      const L = dir > 0 ? lobes.slice().reverse() : lobes;
      for (const l of L) {
        const a = -Math.PI / 2 + dir * l[0];
        pts.push([Math.cos(a) * s * l[1], Math.sin(a) * s * l[1]]);
      }
    };
    side(-1);
    // tanden tussen de lobben
    const all = [];
    const left = pts.slice();
    pts.length = 0; side(1);
    const seq = left.concat(pts.slice(1));
    for (let i = 0; i < seq.length; i++) {
      all.push(seq[i]);
      if (i < seq.length - 1) {
        const a = seq[i], b = seq[i + 1];
        all.push([(a[0] + b[0]) * 0.32, (a[1] + b[1]) * 0.32]);
      }
    }
    g.lineTo(all[0][0] * 0.5, s * 0.1);
    for (const p of all) g.lineTo(p[0], p[1]);
    g.lineTo(all[all.length - 1][0] * 0.5, s * 0.1);
    g.closePath();
  }
  const leafCache = {};
  SK.leaf = function (col) {
    if (leafCache[col]) return leafCache[col];
    const c = document.createElement('canvas'); c.width = c.height = 64;
    const g = c.getContext('2d');
    g.translate(32, 36);
    leafPath(g, 26);
    const gr = g.createLinearGradient(-20, -26, 20, 10);
    gr.addColorStop(0, SK.mix(col, '#ffe7a0', 0.35));
    gr.addColorStop(0.55, col);
    gr.addColorStop(1, SK.mix(col, '#3a1206', 0.45));
    g.fillStyle = gr; g.fill();
    g.strokeStyle = SK.mix(col, '#4a1a06', 0.5); g.lineWidth = 1; g.stroke();
    g.strokeStyle = SK.rgba('#fff0b0', 0.35); g.lineWidth = 1;
    g.beginPath();
    for (const a of [-Math.PI / 2, -Math.PI / 2 - 0.9, -Math.PI / 2 + 0.9, -Math.PI / 2 - 1.7, -Math.PI / 2 + 1.7]) {
      g.moveTo(0, 2); g.lineTo(Math.cos(a) * 18, Math.sin(a) * 18);
    }
    g.stroke();
    g.strokeStyle = SK.mix(col, '#3a1206', 0.5); g.lineWidth = 1.6;
    g.beginPath(); g.moveTo(0, 4); g.lineTo(1, 14); g.stroke();
    leafCache[col] = c; return c;
  };
  SK.LEAF_COLS = ['#f5a623', '#ec7c13', '#de5a17', '#ffc23a', '#c4440f', '#f08c20', '#e8a52a'];
})();

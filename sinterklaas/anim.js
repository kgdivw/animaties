/* =====================================================================
   Wat beweegt: boom en bladeren, vlaggetjes, banier, luifelranden,
   fonteinwater, rook, lichtflikkering, en de personages met hun
   tijdlijn. Plus de lus en de bediening.
   ===================================================================== */
(function () {
  'use strict';
  const SK = window.SK, T = SK.Town;
  const { TAU, clamp, lerp, smooth, mix, rgba, rng, fbm, poly, lin, rad } = SK;
  const P3 = window.Puppet3D, CH = window.Characters;

  const CYCLE = 48;                 // seconden per lus
  const windN = SK.noise1(1234), gustN = SK.noise1(777);
  let WIND = 0.5;                   // 0..~1.5, gezet in draw()
  function windAt(t) {
    const base = 0.45 + (fbm(windN, t * 0.08, 3) - 0.5) * 0.9;
    const gust = Math.pow(smooth(0.62, 0.9, fbm(gustN, t * 0.05, 2)), 1.5) * 0.9;
    return Math.max(0.05, base + gust);
  }

  /* ------------------------------------------------------------ */
  /*  Boom linksvoor: takken + bladeren die in de wind wiegen       */
  /* ------------------------------------------------------------ */
  const BRANCHES = [
    { pts: [[52, 300], [112, 226], [190, 166], [282, 118], [382, 80], [482, 46], [592, 22], [700, 6], [800, -10]], w0: 34, w1: 3, k: 1 },
    { pts: [[36, 230], [62, 160], [96, 96], [130, 44], [160, -14]], w0: 30, w1: 4, k: 0.7 },
    { pts: [[58, 372], [118, 338], [186, 304], [248, 268], [302, 232], [340, 214]], w0: 15, w1: 2, k: 0.9 },
    { pts: [[282, 124], [326, 150], [372, 184], [414, 214], [440, 240]], w0: 8, w1: 1.5, k: 1.1 },
    { pts: [[482, 46], [530, 26], [590, 12], [650, 2], [700, -8]], w0: 7, w1: 1.5, k: 1.2 },
    { pts: [[190, 170], [214, 118], [246, 62], [280, 18], [300, -10]], w0: 9, w1: 2, k: 0.8 },
    { pts: [[382, 90], [418, 52], [468, 22], [520, 0]], w0: 7, w1: 1.5, k: 1 },
    { pts: [[112, 228], [150, 250], [190, 268], [222, 300], [236, 336]], w0: 7, w1: 1.5, k: 1.1 },
    { pts: [[592, 34], [630, 60], [660, 92], [690, 112]], w0: 4, w1: 1, k: 1.3 }
  ];
  // per punt een gewicht: hoe verder van de stam, hoe meer hij beweegt
  for (const b of BRANCHES) {
    b.wt = b.pts.map((p, i) => Math.pow(i / (b.pts.length - 1), 1.4) * b.k);
    b.cur = b.pts.map((p) => [p[0], p[1]]);
  }
  BRANCHES[3].base = [0, 3]; BRANCHES[4].base = [0, 5]; BRANCHES[5].base = [0, 2]; BRANCHES[6].base = [0, 3]; BRANCHES[7].base = [0, 1]; BRANCHES[8].base = [0, 7];
  BRANCHES[3].par = 0; BRANCHES[4].par = 0; BRANCHES[5].par = 0; BRANCHES[6].par = 0; BRANCHES[7].par = 0; BRANCHES[8].par = 0;

  // bladeren: vast aan een tak (b, i, f) met een offset
  const LEAVES = [];
  (function () {
    const r = rng(2024);
    const shadeSet = (dark) => SK.LEAF_COLS.map((c) => mix(c, '#2a0c04', dark));
    const sets = [shadeSet(0.5), shadeSet(0.22), shadeSet(0)];
    BRANCHES.forEach((b, bi) => {
      const n = b.pts.length;
      const count = Math.round((b.w0 > 20 ? 170 : 70) * (bi === 0 ? 2.2 : 1));
      for (let k = 0; k < count; k++) {
        const u = 0.18 + Math.pow(r(), 0.7) * 0.82;
        const fi = u * (n - 1), i = Math.min(n - 2, Math.floor(fi)), f = fi - i;
        const rad = 6 + r() * 40 * (0.5 + u);
        const a = r() * TAU;
        const ox = Math.cos(a) * rad, oy = Math.sin(a) * rad * 0.65 + 6 + r() * 12;
        const layer = r() < 0.3 ? 0 : r() < 0.55 ? 1 : 2;
        LEAVES.push({
          b: bi, i: i, f: f, ox: ox, oy: oy, layer: layer,
          s: 16 + r() * 16 + (layer === 2 ? 4 : 0),
          rot: r() * TAU, ph: r() * TAU, sp: 1.5 + r() * 2.5,
          spr: null, col: sets[layer][(r() * 7) | 0]
        });
      }
    });
    // dicht bladerdek in de linkerbovenhoek
    for (let k = 0; k < 260; k++) {
      const bi = r() < 0.5 ? 1 : 0, b = BRANCHES[bi];
      const i = (r() * 4) | 0, f = r();
      const layer = r() < 0.35 ? 0 : r() < 0.6 ? 1 : 2;
      LEAVES.push({
        b: bi, i: i, f: f, ox: (r() - 0.45) * 170, oy: (r() - 0.65) * 130, layer: layer,
        s: 18 + r() * 18, rot: r() * TAU, ph: r() * TAU, sp: 1.5 + r() * 2.5,
        col: sets[layer][(r() * 7) | 0]
      });
    }
    // de maan blijft vrij
    for (let k = LEAVES.length - 1; k >= 0; k--) {
      const L = LEAVES[k], b = BRANCHES[L.b], a = b.pts[L.i], c = b.pts[L.i + 1];
      const x = a[0] + (c[0] - a[0]) * L.f + L.ox, y = a[1] + (c[1] - a[1]) * L.f + L.oy;
      if (Math.hypot(x - 555, y - 127) < 96) LEAVES.splice(k, 1);
    }
    LEAVES.sort((a, b) => a.layer - b.layer);
    for (const L of LEAVES) L.spr = SK.leaf(L.col);
  })();

  function updateBranches(t) {
    for (let bi = 0; bi < BRANCHES.length; bi++) {
      const b = BRANCHES[bi];
      let px = 0, py = 0;
      if (b.par !== undefined) {           // zijtak volgt het punt van de hoofdtak waar hij aan zit
        const P = BRANCHES[b.par], j = b.base[1];
        px = P.cur[j][0] - P.pts[j][0]; py = P.cur[j][1] - P.pts[j][1];
      }
      for (let i = 0; i < b.pts.length; i++) {
        const w = b.wt[i], p = b.pts[i];
        const sway = Math.sin(t * 1.25 + p[0] * 0.006 + bi) * (0.5 + WIND * 0.8) + Math.sin(t * 2.9 + bi * 1.7) * 0.25 * WIND;
        b.cur[i][0] = p[0] + px + w * (WIND * 7 + sway * 4);
        b.cur[i][1] = p[1] + py + w * (sway * 7 + WIND * 3);
      }
    }
  }
  function drawBranches(ctx) {
    ctx.lineCap = 'round'; ctx.lineJoin = 'round';
    for (const b of BRANCHES) {
      const n = b.cur.length;
      for (let i = 0; i < n - 1; i++) {
        const w = lerp(b.w0, b.w1, i / (n - 1));
        ctx.strokeStyle = '#2a140c'; ctx.lineWidth = w;
        ctx.beginPath(); ctx.moveTo(b.cur[i][0], b.cur[i][1]); ctx.lineTo(b.cur[i + 1][0], b.cur[i + 1][1]); ctx.stroke();
      }
      // warm randlicht aan de onderkant (lantaarns en ramen)
      ctx.strokeStyle = 'rgba(200,110,50,.35)';
      ctx.lineWidth = Math.max(1, b.w0 * 0.18);
      ctx.beginPath();
      for (let i = 0; i < n; i++) { const p = b.cur[i], o = lerp(b.w0, b.w1, i / (n - 1)) * 0.35; if (i) ctx.lineTo(p[0], p[1] + o); else ctx.moveTo(p[0], p[1] + o); }
      ctx.stroke();
    }
  }
  function drawLeaves(ctx, t) {
    for (const L of LEAVES) {
      const b = BRANCHES[L.b], a = b.cur[L.i], c = b.cur[L.i + 1];
      const x = a[0] + (c[0] - a[0]) * L.f + L.ox, y = a[1] + (c[1] - a[1]) * L.f + L.oy;
      const fl = Math.sin(t * L.sp * (0.6 + WIND) + L.ph);
      ctx.save();
      ctx.translate(x + fl * 1.5 * WIND, y);
      ctx.rotate(L.rot + fl * 0.25 * (0.4 + WIND));
      ctx.scale(1, 0.75 + 0.25 * Math.cos(t * L.sp + L.ph));
      ctx.drawImage(L.spr, -L.s, -L.s, L.s * 2, L.s * 2);
      ctx.restore();
    }
  }
  function drawTrunk(ctx) {
    const pts = [[-30, 950], [-30, 200], [14, 205], [40, 228], [66, 282], [74, 330], [66, 420], [58, 520], [60, 640], [72, 760], [98, 850], [150, 915], [210, 950]];
    ctx.save();
    poly(ctx, pts);
    ctx.fillStyle = lin(ctx, -30, 0, 90, 0, [[0, '#120806'], [0.55, '#2a160c'], [0.85, '#4a2814'], [1, '#6a3a1c']]);
    ctx.fill();
    ctx.clip();
    // schorslijnen
    const r = rng(31);
    ctx.strokeStyle = 'rgba(10,4,2,.6)'; ctx.lineWidth = 1.6;
    for (let i = 0; i < 40; i++) {
      const x = -20 + r() * 80, y = 230 + r() * 700, l = 30 + r() * 80;
      ctx.beginPath(); ctx.moveTo(x, y); ctx.quadraticCurveTo(x + (r() - 0.5) * 8, y + l / 2, x + (r() - 0.5) * 6, y + l); ctx.stroke();
    }
    ctx.strokeStyle = 'rgba(230,140,70,.25)'; ctx.lineWidth = 2;
    for (let i = 0; i < 14; i++) {
      const y = 260 + r() * 640;
      ctx.beginPath(); ctx.moveTo(52 + (y > 700 ? (y - 700) * 0.2 : 0), y); ctx.lineTo(48 + (y > 700 ? (y - 700) * 0.2 : 0), y + 30 + r() * 40); ctx.stroke();
    }
    ctx.restore();
    // wortel
    ctx.fillStyle = '#1e0e08';
    poly(ctx, [[60, 900], [150, 930], [220, 950], [40, 950]]); ctx.fill();
  }

  /* vallende blaadjes */
  const FALL = [];
  (function () { const r = rng(55); for (let i = 0; i < 34; i++) FALL.push({ seed: r() * 1000, ph: r(), sp: 0.05 + r() * 0.05, x0: r() * 760, s: 9 + r() * 8, col: SK.LEAF_COLS[(r() * 7) | 0] }); })();
  function drawFalling(ctx, t) {
    for (const F of FALL) {
      const a = (t * F.sp + F.ph) % 1;               // levensloop 0..1
      const y = lerp(60, 930, a);
      const x = F.x0 + a * (260 + WIND * 200) + Math.sin(t * 1.3 + F.seed) * 30;
      const al = smooth(0, 0.05, a) * (1 - smooth(0.93, 1, a));
      ctx.save();
      ctx.globalAlpha = al;
      ctx.translate(x, y);
      ctx.rotate(t * 1.6 + F.seed);
      ctx.scale(Math.cos(t * 2.3 + F.seed), 1);
      ctx.drawImage(SK.leaf(F.col), -F.s, -F.s, F.s * 2, F.s * 2);
      ctx.restore();
    }
  }

  /* ------------------------------------------------------------ */
  /*  Vlaggetjeslijnen, banier, luifelranden                        */
  /* ------------------------------------------------------------ */
  const BUNT = [
    { a: [44, 476], b: [431, 500], sag: 34, n: 13 },
    { a: [182, 430], b: [431, 470], sag: 22, n: 8 },
    { a: [431, 474], b: [560, 488], sag: 12, n: 4 },
    { a: [556, 478], b: [1300, 470], sag: 44, n: 27 },
    { a: [1300, 472], b: [1366, 458], sag: 6, n: 2 }
  ];
  const BCOLS = ['#d4302a', '#f2b632', '#e8781e', '#c62034', '#f6cc4a'];
  function drawBunting(ctx, t) {
    for (let si = 0; si < BUNT.length; si++) {
      const S = BUNT[si];
      const sagNow = S.sag * (1 + Math.sin(t * 0.9 + si) * 0.04);
      const pt = (u) => [lerp(S.a[0], S.b[0], u), lerp(S.a[1], S.b[1], u) + Math.sin(u * Math.PI) * sagNow];
      ctx.strokeStyle = '#2a1a14'; ctx.lineWidth = 1.2;
      ctx.beginPath();
      for (let k = 0; k <= 20; k++) { const p = pt(k / 20); if (k) ctx.lineTo(p[0], p[1]); else ctx.moveTo(p[0], p[1]); }
      ctx.stroke();
      const len = Math.hypot(S.b[0] - S.a[0], S.b[1] - S.a[1]);
      const fw = Math.min(27, len / S.n * 0.85), fh = fw * 1.3;
      for (let i = 0; i < S.n; i++) {
        const u0 = (i + 0.1) / S.n, u1 = (i + 0.1) / S.n + fw / len;
        const p0 = pt(u0), p1 = pt(u1);
        const mx = (p0[0] + p1[0]) / 2;
        const sw = Math.sin(t * 2.2 + mx * 0.02 + si) * 0.35 * (0.4 + WIND) + WIND * 0.25;
        const flut = Math.sin(t * 7 + i * 1.3) * 0.08 * WIND;
        const tip = [mx + Math.sin(sw) * fh, (p0[1] + p1[1]) / 2 + Math.cos(sw) * fh];
        const col = BCOLS[(i + si * 2) % BCOLS.length];
        ctx.fillStyle = col;
        ctx.beginPath(); ctx.moveTo(p0[0], p0[1]);
        ctx.quadraticCurveTo((p0[0] + tip[0]) / 2 - flut * 20, (p0[1] + tip[1]) / 2, tip[0], tip[1]);
        ctx.lineTo(p1[0], p1[1]); ctx.closePath(); ctx.fill();
        ctx.fillStyle = 'rgba(40,10,20,.28)';
        ctx.beginPath(); ctx.moveTo((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2); ctx.lineTo(tip[0], tip[1]); ctx.lineTo(p1[0], p1[1]); ctx.closePath(); ctx.fill();
      }
    }
  }
  function drawBanner(ctx, t) {
    // stang
    ctx.strokeStyle = '#1e1414'; ctx.lineWidth = 3.5; ctx.lineCap = 'round';
    ctx.beginPath(); ctx.moveTo(1302, 400); ctx.lineTo(1388, 397); ctx.stroke();
    ctx.fillStyle = '#e8b54a'; ctx.beginPath(); ctx.arc(1302, 400, 3.5, 0, TAU); ctx.arc(1388, 397, 3.5, 0, TAU); ctx.fill();
    const x0 = 1318, x1 = 1370, y0 = 400, y1 = 532, notch = 26;
    const dx = (x, y) => {
      const k = (y - y0) / (y1 - y0);
      return Math.sin(y * 0.045 - t * 3.2) * 4 * k * (0.5 + WIND) + WIND * 12 * k * k;
    };
    const N = 14, L = [], R = [];
    for (let i = 0; i <= N; i++) {
      const y = lerp(y0, y1, i / N);
      L.push([x0 + dx(x0, y), y]); R.push([x1 + dx(x1, y), y]);
    }
    const tipY = y1 - notch;
    const mid = [(x0 + x1) / 2 + dx(0, tipY), tipY];
    const shape = L.concat([mid], R.slice().reverse());
    // verloop met schaduw in de golven
    ctx.save();
    poly(ctx, shape);
    ctx.fillStyle = '#c8202a'; ctx.fill();
    ctx.clip();
    for (let i = 0; i < N; i++) {
      const y = lerp(y0, y1, i / N);
      const sh = Math.cos(y * 0.045 - t * 3.2);
      ctx.fillStyle = sh > 0 ? 'rgba(255,170,90,' + (sh * 0.22) + ')' : 'rgba(40,0,20,' + (-sh * 0.3) + ')';
      ctx.fillRect(x0 - 30, y, 120, (y1 - y0) / N + 1);
    }
    // gele boorden
    ctx.strokeStyle = '#f2c03a'; ctx.lineWidth = 5;
    ctx.beginPath(); SK.curve(ctx, L.map((p) => [p[0] + 6, p[1]])); ctx.stroke();
    ctx.beginPath(); SK.curve(ctx, R.map((p) => [p[0] - 6, p[1]])); ctx.stroke();
    ctx.restore();
    ctx.strokeStyle = '#8a1018'; ctx.lineWidth = 1; poly(ctx, shape); ctx.stroke();
  }
  function drawValance(ctx, V, t) {
    const n = V.n * 2;
    for (let i = 0; i < n; i++) {
      const u0 = i / n, u1 = (i + 1) / n;
      const x0 = lerp(V.a[0], V.b[0], u0), y0 = lerp(V.a[1], V.b[1], u0);
      const x1 = lerp(V.a[0], V.b[0], u1), y1 = lerp(V.a[1], V.b[1], u1);
      const lift = Math.sin(t * 3 + i * 0.7) * 2 * WIND + WIND * 1.5;
      const red = Math.floor(i / 2) % 2 === 0;
      ctx.fillStyle = red ? '#c42a2c' : '#efe2d2';
      ctx.beginPath();
      ctx.moveTo(x0, y0 - 1);
      ctx.lineTo(x1, y1 - 1);
      ctx.lineTo(x1 + lift * 0.4, y1 + V.h * 0.55);
      ctx.quadraticCurveTo((x0 + x1) / 2 + lift, (y0 + y1) / 2 + V.h * 1.15 - lift * 0.3, x0 + lift * 0.4, y0 + V.h * 0.55);
      ctx.closePath();
      ctx.fill();
      ctx.fillStyle = 'rgba(30,6,16,.18)'; ctx.fill();
    }
    ctx.strokeStyle = '#7a1a1a'; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.moveTo(V.a[0], V.a[1] - 1); ctx.lineTo(V.b[0], V.b[1] - 1); ctx.stroke();
  }

  /* ------------------------------------------------------------ */
  /*  Fonteinwater, rook, gloed                                     */
  /* ------------------------------------------------------------ */
  function drawWater(ctx, t) {
    const cx = 988;
    ctx.save();
    ctx.lineCap = 'round';
    // spuitje bovenop + stralen uit de schalen
    const streams = [];
    for (let k = 0; k < 6; k++) { const a = -0.9 + k * 0.36; streams.push({ x0: cx + a * 8, y0: 580, vx: a * 14, up: 16, y1: 604, rx: 30 }); }
    for (let k = 0; k < 8; k++) { const s = k < 4 ? -1 : 1, j = k % 4; streams.push({ x0: cx + s * (30 + j * 0.5), y0: 605 + j * 0.6, vx: s * (6 + j * 2), up: 2, y1: 640, rx: 52 }); }
    for (let k = 0; k < 10; k++) { const s = k < 5 ? -1 : 1, j = k % 5; streams.push({ x0: cx + s * (52 - j * 3), y0: 641 + j * 1.2, vx: s * (9 + j * 2.2), up: 2, y1: 700, rx: 120 }); }
    ctx.globalCompositeOperation = 'lighter';
    for (let si = 0; si < streams.length; si++) {
      const S = streams[si];
      const pts = [];
      for (let i = 0; i <= 10; i++) {
        const u = i / 10;
        pts.push([S.x0 + S.vx * u, S.y0 - S.up * 4 * u * (1 - u) + (S.y1 - S.y0) * u * u]);
      }
      ctx.strokeStyle = 'rgba(170,200,255,.18)'; ctx.lineWidth = 2.6;
      ctx.beginPath(); SK.curve(ctx, pts); ctx.stroke();
      ctx.setLineDash([3, 7]); ctx.lineDashOffset = -t * 60 - si * 3;
      ctx.strokeStyle = 'rgba(235,245,255,.55)'; ctx.lineWidth = 1.2;
      ctx.beginPath(); SK.curve(ctx, pts); ctx.stroke();
      ctx.setLineDash([]);
    }
    ctx.restore();
    // rimpels in het bassin
    ctx.save();
    ctx.beginPath(); ctx.ellipse(cx, 701, 121, 12, 0, 0, TAU); ctx.clip();
    for (let k = 0; k < 5; k++) {
      const a = (t * 0.35 + k / 5) % 1;
      ctx.strokeStyle = 'rgba(200,220,255,' + (0.35 * (1 - a)).toFixed(3) + ')'; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.ellipse(cx, 702, 26 + a * 100, 3 + a * 9, 0, 0, TAU); ctx.stroke();
    }
    // warme weerspiegeling van de ramen in het water
    ctx.fillStyle = 'rgba(255,170,80,.22)';
    for (let k = 0; k < 7; k++) {
      const x = cx - 100 + k * 32 + Math.sin(t * 1.5 + k) * 3;
      ctx.fillRect(x, 696 + Math.sin(t * 2 + k * 2) * 1.5, 14, 1.4);
    }
    ctx.restore();
  }

  const SMOKE = [
    { x: 356, y: 150, sc: 0.8 }, { x: 465, y: 196, sc: 0.6 }, { x: 1473, y: 150, sc: 1 },
    { x: 1316, y: 228, sc: 0.6 }, { x: 656, y: 194, sc: 0.8 }
  ];
  function drawSmoke(ctx, t) {
    const spr = SK.glow('#8090b8', 1);
    ctx.save();
    for (let ci = 0; ci < SMOKE.length; ci++) {
      const S = SMOKE[ci];
      for (let k = 0; k < 9; k++) {
        const a = (t * 0.07 + k / 9 + ci * 0.13) % 1;
        const x = S.x + a * (40 + WIND * 90) * S.sc + Math.sin(a * 6 + k + t * 0.3) * 6;
        const y = S.y - a * 120 * S.sc;
        const r = (8 + a * 34) * S.sc;
        SK.drawGlow(ctx, spr, x, y, r, 0.16 * smooth(0, 0.12, a) * (1 - a));
      }
    }
    ctx.globalAlpha = 1;
    ctx.restore();
  }
  // roetwolkje uit de schoorsteen als er een Piet beneden landt
  function drawSootPuff(ctx, u) {
    if (u <= 0 || u >= 1) return;
    const c = T.CHIM_R, cx = (c.x0 + c.x1) / 2;
    const spr = SK.glow('#3a3440', 1);
    const r = rng(9);
    ctx.save();
    for (let k = 0; k < 14; k++) {
      const a = r() * TAU, sp = 0.4 + r() * 0.6;
      const x = cx + Math.cos(a) * 30 * u * sp + u * 30 * WIND;
      const y = c.top - 34 - u * 90 * sp - Math.abs(Math.sin(a)) * 20 * u;
      SK.drawGlow(ctx, spr, x, y, 10 + u * 40 * sp, 0.55 * (1 - u) * smooth(0, 0.08, u));
    }
    // vonkjes
    ctx.globalCompositeOperation = 'lighter';
    for (let k = 0; k < 10; k++) {
      const a = -Math.PI / 2 + (r() - 0.5) * 1.8;
      const d = u * (60 + r() * 60);
      ctx.globalAlpha = (1 - u) * 0.9;
      ctx.fillStyle = '#ffcf70';
      ctx.fillRect(cx + Math.cos(a) * d, c.top - 34 + Math.sin(a) * d + u * u * 40, 2, 2);
    }
    ctx.restore();
  }

  const TWINKLE = [[1515, 55, 1.4], [1205, 38, 1], [1408, 105, 0.9], [887, 45, 0.8], [1060, 78, 0.5], [760, 36, 0.6], [1600, 160, 0.5], [960, 120, 0.4], [1300, 130, 0.5]];
  function drawTwinkles(ctx, t) {
    ctx.save();
    ctx.globalCompositeOperation = 'lighter';
    const spr = SK.glow('#cfe0ff');
    for (let i = 0; i < TWINKLE.length; i++) {
      const s = TWINKLE[i], tw = 0.75 + 0.25 * Math.sin(t * (1.3 + i * 0.37) + i * 2);
      const R = 14 * s[2] * tw;
      SK.drawGlow(ctx, spr, s[0], s[1], R, 0.9);
      ctx.globalAlpha = 0.9 * tw;
      ctx.fillStyle = '#ffffff';
      ctx.beginPath();
      const L = 22 * s[2] * tw, w = 1.1 * s[2];
      ctx.moveTo(s[0] - L, s[1]); ctx.lineTo(s[0], s[1] - w); ctx.lineTo(s[0] + L, s[1]); ctx.lineTo(s[0], s[1] + w); ctx.closePath();
      ctx.moveTo(s[0], s[1] - L); ctx.lineTo(s[0] + w, s[1]); ctx.lineTo(s[0], s[1] + L); ctx.lineTo(s[0] - w, s[1]); ctx.closePath();
      ctx.fill();
      ctx.beginPath(); ctx.arc(s[0], s[1], 1.6 * s[2], 0, TAU); ctx.fill();
    }
    ctx.restore();
  }

  const flickN = SK.noise1(99);
  function drawLampGlows(ctx, t, bright) {
    ctx.save();
    ctx.globalCompositeOperation = 'lighter';
    const warm = SK.glow('#ffb04a', 1), core = SK.glow('#fff0c0');
    T.LAMPS.forEach((L, i) => {
      const f = 0.9 + 0.1 * flickN(t * 3 + i * 17);
      SK.drawGlow(ctx, warm, L.glowX, L.glowY, 230 * L.s * f, 0.45);
      SK.drawGlow(ctx, warm, L.glowX, L.glowY, 80 * L.s * f, 0.7);
      SK.drawGlow(ctx, core, L.glowX, L.glowY, 34 * L.s, 0.9 * f);
    });
    T.WALL_LAMPS.forEach((L, i) => {
      const f = 0.9 + 0.1 * flickN(t * 3.4 + i * 31 + 5);
      SK.drawGlow(ctx, warm, L.x, L.y, 80 * f, 0.5);
      SK.drawGlow(ctx, core, L.x, L.y, 16, 0.8 * f);
    });
    // gloed van de zolderkamer waar de Pieten binnenkomen
    if (bright > 0) {
      SK.drawGlow(ctx, warm, 1144, 405, 120, 0.55 * bright);
      SK.drawGlow(ctx, core, 1144, 405, 40, 0.22 * bright);
    }
    ctx.restore();
  }

  /* ------------------------------------------------------------ */
  /*  Personages en hun tijdlijn                                    */
  /* ------------------------------------------------------------ */
  const sint = CH.makeSint();
  const piet1 = CH.makePiet({ a: '#6a2a8a', b: '#f2b632', cap: '#5a2278', feather: '#9a3ad0', prop: 'sack' });
  const piet2 = CH.makePiet({ a: '#2a4aa8', b: '#f2b632', cap: '#203a8a', feather: '#f6d040', prop: 'gift' });
  const horse = CH.makeHorse();

  const HID = 230;     // zo ver onder de nok is iemand helemaal verdwenen
  const CH_TOP = T.CHIM_R.top - 6;
  // sleutels: [p, x, y(+ = omlaag t.o.v. nok), yaw]
  /* Sleutels: [p, x, y(+ = omlaag t.o.v. nok), yaw, (ease voor het segment ná deze sleutel: 'lin')].
     Op p = 0.25 staan ze precies zoals in de template: Piet 800, Piet 930, Sint 1060. */
  const HERO = 0.25;
  const TRACK = {
    // Sint te paard: yaw van het paard (kijkt bij 0 naar rechts). -π/2 = naar de kijker, +π/2 = van ons af
    horse: [
      [0.00, 812, HID, -Math.PI / 2], [0.025, 812, HID, -Math.PI / 2], [0.085, 812, 0, -Math.PI / 2], [0.10, 812, 0, -0.25],
      [0.105, 812, 0, -0.25, 'lin'], [HERO, 1075, 0, -0.25], [0.30, 1075, 0, -0.3],
      [0.78, 1075, 0, -0.3], [0.81, 1075, 0, -2.92], [0.92, 812, 0, -2.92], [0.94, 812, 0, -4.71],
      [0.995, 812, HID, -4.71], [1, 812, HID, -4.71]
    ],
    piet2: [
      [0.00, 740, HID, 0], [0.06, 740, HID, 0], [0.115, 740, 0, 0], [0.13, 740, 0, 0.9],
      [0.135, 740, 0, 0.9, 'lin'], [HERO, 930, 0, 0.9, 'lin'], [0.37, 1204, 0, 1.35], [0.38, 1204, 0, 1.2],
      { hop: [0.385, 0.43, 1204, 1234, 0, 'top'] },
      [0.43, 1234, 'top', 1.2], [0.45, 1234, 'top', 0.1], [0.47, 1234, 'top', 0.1], [0.53, 1234, 'in', 0.1],
      [0.72, 1234, 'in', 0.1], { pop: [0.72, 0.755] }, [0.755, 1234, 'top', 0.1], [0.765, 1234, 'top', -1.3],
      { hop: [0.765, 0.795, 1234, 1188, 'top', 0] }, [0.795, 1188, 0, -1.4, 'lin'],
      [0.885, 740, 0, -1.4], [0.905, 740, 0, -Math.PI], [0.955, 740, HID, -Math.PI], [1, 740, HID, -Math.PI]
    ],
    piet1: [
      [0.00, 682, HID, 0], [0.09, 682, HID, 0], [0.145, 682, 0, 0], [0.16, 682, 0, 0.9],
      [0.165, 682, 0, 0.9, 'lin'], [HERO, 800, 0, 0.9, 'lin'], [0.48, 1200, 0, 1.35], [0.49, 1200, 0, 1.2],
      { hop: [0.495, 0.535, 1200, 1234, 0, 'top'] },
      [0.535, 1234, 'top', 1.2], [0.55, 1234, 'top', 0.3], [0.575, 1234, 'top', 0.3], [0.63, 1234, 'in', 0.3],
      [0.77, 1234, 'in', 0.1], { pop: [0.77, 0.805] }, [0.805, 1234, 'top', 0.1], [0.815, 1234, 'top', -1.3],
      { hop: [0.815, 0.845, 1234, 1188, 'top', 0] }, [0.845, 1188, 0, -1.4, 'lin'],
      [0.93, 682, 0, -1.4], [0.945, 682, 0, -Math.PI], [0.995, 682, HID, -Math.PI], [1, 682, HID, -Math.PI]
    ]
  };
  // 'top' en 'in' omrekenen naar y t.o.v. de nok
  function yval(v, x) {
    if (v === 'top') return CH_TOP - T.ridgeY(x);
    if (v === 'in') return CH_TOP - T.ridgeY(x) + 175;
    return v;
  }
  // werk de sleutels uit tot een lijst segmenten
  function buildTrack(keys) {
    const K = [], specials = [];
    for (const k of keys) { if (Array.isArray(k)) K.push(k); else specials.push(k); }
    return { K: K, S: specials };
  }
  for (const n in TRACK) TRACK[n] = buildTrack(TRACK[n]);

  function evalTrack(tr, p, stride) {
    const K = tr.K;
    let i = 0;
    while (i < K.length - 2 && p > K[i + 1][0]) i++;
    const a = K[i], b = K[i + 1];
    const u = clamp((p - a[0]) / Math.max(1e-6, b[0] - a[0]), 0, 1);
    const isLin = a[4] === 'lin';
    const e = isLin ? u : u * u * (3 - 2 * u);
    const de = isLin ? 1 : 6 * u * (1 - u);
    let x = lerp(a[1], b[1], e);
    const ya = yval(a[2], a[1]), yb = yval(b[2], b[1]);
    let y = lerp(ya, yb, e);
    const yaw = lerp(a[3], b[3], e);
    // afgelegde weg → looppas-fase
    let dist = 0;
    for (let j = 0; j < i; j++) {
      const A = K[j], Bk = K[j + 1];
      dist += Math.abs(Bk[1] - A[1]) + Math.abs(yval(Bk[2], Bk[1]) - yval(A[2], A[1])) * 0.7;
    }
    dist += Math.abs(x - a[1]) + Math.abs(y - ya) * 0.7;
    const speed = (Math.abs(b[1] - a[1]) + Math.abs(yb - ya) * 0.7) / Math.max(1e-6, (b[0] - a[0]) * CYCLE) * de;
    let walk = clamp(speed / 22, 0, 1);
    let jump = 0, inChim = false, onTop = false, air = 0;
    // sprongen: boog + hurken vooraf en bij de landing
    for (const s of tr.S) {
      if (s.hop) {
        const h = s.hop;
        if (p >= h[0] - 0.012 && p <= h[1] + 0.01) {
          const v = clamp((p - h[0]) / (h[1] - h[0]), 0, 1);
          const ev = v * v * (3 - 2 * v);
          x = lerp(h[2], h[3], ev);
          const y0 = yval(h[4], h[2]), y1 = yval(h[5], h[3]);
          y = lerp(y0, y1, ev) - Math.sin(v * Math.PI) * 46;
          walk = 0;
          jump = (1 - smooth(0, 0.18, v)) * smooth(-0.6, 0, (p - h[0]) / (h[1] - h[0])) + smooth(0.85, 1, v) * (1 - smooth(1, 1.4, (p - h[0]) / (h[1] - h[0])));
          air = Math.sin(v * Math.PI);
        }
      }
      if (s.pop) {
        const h = s.pop;
        if (p >= h[0] && p <= h[1]) {
          const v = (p - h[0]) / (h[1] - h[0]);
          const yIn = yval('in', 1234), yTop = yval('top', 1234);
          // veer omhoog, een stuk boven de rand, en neerkomen
          const arc = v < 0.7 ? 1 - Math.pow(1 - v / 0.7, 2) : 1;
          const over = Math.sin(clamp(v / 0.85, 0, 1) * Math.PI) * 60;
          y = lerp(yIn, yTop, arc) - over;
          walk = 0; air = 1 - smooth(0.8, 1, v);
          jump = smooth(0.85, 1, v) * 0.8;
        }
      }
    }
    // in of op de schoorsteen?
    const topY = yval('top', 1234);
    if (Math.abs(x - 1234) < 30) {
      if (y > topY + 0.5) inChim = true; else onTop = true;
    }
    let ph = dist / stride * TAU;
    if (tr.phT) {                                  // fase uit de vooraf geïntegreerde tabel
      const f = clamp(p, 0, 1) * (tr.phT.length - 1), i0 = Math.floor(f), i1 = Math.min(tr.phT.length - 1, i0 + 1);
      ph = tr.phT[i0] + (tr.phT[i1] - tr.phT[i0]) * (f - i0);
    }
    return { x: x, y: y, yaw: yaw, walk: walk, ph: ph, jump: jump, air: air, inChim: inChim, onTop: onTop };
  }

  /* Looppas-fase per tijdlijn: integreer afgelegde weg / effectieve paslengte.
     De paslengte is gemeten aan het skelet (cm per pas) × schaal, ingekort door
     de kijkhoek (wie schuin naar ons toe loopt, zet in beeld kortere passen) en
     door hoeveel hij loopt (walk < 1 = kleinere passen). Zo staat de steunvoet stil. */
  function buildPhase(tr, strideCm, scale, axis) {
    const N = 6000, P = new Float32Array(N + 1);
    let prev = evalTrack(tr, 0, 1), ph = 0;
    for (let i = 1; i <= N; i++) {
      const c = evalTrack(tr, i / N, 1);
      const dd = Math.abs(c.x - prev.x) + Math.abs(c.y - prev.y) * 0.7;
      const f = axis === 'x' ? Math.abs(Math.cos(c.yaw)) : Math.abs(Math.sin(c.yaw));
      if (c.walk > 0.001 && dd < 40) ph += dd / (strideCm * scale * Math.max(0.35, f) * Math.max(0.3, c.walk)) * TAU;
      P[i] = ph; prev = c;
    }
    tr.phT = P;
  }
  const FEET = { piet_zak: ['ftR', 'ftL'], piet_pakje: ['ftR', 'ftL'], paard: ['legFRh', 'legFLh', 'legBRh', 'legBLh'] };
  const FOOT_REST = {};
  let phaseReady = false;
  function initPhase() {
    const C = window.Chars3D;
    const pz = (ph) => Poses.piet({ walk: 1, ph: ph, t: 0 }, 'sack');
    const pp = (ph) => Poses.piet({ walk: 1, ph: ph, t: 0 }, 'gift');
    const ph_ = (ph) => Poses.horse({ walk: 1, ph: ph, t: 0 });
    const s1 = C.measureStride('piet_zak', pz, FEET.piet_zak, 'z');
    const s2 = C.measureStride('piet_pakje', pp, FEET.piet_pakje, 'z');
    const sh = C.measureStride('paard', ph_, FEET.paard, 'x');
    for (const n in FEET) { C.pose(n, { rot: {}, off: {} }); FOOT_REST[n] = C.footY(n, FEET[n]); }
    SK.strides = { piet_zak: s1, piet_pakje: s2, paard: sh };
    console.log('paslengtes (cm)', SK.strides);
    buildPhase(TRACK.piet1, s1, 1.08, 'z');
    buildPhase(TRACK.piet2, s2, 1.1, 'z');
    buildPhase(TRACK.horse, sh, 0.85, 'x');
    phaseReady = true;
  }

  const ACT = (p, a, b) => smooth(a, a + 0.015, p) * (1 - smooth(b - 0.015, b, p));

  // draaisnelheid (rad/s) — het hoofd kijkt alvast de bocht in, de romp volgt
  const turnRate = (track, p, stride) => {
    const a = evalTrack(track, Math.max(0, p - 0.002), stride).yaw, b = evalTrack(track, Math.min(1, p + 0.002), stride).yaw;
    return (b - a) / (0.004 * CYCLE);
  };
  const use3D = () => window.Chars3D && Chars3D.ready && !SK.state.puppet;

  function charStates(p, t) {
    const S = [];
    const d3 = use3D();
    if (d3 && !phaseReady) initPhase();
    // het paard met Sint in het zadel
    const s = evalTrack(TRACK.horse, p, 110);
    const wave = ACT(p, 0.345, 0.5);
    const twist = ACT(p, 0.31, 0.54);
    S.push({
      ch: sint, model: 'paard', rider: true, z: 0, tr: s, scale: d3 ? 0.85 : 1, box: { w: 150, up: 300, down: 25, ol: 1.0 },
      st: { walk: s.walk, ph: s.ph, t: t, wave: wave, twist: twist, wind: WIND, turn: turnRate(TRACK.horse, p, 110),
            look: ACT(p, 0.52, 0.62) * 0.5 - ACT(p, 0.17, 0.27) * 0.3, nod: ACT(p, 0.52, 0.62) * 0.22 + wave * -0.05, tilt: wave * 0.08 },
      hst: { t: t, walk: s.walk, ph: s.ph, wind: WIND, lift: ACT(p, 0.36, 0.5), swish: 0.6,
             nod: Math.max(0, Math.sin((p - 0.43) / 0.07 * TAU)) * ACT(p, 0.43, 0.5) * 0.8,
             earFlick: Math.max(0, Math.sin(t * 0.9) - 0.85) * 6, look: ACT(p, 0.36, 0.5) * 0.3 }
    });
    const p2 = evalTrack(TRACK.piet2, p, 46);
    const gone2 = p > 0.52 && p < 0.999;
    piet2.J.gift.hidden = gone2;
    S.push({
      ch: piet2, model: 'piet_pakje', prop: 'gift', z: -14, tr: p2, scale: d3 ? 1.1 : 1.18, box: { w: 70, up: 175, down: 20 },
      st: { walk: p2.walk, ph: p2.ph, t: t, jump: p2.jump, air: p2.air, armsUp: ACT(p, 0.45, 0.535), wind: WIND, turn: turnRate(TRACK.piet2, p, 46), look: ACT(p, 0.88, 0.9) * 0.4, hideProp: gone2 }
    });
    const p1 = evalTrack(TRACK.piet1, p, 46);
    const gone1 = p > 0.62 && p < 0.999;
    piet1.J.sack.hidden = gone1;
    S.push({
      ch: piet1, model: 'piet_zak', prop: 'sack', z: -28, tr: p1, scale: d3 ? 1.08 : 1.15, box: { w: 70, up: 175, down: 20 },
      st: { walk: p1.walk, ph: p1.ph, t: t, jump: p1.jump, air: p1.air, armsUp: ACT(p, 0.80, 0.83), wind: WIND, turn: turnRate(TRACK.piet1, p, 46), hideProp: gone1 }
    });
    return S;
  }

  /* ------------------------------------------------------------ */
  /*  Binnenshuis: schimmen van de Pieten achter de verlichte ramen */
  /* ------------------------------------------------------------ */
  // kamers: knip-rechthoeken (de ramen), vloerhoogte en schaal van het silhouet
  const ROOMS = {
    attic: { clip: [[1114, 368, 60, 76]], floor: 452, s: 0.42 },
    ground: { clip: [[1072, 534, 56, 90], [1158, 534, 56, 90]], floor: 632, s: 0.56 }
  };
  // per Piet een reeks momenten: drop = uit de schoorsteen plonzen, walk, put = pakje neerzetten, wave
  const INSIDE = {
    piet2: { model: 'piet_pakje', prop: 'gift', segs: [
      { p: [0.534, 0.556], room: 'attic', kind: 'drop', x: 1150, dir: -1 },
      { p: [0.556, 0.578], room: 'attic', kind: 'walk', x0: 1150, x1: 1092 },
      { p: [0.585, 0.622], room: 'ground', kind: 'walk', x0: 1032, x1: 1100 },
      { p: [0.622, 0.648], room: 'ground', kind: 'put', x: 1100, dir: 1 },
      { p: [0.648, 0.700], room: 'ground', kind: 'walk', x0: 1100, x1: 1258, noProp: true }
    ] },
    piet1: { model: 'piet_zak', prop: 'sack', segs: [
      { p: [0.634, 0.656], room: 'attic', kind: 'drop', x: 1146, dir: 1 },
      { p: [0.656, 0.675], room: 'attic', kind: 'walk', x0: 1146, x1: 1206 },
      { p: [0.682, 0.705], room: 'ground', kind: 'walk', x0: 1256, x1: 1186 },
      { p: [0.705, 0.724], room: 'ground', kind: 'wave', x: 1186, dir: -1 },
      { p: [0.724, 0.768], room: 'ground', kind: 'walk', x0: 1186, x1: 1030 }
    ] }
  };
  const SIL = { col: 'rgb(40,13,5)', blur: 1.1, alpha: 0.88 };

  function drawHouseSilhouettes(ctx, p, t) {
    if (!use3D()) return;
    for (const key in INSIDE) {
      const I = INSIDE[key];
      const sg = I.segs.find((s) => p >= s.p[0] && p < s.p[1]);
      if (!sg) continue;
      const R = ROOMS[sg.room];
      const u = (p - sg.p[0]) / (sg.p[1] - sg.p[0]);
      const stride = ((SK.strides && SK.strides[I.model]) || 93) * R.s;
      const st = { t: t, wind: 0, walk: 0, ph: 0, hideProp: !!sg.noProp };
      let x, y = R.floor, yaw;
      if (sg.kind === 'walk') {
        x = lerp(sg.x0, sg.x1, u);
        const dir = Math.sign(sg.x1 - sg.x0);
        yaw = dir > 0 ? Math.PI / 2 : -Math.PI / 2;
        st.walk = 1;
        st.ph = Math.abs(x - sg.x0) / stride * TAU;
      } else if (sg.kind === 'drop') {
        // valt van boven in beeld, landt door de knieën en draait zich om
        x = sg.x;
        const fall = smooth(0, 0.5, u);
        y = R.floor - (1 - fall * fall) * 130;
        st.air = 1 - smooth(0.45, 0.55, u);
        st.jump = smooth(0.48, 0.56, u) * (1 - smooth(0.62, 0.85, u));
        yaw = lerp(0, sg.dir * Math.PI / 2, smooth(0.7, 1, u));
      } else if (sg.kind === 'put') {
        x = sg.x; yaw = sg.dir * Math.PI / 2;
        st.jump = Math.sin(Math.PI * clamp(u * 1.2, 0, 1)) * 0.75;
        st.hideProp = u > 0.55;
      } else if (sg.kind === 'wave') {
        x = sg.x; yaw = lerp(sg.dir * Math.PI / 2, 0, smooth(0, 0.25, u)) ;
        st.armsUp = smooth(0.15, 0.3, u) * (1 - smooth(0.75, 0.95, u));
        st.nod = Math.sin(u * TAU * 2) * 0.08;
      }
      Chars3D.pose(I.model, Poses.piet(st, I.prop));
      Chars3D.draw(ctx, I.model, { x: x, y: y, s: R.s, yaw: yaw, pitch: 0 },
        { w: 70, up: 175, down: 20, silhouette: Object.assign({ clip: R.clip }, SIL) });
    }
    // het neergezette pakje blijft als schim op de vensterbank staan tot het eind van de lus
    if (p >= 0.636) {
      ctx.save();
      ctx.beginPath(); for (const r of ROOMS.ground.clip) ctx.rect(r[0], r[1], r[2], r[3]); ctx.clip();
      if ('filter' in ctx) ctx.filter = 'blur(1.1px)';
      ctx.globalAlpha = SIL.alpha * smooth(0.636, 0.642, p);
      ctx.fillStyle = SIL.col;
      ctx.fillRect(1103, 607, 20, 17); ctx.fillRect(1107, 595, 12, 12);
      ctx.beginPath(); ctx.ellipse(1110, 593, 4, 2.5, -0.5, 0, TAU); ctx.ellipse(1117, 593, 4, 2.5, 0.5, 0, TAU); ctx.fill();
      ctx.restore();
    }
  }

  /* dev: schermpositie van de laagste voet over een stukje tijdlijn (moet stilstaan tijdens de steunfase) */
  SK.footTrace = function (idx, p0, p1, n) {
    const out = [], v = new THREE.Vector3();
    for (let i = 0; i <= n; i++) {
      const p = p0 + (p1 - p0) * i / n, c = charStates(p, p * CYCLE)[idx];
      if (c.rider) Chars3D.pose('paard', Poses.horse(c.hst)); else Chars3D.pose(c.model, Poses.piet(c.st, c.prop));
      const M = Chars3D.models[c.model]; M.root.updateMatrixWorld(true);
      let best = null;
      for (const b of FEET[c.model]) { M.bones[b].getWorldPosition(v); if (!best || v.y < best[1]) best = [b, v.y, v.x, v.z]; }
      const yaw = c.tr.yaw;
      out.push([+(p.toFixed(4)), best[0], +(c.tr.x + c.scale * (best[2] * Math.cos(yaw) + best[3] * Math.sin(yaw))).toFixed(1)]);
    }
    return out;
  };

  function drawChar(ctx, c, pass) {
    const tr = c.tr;
    // welke laag: achter het dak/schoorsteen of ervoor
    const front = tr.onTop;
    if ((pass === 'front') !== front) return;
    const y = T.ridgeY(tr.x) + tr.y;
    const view = { x: tr.x, y: y, s: c.scale, yaw: tr.yaw, pitch: -0.06 };
    if (use3D()) {
      if (c.rider) {
        Chars3D.pose('paard', Poses.horse(c.hst));
        Chars3D.pose('sint_rider', Poses.rider(c.st));
      } else Chars3D.pose(c.model, Poses.piet(c.st, c.prop));
      // neerzetten op de laagste voet (niet tijdens een sprong)
      const grounded = 1 - smooth(0.02, 0.15, Math.max(tr.air || 0, (tr.jump || 0) * 0.4));
      if (FOOT_REST[c.model] !== undefined && grounded > 0) {
        view.y -= (FOOT_REST[c.model] - Chars3D.footY(c.model, FEET[c.model])) * c.scale * grounded;
      }
      Chars3D.draw(ctx, c.model, view, c.box);
      return;
    }
    if (c.rider) view.yaw += Math.PI / 2;      // oude 2D-pop: Sint staand
    c.ch.pose(c.st);
    P3.draw(ctx, c.ch.root, view);
  }
  function drawRoofShadows(ctx, list) {
    ctx.save();
    for (const c of list) {
      const tr = c.tr;
      if (tr.inChim) continue;
      const onTop = tr.onTop;
      const baseY = onTop ? CH_TOP + 2 : T.ridgeY(tr.x) + 3;
      const lift = onTop ? Math.max(0, (CH_TOP - (T.ridgeY(tr.x) + tr.y))) : Math.max(0, -tr.y);
      if (!onTop && tr.y > 4) continue;
      const a = 0.35 * clamp(1 - lift / 70, 0, 1);
      ctx.fillStyle = 'rgba(20,6,14,' + a.toFixed(3) + ')';
      ctx.beginPath(); ctx.ellipse(tr.x + 4, baseY, 26 * c.scale, 5, 0, 0, TAU); ctx.fill();
    }
    ctx.restore();
  }

  function horseState(p, t) {
    const lift = ACT(p, 0.36, 0.5);
    const nod = Math.max(0, Math.sin((p - 0.43) / 0.07 * TAU)) * ACT(p, 0.43, 0.5) * 0.8 + ACT(p, 0.62, 0.72);
    const swish = Math.pow(smooth(0.55, 0.85, fbm(SK.noise1(5), t * 0.2, 2)), 1) * 1.2;
    const ef = Math.max(0, Math.sin(t * 0.9) - 0.85) * 6;
    return {
      t: t, lift: lift, nod: nod, swish: swish, wind: WIND, earFlick: ef,
      stomp: Math.max(0, Math.sin((p - 0.47) / 0.02 * Math.PI)) * ACT(p, 0.47, 0.49),
      look: lift * 0.25
    };
  }
  const HORSE_LIGHT = { sh: '#6a4a5a', shAmt: 0.42, hi: '#fff4dc', hiAmt: 0.35, ol: 'rgba(60,30,40,.4)', olw: 0.8 };
  function drawHorse(ctx, p, t) {
    const hx = 1342, hy = 750;
    ctx.fillStyle = 'rgba(20,8,16,.45)';
    ctx.beginPath(); ctx.ellipse(hx - 4, hy - 1, 110, 13, 0, 0, TAU); ctx.fill();
    const view = { x: hx, y: hy, s: 1, yaw: -2.84 + ACT(p, 0.36, 0.5) * 0.12, pitch: 0.13, light: HORSE_LIGHT };
    if (use3D()) {
      Chars3D.pose('paard', Poses.horse(horseState(p, t)));
      Chars3D.draw(ctx, 'paard', view, { w: 135, up: 200, down: 25, ol: 0.9 });
      return;
    }
    horse.pose(horseState(p, t));
    P3.draw(ctx, horse.root, view);
  }

  /* ------------------------------------------------------------ */
  /*  Voorgrond-props, vignet                                       */
  /* ------------------------------------------------------------ */
  function drawFrontProps(ctx) {
    T.drawLamp(ctx, T.LAMPS[0]);
    T.barrel(ctx, 62, 708, 84, 128);
    T.sack(ctx, 292, 716, 80, 78);
    T.gift(ctx, 368, 734, 46, 50, '#c8202a', '#f2c03a');
    T.barrel(ctx, 1468, 708, 64, 90);
    T.barrel(ctx, 1502, 712, 94, 96);
    T.gift(ctx, 1524, 686, 44, 26, '#c8202a', '#f2c03a');
    // tafel rechts met pakjes
    ctx.fillStyle = lin(ctx, 0, 682, 0, 752, [[0, '#9a5a30'], [1, '#3a1a0a']]);
    ctx.fillRect(1600, 684, 90, 66);
    ctx.fillStyle = '#c08050'; ctx.fillRect(1596, 680, 96, 6);
    T.gift(ctx, 1612, 654, 28, 26, '#2f7a46', '#f2c03a');
    T.gift(ctx, 1644, 660, 26, 20, '#f0b830', '#c8202a');
  }
  function drawVignette(ctx) {
    const B = SK.B;
    const cx = SK.VW / 2, cy = SK.VH * 0.48, R = Math.hypot(B.x1 - B.x0, B.y1 - B.y0) * 0.62;
    ctx.fillStyle = rad(ctx, cx, cy, R * 0.45, R, [[0, 'rgba(8,4,16,0)'], [0.7, 'rgba(8,4,16,.25)'], [1, 'rgba(8,4,16,.6)']]);
    ctx.fillRect(B.x0, B.y0, B.x1 - B.x0, B.y1 - B.y0);
    // warme nevel over het plein
    ctx.globalCompositeOperation = 'screen';
    ctx.fillStyle = rad(ctx, 900, 690, 10, 700, [[0, 'rgba(120,60,20,.22)'], [1, 'rgba(120,60,20,0)']]);
    ctx.fillRect(B.x0, 300, B.x1 - B.x0, B.y1 - 300);
    ctx.globalCompositeOperation = 'source-over';
    // korrel
    const r = rng(3);
    for (let i = 0; i < 2600; i++) {
      ctx.fillStyle = r() < 0.5 ? 'rgba(255,240,220,.035)' : 'rgba(0,0,0,.05)';
      ctx.fillRect(B.x0 + r() * (B.x1 - B.x0), B.y0 + r() * (B.y1 - B.y0), 1.5, 1.5);
    }
  }

  /* ------------------------------------------------------------ */
  /*  Turntable (C): personages los bekijken                        */
  /* ------------------------------------------------------------ */
  function drawTurntable(ctx, t) {
    const B = SK.B;
    ctx.fillStyle = '#1a1a2a'; ctx.fillRect(B.x0, B.y0, B.x1 - B.x0, B.y1 - B.y0);
    const yaw = t * 0.6;
    if (use3D()) {
      const wk = 0.5 + 0.5 * Math.sin(t * 0.3);
      const L3 = [['sint', 300, 1.9, Poses.sint({ t: t, walk: wk, ph: t * 4, wave: smooth(0.3, 0.6, Math.sin(t * 0.4)) }), { w: 85, up: 235, down: 25 }],
        ['piet_zak', 700, 2.2, Poses.piet({ t: t, walk: wk, ph: t * 5 }, 'sack'), { w: 70, up: 175, down: 20 }],
        ['piet_pakje', 1040, 2.2, Poses.piet({ t: t, walk: wk, ph: t * 5 }, 'gift'), { w: 70, up: 175, down: 20 }]];
      for (const L of L3) { Chars3D.pose(L[0], L[3]); Chars3D.draw(ctx, L[0], { x: L[1], y: 800, s: L[2], yaw: yaw, pitch: 0.05 }, L[4]); }
      Chars3D.pose('paard', Poses.horse({ t: t, walk: wk, ph: t * 4, swish: 1 }));
      Chars3D.draw(ctx, 'paard', { x: 1400, y: 800, s: 1.5, yaw: yaw + 1, pitch: 0.1 }, { w: 135, up: 200, down: 25 });
      return;
    }
    const list = [[sint, 330, 2], [piet1, 720, 2.2], [piet2, 1060, 2.2]];
    for (const L of list) {
      L[0].pose({ t: t, walk: 0.5 + 0.5 * Math.sin(t * 0.3), ph: t * 5, wave: L[0] === sint ? smooth(0.3, 0.6, Math.sin(t * 0.4)) : 0, armsUp: 0 });
      P3.draw(ctx, L[0].root, { x: L[1], y: 760, s: L[2], yaw: yaw, pitch: 0.05 });
    }
    horse.pose({ t: t, walk: 0.5 + 0.5 * Math.sin(t * 0.3), ph: t * 4, swish: 1 });
    P3.draw(ctx, horse.root, { x: 1400, y: 760, s: 1.6, yaw: yaw + 1, pitch: 0.1 });
  }

  /* ------------------------------------------------------------ */
  /*  Frame                                                         */
  /* ------------------------------------------------------------ */
  const ref = new Image(); ref.src = 'ref.png';
  const state = { t: 0, playing: true, speed: 1, overlay: 0, turntable: false };
  const qs = new URLSearchParams(location.search);
  if (qs.has('p')) state.t = parseFloat(qs.get('p')) * CYCLE;
  if (qs.has('o')) state.overlay = parseInt(qs.get('o'), 10);
  if (qs.has('pause')) state.playing = false;
  if (qs.has('c')) state.turntable = true;

  function draw(t) {
    const ctx = SK.mainCtx;
    SK.ctx = ctx;
    SK.setMainTransform();
    const p = (t % CYCLE) / CYCLE;
    WIND = windAt(t);
    if (state.turntable) { drawTurntable(ctx, t); return; }

    SK.renderLayer('back', 'v5', (g) => { T.drawSky(g); T.drawClouds(g); T.drawMoon(g); T.drawFarTown(g); }, 'saturate(1.2) contrast(1.06)');
    drawTwinkles(ctx, t);
    drawSmoke(ctx, t);

    const chars = charStates(p, t).sort((a, b) => a.z - b.z);
    for (const c of chars) drawChar(ctx, c, 'back');

    SK.renderLayer('town', 'v5', (g) => {
      SK.GLOWS.length = 0;
      T.drawLeftHouses(g); T.drawMainFacade(g); T.drawMainRoof(g); T.drawChimneyR(g); T.drawRightHouses(g);
    }, 'saturate(1.3) contrast(1.12) brightness(1.04)');
    drawRoofShadows(ctx, chars);
    for (const c of chars) drawChar(ctx, c, 'front');
    // roetwolkjes bij het landen
    drawSootPuff(ctx, (p - 0.525) / 0.06);
    drawSootPuff(ctx, (p - 0.625) / 0.06);
    ctx.save(); ctx.globalCompositeOperation = 'lighter';
    SK.renderLayer('glow', 'v5', (g) => T.drawWindowGlows(g));
    ctx.restore();
    drawHouseSilhouettes(ctx, p, t);

    SK.renderLayer('ground', 'v5', (g) => {
      T.drawSquare(g); T.drawFountain(g); T.drawAwningRight(g); T.drawStallLeft(g);
      for (let i = 1; i < T.LAMPS.length; i++) T.drawLamp(g, T.LAMPS[i]);
      for (const L of T.WALL_LAMPS) T.drawWallLamp(g, L);
    }, 'saturate(1.25) contrast(1.1)');
    drawValance(ctx, T.STALL_VAL, t);
    drawValance(ctx, T.AWN_VAL, t);
    drawWater(ctx, t);
    // (het paard loopt nu met Sint over het dak)
    drawBunting(ctx, t);
    drawBanner(ctx, t);
    SK.renderLayer('front', 'v5', (g) => { drawFrontProps(g); drawTrunk(g); }, 'saturate(1.2) contrast(1.08)');
    updateBranches(t);
    drawBranches(ctx);
    drawLeaves(ctx, t);
    drawFalling(ctx, t);
    const bright = smooth(0.53, 0.58, p) * (1 - smooth(0.9, 0.98, p));
    drawLampGlows(ctx, t, bright);
    SK.renderLayer('vignet', 'v1', (g) => drawVignette(g));

    if (state.overlay && ref.complete) {
      ctx.save();
      if (state.overlay === 1) { ctx.globalAlpha = 0.5; ctx.drawImage(ref, 0, 0, SK.VW, SK.VH); }
      else if (state.overlay === 2) { ctx.beginPath(); ctx.rect(0, 0, SK.VW / 2, SK.VH); ctx.clip(); ctx.drawImage(ref, 0, 0, SK.VW, SK.VH); }
      else if (state.overlay === 3) { ctx.drawImage(ref, 0, 0, SK.VW, SK.VH); }
      ctx.restore();
    }
  }
  SK.drawAt = (p) => { state.t = p * CYCLE; draw(state.t); };
  /* dev: render precies op toneelmaat en stuur naar de dev-server (_snaps/) */
  SK.snap = async function (name, p, overlay) {
    const c = SK.canvas, prevOv = state.overlay;
    c.width = SK.VW; c.height = SK.VH;
    SK.view = { scale: 1, ox: 0, oy: 0, dpr: 1 };
    SK.B = { x0: 0, x1: SK.VW, y0: 0, y1: SK.VH };
    for (const k in SK.layers) SK.layers[k].key = null;
    state.overlay = overlay || 0;
    state.t = p * CYCLE; draw(state.t);
    const url = c.toDataURL('image/png');
    state.overlay = prevOv;
    SK.resize();
    const r = await fetch('/save?name=' + encodeURIComponent(name), { method: 'POST', body: url });
    return r.ok ? 'saved ' + name : 'fail';
  };

  /* ---------------- lus en bediening ---------------- */
  const $ = (id) => document.getElementById(id);
  let last = performance.now(), frames = 0, acc = 0;
  /* dev: hele lus opnemen als losse frames (JPEG) naar de dev-server (_snaps/rec_0000.jpg …).
     Start zonder te wachten; voortgang in SK.rec. */
  SK.record = async function (fps, from, to, i0) {
    fps = fps || 25; from = from || 0; to = to === undefined ? CYCLE : to;
    const c = SK.canvas;
    SK.recording = true;
    c.width = SK.VW; c.height = SK.VH;
    SK.view = { scale: 1, ox: 0, oy: 0, dpr: 1 };
    SK.B = { x0: 0, x1: SK.VW, y0: 0, y1: SK.VH };
    for (const k in SK.layers) SK.layers[k].key = null;
    state.overlay = 0; state.turntable = false;
    const n = Math.round((to - from) * fps);
    SK.rec = { done: i0 || 0, total: n, t0: performance.now(), retries: 0 };
    try {
      for (let i = i0 || 0; i < n; i++) {
        state.t = from + i / fps;
        draw(state.t);
        const url = c.toDataURL('image/jpeg', 0.93);
        for (let tries = 0; ; tries++) {          // bij een haperende server opnieuw proberen
          try {
            const r = await fetch('/save?name=rec_' + String(i).padStart(4, '0') + '.jpg', { method: 'POST', body: url });
            if (r.ok) break;
          } catch (e) { if (tries >= 4) throw e; }
          SK.rec.retries++;
          await new Promise((res) => setTimeout(res, 1000));
        }
        SK.rec.done = i + 1;
      }
    } finally {
      SK.recording = false;
      SK.resize();
    }
    return SK.rec;
  };

  function loop(now) {
    if (SK.recording) { last = now; requestAnimationFrame(loop); return; }
    const dt = Math.min(0.1, (now - last) / 1000); last = now;
    if (state.playing) state.t += dt * state.speed;
    try { draw(state.t); } catch (e) { console.error(e); state.playing = false; throw e; }
    const p = (state.t % CYCLE) / CYCLE;
    $('bar').style.width = (p * 100).toFixed(2) + '%';
    // adaptieve resolutie
    acc += dt; frames++;
    if (frames >= 90) {
      const avg = acc / frames;
      if (avg > 0.034 && SK.quality > 0.6) { SK.quality -= 0.1; SK.resize(); }
      frames = 0; acc = 0;
    }
    requestAnimationFrame(loop);
  }
  window.addEventListener('resize', SK.resize);
  SK.resize();
  requestAnimationFrame(loop);

  const setPlay = () => { $('play').textContent = state.playing ? '❚❚' : '▶'; };
  $('play').onclick = () => { state.playing = !state.playing; setPlay(); };
  $('restart').onclick = () => { state.t = 0; };
  $('speed').onclick = () => { state.speed = state.speed === 1 ? 2 : state.speed === 2 ? 0.5 : 1; $('speed').textContent = state.speed + '×'; };
  $('ref').onclick = () => { state.overlay = (state.overlay + 1) % 4; };
  $('turn').onclick = () => { state.turntable = !state.turntable; };
  const track = $('track');
  const scrub = (e) => { const r = track.getBoundingClientRect(); state.t = clamp((e.clientX - r.left) / r.width, 0, 0.9999) * CYCLE; };
  let dragging = false;
  track.addEventListener('pointerdown', (e) => { dragging = true; scrub(e); });
  window.addEventListener('pointermove', (e) => { if (dragging) scrub(e); });
  window.addEventListener('pointerup', () => { dragging = false; });
  window.addEventListener('keydown', (e) => {
    if (e.code === 'Space') { state.playing = !state.playing; setPlay(); e.preventDefault(); }
    else if (e.key === 'r' || e.key === 'R') state.t = 0;
    else if (e.key === 'o' || e.key === 'O') state.overlay = (state.overlay + 1) % 4;
    else if (e.key === 'c' || e.key === 'C') state.turntable = !state.turntable;
    else if (e.key === 'ArrowRight') state.t += 1;
    else if (e.key === 'ArrowLeft') state.t = Math.max(0, state.t - 1);
  });
  setPlay();
  SK.state = state;
})();

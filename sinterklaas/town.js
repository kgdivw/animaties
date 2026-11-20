/* =====================================================================
   Het decor: lucht, maan, huizen, plein, kraam, fontein, lantaarns.
   Alles hier is statisch en wordt in cachelagen gebakken. Wat beweegt
   (boom, vlaggetjes, water, licht-flikkering, personages) zit in anim.js.
   Coördinaten volgen de template (1672 x 941).
   ===================================================================== */
(function () {
  'use strict';
  const SK = window.SK;
  const { TAU, mix, rgba, poly, lin, rad, rng, clamp } = SK;
  const T = SK.Town = {};
  SK.GLOWS = [];               // raamgloed, gevuld tijdens het bakken van de huizen

  /* ------------------------------------------------------------ */
  /*  Generieke bouwstenen                                          */
  /* ------------------------------------------------------------ */
  const GLASS = ['#fff6cf', '#ffd170', '#f09a35', '#c9661c'];

  function winPath(ctx, x, y, w, h, arch) {
    ctx.beginPath();
    if (arch) {
      const ah = Math.min(h * 0.5, w * 0.5 * arch);
      ctx.moveTo(x, y + h);
      ctx.lineTo(x, y + ah);
      ctx.ellipse(x + w / 2, y + ah, w / 2, ah, 0, Math.PI, TAU);
      ctx.lineTo(x + w, y + h);
    } else ctx.rect(x, y, w, h);
    ctx.closePath();
  }
  /* raam: o.arch (0..1 hoe rond), o.cols/rows (roedes), o.lit, o.frame, o.sill, o.curtain */
  T.win = function (ctx, x, y, w, h, o) {
    o = o || {};
    const fw = o.fw || Math.max(2, w * 0.07);
    const lit = o.lit === undefined ? 1 : o.lit;
    // kozijn
    winPath(ctx, x - fw, y - fw, w + fw * 2, h + fw * 2, o.arch);
    ctx.fillStyle = o.frame || '#3a2216'; ctx.fill();
    // glas met licht van binnen
    winPath(ctx, x, y, w, h, o.arch);
    const g = ctx.createRadialGradient(x + w / 2, y + h * 0.62, 0, x + w / 2, y + h * 0.55, Math.max(w, h) * 0.8);
    g.addColorStop(0, mix(GLASS[0], '#2a1a30', 1 - lit));
    g.addColorStop(0.35, mix(GLASS[1], '#2a1a30', 1 - lit));
    g.addColorStop(0.75, mix(GLASS[2], '#2a1a30', 1 - lit));
    g.addColorStop(1, mix(GLASS[3], '#1a1020', 1 - lit));
    ctx.fillStyle = g; ctx.fill();
    ctx.save(); ctx.clip();
    // gordijntjes / kamerdiepte
    if (o.curtain !== false) {
      ctx.fillStyle = lin(ctx, x, 0, x + w, 0, [[0, 'rgba(150,50,20,.55)'], [0.2, 'rgba(150,50,20,0)'], [0.8, 'rgba(150,50,20,0)'], [1, 'rgba(150,50,20,.55)']]);
      ctx.fillRect(x, y, w, h);
    }
    if (o.inside) o.inside(ctx, x, y, w, h);
    // roedes
    ctx.strokeStyle = o.frame || '#3a2216';
    ctx.lineWidth = fw * 0.55;
    ctx.beginPath();
    const cols = o.cols === undefined ? 2 : o.cols, rows = o.rows === undefined ? 2 : o.rows;
    for (let i = 1; i < cols; i++) { const xx = x + w * i / cols; ctx.moveTo(xx, y - 2); ctx.lineTo(xx, y + h); }
    const top = o.arch ? y + Math.min(h * 0.5, w * 0.5 * o.arch) : y;
    for (let j = 1; j < rows; j++) { const yy = top + (y + h - top) * j / rows; ctx.moveTo(x, yy); ctx.lineTo(x + w, yy); }
    if (o.arch && o.fan) {
      const ah = Math.min(h * 0.5, w * 0.5 * o.arch), cx = x + w / 2, cy = y + ah;
      for (let k = 1; k < o.fan; k++) {
        const a = Math.PI + Math.PI * k / o.fan;
        ctx.moveTo(cx, cy); ctx.lineTo(cx + Math.cos(a) * w / 2, cy + Math.sin(a) * ah);
      }
      ctx.moveTo(x, cy); ctx.lineTo(x + w, cy);
    }
    ctx.stroke();
    // glans
    ctx.fillStyle = 'rgba(255,255,240,.12)';
    ctx.fillRect(x, y, w * 0.18, h);
    ctx.restore();
    if (o.sill !== false) {
      ctx.fillStyle = lin(ctx, 0, y + h + fw, 0, y + h + fw + 5, [[0, o.sillCol || '#d8b48a'], [1, '#6a4a3a']]);
      ctx.fillRect(x - fw - 3, y + h + fw - 1, w + fw * 2 + 6, 5);
    }
    if (lit > 0.05) SK.GLOWS.push([x + w / 2, y + h * 0.55, Math.max(w, h) * 1.15, 0.55 * lit]);
  };

  /* bloembak met rood/geel/oranje bloemetjes */
  T.flowers = function (ctx, x, y, w, seed, o) {
    o = o || {};
    const r = rng(seed || 7);
    // uithangend groen
    ctx.fillStyle = '#1f3a1e';
    for (let i = 0; i < w / 5; i++) {
      const xx = x + r() * w, yy = y + 2 + r() * 6;
      ctx.beginPath(); ctx.ellipse(xx, yy + 4, 2.2, 4 + r() * 4, 0, 0, TAU); ctx.fill();
    }
    // bak
    ctx.fillStyle = lin(ctx, 0, y, 0, y + 9, [[0, o.box || '#6a3a1e'], [1, '#2e170c']]);
    ctx.fillRect(x, y, w, 9);
    ctx.fillStyle = 'rgba(255,200,120,.25)'; ctx.fillRect(x, y, w, 1.5);
    // blad
    for (let i = 0; i < w / 2.2; i++) {
      const xx = x + 1 + r() * (w - 2), yy = y - 1 - r() * 7;
      ctx.fillStyle = r() < 0.5 ? '#2b5a26' : '#3c7a2e';
      ctx.beginPath(); ctx.ellipse(xx, yy, 2.6, 2, r() * 3, 0, TAU); ctx.fill();
    }
    // bloemen
    const cols = o.cols || ['#ff3a22', '#ffcc33', '#ff8a1e', '#ff5050', '#ffe680', '#e82a5a'];
    for (let i = 0; i < w / 2.6; i++) {
      const xx = x + 1 + r() * (w - 2), yy = y - 2 - r() * 9;
      const c = cols[(r() * cols.length) | 0];
      ctx.fillStyle = c;
      ctx.beginPath(); ctx.arc(xx, yy, 1.4 + r() * 1.5, 0, TAU); ctx.fill();
      ctx.fillStyle = 'rgba(255,250,210,.7)';
      ctx.fillRect(xx - 0.5, yy - 0.8, 1, 1);
    }
  };

  /* bakstenen binnen de huidige clip */
  T.bricks = function (ctx, x0, y0, x1, y1, base, seed, o) {
    o = o || {};
    const r = rng(seed || 3), bh = o.h || 7, bw = o.w || 17;
    ctx.fillStyle = o.mortar || mix(base, '#1a0e10', 0.35);
    ctx.fillRect(x0, y0, x1 - x0, y1 - y0);
    for (let y = y0, row = 0; y < y1; y += bh, row++) {
      for (let x = x0 - (row & 1 ? bw / 2 : 0); x < x1; x += bw) {
        const v = r();
        ctx.fillStyle = v < 0.5 ? mix(base, '#2a1210', v * 0.5) : mix(base, '#e09a70', (v - 0.5) * 0.35);
        ctx.fillRect(x + 0.8, y + 0.8, bw - 1.6, bh - 1.6);
      }
    }
  };
  /* natuursteen-blokken */
  T.stones = function (ctx, x0, y0, x1, y1, base, seed, o) {
    o = o || {};
    const r = rng(seed || 5), bh = o.h || 15;
    ctx.fillStyle = base; ctx.fillRect(x0, y0, x1 - x0, y1 - y0);
    ctx.strokeStyle = mix(base, '#1d1018', 0.22); ctx.lineWidth = 0.8;
    for (let y = y0, row = 0; y < y1; y += bh, row++) {
      let x = x0 - r() * 20;
      while (x < x1) {
        const w = (o.w || 30) * (0.7 + r() * 0.7);
        const v = r();
        ctx.fillStyle = v < 0.5 ? rgba('#1a0c10', (0.5 - v) * 0.22) : rgba('#ffe0b0', (v - 0.5) * 0.16);
        ctx.fillRect(x, y, w, bh);
        ctx.strokeRect(x + 0.5, y + 0.5, w - 1, bh - 1);
        x += w;
      }
    }
  };
  /* dakpannen in rijen binnen de huidige clip */
  T.tiles = function (ctx, x0, y0, x1, y1, base, seed, o) {
    o = o || {};
    const r = rng(seed || 11), th = o.h || 9, tw = o.w || 13;
    const hl = o.hl || '#c46a5a';
    ctx.fillStyle = mix(base, '#120608', 0.4); ctx.fillRect(x0, y0, x1 - x0, y1 - y0);
    for (let y = y0, row = 0; y < y1 + th; y += th, row++) {
      const k = (y - y0) / Math.max(1, y1 - y0);
      for (let x = x0 - (row & 1 ? tw / 2 : 0); x < x1; x += tw) {
        const v = r();
        const c = mix(base, v < 0.5 ? '#1a0808' : hl, v < 0.5 ? (0.5 - v) * 0.5 : (v - 0.5) * 0.4);
        ctx.fillStyle = c;
        ctx.beginPath();
        ctx.moveTo(x + 0.6, y);
        ctx.lineTo(x + tw - 0.6, y);
        ctx.lineTo(x + tw - 0.6, y + th - 2);
        ctx.quadraticCurveTo(x + tw / 2, y + th + 1.6, x + 0.6, y + th - 2);
        ctx.closePath();
        ctx.fill();
        // maanlicht op de bovenkant van elke pan
        ctx.fillStyle = rgba(o.moon || '#ffcfa8', 0.10 + 0.12 * (1 - k));
        ctx.fillRect(x + 1, y, tw - 2, 1.3);
      }
    }
  };

  /* ------------------------------------------------------------ */
  /*  Lucht, maan, sterren, wolken                                  */
  /* ------------------------------------------------------------ */
  T.MOON = { x: 555, y: 127, r: 74 };
  T.drawSky = function (ctx) {
    const B = SK.B;
    ctx.fillStyle = lin(ctx, 0, B.y0, 0, 520, [[0, '#00112e'], [0.2, '#001a42'], [0.42, '#022a5c'], [0.58, '#0d4384'], [0.75, '#2a5c9c'], [1, '#4d6fa6']]);
    ctx.fillRect(B.x0, B.y0, B.x1 - B.x0, 560 - B.y0);
    // maangloed in de lucht (warm, groot en zacht)
    const M = T.MOON;
    ctx.save();
    ctx.globalCompositeOperation = 'lighter';
    SK.drawGlow(ctx, SK.glow('#c89a5a', 1), M.x, M.y, 420, 0.35);
    SK.drawGlow(ctx, SK.glow('#ffd9a0', 1), M.x, M.y, 190, 0.55);
    ctx.restore();
    // sterren
    const r = rng(42);
    for (let i = 0; i < 520; i++) {
      const x = B.x0 + r() * (B.x1 - B.x0), y = B.y0 + Math.pow(r(), 1.4) * (330 - B.y0);
      const d = Math.hypot(x - M.x, y - M.y);
      if (d < 120) continue;
      const s = r(), a = (0.25 + 0.75 * r()) * (1 - y / 360) * clamp((d - 120) / 140, 0, 1);
      ctx.fillStyle = 'rgba(' + (200 + (s * 55 | 0)) + ',' + (215 + (s * 40 | 0)) + ',255,' + a.toFixed(3) + ')';
      const sz = s < 0.9 ? 0.9 + s * 0.6 : 1.8;
      ctx.fillRect(x, y, sz, sz);
    }
  };

  T.drawClouds = function (ctx) {
    const blobs = [
      // [x, y, rx, ry, alpha]
      [1310, 196, 70, 14, 0.45], [1380, 186, 80, 18, 0.5], [1460, 200, 60, 14, 0.42], [1520, 215, 70, 12, 0.35],
      [1270, 214, 60, 10, 0.3], [1420, 226, 90, 12, 0.35], [1560, 240, 80, 14, 0.3], [1640, 205, 60, 12, 0.3],
      [250, 196, 60, 10, 0.4], [300, 205, 50, 9, 0.35], [215, 214, 40, 8, 0.3], [395, 172, 40, 8, 0.25],
      [700, 230, 60, 8, 0.2], [880, 248, 80, 9, 0.18]
    ];
    for (const b of blobs) {
      ctx.save();
      ctx.translate(b[0], b[1]); ctx.scale(1, b[3] / b[2]);
      ctx.fillStyle = rad(ctx, 0, -b[2] * 0.2, 0, b[2], [[0, rgba('#4f86c4', b[4])], [0.6, rgba('#2c63a6', b[4] * 0.55)], [1, rgba('#1c4f90', 0)]]);
      ctx.beginPath(); ctx.arc(0, 0, b[2], 0, TAU); ctx.fill();
      ctx.restore();
    }
  };

  T.drawMoon = function (ctx) {
    const M = T.MOON;
    ctx.save();
    ctx.beginPath(); ctx.arc(M.x, M.y, M.r, 0, TAU);
    ctx.fillStyle = rad(ctx, M.x - 18, M.y - 22, 4, M.r * 1.08, [[0, '#fff6d6'], [0.45, '#fde5a6'], [0.85, '#f6cc78'], [1, '#e8b25e']], M.x, M.y);
    ctx.fill();
    ctx.clip();
    // zeeën en kraters
    const maria = [[-22, -18, 22, 15, 0.22], [12, -28, 16, 11, 0.18], [20, 6, 24, 17, 0.2], [-12, 22, 18, 12, 0.18], [-36, 8, 10, 14, 0.14], [36, 30, 12, 9, 0.12], [0, 46, 14, 7, 0.12]];
    for (const m of maria) {
      ctx.fillStyle = rad(ctx, M.x + m[0], M.y + m[1], 0, m[2], [[0, rgba('#c89048', m[4])], [1, rgba('#c89048', 0)]]);
      ctx.beginPath(); ctx.ellipse(M.x + m[0], M.y + m[1], m[2], m[3], 0.3, 0, TAU); ctx.fill();
    }
    const r = rng(9);
    for (let i = 0; i < 26; i++) {
      const a = r() * TAU, d = Math.sqrt(r()) * M.r * 0.9, cr = 1.5 + r() * 5;
      const x = M.x + Math.cos(a) * d, y = M.y + Math.sin(a) * d;
      ctx.strokeStyle = rgba('#b88040', 0.22); ctx.lineWidth = 1;
      ctx.beginPath(); ctx.arc(x, y, cr, 0, TAU); ctx.stroke();
      ctx.strokeStyle = rgba('#fff8e0', 0.25);
      ctx.beginPath(); ctx.arc(x + 0.6, y + 0.6, cr, 0.2, 1.8); ctx.stroke();
    }
    // randverdonkering
    ctx.fillStyle = rad(ctx, M.x, M.y, M.r * 0.7, M.r, [[0, 'rgba(200,120,40,0)'], [1, 'rgba(190,110,40,.35)']]);
    ctx.fillRect(M.x - M.r, M.y - M.r, M.r * 2, M.r * 2);
    ctx.restore();
  };

  /* ------------------------------------------------------------ */
  /*  Verre huizen (blauwig, atmosferisch)                          */
  /* ------------------------------------------------------------ */
  T.drawFarTown = function (ctx) {
    const WALL = '#2c3e66', ROOF = '#1f2c4e', DARK = '#18213e';
    // verre daken links achter
    ctx.fillStyle = DARK;
    poly(ctx, [[400, 330], [440, 250], [500, 238], [575, 236], [580, 330]]); ctx.fill();
    ctx.fillStyle = '#1c2848';
    ctx.fillRect(512, 238, 18, 52); ctx.fillRect(552, 244, 18, 50);
    ctx.fillStyle = '#26345a'; ctx.fillRect(509, 234, 24, 6); ctx.fillRect(549, 240, 24, 6);
    // huis F1: puntgevel met schoorsteen
    ctx.fillStyle = lin(ctx, 0, 200, 0, 700, [[0, '#33456e'], [0.5, '#3a4a70'], [1, '#2b3655']]);
    poly(ctx, [[408, 700], [408, 298], [465, 212], [540, 300], [540, 700]]); ctx.fill();
    ctx.save(); poly(ctx, [[408, 700], [408, 298], [465, 212], [540, 300], [540, 700]]); ctx.clip();
    T.stones(ctx, 400, 210, 545, 700, '#3a4562', 81, { h: 14, w: 26 });
    ctx.fillStyle = 'rgba(14,18,40,.45)'; ctx.fillRect(400, 210, 145, 490);
    ctx.restore();
    ctx.strokeStyle = ROOF; ctx.lineWidth = 9; ctx.lineCap = 'round';
    ctx.beginPath(); ctx.moveTo(398, 312); ctx.lineTo(465, 208); ctx.lineTo(548, 312); ctx.stroke();
    ctx.fillStyle = '#26365c'; ctx.fillRect(457, 198, 16, 30); ctx.fillStyle = '#31446e'; ctx.fillRect(454, 195, 22, 5);
    T.win(ctx, 450, 292, 28, 34, { arch: 0.9, frame: '#1a2238', lit: 0.95, cols: 2, rows: 1, sillCol: '#5a6a8a' });
    T.win(ctx, 498, 378, 30, 46, { frame: '#1a2238', lit: 1, sillCol: '#5a6a8a' });
    T.win(ctx, 432, 378, 28, 46, { frame: '#1a2238', lit: 0.35, sillCol: '#5a6a8a' });
    T.win(ctx, 452, 572, 34, 66, { arch: 1, frame: '#1a2238', lit: 1, sillCol: '#5a6a8a', fan: 4 });
    T.win(ctx, 506, 572, 34, 66, { arch: 1, frame: '#1a2238', lit: 1, sillCol: '#5a6a8a', fan: 4 });
    T.win(ctx, 440, 470, 26, 40, { frame: '#1a2238', lit: 0.6, sillCol: '#5a6a8a' });
    T.win(ctx, 496, 470, 26, 40, { frame: '#1a2238', lit: 0.9, sillCol: '#5a6a8a' });
    // verre straat
    ctx.fillStyle = lin(ctx, 0, 650, 0, 712, [[0, '#2a3048'], [1, '#4a3a4c']]);
    ctx.fillRect(400, 655, 160, 60);

    // rechts achter (boven het dak uit)
    ctx.fillStyle = '#1e2c52';
    poly(ctx, [[1290, 340], [1300, 270], [1350, 250], [1395, 262], [1400, 340]]); ctx.fill();
    ctx.fillStyle = '#22325a';
    ctx.fillRect(1306, 236, 24, 66); ctx.fillRect(1364, 232, 20, 34);
    ctx.fillStyle = '#2c3d68'; ctx.fillRect(1302, 230, 32, 7); ctx.fillRect(1360, 227, 28, 6);
  };

  /* ------------------------------------------------------------ */
  /*  Linkerhuizen: baksteenhuis + trapgevel                        */
  /* ------------------------------------------------------------ */
  T.drawLeftHouses = function (ctx) {
    // ---- huis A (baksteen) ----
    const A = [[30, 700], [30, 338], [300, 338], [300, 700]];
    ctx.save(); poly(ctx, A); ctx.clip();
    T.bricks(ctx, 30, 330, 300, 700, '#7a3a26', 21);
    ctx.fillStyle = lin(ctx, 0, 338, 0, 700, [[0, 'rgba(20,8,20,.45)'], [0.3, 'rgba(20,8,20,.1)'], [1, 'rgba(20,8,20,.3)']]);
    ctx.fillRect(30, 338, 270, 362);
    ctx.restore();
    // dak A
    const RA = [[20, 345], [40, 205], [255, 214], [306, 345]];
    ctx.save(); poly(ctx, RA); ctx.clip();
    T.tiles(ctx, 0, 200, 310, 350, '#6e2a2c', 31);
    ctx.fillStyle = lin(ctx, 0, 205, 0, 345, [[0, 'rgba(30,10,30,.0)'], [1, 'rgba(30,10,30,.45)']]);
    ctx.fillRect(0, 200, 310, 150);
    ctx.restore();
    ctx.fillStyle = '#2a1416'; ctx.fillRect(18, 338, 290, 7);
    // dakkapel A
    ctx.fillStyle = '#5a3a3a'; poly(ctx, [[183, 312], [183, 282], [203, 266], [223, 282], [223, 312]]); ctx.fill();
    T.win(ctx, 190, 283, 26, 26, { lit: 0.95, cols: 2, rows: 1, sill: false });
    ctx.strokeStyle = '#3a1a1a'; ctx.lineWidth = 4; ctx.beginPath(); ctx.moveTo(178, 288); ctx.lineTo(203, 262); ctx.lineTo(228, 288); ctx.stroke();
    T.win(ctx, 104, 360, 46, 76, { lit: 1, cols: 2, rows: 3 });
    T.flowers(ctx, 96, 442, 62, 4);
    T.win(ctx, 222, 374, 36, 64, { lit: 1, cols: 2, rows: 3 });
    T.flowers(ctx, 216, 444, 48, 5);
    T.win(ctx, 52, 372, 26, 60, { lit: 0.8, cols: 1, rows: 3 });

    // ---- huis S: trapgevel van natuursteen ----
    const sx0 = 286, sx1 = 422, apx = 352;
    const G = [[sx0, 700], [sx0, 318]];
    const steps = 4, stw = (apx - 14 - sx0) / steps, sth = (318 - 196) / steps;
    for (let i = 0; i < steps; i++) { G.push([sx0 + i * stw, 318 - (i + 1) * sth]); G.push([sx0 + (i + 1) * stw, 318 - (i + 1) * sth]); }
    G.push([apx - 14, 182]); G.push([apx + 14, 182]);
    for (let i = steps - 1; i >= 0; i--) { G.push([sx1 - (i + 1) * stw, 318 - (i + 1) * sth]); G.push([sx1 - i * stw, 318 - (i + 1) * sth]); }
    G.push([sx1, 318]); G.push([sx1, 700]);
    ctx.save(); poly(ctx, G); ctx.clip();
    T.stones(ctx, sx0, 170, sx1, 700, '#8a6e70', 41, { h: 13, w: 26 });
    ctx.fillStyle = lin(ctx, sx0, 0, sx1, 0, [[0, 'rgba(255,190,120,.10)'], [1, 'rgba(20,10,40,.35)']]);
    ctx.fillRect(sx0, 170, sx1 - sx0, 530);
    ctx.restore();
    // afdekstenen op de trappen
    ctx.fillStyle = '#b8a0a0';
    for (let i = 0; i < steps; i++) {
      ctx.fillRect(sx0 + i * stw - 2, 318 - (i + 1) * sth - 3, stw + 3, 4);
      ctx.fillRect(sx1 - (i + 1) * stw - 1, 318 - (i + 1) * sth - 3, stw + 3, 4);
    }
    // schoorsteen op de top
    ctx.fillStyle = '#7a5a5a'; ctx.fillRect(332, 170, 40, 16);
    ctx.fillStyle = '#9a8080'; ctx.fillRect(328, 164, 48, 7);
    ctx.fillStyle = '#5a3a3a'; ctx.fillRect(342, 152, 12, 13); ctx.fillRect(356, 155, 11, 10);
    // banden
    ctx.fillStyle = '#a89090'; ctx.fillRect(sx0, 466, sx1 - sx0, 7); ctx.fillRect(sx0, 356, sx1 - sx0, 4);
    T.win(ctx, 338, 248, 30, 68, { arch: 1, lit: 1, cols: 2, rows: 2, fan: 3 });
    T.flowers(ctx, 330, 324, 46, 8);
    T.win(ctx, 306, 384, 32, 56, { arch: 1, lit: 1, cols: 2, rows: 2 });
    T.win(ctx, 366, 388, 32, 56, { arch: 1, lit: 1, cols: 2, rows: 2 });
    T.flowers(ctx, 300, 448, 44, 12);
    T.flowers(ctx, 360, 452, 46, 13);
    // benedenverdieping (grotendeels achter de kraam)
    T.win(ctx, 300, 520, 40, 90, { arch: 1, lit: 1, cols: 2, rows: 3, fan: 3 });
    T.win(ctx, 362, 524, 40, 86, { arch: 1, lit: 0.9, cols: 2, rows: 3, fan: 3 });
    T.win(ctx, 60, 500, 56, 90, { lit: 1, cols: 3, rows: 3 });
    T.win(ctx, 230, 500, 50, 90, { lit: 1, cols: 2, rows: 3 });
    ctx.fillStyle = 'rgba(30,14,20,.5)'; ctx.fillRect(30, 690, 392, 12);
  };

  /* ------------------------------------------------------------ */
  /*  Middengebouw: groot schilddak, dakkapellen, schoorstenen      */
  /* ------------------------------------------------------------ */
  T.ridgeY = (x) => 298 - (x - 578) / (1372 - 578) * 5;
  T.CHIM_R = { x0: 1192, x1: 1276, top: 228, bot: 320 };
  T.CHIM_L = { x0: 626, x1: 710, top: 228, bot: 322 };

  function chimney(ctx, c, seed) {
    const w = c.x1 - c.x0;
    ctx.save(); ctx.beginPath(); ctx.rect(c.x0, c.top, w, c.bot - c.top); ctx.clip();
    T.bricks(ctx, c.x0, c.top, c.x1, c.bot, '#8a4a3e', seed, { h: 7, w: 15 });
    ctx.fillStyle = lin(ctx, c.x0, 0, c.x1, 0, [[0, 'rgba(255,200,140,.18)'], [0.5, 'rgba(0,0,0,0)'], [1, 'rgba(20,6,20,.45)']]);
    ctx.fillRect(c.x0, c.top, w, c.bot - c.top);
    ctx.fillStyle = lin(ctx, 0, c.top, 0, c.top + 18, [[0, 'rgba(10,4,10,.45)'], [1, 'rgba(10,4,10,0)']]);
    ctx.fillRect(c.x0, c.top, w, 18);
    ctx.restore();
    // afdekplaat
    ctx.fillStyle = lin(ctx, 0, c.top - 8, 0, c.top + 2, [[0, '#c9a28a'], [1, '#6a4038']]);
    ctx.fillRect(c.x0 - 6, c.top - 8, w + 12, 10);
    // pijpjes
    const pw = 15, gap = (w - pw * 2) / 3;
    for (let i = 0; i < 2; i++) {
      const px = c.x0 + gap + i * (pw + gap);
      ctx.fillStyle = lin(ctx, px, 0, px + pw, 0, [[0, '#a8604a'], [1, '#4a2420']]);
      ctx.fillRect(px, c.top - 32, pw, 25);
      ctx.fillStyle = '#c08a70'; ctx.fillRect(px - 2, c.top - 35, pw + 4, 5);
      ctx.fillStyle = '#1a0a0a'; ctx.fillRect(px + 2, c.top - 35, pw - 4, 2);
    }
  }
  T.chimney = chimney;
  T.drawChimneyR = (ctx) => chimney(ctx, T.CHIM_R, 92);

  function dormer(ctx, cx, apex, eaveY, hw, wallBot, win, seed) {
    // muurtje
    const wall = [[cx - hw * 0.78, wallBot], [cx - hw * 0.78, eaveY - (eaveY - apex) * 0.08], [cx, apex + 10], [cx + hw * 0.78, eaveY - (eaveY - apex) * 0.08], [cx + hw * 0.78, wallBot]];
    ctx.save(); poly(ctx, wall); ctx.clip();
    T.stones(ctx, cx - hw, apex, cx + hw, wallBot, '#a07858', seed, { h: 12, w: 24 });
    ctx.fillStyle = rad(ctx, cx, (apex + wallBot) / 2 + 20, 4, hw * 1.2, [[0, 'rgba(255,200,120,.25)'], [1, 'rgba(30,10,30,.35)']]);
    ctx.fillRect(cx - hw, apex, hw * 2, wallBot - apex);
    ctx.restore();
    // dakje met pannen, links en rechts
    const th = 14;
    const L = [[cx, apex - 4], [cx - hw - 6, eaveY + 4], [cx - hw - 6 + th * 0.6, eaveY + 4 + th * 0.5], [cx, apex + th * 0.7]];
    const R = [[cx, apex - 4], [cx + hw + 6, eaveY + 4], [cx + hw + 6 - th * 0.6, eaveY + 4 + th * 0.5], [cx, apex + th * 0.7]];
    for (const side of [L, R]) {
      ctx.save(); poly(ctx, side); ctx.clip();
      T.tiles(ctx, cx - hw - 10, apex - 6, cx + hw + 10, eaveY + 14, '#7a2e30', seed + (side === L ? 1 : 2), { h: 6, w: 8 });
      ctx.restore();
    }
    // windveer
    ctx.strokeStyle = '#3c1e18'; ctx.lineWidth = 4; ctx.lineJoin = 'round';
    ctx.beginPath(); ctx.moveTo(cx - hw - 4, eaveY + 5); ctx.lineTo(cx, apex + 4); ctx.lineTo(cx + hw + 4, eaveY + 5); ctx.stroke();
    ctx.strokeStyle = 'rgba(255,190,140,.35)'; ctx.lineWidth = 1.2;
    ctx.beginPath(); ctx.moveTo(cx - hw - 4, eaveY + 2); ctx.lineTo(cx, apex + 1); ctx.lineTo(cx + hw + 4, eaveY + 2); ctx.stroke();
    if (win) T.win(ctx, win[0], win[1], win[2], win[3], win[4]);
  }

  T.drawMainRoof = function (ctx) {
    const roof = [[578, 298], [1372, 293], [1392, 474], [538, 474]];
    ctx.save(); poly(ctx, roof); ctx.clip();
    T.tiles(ctx, 530, 288, 1400, 480, '#62282e', 51, { h: 10, w: 14, hl: '#b05a4a' });
    // maan links: iets lichter, rechts en onder donkerder
    ctx.fillStyle = lin(ctx, 540, 0, 1390, 0, [[0, 'rgba(255,190,150,.06)'], [0.6, 'rgba(0,0,0,0)'], [1, 'rgba(20,6,26,.3)']]);
    ctx.fillRect(530, 288, 870, 192);
    ctx.fillStyle = lin(ctx, 0, 296, 0, 474, [[0, 'rgba(255,190,160,.12)'], [0.5, 'rgba(0,0,0,0)'], [1, 'rgba(20,6,20,.4)']]);
    ctx.fillRect(530, 288, 870, 192);
    ctx.restore();
    // nok en hoekkepers
    ctx.strokeStyle = '#4a1c20'; ctx.lineWidth = 6; ctx.lineCap = 'round';
    ctx.beginPath(); ctx.moveTo(576, 299); ctx.lineTo(1374, 294); ctx.stroke();
    ctx.strokeStyle = '#b5675a'; ctx.lineWidth = 1.6;
    ctx.beginPath(); ctx.moveTo(578, 296.5); ctx.lineTo(1372, 291.5); ctx.stroke();
    ctx.strokeStyle = '#4a1c20'; ctx.lineWidth = 5;
    ctx.beginPath(); ctx.moveTo(578, 299); ctx.lineTo(540, 472); ctx.stroke();
    // dakkapellen
    dormer(ctx, 642, 336, 408, 62, 474, [620, 402, 46, 56, { lit: 1, cols: 2, rows: 2 }], 61);
    dormer(ctx, 790, 300, 388, 80, 474, [764, 366, 52, 62, { lit: 1, cols: 2, rows: 3 }], 63);
    dormer(ctx, 935, 378, 440, 64, 474, [915, 428, 40, 38, { lit: 1, cols: 2, rows: 2 }], 65);
    dormer(ctx, 1143, 290, 436, 134, 474, [1114, 368, 60, 76, { lit: 1, cols: 2, rows: 3 }], 67);
    T.flowers(ctx, 758, 438, 64, 21);
    T.flowers(ctx, 1104, 452, 80, 22);
    T.win(ctx, 1218, 410, 26, 34, { lit: 0.85, cols: 1, rows: 2 });
    T.win(ctx, 1048, 410, 26, 34, { lit: 0.85, cols: 1, rows: 2 });
    // goot / dakrand
    ctx.fillStyle = lin(ctx, 0, 466, 0, 482, [[0, '#d4b490'], [0.5, '#9a7458'], [1, '#3a2018']]);
    ctx.fillRect(536, 468, 858, 14);
    // linkerschoorsteen (rechter wordt apart getekend: daar kruipen Pieten in)
    chimney(ctx, T.CHIM_L, 91);
  };

  T.drawMainFacade = function (ctx) {
    const x0 = 552, x1 = 1384, y0 = 480, y1 = 702;
    ctx.save(); ctx.beginPath(); ctx.rect(x0, y0, x1 - x0, y1 - y0); ctx.clip();
    T.stones(ctx, x0, y0, x1, y1, '#9a6a44', 71, { h: 15, w: 34 });
    // lichtval: warm van de lantaarns, schaduw onder de goot
    ctx.fillStyle = lin(ctx, 0, y0, 0, y0 + 40, [[0, 'rgba(25,8,15,.6)'], [1, 'rgba(25,8,15,0)']]);
    ctx.fillRect(x0, y0, x1 - x0, 40);
    ctx.globalCompositeOperation = 'lighter';
    for (const L of [[862, 545, 130], [1004, 545, 130], [700, 600, 160], [1150, 600, 160], [1290, 520, 120]]) {
      ctx.fillStyle = rad(ctx, L[0], L[1], 0, L[2], [[0, 'rgba(170,80,20,.5)'], [1, 'rgba(170,80,20,0)']]);
      ctx.fillRect(L[0] - L[2], L[1] - L[2], L[2] * 2, L[2] * 2);
    }
    ctx.globalCompositeOperation = 'source-over';
    ctx.restore();
    // plint
    ctx.fillStyle = lin(ctx, 0, 690, 0, 704, [[0, '#6a4632'], [1, '#2e1a14']]);
    ctx.fillRect(x0, 688, x1 - x0, 16);
    // stenen boog om de grote ramen
    const archStone = (x, y, w, h) => {
      ctx.fillStyle = '#c49a72';
      ctx.beginPath(); ctx.ellipse(x + w / 2, y + w / 2, w / 2 + 9, w / 2 + 9, 0, Math.PI, TAU); ctx.lineTo(x + w + 9, y + h); ctx.lineTo(x - 9, y + h); ctx.closePath(); ctx.fill();
      ctx.strokeStyle = 'rgba(60,30,20,.5)'; ctx.lineWidth = 1;
      for (let k = 0; k <= 8; k++) {
        const a = Math.PI + Math.PI * k / 8;
        ctx.beginPath();
        ctx.moveTo(x + w / 2 + Math.cos(a) * (w / 2 + 1), y + w / 2 + Math.sin(a) * (w / 2 + 1));
        ctx.lineTo(x + w / 2 + Math.cos(a) * (w / 2 + 9), y + w / 2 + Math.sin(a) * (w / 2 + 9));
        ctx.stroke();
      }
    };
    archStone(590, 530, 82, 112);
    archStone(722, 520, 112, 122);
    T.win(ctx, 590, 530, 82, 112, { arch: 1, lit: 1, cols: 3, rows: 3, fan: 4, inside: shopInside });
    T.win(ctx, 722, 520, 112, 122, { arch: 1, lit: 1, cols: 4, rows: 3, fan: 5, inside: shopInside });
    T.flowers(ctx, 584, 650, 94, 31);
    T.flowers(ctx, 712, 650, 132, 32);
    // deur
    archStone(896, 520, 72, 156);
    ctx.fillStyle = '#4a2410';
    ctx.beginPath(); ctx.moveTo(896, 676); ctx.lineTo(896, 556); ctx.ellipse(932, 556, 36, 36, 0, Math.PI, TAU); ctx.lineTo(968, 676); ctx.closePath(); ctx.fill();
    T.win(ctx, 902, 526, 60, 34, { arch: 1, lit: 1, cols: 1, rows: 1, fan: 4, sill: false, fw: 3 });
    ctx.fillStyle = lin(ctx, 900, 0, 964, 0, [[0, '#6a3416'], [0.5, '#5a2a12'], [1, '#3a1a0a']]);
    ctx.fillRect(900, 564, 64, 112);
    ctx.strokeStyle = '#2a1206'; ctx.lineWidth = 1.5;
    for (let x = 908; x < 964; x += 9) { ctx.beginPath(); ctx.moveTo(x, 566); ctx.lineTo(x, 676); ctx.stroke(); }
    ctx.strokeStyle = '#1a0a04'; ctx.lineWidth = 3; ctx.beginPath(); ctx.moveTo(932, 562); ctx.lineTo(932, 676); ctx.stroke();
    ctx.fillStyle = '#e8b54a'; ctx.beginPath(); ctx.arc(924, 622, 2.6, 0, TAU); ctx.arc(940, 622, 2.6, 0, TAU); ctx.fill();
    ctx.fillStyle = '#8a7060'; ctx.fillRect(884, 676, 96, 8); ctx.fillStyle = '#6a5040'; ctx.fillRect(878, 684, 108, 8);
    // rechthoekige ramen
    T.win(ctx, 1072, 534, 56, 90, { lit: 1, cols: 2, rows: 3 });
    T.win(ctx, 1158, 534, 56, 90, { lit: 1, cols: 2, rows: 3 });
    T.flowers(ctx, 1064, 634, 72, 33);
    T.flowers(ctx, 1150, 634, 72, 34);
    T.win(ctx, 1292, 556, 84, 126, { arch: 1, lit: 1, cols: 3, rows: 3, fan: 4, inside: shopInside });
    T.win(ctx, 1012, 560, 30, 60, { lit: 0.7, cols: 1, rows: 2 });
    // muurlampen-armen
    for (const x of [862, 1004]) {
      ctx.strokeStyle = '#1a1210'; ctx.lineWidth = 3;
      ctx.beginPath(); ctx.moveTo(x - 16, 520); ctx.quadraticCurveTo(x - 6, 512, x, 522); ctx.stroke();
    }
    // plantenbak, bankje, tonnetjes
    ctx.fillStyle = lin(ctx, 0, 660, 0, 700, [[0, '#a88a72'], [1, '#5a4434']]);
    ctx.fillRect(712, 660, 66, 40);
    T.flowers(ctx, 714, 656, 62, 35);
    ctx.fillStyle = '#5a3418'; ctx.fillRect(792, 664, 56, 6); ctx.fillRect(792, 676, 56, 4);
    ctx.fillRect(796, 670, 4, 30); ctx.fillRect(840, 670, 4, 30); ctx.fillRect(792, 654, 56, 5);
    T.barrel(ctx, 1150, 664, 30, 38);
    T.barrel(ctx, 1182, 666, 30, 36);
  };
  function shopInside(ctx, x, y, w, h) {
    // planken met pakjes achter het glas
    const r = rng((x * 7 + y) | 0);
    ctx.fillStyle = 'rgba(120,50,15,.45)';
    for (let k = 1; k <= 2; k++) ctx.fillRect(x, y + h * (0.45 + k * 0.18), w, 3);
    for (let i = 0; i < w / 9; i++) {
      const bx = x + 3 + r() * (w - 12), shelf = r() < 0.5 ? 1 : 2, bw = 6 + r() * 8, bh = 5 + r() * 8;
      const by = y + h * (0.45 + shelf * 0.18) - bh;
      ctx.fillStyle = ['rgba(200,40,30,.6)', 'rgba(230,170,40,.6)', 'rgba(60,120,60,.5)', 'rgba(170,40,90,.5)'][(r() * 4) | 0];
      ctx.fillRect(bx, by, bw, bh);
    }
  }

  /* ------------------------------------------------------------ */
  /*  Rechterhuizen                                                 */
  /* ------------------------------------------------------------ */
  T.drawRightHouses = function (ctx) {
    // ---- huis C: natuursteen met leien dak ----
    const W = [[1380, 702], [1380, 330], [1528, 330], [1528, 702]];
    ctx.save(); poly(ctx, W); ctx.clip();
    T.stones(ctx, 1380, 320, 1528, 702, '#86686a', 101, { h: 13, w: 28 });
    ctx.fillStyle = lin(ctx, 1380, 0, 1528, 0, [[0, 'rgba(30,10,40,.35)'], [1, 'rgba(255,190,130,.08)']]);
    ctx.fillRect(1380, 320, 148, 382);
    ctx.restore();
    // schoorsteen
    ctx.save(); ctx.beginPath(); ctx.rect(1446, 160, 54, 120); ctx.clip();
    T.bricks(ctx, 1446, 160, 1500, 280, '#7a4038', 103, { h: 7, w: 14 });
    ctx.restore();
    ctx.fillStyle = '#b08a78'; ctx.fillRect(1440, 152, 66, 9);
    // dak (leien, blauwig in het maanlicht)
    const R = [[1368, 338], [1455, 240], [1540, 334], [1520, 340], [1455, 268], [1392, 342]];
    ctx.save(); poly(ctx, R); ctx.clip();
    T.tiles(ctx, 1360, 236, 1545, 345, '#2e3a5e', 105, { h: 7, w: 10, hl: '#6a7aa8', moon: '#b8c8ff' });
    ctx.restore();
    // gevelveld onder het dak
    const GV = [[1392, 342], [1455, 268], [1520, 340]];
    ctx.save(); poly(ctx, GV); ctx.clip();
    T.stones(ctx, 1390, 260, 1522, 345, '#8e7070', 107, { h: 12, w: 22 });
    ctx.restore();
    T.win(ctx, 1442, 292, 28, 44, { arch: 1, lit: 1, cols: 2, rows: 2 });
    T.win(ctx, 1414, 392, 32, 64, { lit: 1, cols: 2, rows: 3 });
    T.win(ctx, 1478, 390, 32, 64, { lit: 1, cols: 2, rows: 3 });
    T.flowers(ctx, 1400, 466, 58, 41);
    T.flowers(ctx, 1470, 462, 54, 42);
    ctx.fillStyle = '#a88a8a'; ctx.fillRect(1380, 500, 148, 6);
    T.win(ctx, 1388, 596, 130, 92, { lit: 1, cols: 4, rows: 2, inside: shopInside });

    // ---- huis D: hoge trapgevel van baksteen ----
    const x0 = 1520, x1 = 1700, apx = 1602;
    const G = [[x0, 702], [x0, 330]];
    const steps = 5, stw = (apx - 22 - x0) / steps, sth = (330 - 92) / steps;
    for (let i = 0; i < steps; i++) { G.push([x0 + i * stw, 330 - (i + 1) * sth]); G.push([x0 + (i + 1) * stw, 330 - (i + 1) * sth]); }
    G.push([apx - 22, 72]); G.push([apx + 22, 72]);
    for (let i = steps - 1; i >= 0; i--) { G.push([apx + 22 + (steps - 1 - i) * stw, 92 + (steps - 1 - i) * sth]); G.push([apx + 22 + (steps - i) * stw, 92 + (steps - 1 - i) * sth]); }
    G.push([x1, 330]); G.push([x1, 702]);
    ctx.save(); poly(ctx, G); ctx.clip();
    T.bricks(ctx, x0, 60, x1, 702, '#86493e', 111, { h: 7, w: 17 });
    ctx.fillStyle = lin(ctx, x0, 0, x1, 0, [[0, 'rgba(30,8,30,.35)'], [0.5, 'rgba(255,180,120,.05)'], [1, 'rgba(30,8,30,.2)']]);
    ctx.fillRect(x0, 60, x1 - x0, 642);
    ctx.restore();
    ctx.fillStyle = '#c2a49a';
    for (let i = 0; i < steps; i++) {
      ctx.fillRect(x0 + i * stw - 2, 330 - (i + 1) * sth - 3, stw + 3, 5);
      ctx.fillRect(apx + 22 + (steps - 1 - i) * stw - 1, 92 + (steps - 1 - i) * sth - 3, stw + 3, 5);
    }
    ctx.fillRect(apx - 26, 68, 52, 6);
    ctx.fillRect(x0, 300, x1 - x0, 7); ctx.fillRect(x0, 486, x1 - x0, 9);
    T.win(ctx, 1584, 196, 40, 80, { arch: 1, lit: 1, cols: 2, rows: 3, fan: 3 });
    T.flowers(ctx, 1574, 284, 60, 51);
    T.win(ctx, 1560, 334, 40, 82, { arch: 1, lit: 1, cols: 2, rows: 3, fan: 3 });
    T.win(ctx, 1632, 334, 40, 82, { arch: 1, lit: 1, cols: 2, rows: 3, fan: 3 });
    T.flowers(ctx, 1546, 428, 130, 52);
    T.win(ctx, 1562, 514, 120, 166, { arch: 1, lit: 1, cols: 3, rows: 4, fan: 5, inside: shopInside });
    T.win(ctx, 1600, 130, 24, 34, { arch: 1, lit: 0.8, cols: 1, rows: 1 });
  };

  /* ------------------------------------------------------------ */
  /*  Plein: kinderkopjes in perspectief                            */
  /* ------------------------------------------------------------ */
  // lichtbronnen op de grond: [x, y, straal, sterkte]
  T.GROUND_LIGHTS = [
    [180, 830, 260, 0.9], [430, 750, 200, 0.75], [1292, 735, 200, 0.75], [555, 705, 120, 0.5],
    [630, 705, 150, 0.6], [778, 705, 170, 0.7], [1100, 705, 170, 0.65], [1185, 705, 150, 0.55],
    [990, 770, 280, 0.55], [1620, 700, 200, 0.7], [1450, 700, 160, 0.5], [250, 720, 220, 0.6], [860, 700, 120, 0.5]
  ];
  function groundLight(x, y) {
    let v = 0;
    for (const L of T.GROUND_LIGHTS) {
      const dx = (x - L[0]) / L[2], dy = (y - L[1]) / (L[2] * 0.5);
      v += L[3] * Math.exp(-(dx * dx + dy * dy) * 2.0);
    }
    v += 0.25 * Math.exp(-Math.pow((y - 760) / 70, 2));     // band licht van de gevels
    return 1 - Math.exp(-v * 1.4);
  }
  T.groundLight = groundLight;

  T.drawSquare = function (ctx) {
    const B = SK.B;
    const top = 698, bot = Math.max(VHB(), B.y1 + 2);
    ctx.fillStyle = '#21151f';
    ctx.fillRect(B.x0, top, B.x1 - B.x0, bot - top);
    const r = rng(77);
    let y = top + 4;
    while (y < bot) {
      const h = 7 + (y - top) * 0.085;          // rijen worden naar voren hoger
      const sw = h * 1.55;
      let x = B.x0 - r() * sw;
      while (x < B.x1) {
        const w = sw * (0.75 + r() * 0.5);
        const cx = x + w / 2, cy = y + h / 2;
        const L = groundLight(cx, cy);
        const v = r();
        const k = clamp(0.02 + L * 1.1 + (v - 0.5) * 0.2, 0, 1);
        const base = k < 0.5 ? mix('#3a2836', '#a07884', k * 2) : mix('#a07884', '#f2b08c', (k - 0.5) * 2);
        const gx = Math.max(0.8, h * 0.1);
        const jy = Math.sin(cx * 0.013 + y * 0.05) * h * 0.22 + (r() - 0.5) * h * 0.12;
        // ronde kei met licht van boven
        roundRect(ctx, x + gx, y + jy + gx, w - gx * 2, h - gx * 2, Math.min(h, w) * 0.45);
        const g = ctx.createRadialGradient(cx - w * 0.12, cy + jy - h * 0.22, 0, cx, cy + jy, Math.max(w, h) * 0.62);
        g.addColorStop(0, mix(base, '#ffe8cc', 0.22 + k * 0.25));
        g.addColorStop(0.5, base);
        g.addColorStop(1, mix(base, '#1a0e18', 0.5));
        ctx.fillStyle = g; ctx.fill();
        // natte glans
        if (k > 0.35) {
          ctx.fillStyle = rgba('#fff0d8', (k - 0.35) * 0.35);
          ctx.beginPath(); ctx.ellipse(cx - w * 0.08, cy + jy - h * 0.2, w * 0.25, h * 0.12, 0, 0, TAU); ctx.fill();
        }
        x += w;
      }
      y += h * 0.92;
    }
    // stoeprand langs de gevels
    ctx.fillStyle = lin(ctx, 0, 698, 0, 708, [[0, '#8a6a6a'], [1, '#3a2832']]);
    ctx.fillRect(B.x0, 698, B.x1 - B.x0, 7);
    // warme lichtplassen onder de lantaarns en ramen
    ctx.save();
    ctx.globalCompositeOperation = 'lighter';
    const spr = SK.glow('#ff9a40', 1);
    for (const L of T.GROUND_LIGHTS) SK.drawGlow(ctx, spr, L[0], L[1], L[2] * 1.0, L[3] * 0.5, 0.42);
    ctx.restore();
    // donkerder naar de voorgrond
    ctx.fillStyle = lin(ctx, 0, 700, 0, bot, [[0, 'rgba(40,40,110,.12)'], [0.45, 'rgba(0,0,0,0)'], [1, 'rgba(14,6,16,.55)']]);
    ctx.fillRect(B.x0, 700, B.x1 - B.x0, bot - 700);
    // liggende blaadjes
    const rl = rng(5);
    for (let i = 0; i < 70; i++) {
      const x = B.x0 + rl() * (B.x1 - B.x0), yy = 720 + Math.pow(rl(), 0.7) * (bot - 720);
      const sz = 7 + (yy - 700) * 0.07 + rl() * 6;
      ctx.save(); ctx.translate(x, yy); ctx.rotate(rl() * TAU); ctx.scale(1, 0.55);
      ctx.drawImage(SK.leaf(SK.LEAF_COLS[(rl() * 7) | 0]), -sz, -sz, sz * 2, sz * 2);
      ctx.restore();
    }
    // bladerhoop onder de boom
    for (let i = 0; i < 90; i++) {
      const x = -20 + Math.pow(rl(), 1.5) * 360, yy = 850 + rl() * 95;
      const sz = 14 + rl() * 14;
      ctx.save(); ctx.translate(x, yy); ctx.rotate(rl() * TAU); ctx.scale(1, 0.6);
      ctx.drawImage(SK.leaf(SK.mix(SK.LEAF_COLS[(rl() * 7) | 0], '#2a0c04', rl() * 0.4)), -sz, -sz, sz * 2, sz * 2);
      ctx.restore();
    }
  };
  function VHB() { return SK.VH + 2; }
  function roundRect(ctx, x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x + r, y); ctx.lineTo(x + w - r, y); ctx.quadraticCurveTo(x + w, y, x + w, y + r);
    ctx.lineTo(x + w, y + h - r); ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
    ctx.lineTo(x + r, y + h); ctx.quadraticCurveTo(x, y + h, x, y + h - r);
    ctx.lineTo(x, y + r); ctx.quadraticCurveTo(x, y, x + r, y); ctx.closePath();
  }
  T.roundRect = roundRect;

  /* ------------------------------------------------------------ */
  /*  Fontein (steen; het water zelf beweegt in anim.js)            */
  /* ------------------------------------------------------------ */
  T.FOUNT = { x: 988 };
  T.drawFountain = function (ctx) {
    const cx = 988;
    // schaduw op de keien
    ctx.fillStyle = 'rgba(20,8,20,.35)';
    ctx.beginPath(); ctx.ellipse(cx + 10, 770, 200, 24, 0, 0, TAU); ctx.fill();
    // brede onderste trede
    ctx.fillStyle = lin(ctx, 0, 752, 0, 776, [[0, '#a48a86'], [1, '#4e3a40']]);
    ctx.beginPath(); ctx.ellipse(cx, 764, 188, 18, 0, 0, Math.PI); ctx.lineTo(cx - 188, 754); ctx.ellipse(cx, 754, 188, 18, 0, Math.PI, 0, true); ctx.closePath(); ctx.fill();
    ctx.fillStyle = lin(ctx, cx - 188, 0, cx + 188, 0, [[0, '#9a807c'], [0.45, '#c8aaa0'], [1, '#806468']]);
    ctx.beginPath(); ctx.ellipse(cx, 754, 188, 18, 0, 0, TAU); ctx.fill();
    // bassinwand
    ctx.save();
    ctx.beginPath(); ctx.moveTo(cx - 130, 702); ctx.lineTo(cx - 132, 748); ctx.ellipse(cx, 748, 132, 15, 0, Math.PI, 0, true); ctx.lineTo(cx + 130, 702); ctx.closePath();
    ctx.clip();
    T.stones(ctx, cx - 135, 700, cx + 135, 766, '#8a6e6a', 121, { h: 16, w: 30 });
    ctx.fillStyle = lin(ctx, cx - 132, 0, cx + 132, 0, [[0, 'rgba(30,10,40,.5)'], [0.4, 'rgba(255,190,140,.12)'], [0.7, 'rgba(255,190,140,.05)'], [1, 'rgba(30,10,40,.55)']]);
    ctx.fillRect(cx - 135, 700, 270, 66);
    ctx.restore();
    // rand
    ctx.fillStyle = lin(ctx, 0, 690, 0, 714, [[0, '#d8bcb0'], [1, '#7a6062']]);
    ctx.beginPath(); ctx.ellipse(cx, 702, 136, 18, 0, 0, TAU); ctx.fill();
    // waterspiegel (wordt in anim.js nog bewogen)
    ctx.fillStyle = lin(ctx, 0, 690, 0, 712, [[0, '#2a3a5a'], [1, '#4a5a7a']]);
    ctx.beginPath(); ctx.ellipse(cx, 701, 122, 12.5, 0, 0, TAU); ctx.fill();
    // zuil
    ctx.fillStyle = lin(ctx, cx - 16, 0, cx + 16, 0, [[0, '#7a6064'], [0.4, '#c4a8a0'], [1, '#5a4248']]);
    ctx.beginPath();
    ctx.moveTo(cx - 20, 702); ctx.quadraticCurveTo(cx - 10, 680, cx - 12, 660); ctx.lineTo(cx - 9, 646);
    ctx.lineTo(cx + 9, 646); ctx.lineTo(cx + 12, 660); ctx.quadraticCurveTo(cx + 10, 680, cx + 20, 702); ctx.closePath(); ctx.fill();
    // onderste schaal
    bowl(ctx, cx, 640, 54, 9, 14);
    ctx.fillStyle = lin(ctx, cx - 10, 0, cx + 10, 0, [[0, '#7a6064'], [0.4, '#c4a8a0'], [1, '#5a4248']]);
    ctx.fillRect(cx - 8, 606, 16, 32);
    ctx.beginPath(); ctx.ellipse(cx, 620, 11, 4, 0, 0, TAU); ctx.fill();
    bowl(ctx, cx, 604, 32, 6, 9);
    // top
    ctx.fillStyle = lin(ctx, cx - 7, 0, cx + 7, 0, [[0, '#8a7074'], [0.4, '#d4b8b0'], [1, '#5a4248']]);
    ctx.beginPath(); ctx.moveTo(cx - 6, 602); ctx.quadraticCurveTo(cx - 9, 590, cx - 3, 584); ctx.lineTo(cx + 3, 584); ctx.quadraticCurveTo(cx + 9, 590, cx + 6, 602); ctx.closePath(); ctx.fill();
    ctx.beginPath(); ctx.arc(cx, 580, 5, 0, TAU); ctx.fill();
  };
  function bowl(ctx, cx, y, rx, ry, depth) {
    ctx.fillStyle = lin(ctx, cx - rx, 0, cx + rx, 0, [[0, '#6a5054'], [0.4, '#b89c94'], [1, '#4e383e']]);
    ctx.beginPath(); ctx.moveTo(cx - rx, y); ctx.quadraticCurveTo(cx - rx * 0.6, y + depth * 1.4, cx, y + depth * 1.3); ctx.quadraticCurveTo(cx + rx * 0.6, y + depth * 1.4, cx + rx, y); ctx.closePath(); ctx.fill();
    ctx.fillStyle = lin(ctx, 0, y - ry, 0, y + ry, [[0, '#dcc0b4'], [1, '#8a7070']]);
    ctx.beginPath(); ctx.ellipse(cx, y, rx, ry, 0, 0, TAU); ctx.fill();
    ctx.fillStyle = '#3a4a6a';
    ctx.beginPath(); ctx.ellipse(cx, y + 0.5, rx - 5, ry - 2.5, 0, 0, TAU); ctx.fill();
  }

  /* ------------------------------------------------------------ */
  /*  Kraam, tonnen, pakjes, zak                                    */
  /* ------------------------------------------------------------ */
  T.barrel = function (ctx, x, y, w, h) {
    ctx.fillStyle = 'rgba(20,8,16,.35)';
    ctx.beginPath(); ctx.ellipse(x + w / 2 + 4, y + h, w * 0.6, w * 0.12, 0, 0, TAU); ctx.fill();
    const bulge = w * 0.08;
    ctx.beginPath();
    ctx.moveTo(x + bulge, y); ctx.quadraticCurveTo(x - bulge, y + h / 2, x + bulge, y + h);
    ctx.lineTo(x + w - bulge, y + h); ctx.quadraticCurveTo(x + w + bulge, y + h / 2, x + w - bulge, y); ctx.closePath();
    ctx.fillStyle = lin(ctx, x, 0, x + w, 0, [[0, '#4a2412'], [0.3, '#b06a34'], [0.55, '#8a4a22'], [1, '#2e140a']]);
    ctx.fill();
    ctx.save(); ctx.clip();
    ctx.strokeStyle = 'rgba(30,12,4,.55)'; ctx.lineWidth = 1;
    for (let k = 1; k < 7; k++) {
      const xx = x + w * k / 7;
      ctx.beginPath(); ctx.moveTo(xx, y); ctx.quadraticCurveTo(xx + (xx - x - w / 2) * 0.12, y + h / 2, xx, y + h); ctx.stroke();
    }
    for (const f of [0.12, 0.3, 0.7, 0.88]) {
      const yy = y + h * f;
      ctx.fillStyle = '#2a2224'; ctx.fillRect(x - 4, yy - w * 0.035, w + 8, w * 0.07);
      ctx.fillStyle = 'rgba(255,200,150,.35)'; ctx.fillRect(x, yy - w * 0.035, w * 0.5, 1);
    }
    ctx.restore();
    ctx.fillStyle = lin(ctx, 0, y - w * 0.1, 0, y + w * 0.1, [[0, '#c08a5a'], [1, '#5a2e14']]);
    ctx.beginPath(); ctx.ellipse(x + w / 2, y, w / 2 - bulge, w * 0.1, 0, 0, TAU); ctx.fill();
    ctx.strokeStyle = '#2a2224'; ctx.lineWidth = 2; ctx.stroke();
  };
  T.gift = function (ctx, x, y, w, h, col, rib) {
    const d = Math.min(w, h) * 0.3;
    ctx.fillStyle = mix(col, '#ffe0b0', 0.25);
    poly(ctx, [[x, y], [x + d * 0.7, y - d * 0.5], [x + w + d * 0.7, y - d * 0.5], [x + w, y]]); ctx.fill();
    ctx.fillStyle = mix(col, '#1a0810', 0.4);
    poly(ctx, [[x + w, y], [x + w + d * 0.7, y - d * 0.5], [x + w + d * 0.7, y + h - d * 0.5], [x + w, y + h]]); ctx.fill();
    ctx.fillStyle = lin(ctx, x, y, x + w, y + h, [[0, mix(col, '#fff0d0', 0.15)], [1, mix(col, '#1a0810', 0.2)]]);
    ctx.fillRect(x, y, w, h);
    ctx.fillStyle = rib;
    ctx.fillRect(x + w * 0.42, y, w * 0.16, h);
    ctx.fillRect(x, y + h * 0.4, w, h * 0.16);
    poly(ctx, [[x + w * 0.42, y], [x + w * 0.42 + d * 0.7, y - d * 0.5], [x + w * 0.58 + d * 0.7, y - d * 0.5], [x + w * 0.58, y]]); ctx.fill();
    // strik
    ctx.beginPath(); ctx.ellipse(x + w * 0.5 + d * 0.3 - 5, y - d * 0.3 - 3, 6, 3.5, -0.5, 0, TAU); ctx.ellipse(x + w * 0.5 + d * 0.3 + 5, y - d * 0.3 - 3, 6, 3.5, 0.5, 0, TAU); ctx.fill();
  };
  T.sack = function (ctx, x, y, w, h) {
    ctx.fillStyle = 'rgba(20,8,16,.35)';
    ctx.beginPath(); ctx.ellipse(x + w / 2 + 6, y + h, w * 0.6, 7, 0, 0, TAU); ctx.fill();
    ctx.fillStyle = rad(ctx, x + w * 0.35, y + h * 0.45, 2, w * 0.8, [[0, '#ecd29a'], [0.5, '#c8a064'], [1, '#6a4a24']]);
    ctx.beginPath();
    ctx.moveTo(x + w * 0.38, y + h * 0.16);
    ctx.bezierCurveTo(x - w * 0.15, y + h * 0.3, x - w * 0.05, y + h, x + w * 0.5, y + h);
    ctx.bezierCurveTo(x + w * 1.05, y + h, x + w * 1.15, y + h * 0.3, x + w * 0.62, y + h * 0.16);
    ctx.closePath(); ctx.fill();
    ctx.beginPath(); ctx.moveTo(x + w * 0.38, y + h * 0.18); ctx.lineTo(x + w * 0.3, y); ctx.lineTo(x + w * 0.5, y + h * 0.06); ctx.lineTo(x + w * 0.7, y - h * 0.02); ctx.lineTo(x + w * 0.62, y + h * 0.18); ctx.closePath(); ctx.fill();
    ctx.fillStyle = '#e8b54a'; ctx.fillRect(x + w * 0.36, y + h * 0.14, w * 0.28, 4);
  };

  T.drawStallLeft = function (ctx) {
    // interieurgloed onder de luifel
    ctx.fillStyle = rad(ctx, 230, 640, 10, 200, [[0, 'rgba(255,190,100,.55)'], [1, 'rgba(255,150,60,0)']]);
    ctx.fillRect(60, 560, 360, 160);
    // achterwand en planken met pakjes
    ctx.fillStyle = '#3a1e12'; ctx.fillRect(90, 590, 300, 6);
    const r = rng(17);
    const cols = ['#c82a2a', '#f0b830', '#2f7a46', '#d84a8a', '#e86a22', '#f2e6d0'];
    for (let i = 0; i < 22; i++) {
      const w = 16 + r() * 22, h = 12 + r() * 16;
      const x = 120 + r() * 230, y = 700 - h - (r() < 0.4 ? 26 : 0) - r() * 20;
      T.gift(ctx, x, y, w, h, cols[(r() * cols.length) | 0], r() < 0.5 ? '#f6d04a' : '#f8f0e0');
    }
    // palen
    ctx.fillStyle = lin(ctx, 0, 0, 10, 0, [[0, '#7a4a24'], [1, '#3a1e0e']]);
    ctx.fillRect(104, 585, 9, 210); ctx.fillRect(346, 590, 9, 120);
    // toonbank
    ctx.fillStyle = lin(ctx, 0, 690, 0, 792, [[0, '#a0643a'], [0.1, '#7a4422'], [1, '#3a1c0c']]);
    ctx.fillRect(116, 692, 262, 100);
    ctx.fillStyle = '#c08050'; ctx.fillRect(110, 688, 274, 7);
    ctx.strokeStyle = 'rgba(30,10,4,.6)'; ctx.lineWidth = 1.2;
    for (let y = 712; y < 792; y += 16) { ctx.beginPath(); ctx.moveTo(116, y); ctx.lineTo(378, y); ctx.stroke(); }
    for (const x of [180, 250, 318]) { ctx.beginPath(); ctx.moveTo(x, 695); ctx.lineTo(x, 792); ctx.stroke(); }
    ctx.fillStyle = 'rgba(255,200,130,.18)'; ctx.fillRect(116, 695, 262, 3);
    // luifel (gestreept)
    const tl = [92, 490], tr = [400, 528], br = [414, 588], bl = [58, 584];
    const n = 10;
    for (let i = 0; i < n; i++) {
      const u0 = i / n, u1 = (i + 1) / n;
      const p0 = [SK.lerp(tl[0], tr[0], u0), SK.lerp(tl[1], tr[1], u0)], p1 = [SK.lerp(tl[0], tr[0], u1), SK.lerp(tl[1], tr[1], u1)];
      const q1 = [SK.lerp(bl[0], br[0], u1), SK.lerp(bl[1], br[1], u1)], q0 = [SK.lerp(bl[0], br[0], u0), SK.lerp(bl[1], br[1], u0)];
      const red = i % 2 === 0;
      ctx.fillStyle = lin(ctx, 0, p0[1], 0, q0[1], red ? [[0, '#8a1a1e'], [1, '#d23432']] : [[0, '#b8a8a8'], [1, '#f6ece0']]);
      poly(ctx, [p0, p1, q1, q0]); ctx.fill();
    }
    ctx.fillStyle = lin(ctx, 0, 488, 0, 520, [[0, 'rgba(10,4,20,.45)'], [1, 'rgba(10,4,20,0)']]);
    poly(ctx, [tl, tr, br, bl]); ctx.fill();
    ctx.fillStyle = '#5a2a18'; ctx.fillRect(86, 486, 12, 8);
  };
  T.STALL_VAL = { a: [58, 584], b: [414, 588], n: 10, h: 16 };     // luifelrand (beweegt in de wind)

  T.drawAwningRight = function (ctx) {
    const tl = [1366, 526], tr = [1528, 528], br = [1530, 578], bl = [1354, 584];
    const n = 7;
    for (let i = 0; i < n; i++) {
      const u0 = i / n, u1 = (i + 1) / n;
      const p0 = [SK.lerp(tl[0], tr[0], u0), SK.lerp(tl[1], tr[1], u0)], p1 = [SK.lerp(tl[0], tr[0], u1), SK.lerp(tl[1], tr[1], u1)];
      const q1 = [SK.lerp(bl[0], br[0], u1), SK.lerp(bl[1], br[1], u1)], q0 = [SK.lerp(bl[0], br[0], u0), SK.lerp(bl[1], br[1], u0)];
      const red = i % 2 === 0;
      ctx.fillStyle = lin(ctx, 0, p0[1], 0, q0[1], red ? [[0, '#8a1a1e'], [1, '#d63634']] : [[0, '#b8a8a8'], [1, '#f6ece0']]);
      poly(ctx, [p0, p1, q1, q0]); ctx.fill();
    }
  };
  T.AWN_VAL = { a: [1354, 584], b: [1530, 578], n: 7, h: 13 };

  /* ------------------------------------------------------------ */
  /*  Lantaarnpaal (zwart, sierlijk). Gloed komt uit anim.js.       */
  /* ------------------------------------------------------------ */
  T.LAMPS = [
    // x, voet, bovenkant lantaarn, schaal
    { x: 182, base: 838, top: 342, s: 1.25 },
    { x: 431, base: 750, top: 428, s: 0.9 },
    { x: 556, base: 702, top: 572, s: 0.55 },
    { x: 1292, base: 730, top: 460, s: 0.82 }
  ];
  T.drawLamp = function (ctx, L) {
    const x = L.x, s = L.s, base = L.base, top = L.top;
    const lanternH = 70 * s, postTop = top + lanternH + 6 * s;
    const iron = (x0, x1) => lin(ctx, x0, 0, x1, 0, [[0, '#2a2a34'], [0.35, '#5a5662'], [1, '#0c0c12']]);
    // voet
    ctx.fillStyle = 'rgba(15,6,14,.4)';
    ctx.beginPath(); ctx.ellipse(x + 6 * s, base, 26 * s, 6 * s, 0, 0, TAU); ctx.fill();
    ctx.fillStyle = iron(x - 18 * s, x + 18 * s);
    poly(ctx, [[x - 18 * s, base], [x - 14 * s, base - 14 * s], [x - 9 * s, base - 22 * s], [x - 8 * s, base - 60 * s], [x + 8 * s, base - 60 * s], [x + 9 * s, base - 22 * s], [x + 14 * s, base - 14 * s], [x + 18 * s, base]]);
    ctx.fill();
    // paal
    ctx.fillStyle = iron(x - 5 * s, x + 5 * s);
    ctx.fillRect(x - 4.5 * s, postTop, 9 * s, base - 60 * s - postTop);
    for (const f of [0.08, 0.5]) {
      const yy = postTop + (base - 60 * s - postTop) * f;
      ctx.fillStyle = iron(x - 8 * s, x + 8 * s);
      ctx.fillRect(x - 7 * s, yy, 14 * s, 6 * s);
    }
    // krulletjes onder de lantaarn
    ctx.strokeStyle = '#1a1a22'; ctx.lineWidth = 2.2 * s;
    ctx.beginPath();
    ctx.moveTo(x, postTop + 14 * s); ctx.bezierCurveTo(x - 20 * s, postTop + 10 * s, x - 22 * s, postTop - 4 * s, x - 12 * s, postTop - 2 * s);
    ctx.moveTo(x, postTop + 14 * s); ctx.bezierCurveTo(x + 20 * s, postTop + 10 * s, x + 22 * s, postTop - 4 * s, x + 12 * s, postTop - 2 * s);
    ctx.stroke();
    // lantaarn: glas
    const gw = 20 * s, gt = top + 16 * s, gb = top + lanternH - 8 * s;
    ctx.fillStyle = rad(ctx, x, (gt + gb) / 2 + 4 * s, 1, gw * 1.4, [[0, '#fffbe6'], [0.35, '#ffe39a'], [0.8, '#ffb04a'], [1, '#e0802a']]);
    poly(ctx, [[x - gw, gt], [x + gw, gt], [x + gw * 0.7, gb], [x - gw * 0.7, gb]]); ctx.fill();
    ctx.strokeStyle = '#121218'; ctx.lineWidth = 2.4 * s;
    ctx.beginPath(); ctx.moveTo(x, gt); ctx.lineTo(x, gb); ctx.stroke();
    ctx.lineWidth = 3 * s; poly(ctx, [[x - gw, gt], [x + gw, gt], [x + gw * 0.7, gb], [x - gw * 0.7, gb]]); ctx.stroke();
    // kap
    ctx.fillStyle = iron(x - gw * 1.3, x + gw * 1.3);
    poly(ctx, [[x - gw * 1.3, gt + 1], [x, top], [x + gw * 1.3, gt + 1]]); ctx.fill();
    ctx.fillRect(x - gw * 1.3, gt - 2 * s, gw * 2.6, 4 * s);
    ctx.beginPath(); ctx.arc(x, top - 2 * s, 4 * s, 0, TAU); ctx.fill();
    ctx.fillRect(x - gw * 0.8, gb, gw * 1.6, 5 * s);
    ctx.fillRect(x - 5 * s, gb + 4 * s, 10 * s, postTop - gb - 2 * s);
    L.glowX = x; L.glowY = (gt + gb) / 2; L.glowR = gw;
  };
  T.WALL_LAMPS = [{ x: 862, y: 540 }, { x: 1004, y: 540 }];
  T.drawWallLamp = function (ctx, L) {
    const x = L.x, y = L.y;
    ctx.fillStyle = rad(ctx, x, y + 2, 1, 14, [[0, '#fffbe6'], [0.5, '#ffd27a'], [1, '#e88a2a']]);
    poly(ctx, [[x - 9, y - 8], [x + 9, y - 8], [x + 7, y + 12], [x - 7, y + 12]]); ctx.fill();
    ctx.strokeStyle = '#141418'; ctx.lineWidth = 1.8; ctx.stroke();
    ctx.beginPath(); ctx.moveTo(x, y - 8); ctx.lineTo(x, y + 12); ctx.stroke();
    ctx.fillStyle = '#1a1a20';
    poly(ctx, [[x - 12, y - 8], [x, y - 18], [x + 12, y - 8]]); ctx.fill();
    ctx.fillRect(x - 8, y + 12, 16, 4);
  };

  /* verre gloed rond de lichtbronnen (raam-sprites) — in een cachelaag */
  T.drawWindowGlows = function (ctx) {
    ctx.save();
    ctx.globalCompositeOperation = 'lighter';
    const spr = SK.glow('#ff9a3a', 1);
    for (const g of SK.GLOWS) SK.drawGlow(ctx, spr, g[0], g[1], g[2] * 1.3, g[3] * 0.8);
    ctx.globalAlpha = 1;
    ctx.restore();
  };
})();

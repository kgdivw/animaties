/* =====================================================================
   Puppet3D — een piepkleine 3D-"poppenkast" voor canvas 2D.
   Figuren bestaan uit een skelet (nodes met rotatie) met daaraan
   eenvoudige vormen: ellipsoïde, capsule, afgeknotte kegel, doos,
   kaart (plat vlak) en buis. Elke frame: pose zetten → alles naar
   wereldruimte → orthografisch projecteren → sorteren op diepte →
   tekenen met verlopen die het licht volgen. Zo kunnen de personages
   vrij draaien en toch dezelfde getekende stijl houden als het decor.
   Model-assen: x rechts, y omhoog, z naar de kijker.
   ===================================================================== */
(function () {
  'use strict';
  const TAU = Math.PI * 2;

  /* ---------- 3x3 matrices (rij-major) ---------- */
  const I3 = [1, 0, 0, 0, 1, 0, 0, 0, 1];
  function mul(A, B) {
    return [
      A[0] * B[0] + A[1] * B[3] + A[2] * B[6], A[0] * B[1] + A[1] * B[4] + A[2] * B[7], A[0] * B[2] + A[1] * B[5] + A[2] * B[8],
      A[3] * B[0] + A[4] * B[3] + A[5] * B[6], A[3] * B[1] + A[4] * B[4] + A[5] * B[7], A[3] * B[2] + A[4] * B[5] + A[5] * B[8],
      A[6] * B[0] + A[7] * B[3] + A[8] * B[6], A[6] * B[1] + A[7] * B[4] + A[8] * B[7], A[6] * B[2] + A[7] * B[5] + A[8] * B[8]
    ];
  }
  function ap(M, v) {
    return [M[0] * v[0] + M[1] * v[1] + M[2] * v[2], M[3] * v[0] + M[4] * v[1] + M[5] * v[2], M[6] * v[0] + M[7] * v[1] + M[8] * v[2]];
  }
  function rx(a) { const c = Math.cos(a), s = Math.sin(a); return [1, 0, 0, 0, c, -s, 0, s, c]; }
  function ry(a) { const c = Math.cos(a), s = Math.sin(a); return [c, 0, s, 0, 1, 0, -s, 0, c]; }
  function rz(a) { const c = Math.cos(a), s = Math.sin(a); return [c, -s, 0, s, c, 0, 0, 0, 1]; }
  // volgorde: eerst z (rol), dan x (knik), dan y (draai) — prettig voor gewrichten
  function euler(r) {
    if (!r) return I3;
    let M = I3;
    if (r[1]) M = ry(r[1]);
    if (r[0]) M = mul(M, rx(r[0]));
    if (r[2]) M = mul(M, rz(r[2]));
    return M;
  }

  /* ---------- kleur ---------- */
  const cc = {};
  function rgb(c) {
    if (cc[c]) return cc[c];
    let v;
    if (c[0] === '#') v = [parseInt(c.slice(1, 3), 16), parseInt(c.slice(3, 5), 16), parseInt(c.slice(5, 7), 16)];
    else { const m = c.match(/-?\d+(\.\d+)?/g); v = [+m[0], +m[1], +m[2]]; }
    cc[c] = v; return v;
  }
  function mix(a, b, t) {
    const A = rgb(a), B = rgb(b);
    return 'rgb(' + Math.round(A[0] + (B[0] - A[0]) * t) + ',' + Math.round(A[1] + (B[1] - A[1]) * t) + ',' + Math.round(A[2] + (B[2] - A[2]) * t) + ')';
  }

  /* Licht: warme maan links-boven-voor, warme gloed van ramen/lantaarns
     van onder-rechts als randlicht. Per figuur instelbaar. */
  const DEF_LIGHT = {
    dir: norm([-0.55, 0.62, 0.56]),
    hi: '#fff0cf', hiAmt: 0.42,
    sh: '#22122e', shAmt: 0.58,
    rim: '#ffb347', rimAmt: 0.0,
    ol: 'rgba(28,10,22,.55)', olw: 0.9
  };
  function outline(ctx, L, s, size, p) {
    if (!L.ol || p.noLine || size < 3.2 * s) return;
    ctx.strokeStyle = L.ol; ctx.lineWidth = L.olw * s; ctx.lineJoin = 'round'; ctx.stroke();
  }
  function norm(v) { const l = Math.hypot(v[0], v[1], v[2]) || 1; return [v[0] / l, v[1] / l, v[2] / l]; }

  /* ---------- vorm-bouwers (DSL) ---------- */
  const S = {
    // ellipsoïde: middelpunt, stralen, kleur, opties {rot:[x,y,z], scallop:n, zb, gloss, line}
    E: (c, r, col, o) => Object.assign({ t: 'E', c: c, r: r, col: col }, o),
    // capsule (taps): p0, p1, r0, r1
    C: (p0, p1, r0, r1, col, o) => Object.assign({ t: 'C', p0: p0, p1: p1, r0: r0, r1: r1, col: col }, o),
    // afgeknotte kegel langs lokale y: onderring (c0, rx0, rz0) bovenring (c1, rx1, rz1)
    F: (c0, rx0, rz0, c1, rx1, rz1, col, o) => Object.assign({ t: 'F', c0: c0, c1: c1, a0: [rx0, rz0], a1: [rx1, rz1], col: col }, o),
    // doos: middelpunt, halve maten
    B: (c, h, col, o) => Object.assign({ t: 'B', c: c, h: h, col: col }, o),
    // kaart: veelhoek in 3D
    K: (pts, col, o) => Object.assign({ t: 'K', pts: pts, col: col }, o),
    // omslag: lap stof om een ellips-doorsnede (langs lokale x), hoek th0..th1 (0 = boven)
    W: (c, x0, x1, ry, rz, th0, th1, col, o) => Object.assign({ t: 'W', c: c, x0: x0, x1: x1, ry: ry, rz: rz, th0: th0, th1: th1, col: col }, o),
    // buis: polylijn met straal
    T: (pts, r, col, o) => Object.assign({ t: 'T', pts: pts, r: r, col: col }, o)
  };

  /* Node: { name, pos, rot, prims, kids }. pos is t.o.v. de ouder. */
  function N(name, pos, prims, kids) {
    return { name: name, pos: pos || [0, 0, 0], rot: null, prims: prims || [], kids: kids || [], off: null };
  }
  function index(root) {
    const map = {};
    (function walk(n) { map[n.name] = n; for (const k of n.kids) walk(k); })(root);
    return map;
  }

  /* ---------- per-frame: alles naar wereld en scherm ---------- */
  // view = { x, y (schermpositie van de voeten), s (schaal), yaw, pitch, light }
  function collect(root, view, out) {
    const V = mul(rx(view.pitch || 0), ry(view.yaw || 0));
    const s = view.s;
    (function walk(n, PM, PT) {
      if (n.hidden) return;
      const pos = n.off ? [n.pos[0] + n.off[0], n.pos[1] + n.off[1], n.pos[2] + n.off[2]] : n.pos;
      const T = add(PT, ap(PM, pos));
      const M = mul(PM, euler(n.rot));
      for (const p of n.prims) {
        if (p.hide) continue;
        out.push({ p: p, M: M, T: T });
      }
      for (const k of n.kids) walk(k, M, T);
    })(root, V, [0, 0, 0]);
    return { V: V, s: s };
  }
  function add(a, b) { return [a[0] + b[0], a[1] + b[1], a[2] + b[2]]; }
  function wpt(M, T, v) { const r = ap(M, v); return [r[0] + T[0], r[1] + T[1], r[2] + T[2]]; }

  /* Teken een figuur. Geeft het aantal getekende vormen terug. */
  function draw(ctx, root, view) {
    const L = Object.assign({}, DEF_LIGHT, view.light || {});
    const list = [];
    collect(root, view, list);
    const s = view.s, X = view.x, Y = view.y;
    const P = (w) => [X + w[0] * s, Y - w[1] * s, w[2] * s];   // wereld → scherm
    // lichtrichting in schermruimte (wordt ook gebruikt voor highlight-offsets)
    const Ls = [L.dir[0], -L.dir[1]];
    const items = [];
    for (const it of list) {
      const p = it.p, M = it.M, T = it.T;
      let d;
      if (p.t === 'E') {
        const R = p.rot ? mul(M, euler(p.rot)) : M;
        const A = mul(R, [p.r[0], 0, 0, 0, p.r[1], 0, 0, 0, p.r[2]]);
        const c = P(wpt(M, T, p.c));
        d = { k: 'E', p: p, c: c, A: A, z: c[2] };
      } else if (p.t === 'C') {
        const a = P(wpt(M, T, p.p0)), b = P(wpt(M, T, p.p1));
        d = { k: 'C', p: p, a: a, b: b, z: (a[2] + b[2]) / 2 };
      } else if (p.t === 'F') {
        const n = 18, r0 = [], r1 = [];
        for (let i = 0; i < n; i++) {
          const an = i / n * TAU, ca = Math.cos(an), sa = Math.sin(an);
          r0.push(P(wpt(M, T, [p.c0[0] + ca * p.a0[0], p.c0[1], p.c0[2] + sa * p.a0[1]])));
          r1.push(P(wpt(M, T, [p.c1[0] + ca * p.a1[0], p.c1[1], p.c1[2] + sa * p.a1[1]])));
        }
        const c0 = P(wpt(M, T, p.c0)), c1 = P(wpt(M, T, p.c1));
        const ax = ap(M, [0, 1, 0]);
        d = { k: 'F', p: p, r0: r0, r1: r1, c0: c0, c1: c1, ax: ax, z: (c0[2] + c1[2]) / 2 };
      } else if (p.t === 'B') {
        const h = p.h, c = p.c, v = [];
        for (let i = 0; i < 8; i++) v.push(P(wpt(M, T, [c[0] + (i & 1 ? h[0] : -h[0]), c[1] + (i & 2 ? h[1] : -h[1]), c[2] + (i & 4 ? h[2] : -h[2])])));
        const cz = P(wpt(M, T, c));
        d = { k: 'B', p: p, v: v, M: M, z: cz[2] };
      } else if (p.t === 'K') {
        const pts = p.pts.map((q) => P(wpt(M, T, q)));
        let z = 0; for (const q of pts) z += q[2];
        // normaal in wereldruimte
        const a = p.pts[0], b = p.pts[1], c = p.pts[2];
        const u = [b[0] - a[0], b[1] - a[1], b[2] - a[2]], w = [c[0] - a[0], c[1] - a[1], c[2] - a[2]];
        const nl = norm([u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0]]);
        d = { k: 'K', p: p, pts: pts, n: norm(ap(M, nl)), z: z / pts.length };
      } else if (p.t === 'W') {
        const n = 14, top = [], bot = [], nrm = [];
        for (let i = 0; i <= n; i++) {
          const th = p.th0 + (p.th1 - p.th0) * i / n, cy = Math.cos(th), sz = Math.sin(th);
          const sag0 = p.sag ? p.sag * (1 - Math.abs(cy)) : 0;
          top.push(P(wpt(M, T, [p.c[0] + p.x0, p.c[1] + cy * p.ry - sag0, p.c[2] + sz * p.rz])));
          bot.push(P(wpt(M, T, [p.c[0] + p.x1, p.c[1] + cy * p.ry - sag0, p.c[2] + sz * p.rz])));
          nrm.push(norm(ap(M, [0, cy / p.ry, sz / p.rz])));
        }
        const cz = P(wpt(M, T, p.c));
        d = { k: 'W', p: p, A: top, Bp: bot, n: nrm, z: cz[2] };
      } else if (p.t === 'T') {
        const pts = p.pts.map((q) => P(wpt(M, T, q)));
        let z = 0; for (const q of pts) z += q[2];
        d = { k: 'T', p: p, pts: pts, z: z / pts.length };
      }
      d.z += (p.zb || 0) * s;
      items.push(d);
    }
    items.sort((a, b) => a.z - b.z);
    for (const d of items) paint(ctx, d, L, Ls, s, view);
    return items.length;
  }

  function shades(col, L, f) {
    f = f || 1;
    return {
      hi: mix(col, L.hi, L.hiAmt * f),
      mid: col,
      sh: mix(col, L.sh, L.shAmt * f)
    };
  }

  function paint(ctx, d, L, Ls, s, view) {
    const p = d.p;
    const col = p.col;
    if (p.t === 'E') paintE(ctx, d, L, Ls, s);
    else if (p.t === 'C') paintC(ctx, d, L, Ls, s);
    else if (p.t === 'F') paintF(ctx, d, L, Ls, s);
    else if (p.t === 'B') paintB(ctx, d, L, s);
    else if (p.t === 'K') paintK(ctx, d, L, s);
    else if (p.t === 'T') paintT(ctx, d, L, Ls, s);
    else if (p.t === 'W') paintW(ctx, d, L, s);
    void col; void view;
  }

  function paintE(ctx, d, L, Ls, s) {
    const A = d.A, p = d.p;
    // projectie van de ellipsoïde: S = A2 A2ᵀ (eerste twee rijen, y omgedraaid)
    const a0 = A[0] * s, a1 = A[1] * s, a2 = A[2] * s, b0 = -A[3] * s, b1 = -A[4] * s, b2 = -A[5] * s;
    const sa = a0 * a0 + a1 * a1 + a2 * a2, sb = a0 * b0 + a1 * b1 + a2 * b2, sd = b0 * b0 + b1 * b1 + b2 * b2;
    const tr = (sa + sd) / 2, det = sa * sd - sb * sb;
    const disc = Math.sqrt(Math.max(0, tr * tr - det));
    const l1 = Math.sqrt(Math.max(0.01, tr + disc)), l2 = Math.sqrt(Math.max(0.01, tr - disc));
    const ang = 0.5 * Math.atan2(2 * sb, sa - sd);
    const cx = d.c[0], cy = d.c[1];
    const ex = Math.sqrt(sa), ey = Math.sqrt(sd);
    const hx = cx + Ls[0] * ex * 0.5, hy = cy + Ls[1] * ey * 0.5;
    const sh = shades(p.col, L, p.flat ? 0.5 : 1);
    ctx.beginPath();
    if (p.scallop) {
      const n = p.scallop * 2, ca = Math.cos(ang), sn = Math.sin(ang);
      for (let i = 0; i <= 48; i++) {
        const t = i / 48 * TAU;
        const k = 1 + 0.09 * Math.abs(Math.sin(t * n / 2));
        const x = Math.cos(t) * l1 * k, y = Math.sin(t) * l2 * k;
        const px = cx + x * ca - y * sn, py = cy + x * sn + y * ca;
        if (i) ctx.lineTo(px, py); else ctx.moveTo(px, py);
      }
    } else ctx.ellipse(cx, cy, l1, l2, ang, 0, TAU);
    const R = Math.max(l1, l2) * 1.35;
    const g = ctx.createRadialGradient(hx, hy, 0, hx, hy, R);
    g.addColorStop(0, sh.hi);
    g.addColorStop(p.gloss ? 0.25 : 0.42, sh.mid);
    g.addColorStop(1, sh.sh);
    ctx.fillStyle = g;
    ctx.fill();
    outline(ctx, L, s, Math.min(l1, l2) * 1.4, p);
    if (p.line) { ctx.strokeStyle = p.line; ctx.lineWidth = (p.lw || 0.8) * s; ctx.stroke(); }
    if (p.gloss) {
      ctx.fillStyle = 'rgba(255,250,235,' + p.gloss + ')';
      ctx.beginPath();
      ctx.ellipse(cx + Ls[0] * ex * 0.42, cy + Ls[1] * ey * 0.42, l1 * 0.22, l2 * 0.15, ang, 0, TAU);
      ctx.fill();
    }
    if (L.rimAmt > 0 && !p.noRim) rimArc(ctx, cx, cy, l1, l2, ang, L);
  }

  function rimArc(ctx, cx, cy, l1, l2, ang, L) {
    ctx.save();
    ctx.globalCompositeOperation = 'lighter';
    ctx.strokeStyle = L.rim;
    ctx.globalAlpha = L.rimAmt;
    ctx.lineWidth = Math.max(0.8, Math.min(l1, l2) * 0.18);
    ctx.beginPath();
    // randlicht aan de kant tegenover de maan (rechtsonder)
    const base = Math.atan2(0.55, 0.85) - ang;
    ctx.ellipse(cx, cy, l1 * 0.93, l2 * 0.93, ang, base - 0.9, base + 0.9);
    ctx.stroke();
    ctx.restore();
  }

  function paintC(ctx, d, L, Ls, s) {
    const p = d.p, a = d.a, b = d.b;
    const r0 = p.r0 * s, r1 = p.r1 * s;
    let dx = b[0] - a[0], dy = b[1] - a[1];
    const len = Math.hypot(dx, dy);
    const sh = shades(p.col, L);
    ctx.beginPath();
    if (len < Math.abs(r0 - r1) + 0.5) {
      const big = r0 > r1 ? a : b;
      ctx.arc(big[0], big[1], Math.max(r0, r1), 0, TAU);
      dx = 0; dy = 1;
    } else {
      const th = Math.atan2(dy, dx);
      ctx.arc(a[0], a[1], r0, th + Math.PI / 2, th + Math.PI * 1.5);
      ctx.arc(b[0], b[1], r1, th - Math.PI / 2, th + Math.PI / 2);
      ctx.closePath();
    }
    // verloop dwars op de as, naar het licht toe
    let nx = -dy, ny = dx; const nl = Math.hypot(nx, ny) || 1; nx /= nl; ny /= nl;
    if (nx * Ls[0] + ny * Ls[1] < 0) { nx = -nx; ny = -ny; }
    const mx = (a[0] + b[0]) / 2, my = (a[1] + b[1]) / 2, rr = Math.max(r0, r1);
    const g = ctx.createLinearGradient(mx + nx * rr, my + ny * rr, mx - nx * rr, my - ny * rr);
    g.addColorStop(0, sh.hi);
    g.addColorStop(0.4, sh.mid);
    g.addColorStop(1, sh.sh);
    ctx.fillStyle = g;
    ctx.fill();
    outline(ctx, L, s, rr * 2, p);
    if (p.line) { ctx.strokeStyle = p.line; ctx.lineWidth = 0.8; ctx.stroke(); }
  }

  function hull(pts) {
    const P = pts.slice().sort((a, b) => a[0] - b[0] || a[1] - b[1]);
    const cr = (o, a, b) => (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);
    const lo = [], up = [];
    for (const q of P) { while (lo.length >= 2 && cr(lo[lo.length - 2], lo[lo.length - 1], q) <= 0) lo.pop(); lo.push(q); }
    for (let i = P.length - 1; i >= 0; i--) { const q = P[i]; while (up.length >= 2 && cr(up[up.length - 2], up[up.length - 1], q) <= 0) up.pop(); up.push(q); }
    up.pop(); lo.pop();
    return lo.concat(up);
  }

  function paintF(ctx, d, L, Ls, s) {
    const p = d.p;
    const H = hull(d.r0.concat(d.r1));
    const sh = shades(p.col, L);
    ctx.beginPath();
    H.forEach((q, i) => (i ? ctx.lineTo(q[0], q[1]) : ctx.moveTo(q[0], q[1])));
    ctx.closePath();
    // verloop dwars op de geprojecteerde as
    let dx = d.c1[0] - d.c0[0], dy = d.c1[1] - d.c0[1];
    if (Math.hypot(dx, dy) < 0.01) { dx = 0; dy = -1; }
    let nx = -dy, ny = dx; const nl = Math.hypot(nx, ny) || 1; nx /= nl; ny /= nl;
    if (nx * Ls[0] + ny * Ls[1] < 0) { nx = -nx; ny = -ny; }
    let minp = 1e9, maxp = -1e9;
    for (const q of H) { const v = q[0] * nx + q[1] * ny; if (v < minp) minp = v; if (v > maxp) maxp = v; }
    const mx = (d.c0[0] + d.c1[0]) / 2, my = (d.c0[1] + d.c1[1]) / 2;
    const m0 = mx * nx + my * ny;
    const g = ctx.createLinearGradient(mx + nx * (maxp - m0), my + ny * (maxp - m0), mx + nx * (minp - m0), my + ny * (minp - m0));
    g.addColorStop(0, sh.hi);
    g.addColorStop(0.38, sh.mid);
    g.addColorStop(1, sh.sh);
    ctx.fillStyle = g;
    ctx.fill();
    outline(ctx, L, s, 99, p);
    if (p.fold) {          // plooien: donkere lijntjes van onder naar boven aan de voorkant
      ctx.save(); ctx.clip();
      ctx.strokeStyle = mix(p.col, L.sh, 0.5); ctx.globalAlpha = 0.35; ctx.lineWidth = 1.2 * s;
      ctx.beginPath();
      const n = d.r0.length;
      for (let i = 0; i < n; i += 2) {
        if (d.r0[i][2] < d.c0[2]) continue;
        ctx.moveTo(d.r0[i][0], d.r0[i][1]);
        ctx.lineTo(d.r0[i][0] * 0.4 + d.r1[i][0] * 0.6, d.r0[i][1] * 0.4 + d.r1[i][1] * 0.6);
      }
      ctx.stroke();
      ctx.restore();
    }
    // dop (boven/onder) als die naar de kijker wijst
    const capOf = (ring, sign, colr) => {
      ctx.beginPath();
      ring.forEach((q, i) => (i ? ctx.lineTo(q[0], q[1]) : ctx.moveTo(q[0], q[1])));
      ctx.closePath();
      ctx.fillStyle = colr; ctx.fill();
      void sign;
    };
    if (p.capTop && d.ax[2] > 0.02 && p.a1[0] > 0) capOf(d.r1, 1, mix(p.capTop, L.hi, 0.15));
    if (p.capBot && d.ax[2] < -0.02) capOf(d.r0, -1, p.capBot);
    // banden (goudranden): voorste helft van een tussenliggende ring
    if (p.bands) {
      for (const bd of p.bands) {
        const n = d.r0.length, czc = d.c0[2] + (d.c1[2] - d.c0[2]) * bd.v;
        ctx.strokeStyle = bd.col; ctx.lineWidth = bd.w * s; ctx.lineCap = 'round';
        ctx.beginPath();
        let pen = false;
        for (let i = 0; i <= n; i++) {
          const a = d.r0[i % n], b = d.r1[i % n];
          const x = a[0] + (b[0] - a[0]) * bd.v, y = a[1] + (b[1] - a[1]) * bd.v, z = a[2] + (b[2] - a[2]) * bd.v;
          if (z >= czc - 0.5 * s) { if (pen) ctx.lineTo(x, y); else { ctx.moveTo(x, y); pen = true; } }
          else pen = false;
        }
        ctx.stroke();
      }
    }
  }

  function paintB(ctx, d, L, s) {
    const p = d.p, v = d.v, M = d.M;
    // zes vlakken: [hoekindexen], lokale normaal
    const F = [[[0, 2, 3, 1], [0, 0, -1]], [[4, 5, 7, 6], [0, 0, 1]], [[0, 4, 6, 2], [-1, 0, 0]], [[1, 3, 7, 5], [1, 0, 0]], [[0, 1, 5, 4], [0, -1, 0]], [[2, 6, 7, 3], [0, 1, 0]]];
    const vis = [];
    for (const f of F) {
      const n = ap(M, f[1]);
      if (n[2] > 0.001) vis.push({ f: f[0], n: n });
    }
    for (const fc of vis) {
      const lam = Math.max(0, fc.n[0] * L.dir[0] + fc.n[1] * L.dir[1] + fc.n[2] * L.dir[2]);
      const c = lam > 0.5 ? mix(p.col, L.hi, (lam - 0.5) * L.hiAmt * 1.6) : mix(p.col, L.sh, (0.5 - lam) * L.shAmt * 1.4);
      ctx.beginPath();
      fc.f.forEach((i, k) => (k ? ctx.lineTo(v[i][0], v[i][1]) : ctx.moveTo(v[i][0], v[i][1])));
      ctx.closePath();
      ctx.fillStyle = c; ctx.fill();
      ctx.strokeStyle = mix(p.col, L.sh, 0.5); ctx.lineWidth = 0.5; ctx.stroke();
      // lint over het pakje
      if (p.ribbon) {
        const q = fc.f.map((i) => v[i]);
        const mid = (a, b) => [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];
        ctx.strokeStyle = lam > 0.5 ? mix(p.ribbon, L.hi, 0.3) : mix(p.ribbon, L.sh, 0.35);
        ctx.lineWidth = (p.rw || 3) * s;
        const m01 = mid(q[0], q[1]), m23 = mid(q[2], q[3]), m12 = mid(q[1], q[2]), m30 = mid(q[3], q[0]);
        ctx.beginPath(); ctx.moveTo(m01[0], m01[1]); ctx.lineTo(m23[0], m23[1]);
        ctx.moveTo(m12[0], m12[1]); ctx.lineTo(m30[0], m30[1]); ctx.stroke();
      }
    }
  }

  function paintK(ctx, d, L, s) {
    const p = d.p, n = d.n;
    if (p.oneSided && n[2] < 0) return;
    let col = p.col;
    if (n[2] < 0 && p.back) col = p.back;
    const nn = n[2] < 0 ? [-n[0], -n[1], -n[2]] : n;
    const lam = Math.max(0, nn[0] * L.dir[0] + nn[1] * L.dir[1] + nn[2] * L.dir[2]);
    const c = lam > 0.45 ? mix(col, L.hi, (lam - 0.45) * L.hiAmt * 1.4) : mix(col, L.sh, (0.45 - lam) * L.shAmt * 1.3);
    ctx.beginPath();
    if (p.smooth) {
      const q = d.pts, m = q.length;
      const mid = (a, b) => [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];
      const s0 = mid(q[m - 1], q[0]);
      ctx.moveTo(s0[0], s0[1]);
      for (let i = 0; i < m; i++) { const mm = mid(q[i], q[(i + 1) % m]); ctx.quadraticCurveTo(q[i][0], q[i][1], mm[0], mm[1]); }
    } else d.pts.forEach((q, i) => (i ? ctx.lineTo(q[0], q[1]) : ctx.moveTo(q[0], q[1])));
    ctx.closePath();
    ctx.fillStyle = c; ctx.fill();
    if (!p.zb) outline(ctx, L, s, 99, p);
    if (p.line) { ctx.strokeStyle = p.line; ctx.lineWidth = (p.lw || 1) * s; ctx.stroke(); }
  }

  function paintW(ctx, d, L, s) {
    const p = d.p, A = d.A, Bp = d.Bp, n = d.n, m = A.length - 1;
    for (let i = 0; i < m; i++) {
      const nn = [(n[i][0] + n[i + 1][0]) / 2, (n[i][1] + n[i + 1][1]) / 2, (n[i][2] + n[i + 1][2]) / 2];
      if (nn[2] < -0.05) continue;
      const lam = Math.max(0, nn[0] * L.dir[0] + nn[1] * L.dir[1] + nn[2] * L.dir[2]);
      const c = lam > 0.45 ? mix(p.col, L.hi, (lam - 0.45) * L.hiAmt * 1.4) : mix(p.col, L.sh, (0.45 - lam) * L.shAmt * 1.3);
      ctx.beginPath();
      ctx.moveTo(A[i][0], A[i][1]); ctx.lineTo(A[i + 1][0], A[i + 1][1]); ctx.lineTo(Bp[i + 1][0], Bp[i + 1][1]); ctx.lineTo(Bp[i][0], Bp[i][1]);
      ctx.closePath();
      ctx.fillStyle = c; ctx.fill(); ctx.strokeStyle = c; ctx.lineWidth = 0.6; ctx.stroke();
    }
    if (p.trim) {
      ctx.strokeStyle = p.trim; ctx.lineWidth = (p.tw || 2) * s; ctx.lineCap = 'round';
      ctx.beginPath();
      for (let i = 0; i < m; i++) {
        if ((n[i][2] + n[i + 1][2]) < -0.1) continue;
        ctx.moveTo(A[i][0], A[i][1]); ctx.lineTo(A[i + 1][0], A[i + 1][1]);
        ctx.moveTo(Bp[i][0], Bp[i][1]); ctx.lineTo(Bp[i + 1][0], Bp[i + 1][1]);
      }
      for (const j of [0, m]) if (n[j][2] > -0.05) { ctx.moveTo(A[j][0], A[j][1]); ctx.lineTo(Bp[j][0], Bp[j][1]); }
      ctx.stroke();
      if (p.tassel) {
        ctx.fillStyle = p.trim;
        for (const j of [0, m]) {
          if (n[j][2] < -0.05) continue;
          for (let k = 0; k <= 6; k++) {
            const x = A[j][0] + (Bp[j][0] - A[j][0]) * k / 6, y = A[j][1] + (Bp[j][1] - A[j][1]) * k / 6;
            ctx.beginPath(); ctx.ellipse(x, y + 3 * s, 1.4 * s, 3 * s, 0, 0, Math.PI * 2); ctx.fill();
          }
        }
      }
    }
  }

  function paintT(ctx, d, L, Ls, s) {
    const p = d.p, q = d.pts;
    const sh = shades(p.col, L);
    ctx.lineCap = 'round'; ctx.lineJoin = 'round';
    const path = (ox, oy) => { ctx.beginPath(); q.forEach((v, i) => (i ? ctx.lineTo(v[0] + ox, v[1] + oy) : ctx.moveTo(v[0] + ox, v[1] + oy))); };
    path(0, 0); ctx.strokeStyle = sh.sh; ctx.lineWidth = p.r * 2 * s; ctx.stroke();
    path(Ls[0] * p.r * 0.25 * s, Ls[1] * p.r * 0.25 * s); ctx.strokeStyle = sh.mid; ctx.lineWidth = p.r * 1.3 * s; ctx.stroke();
    path(Ls[0] * p.r * 0.5 * s, Ls[1] * p.r * 0.5 * s); ctx.strokeStyle = sh.hi; ctx.lineWidth = p.r * 0.5 * s; ctx.stroke();
  }

  window.Puppet3D = { S: S, N: N, index: index, draw: draw, mix: mix, norm: norm };
})();

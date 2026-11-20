/* =====================================================================
   Sprite-compositie: een figuur los in een buffer renderen en dan op het
   canvas zetten met één omlijning rond het hele silhouet (geen randjes
   tussen onderdelen) en randlicht: koel/warm maanlicht langs de ene kant,
   warme lantaarngloed langs de andere.
   paint(g, W, H, info) tekent de figuur in de buffer (identiteitstransform).
   ===================================================================== */
(function () {
  'use strict';
  const TAU = Math.PI * 2;
  const BUF = {};
  function buf(id, k, w, h) {
    const key = id + k;
    let c = BUF[key];
    if (!c) { c = BUF[key] = document.createElement('canvas'); c._g = c.getContext('2d'); }
    if (c.width < w || c.height < h) { c.width = Math.max(c.width, w); c.height = Math.max(c.height, h); }
    return c;
  }
  /* view = { x, y (voeten, toneelcoörd.), s (schaal) }
     o = { id, w (halve breedte), up, down (model-eenheden), paint, ol, rims } */
  function drawSprite(ctx, view, o) {
    const m = ctx.getTransform(), sc = m.a, s = view.s;
    const bw = (o.w || 80) * s, up = (o.up || 240) * s, dn = (o.down || 30) * s;
    const X0 = (view.x - bw) * sc + m.e, Y0 = (view.y - up) * sc + m.f;
    const W = Math.ceil(bw * 2 * sc) + 8, H = Math.ceil((up + dn) * sc) + 8;
    const fx = Math.floor(X0) - 4, fy = Math.floor(Y0) - 4;
    const A = buf(o.id, 'a', W, H), Bc = buf(o.id, 'b', W, H);
    const g = A._g, g2 = Bc._g;
    g.setTransform(1, 0, 0, 1, 0, 0); g.clearRect(0, 0, A.width, A.height);
    o.paint(g, W, H, { fx: fx, fy: fy, sc: sc, m: m, Fx: view.x * sc + m.e, Fy: view.y * sc + m.f });
    g.setTransform(1, 0, 0, 1, 0, 0);
    const sil = (col) => {
      g2.setTransform(1, 0, 0, 1, 0, 0); g2.globalCompositeOperation = 'source-over'; g2.globalAlpha = 1;
      g2.clearRect(0, 0, Bc.width, Bc.height);
      g2.drawImage(A, 0, 0);
      g2.globalCompositeOperation = 'source-in';
      g2.fillStyle = col; g2.fillRect(0, 0, Bc.width, Bc.height);
      g2.globalCompositeOperation = 'source-over';
    };
    ctx.save();
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    /* silhouet-modus: alleen een donkere, zachte schaduw, geknipt binnen ramen
       (o.silhouette = { col, blur (toneel-px), alpha, clip: [[x, y, w, h], ...] in toneelcoördinaten }) */
    if (o.silhouette) {
      const S = o.silhouette;
      sil(S.col || 'rgb(48,18,8)');
      ctx.beginPath();
      for (const r of S.clip) ctx.rect(r[0] * sc + m.e, r[1] * sc + m.f, r[2] * sc, r[3] * sc);
      ctx.clip();
      if ('filter' in ctx && S.blur) ctx.filter = 'blur(' + (S.blur * sc).toFixed(2) + 'px)';
      ctx.globalAlpha = S.alpha === undefined ? 0.82 : S.alpha;
      ctx.drawImage(Bc, fx, fy);
      ctx.restore();
      return;
    }
    const k = sc * Math.min(1.4, Math.max(0.7, s));
    const ow = (o.ol === undefined ? 1.1 : o.ol) * k;
    if (ow > 0) {
      sil(o.olCol || 'rgba(26,8,24,0.85)');
      for (let i = 0; i < 8; i++) { const a = i / 8 * TAU; ctx.drawImage(Bc, fx + Math.cos(a) * ow, fy + Math.sin(a) * ow); }
    }
    ctx.drawImage(A, fx, fy);
    const rims = o.rims || [{ col: '#ffe2ae', dx: 1.8, dy: 2.2, a: 0.42 }, { col: '#ff9442', dx: -1.6, dy: -1.6, a: 0.26 }];
    for (const rm of rims) {
      sil(rm.col);
      g2.globalCompositeOperation = 'destination-out';
      g2.drawImage(A, rm.dx * k, rm.dy * k);
      g2.globalCompositeOperation = 'source-over';
      ctx.globalCompositeOperation = 'lighter';
      ctx.globalAlpha = rm.a;
      ctx.drawImage(Bc, fx, fy);
      ctx.globalAlpha = 1; ctx.globalCompositeOperation = 'source-over';
    }
    ctx.restore();
  }
  window.Sprite = { draw: drawSprite };
})();

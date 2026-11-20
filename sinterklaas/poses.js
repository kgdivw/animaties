/* =====================================================================
   Poses voor de 3D-personages. Elke functie krijgt een toestand st en
   geeft { rot, off, hide } terug (zie chars3d.js). Assen: x rechts,
   y omhoog, z naar de kijker. rx > 0 kantelt "naar achteren" voor iets
   dat omlaag wijst (een been zwaait dan naar achteren).
   st.ph  looppas-fase   st.walk 0..1   st.t tijd (s)   st.turn draaisnelheid
   ===================================================================== */
(function () {
  'use strict';
  const sin = Math.sin, cos = Math.cos, max = Math.max, min = Math.min;
  const clamp = (v, a, b) => (v < a ? a : v > b ? b : v);
  /* Loopcyclus van één been. In de steunfase (fractie `duty`) beweegt de voet in een
     rechte lijn met constante snelheid naar achteren (pos +1 → -1): zo kan hij stil op
     de grond staan terwijl het lichaam gelijkmatig verder gaat. In de zwaaifase gaat hij
     vloeiend en opgetild terug naar voren. Geeft [pos, lift]. */
  function gait(ph, duty) {
    const u = ((ph / (Math.PI * 2)) % 1 + 1) % 1;
    if (u < duty) return [1 - 2 * u / duty, 0];
    const v = (u - duty) / (1 - duty), e = v * v * (3 - 2 * v);
    return [-1 + 2 * e, sin(Math.PI * v)];
  }

  /* ---------------- Sinterklaas: statig, mantel zwiert na ---------------- */
  function sint(st) {
    const w = st.walk || 0, ph = st.ph || 0, t = st.t || 0;
    const s = sin(ph), c = cos(ph);
    const breathe = sin(t * 1.6);
    const wave = st.wave || 0, wv = sin(t * 7.2);
    const turn = clamp(st.turn || 0, -3, 3);
    const R = {}, O = {};
    // heup: zacht deinen (hoog bij het passeren), gewicht naar het standbeen
    O.hip = [s * 1.4 * w, Math.abs(c) * 2.4 * w - 1.2 * w + breathe * 0.35 - (st.crouch || 0) * 8, 0];
    R.hip = [0.03 * w, s * 0.07 * w - turn * 0.04, s * 0.025 * w];
    R.chest = [-0.03 * w + (st.lean || 0) + breathe * 0.01, -s * 0.07 * w + turn * 0.05, wave * 0.07];
    R.neck = [0, turn * 0.08, 0];
    R.head = [(st.nod || 0) + cos(ph * 2) * 0.025 * w, (st.look || 0) + turn * 0.12, (st.tilt || 0) + wave * 0.06];
    // mantel: waait naar achteren bij lopen/wind en slingert na
    const fl = 0.06 + w * 0.26 + (st.wind || 0) * 0.1;
    R.cape = [fl + sin(ph * 2 - 1.1) * 0.035 * w + sin(t * 1.7) * 0.02, sin(ph - 0.9) * 0.08 * w - turn * 0.06, sin(ph - 0.9) * 0.03 * w];
    // voeten schuiven onder de mantel uit
    O.ftR = [0, max(0, s) * 5 * w, s * 13 * w];
    O.ftL = [0, max(0, -s) * 5 * w, -s * 13 * w];
    R.ftR = [-max(0, s) * 0.25 * w, 0, 0];
    R.ftL = [-max(0, -s) * 0.25 * w, 0, 0];
    // rechterarm: meezwaaien of groeten
    R.shR = [s * 0.32 * w * (1 - wave) - wave * 0.45 + breathe * 0.01, -wave * 0.3, -0.1 - wave * 2.25];
    R.elR = [-0.3 * (1 - wave) - wave * 0.15 - max(0, -s) * 0.15 * w, 0, -wave * (0.55 + wv * 0.38)];
    R.haR = [0, wave * wv * 0.3, -wave * 0.2];
    // linkerarm houdt de staf voor zich, staf blijft rechtop
    const sa = -0.5 - s * 0.07 * w, ea = -0.85 + s * 0.05 * w;
    R.shL = [sa, 0, 0.16];
    R.elL = [ea, 0, -0.08];
    R.haL = [0, 0, 0];
    R.staff = [-(sa + ea) - 0.04, 0, -0.08 - s * 0.03 * w];
    return { rot: R, off: O };
  }

  /* ---------------- Sint te paard ---------------- */
  // bovenlijf van sint(), benen in de stijgbeugels, teugel in de rechterhand;
  // st.twist (0..1) draait romp en hoofd in het zadel naar de kijker
  function rider(st) {
    const P = sint(Object.assign({}, st, { walk: 0 }));
    const R = P.rot, O = P.off;
    const t = st.t || 0, ph = st.ph || 0, w = st.walk || 0, tw = st.twist || 0, wave = st.wave || 0;
    delete O.ftR; delete O.ftL;
    O.hip = [0, sin(t * 1.6) * 0.3, 0];
    R.hip = [sin(ph * 2) * 0.03 * w, -tw * 0.35, sin(ph) * 0.035 * w];
    R.chest = [-0.04 + sin(ph * 2 + 0.6) * 0.03 * w, -tw * 0.45, wave * 0.07];
    R.head[1] += -tw * 0.45;
    R.thR = [sin(ph) * 0.05 * w, 0, 0]; R.thL = [-sin(ph) * 0.05 * w, 0, 0];
    R.knR = [sin(ph * 2) * 0.04 * w, 0, 0]; R.knL = [sin(ph * 2) * 0.04 * w, 0, 0];
    R.ftR = [0, 0, 0]; R.ftL = [0, 0, 0];
    if (wave < 0.01) { R.shR = [-0.55 + sin(ph * 2) * 0.04 * w, 0, -0.12]; R.elR = [-0.95, 0, 0.25]; }
    const fl = 0.12 + w * 0.22 + (st.wind || 0) * 0.12;
    R.cape = [fl + sin(ph * 2 - 1.1) * 0.04 * w, sin(ph - 0.9) * 0.06 * w + tw * 0.2, 0];
    return P;
  }

  /* ---------------- Piet: veerkrachtig, grote passen ---------------- */
  function piet(st, prop) {
    const w = st.walk || 0, ph = st.ph || 0, t = st.t || 0;
    const s = sin(ph), c = cos(ph);
    const jump = st.jump || 0, air = st.air || 0;
    const turn = clamp(st.turn || 0, -3, 3);
    const R = {}, O = {};
    const bounce = Math.abs(c);                           // 1 bij het passeren, 0 bij neerzetten
    O.hip = [s * 1.2 * w, (bounce * 4.2 - 2.4) * w + sin(t * 2) * 0.35 - jump * 7 + air * 2, 0];
    R.hip = [0.05 * w, s * 0.16 * w - turn * 0.05, s * 0.04 * w];
    R.chest = [0.1 * w + jump * 0.3 - air * 0.1 + sin(ph * 2) * 0.03 * w, -s * 0.2 * w + turn * 0.07, -s * 0.05 * w];
    R.neck = [-0.04 * w, s * 0.06 * w + turn * 0.1, 0];
    R.head = [cos(ph * 2) * 0.05 * w - 0.05 * w + (st.nod || 0) - jump * 0.15, (st.look || 0) + s * 0.05 * w + turn * 0.15, s * 0.04 * w];
    // benen: steunfase in een rechte lijn, zwaaifase opgetild (knie buigt, voet rolt af)
    const gR = gait(ph, 0.6), gL = gait(ph + Math.PI, 0.6);
    const sw = gR[0] * w;
    R.thR = [-gR[0] * 0.62 * w - gR[1] * 0.25 * w - jump * 0.85 + air * 0.5, 0, -0.02];
    R.thL = [-gL[0] * 0.62 * w - gL[1] * 0.25 * w - jump * 0.85 + air * 0.2, 0, 0.02];
    R.knR = [gR[1] * 1.3 * w + 0.08 * w + jump * 1.4 + air * 0.6, 0, 0];
    R.knL = [gL[1] * 1.3 * w + 0.08 * w + jump * 1.4 + air * 0.9, 0, 0];
    R.ftR = [(-gR[1] * 0.3 + max(0, -gR[0]) * 0.2 * (1 - gR[1])) * w - jump * 0.55, 0, 0];
    R.ftL = [(-gL[1] * 0.3 + max(0, -gL[0]) * 0.2 * (1 - gL[1])) * w - jump * 0.55, 0, 0];
    // baret en veer zwiepen na
    R.cap = [0.06, 0, -0.08 + sin(ph - 0.6) * 0.03 * w];
    const lag = sin(ph * 2 - 1.2) * w;
    R.feather = [-0.75 + lag * 0.16 + sin(t * 3.1) * 0.06 - (st.wind || 0) * 0.18 + air * 0.25, sin(t * 2.3) * 0.08, sin(t * 2.7) * 0.05 + s * 0.06 * w];
    const up = st.armsUp || 0;
    if (prop === 'sack') {
      // linkerarm houdt de zak over de schouder, rechterarm zwaait
      R.shL = [-2.35, 0, 0.42]; R.elL = [-1.25, 0, 0.1]; R.haL = [0.3, 0, 0];
      R.shR = [sw * 0.65 - up * 2.4 - air * 0.6, 0, -0.18 - up * 0.3 - air * 0.4];
      R.elR = [-0.35 - max(0, -s) * 0.45 * w - up * 0.2, 0, 0];
    } else if (prop === 'gift') {
      const lift = up;
      R.shR = [-0.92 - lift * 1.45 + s * 0.04 * w, 0, -0.18]; R.elR = [-0.5 + lift * 0.45, 0, 0.42];
      R.shL = [-0.92 - lift * 1.45 - s * 0.04 * w, 0, 0.18]; R.elL = [-0.5 + lift * 0.45, 0, -0.42];
      R.haR = [0, 0, 0.3]; R.haL = [0, 0, -0.3];
    } else {
      R.shR = [sw * 0.65 - air * 0.8, 0, -0.18 - air * 0.5]; R.elR = [-0.35 - max(0, -s) * 0.45 * w, 0, 0];
      R.shL = [-sw * 0.65 - air * 0.8, 0, 0.18 + air * 0.5]; R.elL = [-0.35 - max(0, s) * 0.45 * w, 0, 0];
    }
    const hide = {};
    if (st.hideProp) hide[prop] = true;
    return { rot: R, off: O, hide: hide };
  }

  /* ---------------- Het paard ---------------- */
  function horse(st) {
    const t = st.t || 0, w = st.walk || 0, ph = st.ph || 0;
    const R = {}, O = {};
    O.body = [0, sin(t * 1.3) * 0.6 + Math.abs(sin(ph)) * 2 * w, 0];
    R.body = [0, 0, sin(t * 1.3) * 0.006];
    const lift = st.lift || 0, nod = st.nod || 0, look = st.look || 0;
    R.neck = [0, look * 0.5, lift * 0.28 - nod * 0.22 + sin(t * 0.9) * 0.03];
    R.head = [0, look * 0.6, lift * 0.15 - nod * 0.3 + sin(t * 0.9 + 0.5) * 0.04];
    const ef = st.earFlick || 0;
    R.earL = [0.1 * ef, 0, -0.1 + ef * 0.45];
    R.earR = [0, 0, -0.1 + sin(t * 0.7) * 0.1];
    // draf: diagonale paren (FR+BL, FL+BR); steunfase in een rechte lijn, zwaaifase opgetild
    const stomp = st.stomp || 0;
    const A = gait(ph, 0.55), Bq = gait(ph + Math.PI, 0.55);
    R.legFR = [0, 0, A[0] * 0.3 * w + stomp * 0.5];  R.legFRk = [0, 0, -A[1] * 0.95 * w - stomp * 1.3];  R.legFRh = [0, 0, -A[1] * 0.45 * w + stomp * 0.4];
    R.legBL = [0, 0, A[0] * 0.27 * w];               R.legBLk = [0, 0, A[1] * 0.75 * w];                R.legBLh = [0, 0, -A[1] * 0.3 * w];
    R.legFL = [0, 0, Bq[0] * 0.3 * w];               R.legFLk = [0, 0, -Bq[1] * 0.95 * w];              R.legFLh = [0, 0, -Bq[1] * 0.45 * w];
    R.legBR = [0, 0, Bq[0] * 0.27 * w];              R.legBRk = [0, 0, Bq[1] * 0.75 * w];               R.legBRh = [0, 0, -Bq[1] * 0.3 * w];
    // staart: golf die naar het eind toe groter wordt
    const swish = st.swish || 0, wind = st.wind || 0;
    for (let i = 0; i < 4; i++) {
      R['tail' + i] = [sin(t * 2.2 - i * 0.9) * (0.08 + i * 0.05) * (0.4 + swish) + wind * 0.06, 0, -0.05 + sin(t * 1.1 - i * 0.6) * 0.04];
    }
    return { rot: R, off: O };
  }

  window.Poses = { sint: sint, rider: rider, piet: piet, horse: horse };
})();

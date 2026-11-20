/* =====================================================================
   Personages — Sinterklaas, twee Pieten en het schimmelpaard.
   Elk personage = skelet van nodes + vormen (zie puppet3d.js) en een
   pose(st)-functie die gewrichten zet uit een paar getallen:
     st.ph   looppas-fase (radialen)      st.walk  0..1 hoeveel hij loopt
     st.t    tijd (s), voor ademhaling / wind
     plus per figuur: wave, look, carry, ...
   Het model kijkt bij yaw 0 naar de kijker (+z).
   ===================================================================== */
(function () {
  'use strict';
  const { S, N, index } = window.Puppet3D;
  const { E, C, F, B, K, T, W } = S;
  const GOLD = '#e8b54a', GOLD_D = '#b9832c';
  const SKIN = '#f3c6a2', SKIN_D = '#e2a284';

  /* ------------------------------------------------------------ */
  /*  Sinterklaas  (≈ 205 eenheden hoog, voeten op y = 0)           */
  /* ------------------------------------------------------------ */
  function makeSint() {
    const RED = '#bb1e2b', RED_D = '#8e1220', WHITE = '#f3ede2', BEARD = '#f7f3ee';

    // staf met krul — kromming als spiraal
    const crook = [];
    for (let i = 0; i <= 22; i++) {
      const u = i / 22, th = Math.PI - u * Math.PI * 1.75, r = 9 - u * 4.5;
      crook.push([9 + Math.cos(th) * r, 66 + Math.sin(th) * r, 0]);
    }
    crook.unshift([0, 56, 0]);
    const staff = N('staff', [0, -2, 0], [
      T([[0, -100, 0], [0, 58, 0]], 2.1, GOLD),
      T(crook, 2.3, GOLD),
      E([0, 44, 0], [3.6, 4.5, 3.6], GOLD, { gloss: 0.5 }),
      E([0, 20, 0], [3, 3, 3], GOLD_D)
    ]);

    function arm(side) {             // side: -1 = rechterarm (links in beeld), +1 = linkerarm
      const n = side < 0 ? 'R' : 'L';
      const hand = N('ha' + n, [0, -22, 0], [E([0, -4, 0], [5.6, 6.2, 5.2], '#f6f1e8')], side > 0 ? [staff] : []);
      const el = N('el' + n, [0, -24, 0], [
        C([0, 0, 0], [0, -19, 0], 9.5, 12.5, RED),
        E([0, -19, 0], [12.5, 3.2, 12.5], WHITE, { scallop: 7 }),
        E([0, -16.5, 0], [12.8, 1.6, 12.8], GOLD)
      ], [hand]);
      return N('sh' + n, [side * 26, 12, -1], [C([0, 2, 0], [0, -24, 0], 10, 10, RED)], [el]);
    }

    const head = N('head', [0, 12, 1], [
      // haar achter + zijkant
      E([0, -2, -5], [16.5, 15, 13], '#ece6de'),
      E([0, 0, 0], [15, 16, 14], SKIN),
      E([0, -1.5, 14], [3.6, 3.2, 3.2], SKIN_D, { gloss: 0.25 }),
      E([-7, -4, 11], [4, 2.8, 2.5], '#f0a593', { flat: true }),
      E([7, -4, 11], [4, 2.8, 2.5], '#f0a593', { flat: true }),
      E([-5.4, 3.2, 12.6], [1.6, 2, 1], '#2a1812', { zb: 0.5 }),
      E([5.4, 3.2, 12.6], [1.6, 2, 1], '#2a1812', { zb: 0.5 }),
      E([-6, 7.4, 12.2], [5, 1.9, 2], BEARD, { rot: [0, 0, 0.18], zb: 0.6 }),
      E([6, 7.4, 12.2], [5, 1.9, 2], BEARD, { rot: [0, 0, -0.18], zb: 0.6 }),
      // baard: wolkje van bollen
      E([0, -15, 8], [16, 14, 9.5], BEARD),
      E([-10, -10, 7], [9.5, 12, 8], BEARD),
      E([10, -10, 7], [9.5, 12, 8], BEARD),
      E([0, -28, 8], [13, 13, 8], BEARD),
      E([-8, -36, 7], [8, 9, 6], BEARD),
      E([8, -35, 7], [8, 9, 6], BEARD),
      E([0, -45, 6.5], [7, 8, 5], BEARD),
      E([-5, -6.2, 14.6], [7, 3.4, 3.4], BEARD, { rot: [0, 0, -0.32], zb: 1 }),
      E([5, -6.2, 14.6], [7, 3.4, 3.4], BEARD, { rot: [0, 0, 0.32], zb: 1 }),
      // mijter
      F([0, 9, -0.5], 15.5, 13, [0, 34, -1], 18, 7, '#c22030', { bands: [{ v: 0.08, col: GOLD, w: 3 }] }),
      F([0, 34, -1], 18, 7, [0, 50, -1], 0.4, 0.4, '#c22030'),
      K([[-2.6, 10, 13.4], [2.6, 10, 13.4], [1.6, 49, 1.2], [-1.6, 49, 1.2]], GOLD, { zb: 2 }),
      K([[-9, 27.5, 10.6], [9, 27.5, 10.6], [9, 31, 9.8], [-9, 31, 9.8]], GOLD, { zb: 2.2 }),
      E([0, 51, -1], [2.6, 2.6, 2.6], GOLD, { gloss: 0.4 })
    ]);

    const chest = N('chest', [0, 34, 0], [
      E([0, 4, -1], [28, 18, 20], RED),
      // schoudermantel / pelerine met goudrand
      F([0, -6, -1], 31, 23, [0, 15, -1], 16, 12, RED_D, { bands: [{ v: 0.02, col: GOLD, w: 3 }] }),
      E([0, 12, 14], [4, 4, 2.4], GOLD, { gloss: 0.6, zb: 3 })
    ], [N('neck', [0, 20, 1], [], [head]), arm(-1), arm(1)]);

    const hip = N('hip', [0, 92, 0], [
      F([0, -90, 0], 30, 24, [0, 30, 0], 22, 17, WHITE, { fold: true }),
      F([0, -88, -6], 52, 40, [0, 38, -2], 27, 20, RED, { fold: true, bands: [{ v: 0.035, col: GOLD, w: 4 }], id: 'cape' }),
      // open voorkant van de mantel: wit onderkleed met brede gouden boorden
      K([[-13, -88, 36], [13, -88, 36], [6, 34, 20.5], [-6, 34, 20.5]], WHITE, { zb: 1 }),
      K([[-17, -87, 36.4], [-11, -87, 36.6], [-5, 34, 21], [-9, 34, 20.6]], GOLD, { zb: 1.5 }),
      K([[17, -87, 36.4], [11, -87, 36.6], [5, 34, 21], [9, 34, 20.6]], GOLD, { zb: 1.5 }),
      T([[-14, -84, 36.8], [-7, 34, 21.2]], 0.5, '#fff1b0', { zb: 1.6 }),
      T([[14, -84, 36.8], [7, 34, 21.2]], 0.5, '#fff1b0', { zb: 1.6 })
    ], [chest]);

    const feet = [-1, 1].map((sd) => N('ft' + (sd < 0 ? 'R' : 'L'), [sd * 10, 3.5, 12], [E([0, 0, 5], [6.5, 4.2, 10], '#3b2617', { gloss: 0.3 })]));
    const root = N('root', [0, 0, 0], [], [hip].concat(feet));
    const J = index(root);

    const cape = hip.prims.find((q) => q.id === 'cape');
    function pose(st) {
      const w = st.walk || 0, ph = st.ph || 0, t = st.t || 0;
      const breathe = Math.sin(t * 1.6) * 0.6;
      // mantel waait naar achteren bij lopen en wind
      const fl = w * 0.8 + (st.wind || 0) * 0.35;
      cape.c0 = [Math.sin(ph) * 2 * w, -88 + fl * 3, -6 - fl * 16];
      cape.a0 = [52 + fl * 8, 40 + fl * 6];
      J.hip.off = [0, Math.abs(Math.cos(ph)) * 2.6 * w + breathe * 0.3 - (st.crouch || 0) * 8, 0];
      J.hip.rot = [0.04 * w, Math.sin(ph) * 0.06 * w, Math.sin(ph) * 0.035 * w];
      J.chest.rot = [-0.03 * w + (st.lean || 0), -Math.sin(ph) * 0.05 * w, 0];
      J.ftR.pos = [-10, 3.5 + Math.max(0, Math.sin(ph)) * 4 * w, 8 + Math.sin(ph) * 10 * w];
      J.ftL.pos = [10, 3.5 + Math.max(0, -Math.sin(ph)) * 4 * w, 8 - Math.sin(ph) * 10 * w];
      // hoofd: kijken + knikje bij het lopen
      J.head.rot = [(st.nod || 0) + Math.cos(ph * 2) * 0.03 * w, st.look || 0, (st.tilt || 0)];
      // rechterarm: zwaaien bij het lopen of groeten
      const wave = st.wave || 0;
      const wv = Math.sin(t * 7.5);
      J.shR.rot = [Math.sin(ph) * 0.35 * w * (1 - wave) - wave * 0.4, 0, -0.12 - wave * 2.35];
      J.elR.rot = [-0.25 * (1 - wave) - wave * 0.15, 0, -wave * (0.5 + wv * 0.38)];
      J.haR.rot = [0, 0, -wave * wv * 0.2];
      // linkerarm houdt de staf voor zich, staf blijft rechtop
      const sa = -0.5 - Math.sin(ph) * 0.06 * w, ea = -0.85;
      J.shL.rot = [sa, 0, 0.18];
      J.elL.rot = [ea, 0, -0.1];
      J.haL.rot = [0, 0, 0];
      J.staff.rot = [-(sa + ea) - 0.04, 0, -0.1];
    }
    return { root: root, J: J, pose: pose, height: 205 };
  }

  /* ------------------------------------------------------------ */
  /*  Piet  (≈ 150 eenheden, groot hoofd, pofbroek, baret+veer)     */
  /*  o = { a: hoofdkleur, b: tweede kleur, cap, feather, prop }    */
  /* ------------------------------------------------------------ */
  function makePiet(o) {
    const A = o.a, Bc = o.b, CAP = o.cap, FEA = o.feather;
    const HAIR = '#3a2418';

    function leg(side) {
      const n = side < 0 ? 'R' : 'L';
      const foot = N('ft' + n, [0, -17, 0], [
        E([0, -1.5, 3.5], [5.6, 3.8, 9], '#2b1a26', { gloss: 0.35 }),
        E([0, 1.5, 7.5], [2.4, 1.6, 1], GOLD, { zb: 1 })
      ]);
      const knee = N('kn' + n, [0, -17, 0], [C([0, 0, 0], [0, -17, 0], 4.6, 3.8, Bc)], [foot]);
      return N('th' + n, [side * 8.5, -5, 0], [C([0, 0, 0], [0, -17, 0], 5.6, 4.6, Bc)], [knee]);
    }
    function arm(side) {
      const n = side < 0 ? 'R' : 'L';
      const hand = N('ha' + n, [0, -14.5, 0], [E([0, -2.5, 0], [4.8, 5.2, 4.6], '#f4efe6')]);
      const el = N('el' + n, [0, -15, 0], [
        C([0, 0, 0], [0, -13, 0], 4.6, 4.2, A),
        E([0, -12.5, 0], [5.4, 2, 5.4], '#f6f1e6', { scallop: 6 })
      ], [hand]);
      return N('sh' + n, [side * 17, 22, 0], [
        E([0, -4, 0], [8.5, 9.5, 8.5], Bc),
        K([[-4, 4, 7.2], [4, 4, 7.2], [4, -12, 6], [-4, -12, 6]].map((q) => [q[0] + side * 0, q[1], q[2]]), A, { zb: 0.5 }),
        C([0, -8, 0], [0, -15, 0], 5, 4.6, A)
      ], [el]);
    }

    const feather = N('feather', [-5, 4, -6], [
      K([[2, 0, 0], [10, 14, -4], [6, 32, -14], [-2, 40, -24], [-4, 26, -14], [-3, 10, -4]], FEA, { smooth: true, zb: -1 }),
      K([[0, 0, 2], [3, 14, -10], [0, 32, -18], [0, 40, -24], [-1, 26, -8], [0, 10, 2]], FEA, { smooth: true, zb: -1 }),
      T([[0, 0, 0], [3, 16, -6], [-1, 36, -20]], 0.6, '#fff2c0')
    ]);
    const cap = N('cap', [0, 14, -1], [
      E([0, 0, 0], [23, 6.5, 22], CAP, { rot: [0, 0, 0] }),
      E([0, -3.5, 0], [19.5, 3.2, 18.5], Bc)
    ], [feather]);
    const head = N('head', [0, 19, 1], [
      E([0, 5, -6], [21, 19.5, 17], HAIR),
      E([-11, 3, -10], [9, 12, 9], HAIR),
      E([11, 3, -10], [9, 12, 9], HAIR),
      E([-8, 15, 1], [9, 6, 9], HAIR),
      E([8, 15, 1], [9, 6, 9], HAIR),
      E([0, 0, 0], [19, 19, 17], SKIN),
      E([-18.5, -1, 0], [3, 4.6, 3], SKIN_D),
      E([18.5, -1, 0], [3, 4.6, 3], SKIN_D),
      E([0, 9, 13], [15, 6, 6], HAIR, { zb: 0.2 }),          // pony
      E([-6.4, 1.8, 15.6], [2.1, 2.7, 1.1], '#1e120d', { zb: 0.6 }),
      E([6.4, 1.8, 15.6], [2.1, 2.7, 1.1], '#1e120d', { zb: 0.6 }),
      E([-5.8, 2.8, 16.6], [0.8, 0.9, 0.5], '#ffffff', { zb: 0.9, flat: true }),
      E([7, 2.8, 16.6], [0.8, 0.9, 0.5], '#ffffff', { zb: 0.9, flat: true }),
      E([-6.6, 6.4, 15.4], [3.2, 0.9, 1], HAIR, { zb: 0.7, rot: [0, 0, 0.12] }),
      E([6.6, 6.4, 15.4], [3.2, 0.9, 1], HAIR, { zb: 0.7, rot: [0, 0, -0.12] }),
      E([0, -3, 17.6], [3.3, 2.9, 2.6], SKIN_D, { gloss: 0.25, zb: 1 }),
      E([-10.5, -5, 13], [4.2, 2.8, 2], '#ec8f7f', { flat: true, zb: 0.4 }),
      E([10.5, -5, 13], [4.2, 2.8, 2], '#ec8f7f', { flat: true, zb: 0.4 }),
      // roetvegen
      E([9, -9, 13.5], [3.2, 2, 1], '#7a5a4c', { flat: true, zb: 0.45 }),
      E([-12, 3, 11], [2.4, 1.6, 1], '#7a5a4c', { flat: true, zb: 0.45 }),
      K([[-5.5, -8.4, 16.4], [0, -12.2, 17], [5.5, -8.4, 16.4], [0, -10, 17.2]], '#8a2a24', { smooth: true, zb: 1.2 })
    ], [cap]);

    const chestKids = [N('neck', [0, 27, 0], [], [head]), arm(-1), arm(1)];
    if (o.prop === 'sack') {
      chestKids.push(N('sack', [10, 20, -15], [
        E([0, 0, 0], [19, 18, 15], '#d9b97c'),
        E([-9, 14, 4], [7, 5.5, 6], '#cfae70'),
        T([[-12, 11, 6], [-6, 13, 8]], 1.2, '#8a5a2a')
      ]));
    } else if (o.prop === 'gift') {
      chestKids.push(N('gift', [0, 8, 20], [
        B([0, 0, 0], [13, 9, 9.5], '#c81f2c', { ribbon: '#f2c13c', rw: 3 }),
        B([0, 15, -1], [9, 6, 7], '#f0b62a', { ribbon: '#c81f2c', rw: 2.4 }),
        E([-3, 22, -1], [3.5, 2.2, 2.4], '#c81f2c', { rot: [0, 0, 0.5] }),
        E([3, 22, -1], [3.5, 2.2, 2.4], '#c81f2c', { rot: [0, 0, -0.5] })
      ]));
    }
    const chest = N('chest', [0, 10, 0], [
      E([0, 10, 0], [17.5, 17, 13.5], A),
      K([[-4.5, 25, 10], [4.5, 25, 10], [5, -2, 12.5], [-5, -2, 12.5]], Bc, { zb: 0.8 }),
      E([0, 18, 13.4], [1.6, 1.6, 1], GOLD, { zb: 1.2 }),
      E([0, 10, 14.2], [1.6, 1.6, 1], GOLD, { zb: 1.2 }),
      E([0, 2, 13.4], [1.6, 1.6, 1], GOLD, { zb: 1.2 }),
      E([0, 27, 0], [16.5, 5, 14.5], '#fbf6ec', { scallop: 9 })
    ], chestKids);
    const hip = N('hip', [0, 41, 0], [
      E([-9, 0, 0], [14, 14, 15.5], A),
      E([9, 0, 0], [14, 14, 15.5], Bc),
      E([0, 6, 0], [17.5, 3.2, 14], '#5a3a2a')
    ], [chest, leg(-1), leg(1)]);
    const root = N('root', [0, 0, 0], [], [hip]);
    const J = index(root);

    function pose(st) {
      const w = st.walk || 0, ph = st.ph || 0, t = st.t || 0;
      const jump = st.jump || 0;            // 0..1 hurken/springhouding
      J.hip.off = [0, Math.abs(Math.cos(ph)) * 3 * w + Math.sin(t * 2) * 0.4 - jump * 6, 0];
      J.hip.rot = [0, Math.sin(ph) * 0.12 * w, 0];
      J.chest.rot = [0.06 * w + jump * 0.25, -Math.sin(ph) * 0.12 * w, Math.sin(ph) * 0.03 * w];
      const sw = Math.sin(ph) * w;
      J.thR.rot = [-sw * 0.62 - jump * 0.7, 0, 0];
      J.thL.rot = [sw * 0.62 - jump * 0.7, 0, 0];
      J.knR.rot = [Math.max(0, Math.cos(ph)) * 0.9 * w + jump * 1.2, 0, 0];
      J.knL.rot = [Math.max(0, -Math.cos(ph)) * 0.9 * w + jump * 1.2, 0, 0];
      J.ftR.rot = [-jump * 0.5, 0, 0];
      J.ftL.rot = [-jump * 0.5, 0, 0];
      J.head.rot = [Math.cos(ph * 2) * 0.04 * w + (st.nod || 0), st.look || 0, Math.sin(ph) * 0.05 * w];
      J.cap.rot = [0.12, 0, -0.2];
      const wind = st.wind || 0;
      J.feather.rot = [-0.3 + Math.sin(t * 3.1) * 0.08 - Math.abs(Math.cos(ph)) * 0.12 * w + wind * 0.25, 0, 0.15 + Math.sin(t * 2.3) * 0.07];
      const up = st.armsUp || 0;
      if (o.prop === 'sack') {
        // rechterarm houdt de zak over de schouder vast
        J.shL.rot = [-2.5, 0, 0.35]; J.elL.rot = [-1.2, 0, 0];
        J.shR.rot = [-sw * 0.55 - up * 2.6, 0, -0.15 - up * 0.3]; J.elR.rot = [-0.3 - up * 0.2, 0, 0];
      } else if (o.prop === 'gift') {
        const lift = up;
        J.shR.rot = [-0.95 - lift * 1.5, 0, -0.25]; J.elR.rot = [-0.75 + lift * 0.5, 0, 0.5];
        J.shL.rot = [-0.95 - lift * 1.5, 0, 0.25]; J.elL.rot = [-0.75 + lift * 0.5, 0, -0.5];
        J.gift.off = [0, Math.abs(Math.cos(ph)) * 1.2 * w + lift * 34, -lift * 10];
      } else {
        J.shR.rot = [-sw * 0.55, 0, -0.15]; J.elR.rot = [-0.3, 0, 0];
        J.shL.rot = [sw * 0.55, 0, 0.15]; J.elL.rot = [-0.3, 0, 0];
      }
    }
    return { root: root, J: J, pose: pose, height: 150 };
  }

  /* ------------------------------------------------------------ */
  /*  Het paard  (schimmel, ≈ 185 hoog, kijkt bij yaw 0 naar +x)    */
  /* ------------------------------------------------------------ */
  function makeHorse() {
    const WH = '#f3efe9', W2 = '#e6e0d8', MANE = '#ebe6df', RED = '#c11f2e', HOOF = '#3a3036';
    function leg(name, x, z, hind) {
      const hoof = N(name + 'h', [hind ? -2 : 0, -35, 0], [
        F([0, -5, 0], 7.6, 7, [0, 4, 0], 6.2, 5.8, HOOF),
        F([0, 4, 0], 6.6, 6.2, [0, 10, 0], 6.8, 6.4, '#f6f1ea')
      ]);
      const low = N(name + 'k', hind ? [5, -34, 0] : [0, -34, 0], [
        C([0, 0, 0], [hind ? -2 : 0, -35, 0], 6.4, 5.4, WH),
        E([0, 0, 0], [7.4, 7.4, 7], W2),
        E([hind ? -2 : 0, -30, 0], [6.6, 6, 6.4], W2)
      ], [hoof]);
      const up = hind
        ? N(name, [x, -12, z], [C([0, 6, 0], [5, -34, 0], 16, 7.5, WH)], [low])
        : N(name, [x, -14, z], [C([0, 6, 0], [0, -34, 0], 13, 7.2, WH)], [low]);
      return up;
    }
    const maneN = [];
    for (let i = 0; i < 7; i++) {
      const u = i / 6;
      maneN.push(E([-7 + u * 24, 18 + u * 26, -1], [10 - u * 2.5, 13, 7], MANE, { rot: [0, 0, 0.6], noLine: i > 0 }));
    }
    const head = N('head', [24, 38, 0], [
      E([4.9, 1.2, 0], [20.7, 18.3, 15.9], WH),
      E([29.3, -3.7, 0], [24.4, 14.6, 13.4], WH),
      E([48.8, -7.3, 0], [15.2, 13.4, 12.8], '#efe8e1'),
      E([59.8, -6.1, 7.3], [2.9, 3.7, 2.2], '#6d5552', { zb: 1 }),
      E([59.8, -6.1, -7.3], [2.9, 3.7, 2.2], '#6d5552', { zb: 1 }),
      E([53.7, -18.3, 0], [11, 3.9, 9.8], '#e3d8d0'),
      E([11, 7.3, 14.2], [3.7, 4.4, 2.2], '#1b1010', { zb: 1 }),
      E([11, 7.3, -14.2], [3.7, 4.4, 2.2], '#1b1010', { zb: 1 }),
      E([12.2, 9, 15.9], [1.1, 1.2, 0.6], '#ffffff', { zb: 1.3, flat: true }),
      E([12.2, 9, -15.9], [1.1, 1.2, 0.6], '#ffffff', { zb: 1.3, flat: true }),
      E([-2.4, 18.3, 0], [9.8, 7.3, 9.8], MANE),
      E([4.9, 15.9, 3.7], [7.3, 4.9, 6.1], '#ddd6cc', { rot: [0, 0, -0.6] }),
      // hoofdstel
      T([[36.6, 12.2, 14.9], [39, -19.5, 14.2], [39, -19.5, -14.2], [36.6, 12.2, -14.9]], 1.6, RED, { zb: 0.6 }),
      T([[14.6, 15.9, 15.9], [48.8, 3.7, 13.9]], 1.5, RED, { zb: 0.6 }),
      T([[14.6, 15.9, -15.9], [48.8, 3.7, -13.9]], 1.5, RED, { zb: 0.6 }),
      T([[2.4, 17.1, 14.6], [7.3, -12.2, 15.9]], 1.4, RED, { zb: 0.6 }),
      T([[2.4, 17.1, -14.6], [7.3, -12.2, -15.9]], 1.4, RED, { zb: 0.6 }),
      E([37.8, -2.4, 14.6], [2.9, 2.9, 1.5], GOLD, { zb: 1 }),
      E([37.8, -2.4, -14.6], [2.9, 2.9, 1.5], GOLD, { zb: 1 })
    ], [
      N('earL', [0, 15, 8], [F([0, 0, 0], 5.4, 3.6, [-5, 19, 1], 0.4, 0.4, WH)]),
      N('earR', [0, 15, -8], [F([0, 0, 0], 5.4, 3.6, [-5, 19, -1], 0.4, 0.4, WH)])
    ]);
    const neck = N('neck', [42, 8, 0], [C([0, -4, 0], [22, 38, 0], 21, 13, WH), E([4, 4, 0], [19, 20, 18], WH)].concat(maneN), [head]);
    const tail = N('tail', [-70, 16, 0], []);
    const body = N('body', [0, 90, 0], [
      E([0, 0, 0], [62, 32, 28], WH),
      E([44, -1, 0], [28, 30, 26], WH),
      E([-46, 3, 0], [30, 32, 28.5], WH),
      // dekkleed + zadel
      W([-6, 1, 0], -36, 26, 33.6, 30, -2.05, 2.05, RED, { zb: 0.5, trim: GOLD, tw: 2.6, tassel: true }),
      T([[30, 22, 25], [62, 2, 22], [70, -6, 0], [62, 2, -22], [30, 22, -25]], 2, RED, { zb: 0.8 }),
      E([66, -2, 15], [2.4, 2.4, 1.4], GOLD, { zb: 1 }), E([66, -2, -15], [2.4, 2.4, 1.4], GOLD, { zb: 1 }),
      E([-6, 31, 0], [15, 4.5, 17], '#8d1522', { zb: 1 }),
      E([-6, 33.5, 0], [10, 2.5, 12], '#a31a28', { zb: 1.2 }),
      T([[22, 26, 12], [26, -14, 26]], 1.3, RED, { zb: 1 }),
      T([[22, 26, -12], [26, -14, -26]], 1.3, RED, { zb: 1 })
    ], [neck, tail,
      leg('legFR', 46, 13, false), leg('legFL', 46, -13, false),
      leg('legBR', -48, 13, true), leg('legBL', -48, -13, true)]);
    const root = N('root', [0, 0, 0], [], [body]);
    const J = index(root);
    const tailPrims = [T([], 4.5, MANE)];
    for (let i = 0; i < 7; i++) tailPrims.push(E([0, 0, 0], [7.5 - i * 0.4, 12, 6 - i * 0.3], MANE, { noLine: i > 0 }));
    tail.prims = tailPrims;

    function pose(st) {
      const t = st.t || 0, w = st.walk || 0, ph = st.ph || 0;
      J.body.off = [0, Math.sin(t * 1.3) * 0.6 + Math.abs(Math.sin(ph)) * 2 * w, 0];
      J.body.rot = [0, 0, Math.sin(t * 1.3) * 0.004];
      // nek en hoofd: rustig knikken, af en toe omhoog kijken
      const lift = st.lift || 0, nod = st.nod || 0;
      J.neck.rot = [0, (st.look || 0) * 0.5, -0.05 + lift * 0.25 - nod * 0.25 + Math.sin(t * 0.9) * 0.03];
      J.head.rot = [0, (st.look || 0) * 0.6, -0.9 + lift * 0.2 + nod * 0.35 + Math.sin(t * 0.9 + 0.5) * 0.04];
      const ef = st.earFlick || 0;
      J.earL.rot = [0, 0, -0.15 + ef * 0.5];
      J.earR.rot = [0, 0, -0.15 + Math.sin(t * 0.7) * 0.1];
      // benen (stappen of één hoef laten stampen)
      const sw = Math.sin(ph) * w, stomp = st.stomp || 0;
      J.legFR.rot = [0, 0, sw * 0.35 + stomp * 0.55];
      J.legFRk.rot = [0, 0, -Math.max(0, sw) * 0.6 - stomp * 1.2];
      J.legFL.rot = [0, 0, -sw * 0.35];
      J.legFLk.rot = [0, 0, -Math.max(0, -sw) * 0.6];
      J.legBR.rot = [0, 0, -sw * 0.3];
      J.legBRk.rot = [0, 0, Math.max(0, -sw) * 0.5];
      J.legBL.rot = [0, 0, sw * 0.3];
      J.legBLk.rot = [0, 0, Math.max(0, sw) * 0.5];
      // staart: zwiepen in de wind en af en toe een slag
      const swish = st.swish || 0, wind = st.wind || 0;
      const pts = [];
      for (let i = 0; i <= 8; i++) {
        const u = i / 8;
        const zz = Math.sin(t * 2.2 - u * 2.4) * 12 * u * (0.4 + swish) + wind * 10 * u;
        pts.push([-u * 18 - u * u * 4, -u * 62 + u * u * 6, zz]);
      }
      tailPrims[0].pts = pts.slice(0, 3);
      for (let i = 0; i < 7; i++) {
        const fu = 1.6 + i, k = Math.floor(fu), f = fu - k, a = pts[k], b = pts[Math.min(8, k + 1)];
        tailPrims[i + 1].c = [a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f, a[2] + (b[2] - a[2]) * f];
        tailPrims[i + 1].rot = [0, 0, -0.3 + Math.atan2(b[0] - a[0], -(b[1] - a[1])) * 0.6];
      }
    }
    return { root: root, J: J, pose: pose, height: 185 };
  }

  window.Characters = { makeSint: makeSint, makePiet: makePiet, makeHorse: makeHorse };
})();

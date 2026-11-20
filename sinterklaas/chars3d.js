/* =====================================================================
   Chars3D — de Blender-modellen (models/chars_glb.js) in three.js.
   - Eén WebGL-renderer; elk figuur wordt apart gerenderd in een uitsnede
     en via Sprite.draw() in de 2D-scène gezet (omlijning + randlicht).
   - Poses worden opgegeven in "karakterruimte" (x rechts, y omhoog,
     z naar de kijker), per bot als [rx, ry, rz] (radialen, volgorde YXZ)
     en optioneel een verschuiving in cm — net als de oude puppet-nodes.
   ===================================================================== */
(function () {
  'use strict';
  const C3 = window.Chars3D = { ready: false, failed: false, models: {} };
  if (!window.THREE || !THREE.GLTFLoader || !window.CHAR_GLB) { C3.failed = true; return; }

  const SIZE = 1024;
  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true, premultipliedAlpha: false, preserveDrawingBuffer: true });
  } catch (e) { C3.failed = true; return; }
  renderer.setPixelRatio(1);
  renderer.setSize(SIZE, SIZE, false);
  renderer.setClearColor(0x000000, 0);
  renderer.outputEncoding = THREE.sRGBEncoding;
  renderer.toneMapping = THREE.NoToneMapping;

  const scene = new THREE.Scene();
  const pitchG = new THREE.Group(), yawG = new THREE.Group();
  pitchG.add(yawG); scene.add(pitchG);
  // licht: warm hoofdlicht linksvoor-boven, koel maanlicht van achteren, warme gloed van onder-rechts
  scene.add(new THREE.HemisphereLight(0x7f92c8, 0x6a3a26, 0.5));
  const key = new THREE.DirectionalLight(0xffdcae, 1.35); key.position.set(-0.55, 0.75, 0.75); scene.add(key);
  const moon = new THREE.DirectionalLight(0xc8d6ff, 1.0); moon.position.set(-0.8, 0.55, -0.9); scene.add(moon);
  const lamp = new THREE.DirectionalLight(0xff9a50, 0.65); lamp.position.set(0.7, -0.15, 0.6); scene.add(lamp);
  const cam = new THREE.OrthographicCamera(-1, 1, 1, -1, 1, 5000);
  cam.position.set(0, 0, 2500); cam.lookAt(0, 0, 0);

  const _q = new THREE.Quaternion(), _qd = new THREE.Quaternion(), _qi = new THREE.Quaternion(), _e = new THREE.Euler(0, 0, 0, 'YXZ'), _v = new THREE.Vector3();

  function b64ToBuf(b64) {
    const bin = atob(b64), n = bin.length, u = new Uint8Array(n);
    for (let i = 0; i < n; i++) u[i] = bin.charCodeAt(i);
    return u.buffer;
  }

  function setup(name, gltf) {
    const root = new THREE.Group();
    const sc = gltf.scene;
    sc.scale.setScalar(100);              // meters → cm (karakter-eenheden)
    root.add(sc);
    root.updateMatrixWorld(true);
    const bones = {}, props = {};
    sc.traverse((o) => {
      if (o.isBone) bones[o.name] = o;
      if (o.isMesh) {
        o.frustumCulled = false;
        const ms = Array.isArray(o.material) ? o.material : [o.material];
        for (const mt of ms) {
          if (mt.map) mt.map.encoding = THREE.sRGBEncoding;
          mt.envMapIntensity = 0;
          if ('sheen' in mt) mt.sheen = 0;
          if (/glint/.test(mt.name)) { mt.emissive = new THREE.Color(1, 1, 1); mt.emissiveIntensity = 1.2; }
        }
      }
      if (o.name === 'gift' || o.name === 'sack') props[o.name] = o;
    });
    // rustwaarden + oriëntatie van de ouder in karakterruimte
    const rest = {};
    const rootQ = new THREE.Quaternion(); root.getWorldQuaternion(rootQ);
    for (const n in bones) {
      const b = bones[n];
      const qp = new THREE.Quaternion();
      if (b.parent) b.parent.getWorldQuaternion(qp);
      rest[n] = { q: b.quaternion.clone(), p: b.position.clone(), qp: qp, qpi: qp.clone().invert() };
    }
    C3.models[name] = { root: root, bones: bones, props: props, rest: rest };
  }

  /* pose: { rot: {bot: [rx,ry,rz]}, off: {bot: [x,y,z] cm}, hide: {prop: bool} } */
  C3.pose = function (name, P) {
    const M = C3.models[name]; if (!M) return;
    for (const n in M.bones) {
      const b = M.bones[n], R = M.rest[n];
      const r = P.rot && P.rot[n];
      if (r) {
        _e.set(r[0] || 0, r[1] || 0, r[2] || 0, 'YXZ');
        _qd.setFromEuler(_e);
        // draai om assen van de karakterruimte, gemeten in de ruststand van de ouder
        _q.copy(R.qpi).multiply(_qd).multiply(R.qp).multiply(R.q);
        b.quaternion.copy(_q);
      } else b.quaternion.copy(R.q);
      const o = P.off && P.off[n];
      if (o) {
        _v.set(o[0] * 0.01, o[1] * 0.01, o[2] * 0.01).applyQuaternion(R.qpi);
        b.position.copy(R.p).add(_v);
      } else b.position.copy(R.p);
    }
    for (const k in M.props) M.props[k].visible = !(P.hide && P.hide[k]);
  };

  /* render naar de 2D-context, view = { x, y, s, yaw, pitch }, box = sprite-maat */
  C3.draw = function (ctx, name, view, box) {
    const M = C3.models[name]; if (!M) return false;
    window.Sprite.draw(ctx, view, Object.assign({ id: name }, box, {
      paint: function (g, W, H, info) {
        const w = Math.min(W, SIZE), h = Math.min(H, SIZE);
        const k = 1 / (view.s * info.sc);
        cam.left = (info.fx - info.Fx) * k; cam.right = (info.fx + w - info.Fx) * k;
        cam.top = (info.Fy - info.fy) * k; cam.bottom = (info.Fy - info.fy - h) * k;
        cam.updateProjectionMatrix();
        yawG.rotation.y = view.yaw || 0;
        pitchG.rotation.x = view.pitch || 0;
        yawG.add(M.root);
        renderer.setViewport(0, 0, w, h);
        renderer.setScissor(0, 0, w, h);
        renderer.setScissorTest(true);
        renderer.clear();
        renderer.render(scene, cam);
        yawG.remove(M.root);
        g.drawImage(renderer.domElement, 0, SIZE - h, w, h, 0, 0, w, h);
      }
    }));
    return true;
  };

  /* Laagste voet (cm, in karakterruimte) in de huidige pose. */
  const _fp = new THREE.Vector3();
  C3.footY = function (name, feet) {
    const M = C3.models[name]; if (!M) return 0;
    M.root.updateMatrixWorld(true);
    let lo = Infinity;
    for (const b of feet) { M.bones[b].getWorldPosition(_fp); if (_fp.y < lo) lo = _fp.y; }
    return lo;
  };

  /* Paslengte (cm per volledige looppas) gemeten aan het skelet: laat het figuur
     één cyclus lopen en kijk hoe snel de voet die op de grond staat (de laagste)
     naar achteren schuift t.o.v. het lichaam. fwd = 'z' (Pieten) of 'x' (paard). */
  C3.measureStride = function (name, poseAt, feet, fwd) {
    const M = C3.models[name]; if (!M) return 0;
    const N = 120, S = [];
    for (let i = 0; i <= N; i++) {
      C3.pose(name, poseAt(i / N * Math.PI * 2));
      M.root.updateMatrixWorld(true);
      S.push(feet.map((b) => { M.bones[b].getWorldPosition(_fp); return [fwd === 'x' ? _fp.x : _fp.z, _fp.y]; }));
    }
    // alleen de allerlaagste voet telt, en alleen als die dat in beide samples is; mediaan tegen uitschieters
    const vs = [];
    const lowest = (row) => { let k = 0; for (let j = 1; j < row.length; j++) if (row[j][1] < row[k][1]) k = j; return k; };
    for (let i = 0; i < N; i++) {
      const k0 = lowest(S[i]), k1 = lowest(S[i + 1]);
      if (k0 === k1) vs.push(S[i][k0][0] - S[i + 1][k0][0]);
    }
    C3.pose(name, { rot: {}, off: {} });
    if (!vs.length) return 0;
    vs.sort((a, b) => a - b);
    return vs[vs.length >> 1] * N;
  };

  /* hang model `child` aan bot `bone` van model `parent` (ruiter op het paard).
     pos/yaw: plaats in de ruststand, in karakterruimte van de ouder (cm). */
  function attach(child, parent, bone, pos, yaw) {
    const P = C3.models[parent], Cm = C3.models[child];
    if (!P || !Cm) return;
    P.root.updateMatrixWorld(true);
    const b = P.bones[bone];
    const T = new THREE.Matrix4().compose(new THREE.Vector3(pos[0], pos[1], pos[2]),
      new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), yaw), new THREE.Vector3(1, 1, 1));
    const off = b.matrixWorld.clone().invert().multiply(T);
    Cm.root.matrixAutoUpdate = false;
    Cm.root.matrix.copy(off);
    b.add(Cm.root);
  }

  const loader = new THREE.GLTFLoader();
  const names = Object.keys(window.CHAR_GLB);
  let left = names.length;
  for (const n of names) {
    loader.parse(b64ToBuf(window.CHAR_GLB[n]), '', (gltf) => {
      setup(n, gltf);
      if (--left === 0) {
        attach('sint_rider', 'paard', 'body', [-6, 41.5, 0], Math.PI / 2);
        C3.ready = true;
      }
    }, (err) => { console.error('glb', n, err); C3.failed = true; });
  }
})();

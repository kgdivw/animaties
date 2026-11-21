"""Film-lus, uitgevoerd vanuit look_still.py --film (deelt diens namespace: scene, r, cam, sky, FR, DR, ...).

Per frame: camera, zon, alle bewegende objecten (lokale pos/quat/schaal + zichtbaarheid, ook voor kinderen),
lampkleuren, uitfadende ringen, golfslagbad-hoogtes en spetters uit de bake zetten, renderen, en flits/fade
erover leggen zoals in three.js. Bestaande frames worden overgeslagen, dus afbreken en herstarten mag.
"""
import bpy, os, math, time
import numpy as np
from mathutils import Quaternion

OUT = os.path.join(F, 'frames'); os.makedirs(OUT, exist_ok=True)
NO, NM, NW = len(BAKE['objects']), len(BAKE['mats']), BAKE['wave_n']
O0, M0, W0 = 13, 13 + NO * 11, 13 + NO * 11 + NM * 5

# ---- objecten uit de bake terugvinden (glTF-namen)
objs = [scene.objects.get(n) for n in BAKE['objects']]
missing = [n for n, o in zip(BAKE['objects'], objs) if o is None]
if missing: print('FILM let op: niet gevonden', len(missing), missing[:8])
for o in objs:
    if o: o.rotation_mode = 'QUATERNION'
vis = FR[:, O0 + 10:M0:11]                                  # zichtbaarheid per frame per object
hides = [k for k in range(NO) if objs[k] and vis[:, k].min() < .5]
desc = {k: [objs[k]] + list(objs[k].children_recursive) for k in hides}
affected = {o for k in hides for o in desc[k]}

# ---- golfslagbad
wp = scene.objects.get(BAKE['wavepool'])
if wp and len(wp.data.vertices) == NW:
    WCO = np.empty(NW * 3, np.float32); wp.data.vertices.foreach_get('co', WCO)
else:
    print('FILM let op: golfslagbad niet bruikbaar', wp and len(wp.data.vertices), NW); wp = None

# ---- materialen die bewegen: lampen (kleur/sterkte) en de rest (alpha)
def principled(m):
    return next((n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None) if m and m.node_tree else None
mtrack = [(k,) + TRACK[k] + (principled(TRACK[k][1]),) for k in range(NM) if k in TRACK]

# ---- spetters: punten + geometry nodes (bol per punt, schaal = attribuut r)
dme = bpy.data.meshes.new('drops_pts'); dob = bpy.data.objects.new('drops', dme); scene.collection.objects.link(dob)
ng = bpy.data.node_groups.new('drops_gn', 'GeometryNodeTree')
ng.interface.new_socket('Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
ng.interface.new_socket('Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
N_ = ng.nodes; L_ = ng.links
gi, go = N_.new('NodeGroupInput'), N_.new('NodeGroupOutput')
ico = N_.new('GeometryNodeMeshIcoSphere'); ico.inputs['Radius'].default_value = 1.0; ico.inputs['Subdivisions'].default_value = 2
smooth = N_.new('GeometryNodeSetShadeSmooth')
def m_drops_eevee():                    # Eevee: doorzichtig water wordt een spiegel -> wit schuimend water
    s = NT('L_drops_ee')
    sh = s.bsdf('#eefbff', .3, **{'Subsurface Weight': .6, 'Coat Weight': .5, 'Emission Color': hexlin('#cfefff'), 'Emission Strength': .25})
    return s.done(sh)
smat = N_.new('GeometryNodeSetMaterial')
smat.inputs['Material'].default_value = m_drops_eevee() if r.engine.startswith('BLENDER_EEVEE') else m_clear_water('L_drops', '#f2fdff')
na = N_.new('GeometryNodeInputNamedAttribute'); na.data_type = 'FLOAT'; na.inputs['Name'].default_value = 'r'
iop = N_.new('GeometryNodeInstanceOnPoints')
L_.new(ico.outputs['Mesh'], smooth.inputs['Geometry']); L_.new(smooth.outputs['Geometry'], smat.inputs['Geometry'])
L_.new(smat.outputs['Geometry'], iop.inputs['Instance']); L_.new(gi.outputs[0], iop.inputs['Points'])
L_.new(na.outputs['Attribute'], iop.inputs['Scale']); L_.new(iop.outputs['Instances'], go.inputs[0])
dob.modifiers.new('drops', 'NODES').node_group = ng


def set_drops(i):
    k = DOFF[i]; n = int(DR[k]); d = DR[k + 1:k + 1 + n * 4].reshape(-1, 4)
    dme.clear_geometry()
    if n:
        dme.vertices.add(n)
        co = np.stack([d[:, 0], -d[:, 2], d[:, 1]], 1).astype(np.float32)
        dme.vertices.foreach_set('co', co.ravel())
        dme.attributes.new('r', 'FLOAT', 'POINT').data.foreach_set('value', np.maximum(d[:, 3], .02))
    dme.update()


RX90 = Quaternion((math.cos(math.pi / 4), math.sin(math.pi / 4), 0, 0))


def apply(i):
    f = FR[i]
    # camera
    cam.location = (f[0], -f[2], f[1])
    cam.rotation_quaternion = RX90 @ Quaternion((f[6], f[3], f[4], f[5]))
    cd.angle_y = math.radians(float(f[7]))
    # zon
    d = (f[8], -f[10], f[9]); n = math.sqrt(sum(x * x for x in d)) or 1
    try:
        sky.sun_elevation = max(math.asin(max(min(d[2] / n, 1), -1)), math.radians(.5)); sky.sun_rotation = math.atan2(d[0], d[1])
    except Exception: pass
    # objecten (three y-up -> Blender z-up, per lokale transformatie)
    for k, o in enumerate(objs):
        if not o: continue
        a = f[O0 + k * 11:O0 + k * 11 + 10]
        o.location = (a[0], -a[2], a[1])
        o.rotation_quaternion = (a[6], a[3], -a[5], a[4])
        o.scale = (a[7], a[9], a[8])
    hidden = set()
    for k in hides:
        if f[O0 + k * 11 + 10] < .5: hidden.update(desc[k])
    for o in affected:
        h = o in hidden
        if o.hide_render != h: o.hide_render = h; o.hide_viewport = h
    # materialen
    for k, kind, m, p in mtrack:
        a = f[M0 + k * 5:M0 + k * 5 + 5]
        if not p: continue
        if kind == 'lamp':
            p.inputs['Emission Color'].default_value = (a[0], a[1], a[2], 1); p.inputs['Emission Strength'].default_value = float(a[3]) * 4
        else:
            p.inputs['Alpha'].default_value = float(a[4])
    # golfslagbad: lokale three-y = Blender-z
    if wp:
        WCO[2::3] = f[W0:W0 + NW]; wp.data.vertices.foreach_set('co', WCO); wp.data.update()
    set_drops(i)
    return float(f[11]), float(f[12])


def overlay(path, flash, fade):          # zelfde als de canvas-overlay in three.js: wit erover, dan zwart
    img = bpy.data.images.load(path); px = np.empty(len(img.pixels), np.float32); img.pixels.foreach_get(px)
    a = px.reshape(-1, 4); a[:, :3] = (a[:, :3] * (1 - flash) + flash) * (1 - fade)
    img.pixels.foreach_set(px); img.save(); bpy.data.images.remove(img)


def black(path):
    img = bpy.data.images.new('black', r.resolution_x, r.resolution_y)
    px = np.zeros(r.resolution_x * r.resolution_y * 4, np.float32); px[3::4] = 1; img.pixels.foreach_set(px)
    img.filepath_raw = path; img.file_format = 'PNG'; img.save(); bpy.data.images.remove(img)


a, b = 0, NB
if args.range:
    s0, s1 = args.range.split(':'); a = int(s0 or 0); b = min(int(s1 or NB), NB)
todo = [i for i in range(a, b) if not os.path.exists(os.path.join(OUT, 'f_%05d.png' % i))]
print('FILM %d frames (%d..%d), %d te doen, %s, %dx%d' % (b - a, a, b - 1, len(todo), r.engine, r.resolution_x, r.resolution_y), flush=True)
r.use_persistent_data = True
t_start = time.time()
for n, i in enumerate(todo):
    t0 = time.time()
    final = os.path.join(OUT, 'f_%05d.png' % i); tmp = os.path.join(OUT, '_tmp_%05d.png' % i)
    fl, fd = apply(i)
    if fd > .999: black(tmp)
    else:
        r.filepath = tmp; bpy.ops.render.render(write_still=True)
        if fl > .002 or fd > .002: overlay(tmp, fl, fd)
    os.replace(tmp, final)
    el = time.time() - t_start; left = el / (n + 1) * (len(todo) - n - 1)
    print('FRAME %d (%d/%d) %.1fs  nog ~%dm%02ds' % (i, n + 1, len(todo), time.time() - t0, left // 60, left % 60), flush=True)
print('FILM klaar', flush=True)

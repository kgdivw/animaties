"""
De film: het hele plein rondom, een camera die na elke scène 90° draait, en per
scène Sint (te paard) en de Pieten.

  blender -b --python film.py -- --out ../_film/proef --engine workbench --res 50 --step 2
  blender -b --python film.py -- --out ../_film/final --engine cycles --res 100 --samples 64 --start 0 --end 2350

Tijdlijn (seconden), cyclus van 94 s:
   0–36  scène 1  noord: over het dak, Pieten in de schoorsteen   (zelfde verloop als de browser)
  36–39  camera draait naar oost
  39–54  scène 2  oost: stadhuis, Sint rijdt over het plein, pepernoten, radslag
  54–57  draai naar zuid
  57–73  scène 3  zuid: de pakjesboot aan de kade, Piet sjouwt een pakje van boord
  73–76  draai naar west
  76–91  scène 4  west: bakkerij, Piet klimt via de ladder naar een raam
  91–94  draai terug naar noord (naadloos naar het begin)
"""
import bpy, sys, os, math, json, argparse, random, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument('--out', default=os.path.join(HERE, '..', '_film', 'proef'))
ap.add_argument('--engine', default='workbench')
ap.add_argument('--res', type=int, default=50)
ap.add_argument('--samples', type=int, default=32)
ap.add_argument('--fps', type=int, default=25)
ap.add_argument('--start', type=int, default=0)
ap.add_argument('--end', type=int, default=-1)
ap.add_argument('--step', type=int, default=1)
ap.add_argument('--frames', default='')        # komma-lijst van losse frames (voor controle)
ap.add_argument('--save', default='')
ap.add_argument('--device', default='cpu')    # cpu | gpu (automatisch) | optix | cuda | hip | metal | oneapi
args = ap.parse_args(argv)

bpy.ops.wm.read_factory_settings(use_empty=True)
from mathutils import Vector, Matrix, Quaternion
import bl_lib as L
import scene_town as ST
import scene_sides as SS
import build_characters as BC
import poses as PO

TOTAL = 94.0
SC = {'s1': (0.0, 36.0), 's2': (39.0, 54.0), 's3': (57.0, 73.0), 's4': (76.0, 91.0)}
TURNS = [(36.0, 39.0, 0.0, -90.0), (54.0, 57.0, -90.0, -180.0), (73.0, 76.0, -180.0, -270.0), (91.0, 94.0, -270.0, -360.0)]


def clamp(v, a, b):
    return a if v < a else b if v > b else v


def lerp(a, b, t):
    return a + (b - a) * t


def smooth(e0, e1, x):
    t = clamp((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def ACT(p, a, b):
    return smooth(a, a + 0.015, p) * (1 - smooth(b - 0.015, b, p))


def wind(t):
    return 0.5 + 0.3 * math.sin(t * 0.31) + 0.15 * math.sin(t * 0.93 + 1.0)


# ======================================================================== wereld
scene = bpy.context.scene
cam = L.setup_camera(scene)
M, fc, nleaves = ST.build_all()
SS.build_sides(M)


def world():
    w = bpy.data.worlds.new('night'); scene.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes.get('Background')
    bg.inputs['Color'].default_value = L.hexlin('#2a3c74'); bg.inputs['Strength'].default_value = 1.6


def lights_360():
    sd = bpy.data.lights.new('moonlight', 'SUN'); sd.energy = 1.1; sd.color = L.hexlin('#a8bcff')[:3]; sd.angle = math.radians(1.5)
    so = bpy.data.objects.new('moonlight', sd); L.coll('lights').objects.link(so)
    so.rotation_euler = (math.radians(55), math.radians(-25), math.radians(200))
    roofs = L.coll('roofs')
    for o in list(bpy.data.objects):
        if o.type == 'MESH' and o.name.startswith('daken_'):
            if o.name not in roofs.objects:
                roofs.objects.link(o)
    for k in range(4):                         # per kant: warm vullicht op de gevels + zacht licht op de daken
        th = -k * math.pi / 2
        R = Matrix.Rotation(th, 4, 'Z')
        fd = bpy.data.lights.new('fill%d' % k, 'AREA'); fd.energy = 1500; fd.size = 18; fd.color = L.hexlin('#ffcfa0')[:3]   # vier kanten: elk vullicht valt ook schuin op de buren
        fo = bpy.data.objects.new('fill%d' % k, fd); L.coll('lights').objects.link(fo)
        fo.matrix_world = R @ Matrix.Translation((1.5, -3.0, 5.5)) @ Matrix.Rotation(math.radians(82), 4, 'X')
        fo.visible_glossy = False
        rd = bpy.data.lights.new('roofglow%d' % k, 'AREA'); rd.energy = 1500; rd.size = 12; rd.color = L.hexlin('#ffc0a0')[:3]
        ro = bpy.data.objects.new('roofglow%d' % k, rd); L.coll('lights').objects.link(ro)
        ro.matrix_world = R @ Matrix.Translation((1.5, 6.0, 12.0)) @ Matrix.Rotation(math.radians(35), 4, 'X')
        ro.visible_glossy = False
        try:
            fo.light_linking.receiver_collection = L.coll('town')
            ro.light_linking.receiver_collection = roofs
        except Exception:
            pass
    gd = bpy.data.lights.new('groundsoft', 'AREA'); gd.energy = 3600; gd.size = 30; gd.color = L.hexlin('#d8b8c8')[:3]
    go = bpy.data.objects.new('groundsoft', gd); L.coll('lights').objects.link(go)
    go.location = (0.0, 2.0, 10.0); go.visible_glossy = False
    try:
        go.light_linking.receiver_collection = L.coll('ground')
    except Exception:
        pass
    # licht op de personages: hangt aan de camera (draait mee), alleen voor de figuren
    for nm, en, pos, col in (('charkey', 900, (-3.0, 3.0, 4.0), '#ffd6a4'), ('charrim', 700, (3.5, -2.0, -14.0), '#b8ccff')):
        kd = bpy.data.lights.new(nm, 'AREA'); kd.energy = en; kd.size = 3.0; kd.color = L.hexlin(col)[:3]
        ko = bpy.data.objects.new(nm, kd); L.coll('lights').objects.link(ko)
        ko.parent = cam
        ko.location = pos                     # in camera-ruimte: x rechts, y omhoog, -z vooruit
        aim = Vector((0, -0.6, -11.0)) - Vector(pos)
        ko.rotation_euler = aim.to_track_quat('-Z', 'Y').to_euler()
        try:
            ko.light_linking.receiver_collection = L.coll('chars')
        except Exception:
            pass


world()


def optimize_static():
    """Voeg alle stilstaande meshes per collectie samen (modifiers eerst toepassen).
    Tienduizenden kleine objecten → een handvol: de render hoeft per frame veel minder klaar te zetten."""
    t0 = time.time()
    n0 = len(bpy.data.objects)
    for cname in ('town', 'ground', 'front', 'canopy', 'back', 'env'):
        c = bpy.data.collections.get(cname)
        if not c:
            continue
        obs = [o for o in c.all_objects if o.type == 'MESH' and not o.name.startswith('cobble')]
        if len(obs) < 2:
            continue
        # objectgebonden materialen (bladeren) naar de mesh-data overzetten
        for o in obs:
            if o.material_slots and any(sl.link == 'OBJECT' for sl in o.material_slots):
                mats_ = [sl.material for sl in o.material_slots]
                o.data = o.data.copy()
                for i, m_ in enumerate(mats_):
                    o.material_slots[i].link = 'DATA'
                    o.data.materials[i] = m_
        # daken apart houden: die krijgen hun eigen licht (light linking op de collectie 'roofs')
        is_roof = lambda o: 'roof' in o.name or 'dak' in o.name or o.name.startswith('ridge')
        # objecten mét UV-kaart (ramen, luifels) apart van objecten zonder: bij samenvoegen gaat de UV anders verloren
        has_uv = lambda o: len(o.data.uv_layers) > 0
        groups_ = (('daken', [o for o in obs if is_roof(o)]),
                   ('uv', [o for o in obs if not is_roof(o) and has_uv(o)]),
                   ('samen', [o for o in obs if not is_roof(o) and not has_uv(o)]))
        for label, group in groups_:
            if not group:
                continue
            bpy.ops.object.select_all(action='DESELECT')
            for o in group:
                o.select_set(True)
            bpy.context.view_layer.objects.active = group[0]
            bpy.ops.object.convert(target='MESH')
            if len(group) > 1:
                bpy.ops.object.join()
            bpy.context.view_layer.objects.active.name = '%s_%s' % (label, cname)
    print('samengevoegd: %d -> %d objecten in %.0fs' % (n0, len(bpy.data.objects), time.time() - t0))


optimize_static()
lights_360()          # pas ná het samenvoegen: anders krijgt alles het dakenlicht

# ======================================================================== personages
def build_rig(rig, col='chars'):
    objs = rig.build()
    for o in objs:
        for c in o.users_collection:
            c.objects.unlink(o)
        L.coll(col).objects.link(o)
    return objs[0], {o.name.split('.')[0]: o for o in objs[2:]}, objs


HORSE, _, HORSE_OBJS = build_rig(BC.make_horse())
RIDER, _, RIDER_OBJS = build_rig(BC.make_sint(riding=True))
P2, P2_PROPS, P2_OBJS = build_rig(BC.make_piet('piet_pakje', '#2a4aa8', '#f2b632', '#203a8a', '#f6d040', 'gift', 4))
P1, P1_PROPS, P1_OBJS = build_rig(BC.make_piet('piet_zak', '#6a2a8c', '#f2b632', '#5a2278', '#a03cd6', 'sack', 3))

FEET = {'piet': ['ftR', 'ftL'], 'horse': ['legFRh', 'legFLh', 'legBRh', 'legBLh']}
ANKLE = {'piet': 0.06, 'horse': 0.075}
STRIDE = {'piet': 0.933, 'horse': 0.768}       # m per pas bij schaal 1 (gemeten aan het skelet, zie chars3d.measureStride)


def set_visible(objs, vis):
    for o in objs:
        o.hide_render = not vis
        o.hide_viewport = not vis


def place(arm, pos, yaw, scale):
    arm.location = pos
    arm.rotation_euler = (0, 0, yaw)
    arm.scale = (scale, scale, scale)


def snap(arm, kind, base_z, scale):
    """Laagste voet precies op de grond (base_z)."""
    bpy.context.view_layer.update()
    lo = min((arm.matrix_world @ arm.pose.bones[b].head).z for b in FEET[kind])
    arm.location.z += base_z + ANKLE[kind] * scale - lo


def mount():
    bpy.context.view_layer.update()
    pb = HORSE.pose.bones['body']
    delta = pb.matrix @ pb.bone.matrix_local.inverted()
    RIDER.matrix_world = HORSE.matrix_world @ delta @ Matrix.Translation((-0.06, 0.0, 0.415)) @ Matrix.Rotation(math.pi / 2, 4, 'Z')


# ======================================================================== scène 1 (overgezet uit anim.js)
CYC = 48.0
HID = 230
CH_TOP = 222
D_MAIN = L.ground_d(702)
D_RIDGE = D_MAIN + 1.15


def ridgeY(x):
    return 298 - (x - 578) / (1372 - 578) * 5


def yval(v, x):
    if v == 'top':
        return CH_TOP - ridgeY(x)
    if v == 'in':
        return CH_TOP - ridgeY(x) + 175
    return v


PI = math.pi
TR1 = {
    'horse': {'K': [[0.00, 812, HID, -PI / 2], [0.025, 812, HID, -PI / 2], [0.085, 812, 0, -PI / 2], [0.10, 812, 0, -0.25],
                    [0.105, 812, 0, -0.25, 'lin'], [0.25, 1075, 0, -0.25], [0.30, 1075, 0, -0.3],
                    [0.78, 1075, 0, -0.3], [0.81, 1075, 0, -2.92], [0.92, 812, 0, -2.92], [0.94, 812, 0, -4.71],
                    [0.995, 812, HID, -4.71], [1, 812, HID, -4.71]], 'S': []},
    # in 3D lopen de Pieten tot vóór de schoorsteen (x 1176) en springen er dan van opzij op
    'piet2': {'K': [[0.00, 740, HID, 0], [0.06, 740, HID, 0], [0.115, 740, 0, 0], [0.13, 740, 0, 0.9],
                    [0.135, 740, 0, 0.9, 'lin'], [0.25, 930, 0, 0.9, 'lin'], [0.37, 1176, 0, 1.35], [0.38, 1176, 0, 1.2],
                    [0.43, 1234, 'top', 1.2], [0.45, 1234, 'top', 0.1], [0.47, 1234, 'top', 0.1], [0.53, 1234, 'in', 0.1],
                    [0.72, 1234, 'in', 0.1], [0.755, 1234, 'top', 0.1], [0.765, 1234, 'top', -1.3],
                    [0.795, 1176, 0, -1.4, 'lin'], [0.885, 740, 0, -1.4], [0.905, 740, 0, -PI], [0.955, 740, HID, -PI], [1, 740, HID, -PI]],
              'S': [{'hop': [0.385, 0.43, 1176, 1234, 0, 'top']}, {'pop': [0.72, 0.755]}, {'hop': [0.765, 0.795, 1234, 1176, 'top', 0]}]},
    'piet1': {'K': [[0.00, 682, HID, 0], [0.09, 682, HID, 0], [0.145, 682, 0, 0], [0.16, 682, 0, 0.9],
                    [0.165, 682, 0, 0.9, 'lin'], [0.25, 800, 0, 0.9, 'lin'], [0.48, 1176, 0, 1.35], [0.49, 1176, 0, 1.2],
                    [0.535, 1234, 'top', 1.2], [0.55, 1234, 'top', 0.3], [0.575, 1234, 'top', 0.3], [0.63, 1234, 'in', 0.3],
                    [0.77, 1234, 'in', 0.1], [0.805, 1234, 'top', 0.1], [0.815, 1234, 'top', -1.3],
                    [0.845, 1176, 0, -1.4, 'lin'], [0.93, 682, 0, -1.4], [0.945, 682, 0, -PI], [0.995, 682, HID, -PI], [1, 682, HID, -PI]],
              'S': [{'hop': [0.495, 0.535, 1176, 1234, 0, 'top']}, {'pop': [0.77, 0.805]}, {'hop': [0.815, 0.845, 1234, 1176, 'top', 0]}]},
}


def eval1(tr, p):
    K = tr['K']
    i = 0
    while i < len(K) - 2 and p > K[i + 1][0]:
        i += 1
    a, b = K[i], K[i + 1]
    u = clamp((p - a[0]) / max(1e-6, b[0] - a[0]), 0, 1)
    lin = len(a) > 4 and a[4] == 'lin'
    e = u if lin else u * u * (3 - 2 * u)
    de = 1 if lin else 6 * u * (1 - u)
    x = lerp(a[1], b[1], e)
    ya, yb = yval(a[2], a[1]), yval(b[2], b[1])
    y = lerp(ya, yb, e)
    yaw = lerp(a[3], b[3], e)
    speed = (abs(b[1] - a[1]) + abs(yb - ya) * 0.7) / max(1e-6, (b[0] - a[0]) * CYC) * de
    walk = clamp(speed / 22, 0, 1)
    jump = air = 0.0
    for s in tr['S']:
        if 'hop' in s:
            h = s['hop']
            if h[0] - 0.012 <= p <= h[1] + 0.01:
                v = clamp((p - h[0]) / (h[1] - h[0]), 0, 1)
                ev = v * v * (3 - 2 * v)
                x = lerp(h[2], h[3], ev)
                y = lerp(yval(h[4], h[2]), yval(h[5], h[3]), ev) - math.sin(v * PI) * 46
                walk = 0
                q = (p - h[0]) / (h[1] - h[0])
                jump = (1 - smooth(0, 0.18, v)) * smooth(-0.6, 0, q) + smooth(0.85, 1, v) * (1 - smooth(1, 1.4, q))
                air = math.sin(v * PI)
        if 'pop' in s:
            h = s['pop']
            if h[0] <= p <= h[1]:
                v = (p - h[0]) / (h[1] - h[0])
                yIn, yTop = yval('in', 1234), yval('top', 1234)
                arc = 1 - (1 - v / 0.7) ** 2 if v < 0.7 else 1
                over = math.sin(clamp(v / 0.85, 0, 1) * PI) * 60
                y = lerp(yIn, yTop, arc) - over
                walk = 0; air = 1 - smooth(0.8, 1, v); jump = smooth(0.85, 1, v) * 0.8
    topY = yval('top', 1234)
    in_chim = abs(x - 1234) < 30 and y > topY + 0.5
    ph = tr['phT'][min(len(tr['phT']) - 1, int(round(clamp(p, 0, 1) * (len(tr['phT']) - 1))))] if 'phT' in tr else 0.0
    return {'x': x, 'y': y, 'yaw': yaw, 'walk': walk, 'ph': ph, 'jump': jump, 'air': air, 'inChim': in_chim}


def build_phase1(tr, stride_m, scale, depth, axis):
    N = 6000
    P = [0.0] * (N + 1)
    prev = eval1(tr, 0)
    ph = 0.0
    mpp = depth / L.F_PX                   # meter per pixel op de nok
    for i in range(1, N + 1):
        c = eval1(tr, i / N)
        dd = (abs(c['x'] - prev['x']) + abs(c['y'] - prev['y']) * 0.7) * mpp
        f = abs(math.cos(c['yaw'])) if axis == 'x' else abs(math.sin(c['yaw']))
        if c['walk'] > 0.001 and dd < 0.6:
            ph += dd / (stride_m * scale * max(0.35, f) * max(0.3, c['walk'])) * 2 * PI
        P[i] = ph
        prev = c
    tr['phT'] = P


S1 = {'horse': (1.1, D_RIDGE + 0.05), 'piet2': (1.22, D_RIDGE - 0.1), 'piet1': (1.22, D_RIDGE - 0.2)}
build_phase1(TR1['horse'], STRIDE['horse'], S1['horse'][0], S1['horse'][1], 'x')
build_phase1(TR1['piet2'], STRIDE['piet'], S1['piet2'][0], S1['piet2'][1], 'z')
build_phase1(TR1['piet1'], STRIDE['piet'], S1['piet1'][0], S1['piet1'][1], 'z')


def w1(x, ypx, depth):
    return L.S2W(x, ridgeY(x) + ypx, depth)


def turn1(tr, p):
    a, b = eval1(tr, max(0, p - 0.002))['yaw'], eval1(tr, min(1, p + 0.002))['yaw']
    return (b - a) / (0.004 * CYC)


def scene1(p, t):
    W = wind(t)
    # paard + Sint
    s = eval1(TR1['horse'], p)
    sc, dep = S1['horse']
    wave = ACT(p, 0.345, 0.5); twist = ACT(p, 0.31, 0.54)
    PO.apply_pose(HORSE, PO.horse({'t': t, 'walk': s['walk'], 'ph': s['ph'], 'wind': W, 'lift': ACT(p, 0.36, 0.5), 'swish': 0.6,
                                   'nod': max(0, math.sin((p - 0.43) / 0.07 * 2 * PI)) * ACT(p, 0.43, 0.5) * 0.8,
                                   'earFlick': max(0, math.sin(t * 0.9) - 0.85) * 6, 'look': ACT(p, 0.36, 0.5) * 0.3}))
    pos = w1(s['x'], s['y'], dep)
    place(HORSE, pos, s['yaw'], sc)
    if s['y'] < 4:
        snap(HORSE, 'horse', w1(s['x'], 0, dep).z, sc)
    PO.apply_pose(RIDER, PO.rider({'walk': s['walk'], 'ph': s['ph'], 't': t, 'wave': wave, 'twist': twist, 'wind': W,
                                   'turn': turn1(TR1['horse'], p), 'look': ACT(p, 0.52, 0.62) * 0.5 - ACT(p, 0.17, 0.27) * 0.3,
                                   'nod': ACT(p, 0.52, 0.62) * 0.22 + wave * -0.05, 'tilt': wave * 0.08}))
    mount()
    # Pieten
    for key, arm, prop, props, act_up, gone in (('piet2', P2, 'gift', P2_PROPS, ACT(p, 0.45, 0.535), 0.52), ('piet1', P1, 'sack', P1_PROPS, ACT(p, 0.80, 0.83), 0.62)):
        c = eval1(TR1[key], p)
        sc, dep = S1[key]
        st = {'walk': c['walk'], 'ph': c['ph'], 't': t, 'jump': c['jump'], 'air': c['air'], 'armsUp': act_up, 'wind': W,
              'turn': turn1(TR1[key], p), 'hideProp': gone < p < 0.999}
        if key == 'piet2':
            st['look'] = ACT(p, 0.88, 0.9) * 0.4
        PO.apply_pose(arm, PO.piet(st, prop), props)
        place(arm, w1(c['x'], c['y'], dep), c['yaw'], sc)
        if c['air'] < 0.05 and c['jump'] < 0.2 and c['y'] < 4 and not c['inChim']:
            snap(arm, 'piet', w1(c['x'], c['y'], dep).z, sc)


# ======================================================================== scènes 2–4: tijdlijnen op de grond
class GTrack:
    """Sleutels: (t, lat, dep, z, yaw[, 'lin']) in het kader van een kant. Fase uit afgelegde weg."""
    def __init__(self, keys, stride_m, scale, axis):
        self.K = keys
        self.stride = stride_m * scale
        self.axis = axis
        self.dt = 0.02
        n = int((keys[-1][0] - keys[0][0]) / self.dt) + 2
        self.t0 = keys[0][0]
        self.P = [0.0] * n
        prev = self.raw(self.t0)
        ph = 0.0
        for i in range(1, n):
            c = self.raw(self.t0 + i * self.dt)
            dd = math.hypot(c[0] - prev[0], c[1] - prev[1]) + abs(c[2] - prev[2]) * 1.2
            f = abs(math.cos(c[3])) if axis == 'x' else abs(math.sin(c[3]))
            f = max(0.35, f) if c[5] else 1.0
            if c[4] > 0.001:
                ph += dd / (self.stride * f * max(0.3, c[4])) * 2 * PI
            self.P[i] = ph
            prev = c

    def raw(self, t):
        K = self.K
        i = 0
        while i < len(K) - 2 and t > K[i + 1][0]:
            i += 1
        a, b = K[i], K[i + 1]
        u = clamp((t - a[0]) / max(1e-6, b[0] - a[0]), 0, 1)
        lin = len(a) > 5 and a[5] == 'lin'
        e = u if lin else u * u * (3 - 2 * u)
        de = 1 if lin else 6 * u * (1 - u)
        lat, dep, z = lerp(a[1], b[1], e), lerp(a[2], b[2], e), lerp(a[3], b[3], e)
        yaw = lerp(a[4], b[4], e)
        dist = math.hypot(b[1] - a[1], b[2] - a[2]) + abs(b[3] - a[3]) * 1.2
        speed = dist / max(1e-6, b[0] - a[0]) * de
        walk = clamp(speed / 0.45, 0, 1)
        crab = abs(b[3] - a[3]) < 0.01          # schuin naar de kijker lopen (geen ladder)
        return (lat, dep, z, yaw, walk, crab)

    def at(self, t):
        lat, dep, z, yaw, walk, _ = self.raw(t)
        i = int(clamp((t - self.t0) / self.dt, 0, len(self.P) - 1))
        return {'lat': lat, 'dep': dep, 'z': z, 'yaw': yaw, 'walk': walk, 'ph': self.P[i]}


def put_char(view, arm, kind, c, scale, nosnap=False):
    pos = SS.to_world(view, (c['lat'], c['dep'], c['z']))
    place(arm, pos, SS.VIEW[view] + c['yaw'], scale)
    if not nosnap:
        snap(arm, kind, c['z'], scale)


# ---- scène 2: oost, stadhuis. Iedereen komt van links, doet iets, en gaat rechts weg.
T2 = {
    'horse': GTrack([(0, -10.5, 9.8, 0, -0.35), (5.0, -1.8, 9.6, 0, -0.35), (6.0, -1.8, 9.6, 0, -0.5), (11.5, -1.8, 9.6, 0, -0.5),
                     (12.0, -1.8, 9.6, 0, -0.3, 'lin'), (15.0, 10.5, 9.8, 0, -0.3)], STRIDE['horse'], 1.0, 'x'),
    'piet2': GTrack([(0, -8.5, 8.0, 0, 1.15, 'lin'), (4.6, 0.6, 8.0, 0, 1.15), (5.4, 0.6, 8.0, 0, 1.15), (7.0, 3.4, 8.0, 0, 1.15),
                     (7.4, 3.4, 8.0, 0, 0.2), (11.0, 3.4, 8.0, 0, 0.2), (11.6, 3.4, 8.0, 0, 1.15, 'lin'), (15.0, 10.5, 8.0, 0, 1.15)], STRIDE['piet'], 1.0, 'z'),
    'piet1': GTrack([(0, -11.0, 8.5, 0, 1.15, 'lin'), (5.8, -4.2, 8.5, 0, 1.15), (6.3, -4.2, 8.5, 0, 0.5), (10.4, -4.2, 8.5, 0, 0.5),
                     (11.0, -4.2, 8.5, 0, 1.15, 'lin'), (15.0, 9.5, 8.5, 0, 1.15)], STRIDE['piet'], 1.0, 'z'),
}
PEPER = []
pm = L.plain('pepernoot', '#8a4a1e', 0.6)
for k in range(36):
    o = L.ellipsoid('pepernoot', (0, 0, 0), (0.022, 0.022, 0.013), pm, seg=8, rings=5, col='chars')
    PEPER.append(o)
_pr = random.Random(8)
PEPER_LAUNCH = [(6.6 + _pr.random() * 3.6, _pr.uniform(-1.6, 1.6), _pr.uniform(-2.4, -0.6), _pr.uniform(2.6, 4.0)) for _ in PEPER]


def scene2(lt, t):
    W = wind(t)
    v = 'east'
    h = T2['horse'].at(lt)
    wave = smooth(6.2, 6.8, lt) * (1 - smooth(10.4, 11.0, lt))
    PO.apply_pose(HORSE, PO.horse({'t': t, 'walk': h['walk'], 'ph': h['ph'], 'wind': W, 'swish': 0.6,
                                   'nod': max(0, math.sin((lt - 7.0) * 3.0)) * smooth(6.5, 7.2, lt) * (1 - smooth(9.5, 10, lt)) * 0.6}))
    put_char(v, HORSE, 'horse', h, 1.0)
    PO.apply_pose(RIDER, PO.rider({'walk': h['walk'], 'ph': h['ph'], 't': t, 'wave': wave, 'twist': wave * 0.8, 'wind': W, 'tilt': wave * 0.08}))
    mount()
    # Piet met pakje: sprong met pirouette tussen 5,4 en 7,0 s (armen omhoog, één keer rond)
    c = T2['piet2'].at(lt)
    cw = clamp((lt - 5.4) / 1.6, 0, 1)
    in_cw = 0 < cw < 1
    st = {'walk': 0 if in_cw else c['walk'], 'ph': c['ph'], 't': t, 'wind': W, 'hideProp': True, 'look': -0.3 * smooth(7.4, 8, lt),
          'air': math.sin(PI * cw) if in_cw else 0, 'jump': (smooth(0, 0.12, cw) * (1 - smooth(0.12, 0.25, cw)) + smooth(0.85, 0.95, cw) * (1 - smooth(0.95, 1, cw))) if in_cw else 0}
    P = PO.piet(st, 'gift')
    if in_cw:
        up = smooth(0.1, 0.3, cw) * (1 - smooth(0.8, 0.95, cw))
        P['rot'].update({'shR': [0, 0, -2.7 * up], 'shL': [0, 0, 2.7 * up], 'elR': [0, 0, -0.3 * up], 'elL': [0, 0, 0.3 * up]})
    PO.apply_pose(P2, P, P2_PROPS)
    if in_cw:
        c = dict(c)
        c['yaw'] += 2 * PI * smooth(0.15, 0.9, cw)
        c['z'] += math.sin(PI * clamp((cw - 0.15) / 0.7, 0, 1)) * 0.55
    put_char(v, P2, 'piet', c, 1.0, nosnap=in_cw)
    # Piet met zak strooit pepernoten
    c1 = T2['piet1'].at(lt)
    throw = 0.0
    if 6.3 < lt < 10.4:
        throw = max(0.0, math.sin((lt - 6.3) * 2 * PI * 1.1))
    PO.apply_pose(P1, PO.piet({'walk': c1['walk'], 'ph': c1['ph'], 't': t, 'wind': W, 'armsUp': throw * 0.7}, 'sack'), P1_PROPS)
    put_char(v, P1, 'piet', c1, 1.0)
    hand = SS.to_world(v, (c1['lat'] + 0.15, c1['dep'] - 0.1, 1.35))
    for o, (t_l, vx, vy, vz) in zip(PEPER, PEPER_LAUNCH):
        dt_ = lt - t_l
        if dt_ < 0:
            o.hide_render = True
            continue
        o.hide_render = False
        vw = SS.to_world(v, (vx, vy, 0))
        z = hand.z + vz * dt_ - 4.9 * dt_ * dt_
        if z <= 0.012:   # ligt op de grond
            tl = (vz + math.sqrt(vz * vz + 2 * 9.8 * (hand.z - 0.012))) / 9.8
            o.location = (hand.x + vw.x * tl, hand.y + vw.y * tl, 0.012)
        else:
            o.location = (hand.x + vw.x * dt_, hand.y + vw.y * dt_, z)
        o.rotation_euler = (dt_ * 7, dt_ * 5, 0)


# ---- scène 3: zuid, de pakjesboot
def _gang():
    gt, gb = SS.BOAT.get('gang_top'), SS.BOAT.get('gang_bot')
    return gt, gb


GT, GB = _gang()
DQ = SS.BOAT['dq']
DECK = SS.BOAT['deck']
T3 = {
    'horse': GTrack([(0, -11.0, DQ - 3.2, 0, -0.3), (4.5, -3.2, DQ - 3.2, 0, -0.3), (5.5, -3.2, DQ - 3.2, 0, 0.75), (11.8, -3.2, DQ - 3.2, 0, 0.75),
                     (12.6, -3.2, DQ - 3.2, 0, -0.25, 'lin'), (16.0, 10.5, DQ - 3.0, 0, -0.25)], STRIDE['horse'], 1.0, 'x'),
    'piet2': GTrack([(0, GT[0] - 2.6, GT[1] + 0.25, DECK, 1.57), (1.8, GT[0] - 2.6, GT[1] + 0.25, DECK, 1.57), (3.6, GT[0], GT[1] + 0.25, DECK, 1.57),
                     (4.0, GT[0], GT[1] + 0.1, DECK, 0.0), (6.6, GB[0], GB[1] - 0.15, 0.0, 0.0), (7.0, GB[0], GB[1] - 0.15, 0.0, 1.2),
                     (8.6, 1.6, DQ - 1.9, 0.0, 1.2), (9.6, 1.6, DQ - 1.9, 0.0, 1.2), (12.0, 1.6, DQ - 1.9, 0.0, 1.2, 'lin'), (16.0, 10.5, DQ - 2.2, 0.0, 1.2)],
                    STRIDE['piet'], 1.0, 'z'),
    'piet1': GTrack([(0, -9.5, DQ - 2.6, 0, 1.15, 'lin'), (4.0, 2.9, DQ - 2.6, 0, 1.15), (4.6, 2.9, DQ - 2.6, 0, -0.6), (12.2, 2.9, DQ - 2.6, 0, -0.6),
                     (12.8, 2.9, DQ - 2.6, 0, 1.15, 'lin'), (16.0, 11.0, DQ - 2.6, 0, 1.15)], STRIDE['piet'], 1.0, 'z'),
}
PILE = []
for k, (dl, dd, w_, h_, mat) in enumerate(((0.0, 0.0, 0.34, 0.3, 'gred'), (0.42, 0.1, 0.3, 0.26, 'gyel'), (0.2, 0.05, 0.26, 0.22, 'ggrn'))):
    pos = SS.to_world('south', (2.05 + dl, DQ - 1.6 + dd, 0))
    ob = L.box('stapelpakje', (pos.x, pos.y, h_ / 2 + (0.3 if k == 2 else 0)), (w_, w_ * 0.85, h_), M[mat], col='chars', rot=(0, 0, 0.3 * k))
    rib = L.box('stapellint', (pos.x, pos.y, h_ / 2 + (0.3 if k == 2 else 0)), (w_ * 0.16, w_ * 0.87, h_ + 0.004), M['ribbon'], col='chars', rot=(0, 0, 0.3 * k))
    PILE.append((ob, rib))


def scene3(lt, t):
    W = wind(t)
    v = 'south'
    h = T3['horse'].at(lt)
    wave = smooth(5.6, 6.2, lt) * (1 - smooth(11.2, 11.8, lt))
    PO.apply_pose(HORSE, PO.horse({'t': t, 'walk': h['walk'], 'ph': h['ph'], 'wind': W, 'swish': 0.6, 'lift': wave * 0.6}))
    put_char(v, HORSE, 'horse', h, 1.0)
    PO.apply_pose(RIDER, PO.rider({'walk': h['walk'], 'ph': h['ph'], 't': t, 'wave': wave, 'twist': -wave * 0.3, 'wind': W}))
    mount()
    c = T3['piet2'].at(lt)
    put = smooth(8.6, 9.0, lt) * (1 - smooth(9.2, 9.6, lt))
    PO.apply_pose(P2, PO.piet({'walk': c['walk'], 'ph': c['ph'], 't': t, 'wind': W, 'jump': put * 0.7, 'hideProp': lt > 9.1}, 'gift'), P2_PROPS)
    put_char(v, P2, 'piet', c, 1.0)
    c1 = T3['piet1'].at(lt)
    PO.apply_pose(P1, PO.piet({'walk': c1['walk'], 'ph': c1['ph'], 't': t, 'wind': W, 'nod': 0.15 * math.sin(max(0, lt - 9) * 6) * smooth(9, 9.3, lt) * (1 - smooth(10, 10.5, lt)), 'look': -0.2}, 'sack'), P1_PROPS)
    put_char(v, P1, 'piet', c1, 1.0)
    for k, (ob, rib) in enumerate(PILE):
        vis = k < 2 or lt > 9.1
        ob.hide_render = rib.hide_render = not vis


# ---- scène 4: west, ladder bij de bakker
LB, LT_ = SS.LADDER['bot'], SS.LADDER['top']
LADDER_TOPZ = LT_[2] - 1.15
T4 = {
    'horse': GTrack([(0, -11.5, LB[1] - 4.0, 0, -0.3), (5.0, LB[0] - 4.2, LB[1] - 4.0, 0, -0.3), (6.0, LB[0] - 4.2, LB[1] - 4.0, 0, 0.55),
                     (12.2, LB[0] - 4.2, LB[1] - 4.0, 0, 0.55), (12.8, LB[0] - 4.2, LB[1] - 4.0, 0, -0.25, 'lin'), (15.0, 11.0, LB[1] - 4.0, 0, -0.25)],
                    STRIDE['horse'], 1.0, 'x'),
    'piet2': GTrack([(0, -9.0, LB[1] - 1.0, 0, 1.15, 'lin'), (3.6, LB[0], LB[1] - 0.35, 0, 1.15), (4.2, LB[0], LB[1] - 0.35, 0, PI),
                     (4.4, LB[0], LB[1] - 0.3, 0, PI), (7.4, LB[0], lerp(LB[1], LT_[1], 0.7) - 0.3, LADDER_TOPZ, PI), (9.0, LB[0], lerp(LB[1], LT_[1], 0.7) - 0.3, LADDER_TOPZ, PI),
                     (11.2, LB[0], LB[1] - 0.3, 0, PI), (11.6, LB[0], LB[1] - 0.35, 0, 1.15, 'lin'), (15.0, 10.5, LB[1] - 1.2, 0, 1.15)], STRIDE['piet'], 1.0, 'z'),
    'piet1': GTrack([(0, -10.5, LB[1] - 1.4, 0, 1.15, 'lin'), (3.4, LB[0] - 0.75, LB[1] - 0.75, 0, 1.15), (3.9, LB[0] - 0.75, LB[1] - 0.75, 0, PI - 0.7),
                     (11.6, LB[0] - 0.75, LB[1] - 0.75, 0, PI - 0.7), (12.2, LB[0] - 0.75, LB[1] - 0.75, 0, 1.15, 'lin'), (15.0, 10.0, LB[1] - 1.6, 0, 1.15)],
                    STRIDE['piet'], 1.0, 'z'),
}


def scene4(lt, t):
    W = wind(t)
    v = 'west'
    h = T4['horse'].at(lt)
    wave = smooth(8.8, 9.4, lt) * (1 - smooth(11.0, 11.6, lt))
    PO.apply_pose(HORSE, PO.horse({'t': t, 'walk': h['walk'], 'ph': h['ph'], 'wind': W, 'swish': 0.5}))
    put_char(v, HORSE, 'horse', h, 1.0)
    PO.apply_pose(RIDER, PO.rider({'walk': h['walk'], 'ph': h['ph'], 't': t, 'wave': wave, 'twist': 0.2, 'wind': W, 'look': 0.3}))
    mount()
    c = T4['piet2'].at(lt)
    climbing = 4.4 < lt < 11.2
    top = smooth(7.4, 7.8, lt) * (1 - smooth(8.6, 9.0, lt))
    PO.apply_pose(P2, PO.piet({'walk': c['walk'], 'ph': c['ph'], 't': t, 'wind': W, 'armsUp': top, 'hideProp': lt > 8.4}, 'gift'), P2_PROPS)
    put_char(v, P2, 'piet', c, 1.0, nosnap=climbing)
    c1 = T4['piet1'].at(lt)
    PO.apply_pose(P1, PO.piet({'walk': c1['walk'], 'ph': c1['ph'], 't': t, 'wind': W, 'nod': -0.3 * smooth(4, 4.5, lt) * (1 - smooth(11, 11.5, lt)),
                               'armsUp': 0.4 * smooth(4.2, 4.6, lt) * (1 - smooth(11, 11.4, lt))}, 'sack'), P1_PROPS)
    put_char(v, P1, 'piet', c1, 1.0)


# ======================================================================== frame
ALL_CHARS = HORSE_OBJS + RIDER_OBJS + P2_OBJS + P1_OBJS
CHAR_ROOF = L.coll('chars')


def cam_yaw(t):
    for (a, b, y0, y1) in TURNS:
        if a <= t < b:
            return math.radians(lerp(y0, y1, smooth(a, b, t)))
    if t < 36:
        return 0.0
    if t < 54:
        return math.radians(-90)
    if t < 73:
        return math.radians(-180)
    if t < 91:
        return math.radians(-270)
    return 0.0


def frame(t):
    t = t % TOTAL
    cam.rotation_euler = (math.radians(90), 0, cam_yaw(t))
    act = None
    for k, (a, b) in SC.items():
        if a <= t < b:
            act = k
    set_visible(ALL_CHARS, act is not None)
    for o in PEPER:
        o.hide_render = act != 's2'
    for (ob, rib) in PILE:
        ob.hide_render = rib.hide_render = act != 's3'
    if act == 's1':
        scene1((t - SC['s1'][0]) / (SC['s1'][1] - SC['s1'][0]), t)
    elif act == 's2':
        scene2(t - SC['s2'][0], t)
    elif act == 's3':
        scene3(t - SC['s3'][0], t)
    elif act == 's4':
        scene4(t - SC['s4'][0], t)
    return cam_yaw(t)


# ======================================================================== render
r = scene.render
r.resolution_percentage = args.res
r.film_transparent = True
r.image_settings.file_format = 'PNG'
r.image_settings.color_mode = 'RGBA'
if args.engine == 'cycles':
    r.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    if args.device != 'cpu':
        # GPU: probeer OPTIX/CUDA (NVIDIA), HIP (AMD), METAL (Mac), ONEAPI (Intel)
        prefs = bpy.context.preferences.addons['cycles'].preferences
        kinds = ['OPTIX', 'CUDA', 'HIP', 'METAL', 'ONEAPI'] if args.device == 'gpu' else [args.device.upper()]
        for kind in kinds:
            try:
                prefs.compute_device_type = kind
                prefs.get_devices()
            except Exception:
                continue
            gpus = [d for d in prefs.devices if d.type == kind]
            if gpus:
                for d in prefs.devices:
                    d.use = d.type == kind
                scene.cycles.device = 'GPU'
                print('GPU:', kind, ', '.join(d.name for d in gpus), flush=True)
                break
        else:
            print('geen GPU gevonden, render op CPU', flush=True)
    scene.cycles.samples = args.samples
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 4; scene.cycles.diffuse_bounces = 2; scene.cycles.glossy_bounces = 2
    scene.cycles.caustics_reflective = False; scene.cycles.caustics_refractive = False
    scene.view_settings.view_transform = 'Standard'
    try:
        scene.view_settings.look = 'Medium High Contrast'
    except Exception:
        pass
else:
    r.engine = 'BLENDER_WORKBENCH'
    sh = scene.display.shading
    sh.light = 'STUDIO'; sh.color_type = 'MATERIAL'; sh.show_shadows = True; sh.show_cavity = True
    # workbench toont de 'viewport'-kleur: neem die over uit de nodes
    for m in bpy.data.materials:
        if not m.use_nodes:
            continue
        col = None
        for n in m.node_tree.nodes:
            if n.type == 'BSDF_PRINCIPLED' and not n.inputs['Base Color'].is_linked:
                col = n.inputs['Base Color'].default_value
            elif n.type == 'EMISSION' and not n.inputs['Color'].is_linked:
                col = n.inputs['Color'].default_value
            elif n.type == 'TEX_BRICK':
                col = n.inputs['Color1'].default_value
            elif n.type == 'VALTORGB' and col is None:
                col = n.color_ramp.elements[-1].color
        if col is not None:
            m.diffuse_color = (col[0], col[1], col[2], 1)

if args.save:
    frame(20.0)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(args.save))

os.makedirs(args.out, exist_ok=True)
nfr = int(TOTAL * args.fps)
end = nfr if args.end < 0 else min(nfr, args.end)
frames = [int(x) for x in args.frames.split(',')] if args.frames else list(range(args.start, end, args.step))
log_path = os.path.join(args.out, 'yaw.json')
log = json.load(open(log_path)) if os.path.exists(log_path) else {}
t_all = time.time()
for f in frames:
    t = f / args.fps
    yaw = frame(t)
    r.filepath = os.path.join(os.path.abspath(args.out), 'f_%05d.png' % f)
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    log[str(f)] = {'yaw': yaw, 't': t}
    if f % 20 == 0 or f == frames[-1]:
        json.dump(log, open(log_path, 'w'))
    print('FRAME %d t=%.2f %.1fs' % (f, t, time.time() - t0), flush=True)
json.dump(log, open(log_path, 'w'))
print('KLAAR %d frames in %.0fs' % (len(frames), time.time() - t_all))

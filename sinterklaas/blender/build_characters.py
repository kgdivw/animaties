"""
Bouwt de personages (Sint, twee Pieten, paard) als gladde, geriggede 3D-modellen
en exporteert ze naar .glb.  Draaien:

  blender -b --factory-startup --python build_characters.py -- <uitvoermap>

Coördinaten in het script: "karakterruimte" in centimeters, x rechts, y omhoog,
z naar de kijker (zelfde als de oude puppet3d-engine). Bij het aanmaken van de
mesh wordt omgezet naar Blender (z omhoog, -y = voorkant), zodat de glTF-export
weer y-omhoog / +z-voor oplevert.
"""
import bpy, math, sys, os, random
from mathutils import Vector, Matrix, Euler

if __name__ == '__main__':
    bpy.ops.wm.read_factory_settings(use_empty=True)
U = 0.01
OUT = sys.argv[sys.argv.index('--') + 1] if '--' in sys.argv else os.path.dirname(__file__)
TAU = math.pi * 2


def B(v):
    return Vector((v[0] * U, -v[2] * U, v[1] * U))


def rotm(rot):
    """Euler in graden, volgorde zoals puppet3d: eerst z, dan x, dan y (M = Ry*Rx*Rz)."""
    if not rot:
        return Matrix.Identity(3)
    rx, ry, rz = [math.radians(a) for a in rot]
    return Matrix.Rotation(ry, 3, 'Y') @ Matrix.Rotation(rx, 3, 'X') @ Matrix.Rotation(rz, 3, 'Z')


def smoothstep(e0, e1, x):
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


# ------------------------------------------------------------------ materialen
MATS = {}


def mat(name, hexcol, rough=0.6, metal=0.0, emit=0.0, sheen=0.0, sss=0.0):
    if name in MATS:
        return name
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get('Principled BSDF')
    h = hexcol.lstrip('#')
    rgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    bsdf.inputs['Base Color'].default_value = (lin[0], lin[1], lin[2], 1)
    bsdf.inputs['Roughness'].default_value = rough
    bsdf.inputs['Metallic'].default_value = metal
    if emit:
        try:
            bsdf.inputs['Emission Color'].default_value = (lin[0], lin[1], lin[2], 1)
            bsdf.inputs['Emission Strength'].default_value = emit
        except KeyError:
            pass
    if sheen:
        try:
            bsdf.inputs['Sheen Weight'].default_value = sheen
            bsdf.inputs['Sheen Tint'].default_value = (lin[0] * 0.6 + 0.4, lin[1] * 0.6 + 0.4, lin[2] * 0.6 + 0.4, 1)
        except KeyError:
            pass
    if sss:
        try:
            bsdf.inputs['Subsurface Weight'].default_value = sss
            bsdf.inputs['Subsurface Radius'].default_value = (0.012, 0.005, 0.003)
        except KeyError:
            pass
    MATS[name] = m
    return name


# ------------------------------------------------------------------ geometrie
def ellipsoid(c, r, rot=None, seg=24, rings=14, stripe=None):
    R = rotm(rot)
    V, F, FM = [], [], []
    V.append(c_add(c, R @ Vector((0, r[1], 0))))
    for i in range(1, rings):
        t = math.pi * i / rings
        for j in range(seg):
            p = TAU * j / seg
            v = Vector((math.sin(t) * math.cos(p) * r[0], math.cos(t) * r[1], math.sin(t) * math.sin(p) * r[2]))
            V.append(c_add(c, R @ v))
    V.append(c_add(c, R @ Vector((0, -r[1], 0))))
    bot = len(V) - 1
    for j in range(seg):
        F.append([0, 1 + (j + 1) % seg, 1 + j]); FM.append(stripe(j) if stripe else None)
    for i in range(rings - 2):
        a, b = 1 + i * seg, 1 + (i + 1) * seg
        for j in range(seg):
            j1 = (j + 1) % seg
            F.append([a + j, a + j1, b + j1, b + j]); FM.append(stripe(j) if stripe else None)
    a = 1 + (rings - 2) * seg
    for j in range(seg):
        F.append([a + j, a + (j + 1) % seg, bot]); FM.append(stripe(j) if stripe else None)
    return V, F, FM


def c_add(c, v):
    return (c[0] + v[0], c[1] + v[1], c[2] + v[2])


def lathe(c, prof, seg=32, rot=None, open_a=None, thick=0.0, stripe=None, wave=None, caps=(True, True)):
    """Draaivorm rond de lokale y-as. prof: [(y, rx, rz[, dx, dz])].
    open_a: functie(i)->halve openingshoek (rad) rond de voorkant (+z), voor een mantel.
    wave: functie(i, a)->factor op de straal (kantjes, ruches)."""
    R = rotm(rot)
    V, F, FM = [], [], []
    n = len(prof)
    closed = open_a is None
    cols = seg if closed else seg + 1

    def ring(i, shrink=0.0):
        y, rx, rz = prof[i][0], prof[i][1], prof[i][2]
        dx = prof[i][3] if len(prof[i]) > 3 else 0
        dz = prof[i][4] if len(prof[i]) > 4 else 0
        pts = []
        for j in range(cols):
            if closed:
                a = TAU * j / seg
            else:
                h = open_a(i)
                a0, a1 = math.pi / 2 + h, math.pi / 2 - h + TAU
                a = a0 + (a1 - a0) * j / seg
            k = wave(i, a) if wave else 1.0
            v = Vector((dx + math.cos(a) * (rx - shrink) * k, y, dz + math.sin(a) * (rz - shrink) * k))
            pts.append(c_add(c, R @ v))
        return pts

    for i in range(n):
        V += ring(i)
    for i in range(n - 1):
        for j in range(seg):
            j1 = (j + 1) % cols if closed else j + 1
            a, b = i * cols, (i + 1) * cols
            F.append([a + j, b + j, b + j1, a + j1]); FM.append(stripe(i, j) if stripe else None)
    if closed:
        if caps[0] and prof[0][1] > 0.3:
            V.append(c_add(c, R @ Vector((prof[0][3] if len(prof[0]) > 3 else 0, prof[0][0], prof[0][4] if len(prof[0]) > 4 else 0))))
            ci = len(V) - 1
            for j in range(seg):
                F.append([ci, (j + 1) % seg, j]); FM.append(None)
        if caps[1] and prof[-1][1] > 0.3:
            pl = prof[-1]
            V.append(c_add(c, R @ Vector((pl[3] if len(pl) > 3 else 0, pl[0], pl[4] if len(pl) > 4 else 0))))
            ci = len(V) - 1
            a = (n - 1) * cols
            for j in range(seg):
                F.append([ci, a + j, a + (j + 1) % seg]); FM.append(None)
    elif thick > 0:
        base = len(V)
        for i in range(n):
            V += ring(i, thick)
        for i in range(n - 1):
            for j in range(seg):
                a, b = base + i * cols, base + (i + 1) * cols
                F.append([a + j, a + j + 1, b + j + 1, b + j]); FM.append(None)
        # randen dichtmaken
        for i in range(n - 1):
            for j in (0, seg):
                o, inn = i * cols + j, base + i * cols + j
                o2, in2 = (i + 1) * cols + j, base + (i + 1) * cols + j
                F.append([o, inn, in2, o2] if j == 0 else [o, o2, in2, inn]); FM.append(None)
        for i in (0, n - 1):
            for j in range(seg):
                o, inn = i * cols + j, base + i * cols + j
                q = [o, o + 1, inn + 1, inn]
                F.append(q if i == 0 else q[::-1]); FM.append(None)
    return V, F, FM


def catmull(pts, sub=5):
    P = [Vector(p) for p in pts]
    if len(P) < 3:
        out = []
        for k in range(sub * (len(P) - 1) + 1):
            t = k / sub
            i = min(len(P) - 2, int(t))
            out.append(P[i].lerp(P[i + 1], t - i))
        return out, [k / sub for k in range(len(out))]
    ext = [P[0] * 2 - P[1]] + P + [P[-1] * 2 - P[-2]]
    out, par = [], []
    for i in range(1, len(ext) - 2):
        p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
        for k in range(sub):
            t = k / sub
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
            par.append(i - 1 + t)
    out.append(P[-1]); par.append(len(P) - 1)
    return out, par


def tube(pts, radii, seg=16, flat=1.0, up=(0, 0, 1), caps=True, wav=None):
    """Gladde buis door punten, straal per punt (geïnterpoleerd). flat < 1 drukt de
    doorsnede plat in de richting van 'up'-loodrecht (handig voor veren, mantelranden)."""
    C, par = catmull(pts)
    n = len(C)
    rs = []
    for t in par:
        i = min(len(radii) - 2, int(t))
        f = t - i
        rs.append(radii[i] * (1 - f) + radii[i + 1] * f)
    if wav:
        rs = [r * wav(k / (n - 1)) for k, r in enumerate(rs)]
    T = []
    for k in range(n):
        a = C[max(0, k - 1)]; b = C[min(n - 1, k + 1)]
        t = (b - a)
        T.append(t.normalized() if t.length > 1e-6 else Vector((0, 1, 0)))
    upv = Vector(up)
    N = T[0].cross(upv)
    if N.length < 1e-4:
        N = T[0].cross(Vector((1, 0, 0)))
    N.normalize()
    V, F, FM = [], [], []
    frames = []
    for k in range(n):
        if k:
            N = N - T[k] * N.dot(T[k])
            if N.length < 1e-6:
                N = T[k].orthogonal()
            N.normalize()
        Bn = T[k].cross(N)
        frames.append((N.copy(), Bn.copy()))
    rings = []

    def add_ring(center, Nn, Bb, r):
        idx = len(V)
        for j in range(seg):
            a = TAU * j / seg
            v = center + Nn * (math.cos(a) * r * flat) + Bb * (math.sin(a) * r)
            V.append((v.x, v.y, v.z))
        rings.append(idx)

    # koppen als halve bollen
    capk = 3
    if caps:
        for q in range(capk, 0, -1):
            ang = math.pi / 2 * q / (capk + 1)
            add_ring(C[0] - T[0] * (math.sin(ang) * rs[0]), frames[0][0], frames[0][1], max(0.05, rs[0] * math.cos(ang)))
    for k in range(n):
        add_ring(C[k], frames[k][0], frames[k][1], rs[k])
    if caps:
        for q in range(1, capk + 1):
            ang = math.pi / 2 * q / (capk + 1)
            add_ring(C[-1] + T[-1] * (math.sin(ang) * rs[-1]), frames[-1][0], frames[-1][1], max(0.05, rs[-1] * math.cos(ang)))
    for i in range(len(rings) - 1):
        a, b = rings[i], rings[i + 1]
        for j in range(seg):
            j1 = (j + 1) % seg
            F.append([a + j, a + j1, b + j1, b + j]); FM.append(None)
    if caps:
        for end, rev in ((rings[0], True), (rings[-1], False)):
            ctr = Vector((0, 0, 0))
            for j in range(seg):
                ctr += Vector(V[end + j])
            ctr /= seg
            V.append((ctr.x, ctr.y, ctr.z)); ci = len(V) - 1
            for j in range(seg):
                f = [ci, end + j, end + (j + 1) % seg]
                F.append(f[::-1] if rev else f); FM.append(None)
    return V, F, FM


def torus(c, rx, rz, r, rot=None, seg=40, segr=10, waves=0, wamp=0.0):
    R = rotm(rot)
    V, F, FM = [], [], []
    for i in range(seg):
        a = TAU * i / seg
        k = 1 + (wamp * math.sin(a * waves) if waves else 0)
        cx, cz = math.cos(a) * rx * k, math.sin(a) * rz * k
        nx, nz = math.cos(a), math.sin(a)
        for j in range(segr):
            b = TAU * j / segr
            v = Vector((cx + nx * math.cos(b) * r, math.sin(b) * r, cz + nz * math.cos(b) * r))
            V.append(c_add(c, R @ v))
    for i in range(seg):
        for j in range(segr):
            a, b = i * segr, ((i + 1) % seg) * segr
            j1 = (j + 1) % segr
            F.append([a + j, b + j, b + j1, a + j1]); FM.append(None)
    return V, F, FM


def box(c, h, rot=None):
    R = rotm(rot)
    V = []
    for i in range(8):
        v = Vector((h[0] if i & 1 else -h[0], h[1] if i & 2 else -h[1], h[2] if i & 4 else -h[2]))
        V.append(c_add(c, R @ v))
    F = [[0, 2, 3, 1], [4, 5, 7, 6], [0, 4, 6, 2], [1, 3, 7, 5], [0, 1, 5, 4], [2, 6, 7, 3]]
    return V, F, [None] * 6


# ------------------------------------------------------------------ bouwer
def segdist(p, a, b):
    p, a, b = Vector(p), Vector(a), Vector(b)
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / max(1e-9, ab.dot(ab))))
    return (p - (a + ab * t)).length


class Rig:
    def __init__(self, name, bones):
        self.name = name
        self.bones = bones          # naam -> (kop, staart, ouder)
        self.V, self.F, self.M, self.W, self.S = [], [], [], [], []
        self.props = []

    def weight(self, v, bone, auto, wf):
        if wf:
            return wf(v)
        if bone:
            return {bone: 1.0}
        ws = []
        for b in auto:
            h, t, _ = self.bones[b]
            d = segdist(v, h, t)
            ws.append((b, 1.0 / (d ** 4 + 1e-2)))
        ws.sort(key=lambda x: -x[1])
        ws = ws[:2]
        s = sum(w for _, w in ws)
        return {b: w / s for b, w in ws}

    def add(self, geo, m, bone=None, auto=None, wf=None, smooth=True, alt=None):
        V, F, FM = geo
        base = len(self.V)
        self.V += V
        for i, f in enumerate(F):
            self.F.append([base + k for k in f])
            self.M.append(FM[i] if (FM[i] and alt is None) else (alt if FM[i] else m) if FM[i] else m)
            self.S.append(smooth)
        for v in V:
            self.W.append(self.weight(v, bone, auto, wf))

    def build(self):
        # armature
        arm_data = bpy.data.armatures.new(self.name + '_rig')
        arm = bpy.data.objects.new(self.name + '_rig', arm_data)
        bpy.context.scene.collection.objects.link(arm)
        bpy.context.view_layer.objects.active = arm
        bpy.ops.object.mode_set(mode='EDIT')
        eb = {}
        for n, (h, t, p) in self.bones.items():
            b = arm_data.edit_bones.new(n)
            b.head = B(h); b.tail = B(t)
            if (b.tail - b.head).length < 1e-4:
                b.tail = b.head + Vector((0, 0, 0.02))
            eb[n] = b
        for n, (h, t, p) in self.bones.items():
            if p:
                eb[n].parent = eb[p]
        bpy.ops.object.mode_set(mode='OBJECT')
        # mesh
        me = bpy.data.meshes.new(self.name)
        me.from_pydata([B(v) for v in self.V], [], self.F)
        mats = []
        for mname in self.M:
            if mname not in mats:
                mats.append(mname)
        for mname in mats:
            me.materials.append(MATS[mname])
        for i, poly in enumerate(me.polygons):
            poly.material_index = mats.index(self.M[i])
            poly.use_smooth = self.S[i]
        me.validate()
        ob = bpy.data.objects.new(self.name, me)
        bpy.context.scene.collection.objects.link(ob)
        groups = {n: ob.vertex_groups.new(name=n) for n in self.bones}
        for vi, w in enumerate(self.W):
            for bn, ww in w.items():
                if ww > 1e-4:
                    groups[bn].add([vi], ww, 'REPLACE')
        mod = ob.modifiers.new('rig', 'ARMATURE')
        mod.object = arm
        ob.parent = arm
        objs = [arm, ob]
        # losse rekwisieten (aan een bot gehangen, kunnen verborgen worden)
        for pname, parts, bone in self.props:
            pm = bpy.data.meshes.new(pname)
            PV, PF, PM, PS = [], [], [], []
            for geo, m, sm in parts:
                V, F, FM = geo
                base = len(PV)
                PV += V
                for i, f in enumerate(F):
                    PF.append([base + k for k in f]); PM.append(FM[i] or m); PS.append(sm)
            pm.from_pydata([B(v) for v in PV], [], PF)
            ml = []
            for mname in PM:
                if mname not in ml:
                    ml.append(mname)
            for mname in ml:
                pm.materials.append(MATS[mname])
            for i, poly in enumerate(pm.polygons):
                poly.material_index = ml.index(PM[i]); poly.use_smooth = PS[i]
            po = bpy.data.objects.new(pname, pm)
            bpy.context.scene.collection.objects.link(po)
            po.parent = arm
            po.parent_type = 'BONE'
            po.parent_bone = bone
            # plaats behouden: wereldmatrix terugzetten na het koppelen
            bpy.context.view_layer.update()
            po.matrix_world = Matrix.Identity(4)
            objs.append(po)
        return objs


def export(objs, name):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    path = os.path.join(OUT, name + '.glb')
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True,
                              export_skins=True, export_animations=False, export_yup=True,
                              export_apply=False, export_materials='EXPORT')
    print('EXPORTED', path)


def mirror_bones(d):
    out = {}
    for n, (h, t, p) in d.items():
        out[n] = (h, t, p)
        if n.endswith('R'):
            m = n[:-1] + 'L'
            out[m] = ((-h[0], h[1], h[2]), (-t[0], t[1], t[2]), p[:-1] + 'L' if p and p.endswith('R') else p)
    return out


# ------------------------------------------------------------------ gedeelde kleuren
SKIN = mat('skin', '#f2c09a', 0.5, sss=0.25)
SKIN_D = mat('skin_d', '#e59d80', 0.55)
WHITE_EYE = mat('eye_white', '#fbf8f2', 0.25)
PUPIL = mat('pupil', '#100806', 0.2)
GLINT = mat('glint', '#ffffff', 0.1, emit=2.0)
GOLD = mat('gold', '#e7b445', 0.32, metal=0.85)
BLUSH = mat('blush', '#ef9785', 0.6)


def face_eyes(rig, bone, cx, cy, cz, sep, iris_col, size=1.0, lid=None):
    IR = mat('iris_' + iris_col, iris_col, 0.3)
    for s in (-1, 1):
        x = cx + s * sep
        rig.add(ellipsoid((x, cy, cz), (3.0 * size, 3.4 * size, 1.6 * size), seg=16, rings=10), WHITE_EYE, bone)
        rig.add(ellipsoid((x - s * 0.15, cy - 0.3 * size, cz + 1.15 * size), (2.0 * size, 2.35 * size, 0.85 * size), seg=14, rings=8), IR, bone)
        rig.add(ellipsoid((x - s * 0.15, cy - 0.35 * size, cz + 1.75 * size), (1.05 * size, 1.25 * size, 0.45 * size), seg=12, rings=6), PUPIL, bone)
        rig.add(ellipsoid((x - s * 0.15 - 0.7 * size, cy + 0.9 * size, cz + 2.0 * size), (0.6 * size, 0.7 * size, 0.3 * size), seg=8, rings=5), GLINT, bone)
        if lid:
            rig.add(ellipsoid((x, cy + 1.3 * size, cz + 0.25), (3.3 * size, 1.6 * size, 1.9 * size), seg=16, rings=8), lid, bone)


# ================================================================== PIET
def make_piet(name, A, Bc, CAPc, FEA, prop, seed):
    rnd = random.Random(seed)
    mA = mat(name + '_a', A, 0.55, sheen=0.4)
    mB = mat(name + '_b', Bc, 0.45, sheen=0.3)
    mCap = mat(name + '_cap', CAPc, 0.6, sheen=0.5)
    mFea = mat(name + '_fea', FEA, 0.7, sheen=0.6)
    HAIR = mat('hair_piet', '#4e2a16', 0.65)
    SOCK = mat('sock', '#f3efe8', 0.7)
    SHOE = mat('shoe', '#17131a', 0.35)
    GLOVE = mat('glove', '#221c26', 0.5)
    LACE = mat('lace', '#fbf7ef', 0.7)
    BELT = mat('belt', '#4a2a18', 0.5)
    LIP = mat('lip', '#8a2a26', 0.5)
    SOOT = mat('soot', '#6e4a3c', 0.8)

    bones = mirror_bones({
        'root': ((0, 0, 0), (0, 10, 0), None),
        'hip': ((0, 56, 0), (0, 64, 0), 'root'),
        'chest': ((0, 64, 0), (0, 88, 0), 'hip'),
        'neck': ((0, 88, 0), (0, 96, 0.5), 'chest'),
        'head': ((0, 96, 0.5), (0, 126, 0.5), 'neck'),
        'cap': ((0, 126, -1), (0, 134, -1), 'head'),
        'feather': ((-7, 130, -4), (-9, 146, -16), 'cap'),
        'shR': ((-15.5, 85, 0), (-16, 67, 0), 'chest'),
        'elR': ((-16, 67, 0), (-16, 50, 1), 'shR'),
        'haR': ((-16, 50, 1), (-16, 42, 1.5), 'elR'),
        'thR': ((-8, 52, 0), (-8, 28, 0.5), 'hip'),
        'knR': ((-8, 28, 0.5), (-8, 6, 0), 'thR'),
        'ftR': ((-8, 6, 0), (-8, 2, 12), 'knR'),
    })
    rig = Rig(name, bones)

    for s, side in ((-1, 'R'), (1, 'L')):
        x = 8 * s
        # kousen
        rig.add(tube([(x, 56, 0), (x * 1.02, 40, 0.3), (x * 1.03, 28, 0.5), (x * 1.02, 18, -0.4), (x, 6, 0)], [6.8, 5.6, 4.5, 4.8, 3.5], seg=16), SOCK,
                auto=['th' + side, 'kn' + side])
        # schoenen
        rig.add(ellipsoid((x, 3.4, 4.5), (5.4, 3.6, 9.5)), SHOE, 'ft' + side)
        rig.add(ellipsoid((x, 3.3, 11.5), (4.4, 3.2, 4.2)), SHOE, 'ft' + side)
        rig.add(ellipsoid((x, 1.2, 5), (5.6, 1.2, 11)), mat('sole', '#2a2024', 0.6), 'ft' + side)
        rig.add(box((x, 6.4, 8.6), (2.4, 1.7, 0.6), (-30, 0, 0)), GOLD, 'ft' + side, smooth=False)
        # pofmouw
        rig.add(ellipsoid((15.8 * s, 80.5, 0), (8.6, 9.6, 8.6), stripe=lambda j: mB if (j // 2) % 2 == 0 else None), mA, 'sh' + side)
        # onderarm + kant + handschoen
        rig.add(tube([(15.8 * s, 78, 0), (16.2 * s, 67, 0.2), (16 * s, 51, 1)], [6.0, 5.0, 4.4], seg=14), mA, auto=['sh' + side, 'el' + side])
        rig.add(torus((16 * s, 51.5, 1), 4.6, 4.6, 1.5, waves=12, wamp=0.12, segr=8), LACE, 'el' + side)
        rig.add(ellipsoid((16 * s, 45.6, 1.6), (4.4, 5.3, 4.3)), GLOVE, 'ha' + side)
        rig.add(ellipsoid((13.8 * s, 47.5, 4.2), (1.8, 2.9, 1.8), rot=(0, 0, -25 * s)), GLOVE, 'ha' + side)

    # pofbroek met verticale banen
    stripeP = lambda i, j: mB if (j // 2) % 2 == 0 else None
    rig.add(lathe((0, 0, 0), [(40, 8.5, 8.5), (42, 14.5, 13.5), (46, 19.5, 17.5), (52, 20.8, 18.5), (58, 19.5, 16.8), (62, 15.8, 13.8), (65, 13.6, 12)],
                  seg=32, stripe=stripeP), mA, auto=['hip', 'thR', 'thL'])
    rig.add(torus((0, 64.5, 0), 13.8, 12.2, 1.7, segr=8), BELT, 'hip')
    rig.add(box((0, 64.5, 12.6), (2.6, 2.2, 0.8)), GOLD, 'hip', smooth=False)
    # wambuis
    stripeD = lambda i, j: mB if j % 4 == 0 else None
    rig.add(lathe((0, 0, 0), [(63, 13.6, 12), (68, 15.2, 12.9), (75, 17.2, 14.2), (82, 17.2, 13.8), (86.5, 14.8, 11.8), (90, 8.5, 7.5)],
                  seg=32, stripe=stripeD), mA, auto=['hip', 'chest'])
    for y in (70, 76, 82):
        rig.add(ellipsoid((0, y, 13.6 + (y - 70) * 0.05 + (1 if y == 76 else 0)), (1.3, 1.3, 0.8), seg=10, rings=6), GOLD, 'chest')
    # kraag (ruches)
    rig.add(torus((0, 89, 0.5), 12.5, 11.5, 3.8, waves=14, wamp=0.1, segr=10), LACE, 'chest')
    rig.add(torus((0, 91.5, 0.5), 9.5, 8.8, 2.6, waves=12, wamp=0.1, segr=8), LACE, 'chest')
    # nek
    rig.add(tube([(0, 88, 0), (0, 99, 0.6)], [5.2, 5.2], seg=12), SKIN, auto=['neck', 'head'])

    # hoofd
    hb = 'head'
    rig.add(ellipsoid((0, 112, 0), (16.5, 16.2, 16.6)), SKIN, hb)
    rig.add(ellipsoid((0, 105, 3.6), (13.6, 10.6, 12.6)), SKIN, hb)
    rig.add(ellipsoid((0, 100.6, 7), (6.2, 4.2, 5.2)), SKIN, hb)
    for s in (-1, 1):
        rig.add(ellipsoid((16.2 * s, 109, -0.5), (2.6, 4.4, 3.6)), SKIN_D, hb)
        rig.add(ellipsoid((9.6 * s, 105.6, 12.4), (3.6, 2.5, 1.6)), BLUSH, hb)
        rig.add(tube([(2.6 * s, 117, 15.4), (6 * s, 118.2, 15), (9 * s, 117.2, 13.6)], [0.9, 1.05, 0.7], seg=8), HAIR, hb)
    face_eyes(rig, hb, 0, 111.4, 14.3, 5.6, '#5a321a')
    rig.add(ellipsoid((0, 107.2, 16.4), (2.7, 2.4, 2.6)), SKIN_D, hb)
    rig.add(tube([(-5, 103.6, 14.4), (-2.6, 102, 15.5), (0, 101.6, 15.9), (2.6, 102, 15.5), (5, 103.6, 14.4)], [0.7, 0.85, 0.9, 0.85, 0.7], seg=8), LIP, hb)
    rig.add(ellipsoid((7.8, 102.6, 13.4), (2.6, 1.6, 0.9)), SOOT, hb)
    rig.add(ellipsoid((-11, 110.5, 12.2), (2.0, 1.4, 0.9)), SOOT, hb)
    # krullen
    rig.add(ellipsoid((0, 114.5, -2.8), (17.3, 16.8, 16)), HAIR, hb)
    for k in range(70):
        th = rnd.uniform(0, math.pi * 0.62)       # vanaf de kruin
        ph = rnd.uniform(0, TAU)
        d = Vector((math.sin(th) * math.cos(ph), math.cos(th), math.sin(th) * math.sin(ph)))
        p = Vector((0, 113, -1.5)) + Vector((d.x * 16.2, d.y * 16, d.z * 16))
        if p.z > 7 and p.y < 121:          # gezicht vrijhouden
            continue
        if p.y < 101:
            continue
        r = rnd.uniform(3.0, 4.3)
        rig.add(ellipsoid((p.x, p.y, p.z), (r, r * 0.9, r), seg=12, rings=8), HAIR, hb)
    # baret (slap, scheef) met band
    capb = 'cap'
    rig.add(ellipsoid((3.5, 130.5, -4), (27.5, 8.6, 26), rot=(11, 0, -12), stripe=lambda j: mB if j % 6 == 0 else None), mCap, capb)
    rig.add(ellipsoid((5, 134.5, -5.5), (21, 7.5, 19.5), rot=(11, 0, -12), stripe=lambda j: mB if j % 6 == 0 else None), mCap, capb)
    rig.add(torus((0.5, 125.8, -1), 17.2, 16.8, 2.4, rot=(4, 0, -6), segr=8), mB, capb)
    # pluim: platte, golvende buis
    rig.add(tube([(-7, 130, -4), (-10, 138, -9), (-12.5, 146, -17), (-12, 152, -26), (-8, 155, -35), (-3, 153, -42)],
                 [1.0, 8.5, 11.5, 11, 8.5, 2.5], seg=16, flat=0.32, up=(1, 0, 0),
                 wav=lambda u: 1 + 0.1 * math.sin(u * 46)), mFea, 'feather')
    rig.add(tube([(-7, 131, -5), (-12, 140, -6), (-16, 147, -11), (-18, 151, -19), (-16, 152, -27)],
                 [0.8, 6, 8, 6.5, 2], seg=14, flat=0.32, up=(1, 0, 0.3),
                 wav=lambda u: 1 + 0.1 * math.sin(u * 40 + 1)), mFea, 'feather')
    rig.add(tube([(-7, 130, -4), (-10.4, 138.5, -9.4), (-12.6, 146.4, -17.4), (-12, 152.4, -26.4), (-8, 155.4, -35.4)], [0.5, 0.5, 0.45, 0.4, 0.3], seg=6),
            mat('rachis', '#fff1c8', 0.5), 'feather')

    # rekwisieten
    if prop == 'gift':
        RED = mat('giftred', '#c81f2c', 0.45); YEL = mat('giftyel', '#f0b42a', 0.45); RIB = mat('ribbon', '#f6c43e', 0.3, metal=0.3)
        RIB2 = mat('ribbon2', '#c81f2c', 0.4)
        parts = [
            (box((0, 74, 23), (13, 9, 10)), RED, False),
            (box((0, 74, 23), (2.2, 9.3, 10.3)), RIB, False),
            (box((0, 74, 23), (13.3, 9.3, 2.2)), RIB, False),
            (box((0, 89, 22), (10, 6.2, 8)), YEL, False),
            (box((0, 89, 22), (1.8, 6.5, 8.3)), RIB2, False),
            (box((0, 89, 22), (10.3, 6.5, 1.8)), RIB2, False),
            (torus((-3.2, 97.5, 22), 3.6, 1.6, 1.2, rot=(0, 0, 60)), RIB2, True),
            (torus((3.2, 97.5, 22), 3.6, 1.6, 1.2, rot=(0, 0, -60)), RIB2, True),
            (ellipsoid((0, 96, 22), (1.8, 1.6, 1.6)), RIB2, True),
        ]
        rig.props.append(('gift', parts, 'chest'))
    elif prop == 'sack':
        SACK = mat('sack', '#d6b47a', 0.85)
        sv, sf, sfm = ellipsoid((12, 93, -16), (19, 18, 15), seg=28, rings=18)
        r2 = random.Random(5)
        bumps = [(Vector((r2.uniform(-1, 1), r2.uniform(-1, 1), r2.uniform(-1, 1))).normalized(), r2.uniform(0.05, 0.12)) for _ in range(9)]
        out = []
        for v in sv:
            d = (Vector(v) - Vector((12, 93, -16)))
            dn = d.normalized()
            k = 1 + sum(a * max(0, dn.dot(b)) ** 6 for b, a in bumps)
            w = Vector((12, 93, -16)) + d * k
            out.append((w.x, w.y, w.z))
        parts = [((out, sf, sfm), SACK, True),
                 (tube([(3, 107, -9), (1, 111, -7), (0, 114, -6)], [5, 2.5, 3.5], seg=12), SACK, True),
                 (torus((2.6, 108.5, -8.6), 3.4, 3.4, 0.9, rot=(20, 0, 30), segr=6), mat('rope', '#8a5a2a', 0.8), True)]
        rig.props.append(('sack', parts, 'chest'))
    return rig


# ================================================================== SINT
def make_sint(riding=False):
    """riding=True: zittend te paard (benen schrijlings, kortere mantel)."""
    rnd = random.Random(11)
    RED = mat('sint_red', '#b51b2a', 0.62, sheen=0.7)
    RED_D = mat('sint_red_d', '#951425', 0.6, sheen=0.7)
    ALB = mat('alb', '#f5f0e7', 0.75, sheen=0.3)
    BEARD = mat('beard', '#f7f4ef', 0.8, sheen=0.4)
    GLOVE = mat('sint_glove', '#f6f2ea', 0.6)
    SHOE = mat('shoe', '#17131a', 0.35)
    MITRE = mat('mitre', '#c31f2e', 0.5, sheen=0.5)
    LACE = mat('lace', '#fbf7ef', 0.7)

    bones = mirror_bones({
        'root': ((0, 0, 0), (0, 10, 0), None),
        'hip': ((0, 92, 0), (0, 120, 0), 'root'),
        'cape': ((0, 118, -4), (0, 40, -8), 'hip'),
        'chest': ((0, 120, 0), (0, 150, 0), 'hip'),
        'neck': ((0, 150, 1), (0, 158, 1), 'chest'),
        'head': ((0, 158, 1), (0, 205, 1), 'neck'),
        'shR': ((-25, 144, -1), (-25.5, 121, 0), 'chest'),
        'elR': ((-25.5, 121, 0), (-25, 99, 1), 'shR'),
        'haR': ((-25, 99, 1), (-25, 90, 1), 'elR'),
        'ftR': ((-10, 4, 8), (-10, 2, 22), 'root'),
    } if not riding else {
        'root': ((0, 0, 0), (0, 10, 0), None),
        'hip': ((0, 92, 0), (0, 120, 0), 'root'),
        'cape': ((0, 118, -4), (0, 60, -12), 'hip'),
        'chest': ((0, 120, 0), (0, 150, 0), 'hip'),
        'neck': ((0, 150, 1), (0, 158, 1), 'chest'),
        'head': ((0, 158, 1), (0, 205, 1), 'neck'),
        'shR': ((-25, 144, -1), (-25.5, 121, 0), 'chest'),
        'elR': ((-25.5, 121, 0), (-25, 99, 1), 'shR'),
        'haR': ((-25, 99, 1), (-25, 90, 1), 'elR'),
        'thR': ((-11, 90, 2), (-30, 78, 20), 'hip'),
        'knR': ((-30, 78, 20), (-33, 38, 12), 'thR'),
        'ftR': ((-33, 38, 12), (-33, 31, 24), 'knR'),
    })
    bones['staff'] = ((25, 92, 1), (25, 150, 1), 'haL')
    rig = Rig('sint_rider' if riding else 'sint', bones)

    def wcape(v):
        y = v[1]
        wc = smoothstep(112, 50 if not riding else 66, y) * 0.95
        wch = smoothstep(108, 124, y) * (1 - wc)
        wh = max(0.0, 1 - wc - wch)
        d = {'cape': wc, 'chest': wch, 'hip': wh}
        return {k: x for k, x in d.items() if x > 1e-3}

    for s, side in ((-1, 'R'), (1, 'L')):
        if riding:
            # benen schrijlings in de albe, kanten zoom, schoen in de stijgbeugel
            rig.add(tube([(11 * s, 92, 1), (22 * s, 86, 11), (30 * s, 78, 20), (32.5 * s, 58, 17), (33 * s, 40, 12)], [11, 10, 8.6, 7.4, 6.8], seg=18),
                    ALB, auto=['th' + side, 'kn' + side])
            rig.add(torus((33 * s, 41, 12), 7.6, 7.6, 1.8, waves=12, wamp=0.1, segr=8), LACE, 'kn' + side)
            rig.add(torus((33 * s, 45, 12.5), 7.4, 7.4, 1.0, segr=6), GOLD, 'kn' + side)
            rig.add(ellipsoid((33 * s, 33.5, 19), (5.6, 4.2, 10.5)), SHOE, 'ft' + side)
        else:
            rig.add(ellipsoid((10 * s, 3.8, 12), (6.6, 4.2, 10.5)), SHOE, 'ft' + side)
        # mouw (wijd), kant, goud, handschoen
        rig.add(tube([(25 * s, 146, -1), (25.6 * s, 132, -0.5), (25.5 * s, 121, 0), (25.2 * s, 109, 0.5), (25 * s, 100, 1)], [10.0, 9.4, 9.2, 10.2, 11.2], seg=20, caps=False),
                RED, auto=['sh' + side, 'el' + side])
        rig.add(torus((25 * s, 101.5, 1), 10.9, 10.9, 1.0, segr=6), GOLD, 'el' + side)
        rig.add(torus((25 * s, 99.4, 1), 9.6, 9.6, 1.9, waves=14, wamp=0.1, segr=8), LACE, 'el' + side)
        rig.add(tube([(25 * s, 101, 1), (25 * s, 95, 1.2)], [4.4, 4.2], seg=12), GLOVE, auto=['el' + side, 'ha' + side])
        rig.add(ellipsoid((25 * s, 89.5, 1.4), (5.4, 6.8, 4.8)), GLOVE, 'ha' + side)
        rig.add(ellipsoid((22.2 * s, 92, 4.6), (2.0, 3.2, 2.0), rot=(0, 0, -25 * s)), GLOVE, 'ha' + side)

    if riding:
        # albe als zittende rok over het zadel
        rig.add(lathe((0, 0, 0), [(80, 30, 27), (84, 31, 28), (92, 26, 21), (110, 21.5, 17.5), (126, 19.5, 16)], seg=36), ALB, 'hip')
        cprof = [(60, 52, 46, 0, -16), (80, 46, 40, 0, -10), (100, 36, 29, 0, -4), (118, 28.5, 22.5), (132, 26, 20.5)]
        opening = lambda i: [1.15, 0.95, 0.62, 0.34, 0.22][i]
    else:
        # albe met kanten zoom en goudband
        rig.add(lathe((0, 0, 0), [(1.5, 31, 26), (6, 32, 27), (40, 28.5, 23.5), (80, 24.5, 20), (110, 21.5, 17.5), (126, 19.5, 16)], seg=36,
                      wave=lambda i, a: 1 + (0.025 * math.sin(a * 18) if i == 0 else 0)), ALB, 'hip')
        rig.add(torus((0, 3.5, 0), 31.6, 26.6, 1.6, waves=36, wamp=0.02, segr=8), LACE, 'hip')
        rig.add(torus((0, 12, 0), 31.3, 26.3, 1.4, segr=6), GOLD, 'hip')
        # mantel: open aan de voorkant, wijd uitlopend, met goudboord
        cprof = [(2, 58, 47, 0, -9), (30, 50, 40.5, 0, -6), (70, 38.5, 31.5, 0, -2.5), (100, 31, 25), (118, 28.5, 22.5), (132, 26, 20.5)]
        opening = lambda i: [0.62, 0.58, 0.5, 0.42, 0.34, 0.22][i]
    rig.add(lathe((0, 0, -3), cprof, seg=44, open_a=opening, thick=1.6), RED, wf=wcape)

    # boord langs de opening en de zoom
    def cape_pt(i, a, out=0.9):
        y, rx, rz = cprof[i][0], cprof[i][1] + out, cprof[i][2] + out
        dz = cprof[i][4] if len(cprof[i]) > 4 else 0
        return (math.cos(a) * rx, y, -3 + dz + math.sin(a) * rz)

    for sgn in (-1, 1):
        edge = [cape_pt(i, math.pi / 2 + sgn * opening(i)) for i in range(len(cprof))]
        rig.add(tube(edge, [3.0] * len(edge), seg=10, flat=0.35, up=(0, 0, 1), caps=True), GOLD, wf=wcape)
    hem = []
    for k in range(41):
        h = opening(0)
        a = math.pi / 2 + h + (TAU - 2 * h) * k / 40
        hem.append(cape_pt(0, a, 1.0))
    rig.add(tube(hem, [2.8] * len(hem), seg=8, flat=0.4, up=(0, 1, 0), caps=True), GOLD, wf=wcape)
    # pelerine
    rig.add(lathe((0, 0, -1), [(117, 34, 26.5), (125, 32, 24.5), (133.5, 26, 20), (140, 17, 13.5), (143.5, 10.5, 9)], seg=36), RED_D, 'chest')
    rig.add(torus((0, 117.6, -1), 34.2, 26.7, 1.7, segr=8), GOLD, 'chest')
    rig.add(ellipsoid((0, 136, 19.5), (3.6, 3.6, 2.2)), GOLD, 'chest')
    rig.add(tube([(0, 143, 0), (0, 156, 1)], [8, 8], seg=12), SKIN, auto=['chest', 'neck'])

    # hoofd
    hb = 'head'
    rig.add(ellipsoid((0, 170, 0), (14.6, 16.2, 13.6)), SKIN, hb)
    for s in (-1, 1):
        rig.add(ellipsoid((14.2 * s, 170, -1), (3.0, 4.6, 2.6)), SKIN_D, hb)
        rig.add(ellipsoid((7.6 * s, 166, 10.6), (4.2, 3.2, 1.8)), BLUSH, hb)
        rig.add(tube([(2.4 * s, 177.6, 13.3), (6 * s, 178.8, 12.9), (10.2 * s, 177.2, 10.6)], [1.6, 2.1, 1.3], seg=10), BEARD, hb)
        rig.add(tube([(0.5 * s, 164.6, 15), (4 * s, 164.2, 15.1), (8 * s, 162.8, 13.6), (11.2 * s, 164.4, 10.8)], [2.6, 3.3, 2.8, 1.6], seg=12), BEARD, hb)
    face_eyes(rig, hb, 0, 173.4, 11.9, 5.3, '#3f6f9f', size=0.86, lid=SKIN)
    rig.add(ellipsoid((0, 168.8, 14.4), (3.9, 3.5, 3.7)), SKIN_D, hb)
    # baard: gladde basis met daarop zachte plukken
    rig.add(ellipsoid((0, 147, 7.5), (17, 22, 10)), BEARD, hb)
    rig.add(ellipsoid((0, 160, 8.5), (17.5, 10, 8.5)), BEARD, hb)
    for row in range(11):
        y = 163 - row * 4.6
        w = 17.5 - row * 1.2
        n = max(2, int(w / 3.6))
        for k in range(n + 1):
            x = -w + 2 * w * k / n + rnd.uniform(-1, 1)
            z = 9 + 5.5 * math.sqrt(max(0, 1 - (x / (w + 3)) ** 2)) - row * 0.2
            r = rnd.uniform(5.2, 6.6) - row * 0.2
            rig.add(ellipsoid((x, y + rnd.uniform(-1, 1), z - 1.2), (r, r * 1.25, r * 0.55), rot=(0, 0, rnd.uniform(-25, 25)), seg=14, rings=9), BEARD, hb)
    for s in (-1, 1):                # bakkebaarden en haar opzij/achter
        for k in range(6):
            a = math.radians(-30 + k * 24)
            rig.add(ellipsoid((s * 13.5 * math.cos(a) * 1.05, 168 - k * 1.5, -2 + 13 * math.sin(a) * 0.4 - k * 1.2), (5.2, 6, 5), seg=12, rings=8), BEARD, hb)
    rig.add(ellipsoid((0, 171, -5.5), (15.4, 15, 11.5)), BEARD, hb)
    # mijter
    mprof = [(177.5, 15.8, 13.3), (186, 17.4, 11.0), (198, 18.8, 8.2), (207, 18.0, 5.8), (213.5, 14.0, 3.9), (218, 7.5, 2.2), (220, 0.8, 0.8)]
    rig.add(lathe((0, 0, -0.5), mprof, seg=40), MITRE, hb)
    rig.add(torus((0, 179.2, -0.5), 16.1, 13.6, 2.3, segr=8), GOLD, hb)
    band = [(p[0], p[1] + 0.6, p[2] + 0.6) for p in mprof[:-1]]
    for ry_ in (0, 180):
        rig.add(lathe((0, 0, -0.5), band, seg=6, rot=(0, ry_, 0), open_a=lambda i: math.pi - 0.22, thick=0.6), GOLD, hb)
        rig.add(lathe((0, 0, -0.5), [(196.5, 18.5, 9.3), (200.8, 17.9, 8.1)], seg=12, rot=(0, ry_, 0), open_a=lambda i: math.pi - 0.95, thick=0.6), GOLD, hb)
    rig.add(ellipsoid((0, 221, -0.5), (2.6, 2.6, 2.6)), GOLD, hb)
    for s in (-1, 1):
        rig.add(tube([(6 * s, 180, -11), (7 * s, 166, -14.5), (8 * s, 150, -16.5)], [2.6, 2.6, 2.6], seg=8, flat=0.3, up=(0, 0, 1)), MITRE, hb)
        rig.add(box((8 * s, 149, -16.6), (3, 2, 0.9)), GOLD, hb, smooth=False)
    # staf (aan een eigen bot zodat hij rechtop blijft)
    sx, sz = 25, 1
    rig.add(tube([(sx, -10, sz), (sx, 60, sz), (sx, 150, sz)], [2.0, 2.1, 2.1], seg=12), GOLD, 'staff')
    crook = []
    for i in range(23):
        u = i / 22
        th = math.pi - u * math.pi * 1.75
        r = 9 - u * 4.5
        crook.append((sx + 9 + math.cos(th) * r, 158 + math.sin(th) * r, sz))
    rig.add(tube([(sx, 148, sz)] + crook, [2.2] * 24, seg=12), GOLD, 'staff')
    rig.add(ellipsoid((sx, 136, sz), (3.6, 4.6, 3.6)), GOLD, 'staff')
    rig.add(ellipsoid((sx, 112, sz), (3.0, 3.0, 3.0)), GOLD, 'staff')
    return rig


# ================================================================== PAARD
def make_horse():
    WH = mat('horse', '#f3eee7', 0.6, sheen=0.4)
    WH2 = mat('horse_m', '#ece6dd', 0.6)
    MANE = mat('mane', '#ebe5dc', 0.75, sheen=0.5)
    HOOF = mat('hoof', '#3a3036', 0.4)
    NOSE = mat('nostril', '#6d5552', 0.5)
    RED = mat('horse_red', '#c11f2e', 0.55, sheen=0.6)
    RED_D = mat('horse_red_d', '#8d1522', 0.5)
    EYE = mat('horse_eye', '#1b1010', 0.15)

    bones = {
        'root': ((0, 0, 0), (0, 10, 0), None),
        'body': ((0, 90, 0), (30, 90, 0), 'root'),
        'neck': ((42, 98, 0), (64, 136, 0), 'body'),
        'head': ((66, 138, 0), (92, 110, 0), 'neck'),
        'earL': ((65, 150, 8), (62, 166, 9.5), 'head'),
        'earR': ((65, 150, -8), (62, 166, -9.5), 'head'),
        'tail0': ((-70, 106, 0), (-76, 90, 0), 'body'),
        'tail1': ((-76, 90, 0), (-80, 74, 0), 'tail0'),
        'tail2': ((-80, 74, 0), (-82, 58, 0), 'tail1'),
        'tail3': ((-82, 58, 0), (-83, 40, 0), 'tail2'),
    }
    for nm, x, z, hind in (('legFR', 46, 13, False), ('legFL', 46, -13, False), ('legBR', -48, 13, True), ('legBL', -48, -13, True)):
        if hind:
            bones[nm] = ((x, 80, z), (x + 5, 46, z), 'body')
            bones[nm + 'k'] = ((x + 5, 46, z), (x + 3, 9, z), nm)
            bones[nm + 'h'] = ((x + 3, 9, z), (x + 3, 0, z), nm + 'k')
        else:
            bones[nm] = ((x, 78, z), (x, 42, z), 'body')
            bones[nm + 'k'] = ((x, 42, z), (x, 7, z), nm)
            bones[nm + 'h'] = ((x, 7, z), (x, 0, z), nm + 'k')
    rig = Rig('horse', bones)
    bb = 'body'
    rig.add(ellipsoid((0, 90, 0), (60, 31, 27), seg=32, rings=18), WH, bb)
    rig.add(ellipsoid((44, 92, 0), (28, 30, 25.5)), WH, bb)
    rig.add(ellipsoid((-46, 94, 0), (30, 32, 28.5)), WH, bb)
    rig.add(ellipsoid((30, 109, 0), (20, 13, 13)), WH, bb)
    # hals en hoofd
    rig.add(tube([(34, 96, 0), (46, 112, 0), (56, 127, 0), (65, 139, 0)], [25, 19.5, 15.5, 13], seg=20, flat=0.78, up=(0, 0, 1)), WH, auto=['body', 'neck', 'head'])
    hb = 'head'
    rig.add(ellipsoid((67, 139, 0), (14, 13.5, 11.8)), WH, hb)
    rig.add(ellipsoid((71, 129, 0), (12.5, 10.5, 10.5)), WH, hb)
    rig.add(tube([(66, 140, 0), (76, 128, 0), (85, 117, 0), (91, 110, 0)], [11.8, 10.8, 9.6, 9.6], seg=18, flat=0.85, up=(0, 0, 1)), WH, hb)
    rig.add(ellipsoid((92, 107.5, 0), (10.8, 10.2, 10.2)), mat('muzzle', '#ece3da', 0.6), hb)
    for s in (-1, 1):
        rig.add(ellipsoid((97.5, 108.5, 5.2 * s), (1.9, 2.8, 1.4), rot=(0, 0, 30)), NOSE, hb)
        rig.add(ellipsoid((72, 137.5, 10.2 * s), (3.0, 3.6, 2.0)), EYE, hb)
        rig.add(ellipsoid((72.6, 138.8, 11.8 * s), (0.9, 1.0, 0.5)), GLINT, hb)
        # oren
        rig.add(tube([(65, 149, 8 * s), (63.5, 158, 9 * s), (62, 166.5, 9.5 * s)], [4.6, 3.5, 0.5], seg=12, flat=0.55, up=(1, 0, 0)), WH, 'ear' + ('L' if s > 0 else 'R'))
        # hoofdstel
        rig.add(tube([(68, 150, 10 * s), (70, 140, 11.6 * s), (78, 122, 10.6 * s), (86, 113, 10.2 * s)], [1.3] * 4, seg=6), RED, hb)
        rig.add(ellipsoid((78, 123, 10.9 * s), (2.3, 2.3, 1.2)), GOLD, hb)
    rig.add(torus((86, 113, 0), 10.2, 10.6, 1.5, rot=(0, 0, 55), segr=6), RED, hb)
    rig.add(tube([(66, 148, -10), (68, 151, 0), (66, 148, 10)], [1.3] * 3, seg=6), RED, hb)
    rig.add(ellipsoid((64, 149, 0), (8, 6, 8)), MANE, hb)
    rig.add(ellipsoid((70, 146, 2), (7, 4.5, 6), rot=(0, 0, -40)), MANE, hb)
    # manen
    for i in range(9):
        u = i / 8
        x, y = 30 + u * 34, 114 + u * 32
        rig.add(ellipsoid((x - 2, y + 4, -1.5), (9 - u * 2.5, 11, 6.5), rot=(0, 0, 35)), MANE, auto=['body', 'neck', 'head'])
        rig.add(tube([(x, y + 6, -3), (x - 3, y - 4, -7), (x - 6, y - 14, -8.5)], [4.5, 3.5, 1.2], seg=8, flat=0.5, up=(0, 0, 1)), MANE, auto=['neck', 'head'])
    # benen
    for nm, x, z, hind in (('legFR', 46, 13, False), ('legFL', 46, -13, False), ('legBR', -48, 13, True), ('legBL', -48, -13, True)):
        if hind:
            pts = [(x, 90, z), (x + 3, 66, z * 1.05), (x + 5, 46, z), (x + 4, 28, z), (x + 3, 9, z)]
            rad = [17, 11.5, 7.6, 5.8, 6.2]
            hx = x + 3
        else:
            pts = [(x, 86, z), (x + 0.5, 62, z * 1.03), (x, 42, z), (x, 25, z), (x, 7, z)]
            rad = [14, 9.5, 7.4, 5.6, 6.2]
            hx = x
        rig.add(tube(pts, rad, seg=16), WH, auto=[nm, nm + 'k'])
        rig.add(ellipsoid((pts[2][0], pts[2][1], z), (7.8, 8, 7.4)), WH2, auto=[nm, nm + 'k'])
        rig.add(ellipsoid((hx, 9, z), (6.8, 5.8, 6.6)), WH2, nm + 'k')
        rig.add(lathe((hx, 0, z), [(0, 7.8, 7.2), (4, 7.0, 6.4), (7.5, 6.2, 5.8)], seg=20), HOOF, nm + 'h')
    # staart
    rig.add(tube([(-68, 107, 0), (-75, 92, 0), (-79, 76, 0), (-82, 58, 0), (-83, 40, 0), (-82, 32, 0)], [5, 8.5, 10.5, 10, 7, 2.5], seg=16, flat=0.6, up=(0, 0, 1),
                 wav=lambda u: 1 + 0.06 * math.sin(u * 30)), MANE, auto=['body', 'tail0', 'tail1', 'tail2', 'tail3'])
    # dekkleed: lap stof over de rug, met goudboord en kwastjes
    V, F, FM = [], [], []
    nx, na = 18, 26
    th0 = math.radians(118)
    ry, rz = 33.6, 30

    def bl(x, th, out=0.0):
        return (x, 91 + math.cos(th) * (ry + out), math.sin(th) * (rz + out))

    for i in range(nx + 1):
        x = -38 + 66 * i / nx
        for j in range(na + 1):
            V.append(bl(x, -th0 + 2 * th0 * j / na))
    for i in range(nx):
        for j in range(na):
            a, b = i * (na + 1), (i + 1) * (na + 1)
            F.append([a + j, a + j + 1, b + j + 1, b + j]); FM.append(None)
    base = len(V)
    for i in range(nx + 1):
        x = -38 + 66 * i / nx
        for j in range(na + 1):
            V.append(bl(x, -th0 + 2 * th0 * j / na, -1.2))
    for i in range(nx):
        for j in range(na):
            a, b = base + i * (na + 1), base + (i + 1) * (na + 1)
            F.append([a + j, b + j, b + j + 1, a + j + 1]); FM.append(None)
    rig.add((V, F, FM), RED, bb)
    for x in (-38, 28):
        rig.add(tube([bl(x, -th0 + 2 * th0 * j / 12, 0.6) for j in range(13)], [1.8] * 13, seg=8), GOLD, bb)
    for sgn in (-1, 1):
        rig.add(tube([bl(-38 + 66 * i / 10, sgn * th0, 0.6) for i in range(11)], [1.8] * 11, seg=8), GOLD, bb)
        for i in range(12):
            p = bl(-36 + 62 * i / 11, sgn * th0, 0.8)
            rig.add(ellipsoid((p[0], p[1] - 2.6, p[2]), (1.3, 2.6, 1.3), seg=8, rings=5), GOLD, bb)
    rig.add(ellipsoid((-6, 123, 0), (16, 4.6, 17.5)), RED_D, bb)
    rig.add(ellipsoid((-18, 126, 0), (4, 5, 14)), RED_D, bb)
    rig.add(tube([(28, 112, 25.5), (58, 98, 23), (70, 91, 0), (58, 98, -23), (28, 112, -25.5)], [2.0] * 5, seg=8), RED, bb)
    for s in (-1, 1):
        rig.add(ellipsoid((62, 96, 18 * s), (2.4, 2.4, 1.4)), GOLD, bb)
    rig.add(torus((16, 86, 0), 2.0, 2.0, 1.0), RED_D, bb)   # placeholder klein (singel zit onder het kleed)
    return rig


# ================================================================== main
def main():
    os.makedirs(OUT, exist_ok=True)
    rigs = [
        ('sint', make_sint()),
        ('piet_zak', make_piet('piet_zak', '#6a2a8c', '#f2b632', '#5a2278', '#a03cd6', 'sack', 3)),
        ('piet_pakje', make_piet('piet_pakje', '#2a4aa8', '#f2b632', '#203a8a', '#f6d040', 'gift', 4)),
        ('paard', make_horse()),
        ('sint_rider', make_sint(riding=True)),
    ]
    for name, rig in rigs:
        for o in list(bpy.context.scene.objects):
            bpy.data.objects.remove(o, do_unlink=True)
        objs = rig.build()
        export(objs, name)


if __name__ == '__main__':
    main()

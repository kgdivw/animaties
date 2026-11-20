"""
Gedeelde hulpjes voor de Blender-scène: camera die de template-compositie volgt,
mesh-bouwers en procedurele materialen.

Wereld (Blender): x rechts, y = diepte (weg van de camera), z omhoog, meters.
De camera staat in (0, 0, H) en kijkt horizontaal langs +y. Met S2W() zet je een
pixel van de template (1672 x 941) plus een diepte om naar een wereldpunt, zodat
alles op dezelfde plek in beeld komt als in ref.png.
"""
import bpy, math, bmesh
from mathutils import Vector, Matrix

W_PX, H_PX = 1672, 941
F_PX = 1200.0          # brandpuntsafstand in pixels (≈ 26 mm op 36 mm sensor)
CX, CY = 836.0, 520.0  # optisch midden; CY = horizon
H = 2.2                # camerahoogte (m) — bepaalt de 'diorama'-schaal
TAU = math.pi * 2


def S2W(sx, sy, d):
    """Pixel (sx, sy) op diepte d (m) → wereldpunt."""
    return Vector(((sx - CX) * d / F_PX, d, H + (CY - sy) * d / F_PX))


def ground_d(sy):
    """Diepte waar de grond (z=0) op beeldregel sy ligt."""
    return H * F_PX / (sy - CY)


def px(d):
    """Hoeveel pixels is 1 m op diepte d."""
    return F_PX / d


def setup_camera(scene):
    cam_d = bpy.data.cameras.new('cam')
    cam_d.sensor_fit = 'HORIZONTAL'
    cam_d.sensor_width = 36
    cam_d.lens = 36 * F_PX / W_PX
    cam_d.shift_x = 0.0
    cam_d.shift_y = (CY - H_PX / 2) / W_PX        # horizon op regel CY (onder het midden → beeld omhoog schuiven)
    cam_d.clip_start = 0.1
    cam_d.clip_end = 400
    cam = bpy.data.objects.new('cam', cam_d)
    scene.collection.objects.link(cam)
    cam.location = (0, 0, H)
    cam.rotation_euler = (math.radians(90), 0, 0)
    scene.camera = cam
    scene.render.resolution_x, scene.render.resolution_y = W_PX, H_PX
    return cam


# ------------------------------------------------------------------ collecties
def coll(name):
    c = bpy.data.collections.get(name)
    if not c:
        c = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(c)
    return c


def obj_from(name, V, F, mat=None, smooth=False, col='env', mats=None, fmat=None, uv=None, recalc=True):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in V], [], F)
    me.validate()
    if uv is not None:
        lay = me.uv_layers.new(name='UVMap')
        for poly in me.polygons:
            for li in poly.loop_indices:
                lay.data[li].uv = uv[me.loops[li].vertex_index]
    if recalc:
        bm = bmesh.new(); bm.from_mesh(me)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me)
    coll(col).objects.link(ob)
    if mats:
        for m in mats:
            me.materials.append(m)
        if fmat:
            for i, p in enumerate(me.polygons):
                p.material_index = fmat[i]
    elif mat:
        me.materials.append(mat)
    for p in me.polygons:
        p.use_smooth = smooth
    return ob


def box(name, c, size, mat, col='env', rot=None, bevel=0.0):
    """Doos rond middelpunt c met afmetingen size (x, y, z)."""
    hx, hy, hz = size[0] / 2, size[1] / 2, size[2] / 2
    V = [(-hx, -hy, -hz), (hx, -hy, -hz), (hx, hy, -hz), (-hx, hy, -hz), (-hx, -hy, hz), (hx, -hy, hz), (hx, hy, hz), (-hx, hy, hz)]
    F = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    ob = obj_from(name, V, F, mat, col=col)
    ob.location = c
    if rot:
        ob.rotation_euler = rot
    if bevel > 0:
        m = ob.modifiers.new('bev', 'BEVEL')
        m.width = bevel; m.segments = 2; m.limit_method = 'ANGLE'
    return ob


def prism(name, pts2d, y0, y1, mat, col='env'):
    """Extrudeer een veelhoek in het x/z-vlak van diepte y0 tot y1 (gevels, daken)."""
    n = len(pts2d)
    V = [(p[0], y0, p[1]) for p in pts2d] + [(p[0], y1, p[1]) for p in pts2d]
    F = [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))]
    for i in range(n):
        j = (i + 1) % n
        F.append((i, j, n + j, n + i))
    return obj_from(name, V, F, mat, col=col)


def lathe(name, c, prof, mat, seg=32, col='env', smooth=True, cap=True):
    """Draaivorm om de z-as. prof: [(z, r)] of [(z, rx, ry)]."""
    V, F = [], []
    for (pr) in prof:
        z = pr[0]; rx = pr[1]; ry = pr[2] if len(pr) > 2 else pr[1]
        for j in range(seg):
            a = TAU * j / seg
            V.append((c[0] + math.cos(a) * rx, c[1] + math.sin(a) * ry, c[2] + z))
    n = len(prof)
    for i in range(n - 1):
        for j in range(seg):
            j1 = (j + 1) % seg
            a, b = i * seg, (i + 1) * seg
            F.append((a + j, a + j1, b + j1, b + j))
    if cap:
        V.append((c[0], c[1], c[2] + prof[0][0])); ci = len(V) - 1
        for j in range(seg):
            F.append((ci, (j + 1) % seg, j))
        V.append((c[0], c[1], c[2] + prof[-1][0])); ci = len(V) - 1
        a = (n - 1) * seg
        for j in range(seg):
            F.append((ci, a + j, a + (j + 1) % seg))
    return obj_from(name, V, F, mat, smooth=smooth, col=col)


def tube(name, pts, radii, mat, seg=12, col='env', smooth=True):
    """Buis door punten (wereld), straal per punt; eenvoudige frames."""
    P = [Vector(p) for p in pts]
    n = len(P)
    V, F = [], []
    up = Vector((0, 0, 1))
    N = None
    for k in range(n):
        t = (P[min(n - 1, k + 1)] - P[max(0, k - 1)]).normalized()
        if N is None:
            N = t.cross(up)
            if N.length < 1e-4:
                N = t.cross(Vector((1, 0, 0)))
            N.normalize()
        else:
            N = (N - t * N.dot(t)).normalized()
        Bn = t.cross(N)
        for j in range(seg):
            a = TAU * j / seg
            v = P[k] + (N * math.cos(a) + Bn * math.sin(a)) * radii[k]
            V.append(tuple(v))
    for k in range(n - 1):
        for j in range(seg):
            j1 = (j + 1) % seg
            F.append((k * seg + j, k * seg + j1, (k + 1) * seg + j1, (k + 1) * seg + j))
    for end, rev in ((0, True), (n - 1, False)):
        V.append(tuple(P[end])); ci = len(V) - 1
        for j in range(seg):
            f = (ci, end * seg + j, end * seg + (j + 1) % seg)
            F.append(f[::-1] if rev else f)
    return obj_from(name, V, F, mat, smooth=smooth, col=col)


def ellipsoid(name, c, r, mat, seg=24, rings=14, col='env'):
    V, F = [(c[0], c[1], c[2] + r[2])], []
    for i in range(1, rings):
        t = math.pi * i / rings
        for j in range(seg):
            p = TAU * j / seg
            V.append((c[0] + math.sin(t) * math.cos(p) * r[0], c[1] + math.sin(t) * math.sin(p) * r[1], c[2] + math.cos(t) * r[2]))
    V.append((c[0], c[1], c[2] - r[2])); bot = len(V) - 1
    for j in range(seg):
        F.append((0, 1 + j, 1 + (j + 1) % seg))
    for i in range(rings - 2):
        a, b = 1 + i * seg, 1 + (i + 1) * seg
        for j in range(seg):
            j1 = (j + 1) % seg
            F.append((a + j, b + j, b + j1, a + j1))
    a = 1 + (rings - 2) * seg
    for j in range(seg):
        F.append((a + (j + 1) % seg, a + j, bot))
    return obj_from(name, V, F, mat, smooth=True, col=col)


def join(objs, name):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    objs[0].name = name
    return objs[0]


# ------------------------------------------------------------------ materialen
MAT = {}


def hexlin(h):
    h = h.lstrip('#')
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple([x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c] + [1.0])


class NB:
    """Kleine node-bouwer."""
    def __init__(self, m):
        self.m = m
        self.nt = m.node_tree
        self.n = self.nt.nodes
        self.l = self.nt.links
        self.out = self.n.get('Material Output')
        self.bsdf = self.n.get('Principled BSDF')

    def node(self, t, **kw):
        nd = self.n.new(t)
        for k, v in kw.items():
            if k.startswith('i_'):
                nd.inputs[k[2:].replace('_', ' ')].default_value = v
            else:
                setattr(nd, k, v)
        return nd

    def link(self, a, b):
        self.l.new(a, b)


def new_mat(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    MAT[name] = m
    return m, NB(m)


def plain(name, col, rough=0.6, metal=0.0, emit=0.0, sheen=0.0, spec=0.5):
    if name in MAT:
        return MAT[name]
    m, b = new_mat(name)
    b.bsdf.inputs['Base Color'].default_value = hexlin(col)
    b.bsdf.inputs['Roughness'].default_value = rough
    b.bsdf.inputs['Metallic'].default_value = metal
    if emit:
        b.bsdf.inputs['Emission Color'].default_value = hexlin(col)
        b.bsdf.inputs['Emission Strength'].default_value = emit
    if sheen:
        b.bsdf.inputs['Sheen Weight'].default_value = sheen
    return m


def _coords(b, scale):
    tc = b.node('ShaderNodeTexCoord')
    mp = b.node('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = scale
    b.link(tc.outputs['Object'], mp.inputs['Vector'])
    return mp


def _grime(b, col_socket, amount=0.25, scale=3.0):
    nz = b.node('ShaderNodeTexNoise', i_Scale=scale, i_Detail=6.0)
    ramp = b.node('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position = 0.35; ramp.color_ramp.elements[0].color = (0, 0, 0, 1)
    ramp.color_ramp.elements[1].position = 0.75; ramp.color_ramp.elements[1].color = (1, 1, 1, 1)
    b.link(nz.outputs['Fac'], ramp.inputs['Fac'])
    mix = b.node('ShaderNodeMix', data_type='RGBA', blend_type='MULTIPLY')
    mix.inputs['Factor'].default_value = amount
    b.link(col_socket, mix.inputs[6])
    b.link(ramp.outputs['Color'], mix.inputs[7])
    return mix.outputs[2]


def brick(name, c1, c2, mortar, scale=(1, 1, 1), bw=0.24, rh=0.075, mortar_size=0.012, rough=0.8, bump=0.25, grime=0.3, axis='XZ'):
    """Baksteen/natuursteen/dakpan met reliëf. bw/rh: steenbreedte/rijhoogte (m)."""
    if name in MAT:
        return MAT[name]
    m, b = new_mat(name)
    tc = b.node('ShaderNodeTexCoord')
    sep = b.node('ShaderNodeSeparateXYZ'); b.link(tc.outputs['Object'], sep.inputs[0])
    cmb = b.node('ShaderNodeCombineXYZ')
    # gevelvlak = x/z (of y/z voor zijgevels); brick-node werkt in x/y
    first = {'XZ': 'X', 'YZ': 'Y', 'XY': 'X'}[axis]
    second = {'XZ': 'Z', 'YZ': 'Z', 'XY': 'Y'}[axis]
    b.link(sep.outputs[first], cmb.inputs['X'])
    b.link(sep.outputs[second], cmb.inputs['Y'])
    br = b.node('ShaderNodeTexBrick')
    br.inputs['Color1'].default_value = hexlin(c1)
    br.inputs['Color2'].default_value = hexlin(c2)
    br.inputs['Mortar'].default_value = hexlin(mortar)
    br.inputs['Scale'].default_value = 1.0
    br.inputs['Mortar Size'].default_value = mortar_size
    br.inputs['Mortar Smooth'].default_value = 0.3
    br.inputs['Brick Width'].default_value = bw
    br.inputs['Row Height'].default_value = rh
    br.offset = 0.5
    b.link(cmb.outputs[0], br.inputs['Vector'])
    col = _grime(b, br.outputs['Color'], grime, 2.5)
    b.link(col, b.bsdf.inputs['Base Color'])
    b.bsdf.inputs['Roughness'].default_value = rough
    bp = b.node('ShaderNodeBump', i_Strength=bump, i_Distance=0.02)
    b.link(br.outputs['Fac'], bp.inputs['Height'])
    nz = b.node('ShaderNodeTexNoise', i_Scale=40.0, i_Detail=4.0)
    b.link(cmb.outputs[0], nz.inputs['Vector'])
    bp2 = b.node('ShaderNodeBump', i_Strength=0.12, i_Distance=0.01)
    b.link(nz.outputs['Fac'], bp2.inputs['Height'])
    b.link(bp2.outputs['Normal'], bp.inputs['Normal'])
    b.link(bp.outputs['Normal'], b.bsdf.inputs['Normal'])
    return m


def tiles(name, c1, c2, scale=1.0, tw=0.26, th=0.17, rough=0.5, axis='XY'):
    """Dakpannen: rijen met bolle onderrand (wave) — op het dakvlak (object-xy na draaiing)."""
    if name in MAT:
        return MAT[name]
    m, b = new_mat(name)
    tc = b.node('ShaderNodeTexCoord')
    sep = b.node('ShaderNodeSeparateXYZ'); b.link(tc.outputs['UV'], sep.inputs[0])
    cmb = b.node('ShaderNodeCombineXYZ')
    b.link(sep.outputs['X'], cmb.inputs['X']); b.link(sep.outputs['Y'], cmb.inputs['Y'])
    br = b.node('ShaderNodeTexBrick')
    br.inputs['Color1'].default_value = hexlin(c1)
    br.inputs['Color2'].default_value = hexlin(c2)
    br.inputs['Mortar'].default_value = hexlin('#140506')
    br.inputs['Scale'].default_value = 1.0
    br.inputs['Mortar Size'].default_value = 0.012
    br.inputs['Brick Width'].default_value = tw
    br.inputs['Row Height'].default_value = th
    br.offset = 0.5
    b.link(cmb.outputs[0], br.inputs['Vector'])
    # bolling per pan: sinus over de breedte + aflopen per rij
    wv = b.node('ShaderNodeTexWave', wave_type='BANDS', bands_direction='X', i_Scale=1.0 / tw * 0.5 / 3.14159 * 6.2832 / 2)
    wv.inputs['Scale'].default_value = 1.0
    mpx = b.node('ShaderNodeMath', operation='MULTIPLY'); mpx.inputs[1].default_value = TAU / tw
    b.link(sep.outputs['X'], mpx.inputs[0])
    sn = b.node('ShaderNodeMath', operation='COSINE'); b.link(mpx.outputs[0], sn.inputs[0])
    mpy = b.node('ShaderNodeMath', operation='MULTIPLY'); mpy.inputs[1].default_value = 1.0 / th
    b.link(sep.outputs['Y'], mpy.inputs[0])
    fr = b.node('ShaderNodeMath', operation='FRACT'); b.link(mpy.outputs[0], fr.inputs[0])
    add = b.node('ShaderNodeMath', operation='ADD'); b.link(sn.outputs[0], add.inputs[0])
    fm = b.node('ShaderNodeMath', operation='MULTIPLY'); fm.inputs[1].default_value = -1.6; b.link(fr.outputs[0], fm.inputs[0])   # dikke rand onderaan elke pan
    b.link(fm.outputs[0], add.inputs[1])
    # kleur per pan + lichte onderrand (bolling vangt licht)
    wn = b.node('ShaderNodeTexWhiteNoise'); wn.noise_dimensions = '2D'
    fl_x = b.node('ShaderNodeMath', operation='FLOOR'); fl_y = b.node('ShaderNodeMath', operation='FLOOR')
    dx_ = b.node('ShaderNodeMath', operation='DIVIDE'); dx_.inputs[1].default_value = tw
    dy_ = b.node('ShaderNodeMath', operation='DIVIDE'); dy_.inputs[1].default_value = th
    b.link(sep.outputs['X'], dx_.inputs[0]); b.link(sep.outputs['Y'], dy_.inputs[0])
    b.link(dx_.outputs[0], fl_x.inputs[0]); b.link(dy_.outputs[0], fl_y.inputs[0])
    cw = b.node('ShaderNodeCombineXYZ'); b.link(fl_x.outputs[0], cw.inputs['X']); b.link(fl_y.outputs[0], cw.inputs['Y'])
    b.link(cw.outputs[0], wn.inputs['Vector'])
    tint = b.node('ShaderNodeMix', data_type='RGBA', blend_type='MULTIPLY'); tint.inputs['Factor'].default_value = 0.35
    b.link(br.outputs['Color'], tint.inputs[6])
    tr_ = b.node('ShaderNodeMapRange'); tr_.inputs['To Min'].default_value = 0.65; tr_.inputs['To Max'].default_value = 1.25
    b.link(wn.outputs['Value'], tr_.inputs['Value'])
    tcol = b.node('ShaderNodeCombineColor'); b.link(tr_.outputs['Result'], tcol.inputs[0]); b.link(tr_.outputs['Result'], tcol.inputs[1]); b.link(tr_.outputs['Result'], tcol.inputs[2])
    b.link(tcol.outputs[0], tint.inputs[7])
    lip = b.node('ShaderNodeMapRange'); lip.inputs['From Min'].default_value = 0.3; lip.inputs['From Max'].default_value = 0.02
    lip.inputs['To Min'].default_value = 0.0; lip.inputs['To Max'].default_value = 0.35
    b.link(fr.outputs[0], lip.inputs['Value'])
    lipc = b.node('ShaderNodeMix', data_type='RGBA', blend_type='SCREEN')
    b.link(lip.outputs['Result'], lipc.inputs['Factor']); b.link(tint.outputs[2], lipc.inputs[6]); lipc.inputs[7].default_value = hexlin('#e09070')
    shd = b.node('ShaderNodeMapRange'); shd.inputs['From Min'].default_value = 0.7; shd.inputs['From Max'].default_value = 1.0
    shd.inputs['To Min'].default_value = 0.0; shd.inputs['To Max'].default_value = 0.7
    b.link(fr.outputs[0], shd.inputs['Value'])
    shc = b.node('ShaderNodeMix', data_type='RGBA')
    b.link(shd.outputs['Result'], shc.inputs['Factor']); b.link(lipc.outputs[2], shc.inputs[6]); shc.inputs[7].default_value = hexlin('#1e080a')
    col = _grime(b, shc.outputs[2], 0.3, 1.5)
    b.link(col, b.bsdf.inputs['Base Color'])
    b.bsdf.inputs['Roughness'].default_value = rough
    bp = b.node('ShaderNodeBump', i_Strength=1.0, i_Distance=0.08)
    mx = b.node('ShaderNodeMath', operation='MULTIPLY'); mx.inputs[1].default_value = 0.5
    b.link(add.outputs[0], mx.inputs[0])
    add2 = b.node('ShaderNodeMath', operation='ADD'); b.link(mx.outputs[0], add2.inputs[0]); b.link(br.outputs['Fac'], add2.inputs[1])
    b.link(add2.outputs[0], bp.inputs['Height'])
    b.link(bp.outputs['Normal'], b.bsdf.inputs['Normal'])
    return m


def cobbles(name):
    """Natte kinderkopjes: voronoi-cellen, donkere voegen, glans in de kuiltjes."""
    if name in MAT:
        return MAT[name]
    m, b = new_mat(name)
    tc = b.node('ShaderNodeTexCoord')
    mp = b.node('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (4.0, 5.8, 1)   # stenen iets breder dan diep
    b.link(tc.outputs['Object'], mp.inputs['Vector'])
    vo = b.node('ShaderNodeTexVoronoi', feature='DISTANCE_TO_EDGE')
    vo.inputs['Scale'].default_value = 1.0; vo.inputs['Randomness'].default_value = 0.55
    b.link(mp.outputs[0], vo.inputs['Vector'])
    vc = b.node('ShaderNodeTexVoronoi', feature='F1')
    vc.inputs['Scale'].default_value = 1.0; vc.inputs['Randomness'].default_value = 0.55
    b.link(mp.outputs[0], vc.inputs['Vector'])
    # bolling: afstand tot rand → hoogte
    rp = b.node('ShaderNodeValToRGB')
    rp.color_ramp.elements[0].position = 0.0; rp.color_ramp.elements[0].color = (0, 0, 0, 1)
    rp.color_ramp.elements[1].position = 0.18; rp.color_ramp.elements[1].color = (1, 1, 1, 1)
    rp.color_ramp.interpolation = 'EASE'
    b.link(vo.outputs['Distance'], rp.inputs['Fac'])
    # kleur per steen
    cr = b.node('ShaderNodeValToRGB')
    cr.color_ramp.elements[0].position = 0.0; cr.color_ramp.elements[0].color = hexlin('#5a4654')
    cr.color_ramp.elements[1].position = 1.0; cr.color_ramp.elements[1].color = hexlin('#a8909a')
    e = cr.color_ramp.elements.new(0.55); e.color = hexlin('#7e6672')
    sepc = b.node('ShaderNodeSeparateColor'); b.link(vc.outputs['Color'], sepc.inputs[0])
    b.link(sepc.outputs[0], cr.inputs['Fac'])
    joint = b.node('ShaderNodeMix', data_type='RGBA', blend_type='MIX')
    b.link(rp.outputs['Color'], joint.inputs['Factor'])
    joint.inputs[6].default_value = hexlin('#1e141c')
    b.link(cr.outputs['Color'], joint.inputs[7])
    col = _grime(b, joint.outputs[2], 0.3, 0.8)
    b.link(col, b.bsdf.inputs['Base Color'])
    # nat: glanzend, plassen ruwer/gladder via ruis
    nz = b.node('ShaderNodeTexNoise', i_Scale=0.35, i_Detail=3.0)
    b.link(tc.outputs['Object'], nz.inputs['Vector'])
    rr = b.node('ShaderNodeMapRange')
    rr.inputs['From Min'].default_value = 0.4; rr.inputs['From Max'].default_value = 0.65
    rr.inputs['To Min'].default_value = 0.55; rr.inputs['To Max'].default_value = 0.2
    b.link(nz.outputs['Fac'], rr.inputs['Value'])
    b.link(rr.outputs['Result'], b.bsdf.inputs['Roughness'])
    bp = b.node('ShaderNodeBump', i_Strength=1.0, i_Distance=0.08)
    b.link(rp.outputs['Color'], bp.inputs['Height'])
    b.link(bp.outputs['Normal'], b.bsdf.inputs['Normal'])
    return m


def window_glass(name, warm='#f58a22', core='#ffd890', strength=2.1, shop=False):
    """Verlicht raam: warme kern die naar de randen afloopt (gordijnen/kamerdiepte)."""
    if name in MAT:
        return MAT[name]
    m, b = new_mat(name)
    b.n.remove(b.bsdf)
    tc = b.node('ShaderNodeTexCoord')
    gr = b.node('ShaderNodeTexGradient', gradient_type='SPHERICAL')
    mp = b.node('ShaderNodeMapping')
    mp.inputs['Location'].default_value = (0.5, 0.42, 0)
    mp.inputs['Scale'].default_value = (1.6, 1.25, 1)
    # gradient spherical heeft middelpunt in 0; UV loopt 0..1 → verschuif
    sub = b.node('ShaderNodeVectorMath', operation='SUBTRACT'); sub.inputs[1].default_value = (0.5, 0.42, 0)
    b.link(tc.outputs['UV'], sub.inputs[0])
    sc = b.node('ShaderNodeVectorMath', operation='MULTIPLY'); sc.inputs[1].default_value = (1.7, 1.3, 1)
    b.link(sub.outputs[0], sc.inputs[0])
    b.link(sc.outputs[0], gr.inputs['Vector'])
    ramp = b.node('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position = 0.0; ramp.color_ramp.elements[0].color = hexlin('#8a3410')
    ramp.color_ramp.elements[1].position = 0.85; ramp.color_ramp.elements[1].color = hexlin(core)
    e = ramp.color_ramp.elements.new(0.45); e.color = hexlin(warm)
    b.link(gr.outputs['Fac'], ramp.inputs['Fac'])
    # gordijnen aan de zijkanten en een valletje bovenin
    sepu = b.node('ShaderNodeSeparateXYZ'); b.link(tc.outputs['UV'], sepu.inputs[0])
    ml = b.node('ShaderNodeMapRange'); ml.inputs['From Min'].default_value = 0.06; ml.inputs['From Max'].default_value = 0.2
    b.link(sepu.outputs['X'], ml.inputs['Value'])
    mr = b.node('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = 0.94; mr.inputs['From Max'].default_value = 0.8
    b.link(sepu.outputs['X'], mr.inputs['Value'])
    mt = b.node('ShaderNodeMapRange'); mt.inputs['From Min'].default_value = 0.97; mt.inputs['From Max'].default_value = 0.88
    b.link(sepu.outputs['Y'], mt.inputs['Value'])
    m1 = b.node('ShaderNodeMath', operation='MULTIPLY'); b.link(ml.outputs['Result'], m1.inputs[0]); b.link(mr.outputs['Result'], m1.inputs[1])
    m2 = b.node('ShaderNodeMath', operation='MULTIPLY'); b.link(m1.outputs[0], m2.inputs[0]); b.link(mt.outputs['Result'], m2.inputs[1])
    cur = b.node('ShaderNodeMix', data_type='RGBA')
    b.link(m2.outputs[0], cur.inputs['Factor'])
    cur.inputs[6].default_value = hexlin('#5a1a0c'); b.link(ramp.outputs['Color'], cur.inputs[7])
    out_col = cur.outputs[2]
    if shop:
        # etalage: planken (donkere banden) met daarboven pakjes in allerlei kleuren
        fy = b.node('ShaderNodeMath', operation='MULTIPLY'); fy.inputs[1].default_value = 3.4
        b.link(sepu.outputs['Y'], fy.inputs[0])
        fr = b.node('ShaderNodeMath', operation='FRACT'); b.link(fy.outputs[0], fr.inputs[0])
        shelf = b.node('ShaderNodeMath', operation='LESS_THAN'); shelf.inputs[1].default_value = 0.07
        b.link(fr.outputs[0], shelf.inputs[0])
        low = b.node('ShaderNodeMath', operation='LESS_THAN'); low.inputs[1].default_value = 0.72
        b.link(sepu.outputs['Y'], low.inputs[0])
        sh2 = b.node('ShaderNodeMath', operation='MULTIPLY'); b.link(shelf.outputs[0], sh2.inputs[0]); b.link(low.outputs[0], sh2.inputs[1])
        # pakjes: voronoi-cellen in een band vlak boven elke plank
        gv = b.node('ShaderNodeCombineXYZ')
        gx = b.node('ShaderNodeMath', operation='MULTIPLY'); gx.inputs[1].default_value = 9.0
        b.link(sepu.outputs['X'], gx.inputs[0]); b.link(gx.outputs[0], gv.inputs['X']); b.link(fy.outputs[0], gv.inputs['Y'])
        vo = b.node('ShaderNodeTexVoronoi', feature='F1'); vo.inputs['Scale'].default_value = 1.0
        b.link(gv.outputs[0], vo.inputs['Vector'])
        band = b.node('ShaderNodeMapRange'); band.inputs['From Min'].default_value = 0.07; band.inputs['From Max'].default_value = 0.4
        band.inputs['To Min'].default_value = 1.0; band.inputs['To Max'].default_value = 0.0
        band.clamp = True
        b.link(fr.outputs[0], band.inputs['Value'])
        cut = b.node('ShaderNodeMath', operation='GREATER_THAN'); cut.inputs[1].default_value = 0.35
        b.link(band.outputs['Result'], cut.inputs[0])
        sepv = b.node('ShaderNodeSeparateColor'); b.link(vo.outputs['Color'], sepv.inputs[0])
        pres = b.node('ShaderNodeMath', operation='GREATER_THAN'); pres.inputs[1].default_value = 0.3
        b.link(sepv.outputs[1], pres.inputs[0])
        gm = b.node('ShaderNodeMath', operation='MULTIPLY'); b.link(cut.outputs[0], gm.inputs[0]); b.link(pres.outputs[0], gm.inputs[1])
        gm2 = b.node('ShaderNodeMath', operation='MULTIPLY'); b.link(gm.outputs[0], gm2.inputs[0]); b.link(low.outputs[0], gm2.inputs[1])
        gcol = b.node('ShaderNodeValToRGB')
        cr_ = gcol.color_ramp
        cr_.elements[0].position = 0.0; cr_.elements[0].color = hexlin('#c41e22')
        cr_.elements[1].position = 1.0; cr_.elements[1].color = hexlin('#e8a020')
        for pos, c in ((0.3, '#2a7a3a'), (0.55, '#d84a8a'), (0.8, '#f4d050')):
            e2 = cr_.elements.new(pos); e2.color = hexlin(c)
        cr_.interpolation = 'CONSTANT'
        b.link(sepv.outputs[0], gcol.inputs['Fac'])
        mg = b.node('ShaderNodeMix', data_type='RGBA')
        b.link(gm2.outputs[0], mg.inputs['Factor']); b.link(out_col, mg.inputs[6]); b.link(gcol.outputs['Color'], mg.inputs[7])
        ms = b.node('ShaderNodeMix', data_type='RGBA')
        b.link(sh2.outputs[0], ms.inputs['Factor']); b.link(mg.outputs[2], ms.inputs[6]); ms.inputs[7].default_value = hexlin('#3a1808')
        out_col = ms.outputs[2]
    em = b.node('ShaderNodeEmission', i_Strength=strength)
    b.link(out_col, em.inputs['Color'])
    b.link(em.outputs[0], b.out.inputs['Surface'])
    return m


def stonewall(name, c1, c2, mortar, sx=0.36, sz=0.2, rough=0.8, bump=0.6, axis='XZ'):
    """Onregelmatig metselwerk van natuursteen: voronoi-cellen, kleur per steen."""
    if name in MAT:
        return MAT[name]
    m, b = new_mat(name)
    tc = b.node('ShaderNodeTexCoord')
    sep = b.node('ShaderNodeSeparateXYZ'); b.link(tc.outputs['Object'], sep.inputs[0])
    cmb = b.node('ShaderNodeCombineXYZ')
    first = {'XZ': 'X', 'YZ': 'Y'}[axis]
    mx = b.node('ShaderNodeMath', operation='MULTIPLY'); mx.inputs[1].default_value = 1.0 / sx
    b.link(sep.outputs[first], mx.inputs[0]); b.link(mx.outputs[0], cmb.inputs['X'])
    mz = b.node('ShaderNodeMath', operation='MULTIPLY'); mz.inputs[1].default_value = 1.0 / sz
    b.link(sep.outputs['Z'], mz.inputs[0]); b.link(mz.outputs[0], cmb.inputs['Y'])
    ve = b.node('ShaderNodeTexVoronoi', feature='DISTANCE_TO_EDGE'); ve.inputs['Randomness'].default_value = 0.7
    vc = b.node('ShaderNodeTexVoronoi', feature='F1'); vc.inputs['Randomness'].default_value = 0.7
    b.link(cmb.outputs[0], ve.inputs['Vector']); b.link(cmb.outputs[0], vc.inputs['Vector'])
    edge = b.node('ShaderNodeValToRGB')
    edge.color_ramp.elements[0].position = 0.0; edge.color_ramp.elements[0].color = (0, 0, 0, 1)
    edge.color_ramp.elements[1].position = 0.06; edge.color_ramp.elements[1].color = (1, 1, 1, 1)
    edge.color_ramp.interpolation = 'EASE'
    b.link(ve.outputs['Distance'], edge.inputs['Fac'])
    sc = b.node('ShaderNodeSeparateColor'); b.link(vc.outputs['Color'], sc.inputs[0])
    cr = b.node('ShaderNodeValToRGB')
    cr.color_ramp.elements[0].color = hexlin(c2); cr.color_ramp.elements[1].color = hexlin(c1)
    e = cr.color_ramp.elements.new(0.5); e.color = hexlin(c1)
    b.link(sc.outputs[0], cr.inputs['Fac'])
    mix = b.node('ShaderNodeMix', data_type='RGBA')
    b.link(edge.outputs['Color'], mix.inputs['Factor'])
    mix.inputs[6].default_value = hexlin(mortar); b.link(cr.outputs['Color'], mix.inputs[7])
    col = _grime(b, mix.outputs[2], 0.4, 1.8)
    b.link(col, b.bsdf.inputs['Base Color'])
    b.bsdf.inputs['Roughness'].default_value = rough
    nz = b.node('ShaderNodeTexNoise', i_Scale=6.0, i_Detail=8.0); b.link(cmb.outputs[0], nz.inputs['Vector'])
    add = b.node('ShaderNodeMath', operation='MULTIPLY_ADD'); add.inputs[1].default_value = 0.12
    b.link(nz.outputs['Fac'], add.inputs[0]); b.link(edge.outputs['Color'], add.inputs[2])
    bp = b.node('ShaderNodeBump', i_Strength=bump, i_Distance=0.03)
    b.link(add.outputs[0], bp.inputs['Height']); b.link(bp.outputs['Normal'], b.bsdf.inputs['Normal'])
    return m


def cobble_inst(name):
    """Materiaal voor losse keien (geometry-nodes-instanties): kleur per steen via Object Info."""
    if name in MAT:
        return MAT[name]
    m, b = new_mat(name)
    oi = b.node('ShaderNodeObjectInfo')
    cr = b.node('ShaderNodeValToRGB')
    cr.color_ramp.elements[0].color = hexlin('#4e3c4a'); cr.color_ramp.elements[1].color = hexlin('#a08a96')
    e = cr.color_ramp.elements.new(0.5); e.color = hexlin('#76606c')
    b.link(oi.outputs['Random'], cr.inputs['Fac'])
    col = _grime(b, cr.outputs['Color'], 0.3, 18.0)
    b.link(col, b.bsdf.inputs['Base Color'])
    tc = b.node('ShaderNodeTexCoord')
    nz = b.node('ShaderNodeTexNoise', i_Scale=0.25, i_Detail=2.0); b.link(tc.outputs['Generated'], nz.inputs['Vector'])
    rr = b.node('ShaderNodeMapRange')
    b.link(oi.outputs['Random'], rr.inputs['Value'])
    rr.inputs['To Min'].default_value = 0.16; rr.inputs['To Max'].default_value = 0.42
    b.link(rr.outputs['Result'], b.bsdf.inputs['Roughness'])
    n2 = b.node('ShaderNodeTexNoise', i_Scale=40.0, i_Detail=6.0); b.link(tc.outputs['Object'], n2.inputs['Vector'])
    bp = b.node('ShaderNodeBump', i_Strength=0.35, i_Distance=0.01)
    b.link(n2.outputs['Fac'], bp.inputs['Height']); b.link(bp.outputs['Normal'], b.bsdf.inputs['Normal'])
    return m


def bark(name):
    if name in MAT:
        return MAT[name]
    m, b = new_mat(name)
    tc = b.node('ShaderNodeTexCoord')
    mp = b.node('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (9, 9, 1.6)
    b.link(tc.outputs['Object'], mp.inputs['Vector'])
    nz = b.node('ShaderNodeTexNoise', i_Scale=2.5, i_Detail=10.0, i_Roughness=0.65)
    b.link(mp.outputs[0], nz.inputs['Vector'])
    vo = b.node('ShaderNodeTexVoronoi', feature='DISTANCE_TO_EDGE'); vo.inputs['Scale'].default_value = 3.0
    b.link(mp.outputs[0], vo.inputs['Vector'])
    mx = b.node('ShaderNodeMath', operation='MULTIPLY'); b.link(nz.outputs['Fac'], mx.inputs[0]); b.link(vo.outputs['Distance'], mx.inputs[1])
    cr = b.node('ShaderNodeValToRGB')
    cr.color_ramp.elements[0].position = 0.0; cr.color_ramp.elements[0].color = hexlin('#0e0804')
    cr.color_ramp.elements[1].position = 0.25; cr.color_ramp.elements[1].color = hexlin('#5a3a24')
    e = cr.color_ramp.elements.new(0.1); e.color = hexlin('#2a1a10')
    b.link(mx.outputs[0], cr.inputs['Fac'])
    b.link(cr.outputs['Color'], b.bsdf.inputs['Base Color'])
    b.bsdf.inputs['Roughness'].default_value = 0.85
    bp = b.node('ShaderNodeBump', i_Strength=1.0, i_Distance=0.04)
    b.link(mx.outputs[0], bp.inputs['Height']); b.link(bp.outputs['Normal'], b.bsdf.inputs['Normal'])
    return m


def wood(name, c1='#7a4422', c2='#4a2410', scale=6.0, rough=0.6):
    if name in MAT:
        return MAT[name]
    m, b = new_mat(name)
    tc = b.node('ShaderNodeTexCoord')
    wv = b.node('ShaderNodeTexWave', wave_type='BANDS', bands_direction='Z')
    wv.inputs['Scale'].default_value = scale; wv.inputs['Distortion'].default_value = 6.0; wv.inputs['Detail'].default_value = 4.0
    b.link(tc.outputs['Object'], wv.inputs['Vector'])
    rp = b.node('ShaderNodeValToRGB')
    rp.color_ramp.elements[0].color = hexlin(c2); rp.color_ramp.elements[1].color = hexlin(c1)
    b.link(wv.outputs['Fac'], rp.inputs['Fac'])
    b.link(rp.outputs['Color'], b.bsdf.inputs['Base Color'])
    b.bsdf.inputs['Roughness'].default_value = rough
    bp = b.node('ShaderNodeBump', i_Strength=0.2)
    b.link(wv.outputs['Fac'], bp.inputs['Height'])
    b.link(bp.outputs['Normal'], b.bsdf.inputs['Normal'])
    return m


def plaster(name, col, rough=0.85):
    """Glad pleisterwerk met zachte vlekken."""
    if name in MAT:
        return MAT[name]
    m, b = new_mat(name)
    tc = b.node('ShaderNodeTexCoord')
    nz = b.node('ShaderNodeTexNoise', i_Scale=1.6, i_Detail=6.0); b.link(tc.outputs['Object'], nz.inputs['Vector'])
    cr = b.node('ShaderNodeValToRGB')
    cr.color_ramp.elements[0].color = hexlin(col)
    h = col.lstrip('#'); dk = '#%02x%02x%02x' % tuple(int(int(h[i:i + 2], 16) * 0.82) for i in (0, 2, 4))
    cr.color_ramp.elements[1].color = hexlin(dk)
    b.link(nz.outputs['Fac'], cr.inputs['Fac'])
    col_ = _grime(b, cr.outputs['Color'], 0.25, 2.0)
    b.link(col_, b.bsdf.inputs['Base Color'])
    b.bsdf.inputs['Roughness'].default_value = rough
    n2 = b.node('ShaderNodeTexNoise', i_Scale=60.0, i_Detail=4.0); b.link(tc.outputs['Object'], n2.inputs['Vector'])
    bp = b.node('ShaderNodeBump', i_Strength=0.15, i_Distance=0.01)
    b.link(n2.outputs['Fac'], bp.inputs['Height']); b.link(bp.outputs['Normal'], b.bsdf.inputs['Normal'])
    return m


def planks(name, c1='#8a5228', c2='#5a3016', board=0.12, rough=0.65):
    """Verticale planken (toonbank, tafel, kar) met nerf."""
    if name in MAT:
        return MAT[name]
    m, b = new_mat(name)
    tc = b.node('ShaderNodeTexCoord')
    sep = b.node('ShaderNodeSeparateXYZ'); b.link(tc.outputs['Object'], sep.inputs[0])
    ad = b.node('ShaderNodeMath', operation='ADD'); b.link(sep.outputs['X'], ad.inputs[0]); b.link(sep.outputs['Y'], ad.inputs[1])
    cmb = b.node('ShaderNodeCombineXYZ'); b.link(ad.outputs[0], cmb.inputs['X']); b.link(sep.outputs['Z'], cmb.inputs['Y'])
    br = b.node('ShaderNodeTexBrick')
    br.inputs['Color1'].default_value = hexlin(c1); br.inputs['Color2'].default_value = hexlin(c2)
    br.inputs['Mortar'].default_value = hexlin('#1e0e06'); br.inputs['Scale'].default_value = 1.0
    br.inputs['Mortar Size'].default_value = 0.006; br.inputs['Brick Width'].default_value = board; br.inputs['Row Height'].default_value = 3.0
    b.link(cmb.outputs[0], br.inputs['Vector'])
    mp = b.node('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (40, 2, 2)
    b.link(cmb.outputs[0], mp.inputs['Vector'])
    nz = b.node('ShaderNodeTexNoise', i_Scale=3.0, i_Detail=8.0); b.link(mp.outputs[0], nz.inputs['Vector'])
    mx = b.node('ShaderNodeMix', data_type='RGBA', blend_type='MULTIPLY'); mx.inputs['Factor'].default_value = 0.45
    b.link(br.outputs['Color'], mx.inputs[6]); b.link(nz.outputs['Color'], mx.inputs[7])
    b.link(mx.outputs[2], b.bsdf.inputs['Base Color'])
    b.bsdf.inputs['Roughness'].default_value = rough
    bp = b.node('ShaderNodeBump', i_Strength=0.35, i_Distance=0.01)
    b.link(br.outputs['Fac'], bp.inputs['Height']); b.link(bp.outputs['Normal'], b.bsdf.inputs['Normal'])
    return m


def barrel_wood(name, c1='#9a5c2c', c2='#6a3818', staves=16):
    """Verticale duigen rond een ton: hoek rond het midden (Generated-coördinaten)."""
    if name in MAT:
        return MAT[name]
    m, b = new_mat(name)
    tc = b.node('ShaderNodeTexCoord')
    sep = b.node('ShaderNodeSeparateXYZ'); b.link(tc.outputs['Generated'], sep.inputs[0])
    sx = b.node('ShaderNodeMath', operation='SUBTRACT'); sx.inputs[1].default_value = 0.5; b.link(sep.outputs['X'], sx.inputs[0])
    sy = b.node('ShaderNodeMath', operation='SUBTRACT'); sy.inputs[1].default_value = 0.5; b.link(sep.outputs['Y'], sy.inputs[0])
    at = b.node('ShaderNodeMath', operation='ARCTAN2'); b.link(sy.outputs[0], at.inputs[0]); b.link(sx.outputs[0], at.inputs[1])
    sc = b.node('ShaderNodeMath', operation='MULTIPLY'); sc.inputs[1].default_value = staves / TAU; b.link(at.outputs[0], sc.inputs[0])
    fr = b.node('ShaderNodeMath', operation='FRACT'); b.link(sc.outputs[0], fr.inputs[0])
    fl = b.node('ShaderNodeMath', operation='FLOOR'); b.link(sc.outputs[0], fl.inputs[0])
    wn = b.node('ShaderNodeTexWhiteNoise'); wn.noise_dimensions = '1D'; b.link(fl.outputs[0], wn.inputs['W'])
    cr = b.node('ShaderNodeValToRGB'); cr.color_ramp.elements[0].color = hexlin(c2); cr.color_ramp.elements[1].color = hexlin(c1)
    b.link(wn.outputs['Value'], cr.inputs['Fac'])
    edge = b.node('ShaderNodeMapRange'); edge.inputs['From Min'].default_value = 0.0; edge.inputs['From Max'].default_value = 0.06
    b.link(fr.outputs[0], edge.inputs['Value'])
    cmb = b.node('ShaderNodeCombineXYZ'); b.link(sc.outputs[0], cmb.inputs['X']); b.link(sep.outputs['Z'], cmb.inputs['Y'])
    mp = b.node('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (6, 1.2, 1)
    b.link(cmb.outputs[0], mp.inputs['Vector'])
    nz = b.node('ShaderNodeTexNoise', i_Scale=4.0, i_Detail=8.0); b.link(mp.outputs[0], nz.inputs['Vector'])
    gr = b.node('ShaderNodeMix', data_type='RGBA', blend_type='MULTIPLY'); gr.inputs['Factor'].default_value = 0.4
    b.link(cr.outputs['Color'], gr.inputs[6]); b.link(nz.outputs['Color'], gr.inputs[7])
    dk = b.node('ShaderNodeMix', data_type='RGBA')
    b.link(edge.outputs['Result'], dk.inputs['Factor']); dk.inputs[6].default_value = hexlin('#2a1408'); b.link(gr.outputs[2], dk.inputs[7])
    b.link(dk.outputs[2], b.bsdf.inputs['Base Color'])
    b.bsdf.inputs['Roughness'].default_value = 0.6
    bp = b.node('ShaderNodeBump', i_Strength=0.4, i_Distance=0.01)
    b.link(edge.outputs['Result'], bp.inputs['Height']); b.link(bp.outputs['Normal'], b.bsdf.inputs['Normal'])
    return m


def leaf_mat(name, col):
    """Herfstblad: deels doorschijnend, zodat het oplicht tegen het licht."""
    if name in MAT:
        return MAT[name]
    m, b = new_mat(name)
    b.bsdf.inputs['Base Color'].default_value = hexlin(col)
    b.bsdf.inputs['Roughness'].default_value = 0.55
    b.bsdf.inputs['Emission Color'].default_value = hexlin(col)
    b.bsdf.inputs['Emission Strength'].default_value = 0.35
    tr = b.node('ShaderNodeBsdfTranslucent')
    tr.inputs['Color'].default_value = hexlin(col)
    mx = b.node('ShaderNodeMixShader'); mx.inputs[0].default_value = 0.35
    b.link(b.bsdf.outputs[0], mx.inputs[1]); b.link(tr.outputs[0], mx.inputs[2])
    b.link(mx.outputs[0], b.out.inputs['Surface'])
    return m


def stripes(name, ca, cb, width=0.12, axis='X', rough=0.75, sheen=0.3):
    """Gestreept doek (luifel)."""
    if name in MAT:
        return MAT[name]
    m, b = new_mat(name)
    tc = b.node('ShaderNodeTexCoord')
    sep = b.node('ShaderNodeSeparateXYZ'); b.link(tc.outputs['UV'], sep.inputs[0])
    mul = b.node('ShaderNodeMath', operation='MULTIPLY'); mul.inputs[1].default_value = 1.0 / width
    b.link(sep.outputs['X' if axis == 'X' else 'Y'], mul.inputs[0])
    fr = b.node('ShaderNodeMath', operation='PINGPONG'); fr.inputs[1].default_value = 1.0
    b.link(mul.outputs[0], fr.inputs[0])
    gt = b.node('ShaderNodeMath', operation='GREATER_THAN'); gt.inputs[1].default_value = 0.5
    b.link(fr.outputs[0], gt.inputs[0])
    mx = b.node('ShaderNodeMix', data_type='RGBA')
    b.link(gt.outputs[0], mx.inputs['Factor'])
    mx.inputs[6].default_value = hexlin(ca); mx.inputs[7].default_value = hexlin(cb)
    b.link(mx.outputs[2], b.bsdf.inputs['Base Color'])
    b.bsdf.inputs['Roughness'].default_value = rough
    b.bsdf.inputs['Sheen Weight'].default_value = sheen
    return m


def emit(name, col, strength):
    if name in MAT:
        return MAT[name]
    m, b = new_mat(name)
    b.n.remove(b.bsdf)
    em = b.node('ShaderNodeEmission', i_Strength=strength)
    em.inputs['Color'].default_value = hexlin(col)
    b.link(em.outputs[0], b.out.inputs['Surface'])
    return m


def point_light(name, loc, col, power, radius=0.05, col_name='lights'):
    ld = bpy.data.lights.new(name, 'POINT')
    ld.color = hexlin(col)[:3]
    ld.energy = power
    ld.shadow_soft_size = radius
    lo = bpy.data.objects.new(name, ld)
    coll(col_name).objects.link(lo)
    lo.location = loc
    return lo

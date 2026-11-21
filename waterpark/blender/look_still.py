"""
Look-development: rendert een still van het waterpark in Blender/Cycles met realistische materialen.
De geometrie (incl. de stokpoppetjes in pose) komt uit de three.js-scène: window.__exportBar(bar, naam)
schrijft _snaps/<naam>.glb + <naam>.json (camera, zon, spetters).

  blender -b --python look_still.py -- --in ../_snaps/wp_intro --out ../_snaps/look_intro.png --res 1280x720 --samples 64

Poppetjes (materialen fig_*) blijven zoals ze zijn; al de rest krijgt een nieuw materiaal per soort.
"""
import bpy, bmesh, sys, os, json, math, argparse, time
from mathutils import Vector, Quaternion

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument('--in', dest='inp', required=True)          # pad zonder extensie
ap.add_argument('--out', required=True)
ap.add_argument('--res', default='1280x720')
ap.add_argument('--samples', type=int, default=64)
ap.add_argument('--exposure', type=float, default=0.0)
ap.add_argument('--sky', type=float, default=0.14)           # sterkte van de fysieke lucht
ap.add_argument('--save', default='')
ap.add_argument('--ladder', default='')                      # bv. c1,c2,c4,c8,c16,c32,e  (c<N> = Cycles N s, e = Eevee)
ap.add_argument('--denoise', default='HIGH')                 # HIGH | BALANCED | FAST
ap.add_argument('--esamples', type=int, default=32)
ap.add_argument('--device', default='cpu')                   # cpu | gpu (automatisch) | optix | cuda | hip | metal | oneapi
ap.add_argument('--tube', default='clear')                  # clear = helemaal doorzichtig (gekozen) | dome = dicht onder, glazen dak
args = ap.parse_args(argv)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
meta = json.load(open(args.inp + '.json'))


def t2b(v):            # three.js (y-up) -> Blender (z-up)
    return Vector((v[0], -v[2], v[1]))


def hexlin(h):
    h = h.lstrip('#'); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x / 12.92) if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4) for x in c) + (1.0,)


# ------------------------------------------------------------------ import
bpy.ops.import_scene.gltf(filepath=os.path.abspath(args.inp + '.glb'))
for ob in list(scene.objects):
    if ob.type in ('LIGHT', 'CAMERA'):
        bpy.data.objects.remove(ob, do_unlink=True)


# ------------------------------------------------------------------ node-hulpjes
class NT:
    def __init__(s, name):
        s.m = bpy.data.materials.new(name); s.m.use_nodes = True
        s.t = s.m.node_tree; s.n = s.t.nodes; s.l = s.t.links
        for x in list(s.n): s.n.remove(x)
        s.out = s.new('ShaderNodeOutputMaterial')

    def new(s, kind, **kw):
        nd = s.n.new(kind)
        for k, v in kw.items(): setattr(nd, k, v)
        return nd

    def link(s, a, b): s.l.new(a, b)

    def val(s, node, name, v):
        if name in node.inputs: node.inputs[name].default_value = v

    def pos(s, scale=1.0):
        g = s.new('ShaderNodeNewGeometry')
        if scale == 1.0: return g.outputs['Position']
        m = s.new('ShaderNodeVectorMath', operation='SCALE'); m.inputs['Scale'].default_value = scale
        s.link(g.outputs['Position'], m.inputs[0]); return m.outputs[0]

    def noise(s, vec, scale, detail=4.0, rough=.55, dist=0.0):
        nz = s.new('ShaderNodeTexNoise'); s.link(vec, nz.inputs['Vector'])
        nz.inputs['Scale'].default_value = scale; nz.inputs['Detail'].default_value = detail
        nz.inputs['Roughness'].default_value = rough; nz.inputs['Distortion'].default_value = dist
        return nz

    def ramp(s, fac, stops):
        r = s.new('ShaderNodeValToRGB'); s.link(fac, r.inputs['Fac'])
        el = r.color_ramp.elements
        el[0].position, el[0].color = stops[0][0], hexlin(stops[0][1])
        el[1].position, el[1].color = stops[-1][0], hexlin(stops[-1][1])
        for p, c in stops[1:-1]:
            e = el.new(p); e.color = hexlin(c)
        return r

    def bump(s, h, strength, dist=.1, normal=None):
        b = s.new('ShaderNodeBump'); s.link(h, b.inputs['Height'])
        b.inputs['Strength'].default_value = strength; b.inputs['Distance'].default_value = dist
        if normal is not None: s.link(normal, b.inputs['Normal'])
        return b

    def bsdf(s, color=None, rough=.5, **kw):
        b = s.new('ShaderNodeBsdfPrincipled')
        if isinstance(color, str): b.inputs['Base Color'].default_value = hexlin(color)
        elif color is not None: s.link(color, b.inputs['Base Color'])
        b.inputs['Roughness'].default_value = rough
        for k, v in kw.items(): s.val(b, k, v)
        return b

    def done(s, shader): s.link(shader.outputs[0], s.out.inputs['Surface']); return s.m


# ------------------------------------------------------------------ materialen
def m_paving():
    s = NT('L_paving')
    br = s.new('ShaderNodeTexBrick'); s.link(s.pos(1.0), br.inputs['Vector'])
    br.inputs['Scale'].default_value = 1.6; br.inputs['Mortar Size'].default_value = .012
    br.inputs['Brick Width'].default_value = .6; br.inputs['Row Height'].default_value = .3
    br.inputs['Color1'].default_value = hexlin('#bdb3a3'); br.inputs['Color2'].default_value = hexlin('#a89d8c')
    br.inputs['Mortar'].default_value = hexlin('#7d766c')
    nz = s.noise(s.pos(), 3, 6)
    mix = s.new('ShaderNodeMix', data_type='RGBA', blend_type='MULTIPLY'); mix.inputs['Factor'].default_value = .35
    s.link(br.outputs['Color'], mix.inputs[6]); s.link(nz.outputs['Color'], mix.inputs[7])
    b = s.bump(br.outputs['Fac'], .35, .05)
    sh = s.bsdf(mix.outputs[2], .78); s.link(b.outputs[0], sh.inputs['Normal'])
    return s.done(sh)


def m_grass():
    s = NT('L_grass')
    big = s.noise(s.pos(), .08, 3); fine = s.noise(s.pos(), 45, 2, .7)
    r = s.ramp(big.outputs['Fac'], [(.3, '#2c5a12'), (.55, '#3f7a1a'), (.75, '#5a8a24')])
    mix = s.new('ShaderNodeMix', data_type='RGBA', blend_type='MULTIPLY'); mix.inputs['Factor'].default_value = .35
    s.link(r.outputs['Color'], mix.inputs[6]); s.link(fine.outputs['Color'], mix.inputs[7])
    b = s.bump(fine.outputs['Fac'], .6, .05)
    sh = s.bsdf(mix.outputs[2], .95, **{'Specular IOR Level': .25}); s.link(b.outputs[0], sh.inputs['Normal'])
    return s.done(sh)


def m_concrete(name='L_concrete', base=('#8f8b84', '#a6a198', '#b8b3a8'), boards=True):
    s = NT(name)
    nz = s.noise(s.pos(), 1.2, 6); fine = s.noise(s.pos(), 30, 3)
    r = s.ramp(nz.outputs['Fac'], [(.3, base[0]), (.55, base[1]), (.8, base[2])])
    h = fine.outputs['Fac']
    if boards:   # bekistingsplanken: horizontale banden
        wv = s.new('ShaderNodeTexWave', wave_type='BANDS', bands_direction='Z'); s.link(s.pos(), wv.inputs['Vector'])
        wv.inputs['Scale'].default_value = .9; wv.inputs['Distortion'].default_value = .3
        mx = s.new('ShaderNodeMath', operation='ADD'); s.link(fine.outputs['Fac'], mx.inputs[0])
        sc = s.new('ShaderNodeMath', operation='MULTIPLY'); sc.inputs[1].default_value = .25
        s.link(wv.outputs['Fac'], sc.inputs[0]); s.link(sc.outputs[0], mx.inputs[1]); h = mx.outputs[0]
    b = s.bump(h, .25, .05)
    sh = s.bsdf(r.outputs['Color'], .88); s.link(b.outputs[0], sh.inputs['Normal'])
    return s.done(sh)


def m_stone_white():
    s = NT('L_coping'); nz = s.noise(s.pos(), 6, 5)
    r = s.ramp(nz.outputs['Fac'], [(.35, '#d9d4c8'), (.7, '#efebe2')])
    b = s.bump(nz.outputs['Fac'], .15, .03)
    sh = s.bsdf(r.outputs['Color'], .55); s.link(b.outputs[0], sh.inputs['Normal'])
    return s.done(sh)


def m_water():
    s = NT('L_water')
    p = s.pos()
    # cartoon-vrije caustics: voronoi-randen, licht vervormd
    dn = s.noise(p, .6, 3)
    add = s.new('ShaderNodeVectorMath', operation='ADD'); s.link(p, add.inputs[0]); s.link(dn.outputs['Color'], add.inputs[1])
    vo = s.new('ShaderNodeTexVoronoi', feature='DISTANCE_TO_EDGE'); s.link(add.outputs[0], vo.inputs['Vector'])
    vo.inputs['Scale'].default_value = .9
    cr = s.ramp(vo.outputs['Distance'], [(0.0, '#8fe8f4'), (.07, '#2fb8d0'), (.3, '#0b7f9e')])
    ripple = s.noise(p, 2.2, 4, .5, 1.5)
    b = s.bump(ripple.outputs['Fac'], .18, .1)
    sh = s.bsdf(cr.outputs['Color'], .02, **{'IOR': 1.33, 'Coat Weight': 1.0, 'Coat Roughness': .0, 'Specular IOR Level': .6})
    s.link(b.outputs[0], sh.inputs['Normal']); s.link(b.outputs[0], sh.inputs['Coat Normal'])
    return s.done(sh)


def m_clear_water(name='L_jetwater', tint='#e8fbff'):
    s = NT(name)
    sh = s.bsdf(tint, .04, **{'Transmission Weight': 1.0, 'IOR': 1.33})
    return s.done(sh)


def m_jet():          # fonteinstraal: wit-doorschijnend, schuimend, geen chroom
    s = NT('L_jet'); nz = s.noise(s.pos(), 6, 4, .6, 2)
    r = s.ramp(nz.outputs['Fac'], [(.35, '#cfefff'), (.65, '#ffffff')])
    sh = s.bsdf(r.outputs['Color'], .3, **{'Transmission Weight': .45, 'Subsurface Weight': .5, 'IOR': 1.33, 'Alpha': .85})
    return s.done(sh)


def m_foam():
    s = NT('L_foam'); nz = s.noise(s.pos(), 8, 4)
    sh = s.bsdf('#f4fbff', .5, **{'Subsurface Weight': .4, 'Transmission Weight': .3})
    return s.done(sh)


def m_fiberglass(name, color, trans=0.0):
    s = NT(name)
    nz = s.noise(s.pos(), 4, 3)
    b = s.bump(nz.outputs['Fac'], .02, .02)
    sh = s.bsdf(color, .3, **{'Coat Weight': 1.0, 'Coat Roughness': .03, 'Transmission Weight': trans, 'IOR': 1.5})
    s.link(b.outputs[0], sh.inputs['Normal'])
    m = s.done(sh)
    return m


def m_metal(name, color, rough):
    s = NT(name); nz = s.noise(s.pos(), 20, 4)
    rr = s.new('ShaderNodeMapRange'); s.link(nz.outputs['Fac'], rr.inputs['Value'])
    rr.inputs['To Min'].default_value = rough * .7; rr.inputs['To Max'].default_value = rough * 1.3
    sh = s.bsdf(color, rough, **{'Metallic': 1.0}); s.link(rr.outputs[0], sh.inputs['Roughness'])
    return s.done(sh)


def m_plastic(name, color):
    s = NT(name); sh = s.bsdf(color, .35, **{'Coat Weight': .6, 'Coat Roughness': .1}); return s.done(sh)


def m_wood(name, c1, c2):
    s = NT(name)
    wv = s.new('ShaderNodeTexWave', wave_type='RINGS'); s.link(s.pos(), wv.inputs['Vector'])
    wv.inputs['Scale'].default_value = 3; wv.inputs['Distortion'].default_value = 8; wv.inputs['Detail'].default_value = 4
    r = s.ramp(wv.outputs['Fac'], [(.2, c1), (.8, c2)])
    b = s.bump(wv.outputs['Fac'], .15, .03)
    sh = s.bsdf(r.outputs['Color'], .6); s.link(b.outputs[0], sh.inputs['Normal'])
    return s.done(sh)


def m_trunk():
    s = NT('L_trunk')
    wv = s.new('ShaderNodeTexWave', wave_type='BANDS', bands_direction='Z'); s.link(s.pos(), wv.inputs['Vector'])
    wv.inputs['Scale'].default_value = 6; wv.inputs['Distortion'].default_value = 2; wv.inputs['Detail'].default_value = 3
    r = s.ramp(wv.outputs['Fac'], [(.25, '#4a3524'), (.6, '#7a5c40'), (.85, '#9c8060')])
    b = s.bump(wv.outputs['Fac'], .8, .08)
    sh = s.bsdf(r.outputs['Color'], .85); s.link(b.outputs[0], sh.inputs['Normal'])
    return s.done(sh)


def m_leaf():
    s = NT('L_leaf')
    nz = s.noise(s.pos(), 3, 3)
    r = s.ramp(nz.outputs['Fac'], [(.35, '#24561a'), (.7, '#3f7a24')])
    pb = s.bsdf(r.outputs['Color'], .45, **{'Specular IOR Level': .4})
    tr = s.new('ShaderNodeBsdfTranslucent'); tr.inputs['Color'].default_value = hexlin('#7fb83a')
    mx = s.new('ShaderNodeMixShader'); mx.inputs['Fac'].default_value = .3
    s.link(pb.outputs[0], mx.inputs[1]); s.link(tr.outputs[0], mx.inputs[2])
    return s.done(mx)


LIB = {}
def lib(kind):
    if kind in LIB: return LIB[kind]
    f = {
        'paving': m_paving, 'grass': m_grass, 'coping': m_stone_white, 'water': m_water,
        'concrete': lambda: m_concrete(), 'steps': lambda: m_concrete('L_steps', ('#9d988f', '#b2ada3', '#c4bfb4'), False),
        'slide_red': lambda: m_fiberglass('L_slide_red', '#d81c14'), 'slide_blue': lambda: m_fiberglass('L_slide_blue', '#1157d6'),
        'slide_yellow': lambda: m_fiberglass('L_slide_yellow', '#ffc21a', .65),
        'metal': lambda: m_metal('L_metal', '#b9bdc2', .3), 'metal_dark': lambda: m_metal('L_metal_dark', '#4a4d52', .4),
        'bucket': lambda: m_fiberglass('L_bucket', '#ff8a00'), 'plastic_orange': lambda: m_plastic('L_porange', '#ff5a1f'),
        'plastic_pink': lambda: m_plastic('L_ppink', '#ff3d7f'), 'plastic_yellow': lambda: m_plastic('L_pyellow', '#ffc21a'),
        'wood': lambda: m_wood('L_wood', '#8a5f36', '#b98a57'), 'wood_dark': lambda: m_wood('L_wood_dark', '#4a3020', '#6e4a30'),
        'trunk': m_trunk, 'leaf': m_leaf, 'jetwater': m_jet, 'foam': m_foam,
    }.get(kind)
    LIB[kind] = f() if f else None
    return LIB[kind]


# ------------------------------------------------------------------ palmwaaiers i.p.v. kegelbladeren
# Een blad uit three.js ligt (na de y-up -> z-up conversie) langs lokale +Z, plat in het XZ-vlak.
# We vervangen de mesh door een gebogen nerf met blaadjes die naar buiten en omlaag hangen.
def frond_mesh():
    bm = bmesh.new(); L, N = 4.4, 26
    def rachis(t): return Vector((0, -0.9 * t * t, L * t))          # boog: zakt naar de punt toe door
    for i in range(N):
        t0, t1 = i / N, (i + 1) / N
        a, b = rachis(t0), rachis(t1)
        w = .05 * (1 - t0) + .015
        vs = [bm.verts.new(a + Vector((-w, 0, 0))), bm.verts.new(a + Vector((w, 0, 0))), bm.verts.new(b + Vector((w * .8, 0, 0))), bm.verts.new(b + Vector((-w * .8, 0, 0)))]
        bm.faces.new(vs)
        if t0 < .06: continue
        ll = 1.25 * math.sin(math.pi * min(1, t0 * 1.15)) + .15          # blaadjes: lang in het midden, kort aan de punt
        for sx in (-1, 1):
            base = rachis(t0 + .5 / N)
            tip = base + Vector((sx * ll, -.35 * ll, ll * .35))             # schuin naar voren en omlaag
            side = Vector((0, 0, .055))
            f = [bm.verts.new(base - side), bm.verts.new(base + side), bm.verts.new(tip + side * .2), bm.verts.new(tip - side * .2)]
            bm.faces.new(f)
    me = bpy.data.meshes.new('frond'); bm.to_mesh(me); bm.free()
    return me


FROND = frond_mesh()
nleaf = 0
for ob in list(scene.objects):
    if ob.type == 'MESH' and ob.material_slots and ob.material_slots[0].material and ob.material_slots[0].material.name.split('.')[0] == 'leaf':
        ob.data = FROND; ob.data.materials.clear() if False else None; nleaf += 1
if not FROND.materials: FROND.materials.append(bpy.data.materials.new('leaf'))
print('FRONDS', nleaf)

# ------------------------------------------------------------------ heuvels/bos aan de horizon
def hills():
    bm = bmesh.new(); seg, rings = 160, 6
    import random; rnd = random.Random(7)
    ph = [rnd.uniform(0, 6.28) for _ in range(6)]
    grid = []
    for j in range(rings + 1):
        rr = 230 + j * 70; row = []
        for i in range(seg):
            a = i / seg * math.tau
            h = (14 + 9 * math.sin(a * 3 + ph[0]) + 6 * math.sin(a * 7 + ph[1]) + 3 * math.sin(a * 17 + ph[2])) * math.sin(math.pi * j / rings) ** .7
            h *= 1 + j * .45
            row.append(bm.verts.new((math.cos(a) * rr, math.sin(a) * rr, max(h, 0) - .5)))
        grid.append(row)
    for j in range(rings):
        for i in range(seg):
            bm.faces.new([grid[j][i], grid[j][(i + 1) % seg], grid[j + 1][(i + 1) % seg], grid[j + 1][i]])
    me = bpy.data.meshes.new('hills'); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    ob = bpy.data.objects.new('hills', me); scene.collection.objects.link(ob)
    s = NT('L_forest'); nz = s.noise(s.pos(), .05, 6); fine = s.noise(s.pos(), .8, 5)
    r = s.ramp(nz.outputs['Fac'], [(.3, '#1d3a14'), (.55, '#2f5a1f'), (.8, '#4a6e2c')])
    b = s.bump(fine.outputs['Fac'], 1.0, 1.0)
    sh = s.bsdf(r.outputs['Color'], .95); s.link(b.outputs[0], sh.inputs['Normal'])
    me.materials.append(s.done(sh))
hills()

# ------------------------------------------------------------------ gele tube: koepel (onder dicht, dak doorzichtig)
# De sweep in three.js legt per ring 21 vertices op hoek a = j/20 * boog; offset = cos(a)*zij - sin(a)*boven.
# Attribuut 'up' = -sin(a): +1 bovenin het dak, -1 onderin de goot. (Volgorde blijft behouden door glTF.)
for ob in scene.objects:
    if ob.type != 'MESH' or not ob.material_slots or not ob.material_slots[0].material: continue
    if ob.material_slots[0].material.name.split('.')[0] != 'slide_yellow': continue
    me = ob.data; n = len(me.vertices); full = n == 501 * 21
    arc = math.tau if full else math.pi
    at = me.attributes.new('up', 'FLOAT', 'POINT')
    at.data.foreach_set('value', [-math.sin(arc * (i % 21) / 20) for i in range(n)])
    print('TUBE', ob.name, n, 'full' if full else 'overgang')


def m_tube(variant):
    s = NT('L_slide_yellow_' + variant)
    yel = s.bsdf('#ffc21a', .25, **{'Coat Weight': 1.0, 'Coat Roughness': .03})
    if variant == 'clear':
        # heel weinig dekkend geel; de kleur komt vooral uit het filter (transparant met gele tint)
        alpha = s.new('ShaderNodeValue'); alpha.outputs[0].default_value = .1; afac = alpha.outputs[0]
    else:
        a = s.new('ShaderNodeAttribute', attribute_name='up', attribute_type='GEOMETRY')
        mr = s.new('ShaderNodeMapRange'); s.link(a.outputs['Fac'], mr.inputs['Value'])
        mr.inputs['From Min'].default_value = .05; mr.inputs['From Max'].default_value = .35   # rand van de goot -> dak
        mr.inputs['To Min'].default_value = 1.0; mr.inputs['To Max'].default_value = .0
        afac = mr.outputs['Result']
    # getint glas: dun doorzichtig + glans erbovenop, zodat het dak nog zichtbaar blijft
    glass = s.bsdf('#fff1b8', .02, **{'Coat Weight': 1.0, 'Coat Roughness': .0, 'Specular IOR Level': 1.0})
    tr = s.new('ShaderNodeBsdfTransparent'); tr.inputs['Color'].default_value = hexlin('#ffe08a' if variant == 'clear' else '#fff7dc')
    gm = s.new('ShaderNodeMixShader'); gm.inputs['Fac'].default_value = .93      # vooral doorzicht, wat reflectie
    s.link(glass.outputs[0], gm.inputs[1]); s.link(tr.outputs[0], gm.inputs[2])
    mx = s.new('ShaderNodeMixShader'); s.link(afac, mx.inputs['Fac'])
    s.link(gm.outputs[0], mx.inputs[1]); s.link(yel.outputs[0], mx.inputs[2])
    m = s.done(mx)
    for k, v in [('surface_render_method', 'BLENDED'), ('use_transparency_overlap', True), ('use_backface_culling', False),
                 ('blend_method', 'BLEND'), ('show_transparent_back', True), ('use_transparent_shadow', True), ('shadow_method', 'HASHED')]:
        try: setattr(m, k, v)
        except Exception: pass
    return m


LIB['slide_yellow'] = m_tube(args.tube)

stats = {}
for ob in scene.objects:
    if ob.type != 'MESH': continue
    for slot in ob.material_slots:
        if not slot.material: continue
        name = slot.material.name.split('.')[0]
        if name.startswith('fig_'): stats['fig'] = stats.get('fig', 0) + 1; continue    # poppetjes: as-is
        if name == 'lamp':
            bs = slot.material.node_tree.nodes.get('Principled BSDF')
            if bs: bs.inputs['Emission Strength'].default_value = 6.0
            continue
        m = lib(name)
        if m: slot.material = m; stats[name] = stats.get(name, 0) + 1
        else: stats['keep:' + name] = stats.get('keep:' + name, 0) + 1
print('MATERIALS', stats)

# ------------------------------------------------------------------ spetters
if meta['drops']:
    bm = bmesh.new()
    for x, y, z, r in meta['drops']:
        mat = __import__('mathutils').Matrix.Translation(t2b((x, y, z))) @ __import__('mathutils').Matrix.Scale(max(r, .02), 4)
        bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0, matrix=mat)
    me = bpy.data.meshes.new('drops'); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    ob = bpy.data.objects.new('drops', me); scene.collection.objects.link(ob)
    me.materials.append(m_clear_water('L_drops', '#f2fdff'))

# ------------------------------------------------------------------ camera
cd = bpy.data.cameras.new('cam'); cd.sensor_fit = 'VERTICAL'; cd.angle_y = math.radians(meta['cam']['fov']); cd.clip_end = 3000
cam = bpy.data.objects.new('cam', cd); scene.collection.objects.link(cam); scene.camera = cam
cam.location = t2b(meta['cam']['pos'])
qx, qy, qz, qw = meta['cam']['quat']
cam.rotation_mode = 'QUATERNION'
cam.rotation_quaternion = Quaternion((math.cos(math.pi / 4), math.sin(math.pi / 4), 0, 0)) @ Quaternion((qw, qx, qy, qz))

# ------------------------------------------------------------------ lucht + zon (fysiek)
d = t2b(meta['sun']['dir']).normalized()
el = math.asin(max(min(d.z, 1), -1))
rot = math.atan2(d.x, d.y)                     # hoek rond z, gemeten vanaf +y naar +x
w = bpy.data.worlds.new('sky'); scene.world = w; w.use_nodes = True
nt = w.node_tree
for x in list(nt.nodes):
    if x.type != 'OUTPUT_WORLD': nt.nodes.remove(x)
sky = nt.nodes.new('ShaderNodeTexSky')
for k, v in [('sky_type', 'MULTIPLE_SCATTERING'), ('sun_disc', True), ('sun_size', math.radians(.8)), ('sun_intensity', 1.0),
             ('sun_elevation', max(el, math.radians(.5))), ('sun_rotation', rot), ('altitude', 50.0), ('air_density', 1.0),
             ('aerosol_density', .8), ('dust_density', .8), ('ozone_density', 1.0)]:
    try: setattr(sky, k, v)
    except Exception: pass
bg = nt.nodes.new('ShaderNodeBackground'); bg.inputs['Strength'].default_value = args.sky
nt.links.new(sky.outputs['Color'], bg.inputs['Color'])
nt.links.new(bg.outputs[0], [x for x in nt.nodes if x.type == 'OUTPUT_WORLD'][0].inputs['Surface'])
print('SUN el=%.1f rot=%.1f' % (math.degrees(el), math.degrees(rot)))

# ------------------------------------------------------------------ render
r = scene.render
rx, ry = map(int, args.res.lower().split('x'))
r.resolution_x, r.resolution_y, r.resolution_percentage = rx, ry, 100
r.engine = 'CYCLES'
c = scene.cycles
c.device = 'CPU'; c.samples = args.samples; c.use_denoising = True
if args.device != 'cpu':                                       # gpu = eerste beschikbare: OptiX, CUDA, HIP, Metal, oneAPI
    prefs = bpy.context.preferences.addons['cycles'].preferences
    for kind in (['OPTIX', 'CUDA', 'HIP', 'METAL', 'ONEAPI'] if args.device == 'gpu' else [args.device.upper()]):
        try:
            prefs.compute_device_type = kind; prefs.get_devices()
        except Exception:
            continue
        gpus = [d for d in prefs.devices if d.type == kind]
        if gpus:
            for d in prefs.devices: d.use = d.type == kind
            c.device = 'GPU'; print('DEVICE', kind, [d.name for d in gpus]); break
    else:
        print('DEVICE geen GPU gevonden, CPU')
    try: c.denoising_use_gpu = c.device == 'GPU'
    except Exception: pass
try: c.denoiser = 'OPENIMAGEDENOISE'
except Exception: pass
try: c.denoising_quality = args.denoise
except Exception as e: print('DQ', e)
c.max_bounces = 8; c.diffuse_bounces = 3; c.glossy_bounces = 4; c.transmission_bounces = 8; c.transparent_max_bounces = 16
c.caustics_reflective = False; c.caustics_refractive = False
c.sample_clamp_indirect = 8.0
vs = scene.view_settings
try: vs.view_transform = 'AgX'
except Exception: pass
for look in ('AgX - Medium High Contrast', 'Medium High Contrast', 'AgX - Punchy', 'Punchy'):
    try: vs.look = look; break
    except Exception: pass
vs.exposure = args.exposure
r.image_settings.file_format = 'PNG'
r.filepath = os.path.abspath(args.out)
if args.save: bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(args.save))


def render_to(path):
    r.filepath = os.path.abspath(path); t0 = time.time()
    bpy.ops.render.render(write_still=True)
    dt = time.time() - t0; print('RENDERED', r.filepath, 'in %.1fs' % dt); return dt


if not args.ladder:
    render_to(args.out)
else:
    # Kwaliteitsladder: dezelfde scène, één keer geladen, met een vaste tijd per frame.
    # c<N> = Cycles met tijdslimiet N s (+ ontruisen), e = Eevee. Tijden -> <out>_times.json
    base, times = os.path.splitext(args.out)[0], []
    r.use_persistent_data = True                       # zoals in een film: BVH/shaders blijven tussen frames staan
    for cfg in args.ladder.split(','):
        if cfg.startswith('c'):
            r.engine = 'CYCLES'; c.samples = 4096; c.time_limit = float(cfg[1:])
            c.use_adaptive_sampling = True; c.adaptive_threshold = .02
        else:
            r.engine = 'BLENDER_EEVEE'
            ee = scene.eevee
            for k, v in [('taa_render_samples', args.esamples), ('use_raytracing', True), ('use_shadows', True), ('shadow_ray_count', 2),
                         ('shadow_step_count', 8), ('use_volumetric_shadows', False), ('fast_gi_method', 'GLOBAL_ILLUMINATION')]:
                try: setattr(ee, k, v)
                except Exception: pass
            try: w.sun_threshold = 2.0; w.sun_angle = math.radians(.8); w.use_sun_shadow = True   # zon uit de lucht halen, met schaduw
            except Exception: pass
        times.append((cfg, round(render_to('%s_%s.png' % (base, cfg)), 1)))
    json.dump(times, open(base + '_times.json', 'w'), indent=1)
    print('LADDER', times)

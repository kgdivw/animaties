"""
Bouwt de complete scène (decor + personages) en rendert één beeld.

  blender -b --python render_still.py -- --out ../_snaps/bl_still.png --res 50 --samples 32 [--p 0.25] [--save scene.blend]
"""
import bpy, sys, os, math, argparse
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument('--out', default=os.path.join(HERE, '..', '_snaps', 'bl_still.png'))
ap.add_argument('--res', type=int, default=50)
ap.add_argument('--samples', type=int, default=32)
ap.add_argument('--save', default='')
ap.add_argument('--nochars', action='store_true')
ap.add_argument('--border', default='')   # x0,y0,x1,y1 in template-pixels
args = ap.parse_args(argv)

bpy.ops.wm.read_factory_settings(use_empty=True)

import bl_lib as L
import scene_town
import build_characters as BC
import poses as PO

scene = bpy.context.scene
cam = L.setup_camera(scene)
M, fc, nleaves = scene_town.build_all()
print('leaves', nleaves)


# ------------------------------------------------------------------ lucht
def world():
    w = bpy.data.worlds.new('night'); scene.world = w
    w.use_nodes = True
    nt = w.node_tree; n = nt.nodes; l = nt.links
    for x in list(n):
        if x.type != 'OUTPUT_WORLD':
            n.remove(x)
    out = [x for x in n if x.type == 'OUTPUT_WORLD'][0]
    _new = n.new
    def nnew(t, **kw):
        nd = _new(t)
        for k, v in kw.items():
            setattr(nd, k, v)
        return nd
    n_new = nnew
    tc = n_new('ShaderNodeTexCoord')
    sep = n_new('ShaderNodeSeparateXYZ'); l.new(tc.outputs['Window'], sep.inputs[0])
    ramp = n_new('ShaderNodeValToRGB')
    cr = ramp.color_ramp
    stops = [(0.0, '#5a80b8'), (0.35, '#3a6eb0'), (0.5, '#1a5296'), (0.68, '#06326a'), (0.85, '#011d48'), (1.0, '#001232')]
    cr.elements[0].position = stops[0][0]; cr.elements[0].color = L.hexlin(stops[0][1])
    cr.elements[1].position = stops[-1][0]; cr.elements[1].color = L.hexlin(stops[-1][1])
    for pos, c in stops[1:-1]:
        e = cr.elements.new(pos); e.color = L.hexlin(c)
    # Window-y loopt 0 (onder) .. 1 (boven); de lucht zit in de bovenste helft
    mr = n_new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = 0.42; mr.inputs['From Max'].default_value = 1.0
    l.new(sep.outputs['Y'], mr.inputs['Value']); l.new(mr.outputs['Result'], ramp.inputs['Fac'])
    # sterren
    cmb = n_new('ShaderNodeCombineXYZ')
    mx = n_new('ShaderNodeMath', operation='MULTIPLY'); mx.inputs[1].default_value = 1672 / 941
    l.new(sep.outputs['X'], mx.inputs[0]); l.new(mx.outputs[0], cmb.inputs['X']); l.new(sep.outputs['Y'], cmb.inputs['Y'])
    vo = n_new('ShaderNodeTexVoronoi', feature='F1'); vo.inputs['Scale'].default_value = 140
    l.new(cmb.outputs[0], vo.inputs['Vector'])
    st = n_new('ShaderNodeMath', operation='LESS_THAN'); st.inputs[1].default_value = 0.035
    l.new(vo.outputs['Distance'], st.inputs[0])
    hi = n_new('ShaderNodeMath', operation='MULTIPLY'); l.new(st.outputs[0], hi.inputs[0])
    l.new(mr.outputs['Result'], hi.inputs[1])
    sc = n_new('ShaderNodeMath', operation='MULTIPLY'); sc.inputs[1].default_value = 1.4; l.new(hi.outputs[0], sc.inputs[0])
    add = n_new('ShaderNodeMix', data_type='RGBA', blend_type='ADD'); add.inputs['Factor'].default_value = 1.0
    l.new(ramp.outputs['Color'], add.inputs[6]); l.new(sc.outputs[0], add.inputs[7])
    # wolkenbanden: ruis in schermruimte, uitgerekt
    cm2 = n_new('ShaderNodeCombineXYZ')
    mx2 = n_new('ShaderNodeMath', operation='MULTIPLY'); mx2.inputs[1].default_value = 1.2
    l.new(sep.outputs['X'], mx2.inputs[0]); l.new(mx2.outputs[0], cm2.inputs['X'])
    my2 = n_new('ShaderNodeMath', operation='MULTIPLY'); my2.inputs[1].default_value = 7.0
    l.new(sep.outputs['Y'], my2.inputs[0]); l.new(my2.outputs[0], cm2.inputs['Y'])
    cn = n_new('ShaderNodeTexNoise'); cn.inputs['Scale'].default_value = 2.2; cn.inputs['Detail'].default_value = 6.0
    l.new(cm2.outputs[0], cn.inputs['Vector'])
    cramp = n_new('ShaderNodeValToRGB')
    cramp.color_ramp.elements[0].position = 0.38; cramp.color_ramp.elements[0].color = (0, 0, 0, 1)
    cramp.color_ramp.elements[1].position = 0.62; cramp.color_ramp.elements[1].color = (1, 1, 1, 1)
    l.new(cn.outputs['Fac'], cramp.inputs['Fac'])
    band = n_new('ShaderNodeMapRange'); band.inputs['From Min'].default_value = 0.72; band.inputs['From Max'].default_value = 0.9
    band.inputs['To Min'].default_value = 1.0; band.inputs['To Max'].default_value = 0.0
    l.new(sep.outputs['Y'], band.inputs['Value'])
    cmul = n_new('ShaderNodeMath', operation='MULTIPLY'); l.new(cramp.outputs['Color'], cmul.inputs[0]); l.new(band.outputs['Result'], cmul.inputs[1])
    cmix = n_new('ShaderNodeMix', data_type='RGBA', blend_type='MIX')
    l.new(cmul.outputs[0], cmix.inputs['Factor'])
    l.new(add.outputs[2], cmix.inputs[6]); cmix.inputs[7].default_value = L.hexlin('#3d7cc4')
    bg_cam = n_new('ShaderNodeBackground'); l.new(cmix.outputs[2], bg_cam.inputs['Color'])
    bg_amb = n_new('ShaderNodeBackground'); bg_amb.inputs['Color'].default_value = L.hexlin('#2a3c74'); bg_amb.inputs['Strength'].default_value = 1.6
    lp = n_new('ShaderNodeLightPath')
    ms = n_new('ShaderNodeMixShader')
    l.new(lp.outputs['Is Camera Ray'], ms.inputs[0]); l.new(bg_amb.outputs[0], ms.inputs[1]); l.new(bg_cam.outputs[0], ms.inputs[2])
    l.new(ms.outputs[0], out.inputs['Surface'])


def moon():
    d = 300.0
    c = L.S2W(555, 127, d)
    r = 74 * d / L.F_PX
    m, b = L.new_mat('moon')
    b.n.remove(b.bsdf)
    nz = b.node('ShaderNodeTexNoise', i_Scale=2.2, i_Detail=5.0)
    ramp = b.node('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position = 0.35; ramp.color_ramp.elements[0].color = L.hexlin('#e0b468')
    ramp.color_ramp.elements[1].position = 0.65; ramp.color_ramp.elements[1].color = L.hexlin('#fff2c8')
    b.link(nz.outputs['Fac'], ramp.inputs['Fac'])
    em = b.node('ShaderNodeEmission', i_Strength=1.05)
    b.link(ramp.outputs['Color'], em.inputs['Color']); b.link(em.outputs[0], b.out.inputs['Surface'])
    o = L.ellipsoid('moon', c, (r, r, r), m, seg=48, rings=24, col='sky')
    o.visible_diffuse = False; o.visible_glossy = False; o.visible_shadow = False


def lights():
    # maan: koel licht schuin van achteren-links (randlicht op daken en figuren)
    sd = bpy.data.lights.new('moonlight', 'SUN'); sd.energy = 1.1; sd.color = L.hexlin('#a8bcff')[:3]; sd.angle = math.radians(1.5)
    so = bpy.data.objects.new('moonlight', sd); L.coll('lights').objects.link(so)
    so.rotation_euler = (math.radians(55), math.radians(-25), math.radians(200))
    # warme algemene gloed van het plein (zacht, van voren-onder)
    ad = bpy.data.lights.new('squareglow', 'AREA'); ad.energy = 250; ad.size = 14; ad.color = L.hexlin('#ff9a50')[:3]
    ao = bpy.data.objects.new('squareglow', ad); L.coll('lights').objects.link(ao)
    ao.location = (1.0, 5.0, 0.4); ao.rotation_euler = (math.radians(-85), 0, 0)
    # warm vullicht op alle gevels, vanaf achter de camera (zoals de template: alles baadt in warm licht)
    fd = bpy.data.lights.new('facadefill', 'AREA'); fd.energy = 4300; fd.size = 18; fd.color = L.hexlin('#ffcfa0')[:3]
    fo = bpy.data.objects.new('facadefill', fd); L.coll('lights').objects.link(fo)
    fo.location = (1.5, -3.0, 5.5); fo.rotation_euler = (math.radians(82), 0, 0)
    fo.visible_glossy = False
    try:
        rc = L.coll('fill_receivers')
        for cname in ('town', 'back', 'chars'):
            c = L.coll(cname)
            if c.name not in [x.name for x in rc.children]:
                pass
        fo.light_linking.receiver_collection = L.coll('town')
    except Exception as e:
        print('light linking', e)
    ad.cycles.is_caustics_light = False


world()
lights()
# zacht licht op de daken (zodat de pannen en hun schaduwranden leesbaar worden)
roofs = L.coll('roofs')
for o in list(bpy.data.objects):
    if o.name.startswith(('main_roof', 'dormroof', 'roofA', 'roofC', 'ridge')):
        roofs.objects.link(o)
rd = bpy.data.lights.new('roofglow', 'AREA'); rd.energy = 1500; rd.size = 12; rd.color = L.hexlin('#ffc0a0')[:3]
ro = bpy.data.objects.new('roofglow', rd); L.coll('lights').objects.link(ro)
ro.location = (1.5, 6.0, 12.0); ro.rotation_euler = (math.radians(35), 0, 0)
ro.visible_glossy = False
try:
    ro.light_linking.receiver_collection = roofs
except Exception as e:
    print('ll roofs', e)
gd = bpy.data.lights.new('groundsoft', 'AREA'); gd.energy = 2600; gd.size = 24; gd.color = L.hexlin('#d8b8c8')[:3]
go = bpy.data.objects.new('groundsoft', gd); L.coll('lights').objects.link(go)
go.location = (1.0, 9.0, 9.0); go.rotation_euler = (0, 0, 0)
go.visible_glossy = False
try:
    go.light_linking.receiver_collection = L.coll('ground')
except Exception as e:
    print('ll', e)


# ------------------------------------------------------------------ personages
CH = {}


def place(rig, sx, sy_ground, d, yaw, scale, pose, col='chars'):
    objs = rig.build()
    arm = objs[0]
    for o in objs:
        for c in o.users_collection:
            c.objects.unlink(o)
        L.coll(col).objects.link(o)
    p = L.S2W(sx, sy_ground, d)
    arm.location = p
    arm.rotation_euler = (0, 0, yaw)
    arm.scale = (scale, scale, scale)
    props = {o.name: o for o in objs[2:]}
    PO.apply_pose(arm, pose, props)
    return arm


if not args.nochars:
    d = L.ground_d(702)
    dr = d + 1.15
    RS = 1.22
    def ridge_sy(x):
        return 297 - (x - 580) / (1370 - 580) * 5
    CH['piet_pakje'] = place(BC.make_piet('piet_pakje', '#2a4aa8', '#f2b632', '#203a8a', '#f6d040', 'gift', 4), 930, ridge_sy(930), dr - 0.1, 0.9, RS,
                             PO.piet({'walk': 1, 'ph': 2.2, 't': 3.0, 'wind': 0.5}, 'gift'), col='chars_roof')
    CH['piet_zak'] = place(BC.make_piet('piet_zak', '#6a2a8c', '#f2b632', '#5a2278', '#a03cd6', 'sack', 3), 800, ridge_sy(800), dr - 0.2, 0.9, RS,
                           PO.piet({'walk': 1, 'ph': 0.6, 't': 3.0, 'wind': 0.5}, 'sack'), col='chars_roof')
    # het paard loopt mee over de nok, met Sint in het zadel
    from mathutils import Matrix, Vector
    CH['paard'] = place(BC.make_horse(), 1075, ridge_sy(1075), dr + 0.05, -0.25, 1.1,
                        PO.horse({'t': 3.0, 'walk': 0.8, 'ph': 1.9, 'wind': 0.3}), col='chars_roof')
    rider = place(BC.make_sint(riding=True), 1075, ridge_sy(1075), dr, 0, 1.0,
                  PO.rider({'walk': 0.8, 'ph': 1.9, 't': 3.0, 'wind': 0.3, 'twist': 0.35, 'look': -0.15}), col='chars_roof')
    bpy.context.view_layer.update()
    ha = CH['paard']; pb = ha.pose.bones['body']
    delta = pb.matrix @ pb.bone.matrix_local.inverted()
    seat = Vector((-0.06, 0.0, 0.415))              # zadel t.o.v. paard-root (cm → m, Blender-assen)
    rider.matrix_world = ha.matrix_world @ delta @ Matrix.Translation(seat) @ Matrix.Rotation(math.pi / 2, 4, 'Z')
    CH['sint'] = rider
    dh = dr
    # warm hoofdlicht alleen voor de dakfiguren (light linking)
    # dakfiguren: gericht warm hoofdlicht linksvoor-boven + koel randlicht van de maan (achter-links)
    tgt = L.S2W(960, 210, dr)
    def aim(o, target):
        o.rotation_euler = (target - o.location).to_track_quat('-Z', 'Y').to_euler()
    kd = bpy.data.lights.new('charkey', 'AREA'); kd.energy = 230; kd.size = 2.5; kd.color = L.hexlin('#ffd6a4')[:3]
    ko = bpy.data.objects.new('charkey', kd); L.coll('lights').objects.link(ko)
    ko.location = tgt + Vector((-3.5, -5.0, 3.0)); aim(ko, tgt)
    md = bpy.data.lights.new('charrim', 'AREA'); md.energy = 420; md.size = 2.0; md.color = L.hexlin('#b8ccff')[:3]
    mo = bpy.data.objects.new('charrim', md); L.coll('lights').objects.link(mo)
    mo.location = tgt + Vector((-4.0, 5.0, 2.5)); aim(mo, tgt)
    mo.visible_camera = False
    try:
        mo.light_linking.receiver_collection = L.coll('chars_roof')
    except Exception:
        pass
    hd = bpy.data.lights.new('horsekey', 'AREA'); hd.energy = 160; hd.size = 3; hd.color = L.hexlin('#ffd8a8')[:3]
    ho = bpy.data.objects.new('horsekey', hd); L.coll('lights').objects.link(ho)
    ho.location = L.S2W(1000, 250, dh - 4.0); ho.rotation_euler = (math.radians(70), 0, math.radians(-10))
    try:
        ho.light_linking.receiver_collection = L.coll('chars')
    except Exception:
        pass
    try:
        ko.light_linking.receiver_collection = L.coll('chars_roof')
    except Exception as e:
        print('light linking niet beschikbaar', e)


# ------------------------------------------------------------------ render
r = scene.render
r.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = args.samples
scene.cycles.use_denoising = True
try:
    scene.cycles.denoiser = 'OPENIMAGEDENOISE'
except Exception:
    pass
scene.cycles.max_bounces = 4
scene.cycles.diffuse_bounces = 2
scene.cycles.glossy_bounces = 2
scene.cycles.transmission_bounces = 2
scene.cycles.caustics_reflective = False
scene.cycles.caustics_refractive = False
scene.cycles.blur_glossy = 1.0
r.resolution_percentage = args.res
r.film_transparent = True
try:
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'Medium High Contrast'
except Exception as e:
    print('look', e)
scene.view_settings.exposure = 0.0
r.image_settings.file_format = 'PNG'
if args.border:
    x0, y0, x1, y1 = [float(v) for v in args.border.split(',')]
    r.use_border = True; r.use_crop_to_border = True
    r.border_min_x, r.border_max_x = x0 / 1672, x1 / 1672
    r.border_min_y, r.border_max_y = 1 - y1 / 941, 1 - y0 / 941
r.filepath = os.path.abspath(args.out)
if args.save:
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(args.save))
import time
t0 = time.time()
bpy.ops.render.render(write_still=True)
print('RENDERED', r.filepath, 'in %.1fs' % (time.time() - t0))

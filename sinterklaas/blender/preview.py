"""Workbench-voorvertoning van de .glb-modellen: per model 4 aanzichten."""
import bpy, sys, os, math
from mathutils import Vector
args = sys.argv[sys.argv.index('--') + 1:]
src, out = args[0], args[1]
names = args[2:] or ['sint', 'piet_zak', 'piet_pakje', 'paard']
os.makedirs(out, exist_ok=True)
for name in names:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=os.path.join(src, name + '.glb'))
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_WORKBENCH'
    sh = sc.display.shading
    sh.light = 'STUDIO'; sh.color_type = 'MATERIAL'; sh.show_shadows = True; sh.show_cavity = True
    sh.show_object_outline = False
    sc.render.resolution_x, sc.render.resolution_y = 420, 520
    sc.render.film_transparent = False
    world = bpy.data.worlds.new('w'); sc.world = world
    H = 2.3 if name != 'paard' else 2.0
    cam_d = bpy.data.cameras.new('c'); cam_d.type = 'ORTHO'; cam_d.ortho_scale = H * (1.0 if name != 'paard' else 1.35)
    cam = bpy.data.objects.new('c', cam_d); sc.collection.objects.link(cam); sc.camera = cam
    tgt = Vector((0, 0, H * 0.45 if name != 'paard' else 0.85))
    for k, ang in enumerate([0, 50, 90, 200]):
        a = math.radians(ang)
        # karakter kijkt naar -Y (Blender); camera vanaf voorkant draait mee
        pos = tgt + Vector((math.sin(a) * 8, -math.cos(a) * 8, 0.6))
        cam.location = pos
        d = tgt - pos
        cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
        sc.render.filepath = os.path.join(out, '%s_%d.png' % (name, k))
        bpy.ops.render.render(write_still=True)

"""Pakt models/*.glb in tot models/chars_glb.js (base64), zodat file:// blijft werken."""
import base64, os, sys
d = sys.argv[1]
parts = []
for n in ['sint', 'piet_zak', 'piet_pakje', 'paard', 'sint_rider']:
    b = base64.b64encode(open(os.path.join(d, n + '.glb'), 'rb').read()).decode()
    parts.append('  %s: "%s"' % (n, b))
open(os.path.join(d, 'chars_glb.js'), 'w').write('/* gegenereerd door blender/pack.py */\nwindow.CHAR_GLB = {\n' + ',\n'.join(parts) + '\n};\n')
print('packed', os.path.getsize(os.path.join(d, 'chars_glb.js')) // 1024, 'kB')

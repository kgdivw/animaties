"""
Nabewerking van een Blender-render (alleen PIL):
  - lucht erachter (verloop, wolkenbanden, sterren met kruisglans, maan met gloed)
    als de render een transparante achtergrond heeft;
  - gloed rond lichtbronnen, zachte dromerige waas;
  - kleurcorrectie (koele schaduwen, warme hooglichten) en vignet.

  python post.py in.png out.png [--t 0.0]   (t = tijd in s, laat sterren twinkelen)
"""
import sys, math, random
from PIL import Image, ImageFilter, ImageChops, ImageEnhance, ImageDraw

src, dst = sys.argv[1], sys.argv[2]
T = float(sys.argv[sys.argv.index('--t') + 1]) if '--t' in sys.argv else 0.0
im = Image.open(src)
W, H = im.size
k = W / 1672.0


def hexc(h):
    h = h.lstrip('#'); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def sky():
    """Nachtlucht zoals in de template, in toneelpixels geschaald naar W x H."""
    stops = [(0.0, '#001335'), (0.12, '#00183d'), (0.22, '#001c45'), (0.32, '#0a2a58'), (0.42, '#0f3c72'), (0.55, '#174f8e'), (0.7, '#2a62a2'), (1.0, '#3a6aa6')]
    col = Image.new('RGB', (1, H))
    for y in range(H):
        f = (y / k) / 560.0
        f = min(1.0, f)
        for i in range(len(stops) - 1):
            if stops[i][0] <= f <= stops[i + 1][0]:
                a, b = stops[i], stops[i + 1]
                u = (f - a[0]) / (b[0] - a[0])
                ca, cb = hexc(a[1]), hexc(b[1])
                col.putpixel((0, y), tuple(int(ca[j] + (cb[j] - ca[j]) * u) for j in range(3)))
                break
    s = col.resize((W, H))
    # wolkenbanden: zachte, uitgerekte ellipsen, licht aan de bovenkant
    cl = Image.new('L', (W, H), 0)
    d = ImageDraw.Draw(cl)
    blobs = [(1310, 196, 70, 14, 120), (1390, 186, 90, 18, 140), (1470, 200, 70, 14, 120), (1540, 218, 80, 12, 100), (1270, 214, 60, 10, 90),
             (1430, 228, 110, 13, 100), (1600, 244, 90, 13, 90), (1650, 205, 60, 12, 80), (250, 196, 70, 11, 120), (310, 206, 60, 9, 100),
             (205, 214, 44, 8, 90), (395, 172, 44, 8, 70), (720, 236, 70, 8, 50), (900, 252, 90, 9, 45), (1100, 246, 80, 8, 45)]
    for (x, y, rx, ry, a) in blobs:
        d.ellipse(((x - rx) * k, (y - ry) * k, (x + rx) * k, (y + ry) * k), fill=a)
    cl = cl.filter(ImageFilter.GaussianBlur(9 * k))
    s = Image.composite(Image.new('RGB', (W, H), hexc('#5a92d0')), s, cl.point(lambda v: min(255, int(v * 1.25))))
    # sterren
    r = random.Random(42)
    d2 = ImageDraw.Draw(s)
    mx, my, mr = 555 * k, 127 * k, 74 * k
    for i in range(650):
        x = r.random() * W; y = (r.random() ** 1.4) * 330 * k
        if math.hypot(x - mx, y - my) < mr * 1.8:
            continue
        a = (0.25 + 0.75 * r.random()) * (1 - y / (380 * k))
        tw = 0.7 + 0.3 * math.sin(T * (1 + r.random() * 2) + i)
        v = int(255 * a * tw)
        sz = 0.6 * k if r.random() < 0.9 else 1.2 * k
        d2.ellipse((x - sz, y - sz, x + sz, y + sz), fill=(min(255, v + 10), min(255, v + 20), 255))
    # maan met gloed
    glow = Image.new('L', (W, H), 0)
    dg = ImageDraw.Draw(glow)
    for rr, a in ((4.6, 30), (3.0, 60), (2.0, 110), (1.45, 170)):
        dg.ellipse((mx - mr * rr, my - mr * rr, mx + mr * rr, my + mr * rr), fill=a)
    glow = glow.filter(ImageFilter.GaussianBlur(40 * k))
    s = Image.composite(Image.new('RGB', (W, H), hexc('#ffd79a')), s, glow.point(lambda v: int(v * 0.55)))
    moon = Image.new('RGB', (int(mr * 2) + 2, int(mr * 2) + 2), hexc('#f8d488'))
    mm = Image.new('L', moon.size, 0)
    ImageDraw.Draw(mm).ellipse((0, 0, moon.size[0] - 1, moon.size[1] - 1), fill=255)
    md = ImageDraw.Draw(moon)
    # licht naar het midden, zeeën en kraters
    for i in range(30, 0, -1):
        f = i / 30
        c = tuple(int(hexc('#e8b45e')[j] + (hexc('#fff6d8')[j] - hexc('#e8b45e')[j]) * (1 - f) ** 0.8) for j in range(3))
        rr = mr * f
        md.ellipse((mr - 18 * k * (1 - f) - rr, mr - 22 * k * (1 - f) - rr, mr - 18 * k * (1 - f) + rr, mr - 22 * k * (1 - f) + rr), fill=c)
    marks = Image.new('L', moon.size, 0)
    dmk = ImageDraw.Draw(marks)
    for (x, y, rx, ry, a) in [(-22, -18, 22, 15, 70), (12, -28, 16, 11, 60), (20, 6, 24, 17, 65), (-12, 22, 18, 12, 60), (-36, 8, 10, 14, 45), (36, 30, 12, 9, 40)]:
        dmk.ellipse((mr + (x - rx) * k, mr + (y - ry) * k, mr + (x + rx) * k, mr + (y + ry) * k), fill=a)
    for i in range(26):
        a = r.random() * math.tau; dd = math.sqrt(r.random()) * mr * 0.85; cr = (1.5 + r.random() * 5) * k
        x, y = mr + math.cos(a) * dd, mr + math.sin(a) * dd
        dmk.ellipse((x - cr, y - cr, x + cr, y + cr), outline=50)
    marks = marks.filter(ImageFilter.GaussianBlur(3 * k))
    moon = Image.composite(Image.new('RGB', moon.size, hexc('#c08a48')), moon, marks)
    s.paste(moon, (int(mx - mr), int(my - mr)), mm)
    # heldere sterren met kruisglans
    for (x, y, sc) in [(1515, 55, 0.95), (1205, 38, 0.65), (1408, 105, 0.6), (887, 45, 0.5), (1640, 150, 0.35)]:
        x *= k; y *= k
        L = 22 * sc * k * (0.85 + 0.15 * math.sin(T * 1.7 + x))
        fl = Image.new('L', (W, H), 0)
        df = ImageDraw.Draw(fl)
        df.polygon([(x - L, y), (x, y - 1.2 * k * sc), (x + L, y), (x, y + 1.2 * k * sc)], fill=255)
        df.polygon([(x, y - L), (x + 1.2 * k * sc, y), (x, y + L), (x - 1.2 * k * sc, y)], fill=255)
        df.ellipse((x - 2.2 * k * sc, y - 2.2 * k * sc, x + 2.2 * k * sc, y + 2.2 * k * sc), fill=255)
        halo = fl.filter(ImageFilter.GaussianBlur(4 * k * sc))
        fl = ImageChops.lighter(fl, halo.point(lambda v: min(255, int(v * 1.6))))
        s = Image.composite(Image.new('RGB', (W, H), (235, 242, 255)), s, fl)
    return s


if im.mode == 'RGBA':
    bg = sky()
    bg.paste(im, (0, 0), im)
    im = bg
else:
    im = im.convert('RGB')

# gloed: alleen de felste delen, op drie schalen
lum = im.convert('L')
mask = lum.point(lambda v: 0 if v < 175 else min(255, (v - 175) * 3))
hi = Image.composite(im, Image.new('RGB', im.size, 0), mask)
glow = Image.new('RGB', im.size, 0)
for rr, a in ((6, 0.55), (20, 0.5), (60, 0.45)):
    g = hi.filter(ImageFilter.GaussianBlur(rr * k)).point(lambda v, a=a: int(v * a))
    glow = ImageChops.add(glow, g)
out = ImageChops.screen(im, glow)
soft = out.filter(ImageFilter.GaussianBlur(24 * k)).point(lambda v: int(v * 0.2))
out = ImageChops.screen(out, soft)
out = ImageEnhance.Color(out).enhance(1.1)
out = ImageEnhance.Contrast(out).enhance(1.06)
r_, g_, b_ = out.split()
shadow = out.convert('L').point(lambda v: max(0, 110 - v) * 2)
r_ = ImageChops.subtract(r_, shadow.point(lambda v: v // 12))
b_ = ImageChops.add(b_, shadow.point(lambda v: v // 8))
out = Image.merge('RGB', (r_, g_, b_))
vg = Image.new('L', (W, H), 0)
ImageDraw.Draw(vg).ellipse((-W * 0.25, -H * 0.3, W * 1.25, H * 1.3), fill=255)
vg = vg.filter(ImageFilter.GaussianBlur(W * 0.12))
out = Image.composite(out, ImageEnhance.Brightness(out).enhance(0.55), vg)
out.save(dst)
print('post', dst)

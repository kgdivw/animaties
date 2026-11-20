"""
Nabewerking van de filmframes: 360°-lucht erachter (draait mee met de camera),
optioneel gloed + kleurcorrectie, en daarna naar mp4.

  python post_frames.py <framemap> [--bloom] [--fps 12.5] [--mp4 uit.mp4]

Leest <framemap>/yaw.json (geschreven door film.py) voor de camerarichting per frame.
"""
import sys, os, json, math, random, glob, subprocess
from PIL import Image, ImageDraw, ImageFilter, ImageChops, ImageEnhance

src = sys.argv[1]
BLOOM = '--bloom' in sys.argv
FPS = float(sys.argv[sys.argv.index('--fps') + 1]) if '--fps' in sys.argv else 25.0
MP4 = sys.argv[sys.argv.index('--mp4') + 1] if '--mp4' in sys.argv else None
FF = os.environ.get('FFMPEG', 'ffmpeg')

log = json.load(open(os.path.join(src, 'yaw.json')))
frames = sorted(int(k) for k in log)
W, H = Image.open(os.path.join(src, 'f_%05d.png' % frames[0])).size
k = W / 1672.0
FPX = 1200 * k                       # pixels per radiaal in het midden van het beeld
PW = int(round(2 * math.pi * FPX))   # panoramabreedte
CX = 836 * k


def hexc(h):
    h = h.lstrip('#'); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def panorama():
    stops = [(0.0, '#001335'), (0.12, '#00183d'), (0.22, '#001c45'), (0.32, '#0a2a58'), (0.42, '#0f3c72'), (0.55, '#174f8e'), (0.7, '#2a62a2'), (1.0, '#3a6aa6')]
    col = Image.new('RGB', (1, H))
    for y in range(H):
        f = min(1.0, (y / k) / 560.0)
        for i in range(len(stops) - 1):
            if stops[i][0] <= f <= stops[i + 1][0]:
                a, b = stops[i], stops[i + 1]
                u = (f - a[0]) / (b[0] - a[0])
                ca, cb = hexc(a[1]), hexc(b[1])
                col.putpixel((0, y), tuple(int(ca[j] + (cb[j] - ca[j]) * u) for j in range(3)))
                break
    s = col.resize((PW, H))
    r = random.Random(42)
    # wolkenbanden rondom
    cl = Image.new('L', (PW, H), 0)
    d = ImageDraw.Draw(cl)
    for i in range(70):
        x = r.random() * PW; y = (160 + r.random() * 110) * k
        rx = (40 + r.random() * 90) * k; ry = (8 + r.random() * 10) * k
        d.ellipse((x - rx, y - ry, x + rx, y + ry), fill=int(60 + r.random() * 80))
    cl = cl.filter(ImageFilter.GaussianBlur(9 * k))
    s = Image.composite(Image.new('RGB', (PW, H), hexc('#5a92d0')), s, cl.point(lambda v: min(255, int(v * 1.1))))
    # sterren
    d2 = ImageDraw.Draw(s)
    for i in range(2600):
        x = r.random() * PW; y = (r.random() ** 1.4) * 330 * k
        a = (0.25 + 0.75 * r.random()) * (1 - y / (380 * k))
        v = int(255 * a)
        sz = 0.6 * k if r.random() < 0.9 else 1.2 * k
        d2.ellipse((x - sz, y - sz, x + sz, y + sz), fill=(min(255, v + 10), min(255, v + 20), 255))
    # maan in het noorden (zelfde plek als in de template)
    mx = (math.atan((555 - 836) / 1200.0) % (2 * math.pi)) * FPX
    my, mr = 127 * k, 74 * k
    for ox in (mx, mx - PW, mx + PW):
        glow = Image.new('L', (PW, H), 0)
        dg = ImageDraw.Draw(glow)
        for rr, al in ((4.6, 30), (3.0, 60), (2.0, 110), (1.45, 170)):
            dg.ellipse((ox - mr * rr, my - mr * rr, ox + mr * rr, my + mr * rr), fill=al)
        glow = glow.filter(ImageFilter.GaussianBlur(40 * k))
        s = Image.composite(Image.new('RGB', (PW, H), hexc('#ffd79a')), s, glow.point(lambda v: int(v * 0.55)))
        d3 = ImageDraw.Draw(s)
        d3.ellipse((ox - mr, my - mr, ox + mr, my + mr), fill=hexc('#f8d488'))
        d3.ellipse((ox - mr * 0.75, my - mr * 0.8, ox + mr * 0.55, my + mr * 0.5), fill=hexc('#fbe2a8'))
        for (x, y, rx, ry) in ((-22, -18, 22, 15), (12, -28, 16, 11), (20, 6, 24, 17), (-12, 22, 18, 12)):
            d3.ellipse((ox + (x - rx) * k, my + (y - ry) * k, ox + (x + rx) * k, my + (y + ry) * k), fill=hexc('#e2b46a'))
    # heldere sterren met kruisglans
    for i in range(14):
        x = r.random() * PW; y = (30 + r.random() * 140) * k; sc = 0.4 + r.random() * 0.6
        L = 22 * sc * k
        d4 = ImageDraw.Draw(s)
        d4.polygon([(x - L, y), (x, y - 1.2 * k * sc), (x + L, y), (x, y + 1.2 * k * sc)], fill=(235, 242, 255))
        d4.polygon([(x, y - L), (x + 1.2 * k * sc, y), (x, y + L), (x - 1.2 * k * sc, y)], fill=(235, 242, 255))
    return s


pano = panorama()
pano3 = Image.new('RGB', (PW * 3, H))
for i in range(3):
    pano3.paste(pano, (i * PW, 0))


def sky_for(yaw):
    alpha_c = -yaw                                   # azimut (met de klok mee vanaf noord) in het midden
    x0 = (alpha_c * FPX) % PW - CX + PW
    x0 = int(round(x0))
    return pano3.crop((x0, 0, x0 + W, H))


def grade(im):
    lum = im.convert('L')
    mask = lum.point(lambda v: 0 if v < 175 else min(255, (v - 175) * 3))
    hi = Image.composite(im, Image.new('RGB', im.size, 0), mask)
    glow = Image.new('RGB', im.size, 0)
    for rr, a in ((6, 0.55), (20, 0.5), (60, 0.45)):
        glow = ImageChops.add(glow, hi.filter(ImageFilter.GaussianBlur(rr * k)).point(lambda v, a=a: int(v * a)))
    out = ImageChops.screen(im, glow)
    out = ImageChops.screen(out, out.filter(ImageFilter.GaussianBlur(24 * k)).point(lambda v: int(v * 0.2)))
    out = ImageEnhance.Color(out).enhance(1.1)
    return ImageEnhance.Contrast(out).enhance(1.06)


outdir = os.path.join(src, 'post')
os.makedirs(outdir, exist_ok=True)
for n, f in enumerate(frames):
    im = Image.open(os.path.join(src, 'f_%05d.png' % f)).convert('RGBA')
    bg = sky_for(log[str(f)]['yaw'])
    bg.paste(im, (0, 0), im)
    if BLOOM:
        bg = grade(bg)
    if H % 2:
        bg = bg.crop((0, 0, W - W % 2, H - 1))
    bg.save(os.path.join(outdir, 'p_%05d.jpg' % n), quality=92)
    if n % 100 == 0:
        print('post', n, '/', len(frames), flush=True)
if MP4:
    subprocess.run([FF, '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', os.path.join(outdir, 'p_%05d.jpg'),
                    '-c:v', 'libx264', '-preset', 'slow', '-crf', '18', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', MP4], check=True)
    print('mp4', MP4)

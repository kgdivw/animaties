"""
De andere drie kanten van het plein (en de hoeken), voor de draaiende camera.

Elke kant wordt gebouwd alsof de camera, net als bij de template, naar +y kijkt:
in pixels (1672 x 941) plus diepte, met dezelfde bouwstenen als scene_town.
Daarna wordt alles wat bij die kant hoort om het midden van het plein (de camera)
gedraaid: oost = -90°, zuid = 180°, west = +90°.

Een kant loopt in pixels van -364 tot 2036; op diepte 14,5 m is dat precies
-14,5 .. +14,5 m, zodat de vier kanten in de hoeken op elkaar aansluiten.
"""
import bpy, math, random
from mathutils import Vector, Matrix
import scene_town as ST
from scene_town import facade, roof, window, flowers, lamp, barrel, gift, sack, wpoly
from bl_lib import S2W, ground_d, px, coll, obj_from, box, tube, lathe, ellipsoid, plain, emit, point_light, hexlin, TAU

D0 = ground_d(702)             # 14,5 m: gevellijn van elke kant
LEFT_EDGE, RIGHT_EDGE = -364, 2036
VIEW = {'north': 0.0, 'east': -math.pi / 2, 'south': math.pi, 'west': math.pi / 2}


# ------------------------------------------------------------------ draaien
def build_rotated(theta, fn, *args):
    """Bouw met fn() in het noord-kader en draai alles wat nieuw is om de oorsprong."""
    before = set(bpy.data.objects)
    out = fn(*args)
    new = [o for o in bpy.data.objects if o not in before and o.parent is None]
    piv = bpy.data.objects.new('pivot_%s' % fn.__name__, None)
    coll('env').objects.link(piv)
    piv.rotation_euler = (0, 0, theta)
    for o in new:
        o.parent = piv
    return out


# ------------------------------------------------------------------ huizen
def zy(sy, d):
    return S2W(836, sy, d).z


def house(M, name, x0, x1, top, d=D0, wall='brick', kind='gable', eave=None, rows=((420, 64), (560, 90)), cols=None,
          roofmat='roof', shop=None, flower=True, seed=1, base=702, arch=0, power=4):
    """Huis met de gevel naar het plein.
    kind: 'gable' (puntgevel tot top), 'step' (trapgevel), 'neck' (halsgevel), 'flat' (lijst op `eave`, dak met nok op `top`)."""
    w = x1 - x0
    if kind == 'gable':
        e = eave or top + (w * 0.55)
        pts = [(x0, base), (x1, base), (x1, e), ((x0 + x1) / 2, top), (x0, e)]
    elif kind == 'step':
        e = eave or top + w * 0.7
        n = 4
        cx = (x0 + x1) / 2
        inner = w * 0.14
        stw = (w / 2 - inner) / n
        sth = (e - top) / n
        pts = [(x0, base), (x0, e)]
        for i in range(n):
            pts += [(x0 + i * stw, e - (i + 1) * sth), (x0 + (i + 1) * stw, e - (i + 1) * sth)]
        pts += [(cx - inner, top), (cx + inner, top)]
        for i in range(n - 1, -1, -1):
            pts += [(x1 - (i + 1) * stw, e - (i + 1) * sth), (x1 - i * stw, e - (i + 1) * sth)]
        pts += [(x1, e), (x1, base)]
    elif kind == 'neck':
        e = eave or top + w * 0.75
        cx = (x0 + x1) / 2
        nw = w * 0.22
        sh = e - (e - top) * 0.45
        pts = [(x0, base), (x0, e), (x0 + w * 0.12, e), (cx - nw, sh), (cx - nw, top + 6), (cx, top), (cx + nw, top + 6), (cx + nw, sh), (x1 - w * 0.12, e), (x1, e), (x1, base)]
    else:   # flat: kroonlijst + dak erachter
        e = eave or top + 70
        pts = [(x0, base), (x1, base), (x1, e), (x0, e)]
    facade(name, pts, d, M[wall], thick=4)
    if kind == 'flat':
        roof(name + '_roof', M, M[roofmat], [(x0 - 8, e + 4), (x1 + 8, e + 4)], [(x0 + 20, top), (x1 - 20, top)], d - 0.2, d + 1.4, hip=False)
        a, b = S2W(x0 - 6, e - 4, d - 0.08), S2W(x1 + 6, e + 6, d - 0.08)
        box(name + '_lijst', ((a.x + b.x) / 2, d - 0.12, (a.z + b.z) / 2), (b.x - a.x, 0.3, a.z - b.z), M['trim'], col='town', bevel=0.01)
    else:
        # afdekrand langs de gevelrand
        for i in range(2, len(pts) - 2):
            p0, p1 = S2W(pts[i][0], pts[i][1], d - 0.05), S2W(pts[i + 1][0], pts[i + 1][1], d - 0.05)
            tube(name + '_rand', [p0, p1], [0.05, 0.05], M['trim'], seg=6, col='town')
        # dak erachter (zichtbaar tijdens het draaien)
        dk = [S2W(x0, e, d + 0.1), S2W((x0 + x1) / 2, top + 4, d + 0.1), S2W(x1, e, d + 0.1)]
        for sgn in (0, 1):
            a_, b_ = dk[sgn], dk[sgn + 1]
            V = [a_, b_, b_ + Vector((0, 4, 0)), a_ + Vector((0, 4, 0))]
            sl = (b_ - a_).length
            o = obj_from(name + '_dak', V, [(0, 1, 2, 3)], M[roofmat], col='town', uv=[(0, 0), (sl, 0), (sl, 4), (0, 4)], recalc=False)
            o.modifiers.new('s', 'SOLIDIFY').thickness = 0.08
    # ramen
    for (yy, hh) in rows:
        if yy + hh > base - 4 or yy < (e if kind == 'flat' else e - 30):
            continue
        n = cols or max(1, int(w / 75))
        ww = min(56, w / n * 0.55)
        for k in range(n):
            xx = x0 + w * (k + 0.5) / n - ww / 2
            window(M, xx, yy, ww, hh, d, arch, 2, 3 if hh > 70 else 2, power=power)
            if flower and hh < 80:
                flowers(M, xx - 6, yy + hh + 8, ww + 12, d, seed=seed + k)
    if shop:
        sx0, sy0, sw, sh_ = shop
        window(M, sx0, sy0, sw, sh_, d, 1, 4, 3, power=10, shop=True)
    # bovenste raampje in de gevel
    if kind in ('gable', 'step', 'neck'):
        window(M, (x0 + x1) / 2 - 12, (top + (eave or top + w * 0.6)) / 2 - 8, 24, 32, d, 1, 1, 2, lit=0.85)
    # plint
    a, b = S2W(x0, base - 12, d), S2W(x1, base, d)
    box(name + '_plint', ((a.x + b.x) / 2, d - 0.04, (a.z + b.z) / 2), (b.x - a.x, 0.1, a.z - b.z), M['trim_dark'], col='town')


def awning(M, x0, x1, y_top, y_front, d, name='luifel'):
    fl, fr = S2W(x0 - 10, y_front, d - 0.8), S2W(x1 + 10, y_front, d - 0.8)
    bl, br = S2W(x0, y_top, d), S2W(x1, y_top, d)
    o = obj_from(name, [fl, fr, br, bl], [(0, 1, 2, 3)], M['awning'], col='ground',
                 uv=[(0, 0), ((fr - fl).length, 0), ((br - bl).length, 1), (0, 1)], recalc=False)
    o.modifiers.new('s', 'SOLIDIFY').thickness = 0.02
    n = int((x1 - x0) / 18)
    for i in range(n):
        p0 = fl.lerp(fr, i / n); p1 = fl.lerp(fr, (i + 1) / n); mid = (p0 + p1) / 2
        V = [p0, p1, p1 + Vector((0, 0, -0.09)), mid + Vector((0, 0, -0.18)), p0 + Vector((0, 0, -0.09))]
        obj_from('schulp', V, [(0, 1, 2, 3, 4)], M['flag'][0] if i % 2 == 0 else plain('cream', '#f4ead8', 0.75), col='ground', recalc=False)


def filler(M, x0, x1, seed):
    """Huizen die de hoek dichtmaken (alleen zichtbaar tijdens het draaien)."""
    r = random.Random(seed)
    x = x0
    kinds = ['gable', 'step', 'flat', 'neck']
    walls = ['brick', 'brick2', 'plaster', 'stone_grey']
    i = 0
    while x < x1 - 40:
        w = r.uniform(230, 320)
        xe = min(x1, x + w)
        k = kinds[r.randrange(4)]
        top = r.uniform(170, 300) if k != 'flat' else r.uniform(300, 360)
        house(M, 'hoek%d_%d' % (seed, i), x, xe, top, wall=walls[r.randrange(4)], kind=k, seed=seed * 10 + i,
              rows=((r.uniform(400, 440), 60), (560, 86)), roofmat='roof' if r.random() < 0.6 else 'slate')
        x = xe
        i += 1


# ------------------------------------------------------------------ OOST: stadhuis met klokkentoren
def east_side(M):
    d = D0
    filler(M, LEFT_EDGE, 0, 11)
    house(M, 'oost_a', 0, 300, 290, wall='plaster', kind='flat', eave=380, roofmat='slate', rows=((440, 62), (560, 90)), seed=21)
    house(M, 'oost_b', 300, 560, 210, wall='brick', kind='step', rows=((400, 66), (560, 90)), seed=23)
    # stadhuis
    facade('stadhuis', [(560, 702), (1120, 702), (1120, 330), (980, 330), (980, 280), (940, 280), (940, 245), (740, 245), (740, 280), (700, 280), (700, 330), (560, 330)], d, M['stone_grey'], thick=5)
    for (yy, hh) in ((322, 12), (472, 8)):
        a, b = S2W(552, yy, d - 0.06), S2W(1128, yy + hh, d - 0.06)
        box('sh_lijst', ((a.x + b.x) / 2, d - 0.12, (a.z + b.z) / 2), (b.x - a.x, 0.3, a.z - b.z), M['trim'], col='town', bevel=0.01)
    roof('stadhuis_dak', M, M['slate'], [(552, 334), (1128, 334)], [(600, 250), (1080, 250)], d + 0.4, d + 2.6, hip=True)
    # toren
    dt = d + 1.2
    facade('toren', [(770, 330), (910, 330), (910, 112), (770, 112)], dt, M['stone_grey'], thick=2.4)
    a, b = S2W(762, 104, dt - 0.08), S2W(918, 116, dt - 0.08)
    box('toren_lijst', ((a.x + b.x) / 2, dt + 1.1, (a.z + b.z) / 2), (b.x - a.x, 2.6, a.z - b.z), M['trim'], col='town')
    tl, tr_ = S2W(770, 108, dt), S2W(910, 108, dt)
    apex = S2W(840, 12, dt + 1.2)
    base = [tl, tr_, Vector((tr_.x, tr_.y + 2.4, tr_.z)), Vector((tl.x, tl.y + 2.4, tl.z))]
    obj_from('spits', base + [apex], [(0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4), (3, 2, 1, 0)], M['slate'], col='town')
    ellipsoid('spits_bol', (apex.x, apex.y, apex.z + 0.12), (0.12, 0.12, 0.12), M['gold'], col='town')
    # klok (verlicht) met wijzers op ±8 uur 20
    c = S2W(840, 196, dt - 0.06)
    r_ = 36 / px(dt)
    lathe('klok_rand', (0, 0, 0), [(0, r_ + 0.07), (0.06, r_ + 0.07), (0.06, r_), (0, r_)], M['gold'], seg=40, col='town', cap=False).location = c
    bpy.data.objects['klok_rand'].rotation_euler = (math.pi / 2, 0, 0)
    face = ellipsoid('klok', c, (r_, 0.03, r_), emit('klokglas', '#fff0c8', 3.0), seg=32, rings=8, col='town')
    for ang, ln, wd in ((math.radians(-130), 0.55, 0.05), (math.radians(30), 0.8, 0.035)):
        p1 = c + Vector((math.sin(ang) * r_ * ln, -0.06, math.cos(ang) * r_ * ln))
        tube('wijzer', [c + Vector((0, -0.06, 0)), p1], [wd, wd * 0.7], M['iron'], seg=6, col='town')
    point_light('klokL', c + Vector((0, -0.5, 0)), '#ffe0a0', 40, radius=0.3)
    for k in range(2):
        window(M, 790 + k * 64, 250, 34, 44, dt, 1, 1, 2, power=10)
    # benedenverdieping: arcade van vijf bogen, deur in het midden
    for k, xx in enumerate((585, 690, 795, 900, 1005)):
        if k == 2:
            P = wpoly(ST.arch_pts(xx, 552, 80, 140, 1), d - 0.02)
            obj_from('stadhuis_deur', P, [tuple(range(len(P)))], M['door'], col='town', recalc=False)
            window(M, xx + 6, 556, 68, 40, d - 0.03, 1, 1, 1, sill=False)
        else:
            window(M, xx, 556, 80, 128, d, 1, 3, 3, power=26)
    for k in range(6):
        xx = 588 + k * 88
        window(M, xx, 392, 50, 70, d, 0, 2, 2, power=18)
        flowers(M, xx - 6, 470, 62, d, seed=40 + k)
    for i, (w_, h_) in enumerate(((240, 9), (200, 9), (160, 9))):
        a, b = S2W(840 - w_ / 2, 702 - i * 9 - 9, d - 0.3 - i * 0.3), S2W(840 + w_ / 2, 702 - i * 9, d - 0.3 - i * 0.3)
        box('trede', ((a.x + b.x) / 2, d - 0.5 - i * 0.3, (a.z + b.z) / 2 + 0.02), (b.x - a.x, 1.2 - i * 0.3, a.z - b.z + 0.04), M['trim'], col='town')
    for xs in (735, 945):        # vaandels
        P = wpoly([(xs, 344), (xs + 34, 344), (xs + 34, 470), (xs + 17, 452), (xs, 470)], d - 0.15)
        obj_from('vaandel', P, [tuple(range(5))], M['banner'], col='town', recalc=False).modifiers.new('s', 'SOLIDIFY').thickness = 0.01
        tube('vaandelstok', [S2W(xs - 6, 344, d - 0.16), S2W(xs + 40, 344, d - 0.16)], [0.02, 0.02], M['gold'], seg=6, col='town')
    house(M, 'oost_c', 1120, 1400, 200, wall='brick2', kind='neck', rows=((380, 70), (560, 90)), seed=27, shop=(1150, 560, 200, 120))
    house(M, 'oost_d', 1400, 1700, 300, wall='stone', kind='flat', eave=370, rows=((430, 64), (560, 90)), seed=29)
    filler(M, 1700, RIGHT_EDGE, 13)
    for L in ((420, 772, 455), (1270, 772, 455)):
        lamp(M, *L)
    barrel(M, 1480, 760, 58); barrel(M, 1530, 770, 66)
    gift(M, 1500, 705, 36, 24, M['gred'], d=ground_d(770))
    p = S2W(300, 760, ground_d(760))
    box('bank_o', (p.x, p.y, 0.32), (1.2, 0.35, 0.06), M['wood'], col='ground')
    box('bank_o2', (p.x, p.y + 0.16, 0.55), (1.2, 0.05, 0.32), M['wood'], col='ground')


# ------------------------------------------------------------------ ZUID: kade met de pakjesboot
BOAT = {}


def south_side(M):
    dq = -ST.QUAY_Y               # 10,56 m: kaderand (in dit kader voor de camera)
    dfar = -ST.FAR_QUAY_Y         # 19,5 m: overkant
    WATER_Z = -0.85
    stone = M['curb']
    # kademuren en water
    box('kade', (0, dq + 0.25, -0.45), (40, 0.5, 0.9), stone, col='ground')
    box('kade_rand', (0, dq + 0.05, 0.03), (40, 0.6, 0.1), M['trim'], col='ground', bevel=0.01)
    box('overkant_muur', (0, dfar - 0.25, -0.45), (40, 0.5, 0.9), stone, col='ground')
    wm, wb = None, None
    wm = bpy.data.materials.get('gracht')
    if wm is None:
        import bl_lib as L
        wm, wb = L.new_mat('gracht')
        wb.bsdf.inputs['Base Color'].default_value = hexlin('#0e1830')
        wb.bsdf.inputs['Roughness'].default_value = 0.04
        tc = wb.node('ShaderNodeTexCoord')
        nz = wb.node('ShaderNodeTexNoise', i_Scale=1.6, i_Detail=6.0)
        mp = wb.node('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (0.6, 2.5, 1)
        wb.link(tc.outputs['Object'], mp.inputs['Vector']); wb.link(mp.outputs[0], nz.inputs['Vector'])
        bp = wb.node('ShaderNodeBump', i_Strength=0.25, i_Distance=0.05)
        wb.link(nz.outputs['Fac'], bp.inputs['Height']); wb.link(bp.outputs['Normal'], wb.bsdf.inputs['Normal'])
    obj_from('water', [(-40, dq + 0.5, WATER_Z), (40, dq + 0.5, WATER_Z), (40, dfar - 0.5, WATER_Z), (-40, dfar - 0.5, WATER_Z)], [(0, 1, 2, 3)], wm, col='ground', recalc=False)
    # bolders
    for lat in (-8, -4.5, 4.5, 8):
        lathe('bolder', (lat, dq - 0.25, 0), [(0, 0.11), (0.25, 0.09), (0.3, 0.12), (0.34, 0.0)], M['iron'], seg=14, col='ground')
    # huizen aan de overkant (lager in beeld, verder weg)
    r = random.Random(5)
    lat = -15.0
    i = 0
    dh = dfar + 1.5
    base = 520 + 2.2 * px(dh)
    kinds = ['step', 'gable', 'neck', 'flat', 'step', 'gable', 'neck', 'flat']
    while lat < 15:
        wm_ = r.uniform(3.6, 4.6)
        x0 = 836 + lat * px(dh); x1 = 836 + (lat + wm_) * px(dh)
        hgt = r.uniform(7.0, 9.5)
        top = 520 - (hgt - 2.2) * px(dh)
        k = kinds[i % len(kinds)]
        house(M, 'overkant%d' % i, x0, x1, top, d=dh, wall=['brick', 'plaster', 'brick2', 'stone_grey'][i % 4], kind=k, base=base,
              rows=((base - 175, 40), (base - 110, 44), (base - 52, 46)), cols=2, seed=60 + i, power=3,
              eave=top + 46 if k == 'flat' else None)
        lat += wm_
        i += 1
    # verder langs de gracht (zichtbaar tijdens het draaien): eigen toeval, zodat de rij hierboven niet verandert
    r2 = random.Random(77)
    lat_end = lat
    for side in (-1, 1):
        lat = -15.0 if side < 0 else lat_end
        while abs(lat) < 34:
            wm_ = r2.uniform(3.6, 4.6)
            a_, b_ = (lat - wm_, lat) if side < 0 else (lat, lat + wm_)
            x0 = 836 + a_ * px(dh); x1 = 836 + b_ * px(dh)
            hgt = r2.uniform(7.0, 9.5)
            top = 520 - (hgt - 2.2) * px(dh)
            k = kinds[i % len(kinds)]
            house(M, 'overkant%d' % i, x0, x1, top, d=dh, wall=['brick', 'plaster', 'brick2', 'stone_grey'][i % 4], kind=k, base=base,
                  rows=((base - 175, 40), (base - 110, 44), (base - 52, 46)), cols=2, seed=60 + i, power=3,
                  eave=top + 46 if k == 'flat' else None)
            lat += side * wm_
            i += 1
    # de pakjesboot, aan de kade
    db = dq + 1.75
    boat(M, 0.0, db, WATER_Z)
    # lantaarns op de kade
    for (sx, bsy) in ((240, 790), (1430, 790)):
        lamp(M, sx, bsy, 470)
    BOAT.update({'dq': dq, 'db': db, 'deck': WATER_Z + 1.7})


def boat(M, cx, cy, wz):
    """Stoomboot met raderkast, kajuit, brug en pijp (zijaanzicht, boeg naar rechts)."""
    L_, B_, deck = 13.0, 3.0, wz + 1.7
    hull_dark = plain('romp', '#1a2238', 0.35)
    red = plain('boot_rood', '#b81e26', 0.4)
    white = plain('boot_wit', '#d6cdc0', 0.55)
    black = plain('boot_zwart', '#121214', 0.4)
    gold = M['gold']
    # romp: doorsneden langs de lengte, puntige boeg (rechts), ronde spiegel (links)
    n, segs = 26, 14
    V, F = [], []
    for i in range(n + 1):
        u = i / n * 2 - 1                                   # -1 achtersteven .. +1 boeg
        half = B_ / 2 * (max(0.0, 1 - max(0, u) ** 2.2) ** 0.5 if u > 0 else (1 - (max(0, -u - 0.75) / 0.25) ** 2) ** 0.5 if u < -0.75 else 1.0)
        half = max(half, 0.04)
        top = deck + 0.35 * max(0, u) ** 2                  # zeeg: boeg iets hoger
        for j in range(segs + 1):
            a = math.pi * j / segs                          # 0 = rechterboord-dek, π = linkerboord-dek
            yz = math.sin(a)
            yy = math.cos(a) * half
            zz = top - (top - (wz - 0.9)) * yz ** 1.6
            V.append((cx + u * L_ / 2, cy + yy, zz))
    for i in range(n):
        for j in range(segs):
            a = i * (segs + 1) + j
            b = (i + 1) * (segs + 1) + j
            F.append((a, b, b + 1, a + 1))
    me_hull = obj_from('romp', V, F, hull_dark, smooth=True, col='ground', recalc=True)
    # dek
    dV = []
    for i in range(n + 1):
        u = i / n * 2 - 1
        half = B_ / 2 * (max(0.0, 1 - max(0, u) ** 2.2) ** 0.5 if u > 0 else (1 - (max(0, -u - 0.75) / 0.25) ** 2) ** 0.5 if u < -0.75 else 1.0)
        top = deck + 0.35 * max(0, u) ** 2
        dV.append((cx + u * L_ / 2, cy - max(half, 0.04), top))
        dV.append((cx + u * L_ / 2, cy + max(half, 0.04), top))
    dF = [(2 * i, 2 * i + 2, 2 * i + 3, 2 * i + 1) for i in range(n)]
    obj_from('dek', dV, dF, M['wood'], col='ground', recalc=False)
    # rode band op de waterlijn + witte boeisel-rand
    box('waterlijn', (cx - 0.3, cy - B_ / 2 + 0.02, wz + 0.25), (L_ * 0.86, 0.04, 0.22), red, col='ground')
    box('boeisel', (cx - 0.3, cy - B_ / 2 + 0.02, deck - 0.15), (L_ * 0.86, 0.04, 0.12), gold, col='ground')
    # raderkast (halve schijf aan de zijkant)
    rk = []
    for k in range(17):
        a = math.pi * k / 16
        rk.append((cx - 0.8 + math.cos(a) * 1.5, cy - B_ / 2 - 0.25, deck - 0.2 + math.sin(a) * 1.5))
    obj_from('raderkast', rk, [tuple(range(17))], red, col='ground', recalc=False).modifiers.new('s', 'SOLIDIFY').thickness = 0.3
    for k in range(7):
        a = math.pi * (k + 0.5) / 7
        tube('spaak', [(cx - 0.8, cy - B_ / 2 - 0.42, deck - 0.2), (cx - 0.8 + math.cos(a) * 1.35, cy - B_ / 2 - 0.42, deck - 0.2 + math.sin(a) * 1.35)], [0.04, 0.04], gold, seg=6, col='ground')
    # kajuit met verlichte raampjes
    box('kajuit', (cx - 1.2, cy, deck + 0.75), (6.2, 1.9, 1.5), white, col='ground', bevel=0.03)
    box('kajuit_dak', (cx - 1.2, cy, deck + 1.55), (6.6, 2.2, 0.1), red, col='ground')
    for k in range(7):
        x = cx - 3.9 + k * 0.9
        ellipsoid('patrijspoort', (x, cy - 0.96, deck + 0.85), (0.17, 0.03, 0.17), emit('poortlicht', '#ffd98a', 6.0), seg=12, rings=6, col='ground')
    point_light('kajuitL', (cx - 1.2, cy - 1.6, deck + 0.9), '#ffb060', 140, radius=0.6)
    # stuurhuis
    box('stuurhuis', (cx + 2.6, cy, deck + 1.0), (1.6, 1.5, 2.0), white, col='ground', bevel=0.03)
    box('stuurhuis_dak', (cx + 2.6, cy, deck + 2.05), (1.9, 1.8, 0.1), red, col='ground')
    for k in range(2):
        box('stuurraam', (cx + 2.25 + k * 0.7, cy - 0.76, deck + 1.35), (0.5, 0.03, 0.55), emit('stuurlicht', '#ffd98a', 4.0), col='ground')
    # pijp
    lathe('pijp', (cx + 0.6, cy, deck + 1.6), [(0, 0.38), (2.2, 0.42)], red, seg=24, col='ground')
    lathe('pijp_top', (cx + 0.6, cy, deck + 3.8), [(0, 0.43), (0.5, 0.45), (0.55, 0.0)], black, seg=24, col='ground')
    # mast met vlaggenlijnen
    tube('mast', [(cx + 5.0, cy, deck + 0.2), (cx + 5.0, cy, deck + 5.6)], [0.06, 0.04], M['wood'], seg=8, col='ground')
    for (a, b, nflag) in (((cx + 6.4, cy, deck + 0.6), (cx + 5.0, cy, deck + 5.5), 6), ((cx + 5.0, cy, deck + 5.5), (cx - 6.2, cy, deck + 0.8), 13)):
        A, Bv = Vector(a), Vector(b)
        tube('vlaggenlijn', [A, Bv], [0.01, 0.01], M['iron'], seg=4, col='ground')
        for k in range(nflag):
            p0 = A.lerp(Bv, (k + 0.15) / nflag); p1 = A.lerp(Bv, (k + 0.75) / nflag)
            tip = (p0 + p1) / 2 + Vector((0, 0, -0.4))
            obj_from('bootvlag', [p0, p1, tip], [(0, 1, 2)], M['flag'][k % 5], col='ground', recalc=False).modifiers.new('s', 'SOLIDIFY').thickness = 0.004
    # reling
    for side in (-1, 1):
        pts = [(cx + u, cy + side * (B_ / 2 - 0.08), deck + 0.75) for u in (-6.0, -3, 0, 3, 5.8)]
        tube('reling', pts, [0.025] * 5, gold, seg=6, col='ground')
        for u in range(-6, 6):
            tube('relingpaal', [(cx + u, cy + side * (B_ / 2 - 0.08), deck), (cx + u, cy + side * (B_ / 2 - 0.08), deck + 0.75)], [0.02, 0.02], gold, seg=5, col='ground')
    # loopplank van het dek naar de kade
    g0 = Vector((cx - 3.3, cy - B_ / 2 + 0.2, deck + 0.02))
    g1 = Vector((cx - 3.3, cy - B_ / 2 - 1.55, 0.04))
    dirv = (g1 - g0)
    obj_from('loopplank', [g0 + Vector((-0.4, 0, 0)), g0 + Vector((0.4, 0, 0)), g1 + Vector((0.4, 0, 0)), g1 + Vector((-0.4, 0, 0))], [(0, 1, 2, 3)], M['wood'], col='ground', recalc=False).modifiers.new('s', 'SOLIDIFY').thickness = 0.05
    for sx_ in (-0.4, 0.4):
        tube('plankreling', [g0 + Vector((sx_, 0, 0.7)), g1 + Vector((sx_, 0, 0.7))], [0.02, 0.02], M['rope'], seg=5, col='ground')
    BOAT.update({'gang_top': (g0.x, g0.y, g0.z), 'gang_bot': (g1.x, g1.y, g1.z)})
    # rookpluim (kleine bollen, licht doorzichtig grijs)
    smoke = plain('rook', '#9aa0b0', 0.9)
    for k in range(6):
        ellipsoid('rook', (cx + 0.6 - k * 0.5, cy + k * 0.15, deck + 4.6 + k * 0.45), (0.35 + k * 0.12,) * 3, smoke, seg=12, rings=8, col='ground')


# ------------------------------------------------------------------ WEST: banketbakkerij + ladder
LADDER = {}


def west_side(M):
    d = D0
    filler(M, LEFT_EDGE, 140, 31)
    house(M, 'west_a', 140, 420, 190, wall='brick', kind='neck', rows=((380, 70), (560, 90)), seed=71)
    house(M, 'west_b', 420, 700, 300, wall='plaster', kind='flat', eave=360, roofmat='slate', rows=((420, 64), (560, 90)), seed=73)
    house(M, 'bakkerij', 700, 1020, 160, wall='stone', kind='step', rows=((340, 70), (440, 64)), seed=75, shop=(728, 560, 264, 128))
    awning(M, 715, 1005, 540, 598, d - 0.1, 'bakkerluifel')
    a, b = S2W(760, 486, d - 0.1), S2W(960, 524, d - 0.1)          # uithangbord
    box('bord', ((a.x + b.x) / 2, d - 0.12, (a.z + b.z) / 2), (b.x - a.x, 0.06, a.z - b.z), plain('bord', '#3a1a10', 0.5), col='town', bevel=0.01)
    box('bord_rand', ((a.x + b.x) / 2, d - 0.15, (a.z + b.z) / 2), (b.x - a.x - 0.06, 0.02, a.z - b.z - 0.06), M['gold'], col='town')
    house(M, 'west_c', 1020, 1300, 250, wall='brick2', kind='gable', rows=((400, 70), (560, 90)), seed=77)
    house(M, 'west_d', 1300, 1600, 320, wall='plaster', kind='flat', eave=380, rows=((440, 62), (560, 90)), seed=79)
    filler(M, 1600, RIGHT_EDGE, 33)
    # ladder tegen het raam van west_c (raam in het midden, eerste verdieping)
    win_c = (1020 + 1300) / 2
    top = S2W(win_c, 474, d - 0.1)
    bot = S2W(win_c, 702, d - 0.1) + Vector((0, -1.0, 0))
    bot.z = 0.0
    for sx_ in (-0.24, 0.24):
        tube('ladderboom', [bot + Vector((sx_, 0, 0)), top + Vector((sx_, 0, 0.4))], [0.035, 0.035], M['wood'], seg=8, col='ground')
    n = 9
    for k in range(1, n):
        p = bot.lerp(top + Vector((0, 0, 0.4)), k / n)
        tube('sport', [p + Vector((-0.24, 0, 0)), p + Vector((0.24, 0, 0))], [0.022, 0.022], M['wood'], seg=6, col='ground')
    LADDER.update({'bot': tuple(bot), 'top': tuple(top)})
    for L in ((560, 772, 455), (1420, 772, 455)):
        lamp(M, *L)
    # broodkratten en tonnen bij de bakker
    for k, x in enumerate((690, 1050)):
        p = S2W(x, 720, ground_d(720))
        box('krat', (p.x, p.y, 0.18), (0.6, 0.45, 0.36), M['wood'], col='ground', rot=(0, 0, 0.1 * k))
        for j in range(5):
            ellipsoid('brood', (p.x - 0.2 + j * 0.1, p.y, 0.4), (0.07, 0.16, 0.05), plain('brood', '#c88a3a', 0.6), seg=10, rings=6, col='ground')
    barrel(M, 260, 770, 64)


def corners_north(M):
    """Hoeken van de noordkant (links tot de rand, rechts vanaf huis D tot de rand)."""
    filler(M, LEFT_EDGE, 20, 41)
    filler(M, 1720, RIGHT_EDGE, 43)


def build_sides(M):
    corners_north(M)
    build_rotated(VIEW['east'], east_side, M)
    build_rotated(VIEW['south'], south_side, M)
    build_rotated(VIEW['west'], west_side, M)


def to_world(view, v):
    """Punt uit het kader van een kant (x lateraal, y diepte, z) naar wereld."""
    th = VIEW[view]
    c, s = math.cos(th), math.sin(th)
    return Vector((v[0] * c - v[1] * s, v[0] * s + v[1] * c, v[2]))

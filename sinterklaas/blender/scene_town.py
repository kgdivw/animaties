"""
Het decor in 3D, opgebouwd vanuit pixelposities van de template (zie bl_lib.S2W).
Elke functie bouwt één onderdeel; build_all() zet alles neer.
"""
import bpy, math, random
from mathutils import Vector
from bl_lib import (stonewall, cobble_inst, bark, plaster, planks, barrel_wood, S2W, ground_d, px, coll, obj_from, box, prism, lathe, tube, ellipsoid,
                    plain, brick, tiles, cobbles, window_glass, wood, leaf_mat, stripes, emit,
                    point_light, hexlin, TAU)

R = random.Random(7)

# ------------------------------------------------------------------ materialen
def mats():
    M = {}
    M['brick'] = brick('brick', '#8a3e28', '#6e2e1e', '#b8a08a', bw=0.22, rh=0.07, bump=0.3)
    M['brick2'] = brick('brick2', '#7a3a30', '#5e2a22', '#a89080', bw=0.22, rh=0.07, bump=0.3)
    M['stone'] = stonewall('stone', '#bca286', '#977b62', '#5e4c3e', sx=0.6, sz=0.3, bump=0.45)
    M['stone_grey'] = stonewall('stone_grey', '#bcb0ae', '#90827f', '#58494a', sx=0.48, sz=0.25, bump=0.45)
    M['stone_far'] = stonewall('stone_far', '#6a7694', '#4e5a78', '#2e364e', sx=0.32, sz=0.18, bump=0.3)
    M['trim'] = plain('trim', '#c8b49a', 0.7)
    M['trim_dark'] = plain('trim_dark', '#6a5040', 0.7)
    M['roof'] = tiles('roof', '#7a2c30', '#5c1e24')
    M['ridge'] = plain('ridge', '#5a1e22', 0.5)
    M['plaster'] = plaster('plaster', '#a88a6a')
    M['gutter'] = plain('gutter', '#3a2e2c', 0.4, metal=0.5)
    M['slate'] = tiles('slate', '#34405e', '#28324c', tw=0.14, th=0.09, rough=0.4)
    M['roof_far'] = tiles('roof_far', '#2a3452', '#222a44', tw=0.16, th=0.1)
    M['frame'] = plain('frame', '#3a2216', 0.6)
    M['frame_far'] = plain('frame_far', '#1c2236', 0.6)
    M['glass'] = window_glass('glass')
    M['glass_dim'] = window_glass('glass_dim', '#c87830', '#ffd890', 2.4)
    M['glass_shop'] = window_glass('glass_shop', '#f08a22', '#ffd890', 1.35, shop=True)
    M['door'] = wood('door', '#6a3416', '#3a1a0a', 14)
    M['wood'] = planks('wood')
    M['barrelwood'] = barrel_wood('barrelwood')
    M['burlap'] = brick('burlap', '#b8935a', '#a8844e', '#6e5232', bw=0.014, rh=0.012, mortar_size=0.003, bump=0.35, grime=0.25)
    M['rope'] = plain('rope_env', '#c89a3a', 0.6, metal=0.2)
    M['iron'] = plain('iron', '#16141a', 0.35, metal=0.6)
    M['lantern'] = emit('lantern', '#ffb050', 6.0)
    M['cobble'] = cobbles('cobble')
    M['cobble_i'] = cobble_inst('cobble_i')
    M['mortar'] = plain('mortar', '#1e161c', 0.35)
    M['curb'] = brick('curb', '#8a7470', '#7a6460', '#3a2c30', bw=0.6, rh=0.25, bump=0.3)
    M['fstone'] = brick('fstone', '#a08a86', '#8e7672', '#5a4a4c', bw=0.45, rh=0.2, mortar_size=0.01, bump=0.35)
    M['water'] = plain('water', '#1c2a44', 0.03)
    M['awning'] = stripes('awning', '#c8202a', '#f4ead8', width=0.155)
    M['gold'] = plain('gold_env', '#e7b445', 0.3, metal=0.9)
    M['bark'] = bark('bark')
    M['leaf'] = [leaf_mat('leaf%d' % i, c) for i, c in enumerate(['#f2a020', '#e8761a', '#d4501a', '#ffbe30', '#c4400e'])]
    M['flower_r'] = plain('flower_r', '#e8281e', 0.5)
    M['flower_y'] = plain('flower_y', '#ffc828', 0.5)
    M['flower_o'] = plain('flower_o', '#ff7a1a', 0.5)
    M['green'] = plain('green', '#2a5224', 0.7)
    M['planter'] = plain('planter', '#5a2e16', 0.7)
    for n, c in (('gred', '#c8202a'), ('gyel', '#f0b42a'), ('ggrn', '#2f7a46'), ('gpnk', '#d84a8a'), ('gora', '#e86a22')):
        M[n] = plain(n, c, 0.45)
    M['ribbon'] = plain('ribbon_env', '#f6c84a', 0.3, metal=0.3)
    M['sack'] = plain('sack_env', '#d6b47a', 0.85)
    M['flag'] = [plain('flag%d' % i, c, 0.7, sheen=0.4) for i, c in enumerate(['#d4302a', '#f2b632', '#e8781e', '#c62034', '#f6cc4a'])]
    M['banner'] = plain('banner', '#c8202a', 0.65, sheen=0.5)
    return M


# ------------------------------------------------------------------ hulpjes
def wpoly(pts_px, d):
    return [S2W(x, y, d) for (x, y) in pts_px]


def facade(name, pts_px, d, mat, thick=1.2, col='town'):
    P = wpoly(pts_px, d)
    return prism(name, [(p.x, p.z) for p in P], d, d + thick, mat, col=col)


def arch_pts(x, y, w, h, arch, n=10):
    """Raamomtrek in pixels (rechthoek of met ronde boog)."""
    if not arch:
        return [(x, y + h), (x + w, y + h), (x + w, y), (x, y)]
    ah = min(h * 0.5, w * 0.5 * arch)
    pts = [(x, y + h), (x + w, y + h), (x + w, y + ah)]
    for k in range(1, n):
        a = math.pi * k / n
        pts.append((x + w / 2 + math.cos(a) * w / 2, y + ah - math.sin(a) * ah))
    pts.append((x, y + ah))
    return pts


def window(M, x, y, w, h, d, arch=0, cols=2, rows=2, lit=1.0, far=False, light=True, col='town', sill=True, power=None, shop=None):
    """Raam op gevel (diepte d): glas, kozijn, roedes, vensterbank, lichtje ervoor."""
    pts = arch_pts(x, y, w, h, arch)
    dg = d - 0.012
    P = wpoly(pts, dg)
    x0 = min(p.x for p in P); x1 = max(p.x for p in P); z0 = min(p.z for p in P); z1 = max(p.z for p in P)
    uv = [((p.x - x0) / (x1 - x0), (p.z - z0) / (z1 - z0)) for p in P]
    if shop is None:
        shop = w >= 80 and not far
    gm_ = M['glass_shop'] if shop else (M['glass'] if lit > 0.5 else M['glass_dim'])
    obj_from('glass', P, [tuple(range(len(P)))], gm_, col=col, uv=uv, recalc=False)
    fr = M['frame_far'] if far else M['frame']
    rad = 0.035 * (w / 40) ** 0.3
    loop = [S2W(px_, py_, d - 0.03) for (px_, py_) in pts] + [S2W(pts[0][0], pts[0][1], d - 0.03)]
    tube('frame', loop, [rad] * len(loop), fr, seg=6, col=col)
    top = y + (min(h * 0.5, w * 0.5 * arch) if arch else 0)
    for i in range(1, cols):
        xx = x + w * i / cols
        a, b = S2W(xx, top if arch else y, d - 0.03), S2W(xx, y + h, d - 0.03)
        if arch:
            a = S2W(xx, y + (h * 0.15 if abs(i / cols - 0.5) < 0.01 else h * 0.3), d - 0.03)
        tube('mull', [a, b], [rad * 0.6] * 2, fr, seg=5, col=col)
    for j in range(1, rows):
        yy = top + (y + h - top) * j / rows
        tube('mull', [S2W(x, yy, d - 0.03), S2W(x + w, yy, d - 0.03)], [rad * 0.6] * 2, fr, seg=5, col=col)
    k = px(d)
    if arch and w >= 26:
        ah = min(h * 0.5, w * 0.5 * arch)
        cx, cy0 = x + w / 2, y + ah
        n = 9
        for i in range(n):
            a_ = math.pi * (i + 0.5) / n
            rr_ = w / 2 + 5
            pxp = (cx - math.cos(a_) * rr_, cy0 - math.sin(a_) * (ah + 5))
            c = S2W(pxp[0], pxp[1], d - 0.05)
            big = 1.35 if i == n // 2 else 1.0
            box('vous', c, (9 * big / k, 0.12, 10 * big / k), M['trim'], col=col, rot=(0, -(math.pi / 2 - a_), 0), bevel=0.008)
    elif w >= 26:
        a = S2W(x - 5, y - 9, d); b = S2W(x + w + 5, y - 1, d)
        box('lintel', ((a.x + b.x) / 2, d - 0.05, (a.z + b.z) / 2), (b.x - a.x, 0.12, a.z - b.z), M['trim'], col=col, bevel=0.008)
    if sill:
        a = S2W(x - 4, y + h + 2, d); b = S2W(x + w + 4, y + h + 6, d)
        box('sill', ((a.x + b.x) / 2, d - 0.06, (a.z + b.z) / 2), (b.x - a.x, 0.14, a.z - b.z), M['trim'], col=col)
    if light and lit > 0.3:
        c = S2W(x + w / 2, y + h * 0.55, d - 0.35)
        area = (x1 - x0) * (z1 - z0)
        point_light('winL', c, '#ffa850', (power or 22.0) * 5 * area * lit + 6, radius=0.25)


def flowers(M, x, y, w, d, col='town', seed=1):
    """Bloembak: bakje + bolletjes groen en bloemen (pixels: linkerbovenhoek van de bak)."""
    r = random.Random(seed)
    a = S2W(x, y, d - 0.05); b = S2W(x + w, y + 9, d - 0.05)
    box('fbox', ((a.x + b.x) / 2, d - 0.12, (a.z + b.z) / 2), (b.x - a.x, 0.18, a.z - b.z), M['planter'], col=col)
    k = px(d)
    for i in range(int(w / 1.4)):
        p = S2W(x + r.random() * w, y + 4 - r.random() * 13, d - 0.12 - r.random() * 0.14)
        rr = (2.4 + r.random() * 2.0) / k
        ellipsoid('leafb', p, (rr, rr, rr), M['green'], seg=6, rings=4, col=col)
    for i in range(int(w / 1.6)):
        p = S2W(x + r.random() * w, y - r.random() * 13, d - 0.2 - r.random() * 0.12)
        rr = (1.7 + r.random() * 1.7) / k
        m = [M['flower_r'], M['flower_y'], M['flower_o'], M['flower_r']][r.randrange(4)]
        ellipsoid('fl', p, (rr, rr, rr), m, seg=6, rings=4, col=col)


def roof(name, M, mat, eave_px, ridge_px, de, dr, col='town', hip=True, thick=0.08):
    """Dakvlak tussen goot (pixels, diepte de) en nok (pixels, diepte dr), met UV langs de helling."""
    el, er = S2W(eave_px[0][0], eave_px[0][1], de), S2W(eave_px[1][0], eave_px[1][1], de)
    rl, rr = S2W(ridge_px[0][0], ridge_px[0][1], dr), S2W(ridge_px[1][0], ridge_px[1][1], dr)
    slope = (rl - el).length
    V = [el, er, rr, rl]
    uv = [(el.x, 0), (er.x, 0), (rr.x, slope), (rl.x, slope)]
    o = obj_from(name, V, [(0, 1, 2, 3)], mat, col=col, uv=uv, recalc=False)
    sol = o.modifiers.new('sol', 'SOLIDIFY'); sol.thickness = thick
    if hip:
        for (e, r_) in ((el, rl), (er, rr)):
            back = Vector((e.x, r_.y + (r_.y - e.y), e.z))
            Vh = [e, r_, back]
            sl = (r_ - e).length
            o2 = obj_from(name + '_hip', Vh, [(0, 1, 2)], mat, col=col, uv=[(e.y, 0), (r_.y, sl), (back.y, 0)], recalc=False)
            s2 = o2.modifiers.new('sol', 'SOLIDIFY'); s2.thickness = thick
    return el, er, rl, rr


# ------------------------------------------------------------------ grond
def _sock(node, name, typ=None, out=False):
    for s in (node.outputs if out else node.inputs):
        if s.name == name and (typ is None or s.type == typ) and s.enabled:
            return s
    for s in (node.outputs if out else node.inputs):
        if s.name == name and (typ is None or s.type == typ):
            return s
    raise KeyError(name)


def cobble_field(M, fountain_xy):
    """Kinderkopjes als losse, bolle stenen via geometry nodes (instanties)."""
    V, F = [], []
    seg, rings, e1, e2 = 20, 10, 0.35, 0.55
    sp = lambda v, e: math.copysign(abs(v) ** e, v)
    V.append((0, 0, 0.034))
    for i in range(1, rings):
        t = math.pi / 2 * i / rings            # alleen de bovenhelft + vlakke onderkant
        for j in range(seg):
            p = TAU * j / seg
            ct, st_ = sp(math.cos(t), e1), sp(math.sin(t), e1)
            V.append((0.112 * st_ * sp(math.cos(p), e2), 0.076 * st_ * sp(math.sin(p), e2), 0.034 * ct))
    for j in range(seg):
        F.append((0, 1 + j, 1 + (j + 1) % seg))
    for i in range(rings - 2):
        a, b = 1 + i * seg, 1 + (i + 1) * seg
        for j in range(seg):
            j1 = (j + 1) % seg
            F.append((a + j, b + j, b + j1, a + j1))
    src = obj_from('cobble_src', V, F, M['cobble_i'], smooth=True, col='src')
    host = obj_from('cobble_host', [(-1, -1, 0), (1, -1, 0), (1, 1, 0), (-1, 1, 0)], [(0, 1, 2, 3)], None, col='ground', recalc=False)
    ng = bpy.data.node_groups.new('cobbles', 'GeometryNodeTree')
    ng.interface.new_socket('Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
    ng.interface.new_socket('Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    N = ng.nodes; Lk = ng.links
    gout = N.new('NodeGroupOutput')
    grid = N.new('GeometryNodeMeshGrid')
    grid.inputs['Size X'].default_value = 30; grid.inputs['Size Y'].default_value = 25.0     # hele plein, tot de kade in het zuiden
    grid.inputs['Vertices X'].default_value = 128; grid.inputs['Vertices Y'].default_value = 152
    tr = N.new('GeometryNodeTransform'); tr.inputs['Translation'].default_value = (0, 2.1, 0.0)
    Lk.new(grid.outputs['Mesh'], tr.inputs['Geometry'])
    m2p = N.new('GeometryNodeMeshToPoints'); Lk.new(tr.outputs['Geometry'], m2p.inputs['Mesh'])
    # om de rij een halve steen verspringen
    pos = N.new('GeometryNodeInputPosition')
    sepp = N.new('ShaderNodeSeparateXYZ'); Lk.new(pos.outputs[0], sepp.inputs[0])
    dv = N.new('ShaderNodeMath'); dv.operation = 'DIVIDE'; dv.inputs[1].default_value = 25.0 / 151
    Lk.new(sepp.outputs['Y'], dv.inputs[0])
    rd = N.new('ShaderNodeMath'); rd.operation = 'ROUND'; Lk.new(dv.outputs[0], rd.inputs[0])
    md = N.new('ShaderNodeMath'); md.operation = 'MODULO'; md.inputs[1].default_value = 2.0; Lk.new(rd.outputs[0], md.inputs[0])
    sh = N.new('ShaderNodeMath'); sh.operation = 'MULTIPLY'; sh.inputs[1].default_value = 30 / 127 * 0.5; Lk.new(md.outputs[0], sh.inputs[0])
    cmb = N.new('ShaderNodeCombineXYZ'); Lk.new(sh.outputs[0], cmb.inputs['X'])
    rv = N.new('FunctionNodeRandomValue'); rv.data_type = 'FLOAT_VECTOR'
    _sock(rv, 'Min', 'VECTOR').default_value = (-0.035, -0.022, 0.0)
    _sock(rv, 'Max', 'VECTOR').default_value = (0.035, 0.022, 0.014)
    addv = N.new('ShaderNodeVectorMath'); addv.operation = 'ADD'
    Lk.new(cmb.outputs[0], addv.inputs[0]); Lk.new(_sock(rv, 'Value', 'VECTOR', out=True), addv.inputs[1])
    setp = N.new('GeometryNodeSetPosition'); Lk.new(m2p.outputs['Points'], setp.inputs['Geometry']); Lk.new(addv.outputs[0], setp.inputs['Offset'])
    # niet onder de fontein
    dist = N.new('ShaderNodeVectorMath'); dist.operation = 'DISTANCE'
    pos2 = N.new('GeometryNodeInputPosition'); Lk.new(pos2.outputs[0], dist.inputs[0]); dist.inputs[1].default_value = (fountain_xy[0], fountain_xy[1], 0)
    cmpn = N.new('FunctionNodeCompare'); cmpn.data_type = 'FLOAT'; cmpn.operation = 'LESS_THAN'
    Lk.new(_sock(dist, 'Value', out=True), cmpn.inputs[0]); cmpn.inputs[1].default_value = 1.75
    dele = N.new('GeometryNodeDeleteGeometry'); dele.domain = 'POINT'
    Lk.new(setp.outputs['Geometry'], dele.inputs['Geometry']); Lk.new(cmpn.outputs['Result'], dele.inputs['Selection'])
    oi = N.new('GeometryNodeObjectInfo'); oi.inputs['Object'].default_value = src
    iop = N.new('GeometryNodeInstanceOnPoints')
    Lk.new(dele.outputs['Geometry'], iop.inputs['Points']); Lk.new(oi.outputs['Geometry'], iop.inputs['Instance'])
    rr = N.new('FunctionNodeRandomValue'); rr.data_type = 'FLOAT_VECTOR'
    _sock(rr, 'Min', 'VECTOR').default_value = (-0.05, -0.05, -0.12); _sock(rr, 'Max', 'VECTOR').default_value = (0.05, 0.05, 0.12)
    _sock(rr, 'Seed', 'INT').default_value = 3
    try:
        e2r = N.new('FunctionNodeEulerToRotation')
        Lk.new(_sock(rr, 'Value', 'VECTOR', out=True), e2r.inputs[0]); Lk.new(e2r.outputs[0], iop.inputs['Rotation'])
    except Exception:
        Lk.new(_sock(rr, 'Value', 'VECTOR', out=True), iop.inputs['Rotation'])
    rs = N.new('FunctionNodeRandomValue'); rs.data_type = 'FLOAT_VECTOR'
    _sock(rs, 'Min', 'VECTOR').default_value = (0.9, 0.88, 0.8); _sock(rs, 'Max', 'VECTOR').default_value = (1.08, 1.06, 1.3)
    _sock(rs, 'Seed', 'INT').default_value = 9
    Lk.new(_sock(rs, 'Value', 'VECTOR', out=True), iop.inputs['Scale'])
    Lk.new(iop.outputs['Instances'], gout.inputs[0])
    mod = host.modifiers.new('cobbles', 'NODES'); mod.node_group = ng
    src.hide_render = True; src.hide_viewport = True
    return host


QUAY_Y = -10.56          # rand van het plein aan de grachtkant (wereld-y)
FAR_QUAY_Y = -19.5      # overkant van de gracht


def ground(M):
    # plein + noordkant; in het zuiden houdt het op bij de kade (gracht ertussen, overkant verder weg)
    V = [(-40, QUAY_Y, 0), (40, QUAY_Y, 0), (40, 80, 0), (-40, 80, 0)]
    obj_from('square', V, [(0, 1, 2, 3)], M['mortar'], col='ground', recalc=False)
    V = [(-40, -60, 0), (40, -60, 0), (40, FAR_QUAY_Y, 0), (-40, FAR_QUAY_Y, 0)]
    obj_from('farbank', V, [(0, 1, 2, 3)], M['curb'], col='ground', recalc=False)
    # stoeprand langs de gevels
    d = ground_d(702)
    box('curb', (1, d - 0.25, 0.04), (40, 0.5, 0.08), M['curb'], col='ground')


# ------------------------------------------------------------------ middengebouw
def main_building(M):
    d = ground_d(702)                         # ≈ 14.5 m
    # gevel + plint + kroonlijst
    facade('main_facade', [(552, 702), (1384, 702), (1384, 476), (552, 476)], d, M['stone'], thick=3.0)
    a, b = S2W(548, 470, d - 0.08), S2W(1388, 490, d - 0.08)
    box('cornice', ((a.x + b.x) / 2, d - 0.1, (a.z + b.z) / 2), (b.x - a.x, 0.35, a.z - b.z), M['trim'], col='town', bevel=0.02)
    a, b = S2W(552, 688, d), S2W(1384, 702, d)
    box('plinth', ((a.x + b.x) / 2, d - 0.04, (a.z + b.z) / 2), (b.x - a.x, 0.12, a.z - b.z), M['trim_dark'], col='town')
    # dak (schilddak)
    dr = d + 1.15
    roof('main_roof', M, M['roof'], [(536, 476), (1394, 476)], [(580, 297), (1370, 292)], d - 0.25, dr)
    r0, r1 = S2W(580, 296, dr), S2W(1370, 291, dr)
    tube('ridgecap', [r0, r1], [0.075, 0.075], M['ridge'], seg=10, col='town')
    for k in range(34):                                    # nokpannen: kleine ronde kapjes
        p = r0.lerp(r1, (k + 0.5) / 34)
        ellipsoid('ridgetile', (p.x, p.y, p.z + 0.02), (0.13, 0.09, 0.075), M['ridge'], seg=10, rings=6, col='town')
    g0, g1 = S2W(536, 478, d - 0.32), S2W(1394, 478, d - 0.32)
    tube('gutter', [g0, g1], [0.045, 0.045], M['gutter'], seg=8, col='town')
    # dakkapellen: [midden x, top y, goot y, halve breedte px, raam]
    dorms = [(642, 336, 412, 64, (620, 402, 46, 56, 0, 2, 2)), (790, 300, 390, 82, (764, 366, 52, 62, 0, 2, 3)),
             (935, 378, 442, 66, (915, 428, 40, 38, 0, 2, 2)), (1143, 290, 438, 136, (1114, 368, 60, 76, 0, 2, 3))]
    for i, (cx, top, eave, hw, wn) in enumerate(dorms):
        dd = d - 0.2
        wall = [(cx - hw * 0.8, 478), (cx - hw * 0.8, eave), (cx, top + 10), (cx + hw * 0.8, eave), (cx + hw * 0.8, 478)]
        facade('dormer%d' % i, wall, dd, M['plaster'], thick=1.4)
        # dakje
        apex = S2W(cx, top, dd - 0.1)
        for sgn in (-1, 1):
            e = S2W(cx + sgn * (hw + 8), eave + 6, dd - 0.1)
            V = [apex, e, Vector((e.x, e.y + 1.6, e.z)), Vector((apex.x, apex.y + 1.6, apex.z))]
            sl = (e - apex).length
            o = obj_from('dormroof', V, [(0, 1, 2, 3)], M['roof'], col='town', uv=[(0, 0), (sl, 0), (sl, 1.6), (0, 1.6)], recalc=False)
            o.modifiers.new('s', 'SOLIDIFY').thickness = 0.07
            tube('barge', [apex, e], [0.035, 0.035], M['frame'], seg=6, col='town')
        x, y, w, h, ar, c_, r_ = wn
        window(M, x, y, w, h, dd, ar, c_, r_)
    flowers(M, 758, 438, 64, d - 0.2, seed=21)
    flowers(M, 1104, 452, 80, d - 0.2, seed=22)
    # schoorstenen (rechter apart: daar kruipen Pieten in)
    for nm, x0, x1 in (('chimL', 626, 710), ('chimR', 1192, 1276)):
        dc = d + 0.7
        a, b = S2W(x0, 228, dc), S2W(x1, 330, dc)
        c = 'town' if nm == 'chimL' else 'chimney'
        box(nm, ((a.x + b.x) / 2, dc + 0.3, (a.z + b.z) / 2), (b.x - a.x, 0.6, a.z - b.z), M['brick'], col=c)
        a2, b2 = S2W(x0 - 6, 220, dc - 0.05), S2W(x1 + 6, 230, dc - 0.05)
        box(nm + '_cap', ((a2.x + b2.x) / 2, dc + 0.3, (a2.z + b2.z) / 2), (b2.x - a2.x, 0.7, a2.z - b2.z), M['trim'], col=c)
        for k in range(2):
            pxx = x0 + 22 + k * 30
            a3, b3 = S2W(pxx, 196, dc), S2W(pxx + 15, 222, dc)
            lathe(nm + '_pot', ((a3.x + b3.x) / 2, dc + 0.3, b3.z), [(0, 0.09), (a3.z - b3.z, 0.08), (a3.z - b3.z + 0.02, 0.1)], M['brick2'], seg=12, col=c)
    # ramen benedenverdieping
    window(M, 590, 530, 82, 112, d, 1, 3, 3, power=30)
    window(M, 722, 520, 112, 122, d, 1, 4, 3, power=30)
    window(M, 1072, 534, 56, 90, d, 0, 2, 3)
    window(M, 1158, 534, 56, 90, d, 0, 2, 3)
    window(M, 1292, 556, 84, 126, d, 1, 3, 3, power=30)
    window(M, 902, 526, 60, 34, d - 0.02, 1, 1, 1, sill=False)
    window(M, 1218, 410, 26, 34, d - 0.2, 0, 1, 2)
    window(M, 1048, 410, 26, 34, d - 0.2, 0, 1, 2)
    # deur
    P = wpoly(arch_pts(900, 556, 64, 120, 0) , d - 0.02)
    obj_from('door', P, [tuple(range(4))], M['door'], col='town', recalc=False)
    for x in (906, 958):
        tube('doorring', [S2W(x, 622, d - 0.06), S2W(x + 1, 622, d - 0.07)], [0.03, 0.03], M['gold'], seg=8, col='town')
    a, b = S2W(880, 676, d), S2W(984, 684, d)
    box('step1', ((a.x + b.x) / 2, d - 0.3, 0.06), (b.x - a.x, 0.6, 0.12), M['trim'], col='town')
    # bloembakken
    for (x, y, w, sd) in ((584, 650, 94, 31), (712, 650, 132, 32), (1064, 634, 72, 33), (1150, 634, 72, 34)):
        flowers(M, x, y, w, d, seed=sd)
    # muurlampen
    for x in (862, 1004):
        c = S2W(x, 540, d - 0.25)
        box('wl', c, (0.16, 0.16, 0.24), M['lantern'], col='town')
        box('wlcap', (c.x, c.y, c.z + 0.15), (0.24, 0.24, 0.06), M['iron'], col='town')
        point_light('walllamp', (c.x, c.y - 0.15, c.z), '#ffb060', 25, radius=0.08)
    # plantenbak, bank, tonnetjes
    p = S2W(744, 700, d - 0.4)
    box('planter_big', (p.x, p.y, 0.25), (0.75, 0.5, 0.5), M['fstone'], col='town')
    flowers(M, 714, 656, 62, d - 0.6, seed=35)
    p = S2W(820, 700, d - 0.4)
    box('bench_seat', (p.x, p.y, 0.32), (0.7, 0.3, 0.05), M['wood'], col='town')
    box('bench_back', (p.x, p.y + 0.14, 0.52), (0.7, 0.04, 0.3), M['wood'], col='town')
    for (x, w) in ((1150, 30), (1182, 30)):
        barrel(M, x + w / 2, 702, w, d - 0.3, col='town')


# ------------------------------------------------------------------ linkerhuizen
def left_houses(M):
    d = ground_d(702) - 0.4
    # huis A (baksteen)
    facade('houseA', [(20, 702), (302, 702), (302, 336), (20, 336)], d, M['brick'], thick=4)
    roof('roofA', M, M['roof'], [(10, 342), (308, 342)], [(40, 205), (255, 212)], d - 0.2, d + 1.2)
    for args in ((104, 360, 46, 76, 0, 2, 3), (222, 374, 36, 64, 0, 2, 3), (52, 372, 26, 60, 0, 1, 3),
                 (60, 500, 56, 90, 0, 3, 3), (230, 500, 50, 90, 0, 2, 3)):
        window(M, *args[:4], d, args[4], args[5], args[6])
    flowers(M, 96, 442, 62, d, seed=4); flowers(M, 216, 444, 48, d, seed=5)
    # dakkapel A
    facade('dormA', [(183, 340), (183, 284), (203, 266), (223, 284), (223, 340)], d + 0.3, M['brick2'], thick=1.0)
    window(M, 190, 284, 26, 26, d + 0.28, 0, 2, 1, sill=False)
    # huis S: trapgevel
    ds = d - 0.1
    sx0, sx1, apx = 286, 422, 352
    G = [(sx0, 702), (sx0, 318)]
    steps, stw, sth = 4, (apx - 14 - sx0) / 4, (318 - 196) / 4
    for i in range(steps):
        G += [(sx0 + i * stw, 318 - (i + 1) * sth), (sx0 + (i + 1) * stw, 318 - (i + 1) * sth)]
    G += [(apx - 14, 182), (apx + 14, 182)]
    for i in range(steps - 1, -1, -1):
        G += [(sx1 - (i + 1) * stw, 318 - (i + 1) * sth), (sx1 - i * stw, 318 - (i + 1) * sth)]
    G += [(sx1, 318), (sx1, 702)]
    facade('houseS', G, ds, M['stone_grey'], thick=4)
    for i in range(steps):
        for xx in (sx0 + i * stw, sx1 - (i + 1) * stw):
            a, b = S2W(xx - 2, 318 - (i + 1) * sth - 4, ds - 0.03), S2W(xx + stw + 2, 318 - (i + 1) * sth + 1, ds - 0.03)
            box('cope', ((a.x + b.x) / 2, ds + 0.4, (a.z + b.z) / 2), (b.x - a.x, 0.9, a.z - b.z), M['trim'], col='town')
    a, b = S2W(332, 164, ds + 0.3), S2W(372, 186, ds + 0.3)
    box('chimS', ((a.x + b.x) / 2, ds + 0.5, (a.z + b.z) / 2), (b.x - a.x, 0.5, a.z - b.z), M['brick2'], col='town')
    for args in ((338, 248, 30, 68, 1, 2, 2), (306, 384, 32, 56, 1, 2, 2), (366, 388, 32, 56, 1, 2, 2),
                 (300, 520, 40, 90, 1, 2, 3), (362, 524, 40, 86, 1, 2, 3)):
        window(M, *args[:4], ds, args[4], args[5], args[6])
    flowers(M, 330, 324, 46, ds, seed=8); flowers(M, 300, 448, 44, ds, seed=12); flowers(M, 360, 452, 46, ds, seed=13)
    for yy in (466, 356):
        a, b = S2W(sx0, yy, ds), S2W(sx1, yy + 6, ds)
        box('band', ((a.x + b.x) / 2, ds - 0.04, (a.z + b.z) / 2), (b.x - a.x, 0.1, a.z - b.z), M['trim'], col='town')


# ------------------------------------------------------------------ verre huizen
def far_houses(M):
    d = ground_d(668)
    facade('farF1', [(408, 668), (540, 668), (540, 300), (465, 212), (408, 298)], d, M['stone_far'], thick=3, col='back')
    roofl = [S2W(398, 312, d - 0.1), S2W(465, 206, d - 0.1)]
    tube('farridge', [S2W(396, 314, d - 0.15), S2W(465, 205, d - 0.15), S2W(550, 314, d - 0.15)], [0.12] * 3, M['roof_far'], seg=6, col='back')
    a, b = S2W(457, 196, d + 0.3), S2W(473, 228, d + 0.3)
    box('farchim', ((a.x + b.x) / 2, d + 0.3, (a.z + b.z) / 2), (b.x - a.x, 0.4, a.z - b.z), M['stone_far'], col='back')
    for args in ((450, 292, 28, 34, 1), (498, 378, 30, 46, 0), (432, 378, 28, 46, 0), (452, 572, 34, 66, 1), (506, 572, 34, 66, 1), (440, 470, 26, 40, 0), (496, 470, 26, 40, 0)):
        window(M, *args[:4], d, args[4], 2, 2, far=True, col='back', power=14)
    # daken erachter
    d2 = d + 4
    facade('farback', [(400, 340), (440, 250), (500, 238), (575, 236), (580, 340)], d2, M['roof_far'], thick=2, col='back')
    for x0, x1 in ((512, 530), (552, 570)):
        a, b = S2W(x0, 238, d2 - 0.1), S2W(x1, 300, d2 - 0.1)
        box('farchim2', ((a.x + b.x) / 2, d2, (a.z + b.z) / 2), (b.x - a.x, 0.4, a.z - b.z), M['stone_far'], col='back')
    # rechts achter (boven het dak uit)
    d3 = ground_d(702) + 9
    facade('farR', [(1290, 360), (1300, 270), (1350, 250), (1395, 262), (1400, 360)], d3, M['roof_far'], thick=2, col='back')
    for x0, x1, y0 in ((1306, 1330, 236), (1364, 1384, 232)):
        a, b = S2W(x0, y0, d3 - 0.1), S2W(x1, 320, d3 - 0.1)
        box('farchim3', ((a.x + b.x) / 2, d3, (a.z + b.z) / 2), (b.x - a.x, 0.4, a.z - b.z), M['stone_far'], col='back')


# ------------------------------------------------------------------ rechterhuizen
def right_houses(M):
    d = ground_d(702) - 0.6
    facade('houseC', [(1380, 702), (1528, 702), (1528, 330), (1380, 330)], d, M['stone_grey'], thick=4)
    gv = [(1392, 342), (1455, 268), (1520, 340)]
    facade('houseC_gable', gv, d, M['stone_grey'], thick=4)
    apex = S2W(1455, 238, d - 0.2)
    for sgn, ex in ((-1, 1366), (1, 1542)):
        e = S2W(ex, 340, d - 0.2)
        V = [apex, e, Vector((e.x, e.y + 4, e.z)), Vector((apex.x, apex.y + 4, apex.z))]
        sl = (e - apex).length
        o = obj_from('roofC', V, [(0, 1, 2, 3)], M['slate'], col='town', uv=[(0, 0), (sl, 0), (sl, 4), (0, 4)], recalc=False)
        o.modifiers.new('s', 'SOLIDIFY').thickness = 0.09
    a, b = S2W(1446, 156, d + 0.6), S2W(1500, 280, d + 0.6)
    box('chimC', ((a.x + b.x) / 2, d + 0.8, (a.z + b.z) / 2), (b.x - a.x, 0.6, a.z - b.z), M['brick2'], col='town')
    a, b = S2W(1440, 150, d + 0.55), S2W(1506, 160, d + 0.55)
    box('chimC_cap', ((a.x + b.x) / 2, d + 0.8, (a.z + b.z) / 2), (b.x - a.x, 0.7, a.z - b.z), M['trim'], col='town')
    for args in ((1442, 292, 28, 44, 1, 2, 2), (1414, 392, 32, 64, 0, 2, 3), (1478, 390, 32, 64, 0, 2, 3), (1388, 596, 130, 92, 0, 4, 2)):
        window(M, *args[:4], d, args[4], args[5], args[6])
    flowers(M, 1400, 466, 58, d, seed=41); flowers(M, 1470, 462, 54, d, seed=42)
    # huis D: hoge trapgevel van baksteen
    dd = d - 0.3
    x0, x1, apx = 1520, 1720, 1602
    G = [(x0, 702), (x0, 330)]
    steps, stw, sth = 5, (apx - 22 - x0) / 5, (330 - 92) / 5
    for i in range(steps):
        G += [(x0 + i * stw, 330 - (i + 1) * sth), (x0 + (i + 1) * stw, 330 - (i + 1) * sth)]
    G += [(apx - 22, 72), (apx + 22, 72)]
    for j in range(steps):
        G += [(apx + 22 + j * stw, 92 + j * sth), (apx + 22 + (j + 1) * stw, 92 + j * sth)]
    G += [(x1, 330), (x1, 702)]
    facade('houseD', G, dd, M['brick'], thick=4)
    for i in range(steps):
        for xx in (x0 + i * stw,):
            a, b = S2W(xx - 2, 330 - (i + 1) * sth - 4, dd - 0.03), S2W(xx + stw + 2, 330 - (i + 1) * sth + 2, dd - 0.03)
            box('copeD', ((a.x + b.x) / 2, dd + 0.4, (a.z + b.z) / 2), (b.x - a.x, 0.9, a.z - b.z), M['trim'], col='town')
    for yy, hh in ((300, 7), (486, 9)):
        a, b = S2W(x0, yy, dd), S2W(x1, yy + hh, dd)
        box('bandD', ((a.x + b.x) / 2, dd - 0.05, (a.z + b.z) / 2), (b.x - a.x, 0.12, a.z - b.z), M['trim'], col='town')
    for args in ((1584, 196, 40, 80, 1, 2, 3), (1560, 334, 40, 82, 1, 2, 3), (1632, 334, 40, 82, 1, 2, 3), (1562, 514, 120, 166, 1, 3, 4), (1600, 130, 24, 34, 1, 1, 1)):
        window(M, *args[:4], dd, args[4], args[5], args[6], power=26)
    flowers(M, 1574, 284, 60, dd, seed=51); flowers(M, 1546, 428, 130, dd, seed=52)


# ------------------------------------------------------------------ fontein
def fountain(M):
    cx_px, base_sy = 988, 760
    d = ground_d(base_sy)
    c = S2W(cx_px, base_sy, d)
    cx, cy = c.x, d
    k = px(d)
    R1 = 188 / k; R2 = 132 / k
    lathe('f_step', (cx, cy, 0), [(0, R1), (0.14, R1), (0.16, R1 - 0.05)], M['fstone'], seg=64, col='ground')
    lathe('f_basin', (cx, cy, 0), [(0.1, R2 + 0.02), (0.5, R2), (0.56, R2 + 0.06), (0.62, R2 + 0.04), (0.62, R2 - 0.12), (0.45, R2 - 0.14)], M['fstone'], seg=64, col='ground', cap=False)
    obj_from('f_water', [(cx + math.cos(a) * (R2 - 0.1), cy + math.sin(a) * (R2 - 0.1), 0.5) for a in [TAU * i / 48 for i in range(48)]], [tuple(range(48))], M['water'], col='ground', recalc=False)
    def z_of(sy):
        return S2W(cx_px, sy, d).z
    lathe('f_column', (cx, cy, 0.45), [(0, 0.2), (0.15, 0.13), (z_of(646) - 0.45, 0.1), (z_of(640) - 0.45, 0.12)], M['fstone'], seg=24, col='ground')
    b1 = z_of(640)
    lathe('f_bowl1', (cx, cy, b1), [(-0.16, 0.08), (-0.1, 0.3), (0, 54 / k), (0.03, 54 / k), (0.03, 54 / k - 0.05), (-0.06, 0.2)], M['fstone'], seg=40, col='ground')
    b2 = z_of(604)
    lathe('f_col2', (cx, cy, b1), [(0, 0.08), (b2 - b1, 0.06)], M['fstone'], seg=16, col='ground')
    lathe('f_bowl2', (cx, cy, b2), [(-0.1, 0.05), (-0.06, 0.18), (0, 32 / k), (0.025, 32 / k), (0.025, 32 / k - 0.04), (-0.04, 0.12)], M['fstone'], seg=32, col='ground')
    lathe('f_top', (cx, cy, b2), [(0, 0.05), (0.12, 0.06), (0.18, 0.03), (0.22, 0.05), (0.25, 0.0)], M['fstone'], seg=16, col='ground')
    return (cx, cy)


# ------------------------------------------------------------------ props
def barrel(M, sx, base_sy, w_px, d=None, col='ground', h_ratio=1.45):
    d = d or ground_d(base_sy)
    c = S2W(sx, base_sy, d)
    r = w_px / px(d) / 2
    h = r * 2 * h_ratio
    prof = [(0, r * 0.88), (h * 0.12, r * 0.95), (h * 0.5, r), (h * 0.88, r * 0.95), (h, r * 0.88)]
    lathe('barrel', (c.x, d, 0), prof, M['barrelwood'], seg=32, col=col)
    for f in (0.1, 0.3, 0.7, 0.9):
        rr = [p for p in prof][0][1]
        z = h * f
        rad = r * (0.9 + 0.1 * math.sin(math.pi * f)) + 0.006
        lathe('hoop', (c.x, d, z - 0.015), [(0, rad), (0.03, rad)], M['iron'], seg=28, col=col, cap=False)
    return c.x, d, h


def gift(M, sx, base_sy, w_px, h_px, mat, d=None, col='ground', rot=0.0, z0=0.0):
    d = d or ground_d(base_sy)
    c = S2W(sx, base_sy, d)
    k = px(d)
    w, h = w_px / k, h_px / k
    box('gift', (c.x, d, z0 + h / 2), (w, w * 0.8, h), mat, col=col, rot=(0, 0, rot))
    box('rib', (c.x, d, z0 + h / 2), (w * 0.16, w * 0.82, h + 0.004), M['ribbon'], col=col, rot=(0, 0, rot))
    box('rib', (c.x, d, z0 + h / 2), (w + 0.004, w * 0.14, h + 0.004), M['ribbon'], col=col, rot=(0, 0, rot))
    ellipsoid('bow', (c.x - w * 0.12, d, z0 + h + 0.03), (w * 0.14, w * 0.06, 0.035), M['ribbon'], seg=10, rings=6, col=col)
    ellipsoid('bow', (c.x + w * 0.12, d, z0 + h + 0.03), (w * 0.14, w * 0.06, 0.035), M['ribbon'], seg=10, rings=6, col=col)


def lamp(M, sx, base_sy, top_sy, col='ground'):
    d = ground_d(base_sy)
    c = S2W(sx, base_sy, d)
    top = S2W(sx, top_sy, d).z
    s = (top) / 3.0
    lathe('lamp_base', (c.x, d, 0), [(0, 0.2 * s), (0.08 * s, 0.17 * s), (0.25 * s, 0.09 * s), (0.6 * s, 0.07 * s)], M['iron'], seg=20, col=col)
    lathe('lamp_post', (c.x, d, 0.6 * s), [(0, 0.055 * s), (top - 0.95 * s, 0.045 * s)], M['iron'], seg=16, col=col)
    for f in (0.9 * s, 1.5 * s):
        lathe('lamp_ring', (c.x, d, f), [(0, 0.075 * s), (0.06 * s, 0.075 * s)], M['iron'], seg=16, col=col)
    gz = top - 0.55 * s
    lathe('lamp_glass', (c.x, d, gz), [(0, 0.11 * s, 0.11 * s), (0.36 * s, 0.17 * s, 0.17 * s)], M['lantern'], seg=6, col=col)
    lathe('lamp_cap', (c.x, d, gz + 0.36 * s), [(0, 0.22 * s), (0.04 * s, 0.22 * s), (0.17 * s, 0.03 * s), (0.2 * s, 0.05 * s)], M['iron'], seg=6, col=col)
    lathe('lamp_bot', (c.x, d, gz - 0.06 * s), [(0, 0.08 * s), (0.06 * s, 0.13 * s)], M['iron'], seg=6, col=col)
    for a in range(6):
        an = TAU * a / 6
        tube('lamp_bar', [(c.x + math.cos(an) * 0.11 * s, d + math.sin(an) * 0.11 * s, gz), (c.x + math.cos(an) * 0.17 * s, d + math.sin(an) * 0.17 * s, gz + 0.36 * s)], [0.012 * s] * 2, M['iron'], seg=5, col=col)
    point_light('lampL', (c.x, d - 0.05, gz + 0.18 * s), '#ffae58', 450 * s * s, radius=0.08 * s)


def stall_left(M):
    d = ground_d(792)
    # toonbank
    a, b = S2W(116, 792, d), S2W(378, 690, d)
    box('counter', ((a.x + b.x) / 2, d + 0.3, (a.z + b.z) / 2), (b.x - a.x, 0.6, b.z - a.z), M['wood'], col='ground', bevel=0.01)
    box('countertop', ((a.x + b.x) / 2, d + 0.3, b.z + 0.02), (b.x - a.x + 0.1, 0.7, 0.05), M['wood'], col='ground')
    # palen
    for x in (108, 350):
        p = S2W(x, 792, d)
        top = S2W(x, 584, d).z
        box('post', (p.x, d - 0.05, top / 2), (0.08, 0.08, top), M['wood'], col='ground')
    # luifel: schuin doek met geschulpte rand
    fl, fr_ = S2W(58, 586, d - 0.15), S2W(414, 590, d - 0.15)
    db = d + 1.6
    bl, br = S2W(92, 490, db), S2W(400, 528, db)
    V = [fl, fr_, br, bl]
    obj_from('awning', V, [(0, 1, 2, 3)], M['awning'], col='ground', uv=[(0, 0), ((fr_ - fl).length, 0), ((br - bl).length, 1), (0, 1)], recalc=False).modifiers.new('s', 'SOLIDIFY').thickness = 0.02
    n = 10
    for i in range(n * 2):
        u0, u1 = i / (n * 2), (i + 1) / (n * 2)
        p0 = fl.lerp(fr_, u0); p1 = fl.lerp(fr_, u1)
        pts = [p0, p1]
        mid = (p0 + p1) / 2
        V = [p0, p1, p1 + Vector((0, 0, -0.1)), mid + Vector((0, 0, -0.2)), p0 + Vector((0, 0, -0.1))]
        m = M['flag'][0] if (i // 2) % 2 == 0 else plain('cream', '#f4ead8', 0.75)
        obj_from('scallop', V, [(0, 1, 2, 3, 4)], m, col='ground', recalc=False)
    # pakjes op en achter de toonbank
    r = random.Random(17)
    gm = [M['gred'], M['gyel'], M['ggrn'], M['gpnk'], M['gora']]
    for i in range(14):
        x = 130 + r.random() * 230
        gift(M, x, 690, 16 + r.random() * 22, 12 + r.random() * 18, gm[r.randrange(5)], d=d + 0.1 + r.random() * 0.3, rot=r.uniform(-0.3, 0.3))
    a2, b2 = S2W(120, 640, d + 0.9), S2W(372, 646, d + 0.9)
    box('shelf', ((a2.x + b2.x) / 2, d + 0.9, (a2.z + b2.z) / 2), (b2.x - a2.x, 0.4, 0.04), M['wood'], col='ground')
    for i in range(16):
        x = 126 + r.random() * 236
        gift(M, x, 640, 12 + r.random() * 16, 10 + r.random() * 16, gm[r.randrange(5)], d=d + 0.9 + r.random() * 0.1, rot=r.uniform(-0.3, 0.3), z0=(a2.z + b2.z) / 2 + 0.02)
    ct = b.z + 0.045                                   # bovenkant toonbank
    for i in range(14):
        x = 128 + i * 17.5 + r.uniform(-4, 4)
        gift(M, x, 690, 15 + r.random() * 10, 12 + r.random() * 12, gm[r.randrange(5)], d=d - 0.05 + r.random() * 0.15, rot=r.uniform(-0.35, 0.35), z0=ct)
    # lichtsnoer onder de luifel
    for i in range(12):
        u = (i + 0.5) / 12
        p = fl.lerp(fr_, u) + Vector((0, 0.15, -0.26 - 0.04 * math.sin(u * math.pi)))
        ellipsoid('bulb', p, (0.028, 0.028, 0.034), emit('bulb', '#ffd27a', 14.0), seg=8, rings=5, col='ground')
    point_light('stall_in', S2W(240, 610, d + 0.6), '#ffb060', 420, radius=0.4)
    point_light('stall_front', S2W(240, 650, d - 0.7), '#ffb060', 30, radius=0.5)


def awning_right(M):
    d = ground_d(702) - 1.0
    fl, fr_ = S2W(1354, 586, d - 0.6), S2W(1530, 580, d - 0.6)
    bl, br = S2W(1366, 526, d), S2W(1528, 528, d)
    obj_from('awningR', [fl, fr_, br, bl], [(0, 1, 2, 3)], M['awning'], col='ground', uv=[(0, 0), ((fr_ - fl).length, 0), ((br - bl).length, 1), (0, 1)], recalc=False).modifiers.new('s', 'SOLIDIFY').thickness = 0.02


def bunting(M, col='ground'):
    strings = [((44, 476), (431, 500), 34, 13, 'ground'), ((182, 430), (431, 470), 22, 8, 'ground'), ((431, 474), (560, 488), 12, 4, 'ground'),
               ((556, 478), (1300, 470), 44, 27, 'ground'), ((1300, 472), (1366, 458), 6, 2, 'ground')]
    for si, (a, b, sag, n, cl) in enumerate(strings):
        da = ground_d(702) - 1.6 if a[0] > 500 else ground_d(780)
        if si == 1:
            da = ground_d(800)
        pts = []
        for k in range(21):
            u = k / 20
            pts.append(S2W(a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u + math.sin(u * math.pi) * sag, da))
        tube('string', pts, [0.008] * len(pts), M['iron'], seg=4, col=cl)
        for i in range(n):
            u0 = (i + 0.1) / n
            u1 = u0 + 0.75 / n
            def P(u, dy=0):
                return S2W(a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u + math.sin(u * math.pi) * sag + dy, da)
            p0, p1 = P(u0), P(u1)
            fw = (p1 - p0).length
            tip = (p0 + p1) / 2 + Vector((0.02 * math.sin(i), 0, -fw * 1.3))
            obj_from('flag', [p0, p1, tip], [(0, 1, 2)], M['flag'][(i + si * 2) % 5], col=cl, recalc=False).modifiers.new('s', 'SOLIDIFY').thickness = 0.004


def banner(M):
    d = ground_d(702) - 1.0
    p0, p1 = S2W(1302, 400, d), S2W(1388, 397, d)
    tube('bannerpole', [p0, p1], [0.025, 0.025], M['iron'], seg=8, col='ground')
    pts = [(1318, 402), (1370, 402), (1370, 532), (1344, 506), (1318, 532)]
    P = wpoly(pts, d + 0.01)
    obj_from('banner', P, [tuple(range(5))], M['banner'], col='ground', recalc=False).modifiers.new('s', 'SOLIDIFY').thickness = 0.01
    for xs in (1324, 1364):
        tube('bannerstripe', [S2W(xs, 404, d - 0.005), S2W(xs, 520, d - 0.005)], [0.018, 0.018], M['flower_y'], seg=5, col='ground')


def sack(M, x, y, col='ground', s=1.0, rot=0.0):
    """Jutezak met ingesnoerde hals, slap neergezakt, touw met strik."""
    prof = [(0.0, 0.2, 0.18), (0.04, 0.3, 0.27), (0.16, 0.35, 0.31), (0.32, 0.31, 0.28), (0.46, 0.2, 0.18),
            (0.55, 0.085, 0.08), (0.6, 0.07, 0.065), (0.66, 0.11, 0.1), (0.74, 0.12, 0.11), (0.78, 0.05, 0.05)]
    prof = [(z * s, rx * s, ry * s) for (z, rx, ry) in prof]
    o = lathe('sack', (x, y, 0), prof, M['burlap'], seg=28, col=col)
    o.rotation_euler = (0, 0.06, rot)
    lathe('sack_tie', (x, y, 0.575 * s), [(0, 0.082 * s), (0.03 * s, 0.082 * s)], M['rope'], seg=20, col=col, cap=False)
    tube('sack_bow', [(x + 0.06 * s, y - 0.06 * s, 0.59 * s), (x + 0.13 * s, y - 0.1 * s, 0.5 * s), (x + 0.1 * s, y - 0.12 * s, 0.42 * s)], [0.012 * s] * 3, M['rope'], seg=6, col=col)


def handcart(M, sx, base_sy):
    """Houten handkar vol pakjes (op de plek waar eerst het paard stond)."""
    d = ground_d(base_sy)
    c = S2W(sx, base_sy, d)
    cx, cy = c.x, d
    rot = -0.25
    ca, sa = math.cos(rot), math.sin(rot)
    def P(lx, ly, z):
        return (cx + lx * ca - ly * sa, cy + lx * sa + ly * ca, z)
    # bak
    box('cart_bed', P(0, 0, 0.62), (1.3, 0.75, 0.08), M['wood'], col='ground', rot=(0, 0, rot), bevel=0.01)
    for (lx, ly, w, h) in ((0, -0.37, 1.3, 0.03), (0, 0.37, 1.3, 0.03), (-0.65, 0, 0.03, 0.75), (0.65, 0, 0.03, 0.75)):
        box('cart_side', P(lx, ly, 0.76), (w + 0.03, h + 0.03, 0.24), M['wood'], col='ground', rot=(0, 0, rot), bevel=0.006)
    # wielen
    for ly in (-0.45, 0.45):
        wc = P(0.15, ly, 0.38)
        o = lathe('wheel', (0, 0, -0.03), [(0, 0.38), (0.06, 0.38), (0.06, 0.33), (0, 0.33)], M['wood'], seg=40, col='ground', cap=False)
        o.location = wc; o.rotation_euler = (math.pi / 2, 0, rot)
        hub = lathe('hub', (0, 0, -0.06), [(0, 0.06), (0.12, 0.06)], M['iron'], seg=16, col='ground')
        hub.location = wc; hub.rotation_euler = (math.pi / 2, 0, rot)
        for k in range(8):
            a = TAU * k / 8
            p0 = Vector(wc); dv = Vector((math.cos(a) * ca * 0.34, math.cos(a) * sa * 0.34, math.sin(a) * 0.34))
            tube('spoke', [p0, p0 + dv], [0.018, 0.015], M['wood'], seg=6, col='ground')
    # disselboom naar de grond
    for ly in (-0.22, 0.22):
        tube('handle', [P(-0.6, ly, 0.6), P(-1.25, ly * 1.2, 0.12), P(-1.35, ly * 1.2, 0.08)], [0.03, 0.028, 0.03], M['wood'], seg=8, col='ground')
    box('stand', P(0.55, 0, 0.27), (0.06, 0.6, 0.5), M['wood'], col='ground', rot=(0, 0, rot))
    # lading: pakjes en een zak
    r = random.Random(23)
    gm = [M['gred'], M['gyel'], M['ggrn'], M['gpnk'], M['gora']]
    k = px(d)
    slots = [(-0.4, -0.15, 0.22, 0.2), (-0.38, 0.17, 0.2, 0.26), (-0.05, -0.12, 0.26, 0.22), (0.0, 0.18, 0.18, 0.18),
             (0.32, 0.0, 0.24, 0.3), (-0.2, 0.0, 0.16, 0.14), (0.15, -0.2, 0.15, 0.16)]
    z0 = 0.66
    for i, (lx, ly, w, h) in enumerate(slots):
        zz = z0 + (0.2 if i == 5 else 0)
        p = P(lx, ly, zz)
        m = gm[i % 5]
        rr_ = rot + r.uniform(-0.3, 0.3)
        box('cg', (p[0], p[1], zz + h / 2), (w, w * 0.85, h), m, col='ground', rot=(0, 0, rr_))
        box('cgr', (p[0], p[1], zz + h / 2), (w * 0.16, w * 0.87, h + 0.004), M['ribbon'], col='ground', rot=(0, 0, rr_))
        box('cgr', (p[0], p[1], zz + h / 2), (w + 0.004, w * 0.14, h + 0.004), M['ribbon'], col='ground', rot=(0, 0, rr_))
        ellipsoid('cbow', (p[0], p[1], zz + h + 0.025), (w * 0.2, w * 0.1, 0.035), M['ribbon'], seg=10, rings=6, col='ground')
    sack(M, P(0.42, 0.25, 0)[0], P(0.42, 0.25, 0)[1], col='ground', s=0.62)
    for o in list(bpy.data.objects):
        if o.name.startswith('sack') and abs(o.location.z) < 1e-6 and o.users_collection and o.users_collection[0].name == 'ground':
            pass
    point_light('cart_glow', P(-0.8, -1.2, 1.2), '#ffb060', 60, radius=0.5)


def props(M):
    # tonnen en pakjes vooraan
    barrel(M, 104, 838, 84, col='front')
    barrel(M, 1500, 798, 64)
    barrel(M, 1549, 808, 94, col='front')
    gift(M, 1546, 712, 44, 26, M['gred'], d=ground_d(808) - 0.02, col='front')
    gift(M, 391, 786, 46, 50, M['gred'])
    d = ground_d(795)
    c = S2W(332, 795, d)
    sack(M, c.x, d, col='ground')
    # tafel rechts met pakjes
    dt = ground_d(752)
    a, b = S2W(1600, 752, dt), S2W(1690, 684, dt)
    box('tableR', ((a.x + b.x) / 2, dt, (a.z + b.z) / 2), (b.x - a.x, 0.6, b.z - a.z), M['wood'], col='ground')
    gift(M, 1626, 684, 28, 26, M['ggrn'], d=dt); gift(M, 1657, 684, 26, 20, M['gyel'], d=dt)
    handcart(M, 1335, 752)
    for L in ((431, 750, 428), (556, 702, 572), (1292, 730, 460)):
        lamp(M, *L)
    lamp(M, 182, 838, 342, col='front')


# ------------------------------------------------------------------ boom linksvoor
def leaf_mesh():
    """Esdoornblad (5 lobben), plat, ca. 1 m groot — wordt geschaald per instantie."""
    pts = []
    lobes = [(0, 1.0), (0.62, 0.78), (1.15, 0.86), (1.62, 0.42), (2.1, 0.5)]
    seq = [(-l[0], l[1]) for l in reversed(lobes[1:])] + [(lobes[0][0], lobes[0][1])] + [(l[0], l[1]) for l in lobes[1:]]
    out = []
    for i, (a, r) in enumerate(seq):
        ang = math.pi / 2 + a
        out.append((math.cos(ang) * r * 0.5, 0, math.sin(ang) * r * 0.5))
        if i < len(seq) - 1:
            a2, r2 = seq[i + 1]
            am = math.pi / 2 + (a + a2) / 2
            out.append((math.cos(am) * 0.18, 0, math.sin(am) * 0.18))
    V = [(0, 0, -0.08)] + out
    F = [(0, i, i + 1) for i in range(1, len(out))]
    me = bpy.data.meshes.new('leaf')
    me.from_pydata(V, [], F)
    return me


def tree(M):
    dT = 7.2
    def T(sx, sy, d=dT):
        return S2W(sx, sy, d)
    # stam
    trunk = [T(-40, 1000), T(4, 900), T(22, 780), T(26, 640), T(16, 520), T(28, 400), T(44, 300), T(62, 250)]
    tube('trunk', trunk, [0.5, 0.38, 0.31, 0.29, 0.27, 0.26, 0.24, 0.2], M['bark'], seg=28, col='front')

    branches = [
        ([(40, 300), (112, 226), (190, 166), (282, 118), (382, 80), (482, 46), (592, 22), (700, 6), (800, -10)], 0.3, 0.03),
        ([(30, 240), (62, 160), (96, 96), (130, 44), (160, -14)], 0.28, 0.04),
        ([(50, 372), (118, 338), (186, 304), (248, 268), (302, 232), (340, 214)], 0.15, 0.02),
        ([(282, 118), (326, 150), (372, 184), (414, 214), (440, 240)], 0.08, 0.015),
        ([(482, 46), (530, 26), (590, 12), (650, 2), (700, -8)], 0.07, 0.015),
        ([(190, 166), (214, 118), (246, 62), (280, 18), (300, -10)], 0.09, 0.02),
        ([(112, 226), (150, 250), (190, 268), (222, 300), (236, 336)], 0.07, 0.015),
    ]
    leaf_pts = []
    for bi, (pts, r0, r1) in enumerate(branches):
        n = len(pts)
        W = []
        for i, (x, y) in enumerate(pts):
            dd = dT + 0.25 * i / n * (1 if bi % 2 else -1) + 0.3 * (i / n)
            W.append(T(x, y, dd))
        tube('branch%d' % bi, W, [r0 + (r1 - r0) * i / (n - 1) for i in range(n)], M['bark'], seg=10, col='canopy')
        wgt = [1.0, 1.0, 0.08, 0.5, 0.9, 0.9, 0.06][bi]
        for i in range(1, n):
            f = (0.4 + 0.6 * i / n) * (0.25 if bi == 0 and i < 4 else 1.0)
            leaf_pts.append((W[i - 1], W[i], wgt * f))
    point_light('treewarm', T(240, 330, dT - 1.2), '#ffa040', 260, radius=0.6)
    point_light('trunkwarm', T(150, 650, dT - 1.0), '#ff9a48', 55, radius=0.5)
    point_light('treewarm2', T(520, 120, dT - 1.0), '#ffb060', 180, radius=0.6)
    # bladeren: instanties van het esdoornblad, in clusters rond de takken
    me = leaf_mesh()
    rnd = random.Random(3)
    moon = Vector((555, 127))
    objs = []
    count = 0
    for (a, b, wgt) in leaf_pts:
        for k in range(int(110 * wgt)):
            p = a.lerp(b, rnd.random())
            off = Vector((rnd.gauss(0, 0.38), rnd.gauss(0, 0.4), rnd.gauss(-0.12, 0.32)))
            q = p + off
            # maan vrijhouden (in pixels)
            sx = 836 + q.x * 1200 / q.y; sy = 520 - (q.z - 2.2) * 1200 / q.y
            if (Vector((sx, sy)) - moon).length < 100:
                continue
            ob = bpy.data.objects.new('leaf', me)
            coll('canopy').objects.link(ob)
            ob.location = q
            sc = rnd.uniform(0.16, 0.28)
            ob.scale = (sc, sc, sc)
            ob.rotation_euler = (rnd.uniform(-1.2, 1.2), rnd.uniform(-0.6, 0.6), rnd.uniform(0, TAU))
            ob.active_material = None
            count += 1
            objs.append(ob)
    # per blad een materiaal via object-materiaalslot
    me.materials.append(M['leaf'][0])
    for ob in objs:
        ob.material_slots[0].link = 'OBJECT'
        ob.material_slots[0].material = M['leaf'][rnd.randrange(5)]
    # bladerhoop op de grond
    for k in range(160):
        x = rnd.uniform(-60, 360); y = rnd.uniform(850, 950)
        dg = ground_d(y)
        p = S2W(x, y, dg)
        ob = bpy.data.objects.new('gleaf', me)
        coll('front').objects.link(ob)
        ob.location = (p.x, dg, 0.01 + rnd.random() * 0.03)
        sc = rnd.uniform(0.09, 0.15)
        ob.scale = (sc, sc, sc)
        ob.rotation_euler = (math.pi / 2 + rnd.uniform(-0.3, 0.3), rnd.uniform(-0.3, 0.3), rnd.uniform(0, TAU))
        ob.material_slots[0].link = 'OBJECT'
        ob.material_slots[0].material = M['leaf'][rnd.randrange(5)]
    # verspreide blaadjes op het plein
    for k in range(120):
        y = rnd.uniform(720, 940); x = rnd.uniform(0, 1672)
        dg = ground_d(y); p = S2W(x, y, dg)
        ob = bpy.data.objects.new('gleaf', me)
        coll('ground').objects.link(ob)
        ob.location = (p.x, dg, 0.01)
        sc = rnd.uniform(0.06, 0.1)
        ob.scale = (sc, sc, sc)
        ob.rotation_euler = (math.pi / 2, 0, rnd.uniform(0, TAU))
        ob.material_slots[0].link = 'OBJECT'
        ob.material_slots[0].material = M['leaf'][rnd.randrange(5)]
    return count


def build_all():
    M = mats()
    ground(M)
    main_building(M)
    left_houses(M)
    right_houses(M)
    far_houses(M)
    fc = fountain(M)
    cobble_field(M, fc)
    stall_left(M)
    awning_right(M)
    bunting(M)
    banner(M)
    props(M)
    n = tree(M)
    return M, fc, n

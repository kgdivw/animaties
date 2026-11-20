"""
Python-versie van poses.js + toepassen op Blender-armatures.
Rotaties in karakterruimte (x rechts, y omhoog, z naar de kijker), Euler YXZ,
precies zoals in de browser, zodat film en voorvertoning hetzelfde bewegen.
"""
import math
from mathutils import Quaternion, Vector, Matrix

sin, cos = math.sin, math.cos


def clamp(v, a, b):
    return a if v < a else b if v > b else v


def gait(ph, duty):
    """Loopcyclus van één been: steunfase in een rechte lijn (pos +1 → -1), zwaaifase opgetild."""
    u = (ph / (2 * math.pi)) % 1.0
    if u < duty:
        return 1 - 2 * u / duty, 0.0
    v = (u - duty) / (1 - duty); e = v * v * (3 - 2 * v)
    return -1 + 2 * e, sin(math.pi * v)


def sint(st):
    w = st.get('walk', 0); ph = st.get('ph', 0); t = st.get('t', 0)
    s, c = sin(ph), cos(ph)
    breathe = sin(t * 1.6)
    wave = st.get('wave', 0); wv = sin(t * 7.2)
    turn = clamp(st.get('turn', 0), -3, 3)
    R, O = {}, {}
    O['hip'] = [s * 1.4 * w, abs(c) * 2.4 * w - 1.2 * w + breathe * 0.35 - st.get('crouch', 0) * 8, 0]
    R['hip'] = [0.03 * w, s * 0.07 * w - turn * 0.04, s * 0.025 * w]
    R['chest'] = [-0.03 * w + st.get('lean', 0) + breathe * 0.01, -s * 0.07 * w + turn * 0.05, wave * 0.07]
    R['neck'] = [0, turn * 0.08, 0]
    R['head'] = [st.get('nod', 0) + cos(ph * 2) * 0.025 * w, st.get('look', 0) + turn * 0.12, st.get('tilt', 0) + wave * 0.06]
    fl = 0.06 + w * 0.26 + st.get('wind', 0) * 0.1
    R['cape'] = [fl + sin(ph * 2 - 1.1) * 0.035 * w + sin(t * 1.7) * 0.02, sin(ph - 0.9) * 0.08 * w - turn * 0.06, sin(ph - 0.9) * 0.03 * w]
    O['ftR'] = [0, max(0, s) * 5 * w, s * 13 * w]
    O['ftL'] = [0, max(0, -s) * 5 * w, -s * 13 * w]
    R['ftR'] = [-max(0, s) * 0.25 * w, 0, 0]
    R['ftL'] = [-max(0, -s) * 0.25 * w, 0, 0]
    R['shR'] = [s * 0.32 * w * (1 - wave) - wave * 0.45 + breathe * 0.01, -wave * 0.3, -0.1 - wave * 2.25]
    R['elR'] = [-0.3 * (1 - wave) - wave * 0.15 - max(0, -s) * 0.15 * w, 0, -wave * (0.55 + wv * 0.38)]
    R['haR'] = [0, wave * wv * 0.3, -wave * 0.2]
    sa, ea = -0.5 - s * 0.07 * w, -0.85 + s * 0.05 * w
    R['shL'] = [sa, 0, 0.16]; R['elL'] = [ea, 0, -0.08]; R['haL'] = [0, 0, 0]
    R['staff'] = [-(sa + ea) - 0.04, 0, -0.08 - s * 0.03 * w]
    return {'rot': R, 'off': O}


def rider(st):
    """Sint te paard: bovenlijf van sint(), benen vast in de stijgbeugels, teugel in de rechterhand.
    st.twist (0..1) draait romp en hoofd in het zadel naar de kijker."""
    P = sint(dict(st, walk=0))
    R, O = P['rot'], P['off']
    t, ph, w = st.get('t', 0), st.get('ph', 0), st.get('walk', 0)
    tw, wave = st.get('twist', 0), st.get('wave', 0)
    O.pop('ftR', None); O.pop('ftL', None); O['hip'] = [0, sin(t * 1.6) * 0.3, 0]
    R['hip'] = [sin(ph * 2) * 0.03 * w, -tw * 0.35, sin(ph) * 0.035 * w]
    R['chest'] = [-0.04 + sin(ph * 2 + 0.6) * 0.03 * w, -tw * 0.45, wave * 0.07]
    R['head'][1] += -tw * 0.45 + st.get('look', 0)
    for sd, sg in (('R', 1), ('L', -1)):
        R['th' + sd] = [sin(ph + (0 if sd == 'R' else 3.14)) * 0.05 * w, 0, 0]
        R['kn' + sd] = [sin(ph * 2) * 0.04 * w, 0, 0]
        R['ft' + sd] = [0, 0, 0]
    if wave < 0.01:
        R['shR'] = [-0.55 + sin(ph * 2) * 0.04 * w, 0, -0.12]
        R['elR'] = [-0.95, 0, 0.25]
    fl = 0.12 + w * 0.22 + st.get('wind', 0) * 0.12
    R['cape'] = [fl + sin(ph * 2 - 1.1) * 0.04 * w, sin(ph - 0.9) * 0.06 * w + tw * 0.2, 0]
    return P


def piet(st, prop):
    w = st.get('walk', 0); ph = st.get('ph', 0); t = st.get('t', 0)
    s, c = sin(ph), cos(ph)
    jump = st.get('jump', 0); air = st.get('air', 0)
    turn = clamp(st.get('turn', 0), -3, 3)
    R, O = {}, {}
    bounce = abs(c)
    O['hip'] = [s * 1.2 * w, (bounce * 4.2 - 2.4) * w + sin(t * 2) * 0.35 - jump * 7 + air * 2, 0]
    R['hip'] = [0.05 * w, s * 0.16 * w - turn * 0.05, s * 0.04 * w]
    R['chest'] = [0.1 * w + jump * 0.3 - air * 0.1 + sin(ph * 2) * 0.03 * w, -s * 0.2 * w + turn * 0.07, -s * 0.05 * w]
    R['neck'] = [-0.04 * w, s * 0.06 * w + turn * 0.1, 0]
    R['head'] = [cos(ph * 2) * 0.05 * w - 0.05 * w + st.get('nod', 0) - jump * 0.15, st.get('look', 0) + s * 0.05 * w + turn * 0.15, s * 0.04 * w]
    gR, gL = gait(ph, 0.6), gait(ph + math.pi, 0.6)
    sw = gR[0] * w
    R['thR'] = [-gR[0] * 0.62 * w - gR[1] * 0.25 * w - jump * 0.85 + air * 0.5, 0, -0.02]
    R['thL'] = [-gL[0] * 0.62 * w - gL[1] * 0.25 * w - jump * 0.85 + air * 0.2, 0, 0.02]
    R['knR'] = [gR[1] * 1.3 * w + 0.08 * w + jump * 1.4 + air * 0.6, 0, 0]
    R['knL'] = [gL[1] * 1.3 * w + 0.08 * w + jump * 1.4 + air * 0.9, 0, 0]
    R['ftR'] = [(-gR[1] * 0.3 + max(0, -gR[0]) * 0.2 * (1 - gR[1])) * w - jump * 0.55, 0, 0]
    R['ftL'] = [(-gL[1] * 0.3 + max(0, -gL[0]) * 0.2 * (1 - gL[1])) * w - jump * 0.55, 0, 0]
    R['cap'] = [0.06, 0, -0.08 + sin(ph - 0.6) * 0.03 * w]
    lag = sin(ph * 2 - 1.2) * w
    R['feather'] = [-0.75 + lag * 0.16 + sin(t * 3.1) * 0.06 - st.get('wind', 0) * 0.18 + air * 0.25, sin(t * 2.3) * 0.08, sin(t * 2.7) * 0.05 + s * 0.06 * w]
    up = st.get('armsUp', 0)
    if prop == 'sack':
        R['shL'] = [-2.35, 0, 0.42]; R['elL'] = [-1.25, 0, 0.1]; R['haL'] = [0.3, 0, 0]
        R['shR'] = [sw * 0.65 - up * 2.4 - air * 0.6, 0, -0.18 - up * 0.3 - air * 0.4]
        R['elR'] = [-0.35 - max(0, -s) * 0.45 * w - up * 0.2, 0, 0]
    elif prop == 'gift':
        R['shR'] = [-0.92 - up * 1.45 + s * 0.04 * w, 0, -0.18]; R['elR'] = [-0.5 + up * 0.45, 0, 0.42]
        R['shL'] = [-0.92 - up * 1.45 - s * 0.04 * w, 0, 0.18]; R['elL'] = [-0.5 + up * 0.45, 0, -0.42]
        R['haR'] = [0, 0, 0.3]; R['haL'] = [0, 0, -0.3]
    return {'rot': R, 'off': O, 'hide': {prop: True} if st.get('hideProp') else {}}


def horse(st):
    t = st.get('t', 0); w = st.get('walk', 0); ph = st.get('ph', 0)
    R, O = {}, {}
    O['body'] = [0, sin(t * 1.3) * 0.6 + abs(sin(ph)) * 2 * w, 0]
    R['body'] = [0, 0, sin(t * 1.3) * 0.006]
    lift, nod, look = st.get('lift', 0), st.get('nod', 0), st.get('look', 0)
    R['neck'] = [0, look * 0.5, lift * 0.28 - nod * 0.22 + sin(t * 0.9) * 0.03]
    R['head'] = [0, look * 0.6, lift * 0.15 - nod * 0.3 + sin(t * 0.9 + 0.5) * 0.04]
    ef = st.get('earFlick', 0)
    R['earL'] = [0.1 * ef, 0, -0.1 + ef * 0.45]
    R['earR'] = [0, 0, -0.1 + sin(t * 0.7) * 0.1]
    stomp = st.get('stomp', 0)
    A, Bq = gait(ph, 0.55), gait(ph + math.pi, 0.55)
    R['legFR'] = [0, 0, A[0] * 0.3 * w + stomp * 0.5]; R['legFRk'] = [0, 0, -A[1] * 0.95 * w - stomp * 1.3]; R['legFRh'] = [0, 0, -A[1] * 0.45 * w + stomp * 0.4]
    R['legBL'] = [0, 0, A[0] * 0.27 * w]; R['legBLk'] = [0, 0, A[1] * 0.75 * w]; R['legBLh'] = [0, 0, -A[1] * 0.3 * w]
    R['legFL'] = [0, 0, Bq[0] * 0.3 * w]; R['legFLk'] = [0, 0, -Bq[1] * 0.95 * w]; R['legFLh'] = [0, 0, -Bq[1] * 0.45 * w]
    R['legBR'] = [0, 0, Bq[0] * 0.27 * w]; R['legBRk'] = [0, 0, Bq[1] * 0.75 * w]; R['legBRh'] = [0, 0, -Bq[1] * 0.3 * w]
    swish, wind = st.get('swish', 0), st.get('wind', 0)
    for i in range(4):
        R['tail%d' % i] = [sin(t * 2.2 - i * 0.9) * (0.08 + i * 0.05) * (0.4 + swish) + wind * 0.06, 0, -0.05 + sin(t * 1.1 - i * 0.6) * 0.04]
    return {'rot': R, 'off': O}


# ---------------------------------------------------------------- toepassen
def _q_char_to_blender(r):
    """Euler YXZ in karakterruimte → quaternion in Blender-assen.
    karakter x = blender x, karakter y = blender z, karakter z = blender -y."""
    rx, ry, rz = r[0] or 0, r[1] or 0, r[2] or 0
    qy = Quaternion((0, 0, 1), ry)
    qx = Quaternion((1, 0, 0), rx)
    qz = Quaternion((0, 1, 0), -rz)
    return qy @ qx @ qz


def apply_pose(arm, P, props=None):
    """Zet de pose op een armature-object. Pose-quaternion = rustoriëntatie⁻¹ · Qd · rust."""
    rot = P.get('rot', {}); off = P.get('off', {})
    for pb in arm.pose.bones:
        b = pb.bone
        Mr = b.matrix_local.to_quaternion()
        pb.rotation_mode = 'QUATERNION'
        if pb.name in rot:
            qd = _q_char_to_blender(rot[pb.name])
            pb.rotation_quaternion = Mr.inverted() @ qd @ Mr
        else:
            pb.rotation_quaternion = Quaternion()
        if pb.name in off:
            o = off[pb.name]
            v = Vector((o[0] * 0.01, -o[2] * 0.01, o[1] * 0.01))
            pb.location = Mr.inverted() @ v
        else:
            pb.location = Vector()
    if props:
        hide = P.get('hide', {})
        for name, ob in props.items():
            ob.hide_render = bool(hide.get(name))

"""Sinterklaasdeuntje op "Sinterklaas kapoentje" (traditioneel), precies 94 s, naadloos als lus.

Het traditionele "Sinterklaas kapoentje" als polka in 2/4 op 120 bpm: 1 maat = 1 s,
dus de maten vallen samen met de film (het liedje is 8 maten):
  0–36  scène 1 (F)     intro (tweede helft) + liedje + "bonne"-variant met tweede stem
                        + mineur op de tenen (20–28: Pieten in de schoorsteen) + liedje met tweede stem
  36–39 camerazwaai     harpglissando, V7 naar de nieuwe toonsoort
  39–54 scène 2 (Bes)   liedje + "bonne"-variant
  57–73 scène 3 (C)     "bonne"-variant + liedje, beide met tweede stem
  76–91 scène 4 (F)     liedje + liedje met tweede stem
  91–94 zwaai terug naar F → begin van de lus

Klokkenspel + zachte fluit (melodie), oempa-bas en akkoorden (polka), sleebelletjes,
paardenhoeven als Sint rijdt. Galm via circulaire convolutie, zodat de staart over de
lusnaad heen doorloopt.

    python muziek/deuntje.py muziek/deuntje.wav
"""
import sys, wave
import numpy as np

SR = 44100
BAR = 1.0
E8 = BAR / 4                       # achtste noot
TOTAL = 94.0
N = int(TOTAL * SR)
rng = np.random.default_rng(5)

L = np.zeros(N); R = np.zeros(N)

NAMES = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}


def midi(name):
    n = NAMES[name[0]]
    i = 1
    if name[i] == 'b':
        n -= 1; i += 1
    elif name[i] == '#':
        n += 1; i += 1
    return n + 12 * (int(name[i:]) + 1)


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def add(sig, t0, pan=0.0, gain=1.0):
    i0 = int(round(t0 * SR)) % N
    n = len(sig)
    gl, gr = gain * np.sqrt(0.5 * (1 - pan)), gain * np.sqrt(0.5 * (1 + pan))
    a = min(n, N - i0)                       # wat over het eind loopt, wikkelt om: naadloze lus
    L[i0:i0 + a] += sig[:a] * gl; R[i0:i0 + a] += sig[:a] * gr
    if a < n:
        L[:n - a] += sig[a:] * gl; R[:n - a] += sig[a:] * gr


def tt(dur):
    return np.arange(int(dur * SR)) / SR


# ------------------------------------------------------------------ instrumenten
def glock(f, dur):
    t = tt(min(2.2, dur + 1.6))
    s = (np.sin(2 * np.pi * f * t) * np.exp(-t * 2.2)
         + 0.32 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t * 6)
         + 0.12 * np.sin(2 * np.pi * f * 5.4 * t) * np.exp(-t * 12))
    s *= np.minimum(1, t / 0.002)
    return s


def flute(f, dur):
    t = tt(dur + 0.08)
    vib = 1 + 0.004 * np.sin(2 * np.pi * 5.2 * t) * np.minimum(1, t / 0.25)
    ph = 2 * np.pi * np.cumsum(f * vib) / SR
    s = np.sin(ph) + 0.18 * np.sin(2 * ph) + 0.06 * np.sin(3 * ph)
    s += 0.02 * rng.standard_normal(len(t)) * np.exp(-t * 20)          # adem bij de aanzet
    env = np.minimum(1, t / 0.03) * np.minimum(1, (dur + 0.08 - t) / 0.08)
    return s * env


def tuba(f, dur):
    t = tt(dur)
    ph = 2 * np.pi * f * t
    s = np.sin(ph) + 0.45 * np.sin(2 * ph) + 0.18 * np.sin(3 * ph) + 0.07 * np.sin(4 * ph)
    env = np.minimum(1, t / 0.015) * np.exp(-t * 3.5) * np.minimum(1, (dur - t) / 0.03)
    return s * env


def stab(freqs, dur):
    t = tt(dur)
    s = np.zeros(len(t))
    for f in freqs:
        ph = 2 * np.pi * f * t
        s += np.sin(ph) + 0.35 * np.sin(2 * ph) + 0.15 * np.sin(3 * ph) + 0.06 * np.sin(5 * ph)
    env = np.minimum(1, t / 0.006) * np.exp(-t * 9)
    return s * env / len(freqs)


def pluck(f, dur=1.4):
    """Harp: Karplus-Strong."""
    n = int(dur * SR)
    p = max(2, int(SR / f))
    buf = rng.uniform(-1, 1, p)
    out = np.zeros(n)
    for i in range(n):
        out[i] = buf[i % p]
        buf[i % p] = 0.5 * (buf[i % p] + buf[(i + 1) % p]) * 0.996
    return out


def jingle(dur=0.18, bright=1.0):
    t = tt(dur)
    s = np.zeros(len(t))
    for _ in range(5):                                   # een handvol belletjes, nét niet tegelijk
        f = rng.uniform(5200, 8800)
        d = rng.uniform(0, 0.012)
        tt_ = np.clip(t - d, 0, None)
        s += np.sin(2 * np.pi * f * tt_ + rng.uniform(0, 6)) * np.exp(-tt_ * 28) * (t >= d)
    ns = np.diff(rng.standard_normal(len(t) + 1)) * np.exp(-t * 60) * 0.25
    return (s * 0.2 + ns) * bright


def hoof(pitch=1.0):
    t = tt(0.09)
    s = np.sin(2 * np.pi * 820 * pitch * t) * np.exp(-t * 70) + 0.5 * np.sin(2 * np.pi * 1730 * pitch * t) * np.exp(-t * 110)
    s += 0.3 * np.diff(rng.standard_normal(len(t) + 1)) * np.exp(-t * 160)
    return s


def triangle(dur=1.8):
    t = tt(dur)
    return sum(a * np.sin(2 * np.pi * f * t) * np.exp(-t * k) for f, a, k in ((3950, 1, 2.0), (6120, 0.6, 2.6), (8430, 0.35, 3.4)))


# ------------------------------------------------------------------ muziek: Sinterklaas kapoentje (trad.), in F; per sectie getransponeerd
CH = {'F': ['F', 'A', 'C'], 'C7': ['C', 'E', 'G', 'Bb'], 'Bb': ['Bb', 'D', 'F'],
      'Fm': ['F', 'Ab', 'C'], 'Bbm': ['Bb', 'Db', 'F']}

# frase = lijst maten: (akkoord, [(noot of None, achtsten), ...]); 2/4, achtste = 1
# "Sin-ter-klaas ka- | poen- tje, | gooi wat in mijn | schoen- tje, | gooi wat in mijn | laars- je, | dank je Sin-ter- | klaas- je"
KAP = [('F', [('C5', 1), ('C5', 1), ('D5', 1), ('D5', 1)]), ('F', [('C5', 2), ('A4', 2)]),
       ('Bb', [('C5', 1), ('C5', 1), ('D5', 1), ('D5', 1)]), ('F', [('C5', 2), ('A4', 2)]),
       ('C7', [('Bb4', 1), ('Bb4', 1), ('C5', 1), ('C5', 1)]), ('C7', [('Bb4', 2), ('G4', 2)]),
       ('F', [('A4', 1), ('A4', 1), ('Bb4', 1), ('Bb4', 1)]), ('F', [('A4', 2), ('F4', 2)])]
THIRD = {'C5': 'A4', 'D5': 'Bb4', 'A4': 'F4', 'Bb4': 'G4', 'G4': 'E4', 'F4': 'C4'}
MINOR = {'A4': 'Ab4', 'D5': 'Db5'}
MINOR_CH = {'F': 'Fm', 'Bb': 'Bbm'}


def bonne(ph):
    """Achtsten in tweeën: "bon-ne bon-ne"."""
    return [(ch, [x for (n, d) in ns for x in ([(n, .5), (n, .5)] if d == 1 else [(n, d)])]) for ch, ns in ph]


def stacc(ph):
    """Op de tenen: elke noot half zo lang, dan stilte."""
    return [(ch, [x for (n, d) in ns for x in ((n, d / 2), (None, d / 2))]) for ch, ns in ph]


def minor(ph):
    return [(MINOR_CH.get(ch, ch), [(MINOR.get(n, n), d) for (n, d) in ns]) for ch, ns in ph]


def harm(ph):
    """Tweede stem een terts lager (wordt apart gespeeld, zachter)."""
    return [(ch, ns, [(THIRD.get(n) if n else None, d) for (n, d) in ns]) for ch, ns in ph]


def turn(resolve, pick):
    """3 maten camerazwaai: (slot van het liedje in de oude toonsoort) → V7 nieuw, harpglissando, opmaat."""
    first = [('A4', 2), ('F4', 2)] if resolve else [(None, 4)]
    return [('F', first, 'old'), ('C7', [(None, 4)], 'new'), ('C7', [(None, 2)] + pick, 'new')]


UP_C = [('A4', 1), ('Bb4', 1)]          # opmaat naar C5 (begin van het liedje)
DOWN_BB = [('D5', 1), ('C5', 1)]        # opmaat naar Bb4 (de intro begint bij "gooi wat in mijn laarsje")

# (startmaat, toonsoort-verschuiving, maten, opties)
PLAN = [
    (0, 0, KAP[4:] + KAP + harm(bonne(KAP)) + stacc(minor(KAP)) + harm(KAP), {'hoof': [(4, 9), (29, 33)], 'soft_intro': True}),
    (36, None, (0, -7, False, UP_C), {}),
    (39, -7, KAP + bonne(KAP)[:7], {'hoof': [(39, 54)]}),
    (54, None, (-7, -5, True, UP_C), {}),
    (57, -5, harm(bonne(KAP)) + harm(KAP), {}),
    (73, None, (-5, 0, False, UP_C), {}),
    (76, 0, KAP + harm(KAP)[:7], {'hoof': [(76, 80)]}),
    (91, None, (0, 0, True, DOWN_BB), {}),
]
OCT = 12                                 # melodie een octaaf hoger dan genoteerd (klokkenspel)


def tr(name, k):
    return midi(name) + k


def chord_midi(ch, k, octave=4):
    return [midi(n + str(octave)) + k for n in CH[ch]]


def play_bar(t0, ch, notes, k, vel=1.0, second=None):
    # polka: bas – akkoord – bas (kwint) – akkoord
    root = chord_midi(ch, k, 2)[0]
    while root > midi('Bb2'):
        root -= 12
    while root < midi('E2'):
        root += 12
    fifth = root + 7 if root + 7 <= midi('D3') else root - 5
    add(tuba(hz(root), 0.42), t0, -0.15, 0.30 * vel)
    add(tuba(hz(fifth), 0.42), t0 + 2 * E8, -0.15, 0.27 * vel)
    cm = chord_midi(ch, k, 4)
    cm = [m - 12 if m > midi('E5') else m for m in cm]
    for j in (1, 3):
        add(stab([hz(m) for m in cm], 0.2), t0 + j * E8, 0.25, 0.10 * vel)
    for voice, g in ((notes, 1.0), (second, 0.5)):
        if not voice:
            continue
        tpos = t0
        for (n, d) in voice:
            if n:
                m = tr(n, k) + OCT
                add(glock(hz(m), d * E8), tpos, -0.05 if g == 1 else -0.3, 0.16 * vel * g)
                add(flute(hz(m), d * E8 * 0.92), tpos, 0.1 if g == 1 else 0.35, 0.07 * vel * g)
            tpos += d * E8


SOFT = (20, 28)        # Pieten in de schoorsteen: op de tenen, in mineur
for (b0, k, mats, opt) in PLAN:
    if k is None:
        k_old, k_new, resolve, pick = mats
        for i, (ch, notes, which) in enumerate(turn(resolve, pick)):
            play_bar(b0 + i, ch, notes, k_old if which == 'old' else k_new, 0.85)
        # harpglissando omhoog over de eerste twee maten (toonladder van de nieuwe toonsoort)
        scale = [0, 2, 4, 5, 7, 9, 11]
        for j in range(16):
            m = midi('F3') + k_new + scale[j % 7] + 12 * (j // 7)
            add(pluck(hz(m), 1.2), b0 + 0.25 + j * 0.09, -0.4 + j * 0.05, 0.22)
        add(triangle(), b0 + 2, 0.35, 0.05)
        continue
    for i, bar in enumerate(mats):
        ch, notes = bar[0], bar[1]
        second = bar[2] if len(bar) > 2 else None
        vel = 1.0
        if opt.get('soft_intro') and i < 4:
            vel = 0.55 + 0.45 * i / 4
        if SOFT[0] <= b0 + i < SOFT[1]:
            vel = 0.5
        play_bar(b0 + i, ch, notes, k, vel, second)
    for (h0, h1) in opt.get('hoof', []):              # klip-klop: Sint te paard
        t = h0
        while t < h1 - 1e-6:
            add(hoof(1.0), t, -0.3, 0.08); add(hoof(0.86), t + E8, -0.3, 0.06)
            t += 2 * E8


# sleebelletjes: achtsten, nadruk op de tel, de hele lus door (zachter in de intro)
for i in range(int(TOTAL / E8)):
    t = i * E8
    acc = 1.0 if i % 2 == 0 else 0.55
    if t < 4:
        acc *= 0.35 + 0.65 * t / 4
    if SOFT[0] <= t < SOFT[1]:
        acc *= 0.3 if i % 4 == 0 else 0.0
    add(jingle(0.2), t + rng.uniform(-0.006, 0.006), 0.45, 0.07 * acc)

# ------------------------------------------------------------------ galm (circulair → loopt over de naad door)
def reverb(x, secs=1.6, wet=0.22):
    n = int(secs * SR)
    t = np.arange(n) / SR
    ir = rng.standard_normal(n) * np.exp(-t * 4.0)
    ir = np.convolve(ir, np.ones(6) / 6, mode='same')     # iets doffer
    ir[:int(0.012 * SR)] = 0                               # kleine voorvertraging
    ir /= np.sqrt(np.sum(ir ** 2))
    H = np.fft.rfft(np.pad(ir, (0, N - n)))
    return x + wet * np.fft.irfft(np.fft.rfft(x) * H, n=N)


L = reverb(L); R = reverb(R)
peak = max(np.max(np.abs(L)), np.max(np.abs(R)))
L, R = L / peak * 0.89, R / peak * 0.89
out = sys.argv[1] if len(sys.argv) > 1 else 'deuntje.wav'
pcm = (np.stack([L, R], 1) * 32767).astype('<i2')
with wave.open(out, 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes(pcm.tobytes())
print('geschreven:', out, '%.1f s' % (N / SR))

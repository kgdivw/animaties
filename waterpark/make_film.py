"""Maakt de hele film in één keer: mp4 (1080p, H.264) met de muziek eronder.

  python make_film.py                     # Blender-look (Eevee), resultaat: waterpark_film.mp4
  python make_film.py --look threejs      # three.js-look uit de browser (snel)

Blender-look, stappen (elke stap wordt overgeslagen als het resultaat er al is, dus afbreken en herstarten mag):
  1. bake    de scène draait in een onzichtbare browser en schrijft _film/scene.glb + de staat per frame
  2. render  Blender rendert elke frame naar _film/frames/f_00000.png
  3. mp4     ffmpeg plakt de frames en Sunrise_Fever.mp3 aan elkaar

Nodig: Chrome of Edge, Blender (4.2+), ffmpeg, en internet (three.js komt van unpkg).
Opties: --fps 30  --res 1920x1080  --engine eevee|cycles  --samples 16  --device gpu  --t0/--t1 (seconden)
        --only bake|render (stoppen na die stap)  --rebake (scène opnieuw bakken)  --clean (alle frames weggooien)  --blender/--browser <pad>
"""
import argparse, glob, http.server, os, shutil, subprocess, sys, tempfile, threading, time, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
AUDIO = os.path.join(HERE, 'Sunrise_Fever.mp3')
DUR = 161.9

ap = argparse.ArgumentParser(description='Waterpark Sunrise Fever -> mp4')
ap.add_argument('--look', default='blender', choices=['blender', 'threejs'])
ap.add_argument('--out', default='')
ap.add_argument('--fps', type=int, default=30)
ap.add_argument('--t0', type=float, default=0.0)
ap.add_argument('--t1', type=float, default=DUR)
ap.add_argument('--res', default='1920x1080')
ap.add_argument('--engine', default='eevee', choices=['eevee', 'cycles'])
ap.add_argument('--samples', type=int, default=16, help='Eevee-samples, of Cycles-samples bij --engine cycles')
ap.add_argument('--device', default='gpu', help='Cycles: gpu (automatisch) | cpu | optix | cuda | hip | metal | oneapi')
ap.add_argument('--tube', default='clear', choices=['clear', 'dome'])
ap.add_argument('--film', default=os.path.join(HERE, '_film'), help='werkmap voor bake en frames')
ap.add_argument('--rebake', action='store_true')
ap.add_argument('--clean', action='store_true')
ap.add_argument('--blender', default='')
ap.add_argument('--browser', default='')
ap.add_argument('--port', type=int, default=8790)
ap.add_argument('--only', default='', choices=['', 'bake', 'render'], help='stoppen na deze stap')
ap.add_argument('--show', action='store_true', help='browser zichtbaar (three.js-look is standaard zichtbaar, dan rendert de GPU)')
A = ap.parse_args()
OUT = os.path.abspath(A.out or os.path.join(HERE, 'waterpark_film.mp4' if A.look == 'blender' else 'waterpark_sunrise_fever.mp4'))
FILM = os.path.abspath(A.film)


def say(*m): print('[make_film]', *m, flush=True)


def die(m): say('FOUT:', m); sys.exit(1)


# ------------------------------------------------------------------ programma's zoeken
def find_exe(given, names, globs):
    if given:
        if os.path.exists(given): return given
        die('niet gevonden: ' + given)
    for n in names:
        p = shutil.which(n)
        if p: return p
    for g in globs:
        hits = sorted(glob.glob(g))
        if hits: return hits[-1]                       # hoogste versie
    return None


PF, PF86, LAD = os.environ.get('ProgramFiles', r'C:\Program Files'), os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)'), os.environ.get('LOCALAPPDATA', '')
FFMPEG = find_exe('', ['ffmpeg'], []) or die('ffmpeg niet gevonden (zet het in het PATH)')


def browser():
    return find_exe(A.browser, ['chrome', 'google-chrome', 'chromium', 'chromium-browser', 'msedge'], [
        os.path.join(PF, 'Google', 'Chrome', 'Application', 'chrome.exe'), os.path.join(PF86, 'Google', 'Chrome', 'Application', 'chrome.exe'),
        os.path.join(LAD, 'Google', 'Chrome', 'Application', 'chrome.exe'),
        os.path.join(PF86, 'Microsoft', 'Edge', 'Application', 'msedge.exe'), os.path.join(PF, 'Microsoft', 'Edge', 'Application', 'msedge.exe'),
        '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
    ]) or die('geen Chrome/Edge gevonden (geef --browser <pad>)')


def blender():
    return find_exe(A.blender, ['blender'], [
        os.path.join(PF, 'Blender Foundation', 'Blender *', 'blender.exe'), os.path.join(LAD, 'Programs', 'Blender Foundation', 'Blender *', 'blender.exe'),
        r'C:\Program Files (x86)\Steam\steamapps\common\Blender\blender.exe', '/Applications/Blender.app/Contents/MacOS/Blender',
    ]) or die('Blender niet gevonden (geef --blender <pad>)')


# ------------------------------------------------------------------ server: statische bestanden + bake/frames opvangen
class State:
    proc = None; frames = 0; done = threading.Event(); error = None


def ffmpeg_pipe(fps, t0, t1):
    cmd = [FFMPEG, '-y', '-loglevel', 'error', '-f', 'image2pipe', '-c:v', 'mjpeg', '-framerate', str(fps), '-i', '-',
           '-ss', str(t0), '-t', str(t1 - t0), '-i', AUDIO, '-map', '0:v', '-map', '1:a',
           '-c:v', 'libx264', '-preset', 'slow', '-crf', '17', '-pix_fmt', 'yuv420p', '-profile:v', 'high', '-r', str(fps),
           '-c:a', 'aac', '-b:a', '320k', '-movflags', '+faststart', '-shortest', OUT]
    return subprocess.Popen(cmd, stdin=subprocess.PIPE)


class H(http.server.SimpleHTTPRequestHandler):
    def __init__(s, *a, **k): super().__init__(*a, directory=HERE, **k)

    def end_headers(s):
        s.send_header('Cache-Control', 'no-store'); super().end_headers()

    def do_POST(s):
        u = urllib.parse.urlparse(s.path); q = urllib.parse.parse_qs(u.query)
        body = s.rfile.read(int(s.headers.get('Content-Length') or 0))
        name = os.path.basename(q.get('name', [''])[0])
        p = u.path
        if p == '/bake/start':
            os.makedirs(FILM, exist_ok=True)
            for f in ('scene.glb', 'bake.json', 'frames.bin', 'drops.bin'):
                if os.path.exists(os.path.join(FILM, f)): os.remove(os.path.join(FILM, f))
        elif p == '/bake/file': open(os.path.join(FILM, name), 'wb').write(body)
        elif p == '/bake/append': open(os.path.join(FILM, name), 'ab').write(body)
        elif p == '/bake/log': say('browser:', body.decode(errors='replace'))
        elif p == '/bake/error': State.error = body.decode(errors='replace'); say('browser FOUT:', State.error); State.done.set()
        elif p == '/bake/done': State.done.set()
        elif p == '/start':
            fps = int(q['fps'][0]); State.proc = ffmpeg_pipe(fps, float(q['t0'][0]), float(q['t1'][0])); State.frames = 0
        elif p == '/frame':
            State.proc.stdin.write(body); State.frames += 1
            if State.frames % 150 == 0: say('frames', State.frames)
        elif p == '/end':
            State.proc.stdin.close(); State.proc.wait(); State.done.set()
        s.send_response(200); s.send_header('Content-Length', '2'); s.end_headers(); s.wfile.write(b'ok')

    def log_message(s, *a): pass


def run_browser(query, headless):
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', A.port), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = 'http://127.0.0.1:%d/index.html?%s' % (A.port, query)
    prof = tempfile.mkdtemp(prefix='wp_browser_')
    flags = ['--user-data-dir=' + prof, '--no-first-run', '--no-default-browser-check', '--disable-extensions',
             '--disable-background-timer-throttling', '--disable-renderer-backgrounding', '--disable-backgrounding-occluded-windows',
             '--autoplay-policy=no-user-gesture-required', '--ignore-gpu-blocklist']
    if headless: flags += ['--headless=new', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--window-size=1280,720', url]
    else: flags += ['--window-size=1300,780', '--app=' + url]
    say('browser:', url, '(onzichtbaar)' if headless else '')
    State.done.clear(); State.error = None
    bp = subprocess.Popen([browser()] + flags, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        while not State.done.wait(2):
            if bp.poll() is not None: die('browser is afgesloten voordat het klaar was')
    finally:
        bp.terminate()
        try: bp.wait(10)
        except Exception: bp.kill()
        srv.shutdown(); srv.server_close()
        shutil.rmtree(prof, ignore_errors=True)
    if State.error: die('in de browser: ' + State.error)


tq = '&t0=%g&t1=%g' % (A.t0, A.t1)

# ------------------------------------------------------------------ three.js-look: browser rendert, frames gaan direct naar ffmpeg
if A.look == 'threejs':
    t = time.time()
    run_browser('render=1&auto=%d%s' % (A.fps, tq), headless=False)
    say('klaar in %.0f s ->' % (time.time() - t), OUT)
    sys.exit(0)

# ------------------------------------------------------------------ Blender-look
FR = os.path.join(FILM, 'frames')
bake_json = os.path.join(FILM, 'bake.json')
src = os.path.join(HERE, 'index.html')
import json
fresh = os.path.exists(bake_json) and os.path.getmtime(bake_json) > os.path.getmtime(src)
if fresh:
    b = json.load(open(bake_json))
    fresh = b['fps'] == A.fps and abs(b['t0'] - A.t0) < 1e-6 and abs(b['t1'] - A.t1) < 1e-6
if A.rebake or not fresh:
    if os.path.isdir(FR):
        say('scène verandert -> oude frames weg'); shutil.rmtree(FR)
    say('1/3 bake: scène doorrekenen in de browser ...'); t = time.time()
    run_browser('bake=%d%s' % (A.fps, tq), headless=not A.show)
    say('bake klaar in %.0f s' % (time.time() - t))
else:
    say('1/3 bake: al gedaan (%s)' % bake_json)
if A.only == 'bake': sys.exit(0)
if A.clean and os.path.isdir(FR): shutil.rmtree(FR)

n = json.load(open(bake_json))['n']
have = len(glob.glob(os.path.join(FR, 'f_*.png')))
if have < n:
    say('2/3 render: %d van %d frames te doen met Blender (%s) ...' % (n - have, n, A.engine))
    cmd = [blender(), '-b', '--python', os.path.join(HERE, 'blender', 'look_still.py'), '--', '--film', FILM,
           '--res', A.res, '--engine', A.engine, '--esamples', str(A.samples), '--samples', str(A.samples),
           '--device', A.device, '--tube', A.tube, '--denoise', 'BALANCED']
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors='replace')
    for line in p.stdout:
        if line.startswith(('FRAME', 'FILM', 'MATERIALS', 'DEVICE', 'Error', 'Traceback')) or 'Error' in line or line.startswith('  File'):
            print('  ' + line.rstrip(), flush=True)
    if p.wait() != 0: die('Blender stopte met code %d' % p.returncode)
    have = len(glob.glob(os.path.join(FR, 'f_*.png')))
    if have < n: die('nog maar %d van %d frames' % (have, n))
else:
    say('2/3 render: alle %d frames zijn er al' % n)

if A.only == 'render': sys.exit(0)
say('3/3 mp4 ...')
rc = subprocess.call([FFMPEG, '-y', '-loglevel', 'error', '-framerate', str(A.fps), '-i', os.path.join(FR, 'f_%05d.png'),
                      '-ss', str(A.t0), '-t', str(A.t1 - A.t0), '-i', AUDIO, '-map', '0:v', '-map', '1:a',
                      '-c:v', 'libx264', '-preset', 'slow', '-crf', '17', '-pix_fmt', 'yuv420p', '-profile:v', 'high',
                      '-c:a', 'aac', '-b:a', '320k', '-movflags', '+faststart', '-shortest', OUT])
if rc: die('ffmpeg stopte met code %d' % rc)
say('klaar ->', OUT)

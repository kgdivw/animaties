"""Statische server + video-export: frames uit de browser direct in ffmpeg pipen (geen PNG-berg op schijf).

  python .claude/tools/framepipe.py <poort> <map> <audio> <uitvoer.mp4>

  POST /start?fps=30&t0=0&t1=160  -> start ffmpeg (JPEG-frames via stdin + audio vanaf t0)
  POST /frame (body = JPEG)       -> één frame
  POST /end                       -> sluit af, wacht op ffmpeg, schrijft <uitvoer>.done
  GET  /status                    -> aantal ontvangen frames
"""
import sys, os, subprocess, threading, http.server, urllib.parse

port, root, audio, out = int(sys.argv[1]), os.path.abspath(sys.argv[2]), os.path.abspath(sys.argv[3]), os.path.abspath(sys.argv[4])
state = {'proc': None, 'n': 0}
lock = threading.Lock()


class H(http.server.SimpleHTTPRequestHandler):
    def __init__(s, *a, **k): super().__init__(*a, directory=root, **k)

    def ok(s, body=b'ok'):
        s.send_response(200); s.send_header('Content-Length', str(len(body))); s.end_headers(); s.wfile.write(body)

    def do_GET(s):
        if s.path.startswith('/status'):
            return s.ok(str(state['n']).encode())
        return super().do_GET()

    def do_POST(s):
        u = urllib.parse.urlparse(s.path); q = urllib.parse.parse_qs(u.query)
        body = s.rfile.read(int(s.headers.get('Content-Length') or 0))
        with lock:
            if u.path == '/start':
                fps = q.get('fps', ['30'])[0]; t0 = q.get('t0', ['0'])[0]; t1 = float(q.get('t1', ['0'])[0])
                for f in (out, out + '.done'):
                    if os.path.exists(f): os.remove(f)
                cmd = ['ffmpeg', '-y', '-loglevel', 'error',
                       '-f', 'image2pipe', '-c:v', 'mjpeg', '-framerate', fps, '-i', '-',
                       '-ss', t0, '-t', str(t1 - float(t0)), '-i', audio,
                       '-map', '0:v', '-map', '1:a',
                       '-c:v', 'libx264', '-preset', 'slow', '-crf', '17', '-pix_fmt', 'yuv420p',
                       '-profile:v', 'high', '-r', fps,
                       '-c:a', 'aac', '-b:a', '320k', '-movflags', '+faststart', '-shortest', out]
                state['proc'] = subprocess.Popen(cmd, stdin=subprocess.PIPE); state['n'] = 0
                print('start', ' '.join(cmd), flush=True)
            elif u.path == '/frame':
                state['proc'].stdin.write(body); state['n'] += 1
                if state['n'] % 150 == 0: print('frames', state['n'], flush=True)
            elif u.path == '/end':
                p = state['proc']; p.stdin.close(); rc = p.wait()
                open(out + '.done', 'w').write(f"rc={rc} frames={state['n']}\n")
                print('done', rc, state['n'], flush=True)
        s.ok()

    def log_message(s, *a): pass


http.server.ThreadingHTTPServer(('127.0.0.1', port), H).serve_forever()

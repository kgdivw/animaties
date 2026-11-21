"""Statische server + POST /save?name=x.png -> schrijft een PNG (dataURL) naar <map>/_snaps/."""
import sys, os, base64, http.server, urllib.parse
root = os.path.abspath(sys.argv[2] if len(sys.argv) > 2 else '.')
port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
class H(http.server.SimpleHTTPRequestHandler):
    def __init__(s, *a, **k): super().__init__(*a, directory=root, **k)
    def do_POST(s):
        q = urllib.parse.urlparse(s.path)
        name = os.path.basename(urllib.parse.parse_qs(q.query).get('name', ['snap.png'])[0])
        data = s.rfile.read(int(s.headers['Content-Length'])).decode()
        os.makedirs(os.path.join(root, '_snaps'), exist_ok=True)
        open(os.path.join(root, '_snaps', name), 'wb').write(base64.b64decode(data.split(',', 1)[1]))
        s.send_response(200); s.end_headers(); s.wfile.write(b'ok')
    def log_message(s, *a): pass
http.server.ThreadingHTTPServer(('127.0.0.1', port), H).serve_forever()

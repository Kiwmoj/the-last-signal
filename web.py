"""Play THE LAST SIGNAL in a web browser. The game runs here, in Python/PyQt, and is streamed to the browser as live video;
the browser sends your keys and clicks back. Only the standard library is used, and the one HTML page is served from this file.

    python web.py                 -> open http://localhost:8080
    python web.py --port 9000 --host 0.0.0.0     (let other computers on your network connect)

Limits: one shared game for everyone who connects (it is a single game session), and no sound in the browser (audio is muted on the server).
"""
import argparse
import os
import sys
import threading
import time

if sys.platform != "win32":
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")      # Linux server: render with no display (install a font such as DejaVu)
# on Windows the normal platform is used with the window never shown, so system fonts work

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from PyQt6.QtCore import Qt, QBuffer, QByteArray, QTimer, QIODevice
from PyQt6.QtWidgets import QApplication

from tls.engine import GameWindow
from tls.constants import W, H

PAGE = """<!doctype html><html><head><meta charset="utf-8"><title>THE LAST SIGNAL</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>html,body{margin:0;height:100%;background:#000;overflow:hidden}
#g{position:absolute;inset:0;margin:auto;max-width:100vw;max-height:100vh;aspect-ratio:16/9;image-rendering:pixelated;outline:none}
#h{position:fixed;bottom:4px;left:0;right:0;text-align:center;color:#456;font:12px monospace}</style></head>
<body><img id="g" src="/stream" tabindex="0" draggable="false"><div id="h">Click the game, then use the keyboard. F11 = fullscreen. This browser view has no sound.</div>
<script>
const MAP={ArrowUp:'up',ArrowDown:'down',ArrowLeft:'left',ArrowRight:'right',' ':'space',Enter:'enter',Escape:'esc',Backspace:'bksp',Delete:'del',Tab:'tab'};
const g=document.getElementById('g');g.focus();
function code(e){if(MAP[e.key])return MAP[e.key];if(/^F\\d+$/.test(e.key))return e.key;return e.key.length===1?e.key.toUpperCase():null}
function send(d,e){const c=code(e);if(!c||c==='F11')return;e.preventDefault();if(e.repeat)return;fetch('/key?d='+d+'&k='+encodeURIComponent(c),{method:'POST'})}
addEventListener('keydown',e=>send(1,e));addEventListener('keyup',e=>send(0,e));
function pos(e){const r=g.getBoundingClientRect();return[(e.clientX-r.left)/r.width,(e.clientY-r.top)/r.height]}
g.addEventListener('mousedown',e=>{g.focus();const[x,y]=pos(e);fetch('/mouse?t=press&x='+x+'&y='+y,{method:'POST'})});
g.addEventListener('mousemove',e=>{const n=performance.now();if(n-(g.l||0)<60)return;g.l=n;const[x,y]=pos(e);fetch('/mouse?t=move&x='+x+'&y='+y,{method:'POST'})});
</script></body></html>"""

QT_KEYS = {"up": Qt.Key.Key_Up, "down": Qt.Key.Key_Down, "left": Qt.Key.Key_Left, "right": Qt.Key.Key_Right, "space": Qt.Key.Key_Space,
           "enter": Qt.Key.Key_Return, "esc": Qt.Key.Key_Escape, "bksp": Qt.Key.Key_Backspace, "del": Qt.Key.Key_Delete, "tab": Qt.Key.Key_Tab}
for _n in range(1, 13):
    QT_KEYS["F%d" % _n] = getattr(Qt.Key, "Key_F%d" % _n)


def qt_key(code):
    if code in QT_KEYS:
        return QT_KEYS[code]
    if len(code) == 1:
        return Qt.Key(ord(code))          # letters and digits share their ASCII code with Qt's key values
    return None


class Shared:
    """State passed between the HTTP threads and the Qt thread."""
    frame = b""
    seq = 0
    events = []
    lock = threading.Lock()
    cond = threading.Condition()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _ok(self, ctype, body):
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            self._ok("text/html; charset=utf-8", PAGE.encode())
        elif path == "/frame.jpg":
            self._ok("image/jpeg", Shared.frame)
        elif path == "/stream":
            self.send_response(200)
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            last = -1
            try:
                while True:
                    with Shared.cond:
                        Shared.cond.wait_for(lambda: Shared.seq != last, timeout=2)
                        last, data = Shared.seq, Shared.frame
                    if data:
                        self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: %d\r\n\r\n" % len(data) + data + b"\r\n")
            except (BrokenPipeError, ConnectionError, OSError):
                return
        else:
            self.send_error(404)

    def do_POST(self):
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        with Shared.lock:
            if u.path == "/key":
                Shared.events.append(("key", q.get("d") == "1", q.get("k", "")))
            elif u.path == "/mouse":
                Shared.events.append(("mouse", q.get("t"), float(q.get("x", 0)), float(q.get("y", 0))))
        self._ok("text/plain", b"ok")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8080)
    args = ap.parse_args()

    app = QApplication(sys.argv)
    win = GameWindow()
    win.resize(W * 3, H * 3)
    win.audio.play = lambda *a, **k: None                     # no sound on the server
    win.audio.set_mood = lambda *a, **k: None
    win.audio.set_hum = lambda *a, **k: None
    win.audio.set_music = lambda *a, **k: None
    win.timer.stop()                                          # the server drives the loop itself
    last = [time.perf_counter()]

    def encode():
        win.grab()                                            # paints the game into win.buffer
        ba = QByteArray()
        buf = QBuffer(ba)
        buf.open(QIODevice.OpenModeFlag.WriteOnly)
        win.buffer.save(buf, "JPEG", 82)
        return bytes(ba)

    def tick():
        with Shared.lock:
            evs, Shared.events = Shared.events, []
        for ev in evs:
            if ev[0] == "key":
                k = qt_key(ev[2])
                if k is None:
                    continue
                if ev[1]:
                    if k == Qt.Key.Key_F10:
                        win.hide_hud = not win.hide_hud
                    elif k != Qt.Key.Key_F11:
                        win.key_down(k)
                else:
                    win.key_up(k)
            else:
                x, y = ev[2] * W, ev[3] * H
                s = win.scenes[-1]
                fn = getattr(s, "mouse_press" if ev[1] == "press" else "mouse_move", None)
                if fn:
                    fn(x, y)
        now = time.perf_counter()
        dt = min(now - last[0], .05)
        last[0] = now
        win.time += dt
        try:
            win.scenes[-1].update(dt)
        except Exception:
            win._recover(win.scenes[-1])
        data = encode()
        with Shared.cond:
            Shared.frame = data
            Shared.seq += 1
            Shared.cond.notify_all()

    t = QTimer()
    t.timeout.connect(tick)
    t.start(1000 // 30)
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(f"THE LAST SIGNAL is running in your browser:  http://{'localhost' if args.host in ('127.0.0.1', '0.0.0.0') else args.host}:{args.port}")
    code = app.exec()
    win.audio.shutdown()
    sys.exit(code)


if __name__ == "__main__":
    main()

"""`decomp stop` returns only once the app is gone, so `decomp` started right after doesn't find it still answering."""

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

from decompnet.app import cli


def test_stop_waits_for_the_app_to_go_away(tmp_path, monkeypatch):
    class App(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):  # /health
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps({"app": "decomp-wtf", "version": "x"}).encode())

        def do_POST(self):  # /api/quit: like the real app, it answers and goes away a little later
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"{}")
            threading.Timer(1.0, server.shutdown).start()

    server = HTTPServer(("127.0.0.1", 0), App)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    (tmp_path / ".decomp").mkdir()
    (tmp_path / ".decomp" / "server.json").write_text(json.dumps({"port": server.server_port, "secret": "s"}))
    monkeypatch.setenv("DECOMP_HOME", str(tmp_path))

    t0 = time.monotonic()
    assert cli.stop(None) == 0
    assert time.monotonic() - t0 >= 0.9  # it waited
    assert not cli._alive(server.server_port)

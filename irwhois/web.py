#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Web UI (Persian) for checking .ir domains.

Web layer only: HTTP server, API handlers and static files from web/.
All domain logic lives in irwhois.core; this module never queries whois
directly and embeds no HTML/CSS/JS in Python code.

Run:
    python -m irwhois.web [--port 8000]
"""

import argparse
import json
import os
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from irwhois.core import DEFAULT_TIMEOUT, DEFAULT_WORKERS, batch_check, check_domain

WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")

STATIC_FILES = {
    "index.html": "text/html; charset=utf-8",
    "styles.css": "text/css; charset=utf-8",
    "app.js": "application/javascript; charset=utf-8",
}


class WebHandler(BaseHTTPRequestHandler):
    server_version = "IRWhois/1.0"

    def log_message(self, fmt, *args):
        sys.stderr.write("WEB %s - %s\n" % (self.address_string(), fmt % args))

    def _send_json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_static(self, filename: str):
        """Serve a static file from web/ (allowlist only, no path traversal)."""
        if filename not in STATIC_FILES:
            self.send_response(404)
            self.end_headers()
            return
        path = os.path.join(WEB_DIR, filename)
        try:
            with open(path, "rb") as f:
                body = f.read()
        except FileNotFoundError:
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", STATIC_FILES[filename])
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        try:
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path in ("/", "/index.html"):
                self._serve_static("index.html")
            elif parsed.path == "/styles.css":
                self._serve_static("styles.css")
            elif parsed.path == "/app.js":
                self._serve_static("app.js")
            elif parsed.path == "/api/check":
                qs = urllib.parse.parse_qs(parsed.query)
                domain = (qs.get("domain", [""])[0] or "").strip()
                if not domain:
                    self._send_json({"error": "domain لازم است"}, 400)
                    return
                try:
                    r = check_domain(domain, timeout=self.server.cfg_timeout,
                                     method=self.server.cfg_method)
                except Exception as e:
                    self._send_json({"error": f"خطای داخلی سرور: {e}"}, 500)
                    return
                self._send_json(r)
            else:
                self.send_response(404)
                self.end_headers()
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:
            try:
                self._send_json({"error": f"خطای داخلی سرور: {e}"}, 500)
            except Exception:
                pass

    def do_POST(self):
        try:
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path == "/api/batch":
                length = int(self.headers.get("Content-Length", 0) or 0)
                try:
                    payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
                except Exception:
                    self._send_json({"error": "JSON نامعتبر"}, 400)
                    return
                domains = payload.get("domains", [])
                if not isinstance(domains, list):
                    self._send_json({"error": "domains باید لیست باشد"}, 400)
                    return
                domains = [str(d).strip() for d in domains if str(d).strip()][:500]
                if not domains:
                    self._send_json({"error": "لیست دامنه خالی است"}, 400)
                    return
                try:
                    results = batch_check(domains, workers=self.server.cfg_workers,
                                          delay=0.3, timeout=self.server.cfg_timeout,
                                          method=self.server.cfg_method)
                except Exception as e:
                    self._send_json({"error": f"خطای داخلی سرور: {e}"}, 500)
                    return
                self._send_json({"count": len(results), "results": results})
            else:
                self.send_response(404)
                self.end_headers()
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:
            try:
                self._send_json({"error": f"خطای داخلی سرور: {e}"}, 500)
            except Exception:
                pass


def run_web(port: int = 8000, timeout: int = DEFAULT_TIMEOUT,
            method: str = "auto", workers: int = DEFAULT_WORKERS):
    srv = ThreadingHTTPServer(("127.0.0.1", port), WebHandler)
    srv.cfg_timeout = timeout
    srv.cfg_method = method
    srv.cfg_workers = workers
    print(f"🌐 رابط وب فعال شد: http://127.0.0.1:{port}")
    print("برای توقف Ctrl+C را بزنید.\n")
    try:
        import webbrowser
        try:
            webbrowser.open(f"http://127.0.0.1:{port}")
        except Exception:
            pass
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nسرور متوقف شد.")
    finally:
        srv.server_close()


def main(argv=None):
    p = argparse.ArgumentParser(description="Persian web UI for checking .ir domains")
    p.add_argument("--port", type=int, default=8000, help="port (default: 8000)")
    p.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="per-query timeout (seconds)")
    p.add_argument("--method", choices=["auto", "socket", "http"], default="auto")
    p.add_argument("-w", "--workers", type=int, default=DEFAULT_WORKERS)
    args = p.parse_args(argv)
    run_web(args.port, args.timeout, args.method, args.workers)


if __name__ == "__main__":
    main()

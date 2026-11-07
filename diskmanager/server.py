"""Local web server: JSON API + static treemap UI. Standard library only."""
import argparse
import json
import os
import shutil
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from .scanner import Scanner, extension

STATIC = os.path.join(os.path.dirname(__file__), "static")
MAX_CHILDREN = 400  # per directory sent to the UI; the rest is merged into "other"
scanner = Scanner()


def node_json(n, depth):
    d = {"name": n.name, "size": n.size, "dir": n.is_dir}
    if n.is_dir:
        d["files"] = n.files
        if depth > 0:
            kids = n.children[:MAX_CHILDREN]
            d["children"] = [node_json(c, depth - 1) for c in kids]
            rest = n.children[MAX_CHILDREN:]
            if rest:
                d["children"].append({"name": f"({len(rest)} küçük öğe)", "size": sum(c.size for c in rest), "dir": False, "ext": "(other)"})
    else:
        d["ext"] = extension(n.name)
    return d


def type_stats(root):
    stats = {}
    stack = [root]
    while stack:
        n = stack.pop()
        if n.is_dir:
            stack.extend(n.children)
        else:
            s = stats.setdefault(extension(n.name), [0, 0])
            s[0] += n.size
            s[1] += 1
    out = [{"ext": k, "size": v[0], "count": v[1]} for k, v in stats.items()]
    out.sort(key=lambda x: x["size"], reverse=True)
    return out


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        if u.path == "/api/status":
            self._json({"running": scanner.running, "files": scanner.files_seen,
                        "bytes": scanner.bytes_seen, "current": scanner.current,
                        "errors": scanner.errors, "root": scanner.root_path,
                        "done": scanner.root is not None and not scanner.running})
        elif u.path == "/api/node":
            if scanner.root is None:
                return self._json({"error": "no scan"}, 404)
            rel = q.get("path", [""])[0]
            parts = [p for p in rel.split("/") if p]
            n = scanner.find(parts)
            if n is None:
                return self._json({"error": "not found"}, 404)
            depth = int(q.get("depth", ["1"])[0])
            self._json(node_json(n, min(depth, 6)))
        elif u.path == "/api/types":
            if scanner.root is None:
                return self._json({"error": "no scan"}, 404)
            self._json(type_stats(scanner.root))
        elif u.path == "/api/disk":
            p = scanner.root_path or os.path.expanduser("~")
            t, used, free = shutil.disk_usage(p)
            self._json({"total": t, "used": used, "free": free})
        else:
            self._static(u.path)

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        try:
            data = json.loads(self.rfile.read(n) or b"{}")
        except ValueError:
            return self._json({"error": "bad json"}, 400)
        if self.path == "/api/scan":
            try:
                scanner.start(data.get("path") or os.path.expanduser("~"))
            except (ValueError, RuntimeError) as e:
                return self._json({"error": str(e)}, 400)
            self._json({"ok": True})
        elif self.path == "/api/cancel":
            scanner.cancel()
            self._json({"ok": True})
        else:
            self._json({"error": "unknown"}, 404)

    def _static(self, path):
        if path == "/":
            path = "/index.html"
        full = os.path.normpath(os.path.join(STATIC, path.lstrip("/")))
        if not full.startswith(STATIC) or not os.path.isfile(full):
            self.send_error(404)
            return
        ctype = {"html": "text/html", "js": "text/javascript", "css": "text/css"}.get(full.rsplit(".", 1)[-1], "application/octet-stream")
        with open(full, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    ap = argparse.ArgumentParser(description="Disk usage treemap (Disk Inventory X benzeri)")
    ap.add_argument("path", nargs="?", help="Başlangıçta taranacak klasör")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()
    if args.path:
        scanner.start(args.path)
    # Bind to localhost only: the UI exposes your file names.
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    url = f"http://127.0.0.1:{args.port}/"
    print("Açık:", url)
    if not args.no_browser:
        webbrowser.open(url)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()

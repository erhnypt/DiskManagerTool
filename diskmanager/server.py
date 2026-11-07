"""Local web server: JSON API + static treemap UI. Standard library only."""
import argparse
import faulthandler
import hashlib
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from . import appcleaner
from .scanner import Scanner, extension

STATIC = os.path.join(os.path.dirname(__file__), "static")
MAX_CHILDREN = 400  # per directory sent to the UI; the rest is merged into "other"
scanner = Scanner()
# id -> (app, {path: leftover}) from the last lookup; trash requests are
# validated against this so the client can never name arbitrary paths.
app_cache = {}
app_sizes = {}  # {"state": {"sizes": {id: size}, "done": bool}}, filled by a background thread
cache_items = {}  # path -> item from the last /api/caches listing


def code_version():
    """Hash of the app's source and UI files. The launcher compares it with the
    running server's value so an outdated background server gets restarted."""
    h = hashlib.sha1()
    base = os.path.dirname(__file__)
    for root, _, files in sorted(os.walk(base)):
        for f in sorted(files):
            if f.endswith((".py", ".html")):
                with open(os.path.join(root, f), "rb") as fh:
                    h.update(fh.read())
    return h.hexdigest()[:12]


VERSION = code_version()


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


def reveal(full):
    """Show a file in the OS file manager (Finder on macOS)."""
    if sys.platform == "darwin":
        cmd = ["open", "-R", full]
    elif sys.platform.startswith("win"):
        cmd = ["explorer", "/select,", full]
    else:
        cmd = ["xdg-open", full if os.path.isdir(full) else os.path.dirname(full)]
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


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
        if u.path == "/api/progress":
            # Estimate: bytes found so far vs. bytes used on the disk. Only
            # meaningful for a whole-disk scan, so other roots get no total.
            used = None
            if scanner.root_path == "/":
                try:
                    used = shutil.disk_usage("/")[1]
                except OSError:
                    pass
            self._json({"seen": scanner.bytes_seen, "used": used,
                        "elapsed": round(time.time() - scanner.started_at, 1) if scanner.running else 0})
        elif u.path == "/api/version.txt":  # plain text: easy for the shell launcher
            body = VERSION.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif u.path == "/api/version":
            self._json({"version": VERSION})
        elif u.path == "/api/status":
            self._json({"running": scanner.running, "files": scanner.files_seen,
                        "bytes": scanner.bytes_seen, "current": scanner.current,
                        "errors": scanner.errors, "root": scanner.root_path,
                        "error": scanner.error, "cancelled": scanner.cancelled,
                        "stalled": round(time.time() - scanner.current_since) if scanner.running else 0,
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
        elif u.path == "/api/top":
            if scanner.root is None:
                return self._json({"error": "no scan"}, 404)
            n = max(1, min(int(q.get("n", ["100"])[0]), 1000))
            self._json([{"size": sz, "path": parts} for sz, parts in scanner.top_files(n)])
        elif u.path == "/api/types":
            if scanner.root is None:
                return self._json({"error": "no scan"}, 404)
            self._json(type_stats(scanner.root))
        elif u.path == "/api/apps":
            # Return the list at once; sizes (slow: walks every bundle) are
            # computed in the background and fetched via /api/app-sizes.
            apps = appcleaner.list_apps(with_size=False)
            for i, a in enumerate(apps):
                a["id"] = i
                a["protected"] = appcleaner.is_protected(a)
            app_cache.clear()
            for a in apps:
                app_cache[a["id"]] = (a, None)
            state = {"sizes": {}, "done": False}

            def compute(items, state):
                for a in items:
                    state["sizes"][a["id"]] = appcleaner.path_size(a["path"])
                state["done"] = True

            threading.Thread(target=compute, args=(list(apps), state), daemon=True).start()
            app_sizes["state"] = state
            self._json(apps)
        elif u.path == "/api/app-sizes":
            st = app_sizes.get("state") or {"sizes": {}, "done": True}
            self._json({"sizes": st["sizes"], "done": st["done"]})
        elif u.path == "/api/caches":
            items = appcleaner.list_caches()
            cache_items.clear()
            cache_items.update({i["path"]: i for i in items})
            self._json(items)
        elif u.path == "/api/app-files":
            entry = app_cache.get(int(q.get("id", ["-1"])[0]))
            if entry is None:
                return self._json({"error": "unknown app, reload list"}, 404)
            app = entry[0]
            files = appcleaner.find_leftovers(app)
            app_cache[app["id"]] = (app, {f["path"]: f for f in files})
            self._json({"app": app, "files": files})
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
                scanner.start(scanner.root_path or "/")
            except (ValueError, RuntimeError) as e:
                return self._json({"error": str(e)}, 400)
            self._json({"ok": True})
        elif self.path == "/api/reveal":
            # Only paths inside the scanned tree are accepted (looked up in the
            # tree, never taken verbatim from the client).
            parts = [p for p in str(data.get("path", "")).split("/") if p]
            n = scanner.find(parts) if scanner.root else None
            if n is None:
                return self._json({"error": "not found"}, 404)
            full = n.path(scanner.root_path)
            if not os.path.lexists(full):
                return self._json({"error": "file no longer exists"}, 404)
            try:
                reveal(full)
            except OSError as e:
                return self._json({"error": str(e)}, 500)
            self._json({"ok": True})
        elif self.path == "/api/trash":
            if scanner.root is None or scanner.running:
                return self._json({"error": "scan not finished"}, 409)
            parts = [p for p in str(data.get("path", "")).split("/") if p]
            n = scanner.find(parts) if parts else None  # the scan root is never allowed
            if n is None:
                return self._json({"error": "not found"}, 404)
            full = n.path(scanner.root_path)
            if not os.path.lexists(full):
                return self._json({"error": "file no longer exists"}, 404)
            moved, failed = appcleaner.move_to_trash([full])
            if failed:
                return self._json({"error": failed[0]["error"]}, 500)
            scanner.remove(n)
            self._json({"ok": True, "size": n.size})
        elif self.path == "/api/cache-trash":
            paths = data.get("paths") or []
            bad = [p for p in paths if p not in cache_items]
            if bad or not paths:
                return self._json({"error": "paths not allowed", "paths": bad}, 400)
            moved, failed = appcleaner.move_to_trash(paths)
            for p in moved:
                cache_items.pop(p, None)
            self._json({"moved": moved, "failed": failed})
        elif self.path == "/api/app-trash":
            entry = app_cache.get(data.get("id"))
            if entry is None or entry[1] is None:
                return self._json({"error": "unknown app, reload"}, 404)
            app, allowed = entry
            if appcleaner.is_protected(app):
                return self._json({"error": "system apps cannot be removed"}, 403)
            paths = data.get("paths") or []
            valid = set(allowed)
            if data.get("remove_app"):
                valid.add(app["path"])
            bad = [p for p in paths if p not in valid]
            if bad or not (paths or data.get("remove_app")):
                return self._json({"error": "paths not allowed", "paths": bad}, 400)
            if data.get("remove_app"):
                paths = [app["path"]] + [p for p in paths if p != app["path"]]
            moved, failed = appcleaner.move_to_trash(paths)
            self._json({"moved": moved, "failed": failed})
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
    faulthandler.enable()  # Python traceback in the log on a fatal crash
    ap = argparse.ArgumentParser(description="Disk usage treemap (Disk Inventory X benzeri)")
    ap.add_argument("path", nargs="?", default="/", help="Taranacak klasör (varsayılan: tüm disk, /)")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()
    print(time.strftime("%F %T"), "tarama başlıyor:", args.path, flush=True)
    scanner.start(args.path)  # starts scanning right away, no prompt
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

"""AppCleaner-style helper: list installed macOS apps, find their leftovers
in ~/Library and move them to the Trash. Nothing is ever deleted permanently."""
import os
import plistlib
import shutil
import time

HOME = os.path.expanduser("~")
APP_DIRS = ["/Applications", os.path.join(HOME, "Applications")]
LIBRARY = os.path.join(HOME, "Library")
TRASH = os.path.join(HOME, ".Trash")

# Library subfolders where apps keep data. "name" = may also match the app name.
LOCATIONS = [
    ("Application Support", True), ("Caches", True), ("Logs", True),
    ("Preferences", False), ("Containers", False), ("Group Containers", False),
    ("Saved Application State", False), ("LaunchAgents", False),
    ("WebKit", False), ("HTTPStorages", False), ("Cookies", False),
    ("Application Scripts", False), ("Preferences/ByHost", False),
    ("Logs/DiagnosticReports", False),
]


def path_size(path):
    """Disk usage of a file or directory (st_blocks, symlinks not followed)."""
    try:
        st = os.lstat(path)
    except OSError:
        return 0
    if not os.path.isdir(path) or os.path.islink(path):
        return st.st_blocks * 512
    total = st.st_blocks * 512
    seen = set()
    for root, dirs, files in os.walk(path):
        for n in dirs + files:
            try:
                s = os.lstat(os.path.join(root, n))
            except OSError:
                continue
            if not os.path.isdir(os.path.join(root, n)) or os.path.islink(os.path.join(root, n)):
                if s.st_nlink > 1:
                    if (s.st_dev, s.st_ino) in seen:
                        continue
                    seen.add((s.st_dev, s.st_ino))
            total += s.st_blocks * 512
    return total


def read_app(app_path):
    plist = os.path.join(app_path, "Contents", "Info.plist")
    try:
        with open(plist, "rb") as f:
            info = plistlib.load(f)
    except (OSError, ValueError, plistlib.InvalidFileException):
        return None
    base = os.path.splitext(os.path.basename(app_path))[0]
    return {
        "path": app_path,
        "bundle_id": info.get("CFBundleIdentifier", ""),
        "name": info.get("CFBundleDisplayName") or info.get("CFBundleName") or base,
        "file_name": base,
        "version": info.get("CFBundleShortVersionString", ""),
    }


def list_apps(app_dirs=None):
    apps = []
    for d in app_dirs or APP_DIRS:
        try:
            entries = sorted(os.listdir(d))
        except OSError:
            continue
        for e in entries:
            if e.endswith(".app"):
                a = read_app(os.path.join(d, e))
                if a:
                    a["size"] = path_size(a["path"])
                    apps.append(a)
    apps.sort(key=lambda a: a["size"], reverse=True)
    return apps


def is_protected(app):
    return app["bundle_id"].startswith("com.apple.") or app["path"].startswith("/System/")


def find_leftovers(app, library=None):
    """Return [{path, size, kind}] of files that clearly belong to the app.
    Matching is deliberately conservative: bundle id (exact or id.*), or the
    exact app name in Application Support / Caches / Logs."""
    lib = library or LIBRARY
    bid = app["bundle_id"].lower()
    names = {app["name"].lower(), app["file_name"].lower()}
    out = []
    for sub, by_name in LOCATIONS:
        d = os.path.join(lib, sub)
        try:
            entries = os.listdir(d)
        except OSError:
            continue
        for e in entries:
            el = e.lower()
            stem = el.rsplit(".", 1)[0] if el.endswith((".plist", ".savedstate")) else el
            match = False
            if bid:
                match = (stem == bid or el == bid or stem.startswith(bid + ".")
                         or (sub == "Group Containers" and el.endswith("." + bid)))
            if not match and by_name:
                match = el in names
            if match:
                p = os.path.join(d, e)
                out.append({"path": p, "size": path_size(p), "kind": sub})
    return out


def move_to_trash(paths, trash=None):
    trash = trash or TRASH
    os.makedirs(trash, exist_ok=True)
    moved, failed = [], []
    for p in paths:
        base = os.path.basename(p.rstrip("/"))
        dest = os.path.join(trash, base)
        if os.path.lexists(dest):
            dest = os.path.join(trash, f"{base} {int(time.time())}")
        try:
            shutil.move(p, dest)
            moved.append(p)
        except (OSError, shutil.Error) as e:
            failed.append({"path": p, "error": str(e)})
    return moved, failed

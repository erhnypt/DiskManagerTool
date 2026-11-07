"""Disk scanner: builds an in-memory size tree of a directory."""
import glob
import os
import sys
import time
import threading


class Node:
    __slots__ = ("name", "size", "is_dir", "children", "files", "parent")

    def __init__(self, name, is_dir=False, size=0, parent=None):
        self.name = name
        self.is_dir = is_dir
        self.size = size
        self.children = [] if is_dir else None
        self.files = 0  # number of files below (dirs only)
        self.parent = parent

    def path(self, root_path):
        parts = []
        n = self
        while n.parent is not None:
            parts.append(n.name)
            n = n.parent
        return os.path.join(root_path, *reversed(parts))


def default_skip():
    """Paths left out of a whole-disk scan: virtual filesystems, other volumes
    and (macOS) the Data volume mirror, whose contents already appear through
    firmlinks such as /Users — scanning it too would count everything twice."""
    if sys.platform == "darwin":
        cloud = set()
        for home in glob.glob("/Users/*"):
            cloud.add(os.path.join(home, "Library", "CloudStorage"))
            cloud.add(os.path.join(home, "Library", "Mobile Documents"))
        return cloud | {"/System/Volumes", "/Volumes", "/dev", "/.vol", "/Network", "/cores", "/.Spotlight-V100", "/.fseventsd"}
    return {"/proc", "/sys", "/dev", "/run", "/mnt", "/media"}


class Scanner:
    def __init__(self):
        self.root = None
        self.root_path = None
        self.running = False
        self.cancelled = False
        self.error = None
        self.files_seen = 0
        self.bytes_seen = 0
        self.current = ""
        self.current_since = time.time()
        self.started_at = time.time()
        self.errors = 0
        self.skip = default_skip()
        self._gen = 0  # bumped by start()/cancel(); a stale worker exits quietly
        self._thread = None
        self._lock = threading.Lock()

    def start(self, path):
        path = os.path.abspath(os.path.expanduser(path))
        if not os.path.isdir(path):
            raise ValueError(f"Not a directory: {path}")
        with self._lock:
            if self.running:
                raise RuntimeError("A scan is already running")
            self._gen += 1
            gen = self._gen
            self.running = True
            self.cancelled = False
            self.error = None
            self.files_seen = self.bytes_seen = self.errors = 0
            self.current, self.current_since = path, time.time()
            self.started_at = time.time()
            self.root = None
            self.root_path = path
        self._thread = threading.Thread(target=self._run, args=(path, gen), daemon=True)
        self._thread.start()

    def cancel(self):
        """Stop at once. A worker blocked inside a syscall (iCloud / network
        folders) cannot be interrupted, so the scan is detached instead: the
        generation changes, the state resets immediately and the stale worker
        exits as soon as it wakes up, without touching the new state."""
        with self._lock:
            if self.running:
                self._gen += 1
                self.running = False
                self.cancelled = True
                self.root = None

    def _alive(self, gen):
        return gen == self._gen

    def _run(self, path, gen):
        try:
            root = Node(path, is_dir=True)
            self._walk(path, root, set(), gen)
            if not self._alive(gen):
                return
            self._finalize(root)
            root.name = path
            self.root = root
        except Exception as e:  # never die silently: surface it in the UI
            if self._alive(gen):
                self.error = f"{type(e).__name__}: {e}"
        finally:
            with self._lock:
                if self._alive(gen):
                    self.running = False

    def _walk(self, path, node, seen, gen):
        # Iterative DFS to avoid recursion limits on deep trees.
        stack = [(path, node)]
        while stack:
            if not self._alive(gen):
                return
            dpath, dnode = stack.pop()
            self.current, self.current_since = dpath, time.time()
            try:
                it = os.scandir(dpath)
            except OSError:
                self.errors += 1
                continue
            with it:
                while True:
                    try:
                        entry = next(it)
                    except StopIteration:
                        break
                    except OSError:  # directory changed/unreadable mid-listing
                        self.errors += 1
                        break
                    if not self._alive(gen):
                        return
                    if entry.path in self.skip:
                        continue
                    try:
                        st = entry.stat(follow_symlinks=False)
                        if entry.is_symlink():
                            continue
                        if entry.is_dir(follow_symlinks=False):
                            child = Node(entry.name, True, parent=dnode)
                            dnode.children.append(child)
                            stack.append((entry.path, child))
                        else:
                            if st.st_nlink > 1:
                                key = (st.st_dev, st.st_ino)
                                if key in seen:
                                    continue
                                seen.add(key)
                            # st_blocks is real disk usage (handles sparse files)
                            size = getattr(st, "st_blocks", None)
                            size = size * 512 if size is not None else st.st_size
                            child = Node(entry.name, False, size, dnode)
                            dnode.children.append(child)
                            self.files_seen += 1
                            self.bytes_seen += size
                    except (OSError, ValueError):
                        self.errors += 1

    def _finalize(self, root):
        # Post-order size aggregation, iterative.
        order = []
        stack = [root]
        while stack:
            n = stack.pop()
            order.append(n)
            if n.is_dir:
                stack.extend(n.children)
        for n in reversed(order):
            if n.is_dir:
                n.size = sum(c.size for c in n.children)
                n.files = sum(1 if not c.is_dir else c.files for c in n.children)
                n.children.sort(key=lambda c: c.size, reverse=True)

    def remove(self, node):
        """Detach a node (after it was trashed) and fix ancestor totals."""
        if node.parent is None:
            raise ValueError("cannot remove the scan root")
        node.parent.children.remove(node)
        count = node.files if node.is_dir else 1
        a = node.parent
        while a is not None:
            a.size -= node.size
            a.files -= count
            a = a.parent

    def top_files(self, n=100):
        """The n largest files in the tree as (size, relative parts)."""
        import heapq
        found = []
        stack = [self.root]
        while stack:
            d = stack.pop()
            for c in d.children:
                if c.is_dir:
                    stack.append(c)
                else:
                    found.append(c)
        best = heapq.nlargest(n, found, key=lambda c: c.size)
        out = []
        for c in best:
            parts, x = [], c
            while x.parent is not None:
                parts.append(x.name)
                x = x.parent
            out.append((c.size, list(reversed(parts))))
        return out

    def find(self, rel_parts):
        n = self.root
        for part in rel_parts:
            if n is None or not n.is_dir:
                return None
            n = next((c for c in n.children if c.name == part), None)
        return n


def extension(name):
    ext = os.path.splitext(name)[1].lower()
    return ext if ext else "(none)"

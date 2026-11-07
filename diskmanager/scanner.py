"""Disk scanner: builds an in-memory size tree of a directory."""
import os
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


class Scanner:
    def __init__(self):
        self.root = None
        self.root_path = None
        self.running = False
        self.files_seen = 0
        self.bytes_seen = 0
        self.current = ""
        self.errors = 0
        self._cancel = False
        self._thread = None
        self._lock = threading.Lock()

    def start(self, path):
        path = os.path.abspath(os.path.expanduser(path))
        if not os.path.isdir(path):
            raise ValueError(f"Not a directory: {path}")
        with self._lock:
            if self.running:
                raise RuntimeError("A scan is already running")
            self.running = True
            self._cancel = False
            self.files_seen = self.bytes_seen = self.errors = 0
            self.root = None
            self.root_path = path
        self._thread = threading.Thread(target=self._run, args=(path,), daemon=True)
        self._thread.start()

    def cancel(self):
        self._cancel = True

    def _run(self, path):
        try:
            root = Node(path, is_dir=True)
            seen_inodes = set()
            self._walk(path, root, seen_inodes)
            self._finalize(root)
            root.name = path
            self.root = root
        finally:
            self.running = False

    def _walk(self, path, node, seen):
        # Iterative DFS to avoid recursion limits on deep trees.
        stack = [(path, node)]
        while stack:
            if self._cancel:
                return
            dpath, dnode = stack.pop()
            self.current = dpath
            try:
                it = os.scandir(dpath)
            except OSError:
                self.errors += 1
                continue
            with it:
                for entry in it:
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
                    except OSError:
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

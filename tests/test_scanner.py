import os, tempfile, unittest
from diskmanager.scanner import Scanner


class ScannerTest(unittest.TestCase):
    def test_sizes_and_sorting(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "a", "b"))
            with open(os.path.join(d, "big.bin"), "wb") as f: f.write(os.urandom(200_000))
            with open(os.path.join(d, "a", "b", "small.txt"), "wb") as f: f.write(os.urandom(5_000))
            os.symlink(os.path.join(d, "big.bin"), os.path.join(d, "link"))
            os.link(os.path.join(d, "big.bin"), os.path.join(d, "hard.bin"))
            s = Scanner(); s.start(d)
            s._thread.join()
            root = s.root
            self.assertEqual(root.files, 2)  # symlink skipped, hardlink counted once
            self.assertEqual(root.children[0].name in ("big.bin", "hard.bin"), True)  # largest first
            self.assertGreaterEqual(root.size, 205_000)
            self.assertIsNotNone(s.find(["a", "b", "small.txt"]))


if __name__ == "__main__":
    unittest.main()


class TopAndRemoveTest(unittest.TestCase):
    def test_top_and_remove(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "x"))
            for name, n in [("a", 100_000), ("x/b", 300_000), ("c", 10_000)]:
                with open(os.path.join(d, name), "wb") as f: f.write(os.urandom(n))
            s = Scanner(); s.start(d); s._thread.join()
            top = s.top_files(2)
            self.assertEqual([p for _, p in top], [["x", "b"], ["a"]])
            before = s.root.size
            node = s.find(["x"]); sz = node.size
            s.remove(node)
            self.assertEqual(s.root.size, before - sz)
            self.assertEqual(s.root.files, 2)
            with self.assertRaises(ValueError):
                s.remove(s.root)


class SkipTest(unittest.TestCase):
    def test_skip_paths(self):
        with tempfile.TemporaryDirectory() as d:
            for n in ("keep", "skipme"):
                os.makedirs(os.path.join(d, n))
                with open(os.path.join(d, n, "f"), "wb") as f: f.write(os.urandom(10_000))
            s = Scanner(); s.skip = {os.path.join(os.path.abspath(d), "skipme")}
            s.start(d); s._thread.join()
            self.assertEqual([c.name for c in s.root.children], ["keep"])


class RobustnessTest(unittest.TestCase):
    def test_listing_error_does_not_kill_scan(self):
        import unittest.mock as m
        real = os.scandir

        class Boom:
            def __init__(self, it): self.it = it; self.n = 0
            def __enter__(self): return self
            def __exit__(self, *a): self.it.close()
            def __iter__(self): return self
            def __next__(self):
                self.n += 1
                if self.n == 2: raise OSError("dir vanished")
                return next(self.it)

        with tempfile.TemporaryDirectory() as d:
            for n in "abc":
                open(os.path.join(d, n), "wb").write(b"x" * 5000)
            with m.patch("os.scandir", lambda p: Boom(real(p))):
                s = Scanner(); s.start(d); s._thread = None
                import time
                for _ in range(100):
                    if not s.running: break
                    time.sleep(0.02)
            self.assertFalse(s.running)
            self.assertIsNotNone(s.root)  # finished, not crashed
            self.assertEqual(s.errors, 1)

    def test_cancel_works_even_if_worker_is_blocked(self):
        import threading, time, unittest.mock as m
        block = threading.Event()
        real = os.scandir
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "hang"))
            def slow(p):
                if p.endswith("hang"): block.wait(5)
                return real(p)
            with m.patch("os.scandir", slow):
                s = Scanner(); s.start(d)
                time.sleep(0.2)
                self.assertTrue(s.running)
                t = time.time(); s.cancel()
                self.assertFalse(s.running); self.assertTrue(s.cancelled)
                self.assertLess(time.time() - t, 0.5)
                s.start(d)  # a new scan may start while the old worker hangs
                block.set()
                for _ in range(100):
                    if not s.running: break
                    time.sleep(0.02)
                self.assertIsNotNone(s.root)
                self.assertFalse(s.cancelled)

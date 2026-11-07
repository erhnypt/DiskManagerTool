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

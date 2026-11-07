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

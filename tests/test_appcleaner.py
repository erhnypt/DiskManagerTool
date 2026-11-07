import os, plistlib, tempfile, unittest
from diskmanager import appcleaner as ac


def mkapp(root, name, bid):
    c = os.path.join(root, name + ".app", "Contents")
    os.makedirs(c)
    with open(os.path.join(c, "Info.plist"), "wb") as f:
        plistlib.dump({"CFBundleIdentifier": bid, "CFBundleName": name}, f)
    return os.path.join(root, name + ".app")


def touch(path, data=b"x" * 5000):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "wb").write(data)


class AppCleanerTest(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.apps = os.path.join(self.t.name, "Applications")
        self.lib = os.path.join(self.t.name, "Library")
        os.makedirs(self.apps)
        self.app = mkapp(self.apps, "Foo", "com.acme.foo")
        mkapp(self.apps, "Safari", "com.apple.Safari")

    def tearDown(self):
        self.t.cleanup()

    def test_list_and_protect(self):
        apps = ac.list_apps([self.apps])
        self.assertEqual({a["name"] for a in apps}, {"Foo", "Safari"})
        self.assertTrue(ac.is_protected(next(a for a in apps if a["name"] == "Safari")))

    def test_leftovers_conservative(self):
        L = self.lib
        touch(f"{L}/Application Support/Foo/data.db")
        touch(f"{L}/Preferences/com.acme.foo.plist")
        touch(f"{L}/Caches/com.acme.foo/c")
        touch(f"{L}/Saved Application State/com.acme.foo.savedState/w")
        touch(f"{L}/Group Containers/ABC.com.acme.foo/x")
        touch(f"{L}/Application Support/Foobar/other")        # must NOT match
        touch(f"{L}/Preferences/com.acme.foobar.plist")       # must NOT match
        app = ac.list_apps([self.apps])
        foo = next(a for a in app if a["name"] == "Foo")
        got = {os.path.relpath(f["path"], L) for f in ac.find_leftovers(foo, L)}
        self.assertEqual(got, {"Application Support/Foo", "Preferences/com.acme.foo.plist",
                               "Caches/com.acme.foo", "Saved Application State/com.acme.foo.savedState",
                               "Group Containers/ABC.com.acme.foo"})

    def test_trash_moves_not_deletes(self):
        f = os.path.join(self.t.name, "a.txt"); touch(f)
        trash = os.path.join(self.t.name, "Trash")
        moved, failed = ac.move_to_trash([f, f], trash)
        self.assertEqual((len(moved), len(failed)), (1, 1))
        self.assertTrue(os.path.exists(os.path.join(trash, "a.txt")))


if __name__ == "__main__":
    unittest.main()

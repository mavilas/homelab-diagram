import json
import shutil
import tempfile
import unittest
from pathlib import Path

from homelab_diagram import IconError, IconStore
from homelab_diagram.icon_lock import COMMIT_RE, LOCK_FILE, LockError, load_lock, verify
from tests.helpers import ROOT


class IconLockTest(unittest.TestCase):
    def test_lock_pins_a_full_commit_and_hashes_every_icon(self):
        lock = load_lock()
        self.assertRegex(lock.commit, COMMIT_RE)
        self.assertTrue(lock.url.startswith("https://raw.githubusercontent.com/"))
        self.assertNotIn("/main/", lock.url)
        self.assertGreater(len(lock.icons), 0)
        for icon in lock.icons:
            self.assertRegex(icon.sha256 or "", r"^[0-9a-f]{64}$", icon.name)

    def test_branch_names_are_refused(self):
        raw = json.loads(LOCK_FILE.read_text())
        raw["commit"] = "main"
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp, "lock.json")
            p.write_text(json.dumps(raw))
            with self.assertRaises(LockError):
                load_lock(p)

    def test_fetched_icons_match_the_lock(self):
        self.assertEqual(verify(ROOT / "icons"), [])

    def test_fetched_icons_are_readable_by_other_users(self):
        # Images run renders as an unprivileged user, so 0600 icon files break every render.
        for icon in load_lock().icons:
            mode = (ROOT / "icons" / f"{icon.name}.svg").stat().st_mode & 0o777
            self.assertEqual(mode, 0o644, icon.name)

    def test_verify_reports_a_tampered_and_a_missing_icon(self):
        lock = load_lock()
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            for icon in lock.icons:
                shutil.copy(ROOT / "icons" / f"{icon.name}.svg", d)
            first, second = lock.icons[0].name, lock.icons[1].name
            (d / f"{first}.svg").write_text("<svg/>")
            (d / f"{second}.svg").unlink()
            problems = verify(d)
        self.assertEqual(problems, [f"{first}: sha256 does not match icons.lock.json",
                                    f"{second}: missing (run: python3 fetch_icons.py)"])


class IconStoreTest(unittest.TestCase):
    def test_names_cannot_escape_the_icon_directories(self):
        store = IconStore([ROOT / "icons"])
        for bad in ("../build", "/etc/passwd", "Glyph", ""):
            with self.assertRaises(IconError):
                store.path(bad)

    def test_missing_icon_is_loud(self):
        with self.assertRaises(IconError) as cm:
            IconStore([ROOT / "icons"]).data_uri("no-such-icon")
        self.assertIn("missing icon 'no-such-icon'", str(cm.exception.code))

    def test_svg_and_png_icons_embed_with_their_mime_type(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "a.png").write_bytes(b"\x89PNG")
            store = IconStore([tmp, ROOT / "icons"])
            self.assertTrue(store.data_uri("a").startswith("data:image/png;base64,"))
            self.assertTrue(store.data_uri("glyph-cpu").startswith("data:image/svg+xml;base64,"))


if __name__ == "__main__":
    unittest.main()

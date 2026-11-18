import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from homelab_diagram.rsvg import MIN_LIBRSVG, RSVG_ENV, PreflightError, parse_version, preflight


def fake_rsvg(directory: str, version: str, body: str = "") -> str:
    """A stand-in rsvg-convert that reports `version` and runs `body` for conversions."""
    p = Path(directory, "rsvg-convert")
    p.write_text(f'#!/bin/sh\nif [ "$1" = "--version" ]; then echo "rsvg-convert version {version}"; exit 0; fi\n'
                 f"{body}\n")
    p.chmod(p.stat().st_mode | stat.S_IEXEC)
    return str(p)


class RsvgTest(unittest.TestCase):
    def test_version_parsing(self):
        self.assertEqual(parse_version("rsvg-convert version 2.60.0\n"), (2, 60, 0))
        self.assertEqual(parse_version("rsvg-convert version 2.54"), (2, 54, 0))
        with self.assertRaises(PreflightError):
            parse_version("garbage")

    def test_minimum_is_2_60(self):
        self.assertEqual(MIN_LIBRSVG, (2, 60, 0))

    def test_old_librsvg_fails_loudly(self):
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.dict(os.environ, {RSVG_ENV: fake_rsvg(tmp, "2.54.7")}):
            with self.assertRaises(PreflightError) as cm:
                preflight()
        self.assertIn("2.54.7 is too old", str(cm.exception.code))
        self.assertIn("silently drop every icon", str(cm.exception.code))

    def test_new_version_that_still_drops_icons_fails(self):
        # Claims 2.61 but writes a black PNG: the probe pixel catches it, the version alone would not.
        real = preflight(check_fonts=False).rsvg
        body = f'out=""; while [ $# -gt 0 ]; do [ "$1" = "-o" ] && out=$2; shift; done\n' \
               f'printf \'<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20"><rect width="20" ' \
               f'height="20"/></svg>\' > "$out.svg" && "{real}" -o "$out" "$out.svg"'
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {RSVG_ENV: fake_rsvg(tmp, "2.61.0", body)}):
            with self.assertRaises(PreflightError) as cm:
                preflight()
        self.assertIn("dropped the embedded probe icon", str(cm.exception.code))

    def test_reference_environment_passes(self):
        pre = preflight()
        self.assertGreaterEqual(pre.version, MIN_LIBRSVG)


if __name__ == "__main__":
    unittest.main()

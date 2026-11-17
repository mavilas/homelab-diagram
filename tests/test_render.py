import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from homelab_diagram import IconStore, LayoutError, parse_spec, render, render_svg
from homelab_diagram.cli import main as cli
from tests.helpers import EXAMPLE, ROOT, example_raw

# The refactored original build must reproduce upstream a9a458a's SVG byte for byte (same fonts and icons).
ORIGINAL_SVG_SHA256 = {
    "homelab.svg": "ff2a5e8337b5cd636ad23e475fe925ff7fc8266b393dce0439153c5192260734",
    "homelab-unredacted.svg": "f169da12a931f806d916c54edc199050f915eeabdef93e0ba0cd0c613994e0f7",
}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


class RenderTest(unittest.TestCase):
    def test_cli_renders_spec_to_png_and_svg(self):
        with tempfile.TemporaryDirectory() as tmp:
            png, svg = Path(tmp, "x.png"), Path(tmp, "x.svg")
            self.assertEqual(cli(["render", str(EXAMPLE), "-o", str(png), "--svg", str(svg)]), 0)
            self.assertTrue(svg.read_text().startswith("<svg"))
            with Image.open(png) as im:
                self.assertEqual(im.format, "PNG")
                self.assertEqual(im.width, int(2400 * 1.6))
                # icons survived: the OPNsense icon area is not background colored
                colors = im.convert("RGB").crop((110, 390, 200, 480)).getcolors(100000)
                self.assertGreater(len(colors), 20)

    def test_rendering_is_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            outs = []
            for i in (1, 2):
                png, svg = Path(tmp, f"{i}.png"), Path(tmp, f"{i}.svg")
                render(parse_spec(example_raw()), png, svg)
                outs.append((sha(png), sha(svg)))
        self.assertEqual(outs[0], outs[1])

    def test_svg_has_no_external_references(self):
        text = render_svg(parse_spec(example_raw()), IconStore([ROOT / "icons"]))
        self.assertNotIn("http://", text.replace("http://www.w3.org/2000/svg", ""))
        self.assertNotIn("https://", text)

    def test_text_that_does_not_fit_raises_layout_error(self):
        raw = example_raw()
        raw["groups"][1]["columns"] = 8
        raw["nodes"][2]["model"] = "A very long model name that cannot possibly fit"
        with self.assertRaises(LayoutError):
            render_svg(parse_spec(raw), IconStore([ROOT / "icons"]))

    def test_validate_and_check_commands(self):
        self.assertEqual(cli(["validate", str(EXAMPLE)]), 0)
        self.assertEqual(cli(["check", "--icon-dir", str(ROOT / "icons")]), 0)

    def test_missing_icon_fails_before_writing(self):
        raw = example_raw()
        raw["nodes"][0]["icon"] = "not-there"
        with tempfile.TemporaryDirectory() as tmp:
            spec = Path(tmp, "s.json")
            import json
            spec.write_text(json.dumps(raw))
            png = Path(tmp, "x.png")
            self.assertEqual(cli(["render", str(spec), "-o", str(png)]), 1)
            self.assertFalse(png.exists())

    def test_original_build_is_byte_identical_to_upstream(self):
        for flag in ([], ["--unredacted"]):
            subprocess.run([sys.executable, "build.py", *flag], cwd=ROOT, check=True, capture_output=True)
        for name, digest in ORIGINAL_SVG_SHA256.items():
            self.assertEqual(sha(ROOT / "out" / name), digest, name)


class AgentInstructionsTest(unittest.TestCase):
    def test_agent_docs_do_not_ask_for_commands_on_live_hosts(self):
        text = (ROOT / "CLAUDE.md").read_text().lower()
        for phrase in ("pct list", "docker ps", "zpool", "midclt", "shell access", "live systems", "ip -br"):
            self.assertNotIn(phrase, text)
        self.assertIn("never run commands on", text)


if __name__ == "__main__":
    unittest.main()

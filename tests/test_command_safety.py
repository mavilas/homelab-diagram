"""Exercise actual child processes without touching services or installing tools."""
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from homelab_diagram.rsvg import librsvg_version, PreflightError


class CommandSafetyTests(unittest.TestCase):
    def test_timed_out_converter_receives_term(self):
        with tempfile.TemporaryDirectory() as tmp:
            marker = Path(tmp, "term")
            executable = Path(tmp, "converter")
            executable.write_text(
                f"#!/bin/sh\ntrap 'echo term > \"{marker}\"; exit 0' TERM\n"
                "while :; do sleep .01; done\n"
            )
            executable.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
            with patch("homelab_diagram.rsvg.RSVG_TIMEOUT_S", .2):
                with self.assertRaises(PreflightError):
                    librsvg_version(str(executable))
            self.assertTrue(marker.exists(), "timeout killed the converter without TERM cleanup")

    def test_failed_version_command_cannot_pass_preflight(self):
        with tempfile.TemporaryDirectory() as tmp:
            executable = Path(tmp, "converter")
            executable.write_text('#!/bin/sh\necho "rsvg-convert version 2.60.0"\nexit 1\n')
            executable.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
            with self.assertRaises(PreflightError):
                librsvg_version(str(executable))

    def test_failed_conversion_preserves_existing_outputs(self):
        from types import SimpleNamespace
        from homelab_diagram import parse_spec, render
        from homelab_diagram.commands import CommandError
        spec = parse_spec({"version": 1, "title": "x", "nodes": [{"id": "x", "label": "x"}]})
        with tempfile.TemporaryDirectory() as tmp:
            png, svg = Path(tmp, "x.png"), Path(tmp, "x.svg")
            png.write_bytes(b"previous png")
            svg.write_text("previous svg")
            executable = Path(tmp, "converter")
            executable.write_text('#!/bin/sh\nwhile [ "$1" != "-o" ]; do shift; done\nprintf partial > "$2"\nexit 1\n')
            executable.chmod(0o700)
            with patch("homelab_diagram.render.preflight", return_value=SimpleNamespace(rsvg=str(executable))):
                with self.assertRaises(CommandError):
                    render(spec, png, svg)
            self.assertEqual(png.read_bytes(), b"previous png")
            self.assertEqual(svg.read_text(), "previous svg")

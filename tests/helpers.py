"""Shared test fixtures. Render tests need the reference environment (librsvg >= 2.60, Fira fonts,
fetched icons); they fail rather than skip when it is missing, see README "Tests"."""
import copy
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
EXAMPLE = ROOT / "examples" / "small-lab.yaml"


def example_raw() -> dict:
    return copy.deepcopy(yaml.safe_load(EXAMPLE.read_text()))

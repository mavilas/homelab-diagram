"""Copy the canonical source assets into wheels without duplicating source data."""
from pathlib import Path
import runpy
import shutil

from setuptools import setup
from setuptools.command.build_py import build_py

paths = runpy.run_path(str(Path(__file__).parent / "homelab_diagram/resource_paths.py"))


class BuildWithResources(build_py):
    def run(self):
        super().run()
        root = paths["SOURCE_ROOT"]
        destination = Path(self.build_lib) / paths["PACKAGE_NAME"] / paths["ASSET_DIRECTORY"]
        icons = destination / paths["ICON_DIRECTORY"]
        icons.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / paths["LOCK_FILENAME"], destination / paths["LOCK_FILENAME"])
        for source in (root / paths["ICON_DIRECTORY"]).glob(paths["OWN_GLYPH_PATTERN"]):
            shutil.copyfile(source, icons / source.name)


setup(cmdclass={"build_py": BuildWithResources})

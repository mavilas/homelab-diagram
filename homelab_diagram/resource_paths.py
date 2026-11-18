"""One resource layout contract for source checkouts and built distributions."""
from pathlib import Path

PACKAGE_NAME = "homelab_diagram"
ASSET_DIRECTORY = "_assets"
LOCK_FILENAME = "icons.lock.json"
ICON_DIRECTORY = "icons"
OWN_GLYPH_PATTERN = "glyph-*.svg"
SOURCE_ROOT = Path(__file__).resolve().parent.parent
RESOURCE_ROOT = (SOURCE_ROOT if (SOURCE_ROOT / LOCK_FILENAME).is_file()
                 else Path(__file__).resolve().parent / ASSET_DIRECTORY)

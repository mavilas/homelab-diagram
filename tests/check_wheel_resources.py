"""Artifact regression: installed resources work outside the source checkout.

Run after building a wheel: python tests/check_wheel_resources.py path/to.whl.
"""
from pathlib import Path, PurePosixPath
import sys
import tempfile
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from homelab_diagram._term_group import run_group

with tempfile.TemporaryDirectory() as tmp:
    with zipfile.ZipFile(sys.argv[1]) as wheel:
        names = wheel.namelist()
        assert any(n.endswith('/icons.lock.json') for n in names), 'wheel has no icon lock'
        assert any('/glyph-' in n for n in names), 'wheel has no own glyphs'
        assert all(not PurePosixPath(n).is_absolute() and '..' not in PurePosixPath(n).parts
                   for n in names), 'unsafe wheel path'
        wheel.extractall(tmp)
    code = '''import sys
sys.path.insert(0, sys.argv[1])
from homelab_diagram.icon_lock import load_lock
from homelab_diagram.icons import IconStore
assert load_lock().icons
assert IconStore().data_uri("glyph-cpu").startswith("data:image/svg+xml;base64,")
'''
    result = run_group([sys.executable, '-I', '-c', code, tmp], timeout=30, text=True)
    assert result.returncode == 0, result.stderr
print('PASS: installed wheel lock and glyph resources')

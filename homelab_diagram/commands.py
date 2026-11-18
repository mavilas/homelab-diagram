"""One boundary for bounded external font and rendering tools.

The vendored supervisor terminates the complete process group with SIGTERM,
never escalates, and reports surviving groups. No child output enters errors.
"""
from ._term_group import GroupSurvived, run_group
import subprocess


class CommandError(SystemExit):
    """An external tool failed, timed out, or left a surviving process group."""


def run(argv: list[str], timeout: float):
    try:
        result = run_group(argv, timeout=timeout, text=True)
    except (OSError, subprocess.SubprocessError, GroupSurvived):
        raise CommandError("external tool failed or exceeded its deadline") from None
    if result.returncode:
        raise CommandError("external tool returned a failure status")
    return result

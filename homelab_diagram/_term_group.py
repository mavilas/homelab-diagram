"""Run one child process tree with a bounded, TERM-only stop (test and mutation runners).

subprocess.run(timeout=...) sends SIGKILL to the direct child only. Its
grandchildren (unittest servers, ci_shards workers) are reparented to PID 1 and
keep running: 20 idle ci_shards workers from 5 mutation runs were found on m2,
2.5 to 3.2 hours old (2026-11-11). run_group() replaces that call:

- The child starts in its own session (start_new_session=True), so its pid is
  the process group id of every process it starts and does not move elsewhere.
- On the timeout, on SIGTERM, SIGINT or SIGHUP to this process, or on any
  exception while waiting, the whole group gets SIGTERM, then at most `grace`
  seconds to exit. A group still alive after that is reported on stderr and
  left running. Nothing here sends SIGKILL (gate ruling 2026-11-11 13:11 JST).
- It fails closed: a timeout raises GroupTimeout (a subprocess.TimeoutExpired),
  a signal runs the handler it replaced and raises GroupInterrupted if that
  handler returns; a raising handler retains its exception and receives
  signum/survivor evidence. A group member left behind by a child that exited normally is stopped the
  same way and raises GroupSurvived if it outlives the grace.
- The TERM/INT/HUP handlers it installs are restored on every exit.

Stdlib only, main thread only (Python installs signal handlers there).

Accepted residual: after the leader is reaped, group_alive(pgid) asks about a
group id that no member may hold any more. In that microsecond window an
unrelated new session leader that got the same pid could be seen as our group
and get a SIGTERM. That is extremely unlikely and accepted; while any member
of our group is alive, the pid cannot be reused.
"""

from __future__ import annotations

import math
import os
import signal
import subprocess
import sys
import threading
import time

TERM_GRACE_S = 10.0
POLL_S = 0.1
CANCEL_SIGNALS = (signal.SIGTERM, signal.SIGINT, signal.SIGHUP)


class GroupTimeout(subprocess.TimeoutExpired):
    """The child ran past its timeout. `survivor` is the group id left running, or None."""

    def __init__(self, cmd, timeout, output=None, stderr=None, survivor=None):
        super().__init__(cmd, timeout, output, stderr)
        self.survivor = survivor

    def __str__(self):
        text = super().__str__()
        if self.survivor is not None:
            text += f"; process group {self.survivor} outlived SIGTERM and was left running"
        return text


class GroupInterrupted(RuntimeError):
    """This process got a cancel signal while the child ran; the group was stopped first."""

    def __init__(self, signum, survivor=None):
        super().__init__(f"interrupted by signal {signum}; child process group stopped with SIGTERM"
                         + ("" if survivor is None else f", group {survivor} left running"))
        self.signum, self.survivor = signum, survivor


class GroupSurvived(RuntimeError):
    """The child exited but a process it left in its group outlived SIGTERM."""

    def __init__(self, result, survivor):
        super().__init__(f"process group {survivor} outlived SIGTERM after its leader exited; left running")
        self.result, self.survivor = result, survivor


def group_alive(pgid: int) -> bool:
    """Signal 0 delivers nothing; it only asks whether any member of the group exists."""
    try:
        os.killpg(pgid, 0)
    except (ProcessLookupError, PermissionError):
        return False  # PermissionError: macOS, only a zombie is left in the group
    return True


def _bounded(name, value, allow_zero=False):
    if not (isinstance(value, (int, float)) and math.isfinite(value) and (value >= 0 if allow_zero else value > 0)):
        raise ValueError(f"{name} must be a finite {'non-negative' if allow_zero else 'positive'} number, "
                         f"got {value!r}")
    return float(value)


def _decode(data, text):
    if data is None or not text or isinstance(data, str):
        return data
    return data.decode(errors="replace")


def _close_pipes(process):
    for stream in (process.stdout, process.stderr):
        if stream is not None and not stream.closed:
            stream.close()


def stop_group(process: subprocess.Popen, grace: float, stream=None, text=False):
    """SIGTERM the child's group, wait at most `grace`, return (survivor pgid or None, stdout, stderr).

    Never escalates: a survivor is reported on `stream` (stderr) and left running.
    """
    pgid = process.pid
    # While the leader is unreaped its pid cannot be reused; once reaped, a pid
    # that still names a live group cannot be reused either.
    if process.returncode is None or group_alive(pgid):
        try:
            os.killpg(pgid, signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            pass
    deadline = time.monotonic() + grace
    stdout = stderr = None
    done = False
    while True:
        remaining = deadline - time.monotonic()
        if not done:
            try:
                stdout, stderr = process.communicate(timeout=max(0.0, min(POLL_S, remaining)))
                done = True
            except subprocess.TimeoutExpired as partial:
                stdout, stderr = partial.output, partial.stderr
        if process.poll() is not None and not group_alive(pgid):
            survivor = None
            break
        if remaining <= 0:
            survivor = pgid
            print(f"process group {pgid} (leader pid {pgid}) is still alive {grace:g} s after SIGTERM; "
                  "left running, not killed", file=sys.stderr if stream is None else stream, flush=True)
            break
        if done:
            time.sleep(min(POLL_S, max(0.0, remaining)))
    if not done:
        _close_pipes(process)  # a process outside the group may still hold the pipe
    return survivor, _decode(stdout, text), _decode(stderr, text)


def run_group(argv, *, timeout, grace=TERM_GRACE_S, cwd=None, env=None, text=False, stream=None):
    """Run argv to completion within `timeout` seconds; return a CompletedProcess with captured output.

    See the module docstring for the stop and failure rules.
    """
    timeout = _bounded("timeout", timeout)
    grace = _bounded("grace", grace, allow_zero=True)
    if threading.current_thread() is not threading.main_thread():
        raise RuntimeError("run_group must run on the main thread: it installs the TERM/INT/HUP cleanup handlers")
    received = []

    def record(signum, _frame):
        # Only record: raising here could land inside Popen bookkeeping.
        if not received:
            received.append(signum)

    previous = {}
    process = None
    result = None
    stopped = None
    cleanup_started = False
    try:
        for signum in CANCEL_SIGNALS:
            previous[signum] = signal.signal(signum, record)
        process = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, text=text, start_new_session=True)
        deadline = time.monotonic() + timeout
        while not received:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            try:
                stdout, stderr = process.communicate(timeout=min(POLL_S, remaining))
            except subprocess.TimeoutExpired:
                continue
            result = subprocess.CompletedProcess(argv, process.returncode, stdout, stderr)
            break
        if result is None:
            cleanup_started = True
            stopped = stop_group(process, grace, stream, text)
        elif group_alive(process.pid):
            # The leader exited but left members in its group: stop them too.
            cleanup_started = True
            stopped = stop_group(process, grace, stream, text)
    except BaseException as error:
        if process is not None:
            # Unconfirmed cleanup is conservative evidence, not permission to
            # retry a stop or declare the group absent.
            error.survivor = process.pid
            if stopped is not None:
                error.survivor = stopped[0]
            elif not cleanup_started:
                try:
                    stopped = stop_group(process, grace, stream, text)
                except BaseException as cleanup_error:
                    cleanup_error.survivor = process.pid
                    raise
                error.survivor = stopped[0]
        raise
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, handler if handler is not None else signal.SIG_DFL)
    if received:
        signum = received[0]
        # The disposition this call replaced decides now: the default ends the
        # process, a Python handler runs; either way the child group is stopped.
        try:
            signal.raise_signal(signum)
        except BaseException as error:
            # Preserve the caller's exception/disposition and the cleanup
            # evidence. A raising handler otherwise hides a surviving group.
            error.signum = signum
            error.survivor = stopped[0] if stopped else None
            raise
        raise GroupInterrupted(signum, stopped[0] if stopped else None)
    if result is None:
        _, stdout, stderr = stopped
        raise GroupTimeout(argv, timeout, stdout, stderr, stopped[0])
    if stopped is not None and stopped[0] is not None:
        raise GroupSurvived(result, stopped[0])
    return result

"""Isolated launcher regression tests; run with backend/.venv/bin/python -m pytest scripts/tests."""
import os
from pathlib import Path
import shutil
import shlex
import signal
import subprocess
import sys
import time

import pytest

ROOT = Path(__file__).resolve().parents[2]


def write_executable(path, text):
    path.write_text(text)
    path.chmod(0o755)


def wait_for(predicate, timeout=8):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.05)
    raise AssertionError('condition did not become true before timeout')


def alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False


@pytest.mark.parametrize('signum, expected', [(signal.SIGINT, 130), (signal.SIGTERM, 143)])
def test_combined_launcher_exits_on_signal_and_reaps_both_children(tmp_path, signum, expected):
    scripts = tmp_path / 'scripts'
    scripts.mkdir()
    (tmp_path / 'backend').mkdir()
    shutil.copy2(ROOT / 'scripts/run_all.sh', scripts)
    for name in ('backend', 'frontend'):
        child_code = (
            'import os, time; from pathlib import Path; '
            f'Path({str(tmp_path / (name + ".pid"))!r}).write_text(str(os.getpid())); '
            'time.sleep(60)'
        )
        write_executable(
            scripts / f'run_{name}.sh',
            f'#!/usr/bin/env bash\nexec {shlex.quote(sys.executable)} -c {shlex.quote(child_code)}\n',
        )
    process = subprocess.Popen([str(scripts / 'run_all.sh')], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    pids = []
    try:
        wait_for(lambda: all((tmp_path / f'{name}.pid').exists() for name in ('backend', 'frontend')))
        pids = [int((tmp_path / f'{name}.pid').read_text()) for name in ('backend', 'frontend')]
        process.send_signal(signum)
        output, _ = process.communicate(timeout=8)
        assert process.returncode == expected, output
        assert not any(alive(pid) for pid in pids)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
        for pid in pids:
            if alive(pid):
                os.kill(pid, signal.SIGTERM)


def test_frontend_executes_vite_directly_with_strict_port(tmp_path):
    scripts = tmp_path / 'scripts'
    scripts.mkdir()
    shutil.copy2(ROOT / 'scripts/run_frontend.sh', scripts)
    vite = tmp_path / 'frontend/node_modules/vite/bin/vite.js'
    vite.parent.mkdir(parents=True)
    vite.touch()
    binaries = tmp_path / 'bin'
    binaries.mkdir()
    output = tmp_path / 'args'
    write_executable(binaries / 'node', '#!/bin/bash\nprintf "%s\\n" "$@" > "$OUTPUT"\n')
    write_executable(binaries / 'npm', '#!/bin/bash\nexit 91\n')
    env = dict(os.environ, PATH=f'{binaries}:/usr/bin:/bin', OUTPUT=str(output))
    result = subprocess.run([str(scripts / 'run_frontend.sh')], env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert output.read_text().splitlines() == [str(vite), '--host', '127.0.0.1', '--port', '5173', '--strictPort']

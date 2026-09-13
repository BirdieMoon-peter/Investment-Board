"""Live loopback tests against disposable databases, never the user's database."""
from concurrent.futures import ThreadPoolExecutor
import math
import os
from pathlib import Path
import re
import runpy
import selectors
import shutil
import signal
import socket
import subprocess
import time

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / 'scripts/smoke_watchlist.sh'
DEFAULT_STARTUP_TIMEOUT = runpy.run_path(str(ROOT / 'scripts/smoke_watchlist.py'))['STARTUP_TIMEOUT']


def terminate_smoke(process):
    process.terminate()
    try:
        return process.communicate(timeout=10)
    except subprocess.TimeoutExpired:
        # Each harness process has its own session; never kill unrelated listeners.
        os.killpg(process.pid, signal.SIGKILL)
        return process.communicate(timeout=5)


def run_smoke(*, script=SCRIPT, harness_timeout=None, **env):
    environment = dict(os.environ, **env)
    if harness_timeout is None:
        try:
            startup_timeout = float(environment.get('SMOKE_STARTUP_TIMEOUT', DEFAULT_STARTUP_TIMEOUT))
            if not math.isfinite(startup_timeout) or startup_timeout <= 0:
                raise ValueError
        except ValueError:
            startup_timeout = 0  # Invalid inputs should be rejected immediately by the script.
        # Allow the script's own deadline, final request, and child shutdown to finish first.
        harness_timeout = startup_timeout + 15
    process = subprocess.Popen(
        [str(script)], env=environment, text=True, start_new_session=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    try:
        output, _ = process.communicate(timeout=harness_timeout)
    except subprocess.TimeoutExpired as exc:
        output, _ = terminate_smoke(process)
        exc.output = output
        raise
    except BaseException:
        terminate_smoke(process)
        raise
    return subprocess.CompletedProcess(process.args, process.returncode, output)


def assert_cleaned(output):
    match = re.search(r'Smoke workspace: (.+)', output)
    assert match, output
    assert not Path(match[1]).exists()
    child = re.search(r'Smoke backend PID: (\d+)', output)
    assert child, output
    with pytest.raises(ProcessLookupError):
        os.kill(int(child[1]), 0)


def test_parallel_smokes_use_separate_ports_and_clean_workspaces():
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: run_smoke(), range(2)))
    for result in results:
        assert result.returncode == 0, result.stdout
        assert 'Smoke test passed' in result.stdout
        assert_cleaned(result.stdout)
    ports = [re.search(r'Smoke URL: http://127.0.0.1:(\d+)', item.stdout)[1] for item in results]
    assert len(set(ports)) == 2


def test_occupied_port_fails_without_querying_foreign_listener():
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        listener.listen()
        listener.settimeout(0.2)
        result = run_smoke(SMOKE_PORT=str(listener.getsockname()[1]))
        assert result.returncode != 0
        assert 'Cannot bind smoke port' in result.stdout
        with pytest.raises(TimeoutError):
            listener.accept()


@pytest.mark.parametrize('signum, expected', [(signal.SIGINT, 130), (signal.SIGTERM, 143)])
def test_interrupt_reaps_owned_backend_and_removes_temp_database(signum, expected):
    process = subprocess.Popen([str(SCRIPT)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, start_new_session=True)
    output = ''
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            deadline = time.monotonic() + 10
            while 'Smoke backend PID:' not in output:
                assert time.monotonic() < deadline, output
                if selector.select(timeout=0.5):
                    output += os.read(process.stdout.fileno(), 4096).decode()
                assert process.poll() is None, output
        process.send_signal(signum)
        tail, _ = process.communicate(timeout=10)
        output += tail
        assert process.returncode == expected, output
        assert_cleaned(output)
    finally:
        if process.poll() is None:
            terminate_smoke(process)


def isolated_smoke(tmp_path, app_source):
    scripts = tmp_path / 'scripts'
    scripts.mkdir()
    for name in ('smoke_watchlist.sh', 'smoke_watchlist.py'):
        shutil.copy2(ROOT / 'scripts' / name, scripts)
    binaries = tmp_path / 'backend/.venv/bin'
    binaries.mkdir(parents=True)
    (binaries / 'python').symlink_to(ROOT / 'backend/.venv/bin/python')
    # Override the real app, even if the backend package is installed editable.
    app = tmp_path / 'backend/app'
    app.mkdir()
    (app / '__init__.py').write_text(app_source)
    return scripts / 'smoke_watchlist.sh'


def test_child_startup_failure_prints_log_and_cleans_resources(tmp_path):
    script = isolated_smoke(tmp_path, "raise RuntimeError('intentional isolated startup failure')\n")
    result = run_smoke(script=script)
    output = result.stdout
    assert result.returncode == 1, output
    assert 'exited before becoming ready' in output
    assert 'intentional isolated startup failure' in output
    assert 'Loading backend dependencies' in output
    assert_cleaned(output)


def test_dependency_stall_times_out_with_flushed_stage_and_cleans_resources(tmp_path):
    script = isolated_smoke(tmp_path, 'import time\ntime.sleep(120)\n')
    started = time.monotonic()
    result = run_smoke(script=script, SMOKE_STARTUP_TIMEOUT='0.5')
    output = result.stdout
    assert result.returncode == 1, output
    assert 'startup timed out after 0.5 seconds' in output
    # The child is terminated while blocked in import: its stage must already be flushed.
    assert 'Loading backend dependencies' in output
    assert 'available locally' in output
    assert 'SMOKE_STARTUP_TIMEOUT' in output
    assert time.monotonic() - started < 8
    assert_cleaned(output)
    port = int(re.search(r'Smoke URL: http://127.0.0.1:(\d+)', output)[1])
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', port))


def test_harness_timeout_gracefully_reaps_backend_and_removes_workspace(tmp_path):
    script = isolated_smoke(tmp_path, 'import time\ntime.sleep(120)\n')
    with pytest.raises(subprocess.TimeoutExpired) as timed_out:
        run_smoke(script=script, harness_timeout=2, SMOKE_STARTUP_TIMEOUT='120')
    output = timed_out.value.output
    assert 'Loading backend dependencies' in output
    assert 'Smoke interrupted by signal 15' in output
    assert_cleaned(output)


@pytest.mark.parametrize('value', ['0', '-1', 'nan', 'inf', 'invalid'])
def test_invalid_startup_timeout_is_rejected_before_port_access(value):
    result = run_smoke(SMOKE_STARTUP_TIMEOUT=value, SMOKE_PORT='invalid')
    assert result.returncode == 1
    assert 'SMOKE_STARTUP_TIMEOUT must be a finite positive number' in result.stdout

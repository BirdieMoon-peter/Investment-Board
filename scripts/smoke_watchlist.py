"""Run an isolated watchlist smoke test using only an owned loopback server."""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile
import time
from urllib.error import URLError
from urllib.request import ProxyHandler, build_opener

ROOT = Path(__file__).resolve().parents[1]
STARTUP_TIMEOUT = 120
REQUEST_TIMEOUT = 2


class Interrupted(Exception):
    def __init__(self, signum: int):
        self.signum = signum


def stop_child(child: subprocess.Popen) -> None:
    if child.poll() is None:
        child.terminate()
        try:
            child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            child.kill()
    child.wait()


def serve(socket_fd: int) -> None:
    # This process owns both seeding and serving; the parent can always reap it.
    sys.path.insert(0, str(ROOT / 'backend'))
    print('Loading backend dependencies', flush=True)
    from app.db.services.seed_demo_data_cli import main as seed
    import uvicorn

    print('Seeding isolated smoke database', flush=True)
    seed()
    print('Starting smoke backend server', flush=True)
    with socket.socket(fileno=socket_fd) as listener:
        uvicorn.Server(uvicorn.Config('app.main:app', log_level='warning')).run(sockets=[listener])


def run() -> int:
    child = None
    old_handlers = {}

    def interrupted(signum, _frame):
        raise Interrupted(signum)

    for signum in (signal.SIGINT, signal.SIGTERM):
        old_handlers[signum] = signal.signal(signum, interrupted)

    try:
        try:
            startup_timeout = float(os.environ.get('SMOKE_STARTUP_TIMEOUT', str(STARTUP_TIMEOUT)))
            if not math.isfinite(startup_timeout) or startup_timeout <= 0:
                raise ValueError
        except ValueError:
            raise RuntimeError('SMOKE_STARTUP_TIMEOUT must be a finite positive number') from None

        try:
            port = int(os.environ.get('SMOKE_PORT', '0'))
            if not 0 <= port <= 65535:
                raise ValueError
        except ValueError:
            raise RuntimeError('SMOKE_PORT must be an integer between 0 and 65535') from None

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            try:
                listener.bind(('127.0.0.1', port))
            except OSError as exc:
                raise RuntimeError(f'Cannot bind smoke port {port}: {exc}') from exc
            # Retain the reserved socket through child startup; never race a free-port probe.
            with tempfile.TemporaryDirectory(prefix='investment-board-smoke-') as directory:
                workspace = Path(directory)
                log_path = workspace / 'backend.log'
                print(f'Smoke workspace: {workspace}', flush=True)
                base_url = f'http://127.0.0.1:{listener.getsockname()[1]}'
                print(f'Smoke URL: {base_url}', flush=True)
                try:
                    with log_path.open('w') as log:
                        child = subprocess.Popen(
                            [sys.executable, str(Path(__file__).resolve()), '--serve', str(listener.fileno())],
                            cwd=ROOT / 'backend',
                            env=dict(os.environ, DATABASE_URL=f'sqlite:///{workspace / "smoke.db"}'),
                            pass_fds=(listener.fileno(),), stdout=log, stderr=subprocess.STDOUT,
                        )
                    print(f'Smoke backend PID: {child.pid}', flush=True)
                    opener = build_opener(ProxyHandler({}))

                    def read_json(path, timeout=REQUEST_TIMEOUT):
                        if child.poll() is not None:
                            raise RuntimeError(f'Smoke backend exited before becoming ready (exit {child.returncode})')
                        with opener.open(base_url + path, timeout=timeout) as response:
                            data = json.load(response)
                        if child.poll() is not None:
                            raise RuntimeError('Smoke backend exited during verification')
                        return data

                    deadline = time.monotonic() + startup_timeout
                    while True:
                        remaining = deadline - time.monotonic()
                        if remaining <= 0:
                            raise RuntimeError(
                                f'Smoke backend startup timed out after {startup_timeout:g} seconds. '
                                'Check the last startup stage in the backend log above. '
                                'Ensure backend source and backend/.venv dependency files are available locally '
                                '(on macOS, download any cloud-only/dataless files). '
                                'For a slow cold start, retry with a larger finite positive '
                                'SMOKE_STARTUP_TIMEOUT (default 120 seconds).'
                            )
                        try:
                            items = read_json('/api/watchlist/items', timeout=min(REQUEST_TIMEOUT, remaining))
                            break
                        except (URLError, TimeoutError, ConnectionError):
                            time.sleep(max(0, min(0.1, deadline - time.monotonic())))
                    expected = [('SH', '600519', 'Kweichow Moutai'), ('SZ', '000001', 'Ping An Bank')]
                    if [(row['market'], row['code'], row['name']) for row in items] != expected:
                        raise RuntimeError('Seeded watchlist identities do not match')
                    results = read_json('/api/watchlist/securities/search?query=Ping')
                    if [(row['market'], row['code'], row['name']) for row in results] != expected[1:]:
                        raise RuntimeError('Seeded search identity does not match')
                    print('Smoke test passed: two seeded watchlist identities and local search verified', flush=True)
                except BaseException:
                    if child is not None:
                        stop_child(child)
                        child = None
                    print('Smoke backend log:', file=sys.stderr)
                    print(log_path.read_text() if log_path.exists() else '(not started)', file=sys.stderr)
                    raise
                finally:
                    if child is not None:
                        stop_child(child)
                        child = None
        return 0
    except Interrupted as exc:
        print(f'Smoke interrupted by signal {exc.signum}', file=sys.stderr)
        return 128 + exc.signum
    except Exception as exc:
        print(f'Smoke test failed: {exc}', file=sys.stderr)
        return 1
    finally:
        for signum, handler in old_handlers.items():
            signal.signal(signum, handler)


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--serve':
        serve(int(sys.argv[2]))
    else:
        raise SystemExit(run())

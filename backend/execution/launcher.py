"""One parent owns the worker group. A failed worker stops the whole group.

Restart from committed state instead of letting two owners serve one account.
The OS releases the local lock even after a crash; there is no lease heartbeat
on the observation path and no hidden second process started by an API request.
"""
from contextlib import contextmanager
import multiprocessing
import os
from pathlib import Path
import signal
import tempfile


def initialize():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
    for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
        os.environ.setdefault(name, '1')
    import django
    django.setup()


@contextmanager
def execution_ownership():
    """Exclude another worker group or offline buffer maintenance on this host."""
    # API maintenance commands and runtime containers must see the same lock.
    directory = Path(os.environ.get('QUANTNEST_RUNTIME_DIR', str(Path(tempfile.gettempdir()) / 'quantnest-runtime')))
    path = directory / 'execution.lock'
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a+b') as handle:
        handle.seek(0)
        if os.name == 'nt':
            import msvcrt
            if path.stat().st_size == 0:
                handle.write(b'0')
                handle.flush()
                handle.seek(0)
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise RuntimeError('Execution is already running on this server.') from exc
        else:
            import fcntl
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise RuntimeError('Execution is already running on this server.') from exc
        try:
            yield
        finally:
            if os.name == 'nt':
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)


def child(index, inboxes, output, stop):
    initialize()
    from .worker import run_worker
    run_worker(index, inboxes, output, stop)


def main():
    initialize()
    from django.conf import settings
    from .controller import Controller
    context = multiprocessing.get_context('spawn')
    stop = context.Event()
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    count = settings.EXECUTION_WORKERS
    inboxes = [context.Queue(maxsize=4096) for _ in range(count)]
    output = context.Queue(maxsize=4096)
    processes = []
    with execution_ownership():
        try:
            for index in range(count):
                process = context.Process(target=child, args=(index, inboxes, output, stop), name=f'execution-{index}')
                process.start()
                processes.append(process)
            Controller(inboxes, output).run(stop, processes)
        finally:
            stop.set()
            for process in processes:
                process.join(timeout=10)
                if process.is_alive():
                    process.terminate()
                    process.join(timeout=3)
            for queue in [*inboxes, output]:
                queue.cancel_join_thread()
                queue.close()

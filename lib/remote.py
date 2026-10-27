import os
import shlex
import subprocess
import sys
from pathlib import Path

CONTROL_PERSIST = "60s"

_runtime_dir = os.environ.get("XDG_RUNTIME_DIR")
_SOCK_DIR = (Path(_runtime_dir) if _runtime_dir else Path.home() / ".ssh") / "infra-cm"


class RemoteError(RuntimeError):
    pass


def _ssh_opts(port: int) -> list[str]:
    _SOCK_DIR.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    _SOCK_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    if _SOCK_DIR.stat().st_mode & 0o077:
        _SOCK_DIR.chmod(0o700)
    return [
        '-p', str(port),
        '-o', 'ControlMaster=auto',
        '-o', f'ControlPath={_SOCK_DIR}/%C',
        '-o', f'ControlPersist={CONTROL_PERSIST}',
    ]


def _ssh_rsync_cmd(port: int) -> str:
    """rsync -e takes one string and word-splits it itself."""
    return ' '.join(shlex.quote(part) for part in ['ssh', *_ssh_opts(port)])


def ssh_run(target: str, cmd: str, port: int = 22) -> None:
    result = subprocess.run(
        ['ssh', *_ssh_opts(port), target, cmd],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"  SSH error: {result.stderr.strip()}", file=sys.stderr)
        sys.exit(1)


def ssh_read_file(target: str, path: str, port: int = 22) -> str:
    result = subprocess.run(
        ['ssh', *_ssh_opts(port), target, f'cat {path} 2>/dev/null || true'],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RemoteError(result.stderr.strip() or f'ssh exited with {result.returncode}')
    return result.stdout


def rsync_file(local: Path, target: str, remote: str, port: int = 22) -> bool:
    result = subprocess.run(
        ['rsync', '-az', '--checksum', '--itemize-changes',
         '-e', _ssh_rsync_cmd(port),
         str(local), f'{target}:{remote}'],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"  rsync error: {result.stderr.strip()}", file=sys.stderr)
        sys.exit(1)
    for line in result.stdout.strip().splitlines():
        # itemize format: YXcstpoguax
        # [0]='<' sent, [2]='c' checksum differs, [3]='s' size differs, [8]='+' new file
        # A truly unchanged file produces no output or dots-only flags
        flags = line[1:11] if len(line) > 1 else ''
        if line and line[0] in '<>' and ('c' in flags or 's' in flags or '+' in flags):
            return True
    return False


def write_secret_remote(target: str, content: str, path: str, port: int = 22) -> None:
    subprocess.run(
        ['ssh', *_ssh_opts(port), target, f'cat > {path} && chmod 600 {path}'],
        input=content, text=True, check=True
    )

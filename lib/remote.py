import subprocess
import sys
from pathlib import Path


def ssh_run(target: str, cmd: str, port: int = 22) -> None:
    result = subprocess.run(
        ['ssh', '-p', str(port), target, cmd],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"  SSH error: {result.stderr.strip()}", file=sys.stderr)


def ssh_read_file(target: str, path: str, port: int = 22) -> str:
    result = subprocess.run(
        ['ssh', '-p', str(port), target, f'cat {path} 2>/dev/null || true'],
        capture_output=True, text=True
    )
    return result.stdout


def rsync_file(local: Path, target: str, remote: str, port: int = 22) -> bool:
    result = subprocess.run(
        ['rsync', '-az', '--checksum', '--itemize-changes',
         '-e', f'ssh -p {port}',
         str(local), f'{target}:{remote}'],
        capture_output=True, text=True
    )
    for line in result.stdout.strip().splitlines():
        # itemize format: YXcstpoguax
        # [0]='<' sent, [2]='c' checksum differs, [3]='s' size differs
        # A truly unchanged file produces no output or dots-only flags
        if line and line[0] in '<>' and ('c' in line[1:11] or 's' in line[1:11]):
            return True
    return False


def write_secret_remote(target: str, content: str, path: str, port: int = 22) -> None:
    subprocess.run(
        ['ssh', '-p', str(port), target, f'cat > {path} && chmod 600 {path}'],
        input=content, text=True, check=True
    )

#!/usr/bin/env python3
"""Standard-library bootstrap: run the demo only inside this checkout's .venv."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


class SetupError(Exception):
    pass


def environment_python(root):
    return root / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')


def run_checked(command, **kwargs):
    try:
        return subprocess.run(command, check=True, **kwargs)
    except (OSError, subprocess.CalledProcessError):
        raise SetupError('A setup command failed. Check the terminal output and your network connection; '
                         'your base Python environment was not modified.') from None


def find_python():
    candidates = []
    for minor in ('3.12', '3.11'):
        found = shutil.which('python' + minor)
        if found:
            candidates.append([found])
    if os.name == 'nt' and shutil.which('py'):
        candidates.extend([['py', '-3.12'], ['py', '-3.11']])
    candidates.append([sys.executable])
    for candidate in candidates:
        try:
            result = subprocess.run(
                candidate + ['-c', 'import sys; print("%d.%d" % sys.version_info[:2])'],
                capture_output=True, text=True, check=True,
            )
            if result.stdout.strip() in {'3.11', '3.12'}:
                return candidate
        except (OSError, subprocess.CalledProcessError):
            continue
    raise SetupError('Install Python 3.12 or 3.11, then run this launcher again.')


def environment_ready(python, root):
    # Probe package versions without importing Qt or accessing configuration/API.
    probe = '''import pathlib, sys
if not (sys.version_info[:2] in ((3, 11), (3, 12)) and sys.prefix != sys.base_prefix
        and pathlib.Path(sys.prefix).resolve() == pathlib.Path(sys.argv[1]).parent.joinpath('.venv').resolve()):
    sys.exit(2)
import importlib.metadata
ok = True
for line in pathlib.Path(sys.argv[1]).read_text().splitlines():
    if line and not line.startswith('#'):
        name, expected = line.split('==')
        try:
            ok = ok and importlib.metadata.version(name) == expected
        except importlib.metadata.PackageNotFoundError:
            ok = False
sys.exit(0 if ok else 1)
'''
    try:
        result = subprocess.run([str(python), '-c', probe, str(root / 'requirements.txt')],
                                capture_output=True)
        if result.returncode not in (0, 1):
            raise SetupError('The local .venv is incompatible or broken. Move it aside manually and rerun; '
                             'it will not be deleted automatically.')
        return result.returncode == 0
    except OSError:
        raise SetupError('The local .venv cannot run. Move it aside and rerun this launcher; '
                         'it will not be deleted automatically.') from None


def launch(setup=False, root=ROOT):
    root = Path(root)
    python = environment_python(root)
    if (root / '.venv').is_symlink() or python.is_symlink() and not python.exists():
        raise SetupError('The local .venv is invalid or points elsewhere. Move it aside and rerun.')
    if not python.exists() and (root / '.venv').exists():
        raise SetupError('The existing .venv is incomplete. Move it aside and rerun; no files were deleted.')
    ready = python.exists() and environment_ready(python, root)
    if not ready:
        print('Demo setup creates/uses only this checkout’s .venv and downloads the pinned '
              'application dependencies from PyPI. It does not install into Conda/Miniforge or system Python.')
        if not setup:
            if not sys.stdin.isatty():
                raise SetupError('Setup requires confirmation. Run python run_demo.py --setup '
                                 'to explicitly authorize noninteractive installation.')
            if input('Set up the local demo environment? [y/N] ').strip().lower() not in {'y', 'yes'}:
                print('Setup declined; nothing was installed.')
                return 0
        if not python.exists():
            run_checked(find_python() + ['-m', 'venv', str(root / '.venv')])
        # Validate the target really is an isolated environment before installing.
        run_checked([str(python), '-c',
                     'import sys; assert sys.prefix != sys.base_prefix; '
                     'assert sys.version_info[:2] in ((3, 11), (3, 12))'])
        run_checked([str(python), '-m', 'pip', '--isolated', 'install', '--require-virtualenv', '-r', str(root / 'requirements.txt')])
        if not environment_ready(python, root):
            raise SetupError('The local environment is not ready. Review the installation output and retry.')
    return run_checked([str(python), str(root / 'main.py'), '--demo'], cwd=root).returncode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--setup', action='store_true', help='authorize local dependency setup without prompting')
    args = parser.parse_args()
    try:
        return launch(setup=args.setup)
    except (SetupError, EOFError) as error:
        print(f'Demo launcher: {error}', file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print('\nDemo launcher stopped.', file=sys.stderr)
        return 130


if __name__ == '__main__':
    raise SystemExit(main())

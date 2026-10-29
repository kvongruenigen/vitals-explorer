import io
from pathlib import Path
import subprocess
from unittest.mock import Mock

import pytest

import run_demo as launcher


@pytest.fixture
def project(tmp_path):
    root = tmp_path / 'project with spaces'
    root.mkdir()
    (root / 'requirements.txt').write_text('pytz==2026.5\n')
    return root


def test_existing_environment_ignores_active_interpreter(project, monkeypatch):
    python = launcher.environment_python(project)
    python.parent.mkdir(parents=True)
    python.touch()
    monkeypatch.setattr(launcher, 'environment_ready', lambda *args: True)
    run = Mock(return_value=Mock(returncode=0))
    monkeypatch.setattr(launcher, 'run_checked', run)
    assert launcher.launch(root=project) == 0
    run.assert_called_once_with([str(python), str(project / 'main.py'), '--demo'], cwd=project)


def test_interpreter_selection_checks_versions(monkeypatch):
    monkeypatch.setattr(launcher.shutil, 'which', lambda name: '/bin/' + name)
    run = Mock(side_effect=[Mock(stdout='3.15\n'), Mock(stdout='3.11\n')])
    monkeypatch.setattr(launcher.subprocess, 'run', run)
    assert launcher.find_python() == ['/bin/python3.11']


def test_missing_supported_python(monkeypatch):
    monkeypatch.setattr(launcher.shutil, 'which', lambda name: None)
    monkeypatch.setattr(launcher.subprocess, 'run', Mock(return_value=Mock(stdout='3.15\n')))
    with pytest.raises(launcher.SetupError, match='3.12 or 3.11'):
        launcher.find_python()


def test_declined_setup_installs_nothing(project, monkeypatch):
    monkeypatch.setattr(launcher.sys, 'stdin', Mock(isatty=lambda: True))
    monkeypatch.setattr('builtins.input', lambda prompt: 'no')
    run = Mock()
    monkeypatch.setattr(launcher, 'run_checked', run)
    assert launcher.launch(root=project) == 0
    run.assert_not_called()
    assert not (project / '.venv').exists()


def test_noninteractive_requires_explicit_setup(project, monkeypatch):
    monkeypatch.setattr(launcher.sys, 'stdin', io.StringIO())
    with pytest.raises(launcher.SetupError, match='--setup'):
        launcher.launch(root=project)


def test_setup_uses_argument_lists_and_local_pip(project, monkeypatch):
    monkeypatch.setattr(launcher, 'find_python', lambda: ['/supported/python'])
    monkeypatch.setattr(launcher, 'environment_ready', lambda *args: True)
    run = Mock(return_value=Mock(returncode=0))
    monkeypatch.setattr(launcher, 'run_checked', run)
    assert launcher.launch(setup=True, root=project) == 0
    commands = [call.args[0] for call in run.call_args_list]
    assert commands[0] == ['/supported/python', '-m', 'venv', str(project / '.venv')]
    assert commands[2] == [str(launcher.environment_python(project)), '-m', 'pip', '--isolated', 'install', '--require-virtualenv',
                           '-r', str(project / 'requirements.txt')]
    assert commands[-1][-1] == '--demo'


def test_broken_environment_is_not_deleted(project):
    directory = project / '.venv'
    directory.mkdir()
    marker = directory / 'keep-me'
    marker.write_text('preserve')
    with pytest.raises(launcher.SetupError, match='incomplete'):
        launcher.launch(setup=True, root=project)
    assert marker.read_text() == 'preserve'


def test_subprocess_failures_are_actionable(monkeypatch):
    monkeypatch.setattr(launcher.subprocess, 'run', Mock(side_effect=subprocess.CalledProcessError(1, ['pip'])))
    with pytest.raises(launcher.SetupError, match='base Python environment was not modified'):
        launcher.run_checked(['pip'])


def test_unrunnable_environment_explains_recovery(project, monkeypatch):
    monkeypatch.setattr(launcher.subprocess, 'run', Mock(side_effect=OSError))
    with pytest.raises(launcher.SetupError, match='not be deleted'):
        launcher.environment_ready(Path('/broken/python'), project)


def test_incompatible_environment_explains_recovery(project, monkeypatch):
    monkeypatch.setattr(launcher.subprocess, 'run', Mock(return_value=Mock(returncode=2)))
    with pytest.raises(launcher.SetupError, match='Move it aside manually'):
        launcher.environment_ready(Path('/incompatible/python'), project)

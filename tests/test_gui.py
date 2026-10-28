"""Optional real Qt tests: RUN_GUI_TESTS=1 python -m pytest tests/test_gui.py."""
import os
import threading
import time

import pytest

pytestmark = pytest.mark.skipif(os.environ.get('RUN_GUI_TESTS') != '1', reason='requires desktop Qt WebEngine session')


@pytest.fixture(scope="session")
def qt_app():
    from PyQt5.QtCore import Qt
    from PyQt5.QtWidgets import QApplication
    QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
    app = QApplication.instance() or QApplication([])
    yield app


def wait_until(qt_app, condition):
    deadline = time.monotonic() + 10
    while not condition() and time.monotonic() < deadline:
        qt_app.processEvents()
        time.sleep(.01)
    assert condition()


def test_responsive_and_close(qt_app, monkeypatch):
    from main import BiobeatApp
    from biobeat.demo import synthetic_measurements
    started, release = threading.Event(), threading.Event()

    def token():
        started.set()
        assert release.wait(5)
        return 'fictional'

    monkeypatch.setattr('main.get_access_token', token)
    monkeypatch.setattr('main.get_all_measurements', lambda *args, **kwargs: synthetic_measurements())
    monkeypatch.setenv('BIOBEAT_DEVICE_IDS', 'DEMO-001')
    window = BiobeatApp()
    window.device_dropdown.setCurrentIndex(1)
    window.show()
    window._on_fetch()
    try:
        wait_until(qt_app, started.is_set)
        assert not window.fetch_button.isEnabled()
        assert not window.download_button.isEnabled()
        # A Qt timer fires while the worker is blocked in a mocked request.
        from PyQt5.QtCore import QTimer
        ticks = []
        QTimer.singleShot(0, lambda: ticks.append(True))
        wait_until(qt_app, lambda: bool(ticks))
        window.close()
        assert window.closing
        assert window.worker is not None
    finally:
        release.set()
    wait_until(qt_app, lambda: window.worker is None)
    wait_until(qt_app, lambda: not window.isVisible())
    assert not os.path.exists(window.plot_directory.name)


def test_worker_error_restores_controls(qt_app, monkeypatch):
    from main import BiobeatApp
    from biobeat.errors import AuthenticationError
    from PyQt5.QtWidgets import QMessageBox

    def denied():
        raise AuthenticationError('Mock authorization denied.')

    monkeypatch.setattr('main.get_access_token', denied)
    monkeypatch.setattr(QMessageBox, 'critical', lambda *args: None)
    monkeypatch.setenv('BIOBEAT_DEVICE_IDS', 'DEMO-001')
    window = BiobeatApp()
    window.device_dropdown.setCurrentIndex(1)
    window._on_fetch()
    wait_until(qt_app, lambda: window.worker is None)
    assert window.fetch_button.isEnabled()
    assert not window.download_button.isEnabled()
    assert window.status_label.text() == 'Mock authorization denied.'
    window.close()


def test_no_devices_explains_configuration(qt_app, monkeypatch):
    from main import BiobeatApp
    monkeypatch.delenv('BIOBEAT_DEVICE_IDS', raising=False)
    window = BiobeatApp()
    assert not window.fetch_button.isEnabled()
    assert 'BIOBEAT_DEVICE_IDS' in window.status_label.text()
    window.close()

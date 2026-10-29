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


def test_sorting_is_typed_stable_and_does_not_mutate_dataset(qt_app):
    import pandas as pd
    from PyQt5.QtCore import Qt, QPersistentModelIndex
    from main import PandasModel
    original = pd.DataFrame({'number': [10, 2, None, 2], 'text': ['b', 'a', None, 'c'],
                             'time': pd.to_datetime(['2026-02-01', '2026-01-01', None, '2026-01-02'], utc=True)})
    model = PandasModel(original)
    selected = QPersistentModelIndex(model.index(0, 0))
    model.sort(0, Qt.AscendingOrder)
    assert model._df['text'].tolist()[:3] == ['a', 'c', 'b']
    assert selected.row() == 2
    model.sort(0, Qt.DescendingOrder)
    assert model._df['number'].tolist()[:3] == [10, 2, 2]
    assert pd.isna(model._df['number'].iloc[-1])
    model.sort(1, Qt.AscendingOrder)
    assert model._df['text'].tolist()[:3] == ['a', 'b', 'c']
    model.sort(2, Qt.DescendingOrder)
    assert model._df['time'].iloc[0].month == 2
    assert pd.isna(model._df['time'].iloc[-1])
    assert original['number'].iloc[0] == 10


def test_demo_autoload_timezone_and_locked_controls(qt_app, monkeypatch):
    from main import BiobeatApp
    from biobeat.demo import DEMO_START
    monkeypatch.setattr('main.get_access_token', lambda: pytest.fail('Demo called the live API'))
    window = BiobeatApp(demo=True)
    window.show()
    wait_until(qt_app, lambda: window.retrieval is not None and window.worker is None)
    assert len(window.df) == 72
    assert window.retrieval.start_utc == DEMO_START
    assert window.download_button.isEnabled()
    for widget in [window.device_dropdown, window.start_date_edit, window.start_time_edit,
                   window.end_date_edit, window.end_time_edit]:
        assert not widget.isEnabled()
    assert window.timezone_dropdown.isEnabled()
    assert 'Missing vital values: 0/432' in window.quality_label.text()
    assert window.splitter.count() == 2
    window.timezone_dropdown.setCurrentText('America/New_York')
    wait_until(qt_app, lambda: window.worker is None and window.retrieval.timezone == 'America/New_York')
    assert window.start_time_edit.time().hour() == 3
    assert window.df.datetime_tz.iloc[0].hour == 3
    assert 'America/New_York' in window.quality_label.text()
    window.close()


def test_export_keeps_loaded_provenance_on_control_change_failure_and_empty(qt_app, monkeypatch, tmp_path):
    from PyQt5.QtWidgets import QFileDialog, QMessageBox
    from biobeat.demo import DEMO_START, DEMO_END, synthetic_measurements
    from biobeat.quality import summarize_quality
    from biobeat.results import RetrievalResult
    from biobeat.utils import normalize_measurements
    from main import BiobeatApp
    monkeypatch.setenv('BIOBEAT_DEVICE_IDS', 'DEMO-001,DEMO-002')
    window = BiobeatApp()
    df = normalize_measurements(synthetic_measurements(), 'UTC')
    loaded = RetrievalResult(df, '', 'DEMO-001', 'UTC', DEMO_START, DEMO_END, summarize_quality(df))
    window._retrieval_result(loaded)
    window._set_ui_enabled(True)
    summary = window.quality_label.text()
    window.device_dropdown.setCurrentText('DEMO-002')
    window.timezone_dropdown.setCurrentText('Europe/Zurich')
    monkeypatch.setattr(QMessageBox, 'critical', lambda *args: None)
    monkeypatch.setattr(QMessageBox, 'information', lambda *args: None)
    window._retrieval_error('Mock failure')
    assert window.quality_label.text() == summary
    defaults = []
    def destination(*args):
        defaults.append(args[2])
        return str(tmp_path / 'synthetic.csv'), ''
    monkeypatch.setattr(QFileDialog, 'getSaveFileName', destination)
    window._download_csv()
    assert 'DEMO-001' in defaults[0] and 'DEMO-002' not in defaults[0]
    assert (tmp_path / 'synthetic.csv').exists()
    assert window.retrieval is loaded
    empty = normalize_measurements([], 'UTC')
    window._retrieval_result(RetrievalResult(empty, '', 'DEMO-002', 'UTC', DEMO_START, DEMO_END, summarize_quality(empty)))
    window._set_ui_enabled(True)
    assert window.df.empty and not window.download_button.isEnabled()
    assert window.quality_label.text() == 'No measurements loaded.'
    window.close()


def test_workbench_layout_and_display_headers(qt_app):
    from PyQt5.QtCore import Qt
    from main import BiobeatApp
    window = BiobeatApp(demo=True)
    window.resize(1000, 800)
    window.show()
    wait_until(qt_app, lambda: window.worker is None and window.retrieval is not None)
    assert window.timezone_dropdown.isVisible()
    assert window.sidebar.width() == 258
    assert window.quality_values['records'].text() == '72'
    assert window.quality_values['missing'].text() == '0 / 432'
    assert window.quality_values['median'].text() == '5 min'
    panel = window.sidebar.widget()
    for control in [window.device_dropdown, window.timezone_dropdown, window.start_date_edit,
                    window.start_time_edit, window.end_date_edit, window.end_time_edit]:
        assert control.mapTo(panel, control.rect().topRight()).x() <= panel.width()
    model = window.table_view.model()
    column = window.df.columns.get_loc('sbp')
    assert model.headerData(column, Qt.Horizontal) == 'SBP (mmHg)'
    assert 'sbp' in window.df.columns
    assert window.table_view.horizontalHeader().logicalIndex(0) == window.df.columns.get_loc('datetime_tz')
    window.close()

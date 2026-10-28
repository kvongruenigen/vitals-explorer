"""Capture the actual Qt application using synthetic data only.

Run from the repository root: python scripts/demo_screenshots.py
Requires a desktop session with Qt WebEngine support; never reads live devices.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtWidgets import QApplication
from main import BiobeatApp
from biobeat.utils import export_csv

QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
app = QApplication(sys.argv)
window = BiobeatApp(demo=True)
window.resize(1400, 1100)
output = Path(__file__).resolve().parents[1] / 'docs/images'
output.mkdir(parents=True, exist_ok=True)
window.show()
failed = True


def capture():
    global failed
    if window.worker is not None or window.df is None:
        return
    assert len(window.df) == 72
    assert window.device_dropdown.currentText() == 'DEMO-001'
    assert window.download_button.isEnabled()
    assert window.grab().save(str(output / 'main-synthetic.png'))
    assert window.plot_view.grab().save(str(output / 'plots-synthetic.png'))
    # Keep the synthetic label and CSV controls visible alongside the data table.
    window.plot_view.hide()
    QTimer.singleShot(500, capture_table)


def capture_table():
    global failed
    assert window.grab().save(str(output / 'table-synthetic.png'))
    export = output.parent / 'synthetic-demo.csv'  # ignored; never a real recording
    export_csv(window.df, export)
    failed = False
    print('Captured actual Qt widgets; exported 72 synthetic rows. No API requests.')
    window.close()
    app.quit()


def timeout():
    print('Screenshot capture timed out; inspect Qt/WebEngine support on this desktop.')
    window.close()
    app.quit()


window.plot_view.loadFinished.connect(lambda ok: QTimer.singleShot(2000, capture) if ok else None)
QTimer.singleShot(1000, window._on_fetch)
# Capture relies on loadFinished so the Plotly page has rendered.
QTimer.singleShot(45000, timeout)
app.exec_()
raise SystemExit(1 if failed else 0)

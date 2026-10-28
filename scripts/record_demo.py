"""Record actual synthetic Qt widgets; FFmpeg is an optional developer tool.

Run: python scripts/record_demo.py
No desktop capture, microphone, API access, or live measurements are used.
"""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PyQt5.QtCore import QPoint, QTimer, Qt
from PyQt5.QtGui import QPainter
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication, QFileDialog, QMessageBox, QDialogButtonBox, QLineEdit
import pandas as pd
import main

ROOT = Path(__file__).resolve().parents[1]
FPS = 12
FRAMES = 30 * FPS


def record():
    ffmpeg = shutil.which('ffmpeg')
    if not ffmpeg:
        raise SystemExit('Recording requires FFmpeg on PATH. It is not needed to run the application.')
    QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_DontUseNativeDialogs)
    app = QApplication([])
    app.setQuitOnLastWindowClosed(False)

    def no_api(*args, **kwargs):
        raise AssertionError('Recording must never request live data.')
    main.get_access_token = main.get_all_measurements = no_api
    window = main.BiobeatApp(demo=True)
    window.resize(1280, 960)
    output = ROOT / 'docs/videos/demo-synthetic.mp4'
    output.parent.mkdir(parents=True, exist_ok=True)
    state = {'frame': 0, 'loaded': False, 'zoom': False, 'error': None, 'export_path': None, 'save_frames': 0, 'success_frames': 0}
    previous_cwd = Path.cwd()

    with tempfile.TemporaryDirectory(prefix='VitalsExplorerDemo-') as directory:
        directory = Path(directory)
        frames = directory / 'frames'
        frames.mkdir()
        exports = directory / 'exports'
        exports.mkdir()
        os.chdir(exports)
        csv = exports / 'synthetic-demo.csv'
        original_export = main.export_csv
        def track_export(df, path):
            original_export(df, path)
            state['export_path'] = Path(path)
        main.export_csv = track_export

        def stop(error=None):
            timer.stop()
            state['error'] = error
            if window.worker is not None:
                window.worker.finished.connect(app.quit)
                window.close()
            else:
                window.close()
                app.quit()

        def javascript(source):
            window.plot_view.page().runJavaScript(source)

        def loaded(ok):
            state['loaded'] = ok
        window.plot_view.loadFinished.connect(loaded)

        def sort_table():
            header = window.table_view.horizontalHeader()
            column = window.df.columns.get_loc('hr')
            window.table_view.sortByColumn(column, Qt.AscendingOrder)
            x = header.sectionViewportPosition(column) + header.sectionSize(column) // 2
            QTest.mouseClick(header.viewport(), Qt.LeftButton, pos=QPoint(x, header.height() // 2))

        def open_export():
            # The normal application's export button and dialogs are used unchanged.
            window.download_button.click()

        def choose_file():
            dialog = next(w for w in app.topLevelWidgets() if isinstance(w, QFileDialog) and w.isVisible())
            dialog.setDirectory(str(exports))
            dialog.selectFile(csv.name)
            dialog.findChild(QLineEdit, 'fileNameEdit').setText(csv.name)
            dialog.resize(800, 500)
            dialog.move(window.geometry().center() - dialog.rect().center())

        def save_file():
            dialog = next(w for w in app.topLevelWidgets() if isinstance(w, QFileDialog) and w.isVisible())
            dialog.findChild(QDialogButtonBox).button(QDialogButtonBox.Save).click()

        def dismiss_success():
            box = next(w for w in app.topLevelWidgets() if isinstance(w, QMessageBox) and w.isVisible())
            box.button(QMessageBox.Ok).click()
            assert state['export_path'] == csv
            assert len(pd.read_csv(state['export_path'])) == 72

        def zoom_result(value):
            state['zoom'] = bool(value)

        actions = {
            48: lambda: window.splitter.setSizes([600, 120]),
            78: lambda: javascript('window.scrollTo(0, document.body.scrollHeight)'),
            108: lambda: javascript("""window.scrollTo(0,0);
                var gd=document.querySelector('.plotly-graph-div');
                Plotly.relayout(gd, {'xaxis.range':[gd.data[0].x[12],gd.data[0].x[36]]})
                  .then(function(){window.recordingZoom=true;});"""),
            138: lambda: window.plot_view.page().runJavaScript('window.recordingZoom===true', zoom_result),
            156: lambda: javascript("Plotly.relayout(document.querySelector('.plotly-graph-div'), {'xaxis.autorange':true})"),
            180: lambda: window.splitter.setSizes([180, 600]),
            204: sort_table,
            228: lambda: window.table_view.selectRow(0),
            240: open_export,
            252: choose_file,
            276: save_file,
            306: dismiss_success,
            324: lambda: window.splitter.setSizes([600, 300]),
        }

        def perform(action):
            try:
                action()
            except Exception as error:
                stop(f'Recording action failed at frame {state["frame"]}: {type(error).__name__}')

        def capture():
            try:
                index = state['frame']
                if index == 36:
                    assert state['loaded'] and window.worker is None and len(window.df) == 72
                    assert window.retrieval.device_id == 'DEMO-001'
                if index in actions:
                    # Separate event dispatch lets the frame timer continue in modal dialogs.
                    QTimer.singleShot(0, lambda action=actions[index]: perform(action))
                frame = window.grab()
                painter = QPainter(frame)
                origin = window.mapToGlobal(QPoint(0, 0))
                for widget in app.topLevelWidgets():
                    if isinstance(widget, (QFileDialog, QMessageBox)) and widget.isVisible():
                        # These top-level dialogs belong to this synthetic-only QApplication.
                        # QWidget.isAncestorOf excludes separate dialog windows on macOS.
                        key = 'save_frames' if isinstance(widget, QFileDialog) else 'success_frames'
                        state[key] += 1
                        painter.drawPixmap(widget.mapToGlobal(QPoint(0, 0)) - origin, widget.grab())
                painter.end()
                image = frame.toImage().scaled(1280, 960, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
                assert image.save(str(frames / f'{index:04d}.png'))
                state['frame'] += 1
                if state['frame'] == FRAMES:
                    assert state['zoom'] and csv.exists() and len(pd.read_csv(csv)) == 72
                    assert state['save_frames'] >= FPS and state['success_frames'] >= FPS
                    stop()
            except Exception as error:
                stop(f'Recording verification failed: {type(error).__name__}')

        timer = QTimer()
        timer.timeout.connect(capture)
        window.show()
        timer.start(round(1000 / FPS))
        app.exec_()
        os.chdir(previous_cwd)
        if state['error']:
            raise SystemExit(state['error'])
        subprocess.run([
            ffmpeg, '-hide_banner', '-loglevel', 'error', '-y', '-framerate', str(FPS),
            '-i', str(frames / '%04d.png'), '-c:v', 'libx264', '-threads', '2',
            '-preset', 'fast', '-crf', '26', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(output),
        ], check=True)
    print('Recorded 30 seconds of actual synthetic app interaction, including chart zoom, table sorting, and CSV export.')
    print(f'Video: {output}')


if __name__ == '__main__':
    record()

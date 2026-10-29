import sys
import datetime
import pytz
from tzlocal import get_localzone_name
import pandas as pd
from dotenv import load_dotenv
import tempfile
import logging
from pathlib import Path

from PyQt5.QtGui import QIcon, QPixmap, QPalette, QColor
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings
from PyQt5.QtCore import QAbstractTableModel, Qt, QVariant, QDate, QTime, QUrl, QThread, QTimer, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QComboBox,
    QDateEdit, QTimeEdit, QPushButton, QHBoxLayout,
    QMessageBox, QFileDialog, QTableView, QSizePolicy, QSplitter, QScrollArea,
    QFrame, QGridLayout, QStyle, QStyleFactory,
)

from biobeat.auth import get_access_token
from biobeat.fetch import get_all_measurements
from biobeat.plot import create_vitals_dashboard
from biobeat.utils import normalize_measurements, local_to_utc, export_csv
from biobeat.config import load_device_ids
from biobeat.errors import BioBeatError
from biobeat.demo import synthetic_measurements, DEMO_START, DEMO_END
from biobeat.quality import summarize_quality
from biobeat.results import RetrievalResult
from biobeat.theme import WORKBENCH_STYLE, TABLE_HEADERS

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv(Path.cwd() / '.env')


class PandasModel(QAbstractTableModel):
    """Improved DataFrame model for QTableView with better performance and type handling."""
    def __init__(self, df=None, parent=None):
        super().__init__(parent)
        self._df = df.copy().reset_index(drop=True) if df is not None else pd.DataFrame()
        self._column_types = self._determine_column_types()

    def _determine_column_types(self):
        """Determine the most appropriate type for each column to improve display."""
        type_map = {}
        for col in self._df.columns:
            if pd.api.types.is_numeric_dtype(self._df[col]):
                type_map[col] = float
            elif pd.api.types.is_datetime64_any_dtype(self._df[col]):
                type_map[col] = datetime.datetime
            else:
                type_map[col] = str
        return type_map

    def rowCount(self, parent=None):
        return len(self._df)

    def columnCount(self, parent=None):
        return len(self._df.columns)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return QVariant()

        row = index.row()
        col = index.column()
        col_name = self._df.columns[col]

        if role == Qt.DisplayRole:
            value = self._df.iloc[row, col]
            if pd.isna(value):
                return ""
            if self._column_types[col_name] == datetime.datetime:
                return value.strftime("%Y-%m-%d %H:%M:%S")
            return str(value)

        elif role == Qt.TextAlignmentRole:
            if self._column_types[col_name] in (int, float):
                return Qt.AlignRight | Qt.AlignVCenter
            return Qt.AlignLeft | Qt.AlignVCenter

        return QVariant()

    def sort(self, column, order=Qt.AscendingOrder):
        if not 0 <= column < len(self._df.columns):
            return
        self.layoutAboutToBeChanged.emit()
        old_indexes = self.persistentIndexList()
        original_rows = pd.Series(range(len(self._df)), index=self._df.index)
        self._df = self._df.sort_values(
            self._df.columns[column], ascending=order == Qt.AscendingOrder,
            kind='stable', na_position='last',
        )
        # Keep selections attached to the same records after reordering.
        new_rows = {old: new for new, old in enumerate(original_rows.loc[self._df.index])}
        self.changePersistentIndexList(old_indexes, [
            self.index(new_rows[index.row()], index.column()) for index in old_indexes
        ])
        self._df = self._df.reset_index(drop=True)
        self.layoutChanged.emit()

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return QVariant()
        if orientation == Qt.Horizontal:
            return TABLE_HEADERS.get(self._df.columns[section], self._df.columns[section])
        return str(section + 1)  # Row numbers start at 1

class RetrievalWorker(QThread):
    result = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, device_id, start, end, timezone, demo, directory, parent=None):
        super().__init__(parent)
        self.arguments = (device_id, start, end, timezone, demo, directory)

    def run(self):
        device_id, start, end, timezone, demo, directory = self.arguments
        try:
            if demo:
                records = synthetic_measurements()
            else:
                token = get_access_token()
                records = get_all_measurements(
                    device_id, start.strftime('%Y-%m-%dT%H:%M:%SZ'),
                    end.strftime('%Y-%m-%dT%H:%M:%SZ'), token,
                    cancelled=self.isInterruptionRequested,
                )
            if self.isInterruptionRequested():
                return
            df = normalize_measurements(records, timezone)
            path = ''
            if not df.empty:
                figure = create_vitals_dashboard(df, timezone)
                with tempfile.NamedTemporaryFile(dir=directory, suffix='.html', delete=False) as output:
                    path = output.name
                html = figure.to_html(include_plotlyjs=True, default_height='100vh',
                                      config={'responsive': True, 'displaylogo': False, 'displayModeBar': True})
                html = html.replace('<head>', '<head><style>body{margin:0}.plotly-graph-div{min-height:520px}</style>')
                Path(path).write_text(html, encoding='utf-8')
            if not self.isInterruptionRequested():
                self.result.emit(RetrievalResult(
                    df, path, device_id, timezone, start, end, summarize_quality(df),
                ))
        except BioBeatError as error:
            self.error.emit(str(error))
        except Exception:
            # Exception strings and tracebacks can contain URLs, tokens or data.
            logger.error('Retrieval or processing failed (details suppressed for privacy).')
            self.error.emit('Could not process measurements. Verify the API configuration and response format.')


class BiobeatApp(QWidget):
    def __init__(self, demo=False):
        super().__init__()
        resource_root = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
        self.setWindowIcon(QIcon(str(resource_root / 'res' / 'app-icon.png')))
        self.demo = demo
        self.df = None
        self.retrieval = None
        self._demo_started = False
        self.worker = None
        self.closing = False
        self.plot_directory = tempfile.TemporaryDirectory(prefix='biobeat-')
        self.configuration_error = ''
        try:
            self.devices = ['DEMO-001'] if demo else load_device_ids()
        except BioBeatError as error:
            self.devices = []
            self.configuration_error = str(error)
        self._init_ui()
        self._setup_connections()
        if self.demo:
            self.timezone_dropdown.setCurrentText('Europe/Zurich')
            self._update_demo_range()
        self._set_ui_enabled(True)

    def showEvent(self, event):
        super().showEvent(event)
        if self.demo and not self._demo_started:
            self._demo_started = True
            QTimer.singleShot(0, self._on_fetch)

    def _update_demo_range(self):
        timezone = pytz.timezone(self.timezone_dropdown.currentText())
        for stamp, date_control, time_control in [
            (DEMO_START, self.start_date_edit, self.start_time_edit),
            (DEMO_END, self.end_date_edit, self.end_time_edit),
        ]:
            local = stamp.astimezone(timezone)
            date_control.setDate(QDate(local.year, local.month, local.day))
            time_control.setTime(QTime(local.hour, local.minute))

    def _init_ui(self):
        """Initialize all UI components."""
        self.setWindowTitle("Vitals Explorer")
        self.setMinimumSize(1000, 800)

        self.resize(1280, 960)
        # Fusion and an explicit palette keep controls readable on dark OS themes.
        self._workbench_style = QStyleFactory.create('Fusion')
        self.setStyle(self._workbench_style)
        palette = self.palette()
        for role, color in [(QPalette.Window, '#f7f9fc'), (QPalette.Base, '#ffffff'),
                            (QPalette.Text, '#18324f'), (QPalette.WindowText, '#18324f'),
                            (QPalette.Button, '#ffffff'), (QPalette.ButtonText, '#18324f'),
                            (QPalette.Highlight, '#ccefee'), (QPalette.HighlightedText, '#18324f')]:
            palette.setColor(role, QColor(color))
        self.setPalette(palette)
        self.setStyleSheet(WORKBENCH_STYLE)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        header = QFrame()
        header.setObjectName('appHeader')
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 14, 22, 14)
        icon = QLabel()
        resource_root = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
        icon.setPixmap(QPixmap(str(resource_root / 'res/app-icon.png')).scaled(
            46, 46, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        header_layout.addWidget(icon)
        title = QLabel('Vitals Explorer')
        title.setObjectName('appTitle')
        header_layout.addWidget(title)
        subtitle = QLabel('Research Workbench')
        subtitle.setObjectName('subtitle')
        header_layout.addWidget(subtitle)
        header_layout.addStretch()
        self.mode_badge = QLabel('SYNTHETIC DEMO' if self.demo else 'LIVE API')
        self.mode_badge.setObjectName('modeBadge')
        header_layout.addWidget(self.mode_badge)
        main_layout.addWidget(header)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        main_layout.addLayout(body, 1)
        self.sidebar = QScrollArea()
        self.sidebar.setObjectName('sidebar')
        self.sidebar.setWidgetResizable(True)
        self.sidebar.setFixedWidth(258)
        self.sidebar.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        panel = QWidget()
        panel.setObjectName('controlPanel')
        form_layout = QVBoxLayout(panel)
        form_layout.setContentsMargins(20, 18, 20, 20)
        form_layout.setSpacing(10)
        heading = QLabel('Sample' if self.demo else 'Retrieval')
        heading.setObjectName('sectionTitle')
        form_layout.addWidget(heading)
        self.device_label = QLabel('Device ID')
        self.device_dropdown = QComboBox()
        self.device_dropdown.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.device_dropdown.setMinimumContentsLength(12)
        self.device_dropdown.addItems(['Select a device', *self.devices])
        if self.demo:
            self.device_dropdown.setCurrentIndex(1)
            self.setWindowTitle('Vitals Explorer — SYNTHETIC DEMONSTRATION')
        form_layout.addWidget(self.device_label)
        form_layout.addWidget(self.device_dropdown)
        self._init_datetime_controls()
        for label, layout in [('Start date and time', self.start_datetime_layout),
                              ('End date and time', self.end_datetime_layout)]:
            form_layout.addWidget(QLabel(label))
            form_layout.addLayout(layout)
        self.timezone_label = QLabel('Time zone')
        self.timezone_dropdown = QComboBox()
        self.timezone_dropdown.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.timezone_dropdown.setMinimumContentsLength(12)
        self.timezone_dropdown.addItems(sorted(pytz.all_timezones))
        self.timezone_dropdown.setCurrentText(get_localzone_name())
        self.timezone_dropdown.setAccessibleName('Display time zone')
        form_layout.addWidget(self.timezone_label)
        form_layout.addWidget(self.timezone_dropdown)
        self.fetch_button = QPushButton('Reload demo' if self.demo else 'Fetch data')
        self.fetch_button.setObjectName('primaryAction')
        self.fetch_button.setIcon(self.style().standardIcon(QStyle.SP_BrowserReload))
        self.download_button = QPushButton('Export CSV')
        self.download_button.setIcon(self.style().standardIcon(QStyle.SP_DialogSaveButton))
        self.download_button.setEnabled(False)
        form_layout.addSpacing(6)
        form_layout.addWidget(self.fetch_button)
        form_layout.addWidget(self.download_button)
        self.status_label = QLabel(
            'Fixed synthetic sample. No API requests.' if self.demo else
            self.configuration_error or ('Ready.' if self.devices else
                'No devices configured. Set BIOBEAT_DEVICE_IDS in your local .env and restart.'))
        self.status_label.setWordWrap(True)
        self.status_label.setObjectName('statusText')
        self.status_label.setTextFormat(Qt.PlainText)
        form_layout.addWidget(self.status_label)
        divider = QFrame()
        divider.setObjectName('sectionDivider')
        divider.setFixedHeight(1)
        form_layout.addSpacing(8)
        form_layout.addWidget(divider)
        heading = QLabel('Loaded dataset')
        heading.setObjectName('sectionTitle')
        form_layout.addWidget(heading)
        self.quality_label = QLabel('No measurements loaded.')
        self.quality_label.setWordWrap(True)
        self.quality_label.setTextFormat(Qt.PlainText)
        self.quality_label.setObjectName('qualitySummary')
        self.quality_label.setToolTip(
            'Missing values count the six physiological measurements. Intervals are inferred '
            'from observed timestamps, not confirmed missing measurements or a clinical assessment.')
        form_layout.addWidget(self.quality_label)
        self.quality_grid = QGridLayout()
        self.quality_grid.setHorizontalSpacing(10)
        self.quality_grid.setVerticalSpacing(12)
        self.quality_values = {}
        for row, (key, label) in enumerate([
            ('records', 'Total records'), ('coverage', 'Actual coverage'), ('timezone', 'Time zone'),
            ('missing', 'Missing values'), ('duplicates', 'Duplicate timestamps'),
            ('median', 'Observed median interval'), ('long', 'Long intervals (>3× median)'),
        ]):
            caption, value = QLabel(label), QLabel('—')
            caption.setWordWrap(True)
            value.setWordWrap(True)
            value.setTextFormat(Qt.PlainText)
            value.setTextInteractionFlags(Qt.TextSelectableByMouse)
            value.setObjectName('qualityValue')
            caption.setFixedWidth(105)
            self.quality_grid.addWidget(caption, row, 0, Qt.AlignTop)
            self.quality_grid.addWidget(value, row, 1, Qt.AlignTop)
            self.quality_values[key] = value
        form_layout.addLayout(self.quality_grid)
        note = QLabel('Intervals inferred from timestamps; not confirmed missing measurements.')
        note.setWordWrap(True)
        note.setObjectName('statusText')
        form_layout.addWidget(note)
        form_layout.addStretch()
        self.sidebar.setWidget(panel)
        body.addWidget(self.sidebar)

        self.plot_view = QWebEngineView()
        self.plot_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.plot_view.setHtml('<body style="font:14px sans-serif;color:#526780;background:#fff">'
                               '<p>Select a device and interval, then fetch data.</p></body>')
        self.table_view = QTableView()
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setSortingEnabled(True)
        self.table_view.verticalHeader().setDefaultSectionSize(28)
        self.table_view.horizontalHeader().setMinimumSectionSize(70)
        self.splitter = QSplitter(Qt.Vertical)
        self.splitter.addWidget(self.plot_view)
        self.splitter.addWidget(self.table_view)
        self.plot_view.setMinimumHeight(160)
        self.table_view.setMinimumHeight(120)
        self.splitter.setStretchFactor(0, 2)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setSizes([570, 285])
        self.splitter.setHandleWidth(9)
        body.addWidget(self.splitter, 1)

    def _update_quality(self, result):
        quality = result.quality
        self.quality_label.setText(quality.describe(result.timezone))
        # The accessible full description remains available, while the grid is scanned visually.
        self.sidebar.setAccessibleDescription(self.quality_label.text())
        self.quality_label.setVisible(not quality.records)
        values = dict.fromkeys(self.quality_values, '—')
        if quality.records:
            values.update(
                records=str(quality.records),
                coverage=f'{quality.first:%Y-%m-%d}\n{quality.first:%H:%M} – {quality.last:%Y-%m-%d %H:%M}'
                if quality.first.date() != quality.last.date() else
                f'{quality.first:%Y-%m-%d}\n{quality.first:%H:%M} – {quality.last:%H:%M}',
                timezone=result.timezone, missing=f'{quality.missing} / {quality.records * 6}',
                duplicates=str(quality.duplicates),
                median='Insufficient intervals' if quality.median_seconds is None else
                f'{quality.median_seconds / 60:g} min',
                long='—' if quality.median_seconds is None else str(quality.long_intervals),
            )
        for key, value in values.items():
            self.quality_values[key].setText(value)

    def _init_datetime_controls(self):
        """Initialize datetime controls with sensible defaults."""
        # Start datetime (24 hours ago)
        self.start_date_edit = QDateEdit(calendarPopup=True)
        self.start_time_edit = QTimeEdit()
        self.start_date_edit.setDate(QDate.currentDate().addDays(-1))
        self.start_time_edit.setTime(QTime(0, 0))

        # End datetime (now)
        self.end_date_edit = QDateEdit(calendarPopup=True)
        self.end_time_edit = QTimeEdit()
        self.end_date_edit.setDate(QDate.currentDate())
        self.end_time_edit.setTime(QTime.currentTime())

        # Layouts
        self.start_date_edit.setDisplayFormat('yyyy-MM-dd')
        self.end_date_edit.setDisplayFormat('yyyy-MM-dd')
        self.start_time_edit.setDisplayFormat('HH:mm')
        self.end_time_edit.setDisplayFormat('HH:mm')
        self.start_datetime_layout = QHBoxLayout()
        self.start_time_edit.setFixedWidth(76)
        self.end_time_edit.setFixedWidth(76)
        self.start_datetime_layout.addWidget(self.start_date_edit, 1)
        self.start_datetime_layout.addWidget(self.start_time_edit)

        self.end_datetime_layout = QHBoxLayout()
        self.end_datetime_layout.addWidget(self.end_date_edit, 1)
        self.end_datetime_layout.addWidget(self.end_time_edit)

    def _setup_connections(self):
        """Connect signals to slots."""
        self.timezone_dropdown.currentTextChanged.connect(self._update_timezone_label)
        self.fetch_button.clicked.connect(self._on_fetch)
        self.download_button.clicked.connect(self._download_csv)

    def _update_timezone_label(self, timezone):
        """Update the displayed timezone label when dropdown changes."""
        self.timezone_label.setToolTip(timezone)
        if self.demo:
            self._update_demo_range()
            if self._demo_started and self.worker is None and not self.closing:
                self._on_fetch()

    def _validate_inputs(self):
        """Validate user inputs before fetching data."""
        device_id = self.device_dropdown.currentText()
        if device_id not in self.devices:
            QMessageBox.warning(self, "Invalid ID", "Please select a valid device ID.")
            return False

        # Get selected timezone
        tz_name = self.timezone_dropdown.currentText()
        try:
            pytz.timezone(tz_name)
        except pytz.UnknownTimeZoneError:
            QMessageBox.warning(self, "Timezone Error", "Invalid timezone selected.")
            return False

        # Validate time range
        start_dt = datetime.datetime.combine(
            self.start_date_edit.date().toPyDate(),
            self.start_time_edit.time().toPyTime()
        )
        end_dt = datetime.datetime.combine(
            self.end_date_edit.date().toPyDate(),
            self.end_time_edit.time().toPyTime()
        )

        if start_dt >= end_dt:
            QMessageBox.warning(self, "Invalid Range", "Start time must be before end time.")
            return False

        return True

    def _get_datetime_range(self):
        """Get the selected datetime range in UTC."""
        tz_name = self.timezone_dropdown.currentText()
        if self.demo:
            return DEMO_START, DEMO_END, tz_name

        start_dt_local = datetime.datetime.combine(
            self.start_date_edit.date().toPyDate(),
            self.start_time_edit.time().toPyTime()
        )
        end_dt_local = datetime.datetime.combine(
            self.end_date_edit.date().toPyDate(),
            self.end_time_edit.time().toPyTime()
        )

        start_utc = local_to_utc(start_dt_local, tz_name)
        end_utc = local_to_utc(end_dt_local, tz_name)

        return start_utc, end_utc, tz_name

    def _on_fetch(self):
        if self.closing or self.worker is not None or not self._validate_inputs():
            return
        try:
            start, end, timezone = self._get_datetime_range()
        except BioBeatError as error:
            QMessageBox.warning(self, 'Invalid local time', str(error))
            return
        self._set_ui_enabled(False)
        self.status_label.setText('Loading and processing measurements…')
        self.worker = RetrievalWorker(
            self.device_dropdown.currentText(), start, end, timezone,
            self.demo, self.plot_directory.name, self,
        )
        self.worker.result.connect(self._retrieval_result)
        self.worker.error.connect(self._retrieval_error)
        self.worker.finished.connect(self._retrieval_finished)
        self.worker.start()

    def _retrieval_result(self, result):
        if self.closing:
            return
        self.retrieval = result
        df, path = result.dataframe, result.plot_path
        self.df = df
        self._update_quality(result)
        # Retain only the latest private plot after the worker has completed.
        for previous in Path(self.plot_directory.name).glob('*.html'):
            if str(previous) != path:
                try:
                    previous.unlink(missing_ok=True)
                except OSError:
                    logger.warning('Previous plot cleanup failed; retrying at shutdown.')
        if path:
            self.plot_view.load(QUrl.fromLocalFile(path))
        else:
            self.plot_view.setHtml('<p>No measurements returned.</p>')
        self._update_table(df)
        prefix = 'SYNTHETIC DEMONSTRATION — ' if self.demo else ''
        self.status_label.setText(prefix + (f'{len(df)} measurements loaded.' if len(df) else 'No measurements returned.'))

    def _retrieval_error(self, message):
        if not self.closing:
            self.status_label.setText(message)
            QMessageBox.critical(self, 'Retrieval error', message)

    def _retrieval_finished(self):
        worker = self.worker
        self.worker = None
        worker.deleteLater()
        self._set_ui_enabled(True)
        if self.closing:
            self.close()

    def _update_table(self, df):
        """Update the table view with new data."""
        model = PandasModel(df)
        self.table_view.setModel(model)
        if 'datetime_tz' in df:
            self.table_view.sortByColumn(df.columns.get_loc('datetime_tz'), Qt.AscendingOrder)
        self.table_view.resizeColumnsToContents()
        header = self.table_view.horizontalHeader()
        preferred = ['datetime_tz', 'sbp', 'dbp', 'hr', 'spo2', 'rr', 'temp',
                     'datetime_utc', 'timezone', 'battery', 'offline_records']
        for position, column in enumerate(col for col in preferred if col in df.columns):
            header.moveSection(header.visualIndex(df.columns.get_loc(column)), position)

    def _download_csv(self):
        """Handle CSV download with better filename generation."""
        if self.df is None or self.df.empty:
            QMessageBox.warning(self, "No Data", "No data available to download.")
            return

        default_name = self.retrieval.export_filename()

        filepath, _ = QFileDialog.getSaveFileName(
            self, "Save CSV", default_name, "CSV Files (*.csv)"
        )

        if filepath:
            try:
                export_csv(self.df, filepath)
                QMessageBox.information(
                    self, "Success",
                    f"Data successfully saved to:\n{filepath}"
                )
            except Exception:
                logger.error("CSV export failed.")
                QMessageBox.critical(
                    self, "Error",
                    "Could not save CSV. Check destination permissions and disk space."
                )

    def _set_ui_enabled(self, enabled):
        """Enable or disable UI controls during operations."""
        self.device_dropdown.setEnabled(enabled and not self.demo)
        self.timezone_dropdown.setEnabled(enabled)
        self.start_date_edit.setEnabled(enabled and not self.demo)
        self.start_time_edit.setEnabled(enabled and not self.demo)
        self.end_date_edit.setEnabled(enabled and not self.demo)
        self.end_time_edit.setEnabled(enabled and not self.demo)
        self.fetch_button.setEnabled(enabled and bool(self.devices))
        self.download_button.setEnabled(enabled and self.df is not None and not self.df.empty)

    def closeEvent(self, event):
        self.closing = True
        if self.worker is not None:
            self.closing = True
            self.worker.requestInterruption()
            self.status_label.setText('Closing after the current bounded request finishes…')
            self._set_ui_enabled(False)
            event.ignore()
            return
        self.plot_view.stop()
        self.plot_directory.cleanup()
        event.accept()


def main():
    """Main application entry point."""
    # Enable high DPI scaling
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

    app = QApplication(sys.argv)

    # Configure WebEngine settings
    web_settings = QWebEngineSettings.globalSettings()
    web_settings.setAttribute(QWebEngineSettings.PluginsEnabled, False)
    web_settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
    web_settings.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, False)

    window = BiobeatApp(demo='--demo' in sys.argv)
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

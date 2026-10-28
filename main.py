import sys
import datetime
import pytz
from tzlocal import get_localzone_name
import pandas as pd
from dotenv import load_dotenv
import tempfile
import logging
from pathlib import Path

from PyQt5.QtGui import QIcon
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings
from PyQt5.QtCore import QAbstractTableModel, Qt, QVariant, QDate, QTime, QUrl, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QComboBox,
    QDateEdit, QTimeEdit, QPushButton, QHBoxLayout,
    QMessageBox, QFileDialog, QTableView, QSizePolicy,
)

from biobeat.auth import get_access_token
from biobeat.fetch import get_all_measurements
from biobeat.plot import create_vitals_dashboard
from biobeat.utils import normalize_measurements, local_to_utc, export_csv
from biobeat.config import load_device_ids
from biobeat.errors import BioBeatError
from biobeat.demo import synthetic_measurements

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv(Path.cwd() / '.env')


class PandasModel(QAbstractTableModel):
    """Improved DataFrame model for QTableView with better performance and type handling."""
    def __init__(self, df=None, parent=None):
        super().__init__(parent)
        self._df = df.copy() if df is not None else pd.DataFrame()
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

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return QVariant()
        if orientation == Qt.Horizontal:
            return self._df.columns[section]
        return str(section + 1)  # Row numbers start at 1

class RetrievalWorker(QThread):
    result = pyqtSignal(object, str)
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
                if demo:
                    figure.update_layout(title_text='SYNTHETIC DEMONSTRATION — fictional measurements')
                with tempfile.NamedTemporaryFile(dir=directory, suffix='.html', delete=False) as output:
                    path = output.name
                figure.write_html(path, include_plotlyjs=True)
            if not self.isInterruptionRequested():
                self.result.emit(df, path)
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
            self.start_date_edit.setDate(QDate(2026, 1, 15))
            self.end_date_edit.setDate(QDate(2026, 1, 15))
            self.start_time_edit.setTime(QTime(9, 0))
            self.end_time_edit.setTime(QTime(15, 0))
            self.timezone_dropdown.setCurrentText('Europe/Zurich')

    def _init_ui(self):
        """Initialize all UI components."""
        self.setWindowTitle("Vitals Explorer")
        self.setMinimumSize(1000, 800)

        # Main layout with stretch factors
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Form layout for controls
        form_layout = QVBoxLayout()

        # Device selection
        self.device_label = QLabel("Device ID:")
        self.device_dropdown = QComboBox()
        self.device_dropdown.addItems(['Please select a device ID', *self.devices])
        if self.demo:
            self.device_dropdown.setCurrentIndex(1)
            self.setWindowTitle('Vitals Explorer — SYNTHETIC DEMONSTRATION')

        # Timezone selection
        self.timezone_label = QLabel(f"Time Zone: {get_localzone_name()}")
        self.timezone_toggle = QPushButton("Change Timezone")

        # Create widget for timezone selection
        timezone_device_line = QHBoxLayout()
        timezone_device_line.addWidget(self.device_label)
        timezone_device_line.addWidget(self.device_dropdown)
        timezone_device_line.addWidget(self.timezone_label)
        timezone_device_line.addWidget(self.timezone_toggle)

        # Timezone dropdown (hidden by default)
        self.timezone_dropdown = QComboBox()
        self.timezone_dropdown.addItems(sorted(pytz.all_timezones))
        self.timezone_dropdown.setCurrentText(get_localzone_name())
        self.timezone_dropdown.hide()

        form_layout.addLayout(timezone_device_line)
        form_layout.addWidget(self.timezone_dropdown)

        # Date/time range
        self._init_datetime_controls()
        form_layout.addWidget(QLabel("Start Date and Time:"))
        form_layout.addLayout(self.start_datetime_layout)
        form_layout.addWidget(QLabel("End Date and Time:"))
        form_layout.addLayout(self.end_datetime_layout)

        # Buttons
        self.fetch_button = QPushButton("Fetch Data")
        self.download_button = QPushButton("Download CSV")
        self.download_button.setEnabled(False)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.fetch_button)
        button_layout.addWidget(self.download_button)
        form_layout.addLayout(button_layout)

        # Add form to main layout
        self.status_label = QLabel(
            'SYNTHETIC DEMONSTRATION — fictional device and measurements; no API requests.'
            if self.demo else self.configuration_error or (
                'Ready.' if self.devices else
                'No devices configured. Set BIOBEAT_DEVICE_IDS in your local .env and restart.'
            )
        )
        self.status_label.setWordWrap(True)
        form_layout.addWidget(self.status_label)
        self.fetch_button.setEnabled(bool(self.devices))
        main_layout.addLayout(form_layout)

        # Tabbed view for plot and data
        self.plot_view = QWebEngineView()
        self.plot_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.table_view = QTableView()
        self.table_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setSortingEnabled(True)

        main_layout.addWidget(self.plot_view, stretch=2)
        main_layout.addWidget(self.table_view, stretch=1)

        self.setLayout(main_layout)

        # Apply some basic styling
        self.setStyleSheet("""
            QPushButton {
                padding: 5px;
                min-width: 80px;
            }
        """)

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
        self.start_datetime_layout = QHBoxLayout()
        self.start_datetime_layout.addWidget(self.start_date_edit)
        self.start_datetime_layout.addWidget(self.start_time_edit)

        self.end_datetime_layout = QHBoxLayout()
        self.end_datetime_layout.addWidget(self.end_date_edit)
        self.end_datetime_layout.addWidget(self.end_time_edit)

    def _setup_connections(self):
        """Connect signals to slots."""
        self.timezone_toggle.clicked.connect(self._toggle_timezone_dropdown)
        self.timezone_dropdown.currentTextChanged.connect(self._update_timezone_label)
        self.fetch_button.clicked.connect(self._on_fetch)
        self.download_button.clicked.connect(self._download_csv)

    def _update_timezone_label(self, timezone):
        """Update the displayed timezone label when dropdown changes."""
        self.timezone_label.setText(f"Time Zone: {timezone}")

    def _toggle_timezone_dropdown(self):
        """Toggle visibility of timezone dropdown."""
        visible = self.timezone_dropdown.isVisible()
        self.timezone_dropdown.setVisible(not visible)
        self.timezone_toggle.setText("Hide Timezone" if not visible else "Change Timezone")

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
        if self.worker is not None or not self._validate_inputs():
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

    def _retrieval_result(self, df, path):
        if self.closing:
            return
        self.df = df
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
        self.table_view.resizeColumnsToContents()

    def _download_csv(self):
        """Handle CSV download with better filename generation."""
        if self.df is None or self.df.empty:
            QMessageBox.warning(self, "No Data", "No data available to download.")
            return

        device_id = self.device_dropdown.currentText()
        start_dt = self.df["datetime_utc"].min()
        end_dt = self.df["datetime_utc"].max()

        default_name = (
            f"biobeat_{device_id}_"
            f"{start_dt.strftime('%Y%m%d_%H%M')}_to_"
            f"{end_dt.strftime('%Y%m%d_%H%M')}.csv"
        )

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
        self.device_dropdown.setEnabled(enabled)
        self.timezone_toggle.setEnabled(enabled)
        self.timezone_dropdown.setEnabled(enabled)
        self.start_date_edit.setEnabled(enabled)
        self.start_time_edit.setEnabled(enabled)
        self.end_date_edit.setEnabled(enabled)
        self.end_time_edit.setEnabled(enabled)
        self.fetch_button.setEnabled(enabled and bool(self.devices))
        self.download_button.setEnabled(enabled and self.df is not None and not self.df.empty)

    def closeEvent(self, event):
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

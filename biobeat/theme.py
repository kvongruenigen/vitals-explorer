"""Visual tokens and display labels; exported dataframe column names stay unchanged."""
TABLE_HEADERS = {
    'datetime_tz': 'Local time', 'datetime_utc': 'UTC time', 'timezone': 'Time zone',
    'sbp': 'SBP (mmHg)', 'dbp': 'DBP (mmHg)', 'hr': 'Heart rate (bpm)',
    'spo2': 'SpO₂ (%)', 'rr': 'Respiration (breaths/min)', 'temp': 'Temperature (°C)',
    'battery': 'Battery', 'offline_records': 'Offline records',
}
WORKBENCH_STYLE = """
QWidget { font-family: Arial; font-size: 13px; font-weight: normal;
          color: #18324f; background: #f7f9fc; }
QFrame#appHeader { background: #ffffff; border-bottom: 1px solid #d5dfe9; }
QFrame#appHeader QLabel { background: transparent; }
QLabel { font-weight: normal; }
QLabel#appTitle { font-size: 27px; font-weight: 700; padding-left: 6px; }
QLabel#subtitle { font-size: 19px; color: #61758c; padding-left: 18px; }
QFrame#appHeader QLabel#modeBadge { background: #ccefee; color: #075f67; border-radius: 14px;
                  padding: 7px 14px; font-size: 12px; font-weight: 700; }
QScrollArea#sidebar { border: 0; border-right: 1px solid #d5dfe9; }
QWidget#controlPanel, QWidget#controlPanel QLabel { background: #edf3f8; }
QLabel#sectionTitle { font-size: 17px; font-weight: 700; padding-bottom: 5px; }
QLabel#statusText { font-size: 11px; color: #526780; }
QLabel#qualityValue { color: #18324f; }
QFrame#sectionDivider { background: #c6d4e2; }
QComboBox, QDateEdit, QTimeEdit { background: #ffffff; border: 1px solid #c5d3e0;
    border-radius: 4px; padding: 7px 5px; min-height: 18px; selection-background-color: #ccefee; }
QComboBox:disabled, QDateEdit:disabled, QTimeEdit:disabled {
    background: #e6edf4; color: #526780; border-color: #cbd7e3; }
QComboBox:focus, QDateEdit:focus, QTimeEdit:focus, QPushButton:focus { border: 2px solid #07838c; }
QComboBox QAbstractItemView { background: white; color: #18324f;
    selection-background-color: #ccefee; selection-color: #18324f; }
QPushButton { background: #ffffff; border: 1px solid #078a94; border-radius: 5px;
    padding: 10px 8px; font-weight: 600; }
QPushButton:hover { background: #e0f3f3; }
QPushButton#primaryAction { background: #07858f; color: white; }
QPushButton#primaryAction:hover { background: #066b74; }
QPushButton:disabled { color: #64788b; background: #e4ebf1; border-color: #c5d3e0; }
QTableView { background: white; alternate-background-color: #f2f6fa; gridline-color: #e0e7ef;
    border: 0; selection-background-color: #d4f1f1; selection-color: #18324f; }
QHeaderView::section { background: #eaf0f6; color: #18324f; padding: 8px;
    border: 0; border-right: 1px solid #d5dfe9; border-bottom: 1px solid #d5dfe9; font-weight: 600; }
QTableCornerButton::section { background: #eaf0f6; border: 0; }
QSplitter::handle { background: #dce5ee; }
QSplitter::handle:hover { background: #91cacc; }
QToolTip { background: white; color: #18324f; border: 1px solid #c5d3e0; }
"""

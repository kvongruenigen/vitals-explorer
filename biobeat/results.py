"""A successful retrieval and its provenance travel together to the GUI."""
from dataclasses import dataclass
from datetime import datetime

import pandas as pd

from biobeat.quality import QualitySummary


@dataclass(frozen=True)
class RetrievalResult:
    dataframe: pd.DataFrame
    plot_path: str
    device_id: str
    timezone: str
    start_utc: datetime
    end_utc: datetime
    quality: QualitySummary

    def export_filename(self):
        first = self.dataframe['datetime_utc'].min()
        last = self.dataframe['datetime_utc'].max()
        return f'vitals_{self.device_id}_{first:%Y%m%d_%H%M}_to_{last:%Y%m%d_%H%M}.csv'

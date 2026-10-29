"""Descriptive data quality, without assuming a device sampling schedule."""
from dataclasses import dataclass

import pandas as pd

from biobeat.utils import VITALS


@dataclass(frozen=True)
class QualitySummary:
    records: int
    first: pd.Timestamp | None = None
    last: pd.Timestamp | None = None
    missing: int = 0
    duplicates: int = 0
    median_seconds: float | None = None
    long_intervals: int = 0

    def describe(self, timezone):
        if not self.records:
            return 'No measurements loaded.'
        coverage = f'{self.first:%Y-%m-%d %H:%M} – {self.last:%Y-%m-%d %H:%M} ({timezone})'
        intervals = (
            'Insufficient intervals to estimate cadence/gaps.'
            if self.median_seconds is None else
            f'Observed median interval: {self.median_seconds:g} s; '
            f'long intervals (>3× median): {self.long_intervals} '
            '(inferred, not confirmed missing measurements).'
        )
        return (
            f'{self.records} records | {coverage}\n'
            f'Missing vital values: {self.missing}/{self.records * len(VITALS)} | '
            f'Duplicate timestamps: {self.duplicates} | {intervals}'
        )


def summarize_quality(df):
    if df.empty:
        return QualitySummary(0)
    timestamps = df['datetime_utc']
    unique = timestamps.drop_duplicates().sort_values()
    intervals = unique.diff().dropna().dt.total_seconds()
    median = float(intervals.median()) if len(intervals) >= 2 else None
    return QualitySummary(
        records=len(df), first=df['datetime_tz'].min(), last=df['datetime_tz'].max(),
        missing=int(df.reindex(columns=VITALS).isna().sum().sum()),
        duplicates=int(timestamps.duplicated().sum()), median_seconds=median,
        long_intervals=int((intervals > 3 * median).sum()) if median is not None else 0,
    )

"""Deterministic, entirely synthetic measurements. No API access."""
from datetime import datetime, timedelta, timezone
import math


def synthetic_measurements():
    start = datetime(2026, 1, 15, 8, tzinfo=timezone.utc)
    return [dict(datetime=(start + timedelta(minutes=5*i)).isoformat(),
                 sbp=round(113 + 8*math.sin(i/8), 1),
                 dbp=round(73 + 5*math.sin(i/9), 1),
                 hr=round(72 + 9*math.sin(i/7), 1),
                 spo2=round(98 + math.sin(i/10), 1),
                 rr=round(15 + 2*math.sin(i/6), 1),
                 temp=round(36.8 + .2*math.sin(i/12), 2),
                 battery=90, offline_records=0) for i in range(72)]

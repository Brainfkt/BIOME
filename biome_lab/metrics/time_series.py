from __future__ import annotations

from typing import Dict, List, Optional


class TimeSeries:
    def __init__(self) -> None:
        self.rows: List[Dict[str, float]] = []

    def append(self, row: Dict[str, float]) -> None:
        self.rows.append(row)

    def latest(self) -> Optional[Dict[str, float]]:
        if not self.rows:
            return None
        return self.rows[-1]

    def to_dataframe(self):
        import pandas as pd

        return pd.DataFrame(self.rows)


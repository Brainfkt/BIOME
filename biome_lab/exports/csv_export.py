from __future__ import annotations

from pathlib import Path
from typing import Dict, List


def save_metrics_csv(rows: List[Dict[str, float]], path: Path) -> Path:
    import pandas as pd

    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


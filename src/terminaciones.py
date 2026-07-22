"""Deriva un DataFrame de terminaciones (últimos 2 dígitos de cada número)
para poder reusar las mismas funciones de stats.py / predictor.py, pero con
max_numero=99 en vez de 9999."""
from __future__ import annotations

import pandas as pd


def dataframe_terminaciones(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["numero"] = out["numero"] % 100
    return out

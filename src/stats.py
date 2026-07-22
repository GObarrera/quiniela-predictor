"""Estadística descriptiva sobre los sorteos cargados."""
from __future__ import annotations

import pandas as pd


def frequency_table(df: pd.DataFrame, max_numero: int) -> pd.DataFrame:
    """Frecuencia absoluta y relativa de cada número en el rango [0, max_numero]."""
    total = len(df)
    counts = df["numero"].value_counts().reindex(range(max_numero + 1), fill_value=0)
    freq = pd.DataFrame({
        "numero": counts.index,
        "frecuencia_absoluta": counts.to_numpy(),
    })
    freq["frecuencia_relativa"] = freq["frecuencia_absoluta"] / total if total else 0.0
    return freq.sort_values("numero").reset_index(drop=True)


def moving_frequency(df: pd.DataFrame, window: int, max_numero: int) -> pd.DataFrame:
    """Frecuencia calculada solo sobre los últimos `window` sorteos (recencia)."""
    recent = df.tail(window)
    result = frequency_table(recent, max_numero)
    return result.rename(columns={
        "frecuencia_absoluta": f"frecuencia_absoluta_ult_{window}",
        "frecuencia_relativa": f"frecuencia_relativa_ult_{window}",
    })


def gaps(df: pd.DataFrame, max_numero: int) -> pd.DataFrame:
    """Ausencia actual: cantidad de sorteos desde la última aparición de cada número."""
    total_draws = len(df)
    last_index: dict[int, int] = {}
    for i, numero in enumerate(df["numero"].to_numpy()):
        last_index[int(numero)] = i

    rows = []
    for n in range(max_numero + 1):
        if n in last_index:
            ausencia_actual = total_draws - 1 - last_index[n]
        else:
            ausencia_actual = total_draws  # nunca salió en la muestra
        rows.append({"numero": n, "ausencia_actual": ausencia_actual})
    return pd.DataFrame(rows)


def hot_cold(freq_df: pd.DataFrame, gaps_df: pd.DataFrame, top_n: int) -> dict[str, pd.DataFrame]:
    """Números 'calientes' (más frecuentes) y 'fríos' (mayor ausencia). Puramente descriptivo."""
    merged = freq_df.merge(gaps_df, on="numero")
    calientes = merged.sort_values("frecuencia_absoluta", ascending=False).head(top_n)
    frios = merged.sort_values("ausencia_actual", ascending=False).head(top_n)
    return {"calientes": calientes.reset_index(drop=True), "frios": frios.reset_index(drop=True)}

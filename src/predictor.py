"""Motor de puntuación heurística.

Importante: esto NO es un predictor determinista ni afirma haber descubierto
el mecanismo del sorteo. Es un ranking descriptivo que combina frecuencia
histórica, frecuencia reciente y ausencia actual. Su utilidad real depende
del resultado de `randomness.chi_square_uniformity`: si esa prueba no
rechaza H0, el ranking no tiene valor predictivo más allá de la curiosidad
estadística, y el reporte debe dejarlo explícito.
"""
from __future__ import annotations

import pandas as pd


def score_numeros(
    freq_total: pd.DataFrame,
    freq_reciente: pd.DataFrame,
    gaps_df: pd.DataFrame,
    peso_reciente: float = 0.5,
    peso_ausencia: float = 0.2,
) -> pd.DataFrame:
    df = freq_total.merge(gaps_df, on="numero")
    reciente_col = next(c for c in freq_reciente.columns if c.startswith("frecuencia_relativa_ult_"))
    df = df.merge(freq_reciente[["numero", reciente_col]], on="numero")

    def normalizar(serie: pd.Series) -> pd.Series:
        rango = serie.max() - serie.min()
        if rango == 0:
            return serie * 0.0
        return (serie - serie.min()) / rango

    peso_historico = 1 - peso_reciente - peso_ausencia
    df["score"] = (
        peso_historico * normalizar(df["frecuencia_relativa"])
        + peso_reciente * normalizar(df[reciente_col])
        + peso_ausencia * normalizar(df["ausencia_actual"])
    )
    return df.sort_values("score", ascending=False).reset_index(drop=True)

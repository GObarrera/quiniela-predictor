"""Dependencias temporales y entre posiciones (Fase 2): correlación entre
números de distintas posiciones, autocorrelación, correlación cruzada y
dependencia por día de la semana."""
from __future__ import annotations

import numpy as np
import pandas as pd


def pivot_por_posicion(df: pd.DataFrame) -> pd.DataFrame:
    """Una fila por sorteo (fecha), una columna por posición (1..20)."""
    return df.pivot_table(index="fecha", columns="posicion", values="numero", aggfunc="first")


def correlacion_entre_posiciones(df: pd.DataFrame) -> pd.DataFrame:
    """Matriz de correlación de Pearson entre las series de cada posición."""
    ancho = pivot_por_posicion(df)
    return ancho.corr()


def autocorrelacion(serie: pd.Series, max_lag: int = 20) -> pd.DataFrame:
    """ACF (Pearson) de una serie temporal univariada, con banda de significancia."""
    x = serie.dropna().to_numpy(dtype=float)
    n = len(x)
    media = x.mean()
    var = ((x - media) ** 2).sum()
    max_lag = min(max_lag, max(n - 2, 0))
    lags = list(range(1, max_lag + 1))
    valores = []
    for lag in lags:
        cov = ((x[:-lag] - media) * (x[lag:] - media)).sum()
        valores.append(float(cov / var) if var else 0.0)
    banda = 1.96 / np.sqrt(n) if n else 0.0
    return pd.DataFrame({
        "lag": lags,
        "acf": valores,
        "banda_significancia": banda,
        "significativo": [abs(v) > banda for v in valores],
    })


def correlacion_cruzada(serie_a: pd.Series, serie_b: pd.Series, max_lag: int = 10) -> pd.DataFrame:
    """Correlación cruzada entre dos series (ej: posición 1 vs posición 11)."""
    a = serie_a.dropna().to_numpy(dtype=float)
    b = serie_b.dropna().to_numpy(dtype=float)
    n = min(len(a), len(b))
    a, b = a[:n], b[:n]
    lags = list(range(-max_lag, max_lag + 1))
    valores = []
    for lag in lags:
        if lag >= 0:
            x, y = a[: n - lag], b[lag:]
        else:
            x, y = a[-lag:], b[: n + lag]
        if len(x) < 2 or x.std() == 0 or y.std() == 0:
            valores.append(0.0)
            continue
        valores.append(float(np.corrcoef(x, y)[0, 1]))
    return pd.DataFrame({"lag": lags, "correlacion": valores})


def tabla_por_dia_semana(df: pd.DataFrame, bins: int = 10) -> pd.DataFrame:
    """Tabla de contingencia día_semana x rango_de_número (para test de dependencia temporal)."""
    dias = df["fecha"].dt.day_name()
    rango = pd.cut(df["numero"], bins=bins, include_lowest=True)
    return pd.crosstab(dias, rango)

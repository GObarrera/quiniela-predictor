"""Simulación Monte Carlo / bootstrap para comparar estrategias contra el
azar puro (Fase 6).

No se pueden generar sorteos reales adicionales sin asumir un modelo (eso
sería circular: "simular" con un modelo y después usar esa simulación para
validar el mismo modelo). En cambio, la validación se hace por *backtesting*
walk-forward sobre el histórico real (en cada paso, el ranking se calcula
solo con datos previos, nunca mirando el futuro) y se usa *bootstrap* — la
técnica de remuestreo estándar para estimar intervalos de confianza — sobre
esa secuencia de aciertos/fallos histórica. Esto es lo que el prompt original
pedía como "Monte Carlo": no se inventan sorteos, se cuantifica la
incertidumbre del historial real mediante remuestreo.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def backtest_top_k(serie: pd.Series, k: int, ventana_min: int = 30, semilla: int = 42) -> dict:
    """Para cada sorteo (desde `ventana_min` en adelante), calcula si el valor
    real cayó dentro de: (a) el top-k por frecuencia histórica hasta ese
    momento (sin mirar el futuro), y (b) un top-k elegido al azar, como
    control. Devuelve las series de aciertos para poder bootstrapear."""
    x = serie.to_numpy(dtype=int)
    n = len(x)
    max_val = int(x.max()) + 1
    rng = np.random.default_rng(semilla)

    aciertos_heuristico = np.zeros(n - ventana_min, dtype=bool)
    aciertos_azar = np.zeros(n - ventana_min, dtype=bool)

    for idx, t in enumerate(range(ventana_min, n)):
        historial = x[:t]
        frecuencia = np.bincount(historial, minlength=max_val)
        top_heuristico = set(np.argsort(frecuencia)[::-1][:k].tolist())
        top_azar = set(rng.choice(max_val, size=k, replace=False).tolist())

        real = int(x[t])
        aciertos_heuristico[idx] = real in top_heuristico
        aciertos_azar[idx] = real in top_azar

    return {
        "n_evaluaciones": int(n - ventana_min),
        "k": k,
        "max_val": max_val,
        "tasa_acierto_heuristico": float(aciertos_heuristico.mean()),
        "tasa_acierto_azar_simulado": float(aciertos_azar.mean()),
        "tasa_acierto_teorica_azar": k / max_val,
        "aciertos_heuristico": aciertos_heuristico,
        "aciertos_azar": aciertos_azar,
    }


def bootstrap_ic_diferencia(
    aciertos_a: np.ndarray,
    aciertos_b: np.ndarray,
    n_resamples: int = 100_000,
    seed: int = 42,
    chunk: int = 2000,
) -> dict:
    """Bootstrap no paramétrico sobre la diferencia de tasas de acierto (a-b),
    remuestreando con reemplazo la secuencia histórica de aciertos/fallos.
    Procesado en lotes para no explotar la memoria con `n_resamples` grande."""
    rng = np.random.default_rng(seed)
    n = len(aciertos_a)
    diffs = np.empty(n_resamples)

    hechas = 0
    while hechas < n_resamples:
        lote = min(chunk, n_resamples - hechas)
        idx = rng.integers(0, n, size=(lote, n))
        diffs[hechas : hechas + lote] = aciertos_a[idx].mean(axis=1) - aciertos_b[idx].mean(axis=1)
        hechas += lote

    ic_bajo, ic_alto = np.percentile(diffs, [2.5, 97.5])
    return {
        "n_resamples": n_resamples,
        "diferencia_media": float(diffs.mean()),
        "ic_95": (float(ic_bajo), float(ic_alto)),
        "significativo": bool(not (ic_bajo <= 0 <= ic_alto)),
    }


def comparar_estrategias(serie: pd.Series, k: int, n_resamples: int = 100_000, ventana_min: int = 30) -> dict:
    """Arma el backtest heurístico-vs-azar y su intervalo de confianza bootstrap."""
    bt = backtest_top_k(serie, k=k, ventana_min=ventana_min)
    ic = bootstrap_ic_diferencia(bt["aciertos_heuristico"], bt["aciertos_azar"], n_resamples=n_resamples)
    return {
        "n_evaluaciones": bt["n_evaluaciones"],
        "k": k,
        "tasa_acierto_heuristico": bt["tasa_acierto_heuristico"],
        "tasa_acierto_azar_simulado": bt["tasa_acierto_azar_simulado"],
        "tasa_acierto_teorica_azar": bt["tasa_acierto_teorica_azar"],
        "bootstrap": ic,
    }

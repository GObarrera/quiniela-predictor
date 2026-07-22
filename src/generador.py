"""Análisis exploratorio de periodicidad y "reproducibilidad" del generador
(Fase 4).

No se simulan generadores específicos (LCG, Mersenne Twister, Xorshift, PCG,
Lagged Fibonacci, Blum Blum Shub) porque eso requeriría asumir semilla y
parámetros arbitrarios — lo cual el enfoque pedido explícitamente evita
("comparación estadística, no fuerza bruta de semillas"). En cambio, se usan
las propiedades que de hecho distinguirían un generador determinista simple
de ruido real — autocorrelación / periodicidad (ACF y espectro de Fourier) —
y se agregan los resultados de todos los tests de aleatoriedad en un score
bayesiano heurístico y transparente.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats

from .dependencias import autocorrelacion


def espectro_fourier(serie: pd.Series, top_k: int = 5) -> pd.DataFrame:
    """Picos dominantes del espectro de potencia (FFT): candidatos a periodicidad."""
    x = serie.dropna().to_numpy(dtype=float)
    n = len(x)
    x = x - x.mean()
    espectro = np.abs(np.fft.rfft(x)) ** 2
    freqs = np.fft.rfftfreq(n)

    # se ignora la componente 0 (nivel medio, no representa periodicidad)
    espectro_sin_dc = espectro[1:]
    freqs_sin_dc = freqs[1:]
    top_k = min(top_k, len(espectro_sin_dc))
    idx = np.argsort(espectro_sin_dc)[::-1][:top_k]

    periodos = np.divide(
        1.0, freqs_sin_dc[idx], out=np.full(len(idx), np.inf), where=freqs_sin_dc[idx] != 0
    )
    total_potencia = espectro_sin_dc.sum()
    return pd.DataFrame({
        "frecuencia": freqs_sin_dc[idx],
        "periodo_en_sorteos": periodos,
        "potencia": espectro_sin_dc[idx],
        "potencia_relativa": espectro_sin_dc[idx] / total_potencia if total_potencia else 0.0,
    })


def deteccion_ciclos(serie: pd.Series, max_lag: int = 50) -> pd.DataFrame:
    """Lags de la ACF que superan la banda de significancia: candidatos a ciclo."""
    acf_df = autocorrelacion(serie, max_lag=max_lag)
    return acf_df[acf_df["significativo"]].reset_index(drop=True)


def score_generador_reproducible(n_tests: int, n_rechazan: int, n_sorteos: int, umbral_muestra: int = 500) -> dict:
    """Score bayesiano heurístico (Beta-Binomial) de "probabilidad de generador
    reproducible", tratando cada test de aleatoriedad rechazado como evidencia
    débil. Esto NO prueba que exista un generador determinista: es una
    agregación simple y transparente de cuánta evidencia hay en conjunto,
    con prior no informativo Beta(1,1)."""
    a_prior, b_prior = 1.0, 1.0
    a_post = a_prior + n_rechazan
    b_post = b_prior + (n_tests - n_rechazan)

    media = a_post / (a_post + b_post)
    ic_bajo, ic_alto = scipy_stats.beta.ppf([0.025, 0.975], a_post, b_post)

    advertencia = None
    if n_sorteos < umbral_muestra:
        advertencia = (
            f"Muestra de {n_sorteos} sorteos por debajo del umbral recomendado "
            f"({umbral_muestra}) para este tipo de análisis: las conclusiones de "
            "esta sección son poco robustas y deben tomarse como preliminares."
        )

    return {
        "n_tests_evaluados": n_tests,
        "n_tests_que_rechazan_h0": n_rechazan,
        "probabilidad_posterior_media": float(media),
        "intervalo_credibilidad_95": (float(ic_bajo), float(ic_alto)),
        "advertencia_muestra": advertencia,
    }

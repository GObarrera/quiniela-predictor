"""Batería de pruebas formales de aleatoriedad e independencia (Fase 3).

Este módulo NO determina si el sorteo es "manipulable" ni descubre ningún
mecanismo. Cada función contrasta una hipótesis nula H0 puntual (uniformidad,
independencia, ausencia de rachas, etc.) y reporta estadístico, p-valor (o
valor crítico tabulado cuando no hay p-valor exacto), nivel de significancia
e interpretación explícita.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats


@dataclass
class ChiSquareResult:
    statistic: float
    p_value: float
    degrees_freedom: int
    alpha: float
    rechaza_h0: bool

    def interpretacion(self) -> str:
        if self.rechaza_h0:
            return (
                f"Se RECHAZA H0 de uniformidad (estadístico={self.statistic:.2f}, "
                f"p={self.p_value:.4f} < alpha={self.alpha}). Hay evidencia estadística de que "
                "la distribución observada no es uniforme en esta muestra. Esto NO implica un "
                "mecanismo determinista ni valor predictivo garantizado: requiere más datos y "
                "pruebas adicionales (Fase 3 completa: Kolmogorov-Smirnov, rachas, entropía, etc.) "
                "antes de sacar conclusiones robustas."
            )
        return (
            f"NO se rechaza H0 de uniformidad (estadístico={self.statistic:.2f}, "
            f"p={self.p_value:.4f} >= alpha={self.alpha}). Los datos son consistentes con un "
            "proceso uniforme/aleatorio. Cualquier ranking de números 'calientes' o 'fríos' que "
            "se muestre es puramente descriptivo, SIN valor predictivo."
        )


def chi_square_uniformity(freq_df: pd.DataFrame, alpha: float = 0.05) -> ChiSquareResult:
    """Chi-cuadrado de bondad de ajuste contra una distribución uniforme."""
    observed = freq_df["frecuencia_absoluta"].to_numpy()
    n = observed.sum()
    k = len(observed)
    expected = n / k
    chi2, p = stats.chisquare(observed, f_exp=[expected] * k)
    return ChiSquareResult(
        statistic=float(chi2),
        p_value=float(p),
        degrees_freedom=k - 1,
        alpha=alpha,
        rechaza_h0=bool(p < alpha),
    )


@dataclass
class ResultadoTest:
    """Resultado genérico de una prueba de hipótesis, para poder consolidar
    muchas pruebas distintas (con o sin p-valor exacto) en un solo resumen."""

    nombre: str
    estadistico: float
    alpha: float
    rechaza_h0: bool
    p_valor: float | None = None
    detalle: str = ""

    def interpretacion(self) -> str:
        p_txt = f"p={self.p_valor:.4f}" if self.p_valor is not None else "sin p-valor exacto (valor crítico tabulado)"
        veredicto = "Se RECHAZA H0" if self.rechaza_h0 else "NO se rechaza H0"
        return f"{self.nombre}: {veredicto} (estadístico={self.estadistico:.4f}, {p_txt}). {self.detalle}"


def chi_square_como_resultado(chi2: ChiSquareResult) -> ResultadoTest:
    return ResultadoTest(
        nombre="Chi-cuadrado (uniformidad)",
        estadistico=chi2.statistic,
        alpha=chi2.alpha,
        rechaza_h0=chi2.rechaza_h0,
        p_valor=chi2.p_value,
        detalle=f"{chi2.degrees_freedom} grados de libertad.",
    )


def kolmogorov_smirnov_uniformidad(numeros: pd.Series, max_numero: int, alpha: float = 0.05) -> ResultadoTest:
    """KS de bondad de ajuste contra una uniforme continua en [0, max_numero+1).
    Aproximación continua sobre datos discretos: orientativa, no exacta."""
    data = numeros.to_numpy(dtype=float)
    stat, p = stats.kstest(data, "uniform", args=(0, max_numero + 1))
    return ResultadoTest(
        nombre="Kolmogorov-Smirnov (uniformidad)",
        estadistico=float(stat),
        alpha=alpha,
        rechaza_h0=bool(p < alpha),
        p_valor=float(p),
        detalle="Aproximación continua sobre datos discretos (orientativa).",
    )


# Valores críticos tabulados de A² para H0 completamente especificada
# (D'Agostino & Stephens, 1986, tabla 4.2 - "case 0").
_CRITICOS_ANDERSON_DARLING = {0.10: 1.933, 0.05: 2.492, 0.025: 3.070, 0.01: 3.878}


def anderson_darling_uniformidad(numeros: pd.Series, max_numero: int, alpha: float = 0.05) -> ResultadoTest:
    """Anderson-Darling de bondad de ajuste contra uniforme, con corrección de
    continuidad. Sin implementación nativa en scipy para 'uniform': se calcula
    el estadístico A² manualmente y se compara contra el valor crítico tabulado
    (no hay p-valor exacto)."""
    n = len(numeros)
    u = np.sort((numeros.to_numpy(dtype=float) + 0.5) / (max_numero + 1))
    u = np.clip(u, 1e-12, 1 - 1e-12)
    i = np.arange(1, n + 1)
    s = np.sum((2 * i - 1) * (np.log(u) + np.log(1 - u[::-1])))
    a2 = -n - s / n
    critico = _CRITICOS_ANDERSON_DARLING.get(alpha, _CRITICOS_ANDERSON_DARLING[0.05])
    return ResultadoTest(
        nombre="Anderson-Darling (uniformidad)",
        estadistico=float(a2),
        alpha=alpha,
        rechaza_h0=bool(a2 > critico),
        p_valor=None,
        detalle=f"Comparado contra valor crítico tabulado {critico} (D'Agostino & Stephens 1986).",
    )


def test_de_rachas(numeros: pd.Series, alpha: float = 0.05) -> ResultadoTest:
    """Wald-Wolfowitz: rachas por encima/debajo de la mediana."""
    x = numeros.to_numpy(dtype=float)
    mediana = np.median(x)
    signos = x >= mediana
    n1 = int(signos.sum())
    n2 = int((~signos).sum())
    n = n1 + n2
    rachas = 1 + int(np.sum(signos[1:] != signos[:-1]))
    media_esperada = 2 * n1 * n2 / n + 1
    var_esperada = (2 * n1 * n2 * (2 * n1 * n2 - n)) / (n**2 * (n - 1)) if n > 1 else 0.0
    if var_esperada <= 0:
        z, p = 0.0, 1.0
    else:
        z = (rachas - media_esperada) / np.sqrt(var_esperada)
        p = float(2 * (1 - stats.norm.cdf(abs(z))))
    return ResultadoTest(
        nombre="Wald-Wolfowitz (rachas)",
        estadistico=float(z),
        alpha=alpha,
        rechaza_h0=bool(p < alpha),
        p_valor=p,
        detalle=f"{rachas} rachas observadas sobre {n} valores (esperadas ~{media_esperada:.1f}).",
    )


def entropia_shannon(freq_df: pd.DataFrame) -> dict:
    """Entropía de Shannon de la distribución de frecuencias, normalizada
    contra la entropía máxima posible (distribución uniforme)."""
    p = freq_df["frecuencia_relativa"].to_numpy()
    p = p[p > 0]
    h = float(-(p * np.log2(p)).sum())
    h_max = float(np.log2(len(freq_df)))
    return {
        "entropia_bits": h,
        "entropia_maxima_bits": h_max,
        "eficiencia": h / h_max if h_max else 0.0,
    }


def entropia_condicional(numeros: pd.Series, k: int) -> dict:
    """H(X_t | X_(t-1)) vía la matriz de transición empírica sobre `numeros`
    (rango 0..k-1). Une el concepto de entropía con el de cadena de Markov."""
    x = numeros.to_numpy(dtype=int)
    matriz = np.zeros((k, k))
    for a, b in zip(x[:-1], x[1:]):
        matriz[a, b] += 1
    total = matriz.sum()
    if total == 0:
        return {"entropia_condicional_bits": 0.0, "entropia_marginal_bits": 0.0, "reduccion_incertidumbre_bits": 0.0}

    p_conjunta = matriz / total
    p_previo = p_conjunta.sum(axis=1)

    h_cond = 0.0
    filas, cols = np.nonzero(p_conjunta)
    for i, j in zip(filas, cols):
        pij = p_conjunta[i, j]
        h_cond -= pij * np.log2(pij / p_previo[i])

    p_marg = p_conjunta.sum(axis=0)
    p_marg = p_marg[p_marg > 0]
    h_marg = float(-(p_marg * np.log2(p_marg)).sum())

    n_muestras = len(x) - 1
    n_celdas = k * k
    advertencia = None
    if n_muestras < 5 * n_celdas:
        advertencia = (
            f"Tabla conjunta de {n_celdas} celdas con solo {n_muestras} transiciones observadas: "
            "la mayoría de las celdas tiene 0 o 1 observaciones. La entropía condicional empírica "
            "está sesgada hacia abajo en este régimen (subestima la incertidumbre real) y NO debe "
            "interpretarse como evidencia de dependencia. Usar el test de independencia (chi-cuadrado "
            "sobre bins) para esa conclusión, no este número."
        )

    return {
        "entropia_condicional_bits": float(h_cond),
        "entropia_marginal_bits": h_marg,
        "reduccion_incertidumbre_bits": h_marg - float(h_cond),
        "advertencia_sesgo_muestra": advertencia,
    }


def test_independencia(numeros: pd.Series, bins: int = 10, alpha: float = 0.05) -> ResultadoTest:
    """Chi-cuadrado de independencia entre valores consecutivos (X_t vs X_t-1),
    sobre `bins` categorías de igual ancho (evita tablas de contingencia
    demasiado dispersas para el tamaño de muestra disponible)."""
    codigos = pd.cut(numeros, bins=bins, labels=False, include_lowest=True).to_numpy()
    matriz = np.zeros((bins, bins))
    for a, b in zip(codigos[:-1], codigos[1:]):
        if np.isnan(a) or np.isnan(b):
            continue
        matriz[int(a), int(b)] += 1
    chi2, p, dof, expected = stats.chi2_contingency(matriz)
    freq_min_esperada = float(expected.min())
    valida = freq_min_esperada >= 5
    return ResultadoTest(
        nombre="Test de independencia (X_t vs X_t-1)",
        estadistico=float(chi2),
        alpha=alpha,
        rechaza_h0=bool(p < alpha),
        p_valor=float(p),
        detalle=(
            f"Tabla {bins}x{bins}, {dof} gl, frecuencia esperada mínima {freq_min_esperada:.1f} "
            f"({'válida' if valida else 'ADVERTENCIA: por debajo de 5, resultado poco confiable'})."
        ),
    )


def correccion_benjamini_hochberg(resultados: list[ResultadoTest], alpha: float = 0.05) -> dict:
    """Corrección de Benjamini-Hochberg (control de FDR) sobre los p-valores
    disponibles. Al correr varios tests independientes, es esperable que
    alguno cruce p<alpha por puro azar (con 5 tests al 5%, ~23% de chance de
    al menos un falso positivo); esta corrección evita confundir ruido con
    evidencia real antes de decidir si avanzar a la Fase 5."""
    con_p = [r for r in resultados if r.p_valor is not None]
    m = len(con_p)
    if m == 0:
        return {"n_significativos_bh": 0, "detalle": []}

    orden = sorted(range(m), key=lambda i: con_p[i].p_valor)

    k_max = 0
    for rank, i in enumerate(orden, start=1):
        if con_p[i].p_valor <= (rank / m) * alpha:
            k_max = rank

    significativos_bh = set(orden[:k_max])

    detalle = [
        {
            "nombre": con_p[i].nombre,
            "p_valor": con_p[i].p_valor,
            "umbral_bh": ((rank + 1) / m) * alpha,
            "significativo_bh": i in significativos_bh,
        }
        for rank, i in enumerate(orden)
    ]

    return {"n_significativos_bh": len(significativos_bh), "detalle": detalle}


def resumen_consolidado(resultados: list[ResultadoTest], alpha: float = 0.05) -> dict:
    """Combina los p-valores de todos los tests independientes vía el método
    de Fisher, para dar un veredicto consolidado único."""
    p_validos = [r.p_valor for r in resultados if r.p_valor is not None]
    n_rechazan = sum(1 for r in resultados if r.rechaza_h0)

    if len(p_validos) >= 2:
        combinado = stats.combine_pvalues(p_validos, method="fisher")
        estadistico_fisher = float(combinado.statistic)
        p_fisher = float(combinado.pvalue)
    else:
        estadistico_fisher, p_fisher = float("nan"), float("nan")

    return {
        "n_tests": len(resultados),
        "n_tests_con_p_valor": len(p_validos),
        "n_rechazan_h0": n_rechazan,
        "estadistico_fisher": estadistico_fisher,
        "p_valor_combinado_fisher": p_fisher,
        "veredicto": (
            "Se rechaza H0 de aleatoriedad de forma consolidada (método de Fisher)"
            if (p_fisher == p_fisher and p_fisher < alpha)  # descarta NaN
            else "No se rechaza H0 de aleatoriedad de forma consolidada (método de Fisher)"
        ),
    }

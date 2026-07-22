"""Modelos de ML y cadena de Markov, como detectores de señal (Fase 5).

Solo se entrenan si la Fase 3/4 mostró señal estadísticamente significativa
(p < 0.05 en más de un test independiente) — tal como pedía el prompt
original. Si no, se documenta explícitamente que se omite el entrenamiento en
vez de forzar un resultado.

Se usa RandomForest (scikit-learn) como detector de señal representativo en
vez de sumar XGBoost/LightGBM/HMM: dado que este paso está condicionado a que
haya señal real (algo que, con datos genuinamente aleatorios, no debería
ocurrir), agregar más librerías de ML no cambia la conclusión y sí agrega
dependencias pesadas. Si en el futuro el gate se activa y se quiere comparar
más modelos, se puede extender este módulo.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, log_loss
from sklearn.model_selection import TimeSeriesSplit


def hay_senal_significativa(n_significativos_bh: int) -> tuple[bool, str]:
    """Gate del prompt original: solo avanzar con ML si más de un test
    independiente sigue siendo significativo DESPUÉS de corregir por
    comparaciones múltiples (Benjamini-Hochberg) — no el conteo crudo de
    p<0.05, que sobre-dispara por ruido al correr varios tests a la vez."""
    if n_significativos_bh > 1:
        return True, (
            f"{n_significativos_bh} tests siguen siendo significativos tras la corrección de "
            "Benjamini-Hochberg (FDR): se procede con Fase 5."
        )
    return False, (
        f"Solo {n_significativos_bh} test(s) siguen siendo significativos tras corregir por "
        "comparaciones múltiples (se requiere más de 1). No corresponde entrenar modelos de ML: "
        "hacerlo forzaría una señal que los datos no muestran de forma robusta. Esta sección se "
        "documenta como OMITIDA de forma explícita, en vez de mostrar un resultado forzado."
    )


def matriz_transicion_markov(serie: pd.Series, k: int) -> np.ndarray:
    """Matriz de transición empírica de orden 1 (cadena de Markov) entre
    valores consecutivos de `serie`, en el rango 0..k-1."""
    x = serie.to_numpy(dtype=int)
    conteo = np.zeros((k, k))
    for a, b in zip(x[:-1], x[1:]):
        conteo[a, b] += 1
    filas_sum = conteo.sum(axis=1, keepdims=True)
    return np.divide(conteo, filas_sum, out=np.zeros_like(conteo), where=filas_sum != 0)


def distancia_markov_a_uniforme(matriz_transicion: np.ndarray) -> float:
    """Distancia L1 media entre cada fila de la matriz de transición y la fila
    uniforme esperada bajo independencia total (sin memoria). 0 = coincide con
    independencia perfecta; valores más altos indican mayor 'memoria' aparente."""
    k = matriz_transicion.shape[0]
    uniforme = np.full(k, 1.0 / k)
    filas_no_vacias = matriz_transicion[matriz_transicion.sum(axis=1) > 0]
    if len(filas_no_vacias) == 0:
        return 0.0
    distancias = np.abs(filas_no_vacias - uniforme).sum(axis=1) / 2
    return float(distancias.mean())


def _features_lag(serie: pd.Series, n_lags: int) -> pd.DataFrame:
    datos = pd.DataFrame({"y": serie.to_numpy()})
    for lag in range(1, n_lags + 1):
        datos[f"lag_{lag}"] = datos["y"].shift(lag)
    return datos.dropna().reset_index(drop=True)


def _proba_alineada(modelo, X, clases_totales: list[int]) -> np.ndarray:
    proba_raw = modelo.predict_proba(X)
    proba = np.zeros((len(X), len(clases_totales)))
    idx_map = {c: i for i, c in enumerate(clases_totales)}
    for j, c in enumerate(modelo.classes_):
        proba[:, idx_map[c]] = proba_raw[:, j]
    return proba


def _brier_multiclase(y_true: np.ndarray, proba: np.ndarray, clases_totales: list[int]) -> float:
    idx_map = {c: i for i, c in enumerate(clases_totales)}
    y_onehot = np.zeros_like(proba)
    for fila, val in enumerate(y_true):
        y_onehot[fila, idx_map[int(val)]] = 1
    return float(np.mean(np.sum((proba - y_onehot) ** 2, axis=1)))


def entrenar_random_forest_vs_baseline(serie: pd.Series, k: int, n_lags: int = 5, n_splits: int = 5) -> dict:
    """RandomForest como detector de señal (predice la próxima categoría a
    partir de las últimas `n_lags`), comparado contra un baseline dummy, con
    validación cruzada temporal (TimeSeriesSplit, respeta el orden temporal)."""
    datos = _features_lag(serie, n_lags)
    X = datos.drop(columns="y")
    y = datos["y"].astype(int)
    clases_totales = list(range(k))

    tscv = TimeSeriesSplit(n_splits=n_splits)
    acc_modelo, ll_modelo, brier_modelo = [], [], []
    acc_base, ll_base, brier_base = [], [], []

    for train_idx, test_idx in tscv.split(X):
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
        y_test_np = y_test.to_numpy()

        modelo = RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1)
        modelo.fit(X_train, y_train)
        proba = _proba_alineada(modelo, X_test, clases_totales)
        acc_modelo.append(accuracy_score(y_test, modelo.predict(X_test)))
        ll_modelo.append(log_loss(y_test_np, proba, labels=clases_totales))
        brier_modelo.append(_brier_multiclase(y_test_np, proba, clases_totales))

        base = DummyClassifier(strategy="uniform", random_state=42)
        base.fit(X_train, y_train)
        proba_b = _proba_alineada(base, X_test, clases_totales)
        acc_base.append(accuracy_score(y_test, base.predict(X_test)))
        ll_base.append(log_loss(y_test_np, proba_b, labels=clases_totales))
        brier_base.append(_brier_multiclase(y_test_np, proba_b, clases_totales))

    return {
        "n_clases": k,
        "n_lags": n_lags,
        "n_splits": n_splits,
        "modelo": {
            "accuracy_media": float(np.mean(acc_modelo)),
            "log_loss_media": float(np.mean(ll_modelo)),
            "brier_media": float(np.mean(brier_modelo)),
        },
        "baseline_uniforme": {
            "accuracy_media": float(np.mean(acc_base)),
            "log_loss_media": float(np.mean(ll_base)),
            "brier_media": float(np.mean(brier_base)),
        },
        "supera_baseline_accuracy": float(np.mean(acc_modelo)) > float(np.mean(acc_base)),
        "supera_baseline_log_loss": float(np.mean(ll_modelo)) < float(np.mean(ll_base)),
    }

"""Distribuciones descriptivas adicionales (Fase 2): decenas, paridad,
altos/bajos y distribución modular."""
from __future__ import annotations

import pandas as pd


def por_decenas(df: pd.DataFrame, max_numero: int, ancho: int = 10) -> pd.DataFrame:
    """Agrupa los números en buckets de `ancho` (decenas por defecto)."""
    total = len(df)
    bucket = (df["numero"] // ancho) * ancho
    conteo = bucket.value_counts()

    max_bucket = (max_numero // ancho) * ancho
    inicios = list(range(0, max_bucket + ancho, ancho))
    out = pd.DataFrame({"bucket_inicio": inicios})
    out["bucket_fin"] = out["bucket_inicio"] + ancho - 1
    out["frecuencia_absoluta"] = out["bucket_inicio"].map(conteo).fillna(0).astype(int)
    out["frecuencia_relativa"] = out["frecuencia_absoluta"] / total if total else 0.0
    return out


def pares_impares(df: pd.DataFrame) -> pd.DataFrame:
    es_par = df["numero"] % 2 == 0
    total = len(df)
    return pd.DataFrame({
        "categoria": ["par", "impar"],
        "frecuencia_absoluta": [int(es_par.sum()), int((~es_par).sum())],
        "frecuencia_relativa": [float(es_par.mean()), float((~es_par).mean())] if total else [0.0, 0.0],
    })


def altos_bajos(df: pd.DataFrame, max_numero: int) -> pd.DataFrame:
    punto_medio = (max_numero + 1) / 2
    es_bajo = df["numero"] < punto_medio
    total = len(df)
    return pd.DataFrame({
        "categoria": ["bajo", "alto"],
        "frecuencia_absoluta": [int(es_bajo.sum()), int((~es_bajo).sum())],
        "frecuencia_relativa": [float(es_bajo.mean()), float((~es_bajo).mean())] if total else [0.0, 0.0],
    })


def distribucion_modular(df: pd.DataFrame, k: int) -> pd.DataFrame:
    """Frecuencia de numero % k, para detectar sesgos periódicos de período k."""
    total = len(df)
    resto = df["numero"] % k
    conteo = resto.value_counts().reindex(range(k), fill_value=0).sort_index()
    return pd.DataFrame({
        "resto": conteo.index,
        "frecuencia_absoluta": conteo.to_numpy(),
        "frecuencia_relativa": (conteo / total).to_numpy() if total else conteo.to_numpy().astype(float),
    })

"""Carga y validación de datos históricos de Quiniela Plus desde CSV."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS = ["fecha", "numero"]
OPTIONAL_COLUMNS = {"turno": "unico", "loteria": "unica", "posicion": "1"}


@dataclass
class LoadResult:
    df: pd.DataFrame
    warnings: list[str] = field(default_factory=list)


def load_csv(path: str | Path, digits: int = 4, max_numero: int = 9999) -> LoadResult:
    """Carga el CSV de sorteos, valida su esquema y limpia inconsistencias.

    Columnas esperadas: fecha, numero (obligatorias); turno, loteria, posicion (opcionales).
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"No se encontró el archivo CSV en '{path}'.\n"
            f"Creá el archivo con columnas: {', '.join(REQUIRED_COLUMNS)} "
            f"(+ opcionales: {', '.join(OPTIONAL_COLUMNS)}).\n"
            "Ejemplo de fila: 2026-01-05,Nocturna,Nacional,1,4821"
        )

    df = pd.read_csv(path, dtype=str)
    warnings: list[str] = []

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas obligatorias en el CSV: {missing}")

    for col, default in OPTIONAL_COLUMNS.items():
        if col not in df.columns:
            df[col] = default
            warnings.append(f"Columna '{col}' no encontrada, se usó el valor por defecto '{default}'.")

    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    bad_fecha = int(df["fecha"].isna().sum())
    if bad_fecha:
        warnings.append(f"{bad_fecha} fila(s) con fecha inválida fueron descartadas.")
    df = df.dropna(subset=["fecha"])

    df["numero_raw"] = df["numero"].astype(str).str.strip()
    df["numero"] = pd.to_numeric(df["numero_raw"], errors="coerce")
    bad_numero = int(df["numero"].isna().sum())
    if bad_numero:
        warnings.append(f"{bad_numero} fila(s) con número inválido fueron descartadas.")
    df = df.dropna(subset=["numero"])
    df["numero"] = df["numero"].astype(int)

    posicion_numerica = pd.to_numeric(df["posicion"], errors="coerce")
    df["posicion"] = posicion_numerica.fillna(-1).astype(int)

    out_of_range = int(((df["numero"] < 0) | (df["numero"] > max_numero)).sum())
    if out_of_range:
        warnings.append(
            f"{out_of_range} fila(s) con número fuera de rango [0, {max_numero}] fueron descartadas."
        )
    df = df[(df["numero"] >= 0) & (df["numero"] <= max_numero)]

    before = len(df)
    df = df.drop_duplicates(subset=["fecha", "turno", "loteria", "posicion", "numero"])
    dup = before - len(df)
    if dup:
        warnings.append(f"{dup} fila(s) duplicada(s) fueron eliminadas.")

    df = df.sort_values("fecha").reset_index(drop=True)
    df["numero_fmt"] = df["numero"].apply(lambda n: str(n).zfill(digits))

    if df.empty:
        raise ValueError("El CSV no contiene datos válidos después de la limpieza.")

    return LoadResult(df=df, warnings=warnings)

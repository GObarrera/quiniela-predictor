"""Ensambla el reporte de consola y el reporte guardado en reports/."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from .randomness import ChiSquareResult


def build_report(
    *,
    total_sorteos: int,
    rango: tuple[int, int],
    chi2: ChiSquareResult,
    hot_cold_tables: dict[str, pd.DataFrame],
    ranking: pd.DataFrame,
    top_n: int,
    warnings: list[str],
    digits: int,
) -> str:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines: list[str] = []
    lines.append(f"# Reporte Quiniela Plus — {ts}\n")
    lines.append(f"Sorteos analizados: {total_sorteos}  |  Rango de números: {rango[0]}-{rango[1]}\n")

    if warnings:
        lines.append("## Advertencias de carga de datos")
        for w in warnings:
            lines.append(f"- {w}")
        lines.append("")

    lines.append("## Prueba de aleatoriedad (Chi-cuadrado de uniformidad)")
    lines.append(f"- Estadístico: {chi2.statistic:.4f}")
    lines.append(f"- Grados de libertad: {chi2.degrees_freedom}")
    lines.append(f"- p-valor: {chi2.p_value:.4f}")
    lines.append(f"- Nivel de significancia (alpha): {chi2.alpha}")
    lines.append(f"- Interpretación: {chi2.interpretacion()}")
    lines.append("")

    lines.append(f"## Top {top_n} números 'calientes' (mayor frecuencia histórica)")
    lines.append(_df_to_md(hot_cold_tables["calientes"], digits))
    lines.append("")

    lines.append(f"## Top {top_n} números 'fríos' (mayor ausencia actual)")
    lines.append(_df_to_md(hot_cold_tables["frios"], digits))
    lines.append("")

    lines.append(f"## Ranking heurístico combinado (top {top_n})")
    lines.append(
        "Combina frecuencia histórica, frecuencia reciente y ausencia. "
        "**No es una predicción garantizada** — ver interpretación de la prueba de aleatoriedad arriba."
    )
    lines.append(_df_to_md(ranking.head(top_n), digits))
    lines.append("")

    lines.append("## Conclusión")
    if chi2.rechaza_h0:
        lines.append(
            "Se detectó una desviación estadísticamente significativa respecto a la uniformidad "
            "en esta muestra. Esto amerita investigar con más pruebas (Fase 3 completa) antes de "
            "sacar cualquier conclusión. NO implica que el ranking anterior sea confiable para apostar."
        )
    else:
        lines.append(
            "Los datos analizados son consistentes con un proceso aleatorio uniforme. El ranking "
            "de números 'calientes/fríos' se ofrece solo con fines descriptivos y NO tiene "
            "valor predictivo demostrado."
        )

    return "\n".join(lines)


def _df_to_md(df: pd.DataFrame, digits: int) -> str:
    df = df.copy()
    if "numero" in df.columns:
        df["numero"] = df["numero"].apply(lambda n: str(int(n)).zfill(digits))
    return df.to_string(index=False)


def save_report(content: str, reports_dir: str | Path) -> Path:
    reports_dir = Path(reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = reports_dir / f"reporte_{ts}.md"
    out_path.write_text(content, encoding="utf-8")
    return out_path

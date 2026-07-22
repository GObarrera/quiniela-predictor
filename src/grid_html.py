"""Genera una página HTML con tres grillas separadas de terminaciones
(últimos 2 dígitos): calientes, frías y predicción — cada una mostrando
solo los números que corresponden a esa categoría."""
from __future__ import annotations

from datetime import datetime

import pandas as pd


def _grilla_seccion(titulo: str, descripcion: str, celdas_html: str, clase_color: str) -> str:
    return f"""
    <section class="bloque">
        <h2 class="{clase_color}">{titulo}</h2>
        <div class="descripcion">{descripcion}</div>
        <div class="grilla">
            {celdas_html}
        </div>
    </section>"""


def _celda(numero: int, etiqueta: str, valor) -> str:
    return f"""
        <div class="celda">
            <div class="numero">{numero:02d}</div>
            <div class="valor">{etiqueta}: {valor}</div>
        </div>"""


def build_grid_html(
    freq_df: pd.DataFrame,
    hot_cold: dict[str, pd.DataFrame],
    ranking: pd.DataFrame,
    top_n: int,
    total_sorteos: int,
) -> str:
    calientes_df = hot_cold["calientes"].head(top_n)
    frios_df = hot_cold["frios"].head(top_n)
    prediccion_df = ranking.head(top_n)

    celdas_calientes = "".join(
        _celda(int(row.numero), "veces", int(row.frecuencia_absoluta)) for row in calientes_df.itertuples()
    )
    celdas_frias = "".join(
        _celda(int(row.numero), "sorteos sin salir", int(row.ausencia_actual)) for row in frios_df.itertuples()
    )
    celdas_prediccion = "".join(
        _celda(int(row.numero), "score", round(row.score, 3)) for row in prediccion_df.itertuples()
    )

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Quiniela — Terminaciones por categoría</title>
<style>
    body {{
        font-family: Segoe UI, Arial, sans-serif;
        background: #f4f4f6;
        color: #222;
        margin: 0;
        padding: 24px;
    }}
    h1 {{ font-size: 20px; margin-bottom: 4px; }}
    .subtitulo {{ color: #555; margin-bottom: 20px; font-size: 13px; }}
    .aviso {{
        background: #fff3cd;
        border: 1px solid #ffe08a;
        border-radius: 8px;
        padding: 10px 14px;
        margin-bottom: 24px;
        font-size: 13px;
        max-width: 760px;
    }}
    .bloque {{ margin-bottom: 28px; }}
    .bloque h2 {{ font-size: 16px; margin-bottom: 2px; }}
    .bloque h2.caliente {{ color: #c0392b; }}
    .bloque h2.frio {{ color: #2166ac; }}
    .bloque h2.prediccion {{ color: #b8860b; }}
    .descripcion {{ font-size: 12px; color: #555; margin-bottom: 10px; }}
    .grilla {{
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        max-width: 760px;
    }}
    .celda {{
        border-radius: 8px;
        border: 2px solid #ddd;
        width: 84px;
        height: 64px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        background: #fff;
    }}
    .bloque:nth-of-type(1) .celda {{ border-color: #f1948a; background: #fdedec; }}
    .bloque:nth-of-type(2) .celda {{ border-color: #85c1e9; background: #eaf2f8; }}
    .bloque:nth-of-type(3) .celda {{ border-color: #f0c419; background: #fef9e7; }}
    .celda .numero {{ font-size: 20px; font-weight: 700; }}
    .celda .valor {{ font-size: 10px; color: #444; text-align: center; }}
</style>
</head>
<body>
    <h1>Terminaciones (últimos 2 dígitos) — Quiniela Nocturna Provincia</h1>
    <div class="subtitulo">Generado {ts} · {total_sorteos} sorteos analizados</div>
    <div class="aviso">
        Estas grillas son <strong>puramente descriptivas</strong>. Ninguna de las tres
        categorías garantiza resultados futuros — ver el reporte de texto para el
        resultado de la prueba de aleatoriedad (chi-cuadrado) antes de sacar conclusiones.
    </div>
    {_grilla_seccion(
        f"&#128293; Calientes (top {top_n} por frecuencia histórica)",
        "Terminaciones que más veces salieron en el histórico analizado.",
        celdas_calientes,
        "caliente",
    )}
    {_grilla_seccion(
        f"&#10052; Frías (top {top_n} por mayor ausencia)",
        "Terminaciones que hace más sorteos que no salen.",
        celdas_frias,
        "frio",
    )}
    {_grilla_seccion(
        f"&#11088; Predicción (top {top_n} del ranking heurístico)",
        "Combina frecuencia histórica, frecuencia reciente y ausencia. No es una predicción garantizada.",
        celdas_prediccion,
        "prediccion",
    )}
</body>
</html>
"""

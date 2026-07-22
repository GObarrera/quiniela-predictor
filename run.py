"""Motor de análisis / ranking heurístico de Quiniela Plus.

Uso:
    python run.py --csv data/sorteos.csv
    python run.py --csv data/sorteos.csv --top 15 --ventana 100 --digitos 4 --max-numero 9999

Este script NO predice números ganadores con certeza. Aplica estadística
descriptiva y una prueba de aleatoriedad (chi-cuadrado) y, si corresponde,
deja explícito que cualquier ranking es puramente descriptivo.
"""
from __future__ import annotations

import argparse
import sys
import webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.loader import load_csv
from src.stats import frequency_table, moving_frequency, gaps, hot_cold
from src.randomness import chi_square_uniformity
from src.predictor import score_numeros
from src.report import build_report, save_report
from src.terminaciones import dataframe_terminaciones
from src.grid_html import build_grid_html
from src.config import REPORTS_DIR_DEFAULT


def main() -> None:
    parser = argparse.ArgumentParser(description="Motor de análisis de Quiniela Plus")
    parser.add_argument("--csv", default="data/sorteos.csv", help="Ruta al CSV de sorteos históricos")
    parser.add_argument("--top", type=int, default=10, help="Cantidad de números a mostrar en los rankings")
    parser.add_argument("--ventana", type=int, default=50, help="Cantidad de sorteos recientes para la frecuencia móvil")
    parser.add_argument("--digitos", type=int, default=4, help="Cantidad de dígitos para formatear el número (ej: 4 -> 0912)")
    parser.add_argument("--max-numero", type=int, default=9999, help="Valor máximo posible del número sorteado")
    parser.add_argument("--alpha", type=float, default=0.05, help="Nivel de significancia para la prueba de aleatoriedad")
    parser.add_argument("--reports-dir", default=REPORTS_DIR_DEFAULT, help="Carpeta donde guardar el reporte generado (default: carpeta OneDrive sincronizada)")
    parser.add_argument("--sin-grilla", action="store_true", help="No generar ni abrir la grilla HTML de terminaciones")
    args, _ = parser.parse_known_args()

    try:
        result = load_csv(args.csv, digits=args.digitos, max_numero=args.max_numero)
    except (FileNotFoundError, ValueError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    df = result.df
    for w in result.warnings:
        print(f"AVISO: {w}")

    ventana = min(args.ventana, len(df))

    freq_total = frequency_table(df, args.max_numero)
    freq_reciente = moving_frequency(df, ventana, args.max_numero)
    gaps_df = gaps(df, args.max_numero)
    hc = hot_cold(freq_total, gaps_df, args.top)
    chi2 = chi_square_uniformity(freq_total, alpha=args.alpha)
    ranking = score_numeros(freq_total, freq_reciente, gaps_df)

    report = build_report(
        total_sorteos=len(df),
        rango=(0, args.max_numero),
        chi2=chi2,
        hot_cold_tables=hc,
        ranking=ranking,
        top_n=args.top,
        warnings=result.warnings,
        digits=args.digitos,
    )

    print("\n" + report)
    out_path = save_report(report, args.reports_dir)
    print(f"\nReporte guardado en: {out_path}")

    if not args.sin_grilla:
        df_term = dataframe_terminaciones(df)
        freq_term = frequency_table(df_term, 99)
        freq_term_reciente = moving_frequency(df_term, ventana, 99)
        gaps_term = gaps(df_term, 99)
        hc_term = hot_cold(freq_term, gaps_term, args.top)
        ranking_term = score_numeros(freq_term, freq_term_reciente, gaps_term)

        grilla_html = build_grid_html(
            freq_df=freq_term,
            hot_cold=hc_term,
            ranking=ranking_term,
            top_n=args.top,
            total_sorteos=len(df),
        )
        grilla_path = Path(args.reports_dir) / "grilla_terminaciones.html"
        grilla_path.parent.mkdir(parents=True, exist_ok=True)
        grilla_path.write_text(grilla_html, encoding="utf-8")
        print(f"Grilla de terminaciones: {grilla_path}")
        try:
            webbrowser.open(grilla_path.resolve().as_uri())
        except Exception:
            pass  # sin navegador disponible (ej: corriendo en CI/servidor) -> el archivo ya quedo guardado


if __name__ == "__main__":
    main()

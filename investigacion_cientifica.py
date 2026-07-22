"""Investigación científica completa (Fases 2 a 6 y 8 del protocolo original)
sobre el histórico de Quiniela Nocturna Provincia. Corre sobre data/sorteos.csv
(el mismo CSV que actualiza el descargador diario).

El análisis de dependencia/independencia y los modelos de ML se hacen sobre
las TERMINACIONES (últimos 2 dígitos, 00-99) y no sobre el número completo
(0-9999): con ~6000 sorteos, una tabla de contingencia de 10000x10000 quedaría
demasiado dispersa para que estos métodos sean válidos. El reporte rápido
diario (run.py, con la grilla visual) sigue mostrando el número completo.

Uso:
    python investigacion_cientifica.py
    python investigacion_cientifica.py --csv data/sorteos.csv --top 8 --n-resamples 100000
"""
from __future__ import annotations

import argparse
import sys
import webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.loader import load_csv
from src.terminaciones import dataframe_terminaciones
from src.stats import frequency_table
from src.distribuciones import pares_impares, altos_bajos
from src.randomness import (
    chi_square_uniformity,
    chi_square_como_resultado,
    kolmogorov_smirnov_uniformidad,
    anderson_darling_uniformidad,
    test_de_rachas,
    entropia_shannon,
    entropia_condicional,
    test_independencia,
    resumen_consolidado,
    correccion_benjamini_hochberg,
)
from src.generador import espectro_fourier, deteccion_ciclos, score_generador_reproducible
from src.modelos_ml import (
    hay_senal_significativa,
    matriz_transicion_markov,
    distancia_markov_a_uniforme,
    entrenar_random_forest_vs_baseline,
)
from src.montecarlo import comparar_estrategias
from src.reporte_cientifico import generar_reporte_cientifico, guardar_markdown, guardar_pdf
from src.config import REPORTS_DIR_DEFAULT


def main() -> None:
    parser = argparse.ArgumentParser(description="Investigación científica completa de Quiniela Nocturna Provincia")
    parser.add_argument("--csv", default="data/sorteos.csv")
    parser.add_argument("--top", type=int, default=8, help="k usado en el backtest Monte Carlo (top-k)")
    parser.add_argument("--alpha", type=float, default=0.05)
    parser.add_argument("--n-resamples", type=int, default=100_000, help="remuestreos bootstrap (Fase 6)")
    parser.add_argument("--reports-dir", default=REPORTS_DIR_DEFAULT, help="Carpeta donde guardar el reporte (default: carpeta OneDrive sincronizada)")
    parser.add_argument("--sin-abrir", action="store_true", help="No abrir el PDF automáticamente al terminar")
    args, _ = parser.parse_known_args()

    try:
        result = load_csv(args.csv, digits=4, max_numero=9999)
    except (FileNotFoundError, ValueError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    df = result.df
    for w in result.warnings:
        print(f"AVISO: {w}")

    df_term = dataframe_terminaciones(df)
    numeros_term = df_term["numero"]

    print(f"Analizando {len(df)} sorteos ({df['fecha'].min().date()} a {df['fecha'].max().date()})...")
    print(
        "Nota de método: los tests de dependencia y los modelos de ML se corren sobre "
        "terminaciones (00-99), no sobre el número completo (0-9999) -- ver encabezado del script.\n"
    )

    # ---- Fase 2: descriptiva adicional ----
    freq_term = frequency_table(df_term, 99)
    pi = pares_impares(df)
    ab = altos_bajos(df, 9999)

    # ---- Fase 3: batería de aleatoriedad ----
    chi2 = chi_square_uniformity(freq_term, alpha=args.alpha)
    resultados_fase3 = [
        chi_square_como_resultado(chi2),
        kolmogorov_smirnov_uniformidad(numeros_term, 99, alpha=args.alpha),
        anderson_darling_uniformidad(numeros_term, 99, alpha=args.alpha),
        test_de_rachas(numeros_term, alpha=args.alpha),
        test_independencia(numeros_term, bins=10, alpha=args.alpha),
    ]
    fisher = resumen_consolidado(resultados_fase3, alpha=args.alpha)
    bh = correccion_benjamini_hochberg(resultados_fase3, alpha=args.alpha)

    entropia = entropia_shannon(freq_term)
    entropia_cond = entropia_condicional(numeros_term, 100)

    # ---- Fase 4: generador / periodicidad (exploratorio) ----
    espectro = espectro_fourier(numeros_term, top_k=5)
    max_lag_ciclos = min(50, len(numeros_term) // 2)
    ciclos = deteccion_ciclos(numeros_term, max_lag=max_lag_ciclos)
    score_gen = score_generador_reproducible(
        n_tests=len(resultados_fase3), n_rechazan=bh["n_significativos_bh"], n_sorteos=len(df)
    )

    # ---- Fase 5: ML condicional + cadena de Markov ----
    gate, motivo = hay_senal_significativa(bh["n_significativos_bh"])
    matriz_markov = matriz_transicion_markov(numeros_term, 100)
    distancia_markov = distancia_markov_a_uniforme(matriz_markov)

    resultado_ml = None
    if gate:
        print("Señal significativa detectada tras corrección: entrenando RandomForest...")
        resultado_ml = entrenar_random_forest_vs_baseline(numeros_term, k=100, n_lags=5, n_splits=5)
    else:
        print(f"Fase 5 (ML) omitida: {motivo}\n")

    # ---- Fase 6: Monte Carlo / bootstrap ----
    print(f"Backtesting walk-forward + bootstrap ({args.n_resamples:,} remuestreos)...")
    montecarlo = comparar_estrategias(numeros_term, k=args.top, n_resamples=args.n_resamples)

    # ---- Conclusión final ----
    p_fisher = fisher["p_valor_combinado_fisher"]
    n_sig_bh = bh["n_significativos_bh"]
    n_rechazan_crudo = sum(1 for r in resultados_fase3 if r.rechaza_h0)
    mc_signif = montecarlo["bootstrap"]["significativo"]

    contexto_crudo = (
        f"El método de Fisher combinado (sin corregir) dio p={p_fisher:.4f}, y {n_rechazan_crudo} de "
        f"{len(resultados_fase3)} tests individuales muestran p<{args.alpha} sin corregir; tras "
        f"corregir por comparaciones múltiples (Benjamini-Hochberg), solo {n_sig_bh} sigue siendo "
        "significativo."
    )

    if n_sig_bh > 1 and mc_signif:
        conclusion = (
            f"{contexto_crudo} Hay evidencia estadística robusta de desviación de la uniformidad Y una "
            "ventaja práctica medible en el backtesting. Esto amerita ampliar la muestra y repetir el "
            "análisis con replicación independiente antes de sacar conclusiones firmes: esto NO implica "
            "que se haya identificado un generador reproducible."
        )
    elif n_sig_bh > 1 and not mc_signif:
        conclusion = (
            f"{contexto_crudo} Hay evidencia estadística de desviación de la uniformidad que sobrevive "
            "a la corrección por comparaciones múltiples, pero esa desviación NO se traduce en una "
            "ventaja predictiva medible: el backtesting no supera al azar de forma significativa. Si la "
            "desviación es real, es demasiado sutil o inestable para explotarse, y debe tratarse con "
            "cautela — no como base para apostar."
        )
    else:
        conclusion = (
            f"{contexto_crudo} Encontrar 1-2 tests marginalmente significativos de {len(resultados_fase3)} "
            "corridos es exactamente lo esperable por puro azar (con 5 tests al 5%, ~23% de probabilidad "
            "de al menos un falso positivo), y no sobrevive a la corrección adecuada. El backtesting + "
            "bootstrap tampoco encuentra una ventaja predictiva significativa. En conjunto, los datos son "
            "compatibles con un proceso aleatorio. Ningún ranking, heurística o modelo evaluado en este "
            "reporte demostró una ventaja significativa sobre el azar puro. Los números 'calientes', "
            "'fríos' o de 'predicción' que se muestran en el dashboard diario deben tomarse como "
            "curiosidad estadística descriptiva, sin valor predictivo real."
        )

    contexto = {
        "n_sorteos": len(df),
        "fecha_inicio": df["fecha"].min().date().isoformat(),
        "fecha_fin": df["fecha"].max().date().isoformat(),
        "resultados_fase3": resultados_fase3,
        "fisher": fisher,
        "bh": bh,
        "entropia": entropia,
        "entropia_condicional": entropia_cond,
        "score_generador": score_gen,
        "espectro_top_potencia_relativa": float(espectro["potencia_relativa"].max()) if len(espectro) else 0.0,
        "n_ciclos_detectados": len(ciclos),
        "n_lags_probados": max_lag_ciclos,
        "ml_omitido": not gate,
        "ml_motivo": motivo,
        "resultado_ml": resultado_ml,
        "distancia_markov": distancia_markov,
        "montecarlo": montecarlo,
        "pares_impares": pi.set_index("categoria")["frecuencia_relativa"].round(4).to_dict(),
        "altos_bajos": ab.set_index("categoria")["frecuencia_relativa"].round(4).to_dict(),
        "conclusion_final": conclusion,
    }

    reporte_md = generar_reporte_cientifico(contexto)
    print("\n" + reporte_md)

    reports_dir = Path(args.reports_dir)
    md_path = guardar_markdown(reporte_md, reports_dir / "reporte_cientifico.md")
    pdf_path = guardar_pdf(reporte_md, reports_dir / "reporte_cientifico.pdf")
    print(f"\nReporte científico guardado en:\n  {md_path}\n  {pdf_path}")

    if not args.sin_abrir:
        try:
            webbrowser.open(pdf_path.resolve().as_uri())
        except Exception:
            pass  # sin navegador disponible (ej: corriendo en CI/servidor) -> el archivo ya quedo guardado


if __name__ == "__main__":
    main()

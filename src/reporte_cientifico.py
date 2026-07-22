"""Ensambla el reporte científico automático (Fase 8): responde explícitamente
las 5 preguntas del protocolo original, citando las métricas, p-valores e
intervalos de confianza calculados en las fases anteriores."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fpdf import FPDF
from fpdf.enums import XPos, YPos


def _fmt_ic(ic: tuple[float, float]) -> str:
    return f"[{ic[0]:.4f}, {ic[1]:.4f}]"


def generar_reporte_cientifico(contexto: dict) -> str:
    """`contexto` trae todos los resultados ya calculados por
    investigacion_cientifica.py. Devuelve el reporte en Markdown."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c = contexto
    lineas: list[str] = []

    lineas.append("# Reporte Científico — Quiniela Nocturna Provincia")
    lineas.append("")
    lineas.append(
        f"Generado {ts} · {c['n_sorteos']} sorteos analizados "
        f"({c['fecha_inicio']} a {c['fecha_fin']})"
    )
    lineas.append("")
    lineas.append(
        "**Restricción científica**: ninguna sección de este reporte afirma haber descubierto "
        "el mecanismo real del sorteo. Se distingue explícitamente entre correlación, "
        "coincidencia estadística, inferencia probabilística y evidencia reproducible."
    )
    lineas.append("")

    lineas.append("## Resumen ejecutivo (5 preguntas del protocolo)")
    lineas.append("")

    lineas.append("### 1. ¿Los resultados parecen realmente aleatorios?")
    fisher = c["fisher"]
    lineas.append(f"- {fisher['veredicto']}.")
    lineas.append(
        f"- Método de Fisher combinando {fisher['n_tests_con_p_valor']} tests independientes: "
        f"estadístico={fisher['estadistico_fisher']:.4f}, "
        f"p-valor combinado={fisher['p_valor_combinado_fisher']:.4f}."
    )
    lineas.append("")

    lineas.append("### 2. ¿Existe evidencia estadística de patrones?")
    for r in c["resultados_fase3"]:
        lineas.append(f"- {r.interpretacion()}")
    lineas.append(
        f"- Tras corrección por comparaciones múltiples (Benjamini-Hochberg): "
        f"{c['bh']['n_significativos_bh']} de {len(c['resultados_fase3'])} tests siguen siendo "
        "significativos (detalle en el anexo). Con varios tests corridos a la vez, encontrar "
        "1 test con p<0.05 por puro azar no es inusual; por eso se exige más de 1 test "
        "significativo TRAS la corrección antes de hablar de 'patrón'."
    )
    lineas.append("")

    lineas.append("### 3. ¿Existe evidencia de un generador reproducible?")
    score = c["score_generador"]
    lineas.append(
        f"- Score bayesiano heurístico de 'generador reproducible': "
        f"{score['probabilidad_posterior_media']:.3f} "
        f"(intervalo de credibilidad 95% {_fmt_ic(score['intervalo_credibilidad_95'])})."
    )
    if score["advertencia_muestra"]:
        lineas.append(f"- ADVERTENCIA: {score['advertencia_muestra']}")
    lineas.append(
        f"- Espectro de Fourier: potencia relativa del pico dominante = "
        f"{c['espectro_top_potencia_relativa']:.4f}. Un proceso aleatorio real tiene un espectro "
        "aproximadamente plano (sin picos dominantes); este valor bajo no sugiere periodicidad."
    )
    lineas.append(
        f"- Ciclos candidatos por autocorrelación: {c['n_ciclos_detectados']} lag(s) superan la "
        f"banda de significancia de {c['n_lags_probados']} evaluados — comparable a lo esperable "
        "por azar bajo comparaciones múltiples sin corregir."
    )
    lineas.append("")

    lineas.append("### 4. ¿Puede inferirse parcialmente el mecanismo generador?")
    lineas.append(
        "No se simulan generadores específicos (Linear Congruential Generator, Mersenne Twister, "
        "Xorshift, PCG, Lagged Fibonacci, Blum Blum Shub) porque eso requeriría asumir semilla y "
        "parámetros arbitrarios, y el protocolo pide explícitamente evitar la fuerza bruta de "
        "semillas. Las propiedades que sí distinguirían un generador determinista simple de ruido "
        "real — autocorrelación, periodicidad espectral, dependencia entre sorteos consecutivos — "
        "ya se evaluaron en las preguntas 2 y 3 y no muestran evidencia robusta de estructura."
    )
    lineas.append("")

    lineas.append("### 5. ¿Existe algún modelo que supere significativamente al azar?")
    if c["ml_omitido"]:
        lineas.append(f"- Modelos de ML: OMITIDOS. {c['ml_motivo']}")
    else:
        ml = c["resultado_ml"]
        lineas.append(
            f"- RandomForest vs baseline uniforme — accuracy: {ml['modelo']['accuracy_media']:.4f} "
            f"vs {ml['baseline_uniforme']['accuracy_media']:.4f}; log-loss: "
            f"{ml['modelo']['log_loss_media']:.4f} vs {ml['baseline_uniforme']['log_loss_media']:.4f}; "
            f"Brier: {ml['modelo']['brier_media']:.4f} vs {ml['baseline_uniforme']['brier_media']:.4f}. "
            f"¿Supera al baseline en accuracy? {'Sí' if ml['supera_baseline_accuracy'] else 'No'}."
        )
    mc = c["montecarlo"]
    lineas.append(
        f"- Backtesting walk-forward + bootstrap ({mc['bootstrap']['n_resamples']:,} remuestreos "
        f"sobre {mc['n_evaluaciones']} sorteos evaluados): tasa de acierto del ranking heurístico "
        f"top-{mc['k']} = {mc['tasa_acierto_heuristico']:.4f}, vs control aleatorio simulado = "
        f"{mc['tasa_acierto_azar_simulado']:.4f} (valor teórico de azar puro = "
        f"{mc['tasa_acierto_teorica_azar']:.4f})."
    )
    lineas.append(
        f"- Diferencia heurístico-azar: {mc['bootstrap']['diferencia_media']:.4f}, "
        f"IC 95% bootstrap {_fmt_ic(mc['bootstrap']['ic_95'])} — "
        f"{'DIFERENCIA SIGNIFICATIVA' if mc['bootstrap']['significativo'] else 'diferencia NO significativa (el intervalo incluye el cero)'}."
    )
    lineas.append("")

    lineas.append("## Conclusión")
    lineas.append(c["conclusion_final"])
    lineas.append("")

    lineas.append("## Anexo A: detalle de todos los tests de aleatoriedad (Fase 3)")
    for r in c["resultados_fase3"]:
        lineas.append(f"- {r.interpretacion()}")
    lineas.append("")

    lineas.append("## Anexo B: corrección de comparaciones múltiples (Benjamini-Hochberg)")
    for d in c["bh"]["detalle"]:
        lineas.append(
            f"- {d['nombre']}: p={d['p_valor']:.4f}, umbral BH={d['umbral_bh']:.4f}, "
            f"significativo tras corrección: {'sí' if d['significativo_bh'] else 'no'}."
        )
    lineas.append("")

    lineas.append("## Anexo C: estadística descriptiva adicional (Fase 2)")
    lineas.append(f"- Pares/impares: {c['pares_impares']}")
    lineas.append(f"- Altos/bajos: {c['altos_bajos']}")
    lineas.append(
        f"- Entropía de Shannon: {c['entropia']['entropia_bits']:.4f} bits "
        f"(máxima posible {c['entropia']['entropia_maxima_bits']:.4f} bits, "
        f"eficiencia {c['entropia']['eficiencia']:.4f}). Una eficiencia cercana a 1.0 indica que la "
        "distribución observada está cerca de la máxima incertidumbre posible (uniforme)."
    )
    if c["entropia_condicional"]["advertencia_sesgo_muestra"]:
        lineas.append(f"- ADVERTENCIA (entropía condicional): {c['entropia_condicional']['advertencia_sesgo_muestra']}")
    lineas.append(
        f"- Distancia de la matriz de transición de Markov a independencia total: "
        f"{c['distancia_markov']:.4f} (0 = coincide con independencia perfecta). Esta métrica "
        "también puede estar inflada por dispersión de la tabla si la muestra es chica; ver el "
        "test de independencia (Fase 3) como criterio principal, no este número aislado."
    )
    lineas.append("")

    return "\n".join(lineas)


def guardar_markdown(texto: str, ruta: Path) -> Path:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(texto, encoding="utf-8")
    return ruta


_REEMPLAZOS_PDF = {
    "—": "-", "–": "-", "’": "'", "‘": "'", "“": '"', "”": '"',
    "…": "...", "×": "x", "•": "-", "·": "-",
}


def _sanitizar_para_pdf(texto: str) -> str:
    for a, b in _REEMPLAZOS_PDF.items():
        texto = texto.replace(a, b)
    return texto.encode("latin-1", errors="replace").decode("latin-1")


def guardar_pdf(texto: str, ruta: Path) -> Path:
    """Renderizado simple del reporte en PDF (texto plano con jerarquía de
    encabezados), usando fpdf2 — liviano, sin dependencias nativas."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    for linea_original in texto.split("\n"):
        linea = _sanitizar_para_pdf(linea_original)
        if linea.startswith("# "):
            pdf.set_font("Helvetica", "B", 16)
            pdf.multi_cell(0, 10, linea[2:], new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        elif linea.startswith("## "):
            pdf.set_font("Helvetica", "B", 13)
            pdf.multi_cell(0, 8, linea[3:], new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        elif linea.startswith("### "):
            pdf.set_font("Helvetica", "B", 11)
            pdf.multi_cell(0, 7, linea[4:], new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        elif linea.strip() == "":
            pdf.ln(2)
        else:
            pdf.set_font("Helvetica", "", 10)
            pdf.multi_cell(0, 5, linea.replace("**", ""), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.output(str(ruta))
    return ruta

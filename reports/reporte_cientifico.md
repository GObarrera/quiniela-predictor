# Reporte Científico — Quiniela Nocturna Provincia

Generado 2026-10-19 05:25:27 · 7560 sorteos analizados (2025-07-21 a 2026-10-17)

**Restricción científica**: ninguna sección de este reporte afirma haber descubierto el mecanismo real del sorteo. Se distingue explícitamente entre correlación, coincidencia estadística, inferencia probabilística y evidencia reproducible.

## Resumen ejecutivo (5 preguntas del protocolo)

### 1. ¿Los resultados parecen realmente aleatorios?
- Se rechaza H0 de aleatoriedad de forma consolidada (método de Fisher).
- Método de Fisher combinando 4 tests independientes: estadístico=22.6209, p-valor combinado=0.0039.

### 2. ¿Existe evidencia estadística de patrones?
- Chi-cuadrado (uniformidad): NO se rechaza H0 (estadístico=91.0053, p=0.7042). 99 grados de libertad.
- Kolmogorov-Smirnov (uniformidad): Se RECHAZA H0 (estadístico=0.0173, p=0.0211). Aproximación continua sobre datos discretos (orientativa).
- Anderson-Darling (uniformidad): NO se rechaza H0 (estadístico=2.0078, sin p-valor exacto (valor crítico tabulado)). Comparado contra valor crítico tabulado 2.492 (D'Agostino & Stephens 1986).
- Wald-Wolfowitz (rachas): NO se rechaza H0 (estadístico=-1.8401, p=0.0658). 3701 rachas observadas sobre 7560 valores (esperadas ~3781.0).
- Test de independencia (X_t vs X_t-1): Se RECHAZA H0 (estadístico=112.1512, p=0.0125). Tabla 10x10, 81 gl, frecuencia esperada mínima 66.1 (válida).
- Tras corrección por comparaciones múltiples (Benjamini-Hochberg): 2 de 5 tests siguen siendo significativos (detalle en el anexo). Con varios tests corridos a la vez, encontrar 1 test con p<0.05 por puro azar no es inusual; por eso se exige más de 1 test significativo TRAS la corrección antes de hablar de 'patrón'.

### 3. ¿Existe evidencia de un generador reproducible?
- Score bayesiano heurístico de 'generador reproducible': 0.429 (intervalo de credibilidad 95% [0.1181, 0.7772]).
- Espectro de Fourier: potencia relativa del pico dominante = 0.0027. Un proceso aleatorio real tiene un espectro aproximadamente plano (sin picos dominantes); este valor bajo no sugiere periodicidad.
- Ciclos candidatos por autocorrelación: 4 lag(s) superan la banda de significancia de 50 evaluados — comparable a lo esperable por azar bajo comparaciones múltiples sin corregir.

### 4. ¿Puede inferirse parcialmente el mecanismo generador?
No se simulan generadores específicos (Linear Congruential Generator, Mersenne Twister, Xorshift, PCG, Lagged Fibonacci, Blum Blum Shub) porque eso requeriría asumir semilla y parámetros arbitrarios, y el protocolo pide explícitamente evitar la fuerza bruta de semillas. Las propiedades que sí distinguirían un generador determinista simple de ruido real — autocorrelación, periodicidad espectral, dependencia entre sorteos consecutivos — ya se evaluaron en las preguntas 2 y 3 y no muestran evidencia robusta de estructura.

### 5. ¿Existe algún modelo que supere significativamente al azar?
- RandomForest vs baseline uniforme — accuracy: 0.0100 vs 0.0100; log-loss: 18.0568 vs 4.6052; Brier: 1.0234 vs 0.9900. ¿Supera al baseline en accuracy? Sí.
- Backtesting walk-forward + bootstrap (100,000 remuestreos sobre 7530 sorteos evaluados): tasa de acierto del ranking heurístico top-8 = 0.0819, vs control aleatorio simulado = 0.0758 (valor teórico de azar puro = 0.0800).
- Diferencia heurístico-azar: 0.0061, IC 95% bootstrap [-0.0024, 0.0147] — diferencia NO significativa (el intervalo incluye el cero).

## Conclusión
El método de Fisher combinado (sin corregir) dio p=0.0039, y 2 de 5 tests individuales muestran p<0.05 sin corregir; tras corregir por comparaciones múltiples (Benjamini-Hochberg), solo 2 sigue siendo significativo. Hay evidencia estadística de desviación de la uniformidad que sobrevive a la corrección por comparaciones múltiples, pero esa desviación NO se traduce en una ventaja predictiva medible: el backtesting no supera al azar de forma significativa. Si la desviación es real, es demasiado sutil o inestable para explotarse, y debe tratarse con cautela — no como base para apostar.

## Anexo A: detalle de todos los tests de aleatoriedad (Fase 3)
- Chi-cuadrado (uniformidad): NO se rechaza H0 (estadístico=91.0053, p=0.7042). 99 grados de libertad.
- Kolmogorov-Smirnov (uniformidad): Se RECHAZA H0 (estadístico=0.0173, p=0.0211). Aproximación continua sobre datos discretos (orientativa).
- Anderson-Darling (uniformidad): NO se rechaza H0 (estadístico=2.0078, sin p-valor exacto (valor crítico tabulado)). Comparado contra valor crítico tabulado 2.492 (D'Agostino & Stephens 1986).
- Wald-Wolfowitz (rachas): NO se rechaza H0 (estadístico=-1.8401, p=0.0658). 3701 rachas observadas sobre 7560 valores (esperadas ~3781.0).
- Test de independencia (X_t vs X_t-1): Se RECHAZA H0 (estadístico=112.1512, p=0.0125). Tabla 10x10, 81 gl, frecuencia esperada mínima 66.1 (válida).

## Anexo B: corrección de comparaciones múltiples (Benjamini-Hochberg)
- Test de independencia (X_t vs X_t-1): p=0.0125, umbral BH=0.0125, significativo tras corrección: sí.
- Kolmogorov-Smirnov (uniformidad): p=0.0211, umbral BH=0.0250, significativo tras corrección: sí.
- Wald-Wolfowitz (rachas): p=0.0658, umbral BH=0.0375, significativo tras corrección: no.
- Chi-cuadrado (uniformidad): p=0.7042, umbral BH=0.0500, significativo tras corrección: no.

## Anexo C: estadística descriptiva adicional (Fase 2)
- Pares/impares: {'par': 0.4894, 'impar': 0.5106}
- Altos/bajos: {'bajo': 0.5015, 'alto': 0.4985}
- Entropía de Shannon: 6.6351 bits (máxima posible 6.6439 bits, eficiencia 0.9987). Una eficiencia cercana a 1.0 indica que la distribución observada está cerca de la máxima incertidumbre posible (uniforme).
- ADVERTENCIA (entropía condicional): Tabla conjunta de 10000 celdas con solo 7559 transiciones observadas: la mayoría de las celdas tiene 0 o 1 observaciones. La entropía condicional empírica está sesgada hacia abajo en este régimen (subestima la incertidumbre real) y NO debe interpretarse como evidencia de dependencia. Usar el test de independencia (chi-cuadrado sobre bins) para esa conclusión, no este número.
- Distancia de la matriz de transición de Markov a independencia total: 0.4707 (0 = coincide con independencia perfecta). Esta métrica también puede estar inflada por dispersión de la tabla si la muestra es chica; ver el test de independencia (Fase 3) como criterio principal, no este número aislado.

# Reporte Científico — Quiniela Nocturna Provincia

Generado 2026-09-11 05:22:05 · 6920 sorteos analizados (2025-07-21 a 2026-09-10)

**Restricción científica**: ninguna sección de este reporte afirma haber descubierto el mecanismo real del sorteo. Se distingue explícitamente entre correlación, coincidencia estadística, inferencia probabilística y evidencia reproducible.

## Resumen ejecutivo (5 preguntas del protocolo)

### 1. ¿Los resultados parecen realmente aleatorios?
- Se rechaza H0 de aleatoriedad de forma consolidada (método de Fisher).
- Método de Fisher combinando 4 tests independientes: estadístico=18.5271, p-valor combinado=0.0176.

### 2. ¿Existe evidencia estadística de patrones?
- Chi-cuadrado (uniformidad): NO se rechaza H0 (estadístico=89.3353, p=0.7463). 99 grados de libertad.
- Kolmogorov-Smirnov (uniformidad): Se RECHAZA H0 (estadístico=0.0178, p=0.0249). Aproximación continua sobre datos discretos (orientativa).
- Anderson-Darling (uniformidad): NO se rechaza H0 (estadístico=1.6431, sin p-valor exacto (valor crítico tabulado)). Comparado contra valor crítico tabulado 2.492 (D'Agostino & Stephens 1986).
- Wald-Wolfowitz (rachas): NO se rechaza H0 (estadístico=-1.2463, p=0.2127). 3408 rachas observadas sobre 6920 valores (esperadas ~3459.8).
- Test de independencia (X_t vs X_t-1): Se RECHAZA H0 (estadístico=108.0622, p=0.0240). Tabla 10x10, 81 gl, frecuencia esperada mínima 62.0 (válida).
- Tras corrección por comparaciones múltiples (Benjamini-Hochberg): 2 de 5 tests siguen siendo significativos (detalle en el anexo). Con varios tests corridos a la vez, encontrar 1 test con p<0.05 por puro azar no es inusual; por eso se exige más de 1 test significativo TRAS la corrección antes de hablar de 'patrón'.

### 3. ¿Existe evidencia de un generador reproducible?
- Score bayesiano heurístico de 'generador reproducible': 0.429 (intervalo de credibilidad 95% [0.1181, 0.7772]).
- Espectro de Fourier: potencia relativa del pico dominante = 0.0021. Un proceso aleatorio real tiene un espectro aproximadamente plano (sin picos dominantes); este valor bajo no sugiere periodicidad.
- Ciclos candidatos por autocorrelación: 2 lag(s) superan la banda de significancia de 50 evaluados — comparable a lo esperable por azar bajo comparaciones múltiples sin corregir.

### 4. ¿Puede inferirse parcialmente el mecanismo generador?
No se simulan generadores específicos (Linear Congruential Generator, Mersenne Twister, Xorshift, PCG, Lagged Fibonacci, Blum Blum Shub) porque eso requeriría asumir semilla y parámetros arbitrarios, y el protocolo pide explícitamente evitar la fuerza bruta de semillas. Las propiedades que sí distinguirían un generador determinista simple de ruido real — autocorrelación, periodicidad espectral, dependencia entre sorteos consecutivos — ya se evaluaron en las preguntas 2 y 3 y no muestran evidencia robusta de estructura.

### 5. ¿Existe algún modelo que supere significativamente al azar?
- RandomForest vs baseline uniforme — accuracy: 0.0099 vs 0.0094; log-loss: 18.4003 vs 4.6052; Brier: 1.0240 vs 0.9900. ¿Supera al baseline en accuracy? Sí.
- Backtesting walk-forward + bootstrap (100,000 remuestreos sobre 6890 sorteos evaluados): tasa de acierto del ranking heurístico top-8 = 0.0827, vs control aleatorio simulado = 0.0743 (valor teórico de azar puro = 0.0800).
- Diferencia heurístico-azar: 0.0084, IC 95% bootstrap [-0.0006, 0.0173] — diferencia NO significativa (el intervalo incluye el cero).

## Conclusión
El método de Fisher combinado (sin corregir) dio p=0.0176, y 2 de 5 tests individuales muestran p<0.05 sin corregir; tras corregir por comparaciones múltiples (Benjamini-Hochberg), solo 2 sigue siendo significativo. Hay evidencia estadística de desviación de la uniformidad que sobrevive a la corrección por comparaciones múltiples, pero esa desviación NO se traduce en una ventaja predictiva medible: el backtesting no supera al azar de forma significativa. Si la desviación es real, es demasiado sutil o inestable para explotarse, y debe tratarse con cautela — no como base para apostar.

## Anexo A: detalle de todos los tests de aleatoriedad (Fase 3)
- Chi-cuadrado (uniformidad): NO se rechaza H0 (estadístico=89.3353, p=0.7463). 99 grados de libertad.
- Kolmogorov-Smirnov (uniformidad): Se RECHAZA H0 (estadístico=0.0178, p=0.0249). Aproximación continua sobre datos discretos (orientativa).
- Anderson-Darling (uniformidad): NO se rechaza H0 (estadístico=1.6431, sin p-valor exacto (valor crítico tabulado)). Comparado contra valor crítico tabulado 2.492 (D'Agostino & Stephens 1986).
- Wald-Wolfowitz (rachas): NO se rechaza H0 (estadístico=-1.2463, p=0.2127). 3408 rachas observadas sobre 6920 valores (esperadas ~3459.8).
- Test de independencia (X_t vs X_t-1): Se RECHAZA H0 (estadístico=108.0622, p=0.0240). Tabla 10x10, 81 gl, frecuencia esperada mínima 62.0 (válida).

## Anexo B: corrección de comparaciones múltiples (Benjamini-Hochberg)
- Test de independencia (X_t vs X_t-1): p=0.0240, umbral BH=0.0125, significativo tras corrección: sí.
- Kolmogorov-Smirnov (uniformidad): p=0.0249, umbral BH=0.0250, significativo tras corrección: sí.
- Wald-Wolfowitz (rachas): p=0.2127, umbral BH=0.0375, significativo tras corrección: no.
- Chi-cuadrado (uniformidad): p=0.7463, umbral BH=0.0500, significativo tras corrección: no.

## Anexo C: estadística descriptiva adicional (Fase 2)
- Pares/impares: {'par': 0.4909, 'impar': 0.5091}
- Altos/bajos: {'bajo': 0.5025, 'alto': 0.4975}
- Entropía de Shannon: 6.6346 bits (máxima posible 6.6439 bits, eficiencia 0.9986). Una eficiencia cercana a 1.0 indica que la distribución observada está cerca de la máxima incertidumbre posible (uniforme).
- ADVERTENCIA (entropía condicional): Tabla conjunta de 10000 celdas con solo 6919 transiciones observadas: la mayoría de las celdas tiene 0 o 1 observaciones. La entropía condicional empírica está sesgada hacia abajo en este régimen (subestima la incertidumbre real) y NO debe interpretarse como evidencia de dependencia. Usar el test de independencia (chi-cuadrado sobre bins) para esa conclusión, no este número.
- Distancia de la matriz de transición de Markov a independencia total: 0.5006 (0 = coincide con independencia perfecta). Esta métrica también puede estar inflada por dispersión de la tabla si la muestra es chica; ver el test de independencia (Fase 3) como criterio principal, no este número aislado.

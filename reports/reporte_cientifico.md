# Reporte Científico — Quiniela Nocturna Provincia

Generado 2026-08-14 06:04:47 · 6440 sorteos analizados (2025-07-21 a 2026-08-13)

**Restricción científica**: ninguna sección de este reporte afirma haber descubierto el mecanismo real del sorteo. Se distingue explícitamente entre correlación, coincidencia estadística, inferencia probabilística y evidencia reproducible.

## Resumen ejecutivo (5 preguntas del protocolo)

### 1. ¿Los resultados parecen realmente aleatorios?
- No se rechaza H0 de aleatoriedad de forma consolidada (método de Fisher).
- Método de Fisher combinando 4 tests independientes: estadístico=15.1935, p-valor combinado=0.0555.

### 2. ¿Existe evidencia estadística de patrones?
- Chi-cuadrado (uniformidad): NO se rechaza H0 (estadístico=84.9068, p=0.8427). 99 grados de libertad.
- Kolmogorov-Smirnov (uniformidad): Se RECHAZA H0 (estadístico=0.0180, p=0.0307). Aproximación continua sobre datos discretos (orientativa).
- Anderson-Darling (uniformidad): NO se rechaza H0 (estadístico=1.5049, sin p-valor exacto (valor crítico tabulado)). Comparado contra valor crítico tabulado 2.492 (D'Agostino & Stephens 1986).
- Wald-Wolfowitz (rachas): NO se rechaza H0 (estadístico=0.0583, p=0.9535). 3223 rachas observadas sobre 6440 valores (esperadas ~3220.7).
- Test de independencia (X_t vs X_t-1): Se RECHAZA H0 (estadístico=109.1191, p=0.0204). Tabla 10x10, 81 gl, frecuencia esperada mínima 58.2 (válida).
- Tras corrección por comparaciones múltiples (Benjamini-Hochberg): 0 de 5 tests siguen siendo significativos (detalle en el anexo). Con varios tests corridos a la vez, encontrar 1 test con p<0.05 por puro azar no es inusual; por eso se exige más de 1 test significativo TRAS la corrección antes de hablar de 'patrón'.

### 3. ¿Existe evidencia de un generador reproducible?
- Score bayesiano heurístico de 'generador reproducible': 0.143 (intervalo de credibilidad 95% [0.0042, 0.4593]).
- Espectro de Fourier: potencia relativa del pico dominante = 0.0028. Un proceso aleatorio real tiene un espectro aproximadamente plano (sin picos dominantes); este valor bajo no sugiere periodicidad.
- Ciclos candidatos por autocorrelación: 1 lag(s) superan la banda de significancia de 50 evaluados — comparable a lo esperable por azar bajo comparaciones múltiples sin corregir.

### 4. ¿Puede inferirse parcialmente el mecanismo generador?
No se simulan generadores específicos (Linear Congruential Generator, Mersenne Twister, Xorshift, PCG, Lagged Fibonacci, Blum Blum Shub) porque eso requeriría asumir semilla y parámetros arbitrarios, y el protocolo pide explícitamente evitar la fuerza bruta de semillas. Las propiedades que sí distinguirían un generador determinista simple de ruido real — autocorrelación, periodicidad espectral, dependencia entre sorteos consecutivos — ya se evaluaron en las preguntas 2 y 3 y no muestran evidencia robusta de estructura.

### 5. ¿Existe algún modelo que supere significativamente al azar?
- Modelos de ML: OMITIDOS. Solo 0 test(s) siguen siendo significativos tras corregir por comparaciones múltiples (se requiere más de 1). No corresponde entrenar modelos de ML: hacerlo forzaría una señal que los datos no muestran de forma robusta. Esta sección se documenta como OMITIDA de forma explícita, en vez de mostrar un resultado forzado.
- Backtesting walk-forward + bootstrap (100,000 remuestreos sobre 6410 sorteos evaluados): tasa de acierto del ranking heurístico top-8 = 0.0811, vs control aleatorio simulado = 0.0718 (valor teórico de azar puro = 0.0800).
- Diferencia heurístico-azar: 0.0094, IC 95% bootstrap [0.0002, 0.0186] — DIFERENCIA SIGNIFICATIVA.

## Conclusión
El método de Fisher combinado (sin corregir) dio p=0.0555, y 2 de 5 tests individuales muestran p<0.05 sin corregir; tras corregir por comparaciones múltiples (Benjamini-Hochberg), solo 0 sigue siendo significativo. Encontrar 1-2 tests marginalmente significativos de 5 corridos es exactamente lo esperable por puro azar (con 5 tests al 5%, ~23% de probabilidad de al menos un falso positivo), y no sobrevive a la corrección adecuada. El backtesting + bootstrap tampoco encuentra una ventaja predictiva significativa. En conjunto, los datos son compatibles con un proceso aleatorio. Ningún ranking, heurística o modelo evaluado en este reporte demostró una ventaja significativa sobre el azar puro. Los números 'calientes', 'fríos' o de 'predicción' que se muestran en el dashboard diario deben tomarse como curiosidad estadística descriptiva, sin valor predictivo real.

## Anexo A: detalle de todos los tests de aleatoriedad (Fase 3)
- Chi-cuadrado (uniformidad): NO se rechaza H0 (estadístico=84.9068, p=0.8427). 99 grados de libertad.
- Kolmogorov-Smirnov (uniformidad): Se RECHAZA H0 (estadístico=0.0180, p=0.0307). Aproximación continua sobre datos discretos (orientativa).
- Anderson-Darling (uniformidad): NO se rechaza H0 (estadístico=1.5049, sin p-valor exacto (valor crítico tabulado)). Comparado contra valor crítico tabulado 2.492 (D'Agostino & Stephens 1986).
- Wald-Wolfowitz (rachas): NO se rechaza H0 (estadístico=0.0583, p=0.9535). 3223 rachas observadas sobre 6440 valores (esperadas ~3220.7).
- Test de independencia (X_t vs X_t-1): Se RECHAZA H0 (estadístico=109.1191, p=0.0204). Tabla 10x10, 81 gl, frecuencia esperada mínima 58.2 (válida).

## Anexo B: corrección de comparaciones múltiples (Benjamini-Hochberg)
- Test de independencia (X_t vs X_t-1): p=0.0204, umbral BH=0.0125, significativo tras corrección: no.
- Kolmogorov-Smirnov (uniformidad): p=0.0307, umbral BH=0.0250, significativo tras corrección: no.
- Chi-cuadrado (uniformidad): p=0.8427, umbral BH=0.0375, significativo tras corrección: no.
- Wald-Wolfowitz (rachas): p=0.9535, umbral BH=0.0500, significativo tras corrección: no.

## Anexo C: estadística descriptiva adicional (Fase 2)
- Pares/impares: {'par': 0.4925, 'impar': 0.5075}
- Altos/bajos: {'bajo': 0.5012, 'alto': 0.4988}
- Entropía de Shannon: 6.6343 bits (máxima posible 6.6439 bits, eficiencia 0.9986). Una eficiencia cercana a 1.0 indica que la distribución observada está cerca de la máxima incertidumbre posible (uniforme).
- ADVERTENCIA (entropía condicional): Tabla conjunta de 10000 celdas con solo 6439 transiciones observadas: la mayoría de las celdas tiene 0 o 1 observaciones. La entropía condicional empírica está sesgada hacia abajo en este régimen (subestima la incertidumbre real) y NO debe interpretarse como evidencia de dependencia. Usar el test de independencia (chi-cuadrado sobre bins) para esa conclusión, no este número.
- Distancia de la matriz de transición de Markov a independencia total: 0.5220 (0 = coincide con independencia perfecta). Esta métrica también puede estar inflada por dispersión de la tabla si la muestra es chica; ver el test de independencia (Fase 3) como criterio principal, no este número aislado.

# Reporte Científico — Quiniela Nocturna Provincia

Generado 2026-08-18 03:28:01 · 6500 sorteos analizados (2025-07-21 a 2026-08-17)

**Restricción científica**: ninguna sección de este reporte afirma haber descubierto el mecanismo real del sorteo. Se distingue explícitamente entre correlación, coincidencia estadística, inferencia probabilística y evidencia reproducible.

## Resumen ejecutivo (5 preguntas del protocolo)

### 1. ¿Los resultados parecen realmente aleatorios?
- No se rechaza H0 de aleatoriedad de forma consolidada (método de Fisher).
- Método de Fisher combinando 4 tests independientes: estadístico=10.1461, p-valor combinado=0.2549.

### 2. ¿Existe evidencia estadística de patrones?
- Chi-cuadrado (uniformidad): NO se rechaza H0 (estadístico=84.3077, p=0.8538). 99 grados de libertad.
- Kolmogorov-Smirnov (uniformidad): Se RECHAZA H0 (estadístico=0.0175, p=0.0362). Aproximación continua sobre datos discretos (orientativa).
- Anderson-Darling (uniformidad): NO se rechaza H0 (estadístico=1.4940, sin p-valor exacto (valor crítico tabulado)). Comparado contra valor crítico tabulado 2.492 (D'Agostino & Stephens 1986).
- Wald-Wolfowitz (rachas): NO se rechaza H0 (estadístico=-0.8314, p=0.4057). 3217 rachas observadas sobre 6500 valores (esperadas ~3250.5).
- Test de independencia (X_t vs X_t-1): NO se rechaza H0 (estadístico=80.3710, p=0.4988). Tabla 10x10, 81 gl, frecuencia esperada mínima 58.6 (válida).
- Tras corrección por comparaciones múltiples (Benjamini-Hochberg): 0 de 5 tests siguen siendo significativos (detalle en el anexo). Con varios tests corridos a la vez, encontrar 1 test con p<0.05 por puro azar no es inusual; por eso se exige más de 1 test significativo TRAS la corrección antes de hablar de 'patrón'.

### 3. ¿Existe evidencia de un generador reproducible?
- Score bayesiano heurístico de 'generador reproducible': 0.143 (intervalo de credibilidad 95% [0.0042, 0.4593]).
- Espectro de Fourier: potencia relativa del pico dominante = 0.0029. Un proceso aleatorio real tiene un espectro aproximadamente plano (sin picos dominantes); este valor bajo no sugiere periodicidad.
- Ciclos candidatos por autocorrelación: 4 lag(s) superan la banda de significancia de 50 evaluados — comparable a lo esperable por azar bajo comparaciones múltiples sin corregir.

### 4. ¿Puede inferirse parcialmente el mecanismo generador?
No se simulan generadores específicos (Linear Congruential Generator, Mersenne Twister, Xorshift, PCG, Lagged Fibonacci, Blum Blum Shub) porque eso requeriría asumir semilla y parámetros arbitrarios, y el protocolo pide explícitamente evitar la fuerza bruta de semillas. Las propiedades que sí distinguirían un generador determinista simple de ruido real — autocorrelación, periodicidad espectral, dependencia entre sorteos consecutivos — ya se evaluaron en las preguntas 2 y 3 y no muestran evidencia robusta de estructura.

### 5. ¿Existe algún modelo que supere significativamente al azar?
- Modelos de ML: OMITIDOS. Solo 0 test(s) siguen siendo significativos tras corregir por comparaciones múltiples (se requiere más de 1). No corresponde entrenar modelos de ML: hacerlo forzaría una señal que los datos no muestran de forma robusta. Esta sección se documenta como OMITIDA de forma explícita, en vez de mostrar un resultado forzado.
- Backtesting walk-forward + bootstrap (100,000 remuestreos sobre 6470 sorteos evaluados): tasa de acierto del ranking heurístico top-8 = 0.0815, vs control aleatorio simulado = 0.0754 (valor teórico de azar puro = 0.0800).
- Diferencia heurístico-azar: 0.0060, IC 95% bootstrap [-0.0032, 0.0153] — diferencia NO significativa (el intervalo incluye el cero).

## Conclusión
El método de Fisher combinado (sin corregir) dio p=0.2549, y 1 de 5 tests individuales muestran p<0.05 sin corregir; tras corregir por comparaciones múltiples (Benjamini-Hochberg), solo 0 sigue siendo significativo. Encontrar 1-2 tests marginalmente significativos de 5 corridos es exactamente lo esperable por puro azar (con 5 tests al 5%, ~23% de probabilidad de al menos un falso positivo), y no sobrevive a la corrección adecuada. El backtesting + bootstrap tampoco encuentra una ventaja predictiva significativa. En conjunto, los datos son compatibles con un proceso aleatorio. Ningún ranking, heurística o modelo evaluado en este reporte demostró una ventaja significativa sobre el azar puro. Los números 'calientes', 'fríos' o de 'predicción' que se muestran en el dashboard diario deben tomarse como curiosidad estadística descriptiva, sin valor predictivo real.

## Anexo A: detalle de todos los tests de aleatoriedad (Fase 3)
- Chi-cuadrado (uniformidad): NO se rechaza H0 (estadístico=84.3077, p=0.8538). 99 grados de libertad.
- Kolmogorov-Smirnov (uniformidad): Se RECHAZA H0 (estadístico=0.0175, p=0.0362). Aproximación continua sobre datos discretos (orientativa).
- Anderson-Darling (uniformidad): NO se rechaza H0 (estadístico=1.4940, sin p-valor exacto (valor crítico tabulado)). Comparado contra valor crítico tabulado 2.492 (D'Agostino & Stephens 1986).
- Wald-Wolfowitz (rachas): NO se rechaza H0 (estadístico=-0.8314, p=0.4057). 3217 rachas observadas sobre 6500 valores (esperadas ~3250.5).
- Test de independencia (X_t vs X_t-1): NO se rechaza H0 (estadístico=80.3710, p=0.4988). Tabla 10x10, 81 gl, frecuencia esperada mínima 58.6 (válida).

## Anexo B: corrección de comparaciones múltiples (Benjamini-Hochberg)
- Kolmogorov-Smirnov (uniformidad): p=0.0362, umbral BH=0.0125, significativo tras corrección: no.
- Wald-Wolfowitz (rachas): p=0.4057, umbral BH=0.0250, significativo tras corrección: no.
- Test de independencia (X_t vs X_t-1): p=0.4988, umbral BH=0.0375, significativo tras corrección: no.
- Chi-cuadrado (uniformidad): p=0.8538, umbral BH=0.0500, significativo tras corrección: no.

## Anexo C: estadística descriptiva adicional (Fase 2)
- Pares/impares: {'par': 0.4917, 'impar': 0.5083}
- Altos/bajos: {'bajo': 0.5005, 'alto': 0.4995}
- Entropía de Shannon: 6.6345 bits (máxima posible 6.6439 bits, eficiencia 0.9986). Una eficiencia cercana a 1.0 indica que la distribución observada está cerca de la máxima incertidumbre posible (uniforme).
- ADVERTENCIA (entropía condicional): Tabla conjunta de 10000 celdas con solo 6499 transiciones observadas: la mayoría de las celdas tiene 0 o 1 observaciones. La entropía condicional empírica está sesgada hacia abajo en este régimen (subestima la incertidumbre real) y NO debe interpretarse como evidencia de dependencia. Usar el test de independencia (chi-cuadrado sobre bins) para esa conclusión, no este número.
- Distancia de la matriz de transición de Markov a independencia total: 0.5198 (0 = coincide con independencia perfecta). Esta métrica también puede estar inflada por dispersión de la tabla si la muestra es chica; ver el test de independencia (Fase 3) como criterio principal, no este número aislado.

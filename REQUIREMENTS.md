# REQUIREMENTS

Fuente de verdad del loop autónomo (`autoloop/`). El script lee **solo la tabla** de abajo.

- **Prioridad**: P0 (más alta) a P3.
- **Obligatorio**: `Sí` cuenta para el control de finalización; `No` se hace si hay tiempo.
- **Estado**: `pendiente` · `en_progreso` · `implementado` · `probado` · `bloqueado`.
- **Prueba**: comando que verifica el requisito. Un requisito solo cuenta como terminado si está
  `probado` **y** tiene una prueba declarada; el loop vuelve a correr esa prueba antes de commitear.
- **Depende de**: IDs separados por coma, o `-`.

| ID | Prioridad | Obligatorio | Estado | Depende de | Prueba | Descripción |
|---|---|---|---|---|---|---|
| LOOP-01 | P0 | Sí | probado | - | `bash autoloop/tests/run_tests.sh` | Script de looping con iteraciones limitadas, pausas, timeout por iteración y códigos de salida |
| LOOP-02 | P0 | Sí | probado | LOOP-01 | `bash autoloop/tests/run_tests.sh` | Estado persistente en archivos (REQUIREMENTS/PROJECT_STATUS/ROADMAP/BLOCKERS + autoloop/state) y reanudación sin duplicar trabajo |
| LOOP-03 | P0 | Sí | probado | LOOP-01 | `bash autoloop/tests/run_tests.sh` | Límites y seguridad: instancia única, presupuesto, sin progreso, 3 intentos por tarea, permisos mínimos, sin push ni bypass por defecto |
| LOOP-04 | P0 | Sí | probado | LOOP-01 | `bash autoloop/tests/run_tests.sh` | Control de finalización verificable e informe de bloqueos (autoloop/tracker.py) |
| LOOP-05 | P0 | Sí | probado | LOOP-01 | `bash autoloop/tests/run_tests.sh` | Historial estructurado de iteraciones (autoloop/state/iterations.jsonl) con redacción de claves y datos personales |
| LOOP-06 | P0 | Sí | probado | LOOP-01 | `bash autoloop/tests/run_tests.sh` | Inicio, detención (archivo STOP o señal) y reanudación documentados; modo de prueba sin acciones externas (--mock / --test-mode) |
| QP-01 | P1 | No | probado | - | `python3 -m unittest discover -s tests -q` | Agregar pruebas unitarias con unittest en tests/test_terminaciones.py para src/terminaciones.py (dataframe_terminaciones: últimos 2 dígitos, no modifica el original). Solo pandas, sin red |
| INM-00 | P0 | Sí | bloqueado | - | - | Especificación del buscador inmobiliario nacional (secciones 1 a 16 del pedido) y decisión del repositorio donde se desarrolla. Ver BLOCKERS.md B-001 |
| INM-01 | P0 | Sí | pendiente | INM-00 | - | Buscador de propiedades (filtros, resultados, ficha) |
| INM-02 | P0 | Sí | pendiente | INM-00 | - | Recepción/carga de propiedades por anunciantes |
| INM-03 | P1 | Sí | pendiente | INM-00 | - | CRM de contactos y consultas |
| INM-04 | P1 | Sí | pendiente | INM-00 | - | Captación de profesionales inmobiliarios |
| INM-05 | P1 | Sí | pendiente | INM-03 | - | Email transaccional (en modo prueba hasta tener proveedor y credenciales) |
| INM-06 | P2 | Sí | pendiente | INM-03 | - | WhatsApp Business (en modo prueba hasta tener cuenta aprobada y credenciales) |
| INM-07 | P2 | Sí | pendiente | INM-01 | - | Espacios AdSense (requiere cuenta aprobada; no se activa sin autorización) |
| INM-08 | P2 | Sí | pendiente | INM-01 | - | Módulo de patrocinadores |
| INM-09 | P1 | Sí | pendiente | INM-01, INM-02 | - | Pruebas automatizadas de extremo a extremo |
| INM-10 | P2 | Sí | pendiente | INM-01 | - | Documentación de usuario y operación |

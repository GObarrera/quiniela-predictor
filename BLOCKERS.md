# BLOCKERS

Bloqueos que requieren intervención humana. El loop no los resuelve solo; sigue con lo que sea
independiente. Al resolver uno: cambiá el estado de la tarea en REQUIREMENTS.md (de `bloqueado`
a `pendiente`) y marcá aquí el bloqueo como resuelto.

### B-001 — Falta la especificación del buscador inmobiliario y el repositorio destino

- Estado: abierto
- Afecta: INM-00 y, por dependencia, INM-01 a INM-10.
- Causa: el pedido de looping (sección 17) referencia un "buscador inmobiliario nacional" y sus
  secciones previas, pero en este repositorio (`quiniela-predictor`, un analizador estadístico de
  Quiniela) no existe esa especificación ni código del buscador. Implementarlo acá sin
  especificación mezclaría dos proyectos y obligaría a inventar requisitos.
- Acción requerida:
  1. Decidir el repositorio (uno nuevo, recomendado, o este).
  2. Agregar las secciones 1 a 16 como requisitos en la tabla de REQUIREMENTS.md
     (o pegarlas en `docs/especificacion_inmobiliaria.md` y crear la tarea de desglosarlas).
  3. Pasar INM-00 a `probado` con la prueba `test -f docs/especificacion_inmobiliaria.md`
     o eliminarla si los requisitos ya quedan cargados.
  4. Copiar la carpeta `autoloop/` y los 4 archivos de seguimiento al repositorio elegido.

### B-002 — Credenciales y cuentas de servicios externos (futuro)

- Estado: abierto (no bloquea hoy: depende de B-001)
- Afecta: INM-05 (email), INM-06 (WhatsApp Business), INM-07 (AdSense).
- Causa: requieren cuentas aprobadas, credenciales, condiciones legales (consentimiento,
  baja de suscripción) y posiblemente gastos. El loop no las contrata ni envía comunicaciones reales.
- Acción requerida: crear las cuentas, cargar credenciales como variables de entorno (nunca en el
  repo) y autorizar explícitamente el paso de modo prueba a modo real.

### B-003 — Ejecución desatendida/programada

- Estado: abierto (informativo)
- Causa: correr el loop sin una persona presente necesita una máquina encendida (o un runner) con
  Claude Code autenticado y un presupuesto aprobado. No se configuró ninguna programación.
- Acción requerida: si se desea, seguir "Programación" en autoloop/README.md y aprobar el presupuesto.
